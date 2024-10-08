from mischief_db import *
from utils import *
from slack_api import *
from datetime import datetime
import operator

class MischiefSlack:
    adminSlackId = 'U0750FXN07N' 
    fitnessChannelId = 'C074RMR2FLN'
    botDebugChannelId = 'C07L51TBWFJ'
    
    def __init__(self, json_data):
        self._event = json_data['event']
        self._repeat = False

        ## point values
        self.LIFT_POINTS = 0.0
        self.CARDIO_POINTS = 0.0
        self.SPRINT_POINTS = 0.0
        self.THROW_POINTS = 1.0
        self.REGEN_POINTS = 1.0
        self.PLAY_POINTS = 0.0
        self.VOLUNTEER_POINTS = 0.0
        self.VISUALIZE_WHITE_POINTS = 4.0
        self.VISUALIZE_RED_POINTS = 8.0
        self.VISUALIZE_BLACK_POINTS = 6.0
        self.CROSS_POD = 2.0
        self.DINNER = 1.0
        self.TRUDDY_CHECK_IN = 3.0
        self.FILM = 1.0
        self.PUMP_UP = 1.0
        self._additions = []
        self._reaction_added = False
        self._reaction_removed = False
        self._check_for_commands = False
        self._event_time = json_data['event_time']
        self._bot = 'bot_id' in list(self._event.keys()) and self._event['bot_id'] != None
        self._event_type = self._event['type']

        # assume that if `message_changed` but no `edited`, then was automated url edit and want to skip this message (aka mark as repeat)
        if 'subtype' in self._event and self._event['subtype'] == 'message_changed':
            if 'message' in self._event and not ('edited' in self._event['message']): 
                self._bot = True
        
        if 'ts' in self._event:
            self._ts = self._event['ts']
            self._thread_ts = self._ts # if no `thread_ts`, then it's the parent message so to send a reply we want to use that message's `ts` 
        if 'thread_ts' in self._event:
            self._thread_ts = self._event['thread_ts']                    

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

        if self._check_for_commands and (self._channel == MischiefSlack.fitnessChannelId or self._channel == MischiefSlack.botDebugChannelId):
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
            if 'members' in info:
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
        self.visualize_white_req_filled = 0
        self.visualize_red_req_filled = 0
        self.visualize_black_req_filled = 0
        self.cross_pod_req_filled = 0
        self.dinner_req_filled= 0
        self.truddy_check_in_req_filled = 0
        self.film_req_filled = 0
        self.pump_up_req_filled = 0
        self._req_filled_req_filled = 0
        if '!lift' in self._lower_text:
            self._points_to_add += self.LIFT_POINTS
            self.lift_req_filled += 1
            self._additions.append('!lift')
        if '!cardio' in self._lower_text or '!bike' in self._lower_text or '!breathe' in self._lower_text:
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
        if '!visualize-white' in self._lower_text:
            self._points_to_add += self.VISUALIZE_WHITE_POINTS
            self.visualize_white_req_filled += 1
            self._additions.append('!visualize-white')
        if '!visualize-red' in self._lower_text:
            self._points_to_add += self.VISUALIZE_RED_POINTS
            self.visualize_red_req_filled += 1
            self._additions.append('!visualize-red')
        if '!visualize-black' in self._lower_text:
            self._points_to_add += self.VISUALIZE_BLACK_POINTS
            self.visualize_black_req_filled += 1
            self._additions.append('!visualize-black')
        if '!cross-pod' in self._lower_text:
            self._points_to_add += self.CROSS_POD
            self.cross_pod_req_filled += 1
            self._additions.append('!cross-pod')    
        if '!dinner' in self._lower_text:
            self._points_to_add += self.DINNER
            self.dinner_req_filled += 1
            self._additions.append('!dinner')    
        if '!truddy-check-in' in self._lower_text:
            self._points_to_add += self.TRUDDY_CHECK_IN
            self.truddy_check_in_req_filled += 1
            self._additions.append('!truddy-check-in')    
        if '!film' in self._lower_text:
            self._points_to_add += self.FILM
            self.film_req_filled += 1
            self._additions.append('!film')    
        if '!pump-up' in self._lower_text:
            self._points_to_add += self.PUMP_UP
            self.pump_up_req_filled += 1
            self._additions.append('!pump-up')    
        

    def handle_db(self):
        #added reqs
        if not self._repeat:
            num = add_to_db(self._channel, 
                            self._all_names, 
                            self._points_to_add, 
                            self.lift_req_filled, 
                            self.cardio_req_filled, 
                            self.sprint_req_filled,
                            self.throw_req_filled, 
                            self.regen_req_filled, 
                            self.play_req_filled, 
                            self.volunteer_req_filled, 
                            self.visualize_white_req_filled, 
                            self.visualize_red_req_filled, 
                            self.visualize_black_req_filled, 
                            self.cross_pod_req_filled,
                            self.dinner_req_filled,
                            self.truddy_check_in_req_filled,
                            self.film_req_filled,
                            self.pump_up_req_filled,
                            len(self._additions), 
                            self._all_ids)
            # for i in range(len(self._all_names)):
            #     for workout in self._additions:
            #         add_workout(self._all_names[i], self._all_ids[i], workout)
            if num == len(self._all_names):
                self.like_message()
                message = "Logged: `%s pts` from `%s`" % (self._points_to_add, self._additions)
                
                if len(self._all_names) > 1:
                    message += " to `%s`" % self._all_names
                    
                send_threaded_message(message, self._channel, self._thread_ts)
            else:
                self.like_message(reaction='skull_and_crossbones')

    def isRepeat(self):
        self._repeat = add_num_posts([self._user_id], self._event_time, self._channel)

    def execute_commands(self):
        count = 0
        print("is repeat: ", self._repeat)
        print("text: ", self._text)
        print("lowerText: ", self._lower_text)
        if not self._repeat:
            ## put the fun stuff here
            if "!help" in self._lower_text:
                send_tribe_message("""
                Available commands:
                 !leaderboard
                 !battle-of-the-bays
                 !points
                 !lift
                 !cardio/!bike/!breathe
                 !sprint
                 !throw
                 !regen/!yoga/!stretch/!pt
                 !play/!goalty/!mini/!tryouts
                 !volunteer
                 !visualize-[white/red/black]
                 !cross-pod
                 !dinner
                 !truddy-check-in
                 !film
                 !pump-up
                 """, channel=self._channel, bot_name="tracker")
            if "!points" in self._lower_text:
                send_tribe_message("""
                Point Values:
                    lift: %.1f
                    cardio: %.1f
                    sprint: %.1f
                    throw: %.1f
                    regen: %.1f
                    play: %.1f
                    volunteer: %.1f
                    visualize-white: %.1f
                    visualize-red: %.1f
                    visualize-black: %.1f
                    cross-pod: %.1f
                    dinner: %.1f
                    truddy-check-in: %.1f
                    film: %.1f
                    pump-up: %.1f
                    """ % (self.LIFT_POINTS, 
                              self.CARDIO_POINTS, 
                              self.SPRINT_POINTS, 
                              self.THROW_POINTS, 
                              self.REGEN_POINTS,
                              self.PLAY_POINTS, 
                              self.VOLUNTEER_POINTS, 
                              self.VISUALIZE_WHITE_POINTS, 
                              self.VISUALIZE_RED_POINTS, 
                              self.VISUALIZE_BLACK_POINTS,
                              self.CROSS_POD,
                              self.DINNER,
                              self.TRUDDY_CHECK_IN,
                              self.FILM,
                              self.PUMP_UP), channel=self._channel)
            if "!leaderboard" in self._lower_text:
                count += 1
                leaderboard = get_table()
                to_print = self.getLeaderboardText(leaderboard)
                send_message(to_print, channel=self._channel)
            if "!battle-of-the-bays" in self._lower_text:
                count += 1
                leaderboard = get_table()
                to_print = self.getBattleOfBaysLeaderboardText(leaderboard)
                send_message(to_print, channel=self._channel)
            if "!stats" in self._lower_text:
                count += 1
                leaderboard = get_table()
                to_print = "Stats:\n"
                for x in range(0, len(leaderboard)):
                    if leaderboard[x]['score'] <= 0:
                        continue
                        
                    to_print += "{0:>2}) {1:<20} `points: {2}` `lifts: {3}` `cardio: {4}` `sprints: {5}` `throws: {6}` `regen: {7}` `playing: {8}` `volunteer: {9}` `visualize-white: {10}` `visualize-red: {11}` `visualize-black: {12}` `cross pod: {13}` `dinner: {14}` `truddy check-in: {15}` `film: {16}` `pump-up: {17}` \n".format(
                        x + 1, 
                        leaderboard[x]['name'],
                        leaderboard[x]['score'],
                        leaderboard[x]['num_lifts'], 
                        leaderboard[x]['num_cardio'],
                        leaderboard[x]['num_sprints'],
                        leaderboard[x]['num_throws'], 
                        leaderboard[x]['num_regen'],  
                        leaderboard[x]['num_play'],   
                        leaderboard[x]['num_volunteer'],
                        leaderboard[x]['num_visualize_white'], 
                        leaderboard[x]['num_visualize_red'],
                        leaderboard[x]['num_visualize_black'],
                        leaderboard[x]['num_cross_pod'],
                        leaderboard[x]['num_dinner'],
                        leaderboard[x]['num_truddy_check_in'],
                        leaderboard[x]['num_film'],
                        leaderboard[x]['num_pump_up']
                    )
                send_message(to_print, channel=self._channel)
            if '!yummy' in self._lower_text:  # displays the leaderboard for who posts the most
                count += 1
                to_print = collect_stats(1, True)
                send_message(to_print, channel=self._channel, bot_name=self._name, url=self._avatar_url)
            if '!subtract' in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                # format is "!subtract @user #.#" <-- specifically looks for the last 3 characters to determine how many points to subtract via `self._lower_text[-3:]`
                send_debug_message("SUBTRACTING: " + self._lower_text[-3:] + " FROM: " + str(self._all_names[:-1]))
                num = subtract_from_db(self._all_names[:-1], float(self._lower_text[-3:]), self._all_ids[:-1])
                print(num)
                count += 1
            if '!recalculate-scores' in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                send_debug_message("Recalculating scores")
                table = get_table()
                userScores = {}
                for record in table:
                    newScore = self.recalculateScore(record)
                    userScores[record['slack_id']] = newScore

                print("New User Scores: ", userScores)
                if len(userScores) > 0:
                    update_scores(userScores)
                send_debug_message("Successfully recalculated scores")
                count += 1
            if '!reset' in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                to_print = collect_stats(3, True)
                send_tribe_message(to_print, channel=self._channel, bot_name=self._name)
                reset_scores()
                send_debug_message("Resetting leaderboard")
                count += 1
            if "!create-new-table" in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                create_new_table_v2()
                send_message("Created new table", channel=self._channel)
                count += 1
            insert_column_command = "!insert-new-column"
            if insert_column_command in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                parameters = self._lower_text.split()
                col_name = parameters[1]                
                insert_column(col_name)
                send_message("Inserted column %s" % col_name, channel=self._channel)
                count += 1
            insert_into_command = "!insert"
            if insert_into_command in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                parameters = self._lower_text.split()
                slackId = parameters[1]
                name = parameters[2]
                insert_into_table_v2(slackId, name)
                send_message("Inserted member", channel=self._channel)
                count += 1
            if "!fill-table" in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                groupInfo = get_group_info(True)     
                fill_table_v2(groupInfo)
                send_message("Filled table with slack members", channel=self._channel)
                count += 1
            get_table_command = "!get-table"            
            if get_table_command in self._lower_text and self._user_id == MischiefSlack.adminSlackId:
                table_name = self._lower_text.partition(get_table_command + " ")[2]
                if table_name == "":
                    table_name = None
                table = get_table(table_name)

                tableString = "Table: \n"
                for record in table:                
                    tableString += '\n' + '`' + str(dict(record)) + '`'
                send_debug_message(tableString)
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
            if '!thread-test' in self._lower_text:
                send_threaded_message("Thread response test", self._channel, self._thread_ts)
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
                self.like_message(reaction='concerned-sloop')
            if 'brabara' in self._lower_text:
                self.like_message(reaction='robin-cheese') 
            if 'spoopy' in self._lower_text or 'boo' in self._lower_text:
                self.like_message(reaction='ghost')    
            if 'breath' in self._lower_text:
                self.like_message(reaction='phellon-inside-voice')
            if 'follow along' in self._lower_text:
                send_threaded_message("F O L L O W A L O N G", self._channel, self._thread_ts)
            if count >= 1:
                self.like_message(reaction='jack_o_lantern')

    def recalculateScore(self, record):
        name = record['name']
        oldScore = record['score']
        scores = [record['num_lifts'] * self.LIFT_POINTS,
                  record['num_cardio'] * self.CARDIO_POINTS,
                  record['num_sprints'] * self.SPRINT_POINTS,
                  record['num_throws'] * self.THROW_POINTS,
                  record['num_regen'] * self.REGEN_POINTS,
                  record['num_play'] * self.PLAY_POINTS,
                  record['num_volunteer'] * self.VOLUNTEER_POINTS,
                  record['num_visualize_white'] * self.VISUALIZE_WHITE_POINTS,
                  record['num_visualize_red'] * self.VISUALIZE_RED_POINTS,
                  record['num_visualize_black'] * self.VISUALIZE_BLACK_POINTS,
                  record['num_cross_pod'] * self.CROSS_POD,
                  record['num_dinner'] * self.DINNER,
                  record['num_truddy_check_in'] * self.TRUDDY_CHECK_IN,
                  record['num_film'] * self.FILM,
                  record['num_pump_up'] * self.PUMP_UP]
        newScore = sum(scores)
        print("Name: %s Score: %d -> %d" % (name, oldScore, newScore))
        return newScore

    def getBattleOfBaysLeaderboardText(self, table):
        groupA = [
        	'U074Y1Y3LAE',         # Adeleen Khem
        	'U075A6KJE9G',         # Beth's Chris’ Steakhouse
        	'U074UNSAMHU',         # Robin Meyers
        	'U075AMLTA8H',         # sonja
        	'U074Y1Y264A',         # Keenan
        	'U074X5F5CMP'          # Liam Jay
        ]	        
        groupB = [
        	'U074V4RJ4ER',         # Ailita Eddy (she/they)
        	'U0753RXTN8L',         # Christine Chen
        	'U075157SC57',         # Mitchell Sayasene
        	'U074X5F1ML1',         # Jaclyn Wataoka
        	'U075C9UL552',         # Charlize
        	'U07516KU4G1'          # Beth
        ]        
        groupC = [
        	'U075M1WQ20G',         # Kitty Cheung
        	'U0750FXN07N',         # prett
        	'U075DV39A77',         # Cory Fauver
        	'U0753RXJ9EG',         # Lily
        	'U074V4RGSVB',         # Will
        	'U074FHZLEHK'          # Kyle Johnson
        ]        
        groupD = [
        	'U074LV628JG',         # phellon
        	'U0760TH22M9',         # Vicki
        	'U074S9UM9KR',         # Conor Bauman
        	'U074XU25PV1',         # Jess Brownschidle
        	'U074Y1Y7K0A',         # Aaron Rosenthal
        	'U0750FXEDQU'          # Chris Bernard
        ]        
        groupE = [
        	'U07516LBWMP',         # julia mankoff
        	'U074VHK1DRV',         # Dylan Burns
        	'U0750MZS90C',         # Milan Moslehi
        	'U074W9ZUALR',         # Pin-Wen Wang
        	'U075M46BC4E',         # Patrick Xu
        	'U075792JJJU'          # Cody Kirkland
        ]        
        groupF = [
        	'U0750FY3GKE',         # andrea dree dre
        	'U074HEY4SKH',         # Wyatt Berreman
        	'U074R0WJBT6',         # Chris Lung
        	'U07630Q6RJ7',         # he’s behind that paper i swear
        	'U074JBW9NF5'          # Andrew Berry
        	# 'U07B59DDW5U',         # Vivian Chu
        	# 'U074LV60PFE'          # Nathan Young
        ]        
        eastBaySlackIds = []
        cityBaySlackIds = []
        southBaySlackIds = []
        outerBaySlackIds = []   
        
        # Add overall ranking
        table.sort(key=operator.itemgetter('score'), reverse=True)
        for x in range(0, len(table)):
            table[x]['rank'] = x+1

        groupRecordsA = []
        groupRecordsB = []
        groupRecordsC = []
        groupRecordsD = []
        groupRecordsE = []
        groupRecordsF = []
        eastBayRecords = []
        cityBayRecords = []
        southBayRecords = []
        outerBayRecords = []
        
        for record in table:
            if record['score'] < 0:
                continue
            if record['slack_id'] in eastBaySlackIds:
                eastBayRecords.append(record)
            elif record['slack_id'] in cityBaySlackIds:
                cityBayRecords.append(record)
            elif record['slack_id'] in southBaySlackIds:
                southBayRecords.append(record)
            elif record['slack_id'] in outerBaySlackIds:
                outerBayRecords.append(record)
            elif record['slack_id'] in groupA:
                groupRecordsA.append(record)
            elif record['slack_id'] in groupB:
                groupRecordsB.append(record)
            elif record['slack_id'] in groupC:
                groupRecordsC.append(record)
            elif record['slack_id'] in groupD:
                groupRecordsD.append(record)
            elif record['slack_id'] in groupE:
                groupRecordsE.append(record)
            elif record['slack_id'] in groupF:
                groupRecordsF.append(record)
            
                
    
        eastBayRecords.sort(key=operator.itemgetter('score'), reverse=True)
        cityBayRecords.sort(key=operator.itemgetter('score'), reverse=True)
        southBayRecords.sort(key=operator.itemgetter('score'), reverse=True)
        outerBayRecords.sort(key=operator.itemgetter('score'), reverse=True)
        groupRecordsA.sort(key=operator.itemgetter('score'), reverse=True)
        groupRecordsB.sort(key=operator.itemgetter('score'), reverse=True)
        groupRecordsC.sort(key=operator.itemgetter('score'), reverse=True)
        groupRecordsD.sort(key=operator.itemgetter('score'), reverse=True)
        groupRecordsE.sort(key=operator.itemgetter('score'), reverse=True)
        groupRecordsF.sort(key=operator.itemgetter('score'), reverse=True)
        
        eastBayScoreText = self.getScoreText(eastBayRecords)
        cityBayScoreText = self.getScoreText(cityBayRecords)
        southBayScoreText = self.getScoreText(southBayRecords)
        outerBayScoreText = self.getScoreText(outerBayRecords)
        groupAScoreText = self.getScoreText(groupRecordsA)
        groupBScoreText = self.getScoreText(groupRecordsB)
        groupCScoreText = self.getScoreText(groupRecordsC)
        groupDScoreText = self.getScoreText(groupRecordsD)
        groupEScoreText = self.getScoreText(groupRecordsE)
        groupFScoreText = self.getScoreText(groupRecordsF)
        
        leaderboardText = "Battle of the (Buddy Truddy) Bays Leaderboard:"
        # leaderboardText += "\n\n"
        # leaderboardText += "`Beast Bay: {scoreText}`".format(scoreText=eastBayScoreText)
        # leaderboardText += "\n"
        # leaderboardText += self.getLeaderboardText(eastBayRecords, showZero=True)
        
        # leaderboardText += "\n\n"
        # leaderboardText += "`City Bay: {scoreText}`".format(scoreText=cityBayScoreText)
        # leaderboardText += "\n"
        # leaderboardText += self.getLeaderboardText(cityBayRecords, showZero=True)
        
        # leaderboardText += "\n\n"
        # leaderboardText += "`South Bay: {scoreText}`".format(scoreText=southBayScoreText)
        # leaderboardText += "\n"
        # leaderboardText += self.getLeaderboardText(southBayRecords, showZero=True)
        
        # leaderboardText += "\n\n"
        # leaderboardText += "`Outer Bay: {scoreText}`".format(scoreText=outerBayScoreText)
        # leaderboardText += "\n"
        # leaderboardText += self.getLeaderboardText(outerBayRecords, showZero=True)

        leaderboardText += "\n\n"
        leaderboardText += "`Group A: {scoreText}`".format(scoreText=groupAScoreText)
        leaderboardText += "\n"
        leaderboardText += self.getLeaderboardText(groupRecordsA, showZero=True)

        leaderboardText += "\n\n"
        leaderboardText += "`Group B: {scoreText}`".format(scoreText=groupBScoreText)
        leaderboardText += "\n"
        leaderboardText += self.getLeaderboardText(groupRecordsB, showZero=True)

        leaderboardText += "\n\n"
        leaderboardText += "`Group C: {scoreText}`".format(scoreText=groupCScoreText)
        leaderboardText += "\n"
        leaderboardText += self.getLeaderboardText(groupRecordsC, showZero=True)

        leaderboardText += "\n\n"
        leaderboardText += "`Group D: {scoreText}`".format(scoreText=groupDScoreText)
        leaderboardText += "\n"
        leaderboardText += self.getLeaderboardText(groupRecordsD, showZero=True)

        leaderboardText += "\n\n"
        leaderboardText += "`Group E: {scoreText}`".format(scoreText=groupEScoreText)
        leaderboardText += "\n"
        leaderboardText += self.getLeaderboardText(groupRecordsE, showZero=True)

        leaderboardText += "\n\n"
        leaderboardText += "`Group F: {scoreText}`".format(scoreText=groupFScoreText)
        leaderboardText += "\n"
        leaderboardText += self.getLeaderboardText(groupRecordsF, showZero=True)
        
        return leaderboardText

    def getLeaderboardText(self, records, showZero=False):
        to_print = "Leaderboard:"
        for x in range(0, len(records)):
            record = records[x]
            if not showZero and record['score'] <= 0:
                continue
            if 'rank' in record:
                rank = record['rank']
            else:
                rank = x + 1
            to_print += '\n%d) %s with %.1f points' % (rank, 
                                                       record['name'],
                                                       record['score'])
        return to_print
    
    def getScoreText(self, records):
        scoreSum = sum(record['score'] for record in records)
        numRecords = len(records)
        if numRecords == 0:
            finalScore = 0
        else:
            finalScore = float(scoreSum)/float(numRecords)
        combinedScoreText = "{score:.2f} = {sum}pts / {count}ppl".format(
            sum = scoreSum,
            count = numRecords,
            score = finalScore
        )
        return combinedScoreText
    
    def like_message(self, reaction='robot_face'):
        slack_token = os.getenv('BOT_OAUTH_ACCESS_TOKEN')
        sc = SlackClient(slack_token)
        res = sc.api_call("reactions.add", name=reaction, channel=self._channel, timestamp=self._ts)
        print("response: ", res)

    def __repr__(self):
        return str(self.__dict__)
