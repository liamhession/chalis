from google.appengine.ext import ndb

############## Database Models ################
class Contract(ndb.Model):
    contract_id = ndb.IntegerProperty()
    challenge_name = ndb.StringProperty()
    short_name = ndb.StringProperty()
    objective_type = ndb.StringProperty(choices=['geolocation', 'reddit', 'general'])
    time_period = ndb.IntegerProperty()
    time_unit = ndb.StringProperty(choices=['days', 'weeks', 'months'])
    start_date = ndb.DateProperty()
    stakes_id = ndb.IntegerProperty(repeated=True)
    
class GeolocationObjective(ndb.Model):
    geo_objective_id = ndb.IntegerProperty()
    contract_id = ndb.IntegerProperty()
    checkin_loc = ndb.GeoPtProperty()
    checkin_radius = ndb.IntegerProperty()
    loc_name = ndb.StringProperty()

class Stakes(ndb.Model):
    stakes_id = ndb.IntegerProperty()
    position = ndb.StringProperty(choices=['first', 'second', 'second to last', 'last'])
    stakes_desc = ndb.StringProperty()

class ContractCombatant(ndb.Model):
    contract_id = ndb.IntegerProperty()
    combatant_id = ndb.IntegerProperty()
    position = ndb.IntegerProperty()

class GeolocationProgress(ndb.Model):
    geo_objective_id = ndb.IntegerProperty()
    combatant_id = ndb.IntegerProperty()
    checkin_count = ndb.IntegerProperty()
    last_checkin = ndb.DateTimeProperty()

class Combatant(ndb.Model):
    combatant_id = ndb.IntegerProperty()
    name = ndb.StringProperty()
    challenges_won = ndb.IntegerProperty(default=0)
#    is_in_a_challenge = ndb.BooleanProperty(default=False)

class CombatantUser(ndb.Model):
    combatant_id = ndb.IntegerProperty()
    user_id = ndb.IntegerProperty()

class User(ndb.Model):
    user_id = ndb.IntegerProperty()
    google_username = ndb.StringProperty()
    phone_number = ndb.IntegerProperty()
    challenges_won = ndb.IntegerProperty(default=0)

