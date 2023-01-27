# Script to generate UltRank tiers.

# Requirements:
#  geopy installed: pip install geopy
#  start.gg API key stored in a file 'smashgg.key'
#  From the UltRank TTS Scraping Sheet:
#   ultrank_players.csv
#   ultrank_regions.csv
#   ultrank_invitational.csv

from geopy.geocoders import Nominatim
import csv 
import requests
import re
import sys 
import time

SMASH_GG_ENDPOINT = 'https://api.smash.gg/gql/alpha'

ggkeyfile = open('smashgg.key')
ggkey = ggkeyfile.read()
ggkeyfile.close()
ggheader = {"Authorization": "Bearer " + ggkey}

startgg_slug_regex = re.compile(r'tournament\/[a-z0-9\-]+\/event\/[a-z0-9\-]+')

class PotentialMatch:
    def __init__(self, tag, id_, points, note):
        self.tag = tag
        self.id_ = id_ 
        self.points = points 
        self.note = note 

    def __str__(self):
        return '{} (id {}) - {} points [{}]'.format(self.tag, self.id_, self.points, self.note)

class CountedValue:
    # Stores a counted player value with additional data.

    def __init__(self, player_value, total_points, alt_tag):
        self.player_value = player_value
        self.total_points = total_points
        self.alt_tag = alt_tag

class PlayerValue:
    # Stores scores for players.

    def __init__(self, tag, id_, points=0, note='', invitational=0):
        self.tag = tag
        self.id_ = id_ 
        self.points = points 
        self.note = note
        self.invitational = invitational

    def __str__(self):
        return '{} (id {}) - {} (+{}) points [{}]'.format(self.tag, self.id_, self.points, self.invitational, self.note)

class RegionValue:
    # Stores region multipliers.

    def __init__(self, country_code='', iso2='', county='', jp_postal='', multiplier=1, note=''):
        self.country_code = country_code
        self.iso2 = iso2
        self.county = county 
        self.jp_postal = jp_postal 
        self.multiplier = multiplier 
        self.note = note 

    def match(self, address):
        # Compares an address derived from Nominatim module to the stored region.
        # Higher number = larger match.

        if self.country_code == '':
            return 1

        match = 0

        if address.get('country_code', '') == self.country_code:
            match += 2

            if self.iso2 == '':
                match += 1
            elif address.get('ISO3166-2-lvl4', '') == self.iso2:
                match += 2

                if self.county == '':
                    match += 1
                elif address.get('county', '') == self.county:
                    match += 2

            if self.country_code == 'jp':
                jp_postal = address.get('postcode', 'XX')[0:2]

                if self.jp_postal == '':
                    match += 1
                elif jp_postal == self.jp_postal:
                    match += 2

        return match

    def __eq__(self, other):
        if not isinstance(other, RegionValue):
            return False

        return self.country_code == other.country_code and self.iso2 == other.iso2 and self.county == other.county and self.jp_postal == other.jp_postal and self.multiplier == other.multiplier


    def __hash__(self):
        return hash((self.country_code, self.iso2, self.county, self.jp_postal, self.multiplier))

    def __str__(self):
        ret = ''
        if self.country_code != '':
            ret += '{}'.format(self.country_code)

            if self.iso2 != '':
                ret += '/{}'.format(self.iso2)

                if self.county != '':
                    ret += '/'.format(self.county)
            
            if self.jp_postal != '':
                ret += '/JP Postal {}'.format(self.jp_postal)

        else:
            ret = 'All Other Regions'
        ret += ' [{}] - x{}'.format(self.note, self.multiplier)

        return ret


class Entrant:
    # Wrapper class to store player ids and tags
    def __init__(self, id_num, name):
        self.id_num = str(id_num)
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, Entrant):
            return False
        return self.id_num == other.id_num and self.name == other.name

    def __hash__(self):
        return hash((self.id_num, self.name))
        

def send_request(query, variables):
    # Sends a request to the startgg server.
    progress = False

    tries = 0

    response_json = {}

    while not progress:
        json_payload = {
            "query": query,
            "variables": variables
        }
        try:
            response = requests.post(SMASH_GG_ENDPOINT, json=json_payload, headers=ggheader)

            if response.status_code == 200:
                progress = True
                response_json = response.json()
            else:
                tries += 1
                if response.status_code == 429:
                    print(f'try {tries}: rate limit exceeded... sleeping then trying again... ', end='', flush=True)
                elif response.status_code == 502:
                    print(f'try {tries}: 502 bad gateway... sleeping then trying again... ', end='', flush=True)
                else:
                    print(f'try {tries}: received non-200 response... sleeping then trying again... ', end='', flush=True)
                    print(response.text)
                    print(response.status_code)
                
                time.sleep(60)
                print('retrying')
            

        except Exception as e:
            print(f'try {tries}: requests failure... sleeping then trying again... ', end='', flush=True)
            print(e)
            time.sleep(60)
            tries += 1
            print('retrying')

    return response_json

