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
        obj_type = "location"
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

        self.assertEqual("Gets free lunch", stakes_info['first'])
        self.assertEqual("Buys lunch", stakes_info['last'])
        

class InviteTest(unittest.TestCase):
    def setUp(self):
        logging.info('In Invite setUp()')

    def test_invite_context_creation(self):
        # Will build up a context object in the same way InvitePage does
        context = {'joined' : []}
        
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
            context['joined'].append({'combatant': combatant.name, 'users': users_array})

        # Check that it worked as expected
        liam_combatant = {'combatant': "Liam", 'users': ["liam@gmail.com"]}
        team_combatant = {'combatant': "Best Team", 'users': ["jeff@gmail.com", "bob2@gmail.com"]}
        self.assertTrue(liam_combatant in context['joined'])
        self.assertTrue(team_combatant in context['joined'])


class StatusPageTests(unittest.TestCase):
    def setUp(self):
        logging.info('In StatusPage setUp()')

    def test_fetch_combatant_counts(self):
        # Add a contract with two users, each having checked in a few times
        models.Contract(contract_id=1, short_name="test", objective_type="location").put()
        models.GeolocationObjective(geo_objective_id=1, contract_id=1).put()
        models.User(user_id=1, google_username="test1").put()
        models.User(user_id=2, google_username="test2").put()
        com1 = models.Combatant(combatant_id=1, name="1")
        com2 = models.Combatant(combatant_id=2, name="2")
        com1.put()
        com2.put()
        models.CombatantUser(combatant_id=1, user_id=1).put()
        models.CombatantUser(combatant_id=2, user_id=2).put()
        models.ContractCombatant(contract_id=1, combatant_id=1).put()
        models.ContractCombatant(contract_id=1, combatant_id=2).put()
        models.GeneralProgress(objective_id=1, combatant_id=1, checkin_count=3).put()
        models.GeneralProgress(objective_id=1, combatant_id=2, checkin_count=4).put()

        com_counts = chalis.fetch_combatant_counts(1, "location", [com1, com2])
        
        # 1 should have 3, 2 should have 4
        self.assertTrue({'name': "1", 'count': 3, 'com_id': 1, 'position': None} in com_counts)
        self.assertTrue({'name': "2", 'count': 4, 'com_id': 2, 'position': None} in com_counts)


class CheckinPageTests(unittest.TestCase):
    def setUp(self):
        logging.info('In CheckinPage setUp()')

    def test_update_positions(self):
        # Add a contract with three users, each having checked some times
        models.Contract(contract_id=1, short_name="test", objective_type="location").put()
        models.GeolocationObjective(geo_objective_id=1, contract_id=1).put()
        models.User(user_id=1, google_username="test1").put()
        models.User(user_id=2, google_username="test2").put()
        models.User(user_id=3, google_username="test3").put()
        com1 = models.Combatant(combatant_id=1, name="1").put()
        com2 = models.Combatant(combatant_id=2, name="2").put()
        com3 = models.Combatant(combatant_id=3, name="3").put()
        models.CombatantUser(combatant_id=1, user_id=1).put()
        models.CombatantUser(combatant_id=2, user_id=2).put()
        models.CombatantUser(combatant_id=3, user_id=3).put()
        con_com1 = models.ContractCombatant(contract_id=1, combatant_id=1)
        con_com2 = models.ContractCombatant(contract_id=1, combatant_id=2)
        con_com3 = models.ContractCombatant(contract_id=1, combatant_id=3)
        con_com1.put()
        con_com2.put()
        con_com3.put()
        models.GeneralProgress(objective_id=1, combatant_id=1, checkin_count=3).put()
        models.GeneralProgress(objective_id=1, combatant_id=2, checkin_count=4).put()
        models.GeneralProgress(objective_id=1, combatant_id=3).put()
        
        # com_id is 0 because there is no combatant whose most recent checkin won't be in db
        chalis.update_positions(1, "test", 0)

        self.assertEqual(1, con_com2.position)
        self.assertEqual(2, con_com1.position)
        self.assertEqual(3, con_com3.position)

class RandomTests(unittest.TestCase):
    def setUp(self):
        logging.info('In RandomTests setUp()')

    def test_check_user_auth(self):
        # Add a contract with a user of liamhession
        models.Contract(contract_id = 1, short_name = "test").put()
        models.User(user_id = 1, google_username = "liamhession").put()
        models.Combatant(combatant_id = 1, name = "Liam").put()
        models.ContractCombatant(contract_id = 1, combatant_id = 1).put()
        models.CombatantUser(combatant_id = 1, user_id = 1).put()

        self.assertTrue(chalis.check_user_auth("test"))


    def test_add_desired_user(self):
        return 1

def test_main():
    test_support.run_unittest(HomePageTest, CreateChallengeTest, FetchChallengeInfoTest, InviteTest, RandomTests)

if __name__ == '__main__':
    test_main()
