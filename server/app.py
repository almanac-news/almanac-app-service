 # coding=UTF-8
import requests
import unicodedata
import urllib
import json
import HTMLParser
import redis
from bs4 import BeautifulSoup
import cookielib
import mechanize
from readability.readability import Document
import time
import threading

#setup redis connection
rs = redis.StrictRedis(host='data-cache', port=6379, db=0)

# setup connection to NYT and programmatically login with mechanize
#mechanize setup for cookies and ignoring robots.txt
cj = cookielib.CookieJar()
#put the 'browser' object in the global scope
br = mechanize.Browser()
br.set_handle_robots(False)
br.set_cookiejar(cj)

#login url
url = 'https://myaccount.nytimes.com/auth/login'
#mechanize syntax, open the login page
br.open(url)
#select login form and login with user credentials
br.select_form(nr=0)
br.form['userid'] = 'natejlevine@gmail.com'
br.form['password'] = 'monkeybisness'
br.submit()

#Format unicode we get back from NYT properly, replacing unprintable characters
def normalize(unicode):
    result = (unicode.encode('utf-8')).replace('“','"').replace('”','"').replace("’","'").replace("‘","'").replace('—','-').replace(' ', ' ')
    return result

#Function to scrape article text, clean and format it, and store it into redis under a hashmap
def extractArticles(obj):
    #format long-url in 'url' formatting
    url = urllib.quote(obj['url'], safe='')
    access_token = 'ab6dbf0df548c91cffaa1ae82e0d9f4a52dfe4f8'
    #query bitly with long-url to get shortened version
    bitly_uri = 'https://api-ssl.bitly.com//v3/shorten?access_token=' + access_token + '&longUrl=' + url + '&format=txt'
    r = requests.get(bitly_uri)

    key = r.text[-8:-1]

    #if article is not already in redis db
    if (rs.exists(key) == 0):
        #scrape the news article
        html = br.open(obj['url']).read()

        #run the article through readability
        readable_article = Document(html).summary()
        readable_title = Document(html).title()

        #run it through BeautifulSoup to parse only relevant tags
        soup = BeautifulSoup(readable_article, 'lxml')

        #grab story content tags and concat them together
        storycontent = (soup.find_all("p", { "class":"story-content" }))
        encodedFinal = reduce(lambda x, y: x + '***' + y.text, storycontent, '')
        article = {'title': normalize(obj['title']), 'abstract': normalize(obj['abstract']), 'url': r.text[0:-1], 'created_date': obj['created_date'][0:10], 'article_text': encodedFinal}

        rs.hmset(key, article)
        rs.expire(key, 3600)

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

#Pull articles from NYT Newswire API
def getNews():
    h = HTMLParser.HTMLParser()
    uri = "http://api.nytimes.com/svc/news/v3/content/all/all/24?limit=10&api-key=202f0d73b368cec23b977f5a141728ce:17:73664181"
    try:
        r = requests.get(uri)
    except requests.exceptions.Timeout:
        return "API request timeout"
    except requests.exceptions.RequestException as e:
        return e

    #raises stored HTTP error if one occured
    #hard to say if this works
    r.raise_for_status()

    objectResp = json.loads(h.unescape(r.text))
    #pull out relevant information only
    for obj in objectResp["results"]:
        extractArticles(obj)
    # return 'Did the redis thing'

#Query yahoo finance's historical data api for EU=X (USD to Euro exchange rate) starting
#from (arbitrarily) 2015-11-23 and end date - whenever the article was published
# def getFinData(date):
#     urlFirst = "https://query.yahooapis.com/v1/public/yql?q=select%20*%20from%20yahoo.finance.historicaldata%20where%20symbol%20%3D%20%22EUR%3DX%22%20and%20startDate%20%3D%20%222015-11-23%22%20and%20endDate%20%3D%20%22"
#     urlSecond = "%22&format=json&diagnostics=true&env=store%3A%2F%2Fdatatables.org%2Falltableswithkeys&callback="
#     r = requests.get(urlFirst + date + urlSecond)
#     return r.json()

#API endpoint: for a given date parameter, get a series of currency data from the date set in getFinData
#up until that date
# class GetFinData(Resource):
#     def get(self, date):
#         finData = getFinData(date)
#         series = map(extractData, finData["query"]['results']['quote'])
#         return series

def populateNews():
    next_call = time.time()
    while True:
        getNews()
        next_call = next_call+180
        time.sleep(next_call - time.time())

newsThread = threading.Thread(target=populateNews)
newsThread.start()
