# -*- coding: utf-8 -*-
# Copyright: (c) 2016, Chamchenko
# GNU General Public License v2.0+ (see LICENSE.txt or https://www.gnu.org/licenses/gpl-2.0.txt)
# This file is part of plugin.video.nbainternational


import urlquick
import json
import time
import calendar
import xbmcgui
import os
import re
import uuid

from resources.lib.vars import *
from resources.lib.tools import *
from resources.lib.auth import get_headers
from resources.lib.auth import get_profile_info
from resources.lib.auth import get_device_ids
from resources.lib.auth import get_token
from codequick import Route
from codequick import Listitem
from codequick import Resolver
from codequick.utils import bold
from inputstreamhelper import Helper
from base64 import b64encode





def process_games(game, teams_info, cache_max_age):
        gameID = game['id']
        gameCode = game['seoName']
        game_time = game['st']
        game_time = time.strptime(game_time, '%Y-%m-%dT%H:%M:%S.%f')
        game_end_timestamp = None
        if 'playoff' in game:
            playoff_round = game['playoff']['round']
            host_team_record = int(game['playoff']['hr'].split('-')[0])
            away_team_record = int(game['playoff']['vr'].split('-')[0])
            game_number = host_team_record + away_team_record
        else:
            playoff_round = None
            game_number = None
        if 'et' in game:
            game_end = game['et']
            game_end = time.strptime(game_end, '%Y-%m-%dT%H:%M:%S.%f')
            game_end_timestamp = int(calendar.timegm(game_end) * 1000)
        else:
            if game_number:
                game_number = gameID[-1]
        game_timestamp = int(calendar.timegm(game_time) * 1000)
        host_team_code = game['h'] or 'TBD'
        away_team_code = game['v'] or 'TBD'
        game_state = game['gs']
        game_time_local = toLocalTimezone(time.mktime(game_time) * 1000)
        time_game = game_time_local.strftime("%H:%M")
        title = gen_title(
                            game_timestamp,
                            teams_info,
                            time_game,
                            host_team_code,
                            away_team_code,
                            game_end_timestamp,
                            playoff_round,
                            game_number
                         )
        liz = Listitem()
        liz.label = title
        date_game = game_time_local.strftime("%Y-%m-%d")
        liz.info.date(date_game, "%Y-%m-%d")
        if is_resources():
            thumb = get_thumb(host_team_code, away_team_code)
        elif CACHE_THUMB:
            thumb = download_thumb(GAME_THUMB_URL % gameID, host_team_code, away_team_code)
        else:
            thumb = GAME_THUMB_URL % gameID
        liz.art["thumb"] = thumb
        liz.art["poster"] = thumb
        feeds = []
        if 'caData' in game:
            for feed in game['caData']:
                gt = 1
                cn = None
                rd = False
                if 'name' in feed:
                    name = feed['name']
                    if 'cat' in feed:
                        name = '%s: %s' %(feed['cat'], name)
                elif 'subcat' in feed:
                    if feed['subcat'] == 'Teams' and feed['id'] == 'a':
                        name = 'Home Feed (%s)' % host_team_code
                    elif feed['subcat'] == 'Teams' and feed['id'] == 'b':
                        name = 'Away Feed (%s)' % away_team_code
                        gt = 4
                if 'cat' in feed:
                    if feed['cat'] == 'Condensed':
                        gt = 8
                    else:
                        name = 'Full Game %s' % name
                else:
                    name = 'Full Game %s' % name
                if feed['id'].isnumeric():
                    cn = int(feed['id'])
                if 'audio' in feed:
                    if feed['audio']:
                        rd = True
                        gt = 256
                feeds.append({ 'name': name, 'gt': gt, 'cn': cn, 'rd': rd})
        else:
            name = 'Full Game Home Feed (%s)' % host_team_code
            feeds.append({ 'name': name, 'gt': 1, 'cn': None, 'rd': False})
            if 'af' in game['video']:
                name = 'Full Game Away Feed (%s)' % away_team_code
                feeds.append({ 'name': name, 'gt': 4, 'cn': None, 'rd': False})
            if 'cameraAngles' in game:
                game_cameras = game['cameraAngles'].split(',')
                headers = {'User-Agent': USER_AGENT}
                nba_config = urlquick.get(
                                            CONFIG_ENDPOINT,
                                            headers=headers,
                                            max_age=-1
                                         ).json()
                nba_cameras = {}
                for camera in nba_config['content']['cameras']:
                    if camera['number'] == 0 or camera['number'] == 9:
                        continue
                    if 'audio' in camera:
                        rd = True
                        gt = 256
                    else:
                        rd = False
                        gt = 1
                    nba_cameras[camera['number']] = {'name': camera['name'], 'rd': rd, 'gt': gt}
                for camera in game_cameras:
                    camera = int(camera)
                    if camera == 0 or camera == 9:
                        continue
                    name = 'Full Game %s' % nba_cameras[camera]['name']
                    rd = nba_cameras[camera]['rd']
                    gt = nba_cameras[camera]['gt']
                    feeds.append({ 'name': name, 'gt': gt, 'cn': camera, 'rd': rd})               
        if 'video' in game:
            if 'c' in game['video']:
                name = 'Condensed Game'
                feeds.append({ 'name': name, 'gt': 8, 'cn': None, 'rd': False})
        liz.set_callback(
                            BROWSE_GAME,
                            gameID=gameID,
                            start_time=game_timestamp,
                            end_time=game_end_timestamp,
                            game_state=game_state,
                            feeds=feeds,
                            cache_max_age=cache_max_age
                        )
        return liz



