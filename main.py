# coolest electrical lead B)
#       *
#    /((/((((#%%/
#     #%&@((&%##*
#     (##(####%(    **
#    (%%&&&&&&&%%%#/
# /##%%&&&&&&&&&%*
#  /#%%&&&&&&&&&#
#    (%%&&&&&&&&%#*
#     #%%%&&&&&&&&#
#     (%%%%%%%&&&&&%/
#    (#%%%%%%&&&&&&%#/
#     (#%%%%%%%%%&%*
#     (#%%/     %%(
#      (#*      #%(
#      *        (#/

# mango man
#          ,,,,      ........
#        ,,,,,,,,..............
#       ,****,,*,....,.,.........
#     **/*****,,,,,,.,,.............
#    //(//*/*,,**,,,,,..,.,...........
#   /#(((//*****/**,,,*,,*,,,...........
#  (((#(#(///**/(*//**//,,,,,,,,.....,...
# /######(((#((///(/*/*****,,,,.,...... .,
# (###((####(##(((/(/*/*/*****,,,,...,.. .
# (#####((((###(#(((/////******,,,,..... ..
# *######(##(((((#(((((/***/***,,*,,,......
#  (########((((#((((((///*******,,,,,.....
#   (###(####(((#((((((/(///******,,.......
#    (######((((#(((((((/////*/**,,,,,,...,
#     (#####((((((((((//////*******,,,.....
#      ((#(#((#((((((((((/////**,,*,,,.,,,
#        (####((#(((#(///////****,,,,,,,,
#         ((((((((((///////****,,*,,,,,,
#           (#((#((/(/////****,,,,,,,,.
#             /((//////***,*,,,,,,,,
#                ******,,,,,,,,,,..
#                    .,..,,,,.

import json
import os
from time import sleep

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()
slack_token = os.getenv("SLACK_TOKEN")
client = WebClient(token=slack_token)
prev_message = None

MENTION_LIMIT = 2
emojis = ["one", "two", "three", "four", "five", "six", "seven"]


# for next variation of shitass program
# @dataclass
# class Message:
#     timestamp: str
#     channel_id: str
#     question: str
#     options: List[str]
#     user_reactions: Dict[int, Set]

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


def update_poll_message(channel_id, message_ts, options, user_reactions, question):
    global prev_message

    options_text = ""

    for i, opt in enumerate(options):
        sub_options_text = ""
        reactions = user_reactions.get(i + 1, [])

        if len(reactions) > 0:
            sub_options_text += ', '.join(f'<@{reactions[i]}>' for i in range(min(len(reactions), MENTION_LIMIT)))

        options_text += f"{i + 1}. {opt} - {sub_options_text}\n"

    poll_message = f"*{question}*\n{options_text}"
    if prev_message != poll_message:
        try:
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=poll_message
            )
            print("Poll message updated.")
            prev_message = poll_message
            try:
                with open('poll.json', 'r+') as f:
                    data = {
                        'channel_id': channel_id,
                        'message_ts': message_ts,
                        'options': options,
                        'question': question,
                    }
                    json.dump(data, f)
                    print("Poll backed up")
            except Exception as e:
                print(f"json exploded{e}")

        except SlackApiError as e:
            print(f"Error updating message: {e.response['error']}")


def track_user_reactions(reactions, user_reactions):
    for reaction in reactions:
        emoji = reaction['name']
        if emoji in emojis:
            option_index = emojis.index(emoji) + 1
            reaction['users'].remove("U07ML8X2DE1")
            user_reactions[option_index] = reaction['users']


def init_user_reactions(options):
    return {i + 1: set() for i in range(len(options))}


def main():
    try:
        with open('poll.json', 'r') as f:
            data = json.load(f)
        message_ts = data["message_ts"]
        channel_id = data["channel_id"]
        question = data["question"]
        options = data["options"]
    except Exception as e:
        with open('poll.json', 'w'):
            pass
        channel_id = "C07NBTGJ97A"
        question = "bomboclat"
        options = ["aaron", "pinto", "hhhhh", "guhhh", "fortnite", "faowehiawer", "rawehioariw"]
        print(f"JSON error {e}")
        message_ts = create_poll(channel_id, question, options)
        sleep(1)
        add_reactions(channel_id, message_ts)

    user_reactions = init_user_reactions(options)

    while True:
        current_reactions = read_reactions(channel_id, message_ts)

        if current_reactions:
            track_user_reactions(current_reactions, user_reactions)
            update_poll_message(channel_id, message_ts, options, {k: list(v) for k, v in user_reactions.items()}, question)
            sleep(0.1)


if __name__ == "__main__":
    main()
