import webapp2
from google.appengine.api import users
from google.appengine.api import mail
import jinja2
import os
import json
import logging
import datetime
import time
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
            challenge3_name = Contract.query(Contract.contract_id == desc[2][0]).get().challenge_name

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


# Renders details page where a challenge's info is seen and can be edited 
class ChallengePage(webapp2.RequestHandler):
    def get(self, short_name):
        new_status = self.request.get("new")
        edit_status = self.request.get("edit")
                
        should_be_here = check_user_auth(short_name)
        if not should_be_here and new_status == 0:
            self.redirect('/')  #TODO: just have them see w/o editing

        name = obj_type = length = unit = start = con_id = stakes_ids = stakes_info = checkin = None
        # Get the relevant model's info
        if not new_status:
            name, obj_type, length, unit, start, con_id, stakes_ids = fetch_contract_info(short_name)
        
            # Get stakes objects
            stakes_info = fetch_stakes_info(stakes_ids)

            # Get checkin action string
            if obj_type == "highest-occurrence":
                objective = GeneralObjective.query(GeneralObjective.contract_id == con_id).get()
                if objective:
                    checkin = objective.objective_name

        # New challenges are by default highest-occurrence and start today
        else:
            obj_type = "highest-occurrence"
            start = datetime.date.today()
            name = "New"

        # Convert start's DateProperty format to something usable in template if it is set
        if start:
            start = {'month': start.month, 'day': start.day, 'year': start.year}

        # Create context for page
        context = {'description':name, 'objective':obj_type, 'length':length, 'time_units':unit, 'start_date':start, 'stakes':stakes_info, 'checkin_action':checkin}

        # Render the page in context and display it as either editable or not
        if not new_status and not edit_status:
            if obj_type == 'location':
                geo_obj = GeolocationObjective.query(GeolocationObjective.contract_id == con_id).get()
                context['location'] = str(geo_obj.checkin_loc)
            challenge_page = jinja_environment.get_template("pages/nonedit-details.html")
        else:
            challenge_page = jinja_environment.get_template("pages/details.html")

        self.response.out.write(challenge_page.render(context))


# Doesn't render a page, just where info is sent when any parameter is changed on the ChallengePage
class EditChallenge(webapp2.RequestHandler):
    def post(self, short_name):
        # Arguments object will contain any fields that are changing, along with their new values
        args_object = {}
        args_sent = self.request.arguments() 
        stakes = ["","","",""] 
        for arg in args_sent:
            if arg[:-1] == 'stakes':
                stakes[int(arg[-1:])-1] = self.request.get(arg)
            else:
                args_object[arg] = self.request.get(arg)
        args_object["stakes"] = stakes

        update_challenge(short_name, args_object)


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
    
        # Register the given email as one that belongs to an invitee for future reference
        add_desired_user(short_name, email)

        # Send an email to that person with the link to the join page
        email_invite(short_name, email)


# Page arrived at when accepting an invitation to join a challenge. User chooses combatant name/team
class JoinPage(webapp2.RequestHandler):
    def get(self, short_name):
        user = users.get_current_user()
        if not user: 
            self.redirect(users.create_login_url(self.request.uri))

        # Check that the user that logged in is someone who was invited to the challenge, or already in
        invited = check_user_desired(short_name, user.email())

        # Add the user to the competition if they were invited
        if invited:
            # Grab the username from their email
            username = grab_username(user.email())

            # Create a new user model if this username is not in the db already
            user_id = create_or_fetch_user(username)
            
            # Combatant details
            combatant_id = create_combatant(username) 
                    
            # Link combatant and user
            link_combatant_user(combatant_id, user_id)

            # Get the contract id
            con_id = Contract.query(Contract.short_name == short_name).get().contract_id

            # Link contract and combatant
            link_contract_combatant(con_id, combatant_id)


        # Tell them to get an invite if they weren't invited
        context = {"invited": invited}
        not_invited_page = jinja_environment.get_template("pages/joining.html")
        self.response.out.write(not_invited_page.render(context))