def entrants_query(event_slug, page_num=1, per_page=200):
    query = '''query getEntrants($eventSlug: String!, $pageNum: Int!, $perPage: Int!) {
        event(slug: $eventSlug) {
            entrants(
                query: {
                    page: $pageNum,
                    perPage: $perPage
                }
            ){
                pageInfo {
                    totalPages
                }
                nodes {
                    participants {
                        player {
                            gamerTag
                            id
                        }
                    }
                }
            }
        }
    }'''
    variables = '''{{
        "eventSlug": "{}",
        "pageNum": {},
        "perPage": {}
    }}'''.format(event_slug, page_num, per_page)
    return query, variables

def sets_query(event_slug, page_num=1, per_page=50, phases=None):
    # Generates a query to retrieve sets from an event.

    query = '''query getSets($eventSlug: String!, $pageNum: Int!, $perPage: Int!, $phases: [ID]!) {
  event(slug: $eventSlug) {
    sets(page: $pageNum, perPage: $perPage, filters:{ state: [3], phaseIds: $phases}) {
      pageInfo {
        page
        totalPages
      }
      nodes {
        winnerId
        slots {
          entrant {
            id
            name
            participants {
              player {
                gamerTag
                id
              }
            }
          }
          standing {
            stats {
              score {
                value
              }
            }
          }
        }
      }
    }
  }
}'''
    variables = '''{{
        "eventSlug": "{}",
        "pageNum": {},
        "perPage": {},
        "phases": {}
    }}'''.format(event_slug, page_num, per_page, f'{phases if phases is not None else "[]"}')
    return query, variables

def phase_list_query(event_slug):
    # Generates a query to retrieve a list of phases from an event.

    query = '''query getPhases($eventSlug: String!) {
  event(slug: $eventSlug) {
    phases {
      id
      name
      phaseOrder
      state
    }
  }
}'''
    variables = '''{{
        "eventSlug": "{}"
    }}'''.format(event_slug)

    return query, variables

def sets_phase_query(event_slug, phase, page_num=1, per_page=50):
    # Generates a query to retrieve a list of sets in a particular phase from an event.

    query = '''query getSets($eventSlug: String!, $pageNum: Int!, $perPage: Int!, $phase: ID!) {
  event(slug: $eventSlug) {
    sets(page: $pageNum, perPage: $perPage, filters: {phaseIds: [$phase]}) {
      pageInfo {
        totalPages
      }
      nodes {
        wPlacement
      }
    }
  }
}'''
    variables = '''{{
        "eventSlug": "{}",
        "pageNum": {},
        "perPage": {},
        "phase": {}
    }}'''.format(event_slug, page_num, per_page, phase)

    return query, variables

def phase_seeds_query(phase_id, page_num=1, per_page=300):
    # Generates a query to retrieve a list of seeds in a particular phase from an event.

    query = '''query getPhaseSeeds($id: ID!, $pageNum: Int!, $perPage: Int!) {
  phase(id: $id) {
    seeds(query: {page: $pageNum, perPage: $perPage}) {
      pageInfo {
        totalPages
      }
      nodes {
        progressionSource {
          originPhase {
            id
          }
        }
      }
    }
  }
}'''
    variables = '''{{
        "id": "{}",
        "pageNum": {},
        "perPage": {}
    }}'''.format(phase_id, page_num, per_page)

    return query, variables

def location_query(event_slug):
    # Generates a query to retrieve the location (latitude/longitude) of an event.

    query = '''query getSets($eventSlug: String!) {
  event(slug: $eventSlug) {
    tournament {
      lat
      lng
    }
  }
}'''
    variables = '''{{
        "eventSlug": "{}"
    }}'''.format(event_slug)

    return query, variables

def check_phase_completed(event_slug):
    # Checks to see if any phases are completed.

    # Get ordered list of phases
    query, variables = phase_list_query(event_slug)
    resp = send_request(query, variables)

    try:
        for phase in resp['data']['event']['phases']:
            if phase.get('state', '') == 'COMPLETED':
                return True
    except Exception as e:
        print(e)
        print(resp)
        sys.exit()

    return False

