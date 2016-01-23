[![Build Status](https://circleci.com/gh/almanac-news/almanac-app-service.svg?style=shield&circle-token=:circle-token)](https://circleci.com/gh/almanac-news/almanac-app-service)

# almanac-app-service
A multi-threaded Python service, providing data aggregation and scraping, database storage, and notification support

### To run:

_To run it locally:_

If you don't have virtualenv installed, from command line run:

`sudo pip install virtualenv`

Clone the repo and set up a virtual environment inside it:

`virtualenv venv`

Then activate it with:

`source venv/bin/activate`

To start the server:

`python app.py`

### Note: The most recent version of this must be run with the other modules of Alamanc News including the Redis cache and RethinkDB!!

The architecture is now such that docker-compose with multiple data volumes and linking is integral. The service will not run without at least the redis and rethink links out.
