#!/usr/bin/env python

import sys
import configparser
import io
import urllib.request
import urllib.parse
import urllib.error
import gzip
import json
from datetime import datetime
import time

def main():
    # See https://erikberg.com/api/endpoints#requrl and build_url function
    host = 'erikberg.com'
    sport = 'nba'
    method = 'teams'
    id_ = None
    format_ = 'json'
    parameters = None

    url = build_url(host, sport, method, id_, format_, parameters)
    data, xmlstats_remaining, xmlstats_reset = http_get(url)
    teams = json.loads(data.decode('UTF-8'))
    for team in teams:
        # If no more requests are available in current window, wait.
        # Important: make sure your system is using NTP or equivalent, otherwise
        # this will produce incorrect results.
        if xmlstats_remaining == 0:
            now = int(datetime.now().strftime('%s'))
            delta = xmlstats_reset - now
            print('Reached rate limit. Waiting {} seconds to make new '
                  'request...'.format(delta))
            time.sleep(delta)
        url = build_url(host, sport, 'roster', team['team_id'], 'json', None)
        data, xmlstats_remaining, xmlstats_reset = http_get(url)
        roster = json.loads(data.decode('UTF-8'))
        # Process roster data... In this example, we are just printing each roster
        print('{} {} Roster'.format(roster['team']['first_name'], roster['team']['last_name']))
        for player in roster['players']:
            print('{: >25}, {:2} {:5} {:3} lb'.format(
                player['display_name'],
                player['position'],
                player['height_formatted'],
                player['weight_lb']))

def http_get(url):
    access_token = get_config('access_token')
    user_agent = 'xmlstats-expy/{} ({})'.format(
        get_config('version'),
        get_config('user_agent_contact'))
    req = urllib.request.Request(url)
    # Set Authorization header
    req.add_header('Authorization', 'Bearer ' + access_token)
    # Set user agent
    req.add_header('User-agent', user_agent)
    # Tell server we can handle gzipped content
    req.add_header('Accept-encoding', 'gzip')
    try:
        response = urllib.request.urlopen(req)
    except urllib.error.HTTPError as err:
        # If error is of type application/json, it will be an XmlstatsError
        # see https://erikberg.com/api/objects/xmlstats-error
        if err.headers.get('content-type') == 'application/json':
            data = json.loads(err.read().decode('UTF-8'))
            reason = data['error']['description']
        else:
            reason = err.read()
        print('Server returned {} error code!\n{}'.format(err.code, reason))
        sys.exit(1)
    except urllib.error.URLError as err:
        print('Error retrieving file: {}'.format(err.reason))
        sys.exit(1)
    data = None
    headers = response.info()
    xmlstats_reset = int(headers.get('xmlstats-api-reset'))
    xmlstats_remaining = int(headers.get('xmlstats-api-remaining'))
    if response.info().get('Content-encoding') == 'gzip':
        buf = io.BytesIO(response.read())
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()
    else:
        data = response.read()
    return data, xmlstats_remaining, xmlstats_reset

def get_config(key):
    config = configparser.ConfigParser()
    config.read('xmlstats.ini')
    return config['xmlstats'][key]

def build_url(host, sport, method, id_, format_, parameters):
    path = '/'.join(comp for comp in (sport, method, id_) if comp)
    url = 'https://' + host + '/' + path + '.' + format_
    if parameters:
        paramstring = urllib.parse.urlencode(parameters)
        url = url + '?' + paramstring
    return url

if __name__ == '__main__':
    main()