# Render the form for checking in to the indicated challenge. Form different depending on objective
class CheckinPage(webapp2.RequestHandler):
    def get(self, short_name):
        should_be_here = check_user_auth(short_name)
        if not should_be_here:
            self.redirect('/')
        
        # Get this challenge's contract for use in finding objective info
        contract = Contract.query(Contract.short_name == short_name).get()
        # And the combatant info for use in finding progress
        combatant = fetch_current_combatant(short_name)
  
        # Switch on objective type
        if contract.objective_type == 'location':
            geo_obj = GeolocationObjective.query(GeolocationObjective.contract_id == contract.contract_id).get()
            # Find last checkin date for context
            last_checkin = last_checkin_date(geo_obj.geo_objective_id, combatant.combatant_id)
            if last_checkin:
                last_checkin = time.mktime(last_checkin.timetuple())
            else:
                last_checkin = ""

            # Create context and render page
            context = {'id': geo_obj.geo_objective_id, 'location': str(geo_obj.checkin_loc), 'radius': geo_obj.checkin_radius, 'placename': geo_obj.loc_name, 'last_checkin': last_checkin}
            geo_checkin_page = jinja_environment.get_template("pages/geo-checkin.html")
            self.response.out.write(geo_checkin_page.render(context))

        elif contract.objective_type == 'highest-occurrence':
            gen_obj = GeneralObjective.query(GeneralObjective.contract_id == contract.contract_id).get()
            # Find last checkin date for context
            last_checkin = last_checkin_date(gen_obj.gen_objective_id, combatant.combatant_id)
            if last_checkin:
                last_checkin = time.mktime(last_checkin.timetuple())
            else:
                last_checkin = ""

            # Create context and render page            
            context = {'id': gen_obj.gen_objective_id, 'objective': gen_obj.objective_name, 'last_checkin': last_checkin}
            gen_checkin_page = jinja_environment.get_template("pages/gen-checkin.html")
            self.response.out.write(gen_checkin_page.render(context))

        elif contract.objective_type == 'reddit':
            return 1

        elif contract.objective_type == None:
            self.redirect('/'+short_name+'/details')


# Carries out the action of incrementing the current user's combatant's progress in this objective
class CheckinAction(webapp2.RequestHandler):
    def post(self, short_name):
        obj_id = int(self.request.get('objective_id'))
        combatant = fetch_current_combatant(short_name)
        update_progress(obj_id, combatant.combatant_id)

        # Update all their positions so when we ask later they'll all be up to date        
        update_positions(obj_id, short_name, combatant.combatant_id)


# Renders some kind of infographic about the current state of the challenge
class StatusPage(webapp2.RequestHandler):
    def get(self, short_name):
        # Grab the contract info, and combatants involved
        name, obj_type, length, unit, start, con_id, stakes_ids = fetch_contract_info(short_name)
        combatants = fetch_combatants_info(con_id) 

        # Get each combatant's checkin count and add that info to the combatant object
        template_coms = fetch_combatant_counts(con_id, obj_type, combatants)
                
        # Create context and render page
        # Find how many 10ths into the challenge we are, so we can draw a bar that many spans long
        fraction_over_10 = num_tenths_in(start, unit, length)

        # Make end date object
        multiplier = 1
        if unit == "weeks":
            multiplier = 7
        if unit == "months":
            multiplier = 30
        days_in_challenge = length*multiplier

        end = start + datetime.timedelta(days=days_in_challenge)
        end = {'month': end.month, 'day': end.day}  

        # Make a nice start object
        start = {'month': start.month, 'day': start.day}

        context = {'name': name, 'start': start, 'spans_complete': fraction_over_10, 'combatants': template_coms, 'end': end}
        status_page = jinja_environment.get_template("pages/status.html")
        self.response.out.write(status_page.render(context))


# Renders the current user's user page so they can see all the challenges they're currently in
class UserPage(webapp2.RequestHandler):
    def get(self):
        # Grab a list of challenges current user's in plus combatant name
        challenges, username = fetch_current_challenges_list()

        context = {'challenges': challenges, 'username': username}
        user_page = jinja_environment.get_template("pages/user.html")
        self.response.out.write(user_page.render(context))


############### Unit-testable Functions Used By Handlers ##############
def fetch_current_challenges_list():
    user = users.get_current_user()
    if not user:
        self.redirect('/')
    username = grab_username(user.email())
    user_data = User.query(User.google_username == username).get()
    if not user_data:
        return []
    
    # Get all CombatantUser objects for this user
    com_users = CombatantUser.query(CombatantUser.user_id == user_data.user_id).fetch(20)

    # Get all ContractCombatant objects for this user
    con_coms = []
    for com_user in com_users:
        con_coms += ContractCombatant.query(ContractCombatant.combatant_id == com_user.combatant_id).fetch(20)
    
    # Create array containing challenge names, links, combatant name in that challenge, and position
    challenges = []
    for con_com in con_coms:
        con = Contract.query(Contract.contract_id == con_com.contract_id).get()
        challenge_name = con.challenge_name

        # Link to details page if competition is in future
        if not con.start_date or con.start_date > datetime.date.today():
            link = '/'+con.short_name+'/details'
        # Otherwise link to status page
        else:
            link = '/'+con.short_name+'/status'

        com_name = Combatant.query(Combatant.combatant_id == con_com.combatant_id).get().name

        position = con_com.position

        challenges.append({'challenge_name': challenge_name, 'link': link, 'com_name': com_name, 'position': position})

    return challenges, username