@Route.register(content_type="videos")
def BROWSE_GAMES_MENU(plugin):
    FAVORITE_TEAMS = get_profile_info()['FAVORITE_TEAMS']
    yield Listitem.from_dict(
                                BROWSE_GAMES,
                                bold('Live Games'),
                                params = {'DATE': nowWEST()}
                            )
    if EN_CAL:
        yield Listitem.from_dict(
                                    BROWSE_MONTHS,
                                    bold('Upcoming'),
                                    params = {'cal': True}
                                )
    yield Listitem.from_dict(
                                BROWSE_MONTHS,
                                bold('Games Archive')
                            )
    if FAVORITE_TEAMS:
        yield Listitem.from_dict(
                                    BROWSE_TEAMS,
                                    bold('Favortite Team\'s Games'),
                                    params={'FAVORITE_TEAMS': FAVORITE_TEAMS}
                                )
    yield Listitem.from_dict(
                                BROWSE_TEAMS,
                                bold('Teams')
                            )



@Route.register(content_type='movies')
def BROWSE_TEAMS(plugin, FAVORITE_TEAMS=False):
    headers = {'User-Agent': USER_AGENT}
    teams_info = urlquick.get(
                                TEAMS_URL,
                                headers=headers,
                                max_age=7776000
                             ).json()['teams']
    for team in teams_info:
        if 'external' in teams_info[team]:
            if teams_info[team]['external']:
                continue
        if FAVORITE_TEAMS:
            if teams_info[team]['teamkey'] not in FAVORITE_TEAMS:
                continue
        team_name = '%s %s' % (
                                teams_info[team]['cityname'],
                                teams_info[team]['teamname']
                              )
        team_id = teams_info[team]['teamid']
        team_logo = TEAMS_LOGO_URL % team_id
        yield Listitem.from_dict(
                                    BROWSE_MONTHS,
                                    bold(team_name),
                                    art = {"thumb": team_logo},
                                    params = {'team': team}
                                )



@Route.register
def BROWSE_DAYS(plugin, month, year, cal=False, **kwargs):
    start_day = None
    headers = get_headers(True)
    if not headers:
        yield False
        return
    DATE = nowWEST()
    YEAR = DATE.year
    MONTH = DATE.month
    params = {
                'year': year,
                'month': month
             }
    if year == YEAR and month == MONTH and not cal:
        max_age = 0
        max_days = DATE.day - 1
    elif cal:
        max_days = None
        max_age = 0
        start_day = DATE.day
    else:
        max_age = 7776000
        max_days = None
    m = '0' + str(month) if month < 10 else month
    params = { 'month': '%s-%s' % (year, m)}
    gameDates = urlquick.get(
                                GAMEDATES_URL,
                                params=params,
                                headers=headers,
                                max_age=max_age
                            ).json()['gamedates']
    if not max_days and not start_day:
        gameDates = reversed(gameDates)
    elif start_day and int(m) == MONTH:
        n = len(gameDates) - start_day
        gameDates = gameDates[-n:]
    else:
        gameDates = gameDates[:max_days]
    for gameDate in gameDates:
        if gameDate['gamecount'] != '0':
            gamecount = gameDate['gamecount']
            is_empty = False
            day_time = gameDate['date']
            title = day_time + ' (%s games)' % gamecount
            day_time = time.strptime(day_time, '%Y-%m-%d')
            day_timestamp = calendar.timegm(day_time)
            day = datetime.datetime.fromtimestamp(day_timestamp)
            games = {'games': gameDate}
            yield Listitem.from_dict(
                                        BROWSE_GAMES,
                                        bold(title),
                                        params = {'DATE': day, 'cache_max_age': 60 * 60}
                                    )



