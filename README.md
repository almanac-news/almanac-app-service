# almanac-app-service
Flask server providing data aggregation, processing, and api endpoints for the web-server

### To run:

If you don't have virtualenv installed, from command line run:

`sudo pip install virtualenv`

Clone the repo and set up a virtual environment inside it:

`virtualenv venv`

Then grab Flask:

`pip install Flask`

To start the server:

`python app.py`

### For Testing:

Inside the project repo, run:

`nosetests -v --with-coverage --cover-inclusive --cover-package=server`

### API Endpoints:

##### /news
Currently returns the headline, url, abstract, and created_date of the 10 newest articles from NYT newswire in all categories.


##### /top/_category_
Does the same with top articles from NYT in a specific category taken from the following: home, world, national, politics, nyregion, business, opinion,
technology, science, health, sports, arts, fashion, dining, travel, magazine, realestate.

##### /date/_date_
Takes a date and returns the USD/EUR conversion rate (querying yahoo finance API) each day from an arbitrary start date up to the parameter. Current arbitrary start date is: 2015-11-23.
