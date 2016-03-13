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


class FFApi(object):
    '''
    '''
    def __init__(self):
        pass

    def ff_api(endpoint, payload, col_name):
        r = requests.get(base_url + endpoint, params=payload)
        print(db[col_name].insert(r.json()))

    def get_player_names():
        r = requests.get('http://api.fantasy.nfl.com/v1/players/stats')
        print(db['apiv1_player_names'].insert(r.json()))

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


def main():
    pass

if __name__ == '__main__':
    main()
