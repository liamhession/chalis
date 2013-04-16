import webapp2
import jinja2
import os
import json
from google.appengine.ext import ndb

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

############## Database Models ################
class Contract(ndb.Model):
    contract_id = IntegerProperty()
    challenge_name = StringProperty()
    objective_type = StringProperty(choices=['geolocation', 'reddit', 'general'])
    time_period = IntegerProperty()
    time_unit = StringProperty(choices=['days', 'weeks', 'months'])
    start_date = DateProperty()
    stakes_id = IntegerProperty(repeat=True)
    
class GeolocationObjective(ndb.Model):
    geo_objective_id = IntegerProperty()
    contract_id = IntegerProperty()
    checkin_loc = GeoPtProperty()
    checkin_radius = IntegerProperty()
    loc_name = StringProperty()

class Stakes(ndb.Model):
    stakes_id = IntegerProperty()
    position = StringProperty(choices=['first', 'second', 'second to last', 'last'])
    stakes_desc = StringProperty()

class ContractCombatant(ndb.Model):
    contract_id = IntegerProperty()
    combatant_id = IntegerProperty()
    position = IntegerProperty()

class GeolocationProgress(ndb.Model):
    geo_objective_id = IntegerProperty()
    combatant_id = IntegerProperty()
    checkin_count = IntegerProperty()
    last_checkin = DateTimeProperty()

class Combatant(ndb.Model):
    combatant_id = IntegerProperty()
    name = StringProperty()
    challenges_won = IntegerProperty()
    is_in_a_challenge = BooleanProperty()

class CombatantUser(ndb.Model):
    combatant_id = IntegerProperty()
    user_id = IntegerProperty()

class User(ndb.Model):
    user_id = IntegerProperty()
    name = StringProperty()
    email = StringProperty()
    phone_number = IntegerProperty()
    challenges_won = IntegerProperty()



############## Handlers ################
# Show input box for starting new challenge, as well as most popular challenges. Do NLP on input
#   of bar on enter, send that to the EditingChallenge handler which will redirect to NewChallenge
class HomePage(webapp2.RequestHandler):
    def get(self):
        context = {} #TODO
        home = jinja_environment.get_template("home.html")
        self.response.out.write(home.render(context))


#This handler doesn't render a page, this is just where a new challenge's initial info is sent and 
#   also where info is sent when any parameter is changed on the ChallengePage
class EditingChallenge(webapp2.RequestHandler):
    def post(self):
        

class ChallengePage(webapp2.RequestHandler):
    def post(self, shortname):
        challenge_desc = self.request.get('description')
#TODO: run this description through some basic NLP parsing to populate context
        context = {'objective' : 'geolocation'}
        new_challenge = jinja_environment.get_template("new.html")
        self.response.out.write(new_challenge.render(context))


app = webapp2.WSGIApplication([('/', HomePage), ('/challenge-edit', EditingChallenge), ('/(.*)/details', ChallengePage), ('/(.*)/invite', InvitePage), ('/(.*)/join', JoinPage), ('/(.*)/status', StatusPage), ('/(.*)/checkin', CheckinPage)], debug=True)
