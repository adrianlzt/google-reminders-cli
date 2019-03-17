import argparse
import json
import os
import sys
import readline  # to enable navigating through entered text
import time
from datetime import datetime
from typing import Tuple

import httplib2
from oauth2client import tools
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage
from parsedatetime.parsedatetime import Calendar
from colorama import Fore, Back, Style


APP_KEYS_FILE = os.path.expanduser('~/.config/google-reminders/app_keys.json')
USER_OAUTH_DATA_FILE = os.path.expanduser('~/.config/google-reminders/google-reminders-cli-oauth')

HTTP_OK = 200
WEEKDAYS = {
    0: 'Monday',
    1: 'Tuesday',
    2: 'Wednesday',
    3: 'Thursday',
    4: 'Friday',
    5: 'Saturday',
    6: 'Sunday',
}

def authenticate() -> httplib2.Http:
    """
    returns an Http instance that already contains the user credentials and is
    ready to make requests to alter user data.

    On the first time, this function will open the browser so that the user can
    grant it access to his data
    """
    with open(APP_KEYS_FILE) as f:
        app_keys = json.load(f)
    storage = Storage(USER_OAUTH_DATA_FILE)
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        credentials = tools.run_flow(
            OAuth2WebServerFlow(
                client_id=app_keys['APP_CLIENT_ID'],
                client_secret=app_keys['APP_CLIENT_SECRET'],
                scope=['https://www.googleapis.com/auth/reminders'],
                user_agent='google reminders cli tool'),
            storage,
        )
    auth_http = credentials.authorize(httplib2.Http())
    return auth_http


def build_request_params(
    title: str, year: int, month: int, day: int, hour: int, minute: int,
) -> Tuple[dict, dict]:
    """
    get the headers and data needed for the request

    :return: (headers, data)
    """
    second = 00  # we always use 0 seconds
    headers = {
        'content-type': 'application/json+protobuf',
    }

    id = time.time()  # the reminder id is the unix time at which it was created
    reminder_id = f'cli-reminder-{id}'

    # The structure of the dictionary was extracted from a browser request to
    # create a new reminder. I didn't find any official documentation
    # for the request parameters.
    if year:
        data = {
            "2": {
                "1": 7  # ID used by Calendar to save reminders
            },
            "3": {
                "2": reminder_id
            },
            "4": {
                "1": {
                    "2": reminder_id
                },
                "3": title,
                "5": {
                    "1": year,
                    "2": month,
                    "3": day,
                    "4": {
                        "1": hour,
                        "2": minute,
                        "3": second,
                    }
                },
                "8": 0
            }
        }
    else:
        data = {
            "2": {
                "1": 7  # Simulamos ser calendar
            },
            "3": {
                "2": reminder_id
            },
            "4": {
                "1": {
                    "2": reminder_id
                },
                "3": title,
                "8": 0
            }
        }
    return headers, data


def read_yes_no(prompt) -> bool:
    """
    read yes no answer from the user. default (empty answer) is yes
    """
    ans = input(f'{prompt} [Y/n] ').lower()
    return ans in ['', 'y', 'yes']


def _read_reminder_params(user_input, force=False):
    """
    :return: (headers, data), or None (meaning to action required)
    """
    dt = None

    # Direct input using arguments or asking the user
    if user_input:
        res = Calendar().nlp(user_input)
        if res:
            dt, flags, start_pos, end_post, matched_text = res[0]
            user_input = user_input[0:start_pos].strip()
    else:
        user_input = input('What\'s the reminder: ')

    if not dt:
        date_str = input('When do you want to be reminded (NA to omit date): ')
        if date_str != "NA":
            dt,r = Calendar().parseDT(date_str)
            if r == 0:
                print('Unrecognizable time text')
                return

    date_msg = ""
    if dt:
        weekday = WEEKDAYS[dt.weekday()]
        date_msg = f'on {weekday}, {str(dt.day).zfill(2)}/{str(dt.month).zfill(2)}/{dt.year} at {str(dt.hour).zfill(2)}:{str(dt.minute).zfill(2)}\n'

    print(f'"{user_input}" {date_msg}')

    if not force:
        save = read_yes_no('Do you want to save this?')

    if force or save:
        return build_request_params(user_input, dt.year, dt.month, dt.day, dt.hour, dt.minute)


