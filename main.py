import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from multiprocessing import Process, Manager
import time
from dotenv import load_dotenv
import logging

load_dotenv()

# Initialize Slack App
app = App(token=os.getenv("SLACK_BOT_TOKEN"))

def create_poll(channel_id, question, options, emojis, duration, max_mentions, polls):
    poll_id = len(polls)
    poll_data = {'active': True, 'channel_id': channel_id}

    poll_results = {}

    # Create poll message
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

    # Add initial reactions
    for emoji in stripped_emojis:
        try:
            app.client.reactions_add(
                channel=channel_id,
                name=emoji,
                timestamp=poll_ts
            )
        except Exception as e:
            logging.error(f"Failed to add reaction '{emoji}': {e}")

    # Store poll metadata in shared dict
    poll_data.update({
        'options': options,
        'emojis': stripped_emojis,
        'results': poll_results,
        'max_mentions': max_mentions,
        'start_time': time.time(),
        'duration': duration
    })
    polls[poll_id] = poll_data

    # Start a loop to update the poll every minute
    while poll_data['active']:
        update_poll_results(channel_id, poll_id, polls)
        time.sleep(60)  # Sleep for 60 seconds

        # Check if poll duration has expired
        elapsed_time = time.time() - poll_data['start_time']  # Corrected line
        if elapsed_time >= duration * 3600:  # Convert hours to seconds
            poll_data['active'] = False
            break


def update_poll_results(channel_id, poll_id, polls):
    poll = polls[poll_id]
    stripped_emojis = poll['emojis']
    options = poll['options']
    max_mentions = poll['max_mentions']
    poll_results = poll['results']

    # Fetch reactions for the poll message
    try:
        reaction = app.client.reactions_get(
            channel=channel_id,
            timestamp=poll['timestamp']
        )
    except Exception as e:
        logging.error(f"Error fetching reactions: {e}")
        return

    for emoji in stripped_emojis:
        reaction_data = next((r for r in reaction['message']['reactions'] if r['name'] == emoji), None)
        if reaction_data:
            user_mentions = []
            limit = max_mentions + 1 if max_mentions >= 0 else len(reaction_data['users'])
            for user in reaction_data['users'][:limit]:
                user_info = app.client.users_info(user=user)
                if user_info['user']['id'] != "U07ML8X2DE1":  # Ensure bot's own reactions are excluded
                    user_mentions.append(f"<@{user_info['user']['id']}>")

            poll_results[emoji] = {
                "count": reaction_data['count'] - 1,
                "users": ', '.join(user_mentions)
            }
        else:
            poll_results[emoji] = {
                "count": 0,
                "users": "No votes"
            }

    # Construct the result message
    remaining_time = poll['duration'] * 3600 - (time.time() - poll['start_time'])
    remaining_minutes = max(0, int(remaining_time // 60))
    remaining_seconds = int(remaining_time % 60)
    max_members_msg = "Max Members: " + (str(max_mentions) if max_mentions >= 0 else "No limit")
    result_message = f"Poll Results (Time Remaining: {remaining_minutes}m {remaining_seconds}s, {max_members_msg}):\n"
    if poll['duration'] <= 0:
        result_message = f"Poll Results (Time Remaining: No time limit, {max_members_msg}):\n"

    for option, emoji in zip(options, stripped_emojis):
        user_mentions = poll_results[emoji]['users']
        result_message += f":{emoji}: {option.strip()}: {poll_results[emoji]['count']} votes ({user_mentions})\n"

    # Update the poll message
    try:
        app.client.chat_update(
            channel=channel_id,
            ts=poll['timestamp'],
            text=result_message
        )
    except Exception as e:
        logging.error(f"Failed to update message: {e}")


@app.command("/createpoll")
def handle_createpoll(ack, body, say):
    ack()
    text = body['text']
    try:
        parts = [part.strip() for part in text.split('|')]
        if len(parts) != 5:
            say("Invalid format. Please use the format: question | option1,option2 | emoji1,emoji2 | duration (in hours) | max_mentions (number).")
            return

        question, options, emojis, duration, max_mentions = parts
        options = options.split(',')
        emojis = emojis.split(',')

        try:
            duration = int(duration)
        except ValueError:
            say("Duration must be a valid number of hours.")
            return

        try:
            max_mentions = int(max_mentions)
        except ValueError:
            say("Max mentions must be a valid number.")
            return

        if len(options) != len(emojis):
            say("The number of options must match the number of emojis.")
            return

        channel_id = body['channel_id']
        p = Process(target=create_poll, args=(channel_id, question, options, emojis, duration, max_mentions, polls))
        p.start()

        say(f"Poll created (ID: {len(polls)}): {question}")

    except Exception as e:
        say(f"Failed to create poll: {e}")


@app.command("/removepoll")
def handle_removepoll(ack, body, say):
    ack()
    poll_id_str = body['text'].strip()

    if not poll_id_str.isdigit():
        say("Please provide a valid poll ID.")
        return

    poll_id = int(poll_id_str)

    # Check if the poll ID exists
    if poll_id in polls:
        polls[poll_id]['active'] = False  # Mark poll as inactive
        say(f"Poll (ID: {poll_id}) has been removed successfully.")
    else:
        say(f"No active poll found with ID: {poll_id}.")


# Reaction added event handler
@app.event("reaction_added")
def handle_reaction_added(body, say):
    event = body['event']
    channel_id = event['item']['channel']
    poll_ts = event['item']['ts']

    for poll_id, poll_data in polls.items():
        if poll_data['timestamp'] == poll_ts:
            update_poll_results(channel_id, poll_id, polls)
            break

# Reaction removed event handler
@app.event("reaction_removed")
def handle_reaction_removed(body, say):
    event = body['event']
    channel_id = event['item']['channel']
    poll_ts = event['item']['ts']

    for poll_id, poll_data in polls.items():
        if poll_data['timestamp'] == poll_ts:
            update_poll_results(channel_id, poll_id, polls)
            break

if __name__ == "__main__":
    # Make sure multiprocessing only runs in the main process
    manager = Manager()
    polls = manager.dict()  # Global manager dict

    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()
