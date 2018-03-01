from __future__ import print_function
import requests
import json
import credentials

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

def get_welcome_response():
	session_attributes = {}
	card_title = "Welcome"
	speech_output = "Welcome to Food Finder. What would you like to eat?"
	reprompt_text = None
	should_end_session = False
	return build_response(session_attributes, build_speechlet_response(speech_output, should_end_session))

def handle_session_end_request():
	card_title = "Session Ended"
	speech_output = "Thank you for using Food Finder!"
	should_end_session = True
	return build_response({}, build_speechlet_response(speech_output, should_end_session))

# --------------- Intents ------------------

def food_recommendation_intent(intent, session):
    session_attributes = session.get('attributes', {})
    should_end_session = False
    speech_output = ''
    category = ''
    food = ''
    reprompt_text = 'Is there anything else you want to find?'
    print('food finder is running')
    if 'category' in intent['slots'] or 'Food' in intent['slots']:
        foods = intent['slots']
        print(foods)
        if 'value' in foods['category']:
            category = foods['category']['value']
        else:
            category = None
        if 'value' in foods['Food']:
            food = foods['Food']['value']
        places = yelp_conn(category, food)
        if category == None:
            speech_output = ''.join([speech_output, 'You can find delicious {} at {} on {}'.format(food, places[0]['name'], places[0]['location']['address1'])])
        else:
            speech_output = ''.join([speech_output, 'You can find delicious {} {} at {} on {}'.format(category, food, places[0]['name'], places[0]['location']['address1'])])
        print(places)
    return build_response(session_attributes, build_speechlet_response('Food Finder', speech_output, reprompt_text, should_end_session))

# --------------- Helper Functions ------------------

def yelp_conn(category, term):
    url = 'https://api.yelp.com/v3/businesses/search'
    params = { 'location': 'Los Angeles, CA',
               'term': term,
               'categories': category,
               'sort_by': 'distance',
               'limit': 5
             }
    # create a python file to get access key for the Yelp API
    # if you want to use the skill for your own use
    yelp = requests.get(url = url, params = params, headers = {'Authorization': 'Bearer {}'.format(credentials.api_key)})
    yelp_json = json.loads(yelp.text)

    return yelp_json['businesses']

# --------------- Specific Events ------------------

def on_intent(intent_request, session):
	print("on_intent requestId=" + intent_request['requestId'] + ", sessionId=" + session['sessionId'])
	intent = intent_request['intent']
	intent_name = intent_request['intent']['name']
	if intent_name == "FoodRecommendationIntent":
		return food_recommendation_intent(intent, session)
	elif intent_name == "AMAZON.HelpIntent":
		return get_welcome_response()
	elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
		return handle_session_end_request()
	else:
		raise ValueError("Invalid intent")

# --------------- Generic Events ------------------

def on_session_started(session_started_request, session):
	print("on_session_started requestId=" + session_started_request['requestId']+ ", sessionId=" + session['sessionId'])

def on_launch(launch_request, session):
	print("on_launch requestId=" + launch_request['requestId'] + ", sessionId=" + session['sessionId'])
	return get_welcome_response()

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
