from flask import Flask
from flask_restful import Resource, Api
import requests
import unicodedata

app = Flask(__name__)
api = Api(app)

@app.route('/')
def hello_world():
    return 'Hello World'

def normalize(unicode):
    return unicodedata.normalize('NFKD', unicode).encode('ascii', 'ignore')

def extractArticles(obj):
    return {'title': normalize(obj['title']), 'abstract': normalize(obj['abstract']), 'url': normalize(obj['url'])}
#
# @app.route("/proxy-example")
# def proxy_example():
#     uri = "http://api.nytimes.com/svc/news/v3/content/all/all/2?api-key=202f0d73b368cec23b977f5a141728ce:17:73664181"
#     # params = {'api-key': ''}
#     r = requests.get(uri)
#     objectResp = r.json()
#
#     articles = map(extractArticles, objectResp["results"])
#     print articles
#
#     return 'hello world'

class GetNewswire(Resource):
    def get(self):
        uri = "http://api.nytimes.com/svc/news/v3/content/all/all/2?api-key=202f0d73b368cec23b977f5a141728ce:17:73664181"
        # params = {'api-key': ''}
        r = requests.get(uri)
        objectResp = r.json()
        articles = map(extractArticles, objectResp["results"])

        return articles

api.add_resource(GetNewswire, '/news')

if __name__ == '__main__':
    app.run()
