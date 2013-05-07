import webapp2
from google.appengine.api import users
from google.appengine.api import mail
import jinja2
import os
import json
import logging
import datetime
from google.appengine.ext import ndb

from models import Contract
from models import GeolocationObjective
from models import GeneralObjective
from models import Stakes
from models import ContractCombatant
from models import GeneralProgress
from models import Combatant
from models import CombatantUser
from models import User
from models import DesiredUsers

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
            
        # Create a dictionary of the number of users in each challenge
        contract_users = {}
        all_contract_combatants = ContractCombatant.query().fetch(100)
        for con_com in all_contract_combatants:
            users_num = CombatantUser.query(CombatantUser.combatant_id == con_com.combatant_id).count()
            if con_com.contract_id in contract_users:
                contract_users[con_com.contract_id] += users_num
            else:
                contract_users[con_com.contract_id] = users_num
        
        # Find the 3 contract ids with the most users involved
        desc = sorted(contract_users.iteritems(), key=lambda x:x[1], reverse=True) 

        challenge1_name = challenge2_name = challenge3_name = ""       
        if len(desc) > 0:
            challenge1_name = Contract.query(Contract.contract_id == desc[0][0]).get().challenge_name
        if len(desc) > 1:
            challenge2_name = Contract.query(Contract.contract_id == desc[1][0]).get().challenge_name
        if len(desc) > 2:
            challenge3_name = Contract.query(Contract.contract_id == desc[0][0]).get().challenge_name

        context = {'exampleText': "Who runs the most miles in a month?", 'topChallenge1': challenge1_name, 'topChallenge2': challenge2_name, 'topChallenge3': challenge3_name}
        home = jinja_environment.get_template("pages/frontpage.html")
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

        # Grab the username from their email
        username = grab_username(user.email())

        # Create a new user model if this username is not in the db already
        user_id = create_or_fetch_user(username)
        
        # Combatant details
        combatant_id = create_combatant(username) 
                
        # Link combatant and user
        link_combatant_user(combatant_id, user_id)

        # Create the challenge with just 3 fields filled at beginning
        new_id, short_name = find_short_name(new_name)
        create_challenge(new_id, short_name, new_name)

        # Link contract and combatant
        link_contract_combatant(new_id, combatant_id)

        self.redirect('/'+short_name+'/details?new=1')


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
        new_challenge = self.request.get("new")
        
        should_be_here = check_user_auth(short_name)
        if not should_be_here and not new_challenge:
            self.redirect('/')  #TODO: just have them see w/o editing

        name = obj_type = length = unit = start = con_id = stakes_ids = stakes_info = None
        # Get the relevant model's info
        if not new_challenge:
            name, obj_type, length, unit, start, con_id, stakes_ids = fetch_contract_info(short_name)
        
            # Get stakes objects
            stakes_info = fetch_stakes_info(stakes_ids)

        # Convert start's DateProperty format to something usable in template if it is set
        if start:
            start = {'month': start.month, 'day': start.day, 'year': start.year}

        context = {'description':name, 'objective':obj_type, 'length':length, 'time_units':unit, 'start_date':start, 'stakes':stakes_info}

        # Render the page in context and display it
        challenge_page = jinja_environment.get_template("pages/details.html")
        self.response.out.write(challenge_page.render(context))


# Renders invite page where a user adds other people to the challenge
class InvitePage(webapp2.RequestHandler):
    def get(self, short_name):
        should_be_here = check_user_auth(short_name)
        if not should_be_here:
            self.redirect('/')

        # Build up context that only contains an array of combatant_name : [user1, user2] objects
        context = {'joined' : []}

        # Show a list of already-joined combatants with their usernames
        contract_id = Contract.query(Contract.short_name == short_name).get().contract_id
        combatants_info = fetch_combatants_info(contract_id)

        # Get all users associated with each distinct combatant 
        for combatant in combatants_info:
            users_info = fetch_users_info(combatant.combatant_id)
            users_array = []

            # Fill the array of users associated with combatant.name with their google emails
            for user_info in users_info:
                users_array.append(user_info.google_username+"@gmail.com") 

            # Put the combatant-users object into context's array of these objects
            context['joined'].append({'combatant': combatant.name, 'users': users_array})

        # Render the page in context and display it
        invite_page = jinja_environment.get_template("pages/invite.html")
        self.response.out.write(invite_page.render(context))


