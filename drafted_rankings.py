import pprint

from pymongo import MongoClient
import requests

from config import (APP_KEY,
                    AUTH_TOKEN,
                    LEAGUE_ID)

mc = MongoClient()
db = mc.ff15

base_url = 'http://api.fantasy.nfl.com/v2'
payload = {}
payload['appKey'] = APP_KEY
payload['authToken'] = AUTH_TOKEN
payload['leagueId'] = LEAGUE_ID


def get_players(week):
    col_name = 'week_{}'.format(week)
    db.col_name.drop()
    r = requests.get(base_url + '/players/weekstats?season=2015&week={}'
                     .format(week))
    players = r.json()['games']['102015']['players']
    print('downloaded players', len(players))
    for k, v in players.iteritems():
        player_doc = {'_id': k, 'stats': v['stats']}
        col = db[col_name]
        col.insert_one(player_doc)
        print('db count', db[week].count())


def team_score_for_week(team=None, week=None):
    '''attempt to get total score for one team for one week
    would be a good opportunity to do TDD
    '''
    team_score = 0
    db_roster = (db.matchups.find()[week - 1]['games']['102015']['leagues']
                                   [LEAGUE_ID]['teams'][str(team)]['rosters']
                                   [str(week)])
    my_roster = []
    # Active players for the week
    for player_category in db_roster.itervalues():
        for player in player_category:
            player_id = player['playerId']
            roster_slot = int(player['rosterSlotId'])
            if roster_slot is not 20:
                my_roster.append(int(player_id))
    for player_id_number in my_roster:
        # player_name = player_names(player_id_number)
        points = player_score(player_id=player_id_number, week=week)
        # print('{1}: {0}'.format(player_name, points))
        team_score += points
    return team_score


def player_score(player_id=None, week=None):
    """
    returns a player's score for a given week
    """
    # TODO: Keep this in memory
    r = db.player_stats.find()
    try:
        stats = (r[week - 1]['games']['102015']['players'][str(player_id)]
                  ['stats']['week']['2015'][str(week)])
        score = 0
        for k, v in stats.iteritems():
            if k != 'pts':
                r = stat_multiplier(int(k), float(v))
                score += r
        #print round(score, 2)
        return round(score, 2)
        #return score
    except:
        # player_name = player_names(player_id)
        # print('Missing player: {} for week {}'.format(player_name, week))
        return 0


def stat_multiplier(stat_type, stat_value):
    '''
    '''
    multiplier = db.stat_multipliers.find_one({'_id': stat_type})
    if multiplier:
        result = stat_value * multiplier['multiplier']
        return result
    else:
        return 0


def create_multiplier_table():
    print db.stat_multipliers.drop()
    r = db.league_settings.find()
    multipliers = (r[0]['games']['102015']['leagues'][LEAGUE_ID]['settings']
                    ['scoring']['stats'])
    r = db.stat_lookup_table.find_one()
    stat_names = r['games']['102015']['stats']
    #print(db.collection_names())
    #db['stat_multipliers'].insert(score_multipliers)
    for stat in stat_names.iteritems():
        try:
            barf = stat[0]
            multiplier = multipliers[barf]
            doc = {'_id': int(stat[0]),
                   'name': stat[1]['name'],
                   'multiplier': float(multiplier)}
            if doc['_id'] in [14, 21]:
                doc['multiplier'] = doc['multiplier'] * .01
            if doc['_id'] == 5:
                doc['multiplier'] = .04
            print(doc)
            print db['stat_multipliers'].insert(doc)
        except:
            pass


def create_player_names_collection(player_id=None):
    '''one call to api v1'''

    dbresult = db.apiv1_player_names.find()
    result = list(dbresult)
    # print db.player_name_and_id.drop()
    for i in result[0]['players']:
        player_info = {'_id': i['id'], 'name': i['name']}
        db['player_name_and_id'].insert(player_info)
    return None


def player_names(player_id=None):
    result = db.player_name_and_id.find_one({'_id': str(player_id)})
    return result['name']

'''
results = db.player_name_and_id.find()
for i in results:
    print i
'''

def player_id_from_name(player_name=None):
    import re
    results = db.player_name_and_id.find({'name': re.compile(player_name, re.IGNORECASE)})
    dbresult = list(results)
    if len(dbresult) == 0:
        print('No matches, calling player details API endpoint')
        player_id = raw_input('Player ID: ')
        payload['playerId'] = player_id
        r = requests.get(base_url + '/player/details', params=payload)
        player_name = r.json()['games']['102015']['players'][str(player_id)]['name']
        return {u'_id': player_id, u'name': player_name}
    elif len(dbresult) > 20:
        print('More than 20 matches')
        raise
    for player in enumerate(dbresult, start=1):
        print player[0], player[1]['name'], player[1]
    user_input = raw_input('Choose player: ')
    player_choice = dbresult[int(user_input) - 1]
    return player_choice


