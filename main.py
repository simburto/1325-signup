guh = """coolest electrical lead B)

       *
    /((/((((#%%/
     #%&@((&%##*
     (##(####%(    **
    (%%&&&&&&&%%%#/
 /##%%&&&&&&&&&%*
  /#%%&&&&&&&&&#
    (%%&&&&&&&&%#*
     #%%%&&&&&&&&#
     (%%%%%%%&&&&&%/
    (#%%%%%%&&&&&&%#/
     (#%%%%%%%%%&%*
     (#%%/     %%(
      (#*      #%(
      *        (#/

            ____                                                                ____
          ,'  , `.                                                            ,'  , `.                        
       ,-+-,.' _ |                 ,---,               ,---.               ,-+-,.' _ |                 ,---,  
    ,-+-. ;   , ||             ,-+-. /  |  ,----._,.  '   ,'\           ,-+-. ;   , ||             ,-+-. /  | 
   ,--.'|'   |  || ,--.--.    ,--.'|'   | /   /  ' / /   /   |         ,--.'|'   |  || ,--.--.    ,--.'|'   | 
  |   |  ,', |  |,/       \  |   |  ,"' ||   :     |.   ; ,. :        |   |  ,', |  |,/       \  |   |  ,"' | 
  |   | /  | |--'.--.  .-. | |   | /  | ||   | .\  .'   | |: :        |   | /  | |--'.--.  .-. | |   | /  | | 
  |   : |  | ,    \__\/: . . |   | |  | |.   ; ';  |'   | .; :        |   : |  | ,    \__\/: . . |   | |  | | 
  |   : |  |/     ," .--.; | |   | |  |/ '   .   . ||   :    |        |   : |  |/     ," .--.; | |   | |  |/  
  |   | |`-'     /  /  ,.  | |   | |--'   `---`-'| | \   \  /         |   | |`-'     /  /  ,.  | |   | |--'   
  |   ;/        ;  :   .'   \|   |/       .'__/\_: |  `----'          |   ;/        ;  :   .'   \|   |/       
  '---'         |  ,     .-./'---'        |   :    :                  '---'         |  ,     .-./'---'        
                 `--`---'                  \   \  /                                  `--`---'                 
                                            `--`-'                                                            
         ,,,,      ........
        ,,,,,,,,..............
       ,****,,*,....,.,.........
     **/*****,,,,,,.,,.............
    //(//*/*,,**,,,,,..,.,...........
   /#(((//*****/**,,,*,,*,,,...........
  (((#(#(///**/(*//**//,,,,,,,,.....,...
 /######(((#((///(/*/*****,,,,.,...... .,
 (###((####(##(((/(/*/*/*****,,,,...,.. .
 (#####((((###(#(((/////******,,,,..... ..
 *######(##(((((#(((((/***/***,,*,,,......
  (########((((#((((((///*******,,,,,.....
   (###(####(((#((((((/(///******,,.......
    (######((((#(((((((/////*/**,,,,,,...,
     (#####((((((((((//////*******,,,.....
      ((#(#((#((((((((((/////**,,*,,,.,,,
        (####((#(((#(///////****,,,,,,,,
        ((((((((((///////****,,*,,,,,,
           (#((#((/(/////****,,,,,,,,.
             /((//////***,*,,,,,,,,
               ******,,,,,,,,,,..
                    .,..,,,,.
"""

import logging
import json
import os
import time
from multiprocessing import Process, Manager
from collections import defaultdict
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

app = App(token=os.getenv("SLACK_BOT_TOKEN"))
POLL_FILE = "polls.json"
POLL_PROCESSES_FILE = "poll_processes.json"
poll_processes = {}
POLL_PERMS = "perms.json"
logger = logging.getLogger(__name__)
logging.basicConfig(filename='log.log', level=logging.INFO)
logger.info('Started')

