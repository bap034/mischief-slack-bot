import os
import requests
from slackclient import SlackClient
from requests.structures import CaseInsensitiveDict

__token__ = os.getenv('BOT_OAUTH_ACCESS_TOKEN')
__auth__ = {"Authorization" : "Bearer " + __token__}

def send_message(msg, channel="#bot-beta-testing", url='', bot_name='Workout-Bot V.1'):
    slack_token = os.getenv('BOT_OAUTH_ACCESS_TOKEN')
    sc = SlackClient(slack_token)
    if url == '':
        sc.api_call("chat.postMessage", channel=channel, text=msg, username=bot_name)
    else:
        sc.api_call("chat.postMessage", channel=channel, text=msg, username=bot_name, icon_url=url)

def send_threaded_message(msg, channel="#bot_debug", thread_ts):
    slack_token = os.getenv('BOT_OAUTH_ACCESS_TOKEN')
    sc = SlackClient(slack_token)
    sc.api_call("chat.postMessage", channel=channel, text=msg, thread_ts=thread_ts)    

def send_debug_message(msg, bot_name='bot debug'):
    send_message(msg, channel="#bot-debug", bot_name=bot_name)


def send_tribe_message(msg, channel="#bot-beta-testing", bot_name="Workout-Bot V.1"):
    send_message(msg, channel, bot_name=bot_name)


def send_calendar_message(msg):
    send_message(msg, channel="#bot-beta-testing", bot_name='Workout-Bot V.1')


def get_group_info(print_values=False):
    url = "https://slack.com/api/users.list"
    combinedHeaders = {**__auth__, **{'limit' : '100'}} # Stricter rate limiting if not using pagination: https://api.slack.com/docs/rate-limits#pagination    
    json = requests.get(url, headers=combinedHeaders).json()    
    
    if print_values:
        print("Slack user list: ", json)
        
    return json


def get_emojis():
    url = 'https://slack.com/api/emoji.list'
    json = requests.get(url, headers=__auth__).json()
    return json


def open_im(user_id):
    url = "https://slack.com/api/im.open"
    json = requests.get(url, headers=__auth__).json()
    return json


def create_poll(channel_id, title, options, ts, anon):
    slack_token = os.getenv('BOT_OAUTH_ACCESS_TOKEN')
    sc = SlackClient(slack_token)
    actions = []
    block = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*" + title + "*"
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Delete Poll",
                    "emoji": True
                },
                "value": str(ts),
                "action_id": "deletePoll:" + str(ts),
                "style": "danger"
            }
        },
        {
            "type": "divider"
        }
    ]
    for i in range(0, len(options)):
        block.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": options[i]
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Vote",
                    "emoji": True
                },
                "value": str(ts),
                "action_id": "votePoll:" + str(i) + ":" + str(anon)
            }
        })
        block.append({
            "type": "divider"
        })

    block.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "DM me the current results",
                    "emoji": True
                },
                "action_id": "dmPoll:" + str(ts),
                "style": "primary"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Remind the slackers",
                    "emoji": True
                },
                "action_id": "remindPoll:" + str(ts),
                "style": "danger"
            }
        ]

    })
    print(block)
    sc.api_call("chat.postMessage", channel=channel_id, blocks=block)


def send_categories(title, channel_id, categories):
    slack_token = os.getenv('BOT_OAUTH_ACCESS_TOKEN')
    sc = SlackClient(slack_token)
    block = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*" + title + "*"
            }
        }
    ]
    for category in categories:
        if len(categories[category]) > 0:
            block.append({"type": "divider"})
            block.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*" + category + "*"
                }
            })
            names = ""
            for i in range(len(categories[category])):
                names += str(i + 1) + ") " + categories[category][i] + "\n"
            block.append({
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": names
                }
            })
        else:
            block.append({"type": "divider"})
            block.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*" + category + "*"
                }
            })
    print(block)
    sc.api_call("chat.postMessage", channel=channel_id, blocks=block)
