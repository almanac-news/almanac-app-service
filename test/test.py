import json
import os
from ..server.app import app
import unittest
import tempfile

class SimpleTest(unittest.TestCase):

    # def check_content_type(headers):
    #     eq_(headers['Content-Type'], 'application/json')

    #basic setup
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()

    #test that hitting the '/news' api route returns a list structure
    def test_news(self):
        rv = self.app.get('/news')
        # check_content_type(rv.headers)
        resp = json.loads(rv.data)

        self.assertIsInstance(resp, list)

    #test that hitting the '/top' route with a category returns a list structure
    def test_top(self):
        rv = self.app.get('/top/health')
        resp = json.loads(rv.data)

        self.assertIsInstance(resp, list)

if __name__ == '__main__':
    unittest.main()
