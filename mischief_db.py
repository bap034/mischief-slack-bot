import os
import urllib.parse
import urllib.request
import psycopg2

from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from slack_api import *

from flask import Flask, request, jsonify, make_response

app = Flask(__name__)
__token__ = os.getenv('BOT_OAUTH_ACCESS_TOKEN')
__auth__ = {"Authorization" : "Bearer " + __token__}
__table_name__  = "mischief_data"

# START SQL Connection Methods ----------------------------------------------------
# Always pair this method with the `commitAndCloseSQLConnection()` to properly close completed connections
def getSQLConnection():
    try:
        urllib.parse.uses_netloc.append("postgres")
        url = urllib.parse.urlparse(os.environ["DATABASE_URL"])
        conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        return conn
        
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(error)
        raise error

def commitAndCloseSQLConnection(conn):
    conn.commit()
    conn.cursor().close()
    conn.close()
# END SQL Connection Methods -------------------------------------------------------    

def create_new_table_v2():
    try:    
        sqlConnection = getSQLConnection()
        cursor = sqlConnection.cursor()
    
        print("Dropping existing table: ", __table_name__)
        dropCommand = "DROP TABLE IF EXISTS " + __table_name__
        cursor.execute(dropCommand) 
        print("Successfully dropped existing table: ", __table_name__)
        
        print("Creating new table v2: ", __table_name__)
        createCommand = """
            CREATE TABLE {table_name} (
                slack_id CHAR(11),
                name text,
                score numeric(4, 1), 
                last_post DATE,
                num_posts SMALLINT, 
                num_lifts SMALLINT, 
                num_cardio SMALLINT, 
                num_sprints SMALLINT, 
                num_throws SMALLINT, 
                num_regen SMALLINT,
                num_play SMALLINT, 
                num_volunteer SMALLINT,
                num_visualize_white SMALLINT,
                num_visualize_red SMALLINT,
                num_visualize_black SMALLINT,
                num_cross_pod SMALLINT,
                num_dinner SMALLINT,
                num_truddy_check_in SMALLINT,
                num_film SMALLINT,
                num_pump_up SMALLINT                
            )
        """.format(
            table_name = __table_name__
        )
        cursor.execute(createCommand)
        print("Successfully created new table: ", __table_name__)
    
        commitAndCloseSQLConnection(sqlConnection)   
        return True
        
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        send_debug_message(error)
        return False

def insert_into_table_v2(slackId, name):
    print("Insert into Table %s V2 WITH: " % __table_name__)
    try:
        sqlConnection = getSQLConnection()
        cursor = sqlConnection.cursor()
        
        print("Inserting member: %s id: %s" % (name, slackId))                        
        insertCommand = """
            INSERT INTO {table_name} VALUES (
                '{slack_id}',
                '{name}', 
                {score}, 
                {last_post},
                {num_posts}, 
                {num_lifts}, 
                {num_cardio}, 
                {num_sprints}, 
                {num_throws}, 
                {num_regen},
                {num_play}, 
                {num_volunteer},
                {num_visualize_white},
                {num_visualize_red},
                {num_visualize_black},
                {num_cross_pod},
                {num_dinner},
                {num_truddy_check_in},
                {num_film},
                {num_pump_up}
            )
        """.format(
            table_name = __table_name__,
            slack_id = slackId,
            name = name, 
            score = 0, 
            last_post = "now()",
            num_posts = 0, 
            num_lifts = 0, 
            num_cardio = 0, 
            num_sprints = 0, 
            num_throws = 0, 
            num_regen = 0,
            num_play = 0, 
            num_volunteer = 0, 
            num_visualize_white = 0,
            num_visualize_red = 0,
            num_visualize_black = 0,
            num_cross_pod = 0,
            num_dinner = 0,
            num_truddy_check_in = 0,
            num_film = 0,
            num_pump_up = 0
        )
        print("Executing: ", insertCommand) 
        cursor.execute(insertCommand)
        send_debug_message("%s is new to Mischief" % name)
                
        commitAndCloseSQLConnection(sqlConnection)
        return True
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(error)
        return False
