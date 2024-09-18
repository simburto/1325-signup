import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from multiprocessing import Process
import time
from dotenv import load_dotenv

load_dotenv()

app = App(token=os.getenv("SLACK_BOT_TOKEN"))

polls = {}

@app.event("reaction_added")
def refresh_poll(duration, start_time, poll_id, update_interval, stripped_emojis, channel_id, poll_ts, max_mentions, poll_results):
    def duration_check():
        return duration <= 0 or time.time() - start_time < duration * 3600

    if polls[poll_id]['active'] and duration_check():
        time.sleep(update_interval)

        for emoji in stripped_emojis:
            reaction = app.client.reactions_get(
                channel=channel_id,
                timestamp=poll_ts
            )

            reaction_data = next((r for r in reaction['message']['reactions'] if r['name'] == emoji), None)
            if reaction_data:
                user_mentions = []
                limit = max_mentions + 1 if max_mentions >= 0 else len(reaction_data['users'])
                for user in reaction_data['users'][:limit]:
                    user_info = app.client.users_info(user=user)
                    if user_info['user']['id'] != 'U07ML8X2DE1':
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

        remaining_time = duration * 3600 - (time.time() - start_time)
        remaining_minutes = max(0, int(remaining_time // 60))
        remaining_seconds = int(remaining_time % 60)
        max_members_msg = "Max Members: " + (str(max_mentions) if max_mentions >= 0 else "No limit")
        result_message = f"Poll Results (Time Remaining: {remaining_minutes}m {remaining_seconds}s, {max_members_msg}):\n"
        if duration <= 0:
            result_message = f"Poll Results (Time Remaining: No time limit, {max_members_msg}):\n"

        for option, emoji in zip(options, stripped_emojis):
            user_mentions = poll_results[emoji]['users']
            result_message += f":{emoji}: {option.strip()}: {poll_results[emoji]['count']} votes ({user_mentions})\n"

        if result_message != last_result_message:
            try:
                app.client.chat_update(
                    channel=channel_id,
                    ts=poll_ts,
                    text=result_message
                )
                last_result_message = result_message
            except Exception as e:
                print(f"Failed to update message: {e}")


def create_poll(channel_id, question, options, emojis, duration, max_mentions):
    poll_id = len(polls)
    polls[poll_id] = {'active': True, 'channel_id': channel_id}

    poll_results = {}
    try:
        poll_message = f"*{question}*\n"
        for option, emoji in zip(options, emojis):
            poll_message += f":{emoji.strip()}:{option.strip()}\n"

        result = app.client.chat_postMessage(
            channel=channel_id,
            text=poll_message
        )

        poll_ts = result['ts']
        polls[poll_id]['timestamp'] = poll_ts

        stripped_emojis = [emoji.strip().strip(':') for emoji in emojis]

        for emoji in stripped_emojis:
            try:
                print(f"Adding reaction: {emoji}")
                app.client.reactions_add(
                    channel=channel_id,
                    name=emoji,
                    timestamp=poll_ts
                )
            except Exception as e:
                print(f"Failed to add reaction '{emoji}': {e}")

        update_interval = 5
        last_result_message = ""
        start_time = time.time()

        refresh_poll()

        final_result_message = "Final Poll Results:\n"
        for option, emoji in zip(options, stripped_emojis):
            print(poll_results)
            user_mentions = poll_results[emoji]['users']
            final_result_message += f":{emoji.strip()} {option.strip()}: {poll_results[emoji]['count']} votes ({user_mentions})\n"

        app.client.chat_update(
            channel=channel_id,
            ts=poll_ts,
            text=final_result_message
        )
        polls[poll_id]['active'] = False

    except Exception as e:
        print(f"Error in create_poll process: {e}")


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
        print(emojis)
        print(duration)
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

        poll_id = len(polls)

        channel_id = body['channel_id']
        p = Process(target=create_poll, args=(channel_id, question, options, emojis, duration, max_mentions))
        p.start()

        say(f"Poll created (ID: {poll_id}): {question}")

    except Exception as e:
        say(f"Failed to create poll: {e}")


def convert_to_slack_timestamp(input_ts):
    seconds = int(input_ts) // 1000
    milliseconds = int(input_ts) % 1000
    slack_ts = f"{seconds}.{milliseconds:03d}"
    return slack_ts


if __name__ == "__main__":
    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()