def is_valid_rq(say, polls, rq_channel_id, rq_user_id, rq_poll_id=None):
    level = perms.get(rq_user_id, None)

    if level is None:  # Not in whitelist
        say(f":wompwomp2::wompwomp2: <@{rq_user_id}> you are not in the whitelist! :wompwomp2::wompwomp2:")
        return False

    # We're creating a poll, so check if we have a valid level to do this action and check if ID is valid
    if rq_poll_id is None:
        if level >= 0:
            return True

    poll = polls.get(rq_poll_id, None)

    if poll is None:
        app.client.chat_postEphemeral(channel=rq_channel_id, user=rq_user_id, text=f":wompwomp2::wompwomp2: <@{rq_user_id}> Invalid Poll "
                                                                                   f"ID! :wompwomp2::wompwomp2:")
        return False

    if level == 1:
        if poll['channel_id'] != rq_channel_id:
            app.client.chat_postEphemeral(channel=rq_channel_id, user=rq_user_id, text=f":wompwomp2::wompwomp2: <@{rq_user_id}> You can't "
                                                                                       f"end a poll from a different "
                                                                                       f"channel! :wompwomp2::wompwomp2:")
            return False
        else:
            return True
    else:
        say(f":wompwomp2::wompwomp2: <@{rq_user_id}> you are not authorized! :wompwomp2::wompwomp2:")
        return False


def save_polls_to_file(polls):
    with open(POLL_FILE, 'w') as file:
        json_polls = {str(k): dict(v) for k, v in polls.items()}
        json.dump(json_polls, file)


def load_polls_from_file():
    if os.path.exists(POLL_FILE):
        with open(POLL_FILE, 'r') as file:
            try:
                json_polls = json.load(file)
                return {int(k): v for k, v in json_polls.items()}
            except json.JSONDecodeError:
                return {}
    return {}


def save_poll_processes_to_file(poll_processes):
    with open(POLL_PROCESSES_FILE, 'w') as file:
        json.dump({str(k): v.pid for k, v in poll_processes.items()}, file)


def load_poll_processes_from_file():
    if os.path.exists(POLL_PROCESSES_FILE):
        with open(POLL_PROCESSES_FILE, 'r') as file:
            try:
                return {int(k): v for k, v in json.load(file).items()}
            except json.JSONDecodeError:
                return {}
    return {}


def process_poll(polls, poll_id, channel_id):
    poll = polls[poll_id]
    stripped_emojis = poll['emojis']
    options = poll['options']
    max_mentions = poll['max_mentions']
    poll_results = poll['results']

    try:
        reaction = app.client.reactions_get(
            channel=channel_id,
            timestamp=poll['timestamp']
        )
    except Exception as e:
        logger.info(f"Error fetching reactions: {e}")
        return
    voted = []
    for emoji in stripped_emojis:
        user_mentions = []
        reaction_data = next((r for r in reaction['message']['reactions'] if r['name'] == emoji), None)
        if reaction_data:
            max_mentions = int(max_mentions)
            limit = max_mentions + 1 if max_mentions >= 0 else len(reaction_data['users'])
            for user in reaction_data['users'][:limit]:
                user_info = app.client.users_info(user=user)
                if user_info['user']['id'] != "U07ML8X2DE1":
                    if user_info not in voted:
                        user_mentions.append(f"<@{user_info['user']['id']}>")

            if int(poll['option_count']) != 1:
                voted = []

            if user_mentions not in voted:
                poll_results[emoji] = {
                    "count": reaction_data['count'] - 1,
                    "users": ', '.join(user_mentions)
                }
                voted.append([f"<@{user_info['user']['id']}>"])
        else:
            poll_results[emoji] = {
                "count": 0,
                "users": "No votes"
            }

    return poll, max_mentions, options, stripped_emojis, poll_results