# Handles new user email entered on InvitePage.
class SendInvite(webapp2.RequestHandler):
    def post(self, short_name):
        email = self.request.get('email')
        challenge_desc = self.request.get('description')        
    
        # Register the given email as one that belongs to an invitee for future reference
        add_desired_user(short_name, email)

        # Send an email to that person with the link to the join page
        email_invite(short_name, email, challenge_desc)


# Page arrived at when accepting an invitation to join a challenge. User chooses combatant name/team
class JoinPage(webapp2.RequestHandler):
    def get(self, short_name):
        user = users.get_current_user()
        if not user: 
            self.redirect(users.create_login_url(self.request.uri))

        # Check that the user that logged in is someone who was invited to the challenge, or already in
        invited = check_user_desired(short_name, user.email())

        # Tell them to get an invite if they weren't invited
        if invited == "not":
            not_invited_page = jinja_environment.get_template("pages/no-invite.html")
            self.response.out.write(not_invited_page.render())
        
        elif invited == "already":
            already_joined_page = jinja_environment.get_template("pages/already-joined.html")
            self.response.out.write(already_joined_page.render())
        
        elif invited == "yes":
            # Render page to ask user what combatant they are
            context = {}
            joined_page = jinja_environment.get_template("pages/joined.html")
            self.response.out.write(joined_page.render(context))


# Render the form for checking in to the indicated challenge. Form different depending on objective
class CheckinPage(webapp2.RequestHandler):
    def get(self, short_name):
        should_be_here = check_user_auth(short_name)
        if not should_be_here:
            self.redirect('/')
        
        contract = Contract.query(Contract.short_name == short_name).get()
        logging.info(contract)
        if contract.objective_type == 'location':
            geo_obj = GeolocationObjective.query(GeolocationObjective.contract_id == contract.contract_id).get()
            context = {'id' : geo_obj.geo_objective_id, 'location' : str(geo_obj.checkin_loc), 'radius' : geo_obj.checkin_radius, 'placename' : geo_obj.loc_name}
            geo_checkin_page = jinja_environment.get_template("pages/geo-checkin.html")
            self.response.out.write(geo_checkin_page.render(context))

        elif contract.objective_type == 'highest-occurrence':
            gen_obj = GeneralObjective.query(GeneralObjective.contract_id == contract.contract_id).get()
            context = {'id' : gen_obj.gen_objective_id, 'objective' : gen_obj.objective_name}
            gen_checkin_page = jinja_environment.get_template("pages/gen-checkin.html")
            self.response.out.write(gen_checkin_page.render(context))

        elif contract.objective_type == 'reddit':
            return 1

        elif contract.objective_type == None:
            self.redirect('/'+short_name+'/details')


# Carries out the action of incrementing the current user's combatant's progress in this objective
class CheckinAction(webapp2.RequestHandler):
    def post(self, short_name):
        obj_id = self.request.get('objective_id')
        combatant = fetch_current_combatant(short_name)
        update_progress(obj_id, combatant.combatant_id)


# Renders some kind of infographic about the current state of the challenge
class StatusPage(webapp2.RequestHandler):
    def get(self, short_name):
        self.response.out.write("Liam wins")

############### Unit-testable Functions Used By Handlers ##############
def grab_username(email):
    amp_idx = email.find("@")
    return email[:amp_idx]