# https://qiita.com/futa/items/c7a04c7b0be35508a626
def list_reminders(args, auth_http):
    reminders = _get_reminders(auth_http)

    # Reminders without location neither date
    simple_reminders = list(filter(lambda x: not x["location"] and not x["date"], reminders))
    if len(simple_reminders) > 0:
        print(f"\n{Style.BRIGHT}# Reminders{Style.RESET_ALL}")
        for i in simple_reminders:
            print(f'{Fore.GREEN}>{Style.RESET_ALL} {i.get("msg")} ({i.get("origin")})')

    # Reminders wih location
    location_reminders = list(filter(lambda x: x["location"], reminders))
    if len(location_reminders) > 0:
        print(f"\n{Style.BRIGHT}# Location reminders{Style.RESET_ALL}")
        for i in location_reminders:
            print(f"{Fore.GREEN}{i.get('location').get('name')}{Style.RESET_ALL}: {i.get('msg')} ({i.get('origin')})")

    # Reminders with date
    date_reminders = list(filter(lambda x: x["date"], reminders))
    if len(date_reminders) > 0:
        now = datetime.now()
        date_reminders.sort(key=lambda x: x["date"])
        print(f"\n{Style.BRIGHT}# Date reminders{Style.RESET_ALL}")
        for i in date_reminders:
            date_str = f"{i['date'].strftime('%d/%m/%Y %H:%M')}"
            if not i["time"]:
                date_str = f"{i['date'].strftime('%d/%m/%Y      ')}"

            if now > i["date"]:
                date_str = f"{Fore.RED}{date_str}{Style.RESET_ALL}"
            else:
                date_str = f"{Fore.GREEN}{date_str}{Style.RESET_ALL}"

            print(f"{date_str}: {i.get('msg')} ({i.get('origin')})")

def _get_reminders(auth_http):
    headers = {
        'content-type': 'application/json+protobuf',
    }
    data = {
       "1":{
          "4":"WRP / /WebCalendar/calendar_190310.14_p4"
       },
       "2":[
          { "1":3 },
          { "1":16 },
          { "1":1 },
          { "1":8 },
          { "1":11 },
          { "1":5 },
          { "1":6 },
          { "1":13 },
          { "1":4 },
          { "1":12 },
          { "1":7 },
          { "1":17 }
       ],
       "5":0,  # List only uncompleted reminders
       "6":1000,  # List 1000 events max
    }

    response, content = auth_http.request(
        uri='https://reminders-pa.clients6.google.com/v1internalOP/reminders/list',
        method='POST',
        body=json.dumps(data),
        headers=headers,
    )

    reminders = []

    if response.status == HTTP_OK:
        data_json = json.loads(content)["1"]
        for d in data_json:
            try:
                reminders.append(_parse_reminder(d))
            except Exception as ex:
                raise Exception("Error parsing reminder = %s. Exception: %s" % (d, ex))
    else:
        raise Exception(f'Error while trying to list reminders: status code - {response.status}. {content}')

    return reminders

def _parse_reminder(d):
    msg = d["3"]
    date = d.get("5")
    location = d.get("6")

    origin_id = d["2"]["1"]
    origin_map = {
            1: "inbox",
            4: "keep",
            7: "calendar"
    }

    dt = None
    has_time = False
    if date:
        year = date["1"]
        month = date["2"]
        day = date["3"]
        dt = datetime(year, month, day)

        time = date.get("4")
        if time:
            has_time = True
            hour = time["1"]
            minute = time["2"]
            second = time["3"]
            dt = dt.replace(hour=hour, minute=minute)

    # Only return coordinates and name of the location
    if location:
        location = {
            "name": location.get("7"),
            "lat": location.get("1"),
            "lng": location.get("2")
        }

    if d["1"]["2"].startswith("cli-reminder-"):
        origin = "cli-reminder"
    else:
        origin = origin_map[origin_id] if origin_id in origin_map else "unknown"

    return {
            "msg": msg,
            "date": dt,
            "time": has_time,
            "location": location,
            "origin": origin
        }


def new_reminder(args, auth_http):
    params = _read_reminder_params(args.new_text, args.force)
    if params:
        headers, data = params
        response, content = auth_http.request(
            uri='https://reminders-pa.clients6.google.com/v1internalOP/reminders/create',
            method='POST',
            body=json.dumps(data),
            headers=headers,
        )
        if response.status == HTTP_OK:
            print('Reminder set successfully')
        else:
            print('Error while trying to set a reminder:')
            print(f'    status code - {response.status}')
            print(f'    {content}')
    else:
        print('Reminder was not saved')

def parse_args():
    """
    parse and return the program arguments
    """
    parser = argparse.ArgumentParser(description='Google reminders cli')
    subparsers = parser.add_subparsers(title='subcommands', metavar='action')

    new_desc = '''
    Create new reminders with, or without, date associated.

    Examples:
        buy milk in 2 hours
        watch film matrix
    '''

    parser_new = subparsers.add_parser('new', help='new reminder', description=new_desc,
            formatter_class=argparse.RawTextHelpFormatter)
    parser_new.set_defaults(func=new_reminder)
    parser_new.add_argument('-t','--text', action='store', dest='new_text', help="Text of the reminder, with or without date/time (optional)", default=None)
    parser_new.add_argument('-f','--force', action='store_const', dest='force', help="Do not ask for confirmation", default=False, const=True)

    parser_list = subparsers.add_parser('list', help='list reminders')
    parser_list.set_defaults(func=list_reminders)

    return parser.parse_args()

def main():
    args = parse_args()
    auth_http = authenticate()
    args.func(args, auth_http)

if __name__ == '__main__':
    main()
