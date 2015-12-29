 # coding=UTF-8
from __future__ import division
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
import rethinkdb as r
import re

#setup rethinkdb
conn = r.connect(host="rt-database", port=28015)
if 'news' not in r.db('test').table_list().run(conn):
    r.db('test').table_create('news').run(conn)
if 'finance' not in r.db('test').table_list().run(conn):
    r.db('test').table_create('finance').run(conn)


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
    categories = ['World', 'U.S.', 'Politics', 'Business Day', 'Technology', 'Science', 'Health', 'Real Estate']
    if obj["section"] in categories:
        #setup redis connection
        rs = redis.StrictRedis(host='data-cache', port=6379, db=0)
        #format long-url in 'url' formatting
        url = urllib.quote(obj['url'], safe='')
        access_token = 'ab6dbf0df548c91cffaa1ae82e0d9f4a52dfe4f8'
        #query bitly with long-url to get shortened version
        bitly_uri = 'https://api-ssl.bitly.com//v3/shorten?access_token=' + access_token + '&longUrl=' + url + '&format=txt'
        rq = requests.get(bitly_uri)

        key = rq.text[-8:-1]

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
            storycontent = (soup.find_all("p", { "class" : re.compile(r"^(story-content|articleBody)$")}))
            if (len(storycontent) > 1):
                encodedFinal = reduce(lambda x, y: x + '<p>' + y.text + '</p>', storycontent, '')
                article = {'title': normalize(obj['title']), 'abstract': normalize(obj['abstract']), 'url': rq.text[0:-1], 'created_date': obj['created_date'][0:10], 'article_text': encodedFinal}

                rs.hmset(key, article)
                rs.expire(key, 3600)
                r.db('test').table('news').wait()
                r.db('test').table('news').insert({'id': key, 'article': article}).run(conn)

def delOldData():
    #worker running every 72 hours to delete the last market period's data (390 records)
    #(currently every 1 hr and deleting 120 records for testing)
    rs = redis.StrictRedis(host='data-cache', port=6379, db=1)
    keys = rs.keys('*')
    #for each stock ticker
    for key in keys:
        values = rs.hkeys(key)
        #390 minutes in 6.5 hours
        toDelete = values[-120:]
	# print toDelete
        rs.hdel(key, *toDelete)

#Pull articles from NYT Newswire API
def getNews():
    h = HTMLParser.HTMLParser()
    uri = "http://api.nytimes.com/svc/news/v3/content/all/all/24?limit=5&api-key=202f0d73b368cec23b977f5a141728ce:17:73664181"
    try:
        rq = requests.get(uri)
    except requests.exceptions.Timeout:
        return "API request timeout"
    except requests.exceptions.RequestException as e:
        return e

    #raises stored HTTP error if one occured
    #hard to say if this works
    rq.raise_for_status()

    objectResp = json.loads(h.unescape(rq.text))
    #pull out relevant information only
    for obj in objectResp["results"]:
        extractArticles(obj)
    print 'did the news'

def getFinData():
    #setup redis connection
    rs = redis.StrictRedis(host='data-cache', port=6379, db=1)
    url = "https://query.yahooapis.com/v1/public/yql?q=select%20symbol%2C%20LastTradePriceOnly%20from%20yahoo.finance.quote%20where%20symbol%20in%20(%22MCHI%22%2C%0A%22DBA%22%2C%0A%22USO%22%2C%0A%22IYZ%22%2C%0A%22EEM%22%2C%0A%22VPL%22%2C%0A%22XLE%22%2C%0A%22HEDJ%22%2C%0A%22XLF%22%2C%0A%22XLV%22%2C%0A%22EPI%22%2C%0A%22XLI%22%2C%0A%22EWJ%22%2C%0A%22ILF%22%2C%0A%22BLV%22%2C%0A%22UDN%22%2C%0A%22XLB%22%2C%0A%22IYR%22%2C%0A%22SCPB%22%2C%0A%22FXE%22%2C%0A%22IWM%22%2C%0A%22XLK%22%2C%0A%22XLU%22)&format=json&diagnostics=true&env=store%3A%2F%2Fdatatables.org%2Falltableswithkeys&callback="
    rq = requests.get(url)
    time = rq.json()["query"]["created"]
    obj = rq.json()["query"]["results"]["quote"]
    for datum in obj:
        rs.hset(datum["symbol"], time, datum["LastTradePriceOnly"])
        r.db('test').table('finance').wait()
        r.db('test').table('finance').insert({'symbol': datum["symbol"], 'time': time, 'price': datum["LastTradePriceOnly"]}).run(conn)
    print 'stored the data'

def populateNews():
    next_call = time.time()
    while True:
        getNews()
        next_call = next_call+120
        time.sleep(next_call - time.time())

def populateFinData():
    next_call = time.time()
    while True:
        getFinData()
        #pull data every 15 seconds to make testing easier (eventually 1 min)
        next_call = next_call+15
        now = time.gmtime(time.time())
        #add min/100 to hour to make it easy to check if it's 9:30
        hm = now.tm_hour + now.tm_min/100
        #also check if time is between EST 9:30am and 4pm (14:30 and 21 UTC)
        if  0 <= now.tm_wday < 5 and 14.3 <= hm <= 21.0:
            time.sleep(next_call - time.time())
        else:
            #sleep until the next market open
            sleep()

def sleep():
    now = time.gmtime(time.time())
    hm = now.tm_hour + now.tm_min/100
    #it's a weekend or it's outside trading hours, so sleep and keep checking
    while now.tm_wday > 4 or 21 < hm or hm < 14.3:
        time.sleep(1)
        now = time.gmtime(time.time())
        hm = now.tm_hour + now.tm_min/100
    populateFinData()

def delWorker():
    next_call = time.time()
    while True:
        delOldData()
        #wait 1 hour
        next_call = next_call+3600
        time.sleep(next_call - time.time())

def initNews():
    h = HTMLParser.HTMLParser()
    offset = 0
    #change back to 45 for production
    while offset <= 10:
        r = requests.get("http://api.nytimes.com/svc/news/v3/content/all/all/24?offset=" + str(offset) + "&api-key=202f0d73b368cec23b977f5a141728ce:17:73664181")
        objectResp = json.loads(h.unescape(r.text))
        #pull out relevant information only
        for obj in objectResp["results"]:
            extractArticles(obj)
        #change back to 15 for production
        offset += 10

#initially populate news cache from the past 60 newswire articles
initNews()

newsThread = threading.Thread(target=populateNews)
dataThread = threading.Thread(target=populateFinData)
newsThread.start()
dataThread.start()

delWorkerThread = threading.Thread(target=delWorker)
delWorkerThread.start()