def fill_table_v2(member_info):
    print("Filling Table %s V2 WITH: " % __table_name__)
    # print("member_info: ", member_info)
    
    try:
        sqlConnection = getSQLConnection()
        cursor = sqlConnection.cursor()
        
        print("Inserting members")
        for member in member_info['members']: 
            if member["deleted"] == True: 
                continue
            if member["is_bot"] == True: 
                continue
    
            realName = member["profile"]["real_name"] # Note: deleted users do not have a `member["real_name"]` value but all users have a `profile` with a `real_name`.

            # Because beth's chris' name has a rich text apostrophe
            if member['id'] == 'U075A6KJE9G': 
                realName = 'Steakhouse'
            
            print("Member real_name: ", realName)
            print("Member id: ", member['id'])                
            insertCommand = """
                INSERT INTO {table_name} VALUES (
                    '{slack_id}',
                    '{name}', 
                    {score}, 
                    {last_post},
                    {num_posts}, 
                    {num_lifts}, 
                    {num_cardio}, 
                    {num_sprints}, 
                    {num_throws}, 
                    {num_regen},
                    {num_play}, 
                    {num_volunteer}, 
                    {num_visualize_white},
                    {num_visualize_red},
                    {num_visualize_black},
                    {num_cross_pod},
                    {num_dinner},
                    {num_truddy_check_in},
                    {num_film},
                    {num_pump_up}
                )
            """.format(
                table_name = __table_name__,
                slack_id = member['id'],
                name = realName, 
                score = 0, 
                last_post = "now()",
                num_posts = 0, 
                num_lifts = 0, 
                num_cardio = 0, 
                num_sprints = 0, 
                num_throws = 0, 
                num_regen = 0,
                num_play = 0, 
                num_volunteer = 0, 
                num_visualize_white = 0,
                num_visualize_red = 0,
                num_visualize_black = 0,
                num_cross_pod = 0,
                num_dinner = 0,
                num_truddy_check_in = 0,
                num_film = 0,
                num_pump_up = 0
            )
            print("Executing: ", insertCommand) 
            cursor.execute(insertCommand)
            send_debug_message("%s is new to Mischief" % realName)
                
        commitAndCloseSQLConnection(sqlConnection)
        return True
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(error)
        return False

def add_num_posts(mention_id, event_time, channel_id): # Removed `name` parameter if not using for below comment
    posterSlackId = mention_id[0]
    
    try:
        sqlConnection = getSQLConnection()
        cursor = sqlConnection.cursor()
        
        cursor.execute(sql.SQL(
            "UPDATE mischief_data SET num_posts=num_posts+1 WHERE slack_id = %s"),
            [posterSlackId])
        # Commenting out below since have the `fill-table` method to manually add everyone into the table (can come back to being more fancy with this style of conditional)
        # if cursor.rowcount == 0: #and channel_id == __fitness_channel_id__:
        #     insert_into_table_v2(posterSlackId, name)
        #     # cursor.execute(sql.SQL("INSERT INTO mischief_data VALUES (%s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, %d, %s, now())"),
        #     #                [name, mention_id[0], event_time, name])
        #     # send_debug_message("%s is new to Mischief" % name)
        commitAndCloseSQLConnection(sqlConnection)
        return True
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(error)
        return True

def get_table(table_name=None):
    if table_name == None:
        table_name = __table_name__
        
    print("Fetching Table: ", table_name)
    sqlConnection = getSQLConnection()
    cursor = sqlConnection.cursor(cursor_factory=RealDictCursor)

    command = "SELECT * from %s ORDER BY score DESC" % (table_name)
    print("Executing: ", command) 
    cursor.execute(command)
    table = cursor.fetchall()
    
    print("Fetched table")
    print("Printing records:")
    # column_names = [desc[0] for desc in cursor.description]
    # print(column_names)
    for record in table:
        print(record)        

    commitAndCloseSQLConnection(sqlConnection)    
    return table