@Route.register(content_type="videos")
def BROWSE_GAMES(plugin, DATE=None, games=None, cache_max_age=0):
    if not DATE:
        DATE = nowWEST()
    headers = {'User-Agent': USER_AGENT}
    teams_info = urlquick.get(
                                TEAMS_URL,
                                headers=headers,
                                max_age=7776000
                             ).json()['teams']
    if not games:
        todays_game_url = DAILY_URL % (
                                         DATE.year,
                                         DATE.month,
                                         DATE.day
                                       )
        resp = urlquick.get(
                                todays_game_url,
                                headers=headers,
                                max_age=cache_max_age
                            ).text.replace('var g_schedule=','')
        games = json.loads(resp)
    liz = None
    for game in games['games']:
        if 'game' in game:
            if not game['game']:
                continue
        liz = process_games(game, teams_info, cache_max_age)
        yield liz

    if not liz:
        yield False
        return



@Route.register(content_type="videos")
def BROWSE_MONTHS(plugin, year=None, team=None, cal=False):
    start_month = 1
    if not year:
        this_year = True
        DATE = nowWEST()
        year = DATE.year
        month = DATE.month
        if not team and not cal:
            start_month = 1
            day = DATE + datetime.timedelta(days=-1)
            yield Listitem.from_dict(
                                        BROWSE_GAMES,
                                        bold('Last Night'),
                                        params = {'DATE': day, 'cache_max_age': 60 * 60}
                                    )
            day = DATE + datetime.timedelta(days=-2)
            yield Listitem.from_dict(
                                        BROWSE_GAMES,
                                        bold('Two Nights Ago'),
                                        params = {'DATE': day, 'cache_max_age': 60 * 60}
                                    )
        if cal:
            day = DATE + datetime.timedelta(days=+1)
            yield Listitem.from_dict(
                                        BROWSE_GAMES,
                                        bold('Tomorrow'),
                                        params = {'DATE': day, 'cache_max_age': 60 * 60}
                                    )
            day = DATE + datetime.timedelta(days=+2)
            yield Listitem.from_dict(
                                        BROWSE_GAMES,
                                        bold('In Two days'),
                                        params = {'DATE': day, 'cache_max_age': 60 * 60}
                                    )
            start_month = month
            month = 12

    else:
        this_year = False
        month = 12
    headers = None #get_headers(True)
    if not headers:
        yield False
        return

    for m in reversed(range(start_month,month+1)):
        params = { 'month': '%s-%s' % (year, m)}
        month_infos = urlquick.get(
                                    GAMEDATES_URL,
                                    params=params,
                                    headers=headers,
                                    max_age=7776000
                                  ).json()
        game_count = 0
        for d in month_infos['gamedates']:
            game_count += int(d['gamecount'])
        if game_count == 0:
            continue
        if m == month and this_year:
            title = 'This Month'
        elif m == month - 1 and this_year:
            title = 'Last Month'
        else:
            title = calendar.month_name[m]

        if not team:
            if not cal:
                title = '%s (%s games)' % (title, game_count)
            callB = BROWSE_DAYS
        else:
            callB = BROWSE_MONTH
        yield Listitem.from_dict(
                                    callB,
                                    bold(title),
                                    params = {
                                                'month': m,
                                                'year': year,
                                                'team': team,
                                                'cal': cal
                                             }
                                )
    if not cal:
        yield Listitem.from_dict(
                                    BROWSE_YEARS,
                                    bold('Older'),
                                    params = {
                                                'year': year,
                                                'team': team
                                             }
                                )



