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

Outside the project repo, run:

`python -m almanac-app-service.test.test -v`