def draft_order():
    '''
    Hack
    '''
    #db.sunday_challenge_teams.drop()
    previous_teams = list(db.sunday_challenge_teams.find())
    pprint.pprint(previous_teams)
    try:
        for prev_team in previous_teams:
            print prev_team['owner'], prev_team['draft position']
            for player in enumerate(prev_team['drafted players']):
                print player[0] + 1, player[1]
        draft_position = int(raw_input('Draft position: '))
        roster_position = int(raw_input('Start at roster position: '))
        try:
            team = previous_teams[draft_position - 1]
        except:
            owner = raw_input('Owner: ')
            team = {'owner': owner, 'draft position': draft_position, 'drafted players': []}

        for position in range(roster_position, 19):
            player_query = raw_input('Partial player name, case insensitive: ')
            player_choice = player_id_from_name(player_query)
            print 'You selected {}, draft position {}.'.format(player_choice['name'], position)
            team['drafted players'].append(player_choice)
    except:
        print team['owner']
        for player in team['drafted players']:
            print player
    finally:
        if raw_input('Insert into database? ') in ['y', 'yes']:
            try:
                print(db['sunday_challenge_teams'].replace_one({'_id': team['_id']}, team, upsert=True))
            except:
                print(db['sunday_challenge_teams'].insert(team))
    

class FFApi(object):
    '''
    '''
    def __init__(self):
        pass

    def get_player_names():
        r = requests.get('http://api.fantasy.nfl.com/v1/players/stats')
        print(db['apiv1_player_names'].insert(r.json()))

    def player_stats():
        '''players/weekstats'''
        payload['season'] = '2015'
        for week in range(1, 17):
            payload['week'] = week
            r = requests.get(base_url + '/players/weekstats', params=payload)
            print(db.player_stats.insert(r.json()))

    def league_transactions():
        payload['count'] = '1000'
        for feed_type in ['transactions', 'lmChanges']:
            payload['feedType'] = feed_type
            r = requests.get(base_url + '/league/feed', params=payload)
            db.barf.insert(r.json())

    def stat_lookup_table():
        '''game/stats'''
        r = requests.get(base_url + '/game/stats', params=payload)
        print(db.stat_lookup_table.insert(r.json()))

    def game_settings():
        '''?'''
        r = requests.get(base_url + '/game/settings', params=payload)
        db.game_settings.insert(r.json())

    def roster_slots():
        endpoint = '/game/rosterslots'
        r = requests.get(base_url + endpoint, params=payload)
        print(db.roster_slots.insert(r.json()))

    def ff_api(endpoint, payload, col_name):
        r = requests.get(base_url + endpoint, params=payload)
        print(db[col_name].insert(r.json()))

    def get_player_details(self, player_id):
        payload['playerId'] = player_id
        self.ff_api('/player/details', payload, 'player_details')

    def league_settings():
        url = base_url + '/league/settings'
        r = requests.get(url, params=payload)
        db.league_settings.insert(r.json())

    def matchups():
        '''league/matchups'''
        for week in range(1, 17):
            payload['week'] = week
            r = requests.get(base_url + '/league/matchups', params=payload)
            pprint.pprint(r.json()['games'])
            print(db.matchups.insert(r.json()))


def test_team_score(team=None, week=None):
    scores = {2:
              {1: 143.34,
               2: 114.24,
               3: 142.68,
               4: 146.54,
               5: 121.52,
               6: 123.02,
               7: 115.90,
               8: 136.80,
               9: 150.36,
               10: 126.68,
               11: 106.96,
               12: 147.12,
               13: 156.84,
               14: 156.86,
               15: 164.90,
               16: 139.44}
              }
    return scores[team][week]


def main():
    print(db.collection_names())
    
    for week in range(1, 17):
        team_score = team_score_for_week(team=2, week=week)
        nfl_score = test_team_score(week=week, team=2)
        # Hack
        score_delta = round(team_score - nfl_score, 2)
        print('Week {} score: {}, NFL: {}, delta: {}'.format(week,
              team_score,
              nfl_score,
              score_delta))


if __name__ == '__main__':
    main()
