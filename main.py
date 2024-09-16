import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from time import sleep
from dotenv import load_dotenv

load_dotenv()
slack_token = os.getenv("SLACK_TOKEN")
client = WebClient(token=slack_token)

MENTION_LIMIT = 1


def create_poll(channel_id, question, options):
    try:
        options_text = "\n".join(f"{i + 1}. {opt}" for i, opt in enumerate(options))
        poll_message = f"*{question}*\n{options_text}"

        response = client.chat_postMessage(
            channel=channel_id,
            text=poll_message
        )

        return response["ts"]

    except SlackApiError as e:
        print(f"Error creating poll: {e.response['error']}")


def read_reactions(channel_id, message_ts):
    try:
        response = client.reactions_get(
            channel=channel_id,
            full=True,
            timestamp=message_ts,
        )
        return response['message'].get('reactions', [])
    except SlackApiError as e:
        print(f"Error reading reactions: {e.response['error']}")


def add_reactions(channel_id, message_ts):
    emojis = ["one", "two", "three", "four", "five", "six", "seven"]
    for emoji in emojis:
        try:
            client.reactions_add(
                channel=channel_id,
                name=emoji,
                timestamp=message_ts
            )
            print(f"Added reaction '{emoji}'.")
        except SlackApiError as e:
            print(f"Error adding reaction: {e.response['error']}")


def update_poll_message(channel_id, message_ts, options, user_reactions):
    options_text = "\n".join(
        f"{i + 1}. {opt} - {', '.join(user_reactions.get(i + 1, []))}" for i, opt in enumerate(options))
    poll_message = f"*{question}*\n{options_text}"

    try:
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=poll_message
        )
        print("Poll message updated.")
    except SlackApiError as e:
        print(f"Error updating message: {e.response['error']}")


def track_user_reactions(reactions, user_reactions, reaction_queues):
    for reaction in reactions:
        emoji = reaction['name']
        if emoji in ["one", "two", "three", "four", "five", "six", "seven"]:
            option_index = ["one", "two", "three", "four", "five", "six", "seven"].index(emoji) + 1
            for user in reaction['users']:
                if user != "U07ML8X2DE1":
                    if len(user_reactions[option_index]) < MENTION_LIMIT:
                        user_reactions[option_index].add(f"<@{user}>")
                        reaction_queues[option_index].append(user)


def remove_user_reactions(previous_reactions, current_reactions, user_reactions, reaction_queues):
    current_reaction_users = {
        emoji: {user for reaction in current_reactions if reaction['name'] == emoji for user in reaction['users']} for
        emoji in ["one", "two", "three", "four", "five", "six", "seven"]}

    for reaction in previous_reactions:
        emoji = reaction['name']
        if emoji in ["one", "two", "three", "four", "five", "six", "seven"]:
            option_index = ["one", "two", "three", "four", "five", "six", "seven"].index(emoji) + 1
            for user in reaction['users']:
                if user != "U07ML8X2DE1":
                    if user not in current_reaction_users[emoji]:
                        user_reactions[option_index].discard(f"<@{user}>")
                        reaction_queues[option_index].remove(user)

                        if reaction_queues[option_index]:
                            next_user = reaction_queues[option_index].pop(0)
                            user_reactions[option_index].add(f"<@{next_user}>")


def init_user_reactions(options):
    return {i + 1: set() for i in range(len(options))}


def init_reaction_queues(options):
    return {i + 1: [] for i in range(len(options))}


if __name__ == "__main__":
    channel_id = "C07NBTGJ97A"
    question = "bomboclat"
    options = ["aaron", "pinto", "hhhhh", "guhhh", "fortnite", "faowehiawer", "rawehioariw"]

    message_ts = create_poll(channel_id, question, options)
    sleep(1)
    add_reactions(channel_id, message_ts)

    user_reactions = init_user_reactions(options)
    reaction_queues = init_reaction_queues(options)

    previous_reactions = []

    while True:
        current_reactions = read_reactions(channel_id, message_ts)
        if current_reactions:
            track_user_reactions(current_reactions, user_reactions, reaction_queues)
            update_poll_message(channel_id, message_ts, options, {k: list(v) for k, v in user_reactions.items()})
            remove_user_reactions(previous_reactions, current_reactions, user_reactions, reaction_queues)
            update_poll_message(channel_id, message_ts, options, {k: list(v) for k, v in user_reactions.items()})
            previous_reactions = current_reactions

        sleep(2)