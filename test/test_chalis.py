import unittest
from test import test_support
from webtest import TestApp
from google.appengine.ext import webapp
import logging

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed

import datetime

import chalis
import models

class SuccessFailError(unittest.TestCase):

    def setUp(self):
        logging.info('In setUp()')
        
    def tearDown(self):
        logging.info('In tearDown()')

    def test_success(self):
        logging.info('Running test_success()')
        self.assertTrue(True)


class HomePageTest(unittest.TestCase):

    def setUp(self):
        self.application = chalis.app

    def test_default_page(self):
        app = TestApp(self.application)
        response = app.get('/')
        self.assertEqual('200 OK', response.status)
        self.assertTrue('Hello, world!' in response) 
        
class CreateChallengeTest(unittest.TestCase):
    def setUp(self):
        logging.info('In CreateChallenge setUp()')
                
    def test_short_name_creation(self):
        new_id, short_name = chalis.find_short_name('808 Cali Bros Reddit Challenge')
        self.assertEqual('808CaliBrosRedd', short_name)  

    def test_new_contract_creation(self):
        full_name = '808 Cali Bros Reddit Challenge'

        new_id, short_name = chalis.find_short_name(full_name)
        
        chalis.create_challenge(new_id, short_name, full_name)

        added_contract = models.Contract.query(models.Contract.contract_id == new_id).get()

        self.assertEqual(new_id, added_contract.contract_id)
        self.assertEqual(short_name, added_contract.short_name)
        self.assertEqual(full_name, added_contract.challenge_name)
     
        
class FetchChallengeInfoTest(unittest.TestCase):
    def setUp(self):
        logging.info('In FetchChallengeInfo setUp()')

    def test_fetch_contract_info(self):
        # Info to be entered in so we can later retreive it
        name = "Great new challenge"
        short_name = "Greatnewchallenge" 
        obj_type = "geolocation"
        length = 1
        unit = "weeks"
        start = datetime.date.today()
        con_id = 2
        stakes_ids = [1, 2]

        newCon = models.Contract(contract_id = con_id,
                        challenge_name = name,
                        short_name = short_name,
                        objective_type = obj_type,
                        time_period = length,
                        time_unit = unit,
                        start_date = start,
                        stakes_id = stakes_ids)
        newCon.put()

        r1, r2, r3, r4, r5, r6, r7 = chalis.fetch_contract_info(short_name)
        self.assertEqual(name, r1)
        self.assertEqual(obj_type, r2)
        self.assertEqual(length, r3)
        self.assertEqual(unit, r4)
        self.assertEqual(start, r5)
        self.assertEqual(con_id, r6)
        self.assertEqual(stakes_ids, r7)

    def test_fetch_stakes_info(self):
        
        


def test_main():
    test_support.run_unittest(HomePageTest, CreateChallengeTest)

if __name__ == '__main__':
    test_main()
