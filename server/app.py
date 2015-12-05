from flask import Flask
import requests

@app.route('/')
def hello_world():
    return 'Hello World'

def extractArticles(obj):
    return {'title': obj['title'], 'abstract': obj['abstract'], 'url': obj['url']}

@app.route("/proxy-example")
def proxy_example():
    uri = "http://api.nytimes.com/svc/news/v3/content/all/all/2?api-key=202f0d73b368cec23b977f5a141728ce:17:73664181"
    # params = {'api-key': ''}
    r = requests.get(uri)
    objectResp = r.json()

    articles = map(extractArticles, objectResp["results"])
    print articles

    return 'hello world'

if __name__ == '__main__':
    app.run()
