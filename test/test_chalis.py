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

    def test_fetch_contract_info_only_short_name(self):
        full_name = "My Fave Challenge"
        short_name = "MyFaveChallenge"
        newCon = models.Contract(contract_id = 1,
                                 challenge_name = full_name,
                                 short_name = short_name)
        newCon.put()

        r1, r2, r3, r4, r5, r6, r7 = chalis.fetch_contract_info(short_name)

        self.assertEqual(1, r6)
        self.assertEqual(full_name, r1)
        self.assertEqual(None, r2)
        self.assertEqual(None, r3)
        self.assertEqual(None, r4)
        self.assertEqual(None, r5)
        self.assertEqual([], r7)

    def test_fetch_stakes_info(self):
        new_stakes1 = models.Stakes(stakes_id = 1,
                                  position = 'first',
                                  stakes_desc = "Gets free lunch")
        new_stakes2 = models.Stakes(stakes_id = 2,
                                   position = 'last',
                                   stakes_desc = "Buys lunch")
        new_stakes1.put()
        new_stakes2.put()

        stakes_info = chalis.fetch_stakes_info([1,2])

        self.assertEqual("Gets free lunch", stakes_info[0]['first'])
        self.assertEqual("Buys lunch", stakes_info[1]['last'])
        

class InviteTest(unittest.TestCase):
    def setUp(self):
        logging.info('In Invite setUp()')

    def test_invite_context_creation(self):
        # Will build up a context object in the same way InvitePage does
        context = {'joined' : {}}
        
        # First need to add combatant-users for a new contract,
        models.Contract(contract_id = 1).put()
        models.User(user_id = 1, google_username = "liam").put()
        models.Combatant(combatant_id = 1, name = "Liam").put()
        models.ContractCombatant(contract_id = 1, combatant_id = 1).put()
        models.CombatantUser(combatant_id = 1, user_id = 1).put()
        models.User(user_id = 2, google_username = "jeff").put()
        models.User(user_id = 3, google_username = "bob2").put()
        models.Combatant(combatant_id = 2, name = "Best Team").put()
        models.ContractCombatant(contract_id = 1, combatant_id = 2).put()
        models.CombatantUser(combatant_id = 2, user_id = 2).put()
        models.CombatantUser(combatant_id = 2, user_id = 3).put()

        # Fill context.joined array
        contract_id = 1
        combatants_info = chalis.fetch_combatants_info(contract_id)

        # Get all users associated with each distinct combatant 
        for combatant in combatants_info:
            users_info = chalis.fetch_users_info(combatant.combatant_id)
            users_array = []

            # Fill the array of users associated with combatant.name with their google emails
            for user_info in users_info:
                users_array.append(user_info.google_username+"@gmail.com") 

            # Put the combatant-users object into context's array of these objects
            context['joined'][combatant.name] = users_array

        # Check that it worked as expected
        self.assertEqual("liam@gmail.com", context['joined']["Liam"][0])
        self.assertTrue("jeff@gmail.com", context['joined']["Best Team"])
        self.assertTrue("bob2@gmail.com", context['joined']["Best Team"])

def test_main():
    test_support.run_unittest(HomePageTest, CreateChallengeTest, FetchChallengeInfoTest, InviteTest)

if __name__ == '__main__':
    test_main()
