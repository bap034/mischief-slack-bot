# Mischief Tracking Bot
A variation of the tribe-workout-bots repo. Done on Render since Heroku removed their free tier for PostGre.

## Deploying on Render

### Pre-Reqs:
1. Make an account on Render
1a. Connect your Github account to Render (alternatively, just deploy with one of our public bot repos)
2. Have your bot repo ready

## Create Web Service 
1. From the Render dashboards, click "New +" at the top and select Web Service
2. Connect your bot repository (or paste the bot repository under Public Git repository)
3. Fill out the following: 
**Name**: Can be whatever you want
**Region**: Probably any of these is fine; I usually go with Oregon/Us-west
**Environment**: Python 3
**Build command**: Might be already filled in; if not go with "pip install -r requirements.txt"
**Run command**: gunicorn app:app
**Instance type**: select the free one
4. "Create web service"

## Create DB
1. From the Render dashboards, click "New +" at the top and select PostgreSQL
2. You can name the DB whatever, otherwise stick with what is filled in there. Select the free tier.
2a. Make sure the region is the same as your web service region
3. "Create Database"

## Set up Environment Variables
1. Open three tabs - one for your web service, one for your DB, and one for the Slack app. (IF YOU HAVEN'T CREATED THE APP IN SLACK ALREADY, DO SO PER INSTRUCTIONS HERE -> https://github.com/samloop/tribe-workout-bots/blob/master/README.md) 
1a. Web service and DB can be found from the Render dashboard. Slack app can be found here (must be logged into workspace): https://api.slack.com/apps
2. On the DB tab, scroll down to "Connections." You should see values for hostname, port, and database, as well as hidden values for password, internal url, and external url. Copy the internal url (you'll use this in step 4).
3. On the Slack apps page, navigate to your app, then click "OAuth & Permissions" on the left.  
4. Now on the web service tab, click "Environment" on the left. From there, you want to click "Add Environment Variable." Copy and paste the following for key:value:
- DATABASE_URL: [internal url you copied in step 2]
- BOT_OAUTH_ACCESS_TOKEN: [insert Bot User OAuth Token from Slack page]
- OAUTH_ACCESS_TOKEN: [insert User OAuth Token from Slack page]
  - *This may be all you need for now, but check your code for other environment variables that may need to be added.*	
5. Save your environment variables. 


## Create DB Table - optional, depending on version of Slack
* I believe I created a command `!create-new-table` to do the database creation. [Can consult the `mischief_season_challenge.py` for the command.](https://github.com/bap034/mischief-slack-bot/blob/307f588e01686e1aa0afcf18dce58e78a6cc68f2/mischief_season_challenge.py#L315)
* Make sure to update the [`adminSlackId`, `fitnessChannelId`, and `botDebugChannelId`](https://github.com/bap034/mischief-slack-bot/blob/307f588e01686e1aa0afcf18dce58e78a6cc68f2/mischief_season_challenge.py#L8) values

Original instructions:
1. You have to create the table that will hold all the Slack information. Navigate to your DB in Render.
2. On the top right, there will be a button that says "Connect." Click this, then click to "External connection."
3. Copy the first url starting with "postgres://...".
4. In your command line, run ```psql <copied command>```
5. Copy your Create Table statement (i.e. below) and insert any rows you need to!	
# DB
Table can be created with:
name 0
num_posts 1
num_workouts 2
num_lifts 3
num_cardio 4
num_sprints 5
num_throws 6
num_regen 7
num_play 8
num_volunteer 9
score 10
date 11
id 12
last time 13
```
CREATE TABLE mischief_data(name text, num_posts SMALLINT, num_workouts SMALLINT, num_lifts SMALLINT, num_cardio SMALLINT, num_sprints SMALLINT, num_throws SMALLINT, num_regen SMALLINT, num_play SMALLINT, num_volunteer SMALLINT, score numeric(4, 1), last_post DATE, slack_id CHAR(11), last_time BIGINT);
```

I never got the DB working automatically because I am lazy. So instead I manually inserted each Slack member's row with the following:
```
INSERT INTO mischief_data VALUES ('<Name>', 0, 0, 0, 0, 0, 0, 0, 0, 0, '2022-11-11','<Slack ID>', 0);
```

# POINTS
```
lift - 2 pts
cardio - 1 pt
sprints - 2 pt
throw - 1 pt
yoga/stretch/regen - 1.5 pts
mini/goalty/tryout - 3 pts
volunteer - 3 pt
```
See app.py, db file to modify, parse additions method in season challenge
