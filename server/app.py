 # coding=UTF-8
from __future__ import division
import os
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
    r.db('test').table('finance').index_create('time').run(conn)
if 'subscriptions' not in r.db('test').table_list().run(conn):
    r.db('test').table_create('subscriptions').run(conn)


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
br.form['userid'] = os.environ['USERID']
br.form['password'] = os.environ['PASSWORD']
br.submit()

#Format unicode we get back from NYT properly, replacing unprintable characters
def normalize(unicode):
    result = (unicode.encode('utf-8')).replace('“','"').replace('”','"').replace("’","'").replace("‘","'").replace('—','-')
    return result

#Function to scrape article text, clean and format it, and store it into redis under a hashmap
def extractArticles(obj):
    categories = [
        'World',
        'U.S.',
        'Politics',
        'Business Day',
        'Technology',
        'Science',
        'Health',
        'Real Estate'
    ]
    if obj["section"] in categories:
        #setup redis connection
        rs = redis.StrictRedis(host='data-cache', port=6379, db=0)
        #format long-url in 'url' formatting
        url = urllib.quote(obj['url'], safe='')
        access_token = os.environ['BITLY_TOKEN']
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
                article = {
                    'title': normalize(obj['title']),
                    'abstract': normalize(obj['abstract']),
                    'url': rq.text[0:-1],
                    'created_date': obj['created_date'],
                    'article_text': encodedFinal,
                    'section': obj['section'],
                    'subsection': obj['subsection']
                }

                rs.hmset(key, article)
                rs.expire(key, 3600)
                r.db('test').table('news').wait()
                r.db('test').table('news').insert({'id': key, 'article': article, 'section': obj['section'], 'subsection': obj['subsection'], 'likes': 0}).run(conn)

#Pull articles from NYT Newswire API
def getNews():
    h = HTMLParser.HTMLParser()
    nyt_key = os.environ['NYT_KEY']
    uri = "http://api.nytimes.com/svc/news/v3/content/all/all/24?limit=5&api-key=" + nyt_key
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
    gmt = time.gmtime(time.time())
    now = str(gmt.tm_year) + '-' + str(gmt.tm_mon) + '-' + str(gmt.tm_mday) + 'T' + str(gmt.tm_hour) + ':' + str(gmt.tm_min) + ':' + str(gmt.tm_sec)
    print 'did the news: ' + now

def getFinData():
    url = (
        "https://query.yahooapis.com/v1/public/yql?q=select%20symbol%2C%20LastTradePriceOnly%20"
        "from%20yahoo.finance.quote%20where%20symbol%20in%20(%22MCHI%22%2C%0A%22DBA%22%2C%0A%22"
        "USO%22%2C%0A%22IYZ%22%2C%0A%22EEM%22%2C%0A%22VPL%22%2C%0A%22XLE%22%2C%0A%22HEDJ%22%2C%"
        "0A%22XLF%22%2C%0A%22XLV%22%2C%0A%22EPI%22%2C%0A%22XLI%22%2C%0A%22EWJ%22%2C%0A%22ILF%22"
        "%2C%0A%22BLV%22%2C%0A%22UDN%22%2C%0A%22XLB%22%2C%0A%22IYR%22%2C%0A%22SCPB%22%2C%0A%22F"
        "XE%22%2C%0A%22IWM%22%2C%0A%22XLK%22%2C%0A%22XLU%22)&format=json&diagnostics=true&env=s"
        "tore%3A%2F%2Fdatatables.org%2Falltableswithkeys&callback="
    )
    rq = requests.get(url)
    date = rq.json()["query"]["created"]
    obj = rq.json()["query"]["results"]["quote"]
    for datum in obj:
        r.db('test').table('finance').wait()
        r.db('test').table('finance').insert({'symbol': datum["symbol"], 'time': date, 'price': datum["LastTradePriceOnly"]}).run(conn)
    gmt = time.gmtime(time.time())
    now = str(gmt.tm_year) + '-' + str(gmt.tm_mon) + '-' + str(gmt.tm_mday) + 'T' + str(gmt.tm_hour) + ':' + str(gmt.tm_min) + ':' + str(gmt.tm_sec)
    print 'stored the data: ' + now

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
        time.sleep(next_call - time.time())

def initNews():
    h = HTMLParser.HTMLParser()
    offset = 0
    #change back to 45 for production
    while offset <= 10:
        nyt_key = os.environ['NYT_KEY']
        r = requests.get("http://api.nytimes.com/svc/news/v3/content/all/all/24?offset=" + str(offset) + "&api-key=" + nyt_key)
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

next_c = time.time()
while True:
    for thread in threading.enumerate():
        if thread.is_alive() != True:
            if thread.name == 'Thread-1':
                #re-login to NYT with mechanize
                newsThread = threading.Thread(target=populateNews)
                newsThread.start()
            elif thread.name == 'Thread-2':
                dataThread = threading.Thread(target=populateFinData)
                dataThread.start()
    next_c = next_c+5
    time.sleep(next_c - time.time())