def collect_phases(event_slug):
    # Collects phases that are part of the main tournament. (Hopefully) excludes amateur brackets.

    # Get ordered list of phases
    query, variables = phase_list_query(event_slug)
    resp = send_request(query, variables)

    try:
        phases = resp['data']['event']['phases']
        phases.sort(key=lambda phase: phase['phaseOrder'])
    except Exception as e:
        print(e)
        print(resp)
        sys.exit()

    # Find the first phase that reaches a conclusion; 99% of the time this is the actual final phase.
    top_phase = None 

    for phase in phases:
        page = 1

        while True:
            query, variables = sets_phase_query(event_slug, phase['id'], page_num=page)
            resp = send_request(query, variables)

            try:
                for set_data in resp['data']['event']['sets']['nodes']:
                    if set_data['wPlacement'] == 1:
                        top_phase = phase['id']
                        break
            except Exception as e:
                print(e)
                print(resp)
                sys.exit()

            if top_phase != None or page >= resp['data']['event']['sets']['pageInfo']['totalPages']:
                break
            page += 1

        if top_phase != None:
            break

    if top_phase == None:
        return []

    # Iterate through phases using the phase seeds, until there are no more preceding phases.
    phases_to_check = [top_phase] # If the auto-phase getter gets the wrong phase, put the correct phase in this array.
    phases_checked = []

    while len(phases_to_check) > 0:
        page = 1

        phase = phases_to_check.pop()
        phases_checked.append(phase)

        while True:
            query, variables = phase_seeds_query(phase, page_num=1)
            resp = send_request(query, variables)

            try:
                for seed_data in resp['data']['phase']['seeds']['nodes']:
                    if seed_data['progressionSource'] == None:
                        continue 
                    phase_id = seed_data['progressionSource']['originPhase']['id']

                    if phase_id not in phases_to_check and phase_id not in phases_checked:
                        phases_to_check.append(phase_id)

            except Exception as e:
                print(e)
                print(resp)
                sys.exit()

            if page >= resp['data']['phase']['seeds']['pageInfo']['totalPages']:
                break
            page += 1

    phase_names = []
    for phase in phases_checked:
        for phase_data in phases:
            if phase == phase_data['id']:
                phase_names.append(phase_data['name'])

    print('using following phases: {}'.format(phase_names))

    return phases_checked

def get_entrants(event_slug):
    page = 1
    participants = set()

    while True:
        query, variables = entrants_query(event_slug, page_num=page)
        resp = send_request(query, variables)

        for entrant in resp['data']['event']['entrants']['nodes']:
            try:
                player_data = Entrant(entrant['participants'][0]['player']['id'], entrant['participants'][0]['player']['gamerTag'])

                participants.add(player_data)
            except Exception as e:
                print(e)
                print(resp)
                sys.exit()


        if page >= resp['data']['event']['entrants']['pageInfo']['totalPages']:
            break
        page += 1

    return participants

def get_dqs(event_slug, phases=None):
    # Retrieves DQs of an event.

    page = 1
    dq_list = {}
    participants = set()

    while True:
        # print(page)
        query, variables = sets_query(event_slug, page_num=page, phases=phases)
        resp = send_request(query, variables)

        try:
            for set_data in resp['data']['event']['sets']['nodes']:
                if set_data['winnerId'] == None:
                    continue

                # print(set_data)

                loser = 1 if set_data['winnerId'] == set_data['slots'][0]['entrant']['id'] else 0

                player_data_0 = Entrant(set_data['slots'][0]['entrant']['participants'][0]['player']['id'], set_data['slots'][0]['entrant']['participants'][0]['player']['gamerTag'])
                player_data_1 = Entrant(set_data['slots'][1]['entrant']['participants'][0]['player']['id'], set_data['slots'][1]['entrant']['participants'][0]['player']['gamerTag'])
                if set_data['slots'][0]['standing'] == None and set_data['slots'][1]['standing'] == None:
                    player_id = set_data['slots'][loser]['entrant']['participants'][0]['player']['id']

                    if player_id in dq_list.keys():
                        dq_list[player_id][1] += 1
                    else:
                        dq_list[player_id] = [set_data['slots'][loser]['entrant']['participants'][0]['player']['gamerTag'], 1]
                    continue

                game_count = set_data['slots'][loser]['standing']['stats']['score']['value']

                if game_count == -1:
                    player_id = set_data['slots'][loser]['entrant']['participants'][0]['player']['id']

                    if player_id in dq_list.keys():
                        dq_list[player_id][1] += 1
                    else:
                        dq_list[player_id] = [set_data['slots'][loser]['entrant']['participants'][0]['player']['gamerTag'], 1] 
                else:
                    # not a dq, record both players as participants
                    participants.add(player_data_0)
                    participants.add(player_data_1)
        except Exception as e:
            print(e)
            print(resp)
            sys.exit()

        if page >= resp['data']['event']['sets']['pageInfo']['totalPages']:
            break
        page += 1

    return dq_list, participants

