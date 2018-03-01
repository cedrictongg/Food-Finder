import requests
import json
import credentials

url = 'https://api.yelp.com/v3/businesses/search'
params = { 'location': 'Los Angeles, CA',
           'term': 'burgers',
           'categories': 'vegan',
           'sort_by': 'distance',
           'limit': 5
         }
# create a python file to get access key for the Yelp API
# if you want to use the skill for your own use
yelp = requests.get(url = url, params = params, headers = {'Authorization': 'Bearer {}'.format(credentials.api_key)})
yelp_json = json.loads(yelp.text)
for i in yelp_json['businesses']:
    print('You can find delicious {} {} from {} at {}.'.format(params['categories'], params['term'], i['name'], i['location']['address1']))

# print('You can find delicious {} from {} at {}.'.format(params['term'], yelp_json['businesses'][0]['name'], yelp_json['businesses'][0]['location']['address1']))