def collect_stats(datafield, rev):
    try:
        sqlConnection = getSQLConnection()
        cursor = sqlConnection.cursor(cursor_factory=RealDictCursor)
        
        # get all of the people whose scores are greater than 0 (any non players have a workout score of -1; anyone participating will eventually have score over 0)
        command = "SELECT * FROM %s WHERE score > 0 ORDER BY score DESC" % __table_name__
        print("Executing: ", command) 
        cursor.execute(command)
        
        leaderboard = cursor.fetchall()
        string1 = "Stats:\n"
        for x in range(0, len(leaderboard)):
            string1 += "{0:>2}) {1:<20} `points: {2}` `lifts: {3}` `cardio: {4}` `sprints: {5}` `throws: {6}` `regen: {7}` `playing: {8}` `volunteer: {9}` `visualize-white: {10}` `visualize-red: {11}` `visualize-black: {12}` `cross pod: {13}` `dinner: {14}` `truddy check-in: {15}` `film: {16}` `pump-up: {17}` \n".format(
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
        cursor.close()
        sqlConnection.close()
        return string1
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(error)

# def collect_leaderboard(datafield, rev):
#     try:
#         sqlConnection = getSQLConnection()
#         cursor = sqlConnection.cursor()
#         # get all of the people whose scores are greater than 0 (any non players have a workout score of -1; anyone participating will eventually have score over 0)
#         command = "SELECT * FROM %s WHERE score > 0 ORDER BY score DESC" % __table_name__
#         print("Executing: ", command) 
#         cursor.execute(command)
        
#         leaderboard = cursor.fetchall()
#         # leaderboard.sort(key=lambda s: s[10], reverse=rev)  # sort the leaderboard by score descending
#         string1 = "Leaderboard:\n"
#         for x in range(0, len(leaderboard)):
#             string1 += '%d) %s	with %.1f points \n' % (x + 1, 
#                                                         leaderboard[x]['name'],
#                                                         leaderboard[x]['score'])
#         cursor.close()
#         sqlConnection.close()
#         return string1
#     except (Exception, psycopg2.DatabaseError) as error:
#         send_debug_message(error)        

def get_emojis():
    url = 'https://slack.com/api/emoji.list'
    json = requests.get(url, headers=__auth__).json()
    return json


def add_to_db(channel_id, 
              names, 
              addition, 
              lift_num, 
              cardio_num, 
              sprint_num, 
              throw_num, 
              regen_num, 
              play_num, 
              volunteer_num, 
              visualize_white_num,
              visualize_red_num, 
              visualize_black_num,
              cross_pod_num, 
              dinner_num, 
              truddy_check_in_num, 
              film_num, 
              pump_up_num, 
              num_workouts, 
              ids):  # add "addition" to each of the "names" in the db
    cursor = None
    sqlConnection = None
    num_committed = 0
    try:
        sqlConnection = getSQLConnection()
        cursor = sqlConnection.cursor(cursor_factory=RealDictCursor)
        
        print("names: ", names)
        print("ids: ", ids)
        for x in range(0, len(names)):
            print("starting", names[x])            
            updateCommand = """
                UPDATE {table_name} 
                SET score=score+{score_val_key}, 
                    last_post={last_post},
                    num_lifts=num_lifts+{lift_num_key}, 
                    num_cardio=num_cardio+{cardio_num_key}, 
                    num_sprints=num_sprints+{sprint_num_key}, 
                    num_throws=num_throws+{throw_num_key}, 
                    num_regen=num_regen+{regen_num_key}, 
                    num_play=num_play+{play_num_key}, 
                    num_volunteer=num_volunteer+{volunteer_num_key},
                    num_visualize_white=num_visualize_white+{visualize_white_num_key},
                    num_visualize_red=num_visualize_red+{visualize_red_num_key},
                    num_visualize_black=num_visualize_black+{visualize_black_num_key},
                    num_cross_pod=num_cross_pod+{cross_pod_num_key},
                    num_dinner=num_dinner+{dinner_num_key},
                    num_truddy_check_in=num_truddy_check_in+{truddy_check_in_num_key},
                    num_film=num_film+{film_num_key},
                    num_pump_up=num_pump_up+{pump_up_num_key}
                WHERE slack_id = '{slack_id}'
            """.format(
                table_name = __table_name__,
                slack_id = ids[x],
                score_val_key = float(addition), 
                last_post = "now()",
                lift_num_key = str(lift_num), 
                cardio_num_key = str(cardio_num), 
                sprint_num_key = str(sprint_num), 
                throw_num_key = str(throw_num), 
                regen_num_key = str(regen_num),
                play_num_key = str(play_num), 
                volunteer_num_key = str(volunteer_num), 
                visualize_white_num_key = str(visualize_white_num),
                visualize_red_num_key = str(visualize_red_num),
                visualize_black_num_key = str(visualize_black_num),
                cross_pod_num_key = str(cross_pod_num),
                dinner_num_key = str(dinner_num),
                truddy_check_in_num_key = str(truddy_check_in_num),
                film_num_key = str(film_num),
                pump_up_num_key = str(pump_up_num)
            )
            print("Executing: ", updateCommand) 
            cursor.execute(updateCommand)
            
            sqlConnection.commit()
            send_debug_message("committed %s with %s points" % (names[x], str(addition)))
            print("committed %s" % names[x])
            num_committed += 1
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(str(error))
    finally:
        if cursor is not None:
            cursor.close()
            sqlConnection.close()
        return num_committed


def subtract_from_db(names, subtraction, ids):  # subtract "subtraction" from each of the "names" in the db
    cursor = None
    sqlConnection = None
    num_committed = 0
    try:
        sqlConnection = getSQLConnection()
        cursor = sqlConnection.cursor()
        for x in range(0, len(names)):
            cursor.execute(sql.SQL(
                "UPDATE mischief_data SET score = score - %s WHERE slack_id = %s"),
                [subtraction, ids[x]])
            sqlConnection.commit()
            send_debug_message("subtracted %s" % names[x])
            num_committed += 1
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(str(error))
    finally:
        if cursor is not None:
            cursor.close()
            sqlConnection.close()
        return num_committed

def update_scores(userScores): # Expecting `userScores` as a map of {'slack_id': int(score)}
    try:
        sqlConnection = getSQLConnection()
        cursor = sqlConnection.cursor()
        for user, score in userScores.items():
            command = "UPDATE {table_name} SET score = {new_score} WHERE slack_id = '{user_id}'".format(
                table_name = __table_name__,
                new_score = score,
                user_id = user
            )
            print("Executing: ", command)
            cursor.execute(command)
            
        commitAndCloseSQLConnection(sqlConnection)  
        print("Successfully updated Scores")
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(str(error))

def reset_scores():  # reset the scores of everyone
    cursor = None
    sqlConnection = None
    try:
        sqlConnection = getSQLConnection()
        cursor = sqlConnection.cursor()
        # cursor.execute(sql.SQL("""
        #     UPDATE mischief_data SET num_workouts = 0, num_lifts = 0, num_cardio = 0, num_sprints = 0, num_throws = 0, num_regen = 0, num_play = 0, 
        #     num_volunteer = 0, score = 0, last_post = now() WHERE score != -1
        # """))

        updateCommand = """
            UPDATE {table_name} 
            SET score={score_val_key}, 
                last_post={last_post},
                num_lifts={lift_num_key}, 
                num_cardio={cardio_num_key}, 
                num_sprints={sprint_num_key}, 
                num_throws={throw_num_key}, 
                num_regen={regen_num_key}, 
                num_play={play_num_key}, 
                num_volunteer={volunteer_num_key},
                num_visualize_white={visualize_white_num_key},
                num_visualize_red={visualize_red_num_key},
                num_visualize_black=num_visualize_black+{visualize_black_num_key},
                num_cross_pod=num_cross_pod+{num_cross_pod_key},
                num_dinner=num_dinner+{num_dinner_key},
                num_truddy_check_in=num_truddy_check_in+{num_truddy_check_in_key},
                num_film=num_film+{num_film_key},
                num_pump_up=num_pump_up+{num_pump_up_key}
            WHERE score != -1
        """.format(
            table_name = __table_name__,
            score_val_key = 0, 
            last_post = "now()",
            lift_num_key = 0, 
            cardio_num_key = 0, 
            sprint_num_key = 0, 
            throw_num_key = 0, 
            regen_num_key = 0,
            play_num_key = 0, 
            volunteer_num_key = 0, 
            visualize_white_num_key = 0,
            visualize_red_num_key = 0,
            visualize_black_num_key = 0,
            num_cross_pod_key = 0,
            num_dinner_key = 0,
            num_truddy_check_in_key = 0,
            num_film_key = 0,
            num_pump_up_key = 0
        )
        print("Executing: ", updateCommand) 
        cursor.execute(updateCommand)
        sqlConnection.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(str(error))
    finally:
        if cursor is not None:
            cursor.close()
            sqlConnection.close()


def reset_talkative():  # reset the num_posts of everyone
    cursor = None
    sqlConnection = None
    try:
        sqlConnection = getSQLConnection()
        cursor = sqlConnection.cursor()
        cursor.execute(sql.SQL(
            "UPDATE mischief_data SET num_posts = 0 WHERE workout_score != -1"))
        sqlConnection.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(str(error))
    finally:
        if cursor is not None:
            cursor.close()
            sqlConnection.close()

def insert_column(col_name): # insert a column to table
    print("Inserting %s into table" % col_name)
    
    try:
        sqlConnection = getSQLConnection()
        cursor = sqlConnection.cursor()

        insertCommand = """
            ALTER TABLE {table_name}            
            ADD {column_name} SMALLINT NOT NULL DEFAULT({default_value})            
        """.format(
            table_name = __table_name__,
            column_name = col_name,
            default_value = 0
        )
        
        print("Executing: ", insertCommand) 
        cursor.execute(insertCommand)
        send_debug_message("Successfully added %s to table %s" % (col_name, __table_name__))
                
        commitAndCloseSQLConnection(sqlConnection)
        return True
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(error)
        return False
    