def read_players():
    players = {}
    tags = set()

    with open('ultrank_players.csv', newline='') as players_file:
        reader = csv.DictReader(players_file)

        for row in reader:
            id_ = row['Start.gg Num ID']
            if id_ == '':
                id_ = row['Player']

            tag = row['Player'].strip()
            if tag == '':
                continue

            points = int(row['Points'])

            if id_ not in players:
                player_value = PlayerValue(tag, id_, points, row['Note'])
                players[id_] = player_value
            else:
                player_value = players[id_]

                if player_value.points < points:
                    player_value.points = points
                player_value.note += ", " + row['Note']

            tags.add(tag)

    with open('ultrank_invitational.csv', newline='') as invit_file:
        reader = csv.DictReader(invit_file)

        for row in reader:
            id_ = row['Num']
            if id_ == '':
                id_ = row['Player']

            if id_ in players:
                player_value = players[id_]
                player_value.invitational = int(row['Additional Points'])

    return players, tags

def read_regions():
    regions = set()

    with open('ultrank_regions.csv', newline='') as regions_file:
        reader = csv.DictReader(regions_file)

        for row in reader:
            region_value = RegionValue(country_code=row['country_code'], iso2=row['ISO3166-2'], county=row['county'], jp_postal=row['jp-postal-code'], multiplier=int(row['Multiplier']), note=row['Note'])
            regions.add(region_value)

    return regions


if __name__ == '__main__':
    event_slug = input('input event slug: ')
    if not startgg_slug_regex.fullmatch(event_slug):
        print('Invalid slug! Must be of form "tournament/.../event/..."')
        sys.exit()

    is_invitational = input('is this an invitational? (y/n) ')
    is_invitational = is_invitational.upper() == 'Y' or is_invitational.upper() == 'YES'

    scored_players, scored_tags = read_players()
    region_mults = read_regions()

    # Check if the event has progressed enough to detect DQs. (Unused)

    # event_progressed = check_phase_completed(event_slug)

    # if event_progressed:
    #     phases = str(collect_phases(event_slug))

    #     dq_list, participants = get_dqs(event_slug, phases)

    #     total_dqs = 0

    #     participant_ids = [part.id_num for part in participants]
    #     for player_id, dqs in dq_list.items():
    #         if player_id not in participant_ids:
    #             total_dqs += 1
    # else:
    #     participants = get_entrants(event_slug)
    #     total_dqs = -1

    participants = get_entrants(event_slug)
    total_dqs = -1 # Placeholder Value

    geo = Nominatim(user_agent='ultrank')

    query, variables = location_query(event_slug)
    resp = send_request(query, variables)

    try:
        lat = resp['data']['event']['tournament']['lat']
        lng = resp['data']['event']['tournament']['lng']
    except Exception as e:
        print(e)
        print(resp)
        sys.exit()

    address = geo.reverse('{}, {}'.format(lat, lng)).raw['address']

    # add things up
    total_score = 0

    best_match = 0
    best_region = None

    for region in region_mults:
        match = region.match(address)
        if match > best_match:
            best_region = region
            best_match = match 

    total_score += len(participants) * best_region.multiplier

    participants_string = '{} - {} DQs = {}'.format(len(participants) + total_dqs, total_dqs, len(participants)) if total_dqs != -1 else '{}'.format(len(participants))

    print('Entrants: {} x {} [{}] = {}'.format(participants_string, best_region.multiplier, best_region.note, len(participants) * best_region.multiplier))

    print()
    print('Top Player Points: ')

    valued_participants = []
    potential_matches = []

    for participant in participants:
        if participant.id_num in scored_players:
            player_value = scored_players[participant.id_num]

            score = player_value.points + (player_value.invitational if is_invitational else 0)

            total_score += score

            valued_participants.append(CountedValue(player_value, score, participant.name))
        elif participant.name in scored_tags:
            for player_value in scored_players.values():
                if participant.name.upper() == player_value.tag.upper():
                    score = player_value.points + (player_value.invitational if is_invitational else 0)
                    potential_matches.append(PotentialMatch(participant.name, participant.id_num, score, player_value.note))

    # Sort for readability
    valued_participants.sort(reverse=True, key=lambda p: p.total_points)
    potential_matches.sort(key=lambda m: m.tag)

    for participant in valued_participants:
        full_tag = participant.alt_tag + (' (aka {})'.format(participant.player_value.tag) if participant.alt_tag != participant.player_value.tag else '')
        print('  {} - {} points [{}]'.format(full_tag, participant.total_points, participant.player_value.note))

    print()
    print('Total Score: {}'.format(total_score))

    print()
    print('-----')
    print('Potentially Mismatched Players')
    for match in potential_matches:
        print('  {}'.format(str(match)))


