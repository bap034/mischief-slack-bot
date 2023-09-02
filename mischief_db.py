import os
import urllib.parse
import urllib.request
import psycopg2

from psycopg2 import sql
from slack_api import *

from flask import Flask, request, jsonify, make_response

app = Flask(__name__)
__token__ = os.getenv('BOT_OAUTH_ACCESS_TOKEN')
__auth__ = {"Authorization" : "Bearer " + __token__}
__table_name__  = "mischief_data"

# CREATE TABLE mischief_data(name text, num_posts SMALLINT, num_workouts SMALLINT, num_throw SMALLINT, num_regen SMALLINT, score numeric(4, 1), last_post DATE, slack_id CHAR(9), last_time BIGINT, pod text, team text)

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

# def get_db(): 
#     print("Fetching DB: ", __table_name__)
#     executeSQL(sql.SQL("SELECT * from %s"), __table_name__)

def create_new_db_v2(member_info):
    try:    
        sqlConnection = getSQLConnection()
        cursor = sqlConnection.cursor()
    
        print("Dropping existing DB: ", __table_name__)
        dropCommand = "DROP TABLE IF EXISTS " + __table_name__
        cursor.execute(dropCommand) 
        print("Successfully dropped existing DB: ", __table_name__)
        
        print("Creating new DB v2: ", __table_name__)
        createCommand = """
            CREATE TABLE {table_name} (
              name text, 
              num_posts SMALLINT, 
              num_workouts SMALLINT, 
              num_lifts SMALLINT, 
              num_cardio SMALLINT, 
              num_sprints SMALLINT, 
              num_throws SMALLINT, 
              num_regen SMALLINT,
              num_play SMALLINT, 
              num_volunteer SMALLINT, 
              score numeric(4, 1), 
              last_post DATE, 
              slack_id CHAR(11), 
              last_time BIGINT
            )
        """.format(
            table_name = __table_name__
        )
        cursor.execute(createCommand)
        print("Successfully created new DB: ", __table_name__)
    
        commitAndCloseSQLConnection(sqlConnection)   
        return True
        
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        send_debug_message(error)
        return False

# this doesn't really work
def init_db(member_info):
    print("ATTEMPTING INIT WITH: ") #, member_info)
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
        cursor = conn.cursor()
        cursor.execute("SELECT * from mischief_data")
        print("Printing records:")
        for record in cursor:
            print(record)
        # print("Members: ", member_info['members'])
        # print("cursor: ", cursor)
        # print("cursor.rowcount: ", cursor.rowcount)       
        print("Inserting members")
        if cursor.rowcount == 0: #and channel_id == "C03UHTL3J58": << rowcount is based on execute command count (will be -1 if no execute commands)
            for member in member_info['members']:   
                member_real_name = member['real_name']
                print("Member real_name: ", member_real_name)
                print("Member id: ", member['id'])
                cursor.execute(sql.SQL("INSERT INTO mischief_data VALUES (%s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, now(), %s, extract(epoch from now()))"),
                               [member_real_name, member['id']])
                send_debug_message("%s is new to Mischief" % member_real_name)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(error)
        return False

def add_num_posts(mention_id, event_time, name, channel_id):
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
        cursor = conn.cursor()
        cursor.execute(sql.SQL(
            "UPDATE mischief_data SET num_posts=num_posts+1 WHERE slack_id = %s"),
            [mention_id[0]])
        if cursor.rowcount == 0 and channel_id == "C03UHTL3J58":
            cursor.execute(sql.SQL("INSERT INTO mischief_data VALUES (%s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, %d, %s, now())"),
                           [name, mention_id[0], event_time, name])
            send_debug_message("%s is new to Mischief" % name)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(error)
        return True

def collect_stats(datafield, rev):
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
        cursor = conn.cursor()
        # get all of the people whose scores are greater than 0 (any non players have a workout score of -1; anyone participating will eventually have score over 0)
        cursor.execute(sql.SQL(
            "SELECT * FROM mischief_data WHERE score > 0"), )
        leaderboard = cursor.fetchall()
        leaderboard.sort(key=lambda s: s[10], reverse=rev)  # sort the leaderboard by score descending
        string1 = "Leaderboard:\n"
        for x in range(0, len(leaderboard)):
            string1 += '%d) %s with %.1f point(s); %.1d lift(s); %.1d cardio; %.1d sprints; %.1d throw(s); %.1d regen; %.1d goalty/mini/tryouts; %.1d volunteer. \n' % (x + 1, leaderboard[x][0], 
                leaderboard[x][10], leaderboard[x][3], leaderboard[x][4], leaderboard[x][5], leaderboard[x][6],
                leaderboard[x][7], leaderboard[x][8], leaderboard[x][9])
        cursor.close()
        conn.close()
        return string1
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(error)