def fetch_combatant_counts(con_id, obj_type, combatants):
    # Get objective_id in order to later get progress info
    if obj_type == 'location':
        obj_id = GeolocationObjective.query(GeolocationObjective.contract_id == con_id).get().geo_objective_id
    elif obj_type == 'highest-occurrence':
        obj_id = GeneralObjective.query(GeneralObjective.contract_id == con_id).get().gen_objective_id

    template_coms = []
    for com in combatants:
        curr_id = com.combatant_id
        #Default count of 0
        count = 0
        progress = GeneralProgress.query(GeneralProgress.objective_id == obj_id, GeneralProgress.combatant_id == curr_id).get()
        if progress:
            count = progress.checkin_count
        curr_com = {}
        curr_com["name"] = com.name
        curr_com["count"] = count
        curr_com["com_id"] = com.combatant_id
        curr_com["position"] = ContractCombatant.query(ContractCombatant.contract_id == con_id, ContractCombatant.combatant_id == com.combatant_id).get().position
        template_coms.append(curr_com)
    return template_coms


def num_tenths_in(start_date, unit, length):
    diff = datetime.date.today() - start_date
    days_in = diff.days
    multiplier = 1
    if unit == "weeks":
        multiplier = 7
    if unit == "months":
        multiplier = 30
    days_in_challenge = length*multiplier
    percent_done = float(days_in)/days_in_challenge
    fraction_over_10 = int(percent_done*10)
    return fraction_over_10


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
    stakes = Stakes.query(Stakes.stakes_id.IN(stakes_ids)).fetch(4)

    stakes_info = {}
    for stake in stakes:
        stakes_info[stake.position] = stake.stakes_desc

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
    if not contract.stakes_id:
        curr_stakes = [0,0,0,0]
    else:
        curr_stakes = contract.stakes_id
    stakes_ids = enter_stakes(args_obj["stakes"], curr_stakes)
    contract.stakes_id = stakes_ids
    
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
        # Get current highest GeolocationObjective id
        top_objective = GeolocationObjective.query().order(-GeolocationObjective.geo_objective_id).get()
        if top_objective:
            new_id = top_objective.geo_objective_id + 1
        else:
            new_id = 1

        # Make new GeolocationObjective model
        GeolocationObjective(checkin_loc = ndb.GeoPt(args_obj["checkin-loc"]), checkin_radius = int(args_obj["radius"]), loc_name = args_obj["checkin-loc-name"], geo_objective_id = new_id, contract_id = contract.contract_id).put()


def enter_stakes(stakes_descs, existing_ids):
    stakes_id = get_new_stakes_id()    

    # Put any first place description in db and get its stakes_id in array
    if existing_ids[0] == 0 and stakes_descs[0] != "":
        Stakes(stakes_id = stakes_id, position = "first", stakes_desc = stakes_descs[0]).put()
        existing_ids[0] = stakes_id
        stakes_id += 1
    # If one exists and the new one is different, replace the text
    elif existing_ids[0] != 0:
        first_stake = Stakes.query(Stakes.stakes_id == existing_ids[0]).get()
        if first_stake.stakes_desc != stakes_descs[0]:
            first_stake.stakes_desc = stakes_descs[0]

    # Second place
    if existing_ids[1] == 0 and stakes_descs[1] != "":
        Stakes(stakes_id = stakes_id, position = "second", stakes_desc = stakes_descs[1]).put()
        existing_ids[1] = stakes_id
        stakes_id += 1
    elif existing_ids[1] != 0:
        sec_stake = Stakes.query(Stakes.stakes_id == existing_ids[1]).get()
        if sec_stake.stakes_desc != stakes_descs[1]:
            sec_stake.stakes_desc = stakes_descs[1]


    # Second to last place
    if existing_ids[2] == 0 and stakes_descs[2] != "":
        Stakes(stakes_id = stakes_id, position = "second to last", stakes_desc = stakes_descs[2]).put()
        existing_ids[2] = stakes_id
        stakes_id += 1
    elif existing_ids[2] != 0:
        sec_last_stake = Stakes.query(Stakes.stakes_id == existing_ids[2]).get()
        if sec_last_stake.stakes_desc != stakes_descs[2]:
            sec_last_stake.stakes_desc = stakes_descs[2]


    # Last place
    if existing_ids[3] == 0 and stakes_descs[3] != "":
        Stakes(stakes_id = stakes_id, position = "last", stakes_desc = stakes_descs[3]).put()
        existing_ids[3] = stakes_id
        stakes_id += 1
    elif existing_ids[3] != 0:
        last_stake = Stakes.query(Stakes.stakes_id == existing_ids[3]).get()
        if last_stake.stakes_desc != stakes_descs[3]:
            last_stake.stakes_desc = stakes_descs[3]

    return existing_ids