@Route.register(content_type="videos")
def BROWSE_MONTH(plugin, year, month, team, **kwargs):
    headers = {'User-Agent': USER_AGENT}
    teams_info = urlquick.get(
                                TEAMS_URL,
                                headers=headers,
                                max_age=7776000
                             ).json()['teams']
    try:
        params = {
                    'year': year,
                    'month': month,
                    'team': team
                 }
        games = urlquick.get(
                                MONTHLY_URL,
                                params=params,
                                headers=headers,
                                max_age=240
                            ).json()['games']
        if not any(games):
            raise Exception('')
    except:
        plugin.notify(
                        'Info',
                        'No available game in the selected Month',
                        display_time=3000,
                        sound=True
                     )
        yield False
        return
    for game in games:
        if game != []:
            game = game[0]
            liz = process_games(game,teams_info, 0)
            yield liz




@Route.register(content_type="videos")
def BROWSE_YEARS(plugin, year, team=False):
    for y in reversed(range(2013,year)):
        yield Listitem.from_dict(
                                    BROWSE_MONTHS,
                                    bold(str(y)),
                                    params = {
                                                'year': y,
                                                'team': team
                                             }
                                )



@Route.register(content_type="videos")
def BROWSE_GAME(plugin, gameID, start_time, end_time, game_state, feeds, cache_max_age):
    headers = get_headers()
    play_options = urlquick.get(
                                PLAY_OPTIONS_URL % gameID,
                                headers=headers,
                                max_age=cache_max_age
                            ).json()
    for play_option in play_options['Vods']:
        yield Listitem.from_dict(
                                PLAY_GAME,
                                bold(play_option['DisplayName'][0]['Value']),
                                params = {
                                    'gameID': gameID,
                                    'videoProfileId': play_option['PlayActions'][0]['VideoProfile']['Id'],
                                    'applicationToken': '0'
                                }
                            )
    if len(play_options['Schedules']) > 0:
        for play_option in play_options['Schedules'][0]['Productions']:
            yield Listitem.from_dict(
                                    PLAY_GAME,
                                    bold(play_option['DisplayName'][0]['Value']),
                                    params = {
                                        'gameID': gameID,
                                        'videoProfileId': play_option['ExternalId'],
                                        'applicationToken': play_option['Id']
                                    }
                                )



@Resolver.register
def PLAY_GAME(plugin, gameID, videoProfileId, applicationToken):
    access_token = get_token()
    deviceinfos = get_device_ids()
    headers = {
        'content-type': 'text/plain;charset=UTF-8',
        'authorizationtoken': access_token,
        'azukiimc': 'IMC7.1.0_AN_D3.0.0_S0',
        'deviceprofile': b64encode(('{"model":"Unknown","osVersion":"89.0.4389.114","vendorName":"Unknown","osName":"HTML5","deviceUUID":"%s"}' % deviceinfos['DEVICEID']).encode('ascii')),
        'ApplicationToken': applicationToken
    } 
    sessionId = uuid.uuid1()
    play_options = urlquick.post(
                            PLAY_ROLL_URL % (videoProfileId, sessionId),
                            headers=headers,
                            data=b'{}',
                            max_age=0,
                            raise_for_status=False
                        ).json()['response']
    Script.log(play_options)
    url = '%s/%s&ISO3166=US&sessionId=%s' % (play_options['cdns']['cdn'][0]['base_uri'], play_options['manifest_uri'], sessionId)
    protocol = play_options['package_type']
    license_url = WIDEVINE_LICENSE_URL % (videoProfileId, sessionId)
    
    liz = Listitem()
    liz.path = url
    #liz.label = name
    liz.property[INPUTSTREAM_PROP] = 'inputstream.adaptive'
    
    is_helper = Helper(protocol, drm=DRM)
    if is_helper.check_inputstream():
        liz.property['inputstream.adaptive.manifest_type'] = protocol
        liz.property['inputstream.adaptive.license_type'] = DRM
        license_key = '%s|AuthorizationToken=%s&ApplicationToken=%s|R{SSM}|' % (license_url, access_token, applicationToken)
        liz.property['inputstream.adaptive.license_key'] = license_key
        liz.property['inputstream.adaptive.manifest_update_parameter'] = 'full'
        liz.property['inputstream.adaptive.play_timeshift_buffer'] = 'true'
        liz.property['ResumeTime'] = '2000'
        yield liz

    yield False
    return