def collect_leaderboard(datafield, rev):
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
        cursor = conn.cursor()
        # get all of the people whose scores are greater than 0 (any non players have a workout score of -1; anyone participating will eventually have score over 0)
        cursor.execute(sql.SQL(
            "SELECT * FROM mischief_data WHERE score > 0"), )
        leaderboard = cursor.fetchall()
        leaderboard.sort(key=lambda s: s[10], reverse=rev)  # sort the leaderboard by score descending
        string1 = "Leaderboard:\n"
        for x in range(0, len(leaderboard)):
            string1 += '%d) %s with %.1f point(s)\n' % (x + 1, leaderboard[x][0], 
                leaderboard[x][10])
        cursor.close()
        conn.close()
        return string1
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(error)        

def get_group_info():
    url = "https://slack.com/api/users.list"
    json = requests.get(url, headers=__auth__).json()
    return json


def get_emojis():
    url = 'https://slack.com/api/emoji.list'
    json = requests.get(url, headers=__auth__).json()
    return json


def add_to_db(channel_id, names, addition, lift_num, cardio_num, sprint_num, throw_num, regen_num, play_num, volunteer_num, num_workouts, ids):  # add "addition" to each of the "names" in the db
    cursor = None
    conn = None
    num_committed = 0
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
        print("names: ", names)
        print("ids: ", ids)
        cursor = conn.cursor()
        for x in range(0, len(names)):
            print("starting", names[x])
            cursor.execute(sql.SQL(
                "SELECT score FROM mischief_data WHERE slack_id = %s"), [str(ids[x])])
            score = cursor.fetchall()[0][0]
            score = int(score)
            if score != -1:
                cursor.execute(sql.SQL("""
                    UPDATE mischief_data SET num_workouts=num_workouts+%s,
                    num_lifts=num_lifts+%s, num_cardio=num_cardio+%s, num_sprints=num_sprints+%s, num_throws=num_throws+%s, num_regen=num_regen+%s, 
                    num_play=num_play+%s, num_volunteer=num_volunteer+%s,
                    score=score+%s, last_post=now() WHERE slack_id = %s
                    """),
                    [str(num_workouts), str(lift_num), str(cardio_num), str(sprint_num), str(throw_num), str(regen_num), str(play_num), str(volunteer_num), str(addition), ids[x]])
                conn.commit()
                send_debug_message("committed %s with %s points" % (names[x], str(addition)))
                print("committed %s" % names[x])
                num_committed += 1
            else:
                send_debug_message("invalid workout poster found " + names[x])
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(str(error))
    finally:
        if cursor is not None:
            cursor.close()
            conn.close()
        return num_committed


def subtract_from_db(names, subtraction, ids):  # subtract "subtraction" from each of the "names" in the db
    cursor = None
    conn = None
    num_committed = 0
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
        cursor = conn.cursor()
        for x in range(0, len(names)):
            cursor.execute(sql.SQL(
                "UPDATE mischief_data SET score = score - %s WHERE slack_id = %s"),
                [subtraction, ids[x]])
            conn.commit()
            send_debug_message("subtracted %s" % names[x])
            num_committed += 1
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(str(error))
    finally:
        if cursor is not None:
            cursor.close()
            conn.close()
        return num_committed


def reset_scores():  # reset the scores of everyone
    cursor = None
    conn = None
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
        cursor = conn.cursor()
        cursor.execute(sql.SQL("""
            UPDATE mischief_data SET num_workouts = 0, num_lifts = 0, num_cardio = 0, num_sprints = 0, num_throws = 0, num_regen = 0, num_play = 0, 
            num_volunteer = 0, score = 0, last_post = now() WHERE score != -1
        """))
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(str(error))
    finally:
        if cursor is not None:
            cursor.close()
            conn.close()


def reset_talkative():  # reset the num_posts of everyone
    cursor = None
    conn = None
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
        cursor = conn.cursor()
        cursor.execute(sql.SQL(
            "UPDATE mischief_data SET num_posts = 0 WHERE workout_score != -1"))
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(str(error))
    finally:
        if cursor is not None:
            cursor.close()
            conn.close()

def add_workout(name, slack_id, workout_type):
    cursor = None
    conn = None
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
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(str(error))
    finally:
        if cursor is not None:
            cursor.close()
            conn.close()

def get_workouts_after_date(date, type, slack_id):
    cursor = None
    conn = None
    workouts = []
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
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(str(error))
    finally:
        if cursor is not None:
            cursor.close()
            conn.close()
    return workouts

def get_group_workouts_after_date(date, type):
    cursor = None
    conn = None
    workouts = []
    print(date, type)
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
    except (Exception, psycopg2.DatabaseError) as error:
        send_debug_message(str(error))
    finally:
        if cursor is not None:
            cursor.close()
            conn.close()
    return workouts
