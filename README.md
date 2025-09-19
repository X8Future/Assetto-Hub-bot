# Future Crew Add on bot

An Assetto Corsa bot that connects to your Assetto Server Hub to make custom leaderboards, whitelist edits, and player count forums with the latest Discord.py

Connects to the Assetto Server Hub made by [Assetto Servers](https://assettoserver.org/patreon-docs/plugins/PatreonHubPlugin). Must have that to use the bot [information here](https://assettoserver.org/patreon-docs/assettoserver-hub/)

# ❗ Disclaimer
Code is made and tested in Future Crew servers™. Code is written by an AMATEUR and should be treated as such, some parts may not make sense, be redundant, or just not work (whitelist command). 
Updates may come in the future to fix issues. 
### USE AT YOUR OWN RISK...

Tested on `Windows` and `Ubuntu` systems.
Currently running on an Ubuntu system but written and tested on Windows 11


# ⚙️ Configuration
## Make sure to check wherever there is a # to see what it says, most of the time it will be telling you information you need to fill out
In the .env
```
DISCORD_TOKEN= Your Bot Token from the discord developer dashboard
```
Go through each of the commands and fill out the ```DB_PATH =``` or ```db_path =``` sections with your hub.db path
```
Ex: DB_PATH = '/root/Bot-File/Hub.db'
```

Head over to [Steam api key](https://steamcommunity.com/dev/apikey), and sign up for an API key (required for the bot to check Steam ID status)
```
Put in Add-run.py, wlo.py, and whitelist.py
```

In the ``wlo.py``, and ``whitelist_delete.py``
```
ALLOWED_ROLE_ID = enter role ID Ex: 123456789012345678
```
The bot should create this file when run, but if not create the file below in the commands section
```
"leaderboard_message_id.json"
```
In the ```leaderboard.py``` you need to add emoji and role info, to do this get the emoji name and number, then also get the role id you want to match your emoji
```
Ex: ROLE_EMOJI_PRIORITY = [
    (1384629851037468673, "<:Staff:1394901391826485268>"),
    (1273948572638492817, "<:Lifetime:1394906121122353182>"),
]
```
In the ```Bansusers.py``` and ```changetxt.py``` you need to fill out the ```ENDPOINTS``` data for the bot to access and edit your blacklist.txt's
```
EX: ENDPOINTS = [
    {"host": "123.45.678", "username": "root", "password": "Password", "remote_path": "/root/Servername/blacklist.txt"},]
```
```
Embeds can be edited via their messages, and what you want to say
```
In the ```Automod``` fill out each of the spaces
```
- IMMUNE_ROLES = {} # roles immune to the automod
- HARD_BAD_WORDS = [] # Bad words that will always be blocked 
- BAD_WORD_KEYWORDS = [] # Words that if they even have a little of the word in will be blocked
- HARD_BLOCKED_DOMAINS = [] # Website always blocked ADULT_SITE_KEYWORDS = [] # 18+ Website key words
- WHITELISTED_INVITES = {} # Invite links you want to be allowed BYPASS_CHANNELS = {} #  Channels the auto mod won't work
- APPEALS_ROLE_ID = # Roles you want to give for appeals
- APPEALS_CATEGORY_ID = # Where you want the Appeals channels to be created
```

In the ```Live_persons``` section, you need to fill out the channel you want alerts for and the roles you want to be alerted
```
- ALERT_CHANNEL_ID = # Where you want the bot to tell you a server has gone down
- ALERT_ROLE_ID = # The role you want to get pinged when a server goes down
- ALERT_USER = "<@>" # If you want a person to be pinged as well as a role
```

# ⏬ Installation
Install python [using](https://www.python.org/downloads/) 
For Ubuntu: sudo apt update && sudo apt install python3

Install discord.py and dotenv to be able to start the bot
```
pip install discord.py python-dotenv
```

Configure the Configfile and then deploy the Commands.
```
pip install aiohttp
pip install discord.py requests
pip install discord.py aiosqlite pytz
```

# 🤖 Running the Bot

Make sure you're in the central file for the bot `Windows`
```
cd ..\Assetto-Hub-bot-main
```
`Ubuntu`
```
cd ../Assetto-Hub-bot-main
```

Make sure you deploy the command from the main file and not from the commands file or it won't run

You can start the Bot `WINDOWS`
```
python bot.py
```

For `UBUNTU` servers
```
python3 bot.py
```

Normally, it start spitting out a few things, "connecting using a static token" connected to "bot user name" and a few other things. If you see that you should be good to go, if you are running the bot for the first time, there will be a few errors just as it creates the first embeds for your server, but it should be good from there.

# 📝 Commands
With /leaderboard you can add a leaderboard to your custom channel

With /wlo you can override someone's Steam ID in the whitelist 

With /check_whitelist you can check someone's status on whitelist to see what ID they connected to or if they have attempted to whitelist

/delete_user_players: will remove a user from the database and give them a fresh chance to re-whitelist 

/add_player_run will add a player run to the leaderboard if you remove the run and it was legit or someone is missing a run

/remove_player will remove a leaderboard run based on a Discord ID or Steam ID and will DM the user to let them know that their run has been removed from the leaderboard. Make sure when choosing you put an option for either steam ID or discord ID so the bot will know what to look for, then select player_id for steam id or discord_user for a user already whitelisted

/serverembed will allow you to add a server embed with up to 5 servers (you can add more server slots). The bot supports Invite links instead of API's now. Invite1 is the first server, and so on, same with name1 and vip_slots1. VIP slots will show VIP slots if any, if there are no reserved slots just click no, VIP only slots will filter just VIP slots is you have a VIP only server. Embed includes Public Slots, Reserved slots, VIP only slots, Time of server, Weather of server, and the Join Link. Embed color and thumbnail can also be chosen. 

/refresh will refresh all embeds connected to the bot incase they stop updating 

/ban_user allows you to ban a user on multiple servers through the blacklist.txt with just the steamID

/bannedlist allows you to see the users banned 

/blacklist_remove allows you to unban a user from all the servers

/appeals will create an appeals embed in a channel of your choice

/timeout will timeout a user for how long you want (#h #m #s format Ex: 1h 10m 20s)

/liveembed will create a live embed of all servers you have created in the /serverembed command 

/removestrike will remove the # of strikes you choose for the user

/load_cog will load any cog that are not loaded on the start of the bot

/removettimeout will remove the timeout of a user and allow you to choose if you want to remove a strike or not

/Whitelist command is a WIP and is not complete, and can be removed or edited to work (adds a user to the whitelist, but won't sync with the hub at this point in time)

# ✨ Customize
This bot is fully customizable and you can change almost anything you want. Nothing is hard-coded into the bot, and it should run if something is changed. However, changing things besides embeds, messages sent, locations to where things are going, or other modifications in which the command itself is not changing may result in broken code. All code is free to use without Future Crew's knowledge or copyright (check MIT LICENSE). If you have any questions about CUSTOMIZATION, you can DM me on Discord @mex8future
