from flask import Flask
from flask_restful import Resource, Api
import requests
import unicodedata
import numpy

app = Flask(__name__)
api = Api(app)

app.config.from_envvar('APP_SETTINGS', silent=True)

@app.route('/')
def landing_page():
    return "Swole Team 6"

#Convert unicode data we get back from NYT to ASCII
def normalize(unicode):
    return unicodedata.normalize('NFKD', unicode).encode('ascii', 'ignore')

#Mapping function to extract title, abstract, url, and date from the response array
def extractArticles(obj):
    return {'title': normalize(obj['title']), 'abstract': normalize(obj['abstract']), 'url': normalize(obj['url']), 'created_date': obj['created_date'][0:10]}

#Mapping function to pull out and compose the date and closing value for each day in the
#list of results from Yahoo
#obj represents stats from asset prices per one specific day
def extractData(obj):
    return {'date': obj["Date"], 'value': obj['Close']}

#Map extractData onto the series of data retrieved from Yahoo for each news article's window of time
#obj represents an article's dict as composed from extractArticles
def mapFinData(obj):
    finData = getFinData(obj["created_date"])
    #attach the data to a key on the obj
    obj["data"] = map(extractData, finData["query"]['results']['quote'])
    return obj

# def mean(list):
#
# def standardDev(obj):
#     length = len(list)
#     mean = reduce(lambda x, y: x + y, list) / length
#     differences = map(lambda x: math.sqrt(x - mean), list)
#     variance = reduce(lambda x, y: x + y, differences) / length
#     return math.sqrt(variance)

#Flask-RESTful syntax to set up an api endpoint that hits NYT newswire, then gets relevant financial data from Yahoo finance
# and parses the results into a JSON object
class GetNewswire(Resource):
    def get(self):
        uri = "http://api.nytimes.com/svc/news/v3/content/all/all/24?limit=10&api-key=202f0d73b368cec23b977f5a141728ce:17:73664181"

        r = requests.get(uri)
        objectResp = r.json()
        #pull out relevant information only
        articles = map(extractArticles, objectResp["results"])

        #attach relevant financial data to each article's dict
        data = map(mapFinData, articles)
        return data

#API endpoint to get top stories categorically w/ financial data.
#Valid categories include: home, world, national, politics, nyregion, business, opinion,
#technology, science, health, sports, arts, fashion, dining, travel, magazine, realestate
class GetTop(Resource):
    def get(self, category):
        uri = "http://api.nytimes.com/svc/topstories/v1/" + category + ".json?api-key=073b7d846c48b66824b40bffc377123c:8:73664181"
        r = requests.get(uri)
        objectResp = r.json()
        articles = map(extractArticles, objectResp["results"])

        data = map(mapFinData, articles)
        return data

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
