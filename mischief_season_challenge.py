from mischief_db import *
from utils import *
from slack_api import *
from datetime import datetime

class MischiefSlack:
    adminSlackId = 'U05BDFHGQQL' 
    
    def __init__(self, json_data):
        self._event = json_data['event']
        self._repeat = False

        ## point values
        self.LIFT_POINTS = 2.0
        self.CARDIO_POINTS = 1.0
        self.SPRINT_POINTS = 2.0
        self.THROW_POINTS = 1.0
        self.REGEN_POINTS = 1.5
        self.PLAY_POINTS = 3.0
        self.VOLUNTEER_POINTS = 3.0
        self._additions = []
        self._reaction_added = False
        self._reaction_removed = False
        self._check_for_commands = False
        self._event_time = json_data['event_time']
        self._bot = 'bot_id' in list(self._event.keys()) and self._event['bot_id'] != None
        self._event_type = self._event['type']

        # right now tbh too scared to play around with this but i am fairly sure i can remove a chunk of it
        if 'files' in list(self._event.keys()):
            self._files = self._event['files']
        else:
            self._files = []
        if 'attachments' in list(self._event.keys()):
            self._calendar = True
            self._calendar_text = self._event['attachments'][0]['text']
            self._calendar_title = self._event['attachments'][0]['title']
        else:
            self._calendar = False
        if 'text' in list(self._event.keys()):
            self._text = self._event['text']
        else:
            self._text = ''
        self._subtype = self._event['subtype'] if 'subtype' in list(self._event.keys()) else 'message'
        if self._subtype == 'message_deleted':
            self._previous_message = self._event['previous_message']
            self._bot = True
            self._channel = self._event['channel']
            # if self._channel != 'GBR6LQBMJ':
            #     send_debug_message("Found a deleted message in channel %s written by %s" % (
            #     self._channel, self._previous_message['user']))
            #     send_debug_message(self._previous_message['text'])
        elif self._subtype == 'message_changed':
            self._check_for_commands = True
            self._previous_message = self._event['previous_message']
            self._user_id = self._previous_message['user']
            self._previous_message_text = self._previous_message['text']
            self._text = self._event['message']['text']
            self._channel = self._event['channel']
            self._ts = self._event['message']['ts']
            # send_debug_message("Found a edited message in channel %s that used to say:" % self._channel)
            # send_debug_message(self._previous_message_text)
        elif self._subtype == 'bot_message':
            self._bot = True
            self._channel_type = self._event['channel_type']
            self._channel = self._event['channel']
            self._ts = self._event['ts']
            self.user_id = self._event['bot_id']
        elif self._event['type'] == 'reaction_added' or self._event['type'] == 'reaction_removed':
            self._reaction_added = self._event['type'] == 'reaction_added'
            if not self._bot:
                self._user_id = self._event['user']
            else:
                self.user_id = self._event['bot_id']
            self._reaction_removed = not self._reaction_added
            self._item = self._event['item']
            self._reaction = self._event['reaction']
            self._channel = self._item['channel']
            self._item_ts = self._item['ts']
            self._user_id = self._event['user']
        elif self._subtype == 'message' or self._subtype == 'file_share':
            self._check_for_commands = True
            self._bot = 'bot_id' in list(self._event.keys()) and self._event['bot_id'] != None or 'user' not in list(
                self._event.keys())
            self._event_type = self._event['type']
            self._ts = self._event['ts']
            self._channel = self._event['channel']
            self._channel_type = self._event['channel_type']
            if 'files' in list(self._event.keys()):
                self._files = self._event['files']
            else:
                self._files = []

            if 'text' in list(self._event.keys()):
                self._text = self._event['text']
            else:
                self._text = ''

            if not self._bot:
                self._user_id = self._event['user']
            else:
                self.user_id = self._event['bot_id'] if 'bot_id' in list(self._event.keys()) else ''

        if self._check_for_commands:
            self.parse_text_for_mentions()

            if not self._bot:
                self._all_ids = self._mentions + [self._user_id]
            else:
                self._all_ids = self._mentions

            self.match_names_to_ids()
            self._lower_text = self._text.lower()
            self.parse_for_additions()

    def parse_text_for_mentions(self):
        text = self._text
        indicies = []
        mention_ids = []
        i = 0
        while (i < len(text)):
            temp = text.find('@', i)
            if temp == -1:
                i = len(text)
            else:
                indicies.append(temp)
                i = temp + 1
        for index in indicies:
            mention_ids.append(text[index + 1:text.find('>', index)])
        self._mentions = mention_ids

    def match_names_to_ids(self):
        mention_ids = self._all_ids
        self._all_avatars = []
        mention_names = []
        info = get_group_info()
        
        for id in mention_ids:
            for member in info['members']:
                if member['id'] == id:
                    mention_names.append(member['profile']['real_name'])
                    self._all_avatars.append(member['profile']['image_512'])
        self._all_names = mention_names
        if len(self._all_names) > 0:
            self._name = self._all_names[-1]
            self._avatar_url = self._all_avatars[-1]
        else:
            self._name = ""

    def parse_for_additions(self):
        ## TODO: update point reqs
        #DB reqs added
        self._points_to_add = 0
        self.lift_req_filled = 0
        self.cardio_req_filled = 0
        self.sprint_req_filled = 0
        self.throw_req_filled = 0
        self.regen_req_filled = 0
        self.play_req_filled = 0
        self.volunteer_req_filled = 0
        self._req_filled = 0
        if '!lift' in self._lower_text:
            self._points_to_add += self.LIFT_POINTS
            self.lift_req_filled += 1
            self._additions.append('!lift')
        if '!cardio' in self._lower_text:
            self._points_to_add += self.CARDIO_POINTS
            self.cardio_req_filled += 1
            self._additions.append('!cardio')
        if '!sprint' in self._lower_text:
            self._points_to_add += self.SPRINT_POINTS
            self.sprint_req_filled += 1
            self._additions.append('!sprint')            
        if '!throw' in self._lower_text:
            self._points_to_add += self.THROW_POINTS
            self.throw_req_filled += 1
            self._additions.append('!throw')
        if '!regen' in self._lower_text or '!yoga' in self._lower_text or '!stretch' in self._lower_text or '!pt' in self._lower_text:
            self._points_to_add += self.REGEN_POINTS
            self.regen_req_filled += 1
            self._additions.append('!regen')
        if '!goalty' in self._lower_text or '!mini' in self._lower_text or '!tryouts' in self._lower_text or '!play' in self._lower_text:
            self._points_to_add += self.PLAY_POINTS
            self.play_req_filled += 1
            self._additions.append('!play')
        if '!volunteer' in self._lower_text:
            self._points_to_add += self.VOLUNTEER_POINTS
            self.volunteer_req_filled += 1
            self._additions.append('!volunteer')

    def handle_db(self):
        #added reqs
        if not self._repeat:
            num = add_to_db(self._channel, self._all_names, self._points_to_add, self.lift_req_filled, self.cardio_req_filled, self.sprint_req_filled,
                self.throw_req_filled, self.regen_req_filled, self.play_req_filled, self.volunteer_req_filled, len(self._additions), self._all_ids)
            # for i in range(len(self._all_names)):
            #     for workout in self._additions:
            #         add_workout(self._all_names[i], self._all_ids[i], workout)
            if num == len(self._all_names):
                self.like_message()
            else:
                self.like_message(reaction='skull_and_crossbones')

    def isRepeat(self):
        self._repeat = add_num_posts([self._user_id], self._event_time, self._name, self._channel)

    def execute_commands(self):
        count = 0
        print("is repeat: ", self._repeat)
        print("lowerText: ", self._lower_text)
        if not self._repeat:
            ## put the fun stuff here
            if "!help" in self._lower_text:
                send_tribe_message("Available commands:\n!leaderboard\n!points"
                                   "\n!lift\n!cardio\n!sprint\n!throw\n!regen/!yoga/!stretch/!pt\n!play/!goalty/!mini/!tryouts\n!volunteer\n",
                                   channel=self._channel, bot_name="tracker")
            if "!points" in self._lower_text:
                send_tribe_message("Point Values:\nlift: %.1f\n cardio: %.1f\nsprint: %.1f\nthrow: %.1f\nregen: %.1f\nplay: %.1f\nvolunteer: %.1f\n"
                                   % (self.LIFT_POINTS, self.CARDIO_POINTS, self.SPRINT_POINTS, self.THROW_POINTS, self.REGEN_POINTS, 
                                    self.PLAY_POINTS, self.VOLUNTEER_POINTS), channel=self._channel)
            if "!leaderboard" in self._lower_text:
                count += 1
                to_print = collect_leaderboard(3, True)
                send_message(to_print, channel=self._channel, bot_name=self._name, url=self._avatar_url)
            if "!stats" in self._lower_text:
                count += 1
                to_print = collect_stats(3, True)
                send_message(to_print, channel=self._channel, bot_name=self._name, url=self._avatar_url)
            if '!yummy' in self._lower_text:  # displays the leaderboard for who posts the most
                count += 1
                to_print = collect_stats(1, True)
                send_message(to_print, channel=self._channel, bot_name=self._name, url=self._avatar_url)
            if '!subtract' in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                send_debug_message("SUBTRACTING: " + self._lower_text[-3:] + " FROM: " + str(self._all_names[:-1]))
                num = subtract_from_db(self._all_names[:-1], float(self._lower_text[-3:]), self._all_ids[:-1])
                print(num)
                count += 1
            if '!reset' in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                to_print = collect_stats(3, True)
                send_tribe_message(to_print, channel=self._channel, bot_name=self._name)
                reset_scores()
                send_debug_message("Resetting leaderboard")
                count += 1
            if "!create-new-table" in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                create_new_table_v2()
                send_message("Created new table", channel=self._channel, bot_name=self._name, url=self._avatar_url)
                count += 1
            insert_into_command = "!insert"
            if insert_into_command in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                parameters = self._lower_text.split()
                slackId = parameters[1]
                name = parameters[2]
                insert_into_table_v2(slackId, name)
                send_message("Inserted member", channel=self._channel, bot_name=self._name, url=self._avatar_url)
                count += 1
            if "!fill-table" in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                groupInfo = get_group_info()     
                fill_table_v2(groupInfo)
                send_message("Filled table with slack members", channel=self._channel, bot_name=self._name, url=self._avatar_url)
                count += 1
            get_table_command = "!get-table"            
            if get_table_command in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                table_name = self._lower_text.partition(get_table_command + " ")[2]
                if table_name == "":
                    table_name = None
                table = get_table(table_name)
                # message = "Table: " + "\n" + table.description()
                # send_message(message, channel=self._channel, bot_name=self._name, url=self._avatar_url)
                count += 1
            if '!silence' in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                to_print = collect_stats(1, True)
                send_tribe_message(to_print, channel=self._channel, bot_name=self._name)
                reset_talkative()
                send_debug_message("Resetting talkative")
                count += 1
            if '!add' in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                send_debug_message("ADDING: " + self._lower_text[-3:] + " TO: " + str(self._all_names[:-1]))
                num = add_to_db(self._all_names[:-1], self._lower_text[-3:], 1, self._all_ids[:-1])
                print(num)
                count += 1
            if '!self' in self._lower_text:
                req = get_req(self._user_id)
                send_message(req, channel=self._channel, bot_name=self._name)
                count += 1
            if '!test' in self._lower_text:
                pass
            if self._points_to_add > 0:
                self.like_message(reaction='angry')
            if 'groupme' in self._lower_text or 'ultiworld' in self._lower_text:
                self.like_message(reaction='thumbsdown')
            if 'good bot' in self._lower_text:
                self.like_message(reaction='blush')
            if 'bad bot' in self._lower_text:
                self.like_message(reaction='sob')    
            if 'bread' in self._lower_text:
                self.like_message(reaction='bread')
                self.like_message(reaction='moneybag')
                self.like_message(reaction='croissant')
                self.like_message(reaction='100')
            if 'nate' in self._lower_text:
                self.like_message(reaction='male_mage')
            if 'pollo' in self._lower_text:
                self.like_message(reaction='poultry_leg')
                send_tribe_message("Pingüino !!", channel=self._channel, bot_name="tracker")    
            if 'welcome bot' in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                self.like_message(reaction='crown')
                send_tribe_message("it's botney bitch", channel=self._channel, bot_name="tracker")  
                count += 1    
            if 'sloop' in self._lower_text:
                self.like_message(reaction='crown')
            if 'brabara' in self._lower_text:
                self.like_message(reaction='stache') 
            if 'spoopy' in self._lower_text or 'boo' in self._lower_text:
                self.like_message(reaction='ghost')    
            if count >= 1:
                self.like_message(reaction='jack_o_lantern')

    def like_message(self, reaction='robot_face'):
        slack_token = os.getenv('BOT_OAUTH_ACCESS_TOKEN')
        sc = SlackClient(slack_token)
        res = sc.api_call("reactions.add", name=reaction, channel=self._channel, timestamp=self._ts)
        print("response: ", res)

    def __repr__(self):
        return str(self.__dict__)
