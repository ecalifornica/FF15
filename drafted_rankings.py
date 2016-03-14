import pprint
import re

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


def api_get_players(week):
    '''
    '''
    col_name = 'week_{}'.format(week)
    # db.col_name.drop()
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
    Takes a team league position and a week.
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
            # 20 is the code for benched players.
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


def draft_board():
    # TODO: Sort by league_position explicitly
    r = list(db.sunday_challenge_teams.find())
    
    for x in range(18):
        draft_row = []
        for i in range(8):
            #draft_row.append(r[i]['drafted players'][x]['name'][:9])
            total_score = 0
            player_id = r[i]['drafted players'][x]['_id']
            for week in range(1, 17):
                total_score += player_score(player_id, week)
            #total_score = r[i]['drafted players'][x]['_id']
            draft_row.append('{:6.2f}'.format(total_score))
        print '----------------------------------------------------------------------------------------'
        print '{}{}'.format('draft pos {:2}  || '.format(x + 1), ' | '.join(draft_row))
        '''
            for team in r:
                if team['draft position'] == i:
                    for player in team['drafted players']:
                        print team['owner'], player
        '''

    



def create_multiplier_table():
    '''
    '''
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
    '''
    Takes an ID and returns a name.
    '''
    result = db.player_name_and_id.find_one({'_id': str(player_id)})
    return result['name']


def player_id_from_name(player_name=None):
    '''
    Needs to be rewritten.
    '''
    results = db.player_name_and_id.find({'name': re.compile(player_name,
                                                             re.IGNORECASE)})
    dbresult = list(results)
    if len(dbresult) == 0:
        print('No matches, calling player details API endpoint')
        player_id = raw_input('Player ID: ')
        payload['playerId'] = player_id
        r = requests.get(base_url + '/player/details', params=payload)
        player_name = (r.json()['games']['102015']['players']
                               [str(player_id)]['name'])
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
    This needs to be broken up.
    '''
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
            team = {'owner': owner,
                    'draft position': draft_position,
                    'drafted players': []}

        for position in range(roster_position, 19):
            player_query = raw_input('Partial player name, case insensitive: ')
            player_choice = player_id_from_name(player_query)
            print('You selected {}, draft position {}.'
                  .format(player_choice['name'], position))
            team['drafted players'].append(player_choice)
    except:
        print team['owner']
        for player in team['drafted players']:
            print player
    finally:
        if raw_input('Insert into database? ') in ['y', 'yes']:
            try:
                print(db['sunday_challenge_teams']
                      .replace_one({'_id': team['_id']}, team, upsert=True))
            except:
                print(db['sunday_challenge_teams'].insert(team))


def test_team_scores(team=None, week=None):
    '''
    Returns a team's scores for each week of the season.
    '''
    scores = {}
    barf = db.sunday_challenge_teams.find()
    for team in barf:
        # TODO: Convert unicode to float
        scores[int(team['league_position'])] = team['week_points']

    return scores


def db_create_team_week_points():
    '''
    Pull each team's total points by week and add to team doc.
    '''

    for team in range(1, 9):
        week_points = {}
        for week in range(1, 17):
            r = (db.matchups.find()[week - 1]['games']['102015']['leagues'][LEAGUE_ID]['teams'][str(team)]['stats']['week']['2015'][str(week)]['pts'])
            week_points[str(week)] = r
            # print team, week, r
        print db.sunday_challenge_teams.find_one_and_update({'league_position': team}, {'$set': {'week_points': week_points}})
        # Check
        # print db.sunday_challenge_teams.find_one({'league_position': team})


def db_add_league_position():
    '''
    Add internal league id number to team docs.
    '''
    team_owners_ids = {
        'kasey': 1,
        'robert': 2,
        'dan': 3,
        'shawn': 4,
        'nate': 5,
        'mcclune': 6,
        'nikzad': 7,
        'tocci': 8}
    for owner, league_position in team_owners_ids.iteritems():
        print db.sunday_challenge_teams.find_one_and_update({'owner': owner}, {'$set': {'league_position': league_position}})


def print_score_deltas():
    #print(db.collection_names())
    total_delta = 0
    nfl_scores = test_team_scores()
    for week in range(1, 17):
        print('Week: {}'.format(week))
        for team in range(1, 9):
            team_score = team_score_for_week(team=team, week=week)
            #nfl_score = test_team_score(week=week, team=team)
            # Hack
            nfl_score = float(nfl_scores[team][str(week)])
            score_delta = round(team_score - nfl_score, 2)
            total_delta += abs(score_delta)
            print('Team {} score: {}, NFL: {}, delta: {}'.format(team,
                  team_score,
                  nfl_score,
                  score_delta))
    print('Total season delta: {}'.format(total_delta))


def main():
    draft_board()

if __name__ == '__main__':
    main()
