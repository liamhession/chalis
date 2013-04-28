import webapp2
from google.appengine.api import users
import jinja2
import os
import json
import logging

from models import Contract
from models import GeolocationObjective
from models import Stakes
from models import ContractCombatant
from models import GeolocationProgress
from models import Combatant
from models import CombatantUser
from models import User

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

############## Handlers ################
# Show input box for starting new challenge, as well as most popular challenges.
# Send text put into new challenge field to the EditingChallenge handler, redirect to NewChallenge 
#  Eventually, do NLP on input of bar on enter
class HomePage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user: 
            self.redirect(users.create_login_url(self.request.uri))
            
        context = {} #TODO
        home = jinja_environment.get_template("pages/home.html")
        self.response.out.write(home.render(context))


# Create the relevant database items for a new challenge, given only the description so far.
# Redirect to the challenge details page for the newly short-named challenge
class CreateChallenge(webapp2.RequestHandler):
    def post(self):
        # Description is posted, user should be logged in...
        new_name = self.request.get('description')
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))

        # Create a new user model if this username is not in the db already
        user_id = create_or_fetch_user(user) 
        
        # Combatant details
        combatant_id = create_combatant(user) 
                
        # Link combatant and user
        link_combatant_user(combatant_id, user_id)

        # Create the challenge with just 3 fields filled at beginning
        new_id, short_name = find_short_name(new_name)
        create_challenge(new_id, short_name, new_name)

        # Link contract and combatant
        link_contract_combatant(new_id, combatant_id)

        self.redirect('/'+short_name+'/details')


# Doesn't render a page, just where info is sent when any parameter is changed on the ChallengePage
class EditChallenge(webapp2.RequestHandler):
    def post(self, short_name):
        # Arguments object will contain any fields that are changing, along with their new values
        args_object = {}
        args_sent = self.request.arguments()  
        for arg in args_sent:
            args_object[arg] = self.request.get(arg)

        update_challenge(short_name, args_object)


# Renders details page where a challenge's info is seen and can be edited 
class ChallengePage(webapp2.RequestHandler):
    def get(self, short_name):
        # Get the relevant model's info
        name, obj_type, length, unit, start, con_id, stakes_ids = fetch_contract_info(short_name)
        
        # Get stakes objects
        stakes_info = fetch_stakes_info(stakes_ids)

        context = {'description':name, 'objective':obj_type, 'length':length, 'time_units':unit, 'start_date':start, 'stakes':stakes_info}

        challenge_page = jinja_environment.get_template("details.html")
        self.response.out.write(challenge_page.render(context))


# Renders invite page where a user adds other people to the challenge
class InvitePage(webapp2.RequestHandler):
    def get(self, short_name):
        self.response.out.write(short_name)

############### Unit-testable Functions Used By Handlers ##############
def find_short_name(new_name): 
    # Create a shortened version of this name to appear in URLs
    # Get ride of spaces and the word "challenge" first
    short_name = new_name.replace(" ", "")
    short_name = short_name.replace("Challenge", "")
    short_name = short_name.replace("challenge", "")

    if len(short_name) < 25:
        short_name = short_name[0:15]
    # For quite long names we'll start short version on second word
    else:
        start_short = new_name.find(' ')
        short_name = short_name[start_short:start_short+15]

    # Confirm this particular short name is not already present in the db
    already_exists = True
    appended_number = 1
    while already_exists:
        already_exists = Contract.query(Contract.short_name == short_name).get()
        if already_exists:
            appendage = str(appended_number)
            if short_name[-len(appendage):] == appendage:
                short_name = short_name[-len(appendage):] + str(appended_number+1)
                appended_number += 1

    # Get the next contract_id in order for the new entry
    curr_top = Contract.query().order(-Contract.contract_id).get()
    if curr_top:
        new_id = curr_top.contract_id + 1
    else:
        new_id = 1

    return new_id, short_name


def create_challenge(new_id, short_name, full_name):
    # Create the new entry
    new_contract = Contract(contract_id = new_id, challenge_name = full_name, short_name = short_name)
    new_contract.put()


def fetch_stakes_info(stakes_ids):
    # Get all stakes objects, then create an array of dictionaries
    stakes = Stakes.query(Stakes.stakes_id.IN(stakes_ids)).fetch(20)
    stakes_info = []
    for stake in stakes:
        stakes_info.append({stake.position:stake.stakes_desc})

    return stakes_info
   
   
def fetch_contract_info(short_name):
    # Get relevant contract model
    contract = Contract.query(Contract.short_name == short_name).get()

    # Will send blanks for the elements of retrieved Contract that are not yet filled in
    name = contract.challenge_name
    obj_type = contract.objective_type
    length = contract.time_period
    unit = contract.time_unit
    start = contract.start_date
    
    # Get more aspects of challenge using ids to search other Models
    con_id = contract.contract_id
    stakes_ids = contract.stakes_id

    return name, obj_type, length, unit, start, con_id, stakes_ids


def update_challenge(short_name, args_obj):
    # Get the contract to be updateds
    contract = Contract.query(Contract.short_name == short_name).get()

    # Update all fields represented in args_obj
    for k, v in args_obj:
        if k == "description":
            contract.challenge_name = v
        elif k == "objective":
            contract.objective_type = v
        elif k == "":
            print "woch"


def create_or_fetch_user(username):
    # Look for a user with that username in existence
    user = User.query(User.google_username == username).get()

    if user:
        return user.user_id

    else:
        top_id_res = User.query().order(-User.user_id).get()
        if top_id_res:
            uid = top_id_res.user_id + 1
        else:
            uid = 1

        new_user = User(user_id = uid,
                        google_username = username)
        new_user.put()
        return uid


def create_combatant(name):
    # Get the new highest combatant_id
    top_id_res = Combatant.query().order(-Combatant.combatant_id).get()
    if top_id_res:
        cid = top_id_res.combatant_id + 1
    else:
        cid = 1

    # Make the combatant and return id used
    new_combatant = Combatant(combatant_id = cid,
                              name = name)
    new_combatant.put()

    return cid


def link_combatant_user(combatant_id, user_id):
    # Create new CombatantUser entry and put it
    new_cu = CombatantUser(combatant_id = combatant_id, user_id = user_id)
    new_cu.put()


def link_contract_combatant(contract_id, combatant_id):
    # Create new ContractCombatant entry, no position specified, and put it
    new_cc = ContractCombatant(contract_id = contract_id, combatant_id = combatant_id)
    new_cc.put()


app = webapp2.WSGIApplication([('/', HomePage), ('/new', CreateChallenge), ('/(.*)/edit', EditChallenge), ('/(.*)/details', ChallengePage), ('/(.*)/invite', InvitePage)], debug=True)##, ('/(.*)/join', JoinPage), ('/(.*)/status', StatusPage), ('/(.*)/checkin', CheckinPage)], debug=True)