# Returns whether or not the current user can see info related to challenge "short_name"
def check_user_auth(short_name):
    user = users.get_current_user()
    # Can't see it if they're not even logged in!
    if not user: 
        return False

    # Find all the users associated with this challenge
    contract = Contract.query(Contract.short_name == short_name).get()
    if not contract:
        logging.info("Couldnt find that one")
        return False

    contract_id = contract.contract_id
    combatants_info = fetch_combatants_info(contract_id)

    users_array = []
    # Get all users associated with each distinct combatant 
    for combatant in combatants_info:
        users_info = fetch_users_info(combatant.combatant_id)

        # Fill the array of users associated with combatant.name with their google emails
        for user_info in users_info:
            users_array.append(str(user_info.google_username))

    # If the current user's id is in users_array then they're good to go 
    return str(user) in users_array



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
    if not stakes_ids:
        return []

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
    #contract.challenge_name = args_obj["description"]
    contract.objective_type = str(args_obj["objective"])
    contract.time_unit = str(args_obj["unit"])
    contract.time_period = int(args_obj["length"])
    contract.start_date = datetime.date(int(args_obj["year"]), int(args_obj["month"]), int(args_obj["day"]))
    
    contract.put()
    
    # Enter in Objective models
    if contract.objective_type == "highest-occurrence":
        # Get current highest GeneralObjective id
        top_objective = GeneralObjective.query().order(-GeneralObjective.gen_objective_id).get()
        if top_objective:
            new_id = top_objective.gen_objective_id + 1
        else:
            new_id = 1

        # Make new GeneralObjective model
        GeneralObjective(objective_name = str(args_obj["objective-name"]), contract_id = contract.contract_id, gen_objective_id = new_id).put()

    elif contract.objective_type == "location":
        logging.info("location")
        # Get current highest GeolocationObjective id
        top_objective = GeolocationObjective.query().order(-GeolocationObjective.geo_objective_id).get()
        if top_objective:
            new_id = top_objective.geo_objective_id + 1
        else:
            new_id = 1

        # Make new GeolocationObjective model
        GeolocationObjective(checkin_loc = ndb.GeoPt(args_obj["checkin-loc"]), checkin_radius = args_obj["radius"], loc_name = args_obj["checkin-loc-name"], geo_objective_id = new_id, contract_id = contract.contract_id).put()


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


def fetch_combatants_info(contract_id):
    # Grab all the ContractCombatant objects with this contract_id
    con_coms = ContractCombatant.query(ContractCombatant.contract_id == contract_id).fetch(20)

    # Create Combatant models that are represented by con_coms
    combatants = []
    for con_com in con_coms:
        com = Combatant.query(Combatant.combatant_id == con_com.combatant_id).get()
        combatants.append(com)

    return combatants


def fetch_users_info(combatant_id):
    # Grab all the CombatantUser objects with this combatant_id
    com_users = CombatantUser.query(CombatantUser.combatant_id == combatant_id).fetch(20)

    # Create User models that are represented by com_users
    users = []
    for com_user in com_users:
        user = User.query(User.user_id == com_user.user_id).get()
        users.append(user)

    return users


def fetch_current_combatant(short_name):
    # Find what user is logged in 
    user = users.get_current_user()
    if not user:
        self.redirect('/')
   
    # Find all the users associated with this challenge
    contract_id = Contract.query(Contract.short_name == short_name).get().contract_id
    combatants_info = fetch_combatants_info(contract_id)

    # Get all users associated with each distinct combatant 
    for combatant in combatants_info:
        users_info = fetch_users_info(combatant.combatant_id)

        # Return current combatant if user is found
        for user_info in users_info:
            if user_info.google_username == str(user):
                return combatant


def update_progress(obj_id, com_id):
    # Find that progress entry
    progress = GeneralProgress.query(GeneralProgress.objective_id == obj_id, GeneralProgress.combatant_id == com_id).get()
    # Increment its checkin_count, set current time, and put it back
    progress.checkin_count += 1
    progress.last_checkin = datetime.date.today()
    progress.put()


def add_desired_user(short_name, email):
    # Find appropriate contract_id, then get desired users list
    contract = Contract.query(Contract.short_name == short_name).get()
    players = DesiredUsers.query(DesiredUsers.contract_id == contract.contract_id).get()

    # Create new DesiredUsers object if none
    if not players:
        DesiredUsers(contract_id = contract.contract_id, users = [email]).put()

    # Otherwise update list of users that have been invited, then put it back in db
    else:
        players.users.append(email)
        players.put()


def email_invite(short_name, email, desc):
    user = users.get_current_user()
    sender = user.email()
    subject = "Step up to the challenge on Chalis!"
    body = """
Hi there friend! 

I would like you to join my challenge on chalis.com. To take me on in:
%s

Just go to this link, log in with this email, and join the competition!
%s
""" % (desc, "http://chalis.com/"+short_name+"/join")

    mail.send_mail(sender=sender, to=email, subject=subject, body=body)



app = webapp2.WSGIApplication([('/', HomePage), ('/new', CreateChallenge), ('/(.*)/edit', EditChallenge), ('/(.*)/details', ChallengePage), ('/(.*)/invite', InvitePage), ('/(.*)/send-invite', SendInvite), ('/(.*)/join', JoinPage), ('/(.*)/status', StatusPage), ('/(.*)/checkin', CheckinPage), ('/(.*)/do-checkin', CheckinAction)], debug=True)
