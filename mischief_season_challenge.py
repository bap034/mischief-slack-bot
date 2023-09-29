from mischief_db import *
from utils import *
from slack_api import *
from datetime import datetime
import operator

class MischiefSlack:
    adminSlackId = 'U05BDFHGQQL' 
    fitnessChannelId = 'C05B44X6P3R'
    botDebugChannelId = 'C05PYDSSMUK'
    
    def __init__(self, json_data):
        self._event = json_data['event']
        self._repeat = False

        ## point values
        self.LIFT_POINTS = 1.0
        self.CARDIO_POINTS = 1.0
        self.SPRINT_POINTS = 1.0
        self.THROW_POINTS = 1.0
        self.REGEN_POINTS = 2.0
        self.PLAY_POINTS = 1.0
        self.VOLUNTEER_POINTS = 1.0
        self.VISUALIZE_WHITE_POINTS = 1.0
        self.VISUALIZE_RED_POINTS = 2.0
        self.VISUALIZE_BLACK_POINTS = 3.0
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
        self._req_filled = 0
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

    def handle_db(self):
        #added reqs
        if not self._repeat:
            num = add_to_db(self._channel, self._all_names, self._points_to_add, self.lift_req_filled, self.cardio_req_filled, self.sprint_req_filled,
                self.throw_req_filled, self.regen_req_filled, self.play_req_filled, self.volunteer_req_filled, self.visualize_white_req_filled, self.visualize_red_req_filled, self.visualize_black_req_filled, len(self._additions), self._all_ids)
            # for i in range(len(self._all_names)):
            #     for workout in self._additions:
            #         add_workout(self._all_names[i], self._all_ids[i], workout)
            if num == len(self._all_names):
                self.like_message()
            else:
                self.like_message(reaction='skull_and_crossbones')

    def isRepeat(self):
        self._repeat = add_num_posts([self._user_id], self._event_time, self._channel)

    def execute_commands(self):
        count = 0
        print("is repeat: ", self._repeat)
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
                 !cardio/!bike
                 !sprint
                 !throw
                 !regen/!yoga/!stretch/!pt
                 !play/!goalty/!mini/!tryouts
                 !volunteer
                 !visualize-[white/red/black]""", channel=self._channel, bot_name="tracker")
            if "!points" in self._lower_text:
                send_tribe_message("Point Values:\nlift: %.1f\ncardio: %.1f\nsprint: %.1f\nthrow: %.1f\nregen: %.1f\nplay: %.1f\nvolunteer: %.1f\nvisualize-white: %.1f\nvisualize-red: %.1f\nvisualize-black: %.1f"
                                   % (self.LIFT_POINTS, self.CARDIO_POINTS, self.SPRINT_POINTS, self.THROW_POINTS, self.REGEN_POINTS, 
                                    self.PLAY_POINTS, self.VOLUNTEER_POINTS, self.VISUALIZE_WHITE_POINTS, self.VISUALIZE_RED_POINTS, self.VISUALIZE_BLACK_POINTS), channel=self._channel)
            if "!leaderboard" in self._lower_text:
                count += 1
                leaderboard = get_table()
                to_print = self.getLeaderboardText(leaderboard)
                send_message(to_print, channel=self._channel, bot_name=self._name, url=self._avatar_url)
            if "!battle-of-the-bays" in self._lower_text:
                count += 1
                leaderboard = get_table()
                to_print = self.getBattleOfBaysLeaderboardText(leaderboard)
                send_message(to_print, channel=self._channel, bot_name=self._name, url=self._avatar_url)
            if "!stats" in self._lower_text:
                count += 1
                leaderboard = get_table()
                to_print = "Stats:\n"
                for x in range(0, len(leaderboard)):
                    if leaderboard[x]['score'] <= 0:
                        continue
                        
                    to_print += "{0:>2}) {1:<20} `points: {2}` `lifts: {3}` `cardio: {4}` `sprints: {5}` `throws: {6}` `regen: {7}` `playing: {8}` `volunteer: {9}` `visualize-white: {10}` `visualize-red: {11}` `visualize-black: {12}` \n".format(
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
                        leaderboard[x]['num_visualize_black']
                    )
                send_message(to_print, channel=self._channel, bot_name=self._name, url=self._avatar_url)
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
            if 'breath' in self._lower_text:
                self.like_message(reaction='wind_blowing_face')
                self.like_message(reaction='phellon-inside-voice')
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
                  record['num_visualize_black'] * self.VISUALIZE_BLACK_POINTS]
        newScore = sum(scores)
        print("Name: %s Score: %d -> %d" % (name, oldScore, newScore))
        return newScore

    def getBattleOfBaysLeaderboardText(self, table):
        eastBaySlackIds = ['U05BAUGSUAX',    # beth
                           'U05BB2SN49Y',    # munis
                           'U05KVP65DHQ',    # cody
                           'U05B4CVD0T0',    # phellon
                           'U05BFAWCLP4',    # gu
                           'U05BB2S8KDY',    # cory
                           'U05BU08K8D7',    # lupa
                           'U05BDFHGQQL',    # brett
                           'U05B84JNRPF',    # viv
                           #'U05BAUGDLCB',    # berry                           
                           'U05B84JA353']    # dre
                          
        cityBaySlackIds = ['U05AWGDEKF1',    # vicki
                           'U05BRFCEYLW',    # josh
                           'U05BDFHA1V2',    # craw
                           'U05MT0UE144',    # james
                           'U05BF779VEX',    # mars
                           'U05B8LZC154',    # jess
                           'U05BCCP2N13',    # addy
                           'U05C2D8GFA8',    # liam
                           'U05BPMJ727K',    # manks
                           'U05BFAW8Z50',    # cass
                           'U05CE8N36D8',    # allan
                           # 'U05C0PGPGQY',    # nate
                           'U05B4CV6CS2',    # jeff
                           'U05BB2SF4US',    # mitch
                           'U05C526NQ2U',    # sonja
                           'U05BPMJDLUR']    # pin
        
        southBaySlackIds = ['U05BDFH3D3N',    # chris lung
                            'U05C5261Z0Q',    # milan
                            'U05BAUGL2QK',    # lily
                            'U05B84JGC93',    # kyle
                            'U05C0PH11CG',    # robin
                            'U05BG9U74V9',    # jackie
                            'U05AWGCPGJ3',    # kitty  
                            'U05ML4F8284']    # dylan                                                    
        
        outerBaySlackIds = []    
        
        # Add overall ranking
        table.sort(key=operator.itemgetter('score'), reverse=True)
        for x in range(0, len(table)):
            table[x]['rank'] = x+1
        
        eastBayRecords = []
        cityBayRecords = []
        southBayRecords = []
        outerBayRecords = []
        
        for record in table:
            if record['score'] == 0:
                continue
            if record['slack_id'] in eastBaySlackIds:
                eastBayRecords.append(record)
            elif record['slack_id'] in cityBaySlackIds:
                cityBayRecords.append(record)
            elif record['slack_id'] in southBaySlackIds:
                southBayRecords.append(record)
            elif record['slack_id'] in outerBaySlackIds:
                outerBayRecords.append(record)
    
        eastBayRecords.sort(key=operator.itemgetter('score'), reverse=True)
        cityBayRecords.sort(key=operator.itemgetter('score'), reverse=True)
        southBayRecords.sort(key=operator.itemgetter('score'), reverse=True)
        outerBayRecords.sort(key=operator.itemgetter('score'), reverse=True)
        
        eastBayScoreText = self.getScoreText(eastBayRecords)
        cityBayScoreText = self.getScoreText(cityBayRecords)
        southBayScoreText = self.getScoreText(southBayRecords)
        outerBayScoreText = self.getScoreText(outerBayRecords)
        
        leaderboardText = "Battle of the Bays Leaderboard:"
        leaderboardText += "\n\n"
        leaderboardText += "`Beast Bay: {scoreText}`".format(scoreText=eastBayScoreText)
        leaderboardText += "\n"
        leaderboardText += self.getLeaderboardText(eastBayRecords, showZero=True)
        
        leaderboardText += "\n\n"
        leaderboardText += "`City Bay: {scoreText}`".format(scoreText=cityBayScoreText)
        leaderboardText += "\n"
        leaderboardText += self.getLeaderboardText(cityBayRecords, showZero=True)
        
        leaderboardText += "\n\n"
        leaderboardText += "`South Bay: {scoreText}`".format(scoreText=southBayScoreText)
        leaderboardText += "\n"
        leaderboardText += self.getLeaderboardText(southBayRecords, showZero=True)
        
        # leaderboardText += "\n\n"
        # leaderboardText += "`Outer Bay: {scoreText}`".format(scoreText=outerBayScoreText)
        # leaderboardText += "\n"
        # leaderboardText += self.getLeaderboardText(outerBayRecords, showZero=True)
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
