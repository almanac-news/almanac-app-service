 # coding=UTF-8
from flask import Flask
from flask_restful import Resource, Api
import requests
import unicodedata
# import numpy
from flask.ext.cors import CORS
import urllib
import json

app = Flask(__name__)
#enable cross-origin headers
CORS(app)
api = Api(app)

app.config.from_envvar('APP_SETTINGS', silent=True)

@app.route('/')
def landing_page():
    return "JOB SEARCH DIESEL!!!!!!!!!!"

#Convert unicode data we get back from NYT to ASCII
def normalize(unicode):
    result = (unicode.encode('utf-8')).replace('“','"').replace('”','"').replace("’","'")
    return result
    # query = urllib.quote(unicode.encode('utf8', 'replace'))
    # return urllib.unquote(query).decode('utf8')

#Mapping function to extract title, abstract, url, and date from the response array
def extractArticles(obj):
    url = urllib.quote(obj['url'], safe='')
    access_token = 'ab6dbf0df548c91cffaa1ae82e0d9f4a52dfe4f8'
    uri = 'https://api-ssl.bitly.com//v3/shorten?access_token=' + access_token + '&longUrl=' + url + '&format=txt'
    r = requests.get(uri)
    print obj['title']
    return {'title': normalize(obj['title']), 'abstract': normalize(obj['abstract']), 'url': r.text[0:-2], 'created_date': obj['created_date'][0:10]}

#Mapping function to pull out and compose the date and closing value for each day in the
#list of results from Yahoo
#obj represents stats from asset prices per one specific day
def extractData(obj):
    return {'date': obj["Date"], 'value': obj['Close']}

#Map extractData onto the series of data retrieved from Yahoo for each news article's window of time
#obj represents an article's dict as composed from extractArticles
#CURRENTLY UNNECESSARY DUE TO 'date/<date>' ROUTE
# def mapFinData(obj):
#     finData = getFinData(obj["created_date"])
#     #attach the data to a key on the obj
#     obj["data"] = map(extractData, finData["query"]['results']['quote'])
#     return obj

#Flask-RESTful syntax to set up an api endpoint that hits NYT newswire, then gets relevant financial data from Yahoo finance
# and parses the results into a JSON object
class GetNewswire(Resource):
    def get(self):
        uri = "http://api.nytimes.com/svc/news/v3/content/all/all/24?limit=10&api-key=202f0d73b368cec23b977f5a141728ce:17:73664181"

        r = requests.get(uri)
        print r.headers['content-type']
        print r.encoding
        objectResp = json.loads(normalize(r.text))
        #pull out relevant information only
        articles = map(extractArticles, objectResp["results"])

        # #attach relevant financial data to each article's dict
        # data = map(mapFinData, articles)
        # return data

        return articles

#API endpoint to get top stories categorically w/ financial data.
#Valid categories include: home, world, national, politics, nyregion, business, opinion,
#technology, science, health, sports, arts, fashion, dining, travel, magazine, realestate
class GetTop(Resource):
    def get(self, category):
        uri = "http://api.nytimes.com/svc/topstories/v1/" + category + ".json?api-key=073b7d846c48b66824b40bffc377123c:8:73664181"
        r = requests.get(uri)
        objectResp = r.json()
        articles = map(extractArticles, objectResp["results"])

        # data = map(mapFinData, articles)
        # return data

        #return just the top 10 for now
        return articles[0:9]

#Query yahoo finance's historical data api for EU=X (USD to Euro exchange rate) starting
#from (arbitrarily) 2015-11-23 and end date - whenever the article was published
def getFinData(date):
    urlFirst = "https://query.yahooapis.com/v1/public/yql?q=select%20*%20from%20yahoo.finance.historicaldata%20where%20symbol%20%3D%20%22EUR%3DX%22%20and%20startDate%20%3D%20%222015-11-23%22%20and%20endDate%20%3D%20%22"
    urlSecond = "%22&format=json&diagnostics=true&env=store%3A%2F%2Fdatatables.org%2Falltableswithkeys&callback="
    r = requests.get(urlFirst + date + urlSecond)
    return r.json()

#API endpoint: for a given date parameter, get a series of currency data from the date set in getFinData
#up until that date
class GetFinData(Resource):
    def get(self, date):
        finData = getFinData(date)
        series = map(extractData, finData["query"]['results']['quote'])
        return series


#Attach the endpoints to the correct url
api.add_resource(GetNewswire, '/news')
api.add_resource(GetTop, '/top/<category>')
api.add_resource(GetFinData, '/date/<date>')

if __name__ == '__main__':
    app.run(host='0.0.0.0')
