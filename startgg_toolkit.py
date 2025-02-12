# Contains scripts to assist with interacting with the start.gg API.
# Requires a file "smashgg.key" in the same directory with your start.gg API key inside.

import requests 
import re 
import time

SMASH_GG_ENDPOINT = 'https://api.smash.gg/gql/alpha'

ggkeyfile = open('smashgg.key')
ggkey = ggkeyfile.read()
ggkeyfile.close()
ggheader = {"Authorization": "Bearer " + ggkey}

startgg_slug_regex = re.compile(
    r'tournament\/[a-z0-9\-_]+\/events?\/[a-z0-9\-_]+')


class InvalidEventUrlException(Exception):
    pass

def send_request(query, variables, quiet=False):
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
            response = requests.post(
                SMASH_GG_ENDPOINT, json=json_payload, headers=ggheader, timeout=60)

            if response.status_code == 200:
                response_json = response.json()
                progress = True
            else:
                tries += 1
                if response.status_code == 429:
                    if not quiet:
                        print(f'try {tries}: rate limit exceeded... sleeping then trying again... ', end='', flush=True)
                elif response.status_code == 502:
                    if not quiet:
                        print(f'try {tries}: 502 bad gateway... sleeping then trying again... ', end='', flush=True)
                else:
                    if not quiet:
                        print(f'try {tries}: received non-200 response... sleeping then trying again... ', end='', flush=True)
                        print(response.text)
                        print(response.status_code)

                time.sleep(60)
                if not quiet:
                    print('retrying')

        except Exception as e:
            tries += 1
            if not quiet:
                print(f'try {tries}: requests failure... sleeping then trying again... ', end='', flush=True)
                print(e)
            time.sleep(60)
            if not quiet:
                print('retrying')


    return response_json


def isolate_slug(url):
    match = startgg_slug_regex.search(url)

    if not match:
        raise InvalidEventUrlException 

    return match.group(0).replace('/events/', '/event/')