def get_new_stakes_id():
    top_stake = Stakes.query().order(-Stakes.stakes_id).get()
    if top_stake:
        return top_stake.stakes_id + 1
    else:
        return 1


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


# Updates an existing progress object or creates a new one if none exists
def update_progress(obj_id, com_id):
    # Find that progress entry
    progress = GeneralProgress.query(GeneralProgress.objective_id == obj_id, GeneralProgress.combatant_id == com_id).get()

    if progress:
        # Increment its checkin_count, set current time, and put it back
        progress.checkin_count += 1
        progress.last_checkin = datetime.datetime.now()
        progress.put()
    else:
        new_progress = GeneralProgress(objective_id = obj_id, combatant_id = com_id, checkin_count = 1, last_checkin = datetime.datetime.now()).put()


# Need to know most recently checked-in combatant's com_id because it won't be reflected in db yet
def update_positions(obj_id, short_name, com_id):
    name, obj_type, length, unit, start, con_id, stakes_ids = fetch_contract_info(short_name)

    combatants = fetch_combatants_info(con_id)

    com_counts = fetch_combatant_counts(con_id, obj_type, combatants)

    # Make it reflect that com_id's count is one higher than com_counts says
    for com_count in com_counts:
        if com_count['com_id'] == com_id:
            com_count['count'] += 1

    # Sort the com_counts objects in terms of decreasing count
    com_counts.sort(key=lambda x: x['count'], reverse=True)

    # Set the position of each combatant in their ContractCombatant model
    position = 1
    for com_count in com_counts:
        con_com = ContractCombatant.query(ContractCombatant.contract_id == con_id, ContractCombatant.combatant_id == com_count['com_id']).get()
        con_com.position = position
        con_com.put()
        position += 1


def fetch_current_position(short_name):
    # Get the current combatant's info if they're logged in
    com = fetch_current_combatant(short_name)
    # Get contract info for con_id
    name, obj_type, length, unit, start, con_id, stakes_ids = fetch_contract_info(short_name)

    con_com = ContractCombatant.query(ContractCombatant.contract_id == con_id, ContractCombatant.combatant_id == com.combatant_id).get()
    return con_com.position
    

# Given a combatant and objective, find the last time they checked in to that objective
def last_checkin_date(obj_id, com_id):
    # Find the progress entry if any
    progress = GeneralProgress.query(GeneralProgress.objective_id == obj_id, GeneralProgress.combatant_id == com_id).get()

    if progress:
        return progress.last_checkin

    else:
        return None


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


def check_user_desired(short_name, email):
    contract = Contract.query(Contract.short_name == short_name).get()
    des_users = DesiredUsers.query(DesiredUsers.contract_id == contract.contract_id).get()

    if not des_users:
        return False

    user_list = des_users.users
    if email not in user_list:
        return False

    return True


def email_invite(short_name, email):
    user = users.get_current_user()
    sender = user.email()
    subject = "Step up to the challenge on Chalis!"
    body = """
Hi there friend! 

I would like you to join my challenge on chalis.
Just go to this link, log in with this email, and join the competition!
%s
""" % ("http://chalisfinal.appspot.com/"+short_name+"/join")

    mail.send_mail(sender=sender, to=email, subject=subject, body=body)



app = webapp2.WSGIApplication([('/', HomePage), ('/new', CreateChallenge), ('/(.*)/edit', EditChallenge), ('/(.*)/details', ChallengePage), ('/(.*)/invite', InvitePage), ('/(.*)/send-invite', SendInvite), ('/(.*)/join', JoinPage), ('/(.*)/status', StatusPage), ('/(.*)/checkin', CheckinPage), ('/(.*)/do-checkin', CheckinAction), ('/user', UserPage)], debug=True)