def update_poll_results(channel_id, poll_id, polls):
    if polls.get(poll_id, None):
        poll, max_mentions, options, stripped_emojis, poll_results = process_poll(polls, poll_id, channel_id)
        if int(poll['option_count']) == 1:
            option_msg = "One vote"
        else:
            option_msg = "Unlimited votes"
        remaining_time = poll['duration'] * 3600 - (time.time() - poll['start_time'])
        remaining_minutes = max(0, int(remaining_time // 60))
        remaining_seconds = int(remaining_time % 60)
        max_members_msg = "Max Members: " + (str(max_mentions) if max_mentions >= 0 else "No limit")
        result_message = f"Poll Results (Time Remaining: {remaining_minutes}m {remaining_seconds}s, {max_members_msg}, {option_msg}):\n"
        if poll['duration'] <= 0:
            result_message = f"Poll Results (Time Remaining: No time limit, {max_members_msg}):\n"

        if polls[poll_id]['option_count'] == 1:
            data = poll_results

            user_set = set()  # To keep track of unique users

            for key, value in data.items():
                if value['users']:
                    # Split users by comma and strip whitespace
                    users = [user.strip() for user in value['users'].split(',')]
                    # Add new users to the set
                    unique_users = [user for user in users if user not in user_set]
                    # Update the set with the new unique users
                    user_set.update(unique_users)
                    value['users'] = ', '.join(unique_users)

            poll_results = data

        for option, emoji in zip(options, stripped_emojis):
            try:
                user_mentions = poll_results[emoji]['users']
                count = poll_results[emoji]['count']
            except KeyError:
                user_mentions = ''
            if user_mentions == '':
                count = 0
            user_mentions = str(user_mentions).replace("]", "").replace("[", "").replace("'", "")
            result_message += f":{emoji}: {option.strip()}: {count} votes ({user_mentions})\n"

        try:
            app.client.chat_update(
                channel=channel_id,
                ts=poll['timestamp'],
                text=result_message
            )
        except Exception as e:
            logger.info(f"Failed to update message: {e}")


def create_poll(channel_id, question, options, emojis, duration, max_mentions, option_count, polls, poll_id=None):
    if poll_id is None:
        poll_id = len(polls)

    poll_data = polls.get(poll_id, {'active': True, 'channel_id': channel_id})
    poll_results = poll_data.get('results', {})

    if 'timestamp' not in poll_data:
        poll_message = f"*{question}*\n"
        for option, emoji in zip(options, emojis):
            poll_message += f":{emoji.strip()}:{option.strip()}\n"

        result = app.client.chat_postMessage(
            channel=channel_id,
            text=poll_message
        )

        poll_ts = result['ts']
        poll_data['timestamp'] = poll_ts

        stripped_emojis = [emoji.strip().strip(':') for emoji in emojis]

        for emoji in stripped_emojis:
            try:
                app.client.reactions_add(
                    channel=channel_id,
                    name=emoji,
                    timestamp=poll_ts
                )
            except Exception as e:
                logger.info(f"Failed to add reaction '{emoji}': {e}")

        poll_data.update({
            'options': options,
            'emojis': stripped_emojis,
            'results': poll_results,
            'max_mentions': max_mentions,
            'start_time': time.time(),
            'duration': duration,
            'option_count': option_count,
        })

        polls[poll_id] = poll_data
        save_polls_to_file(polls)
        logger.info(f"create poll {polls}")

    while True:
        if not polls.get(poll_id, None):
            break

        update_poll_results(channel_id, poll_id, polls)
        time.sleep(10)

        elapsed_time = time.time() - poll_data['start_time']
        if elapsed_time >= duration * 3600 and duration > 0:
            cleanup_poll(polls, poll_id, channel_id)
            break

    save_polls_to_file(polls)


def cleanup_poll(polls, poll_id, channel_id):
    poll, max_mentions, options, stripped_emojis, poll_results = process_poll(polls, poll_id, channel_id)

    result_message = f"Final Poll Results:\n"
    if polls[poll_id]['option_count'] == 1:
        data = poll_results

        user_set = set()  # To keep track of unique users

        for key, value in data.items():
            if value['users']:
                # Split users by comma and strip whitespace
                users = [user.strip() for user in value['users'].split(',')]
                # Add new users to the set
                unique_users = [user for user in users if user not in user_set]
                # Update the set with the new unique users
                user_set.update(unique_users)
                value['users'] = ', '.join(unique_users)

        poll_results = data

    for option, emoji in zip(options, stripped_emojis):
        try:
            user_mentions = poll_results[emoji]['users'].split(",")
            count = poll_results[emoji]['count']
        except KeyError:
            user_mentions = ''
        if user_mentions == '':
            count = 0
        user_mentions = str(user_mentions).replace("]", "").replace("[", "").replace("'", "")
        result_message += f":{emoji}: {option.strip()}: {count} votes ({user_mentions})\n"

    try:
        app.client.chat_update(
            channel=channel_id,
            ts=poll['timestamp'],
            text=result_message
        )
    except Exception as e:
        logger.info(f"Failed to update message: {e}")

    polls.pop(poll_id, None)
    save_polls_to_file(polls)


@app.command("/createpoll")
def handle_createpoll(ack, body, say):
    ack()
    text = body['text']
    channel_id = body['channel_id']
    if is_valid_rq(say, polls, channel_id, body['user_id']):
        try:
            parts = [part.strip() for part in text.split('|')]
            if len(parts) != 6:
                app.client.chat_postEphemeral(channel=channel_id, user=body['user_id'], text="Invalid format. Please use the format: "
                                                                                             "question | option1,option2 | emoji1,"
                                                                                             "emoji2 | duration (in hours) | max_mentions "
                                                                                             "(number) | 1 option.")
                return

            question, options, emojis, duration, max_mentions, option_count = parts
            options = options.split(',')
            emojis = emojis.split(',')

            try:
                duration = int(duration)
            except ValueError:
                app.client.chat_postEphemeral(channel=channel_id, user=body['user_id'], text="Duration must be a valid number of hours.")
                return

            try:
                max_mentions = int(max_mentions)
            except ValueError:
                app.client.chat_postEphemeral(channel=channel_id, user=body['user_id'], text="Max mentions must be a valid number.")
                return

            if len(options) != len(emojis):
                app.client.chat_postEphemeral(channel=channel_id, user=body['user_id'], text="The number of options must match the number "
                                                                                             "of emojis.")
                return

            p = Process(target=create_poll,
                        args=(channel_id, question, options, emojis, duration, max_mentions, option_count, polls))
            p.start()
            poll_id = len(polls)

            poll_processes[poll_id] = p
            save_poll_processes_to_file(poll_processes)
            say(f"Poll created (ID: {poll_id}): {question}")

        except Exception as e:
            app.client.chat_postEphemeral(channel=channel_id, user=body['user_id'], text=f":wompwomp2::wompwomp2: Failed to create poll: "
                                                                                         f"{e} :wompwomp2::wompwomp2:")


@app.command("/endpoll")
def handle_endpoll(ack, body, say):
    ack()
    poll_id_str = body['text'].strip()
    channel_id = body['channel_id']
    if not poll_id_str.isdigit():
        app.client.chat_postEphemeral(channel=channel_id, user=body['user_id'], text="Please provide a valid poll ID.")
        return
    poll_id = int(poll_id_str)
    if is_valid_rq(say, polls, channel_id, body['user_id'], poll_id):
        if poll_id in polls:
            cleanup_poll(polls, poll_id, channel_id)

            if poll_id in poll_processes:
                process = poll_processes[poll_id]
                process.terminate()
                process.join()
                del poll_processes[poll_id]
                save_poll_processes_to_file(poll_processes)
                app.client.chat_postEphemeral(channel=channel_id, user=body['user_id'], text=f"Poll (ID: {poll_id}) has been ended "
                                                                                             f"successfully.")
            else:
                app.client.chat_postEphemeral(channel=channel_id, user=body['user_id'], text=f"Poll (ID: {poll_id}) is not running, but "
                                                                                             f"has been deactivated.")
        else:
            app.client.chat_postEphemeral(channel=channel_id, user=body['user_id'], text=f"No active poll found with ID: {poll_id}.")


@app.event("reaction_added")
def handle_reaction_added(ack, body):
    ack()
    event = body['event']
    channel_id = event['item']['channel']
    poll_ts = event['item']['ts']

    for poll_id, poll_data in polls.items():
        if poll_data['timestamp'] == poll_ts:
            update_poll_results(channel_id, poll_id, polls)
            break


@app.event("reaction_removed")
def handle_reaction_removed(ack, body):
    ack()
    event = body['event']
    channel_id = event['item']['channel']
    poll_ts = event['item']['ts']

    for poll_id, poll_data in polls.items():
        if poll_data['timestamp'] == poll_ts:
            update_poll_results(channel_id, poll_id, polls)
            break


def reload_active_polls():
    for poll_id, poll_data in polls.items():
        if poll_data['active']:
            p = Process(target=create_poll, args=(
                poll_data['channel_id'],
                "",
                poll_data['options'],
                poll_data['emojis'],
                poll_data['duration'],
                poll_data['max_mentions'],
                poll_data['option_count'],
                polls,
                poll_id
            ))
            p.start()
            poll_processes[poll_id] = p

    save_poll_processes_to_file(poll_processes)


if __name__ == "__main__":
    with open(POLL_PERMS, 'r') as file:
        try:
            perms = json.load(file)
        except json.JSONDecodeError as e:
            logger.info(f"Failed to load permissions: {e}")

    manager = Manager()
    polls = manager.dict(load_polls_from_file())
    poll_processes = {}
    reload_active_polls()

    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()