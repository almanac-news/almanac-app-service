from flask import Flask
from flask_restful import Resource, Api
import requests
import unicodedata
from bs4 import BeautifulSoup

app = Flask(__name__)
api = Api(app)

app.config.from_envvar('APP_SETTINGS', silent=True)

#Function to convert unicode data we get back from NYT to ASCII
def normalize(unicode):
    return unicodedata.normalize('NFKD', unicode).encode('ascii', 'ignore')

#Mapping function to extract title, abstract, and url from the response array
def extractArticles(obj):
    return {'title': normalize(obj['title']), 'abstract': normalize(obj['abstract']), 'url': normalize(obj['url'])}

#Flask-RESTful syntax to set up an api endpoint that hits NYT newswire and parses the results
class GetNewswire(Resource):
    def get(self):
        uri = "http://api.nytimes.com/svc/news/v3/content/all/all/2?api-key=202f0d73b368cec23b977f5a141728ce:17:73664181"
        # params = {'api-key': ''}
        r = requests.get(uri)
        objectResp = r.json()
        articles = map(extractArticles, objectResp["results"])
        return articles

#API endpoint to get top stories categorically.
#Valid categories include: home, world, national, politics, nyregion, business, opinion,
#technology, science, health, sports, arts, fashion, dining, travel, magazine, realestate
class GetTop(Resource):
    def get(self, category):
        uri = "http://api.nytimes.com/svc/topstories/v1/" + category + ".json?api-key=073b7d846c48b66824b40bffc377123c:8:73664181"
        r = requests.get(uri)
        objectResp = r.json()
        articles = map(extractArticles, objectResp["results"])
        return articles

#Actually attach the endpoint to the correct url
api.add_resource(GetNewswire, '/news')
api.add_resource(GetTop, '/top/<category>')

if __name__ == '__main__':
    app.run()
