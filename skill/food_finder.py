from __future__ import print_function
import requests
import json
import credentials
import boto3

from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }

def build_response(session_attributes, speechlet_response):
    return {
    	'version': '1.0',
    	'sessionAttributes': session_attributes,
    	'response': speechlet_response
    }

# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response(session):
    session_attributes = {}
    card_title = 'Welcome'
    should_end_session = False
    speech_output = ''
    check = get_item(session['user']['userId'])
    if not check:
        speech_output = 'Welcome to Food Finder. Start by saying: choose location'
    else:
        speech_output = 'Welcome to Food Finder. What would you like to eat?'
    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, speech_output, should_end_session))

def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thank you for using Food Finder!"
    should_end_session = True
    return build_response({}, build_speechlet_response(card_title, speech_output, None, should_end_session))

# --------------- Intents ------------------

# TODO: Add a way to change location if the user requests it
def get_location_intent(intent, session):
    session_attributes = {}
    check = get_item(session['user']['userId'])
    dialog_state = intent['dialogState']
    speech_output = ''
    print(intent)
    if 'location' in check[0]:
        should_end_session = False
        speech_output = 'Your location should be: {}.'.format(check[0]['location'])
        speech_output = ''.join([speech_output, ' What would you like to eat?'])
        reprompt_text = 'What would you like to eat?'
        return build_response(session_attributes, build_speechlet_response(intent['intent']['name'], speech_output, reprompt_text, should_end_session))
    else:
        if dialog_state in ('STARTED', 'IN_PROGRESS'):
            return continue_dialog()
        elif dialog_state == 'COMPLETED':
            should_end_session = False
            insert_item(session['user']['userId'], intent['intent']['slots']['Area']['value'])
            speech_output = ''.join([speech_output, 'Alright, we can start looking for food. What did you want to eat?'])
            reprompt_text = 'What did you want to eat?'
            return build_response(session_attributes, build_speechlet_response(intent['intent']['name'], speech_output, reprompt_text, should_end_session))

def food_recommendation_intent(intent, session):
    session_attributes = session.get('attributes', {})
    check = get_item(session['user']['userId'])
    dialog_state = intent['dialogState']
    intent = intent['intent']
    should_end_session = False
    speech_output = ''
    reprompt_text = speech_output
    category = ''
    food = ''
    print('food finder is running')
    if 'category' in intent['slots'] or 'Food' in intent['slots']:
        foods = intent['slots']
        print(foods)
        if 'value' in foods['Category'] and 'value' in foods['Food']:
            should_end_session = True
            category = foods['Category']['value']
            food = foods['Food']['value']
            places = yelp_conn(category, food, check[0]['location'])
            if foods['Category']['value'].upper() == 'none'.upper():
                speech_output = ''.join([speech_output, 'You can find {}, with your dietary restriction, if any, at {} on {}'.format(food, places[0]['name'], places[0]['location']['address1'])])
            return build_response(session_attributes, build_speechlet_response('Food Finder', speech_output, reprompt_text, should_end_session))
        else:
            if dialog_state in ('STARTED', 'IN_PROGRESS'):
                return continue_dialog()
            elif dialog_state == 'COMPLETED':
                should_end_session = True
                print('ending here')
                return build_response(session_attributes, build_speechlet_response('Food Finder', speech_output, reprompt_text, should_end_session))
            speech_output = ''.join([speech_output, 'Try to specify what you want to eat!'])
    return build_response(session_attributes, build_speechlet_response('Food Finder', speech_output, reprompt_text, should_end_session))

# --------------- Helper Functions ------------------

def insert_item(userId, location):
    dynamodb = boto3.resource('dynamodb', region_name = 'us-east-1')
    table = dynamodb.Table('FoodFinderSkill')

    response = table.put_item(
        Item = {
            'userId': userId,
            'location': location
        }
    )
    print('item inserted')

def get_item(userId):
    dynamodb = boto3.resource('dynamodb', region_name = 'us-east-1')
    table = dynamodb.Table('FoodFinderSkill')
    response = 'None'
    try:
        response = table.query(
            KeyConditionExpression = Key('userId').eq(userId)
        )
    except IndexError as e:
        return None
    else:
        return response['Items']


def yelp_conn(category, term, location):
    url = 'https://api.yelp.com/v3/businesses/search'
    params = { 'location': location,
               'term': term,
               'categories': category,
               'sort_by': 'rating',
               'limit': 1
             }
    # create a python file to get access key for the Yelp API
    # if you want to use the skill for your own use
    yelp = requests.get(url = url, params = params, headers = {'Authorization': 'Bearer {}'.format(credentials.api_key)})
    yelp_json = json.loads(yelp.text)
    return yelp_json['businesses']

def continue_dialog():
    message = {}
    message['shouldEndSession'] = False
    message['directives'] = [{'type': 'Dialog.Delegate'}]
    return build_response({}, message)

# --------------- Specific Events ------------------

def on_intent(intent_request, session):
    print("on_intent requestId=" + intent_request['requestId'] + ", sessionId=" + session['sessionId'])
    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']
    if intent_name == 'FoodRecommendationIntent':
    	return food_recommendation_intent(intent_request, session)
    elif intent_name == 'GetLocationIntent':
        return get_location_intent(intent_request, session)
    elif intent_name == 'AMAZON.HelpIntent':
    	return get_welcome_response(session)
    elif intent_name == 'AMAZON.CancelIntent' or intent_name == 'AMAZON.StopIntent':
    	return handle_session_end_request()
    else:
    	raise ValueError("Invalid intent")

# --------------- Generic Events ------------------

def on_session_started(session_started_request, session):
    print("on_session_started requestId=" + session_started_request['requestId']+ ", sessionId=" + session['sessionId'])

def on_launch(launch_request, session):
    print("on_launch requestId=" + launch_request['requestId'] + ", sessionId=" + session['sessionId'])
    return get_welcome_response(session)

def on_session_ended(session_ended_request, session):
    print("on_session_ended requestId=" + session_ended_request['requestId'] + ", sessionId=" + session['sessionId'])

# --------------- Main handler ------------------

def lambda_handler(event, context):
    print("event.session.application.applicationId=" + event['session']['application']['applicationId'])

    if event['session']['new']:
    	on_session_started({'requestId': event['request']['requestId']}, event['session'])

    if event['request']['type'] == "LaunchRequest":
    	return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
    	return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
    	return on_session_ended(event['request'], event['session'])
