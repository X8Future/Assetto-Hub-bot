# Future Crew Add on bot

An Assetto Corsa bot that connects to your Assetto Server Hub to make custom leaderboards, whitelist edits, player count forums and so much more with the latest Discord.py

Connects to the Assetto Server Hub made by [Assetto Servers](https://assettoserver.org/patreon-docs/plugins/PatreonHubPlugin). Must have that to use the bot [information here](https://assettoserver.org/patreon-docs/assettoserver-hub/)

# ❗ Disclaimer
Code is made and tested in Future Crew servers™. Code is written by an AMATEUR and should be treated as such, some parts may not make sense, be redundant, or just not work. 
Updates are pushed when I feel like it. Some issues may never be fixed and some may be updated or addressed in the next update or bug fix 
### USE AT YOUR OWN RISK...

Written on `Windows` enviroment and `Ubuntu` enviroment.
The bot currently runs on an Ubuntu system but shoiuld be just fine on Windows 10/11


# ⚙️ Configuration
## Make sure to check wherever there is a # to see what it says. 
Most of the time, it will be telling you information you need to fill out. V0.5 should fix a lot of the commonly used function parts and should reduce setup time
In the .env
```
DISCORD_TOKEN= Your Bot Token from the discord developer dashboard
GUILD_ID= # Your Guild ID (also known as the Server ID)
APPLICATION_ID= # Your Client ID NOT to be confused with your Client Secret
```
Go through each of the commands and fill out the ```DB_PATH =``` or ```db_path =``` sections with your hub.db path
```
Ex: DB_PATH = '/root/Bot-File/Hub.db'
```

Head over to [Steam api key](https://steamcommunity.com/dev/apikey), and sign up for an API key (required for the bot to check Steam ID status)
```
Put in Add-run.py, wlo.py, and whitelist.py
```

In the ```remove_player.py```, ```wlo.py```, ```transfer.py```, ```whitelist.py```, ```embedbuilder.py```, ```user_list.py```, ```check_bans.py
```, and ```whitelist_delete.py```
```
ALLOWED_ROLE_ID = enter role ID Ex: 123456789012345678, make sure if there is a syntax you put it INSIDE of them
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
In the ```ban_user.py```, ```overtake_roles.py```, ```staff.py```, ```whitelist.py``` and ```changetxt.py``` you need to fill out the ```ENDPOINTS``` data for the bot to access and edit your blacklist.txt's
```
EX: ENDPOINTS = [
    {"host": "123.45.678", "username": "root", "password": "Password", "remote_path": "/root/Servername/blacklist.txt"},]
```
```
Embeds can be edited via their messages, and what you want to say
```
In the ```automod.py``` fill out each of the spaces
```
IMMUNE_ROLES = {} # Roles immune to automod
HARD_BAD_WORDS = [] # Words that are hard-coded to be automatically blocked (can't upload them here cause GITHUB will take down the Repo)
BAD_WORD_KEYWORDS = [] # Words that close to these words you want automatically blocked (can't upload them here cause GITHUB will take down the Repo)
HARD_BLOCKED_DOMAINS = [] # Websites you want to be automatically blocked (can't upload them here cause GITHUB will take down the Repo)
ADULT_SITE_KEYWORDS = []  # Website words you want to be automatically blocked (can't upload them here cause GITHUB will take down the Repo)
WHITELISTED_INVITES = {} # Invites you want to be allowed to use
BYPASS_CHANNELS = {} # Channel IDs you can bypass this moderation 
APPEALS_ROLE_ID =  # Role IDs you want who can bypass moderation 
APPEALS_CATEGORY_ID =  # Channel ID where you want the appeals to be sent
```

~~In the ```Live_persons``` section, you need to fill out the channel you want alerts for and the roles you want to be alerted~~ 
## (WIP at the moment, skip this step)
```
- ALERT_CHANNEL_ID = # Where you want the bot to tell you a server has gone down
- ALERT_ROLE_ID = # The role you want to get pinged when a server goes down
- ALERT_USER = "<@>" # If you want a person to be pinged as well as a role
```

In the ```overtake_roles.py``` & the ```staff.py``` Fill out the ``ROLE_IDS`` Section
```
EX: SCORE_ROLE_IDS = {
    "whiteline": 1257423714614644956,
    "verifiedwhiteline": 1257423330395422844,
    "certifiedwhiteline": 1186780889552789504,
}
```
Head over to the Forums section and read through the ```INFO.txt```. This will help you sort through the folders and decide what needs to be changed and updated. 
```
- Things to Edit: 
        - self.api_urls = [] # Put your API URL's for your servres Ex: "http://91.99.6.152:80811/INFO" (ServerIP:Port/INFO)
        - "https://futurecrew.sirv.com/images/fdr/{i}.png" # The link for the photos, This is the newer version where all links are the same but the number at the end, see ```INFO.txt``` for more info
        - name="Cops and Robbers Public", # Change the thread Name to what you want it to be
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
sudo dnf install python3-aiofiles
```

# 🤖 Running the Bot

Make sure you're in the central file for the bot 
`Windows`
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
Command Name `/leaderboard`
- This command will allow you to add a leaderboard to your custom channel ID

Command Name `/wlo`
- wlo will allow you to overwrite someones SteamID in the whitelist.db

Command Name `/check_whitelist`
- Checking whitelist will allow you to check someone's whitelist status to see what ID they connected to, how many times they have attempted to whitelist and more

Command Name `/remove_whitelist`
- Will remove a user from the database and give them a fresh chance to re-whitelist 

Command Name `/add_player_run`
- Adds a player run to the leaderboard if you remove the run and it was legit or someone is missing a run

Command Name `/remove_player`
- Will remove a leaderboard run based on a Discord ID or Steam ID and will DM the user to let them know that their run has been removed from the leaderboard. Make sure when choosing you put an option for either steam ID or discord ID so the bot will know what to look for, then select player_id for steam id or discord_user for a user already whitelisted

Command Name `/serverembed`
- This command creates a server embed (up to 5 servers) using invite links. Numbered inputs map to each server and the embed shows slot types, server time, weather, and a join link, with customizable color and thumbnail.

Command Name `/enablewelcome`&`/welcomeset` 
- Enablewelocome will enable the command for and start sending welcome messages to new users to the server, welcomeset will allow you to move the channel you want the welcome messages

Command Name `/ban_user`
- Allows you to ban a user on multiple servers through the blacklist.txt with just the SteamID

Command Name `/bannedlist`
- Shows all banned SteamID's

Command Name `/blacklist_remove`
- Remove a user from the blacklist

Command Name `/appeals`
- Create the appeals embed in a channel of your choice

Command Name `/timeout`
- Will timeout a user for how long you want (#h #m #s format Ex: 1h 10m 20s)

Command Name `/removestrike`
- Will remove the # of strikes you choose for the user

Command Name `/load_cog`
- Will load any cog that is not loaded at the start of the bot

Command Name `/reload_cog `
- Will allow you to refresh a cog if something isn't working

Command Name `/unload_cog`
- Will unload a cog, helpful for commands not used much to reduce bot traffic

Command Name `/removettimeout`
- Will remove the timeout of a user and allow you to choose if you want to remove a strike or not

Command Name `/Whitelist`
- With V0.4 this command is now working! The /whitelist command will allow you to create a embed in any channel you like, allowing users to whitelist to a whitelist.db that will allow role updating and more

Command Name `/server_status` & `/deletecounter`
- Allows you to create a tracker for Total number of poeple in the server and your Staff online, /deletecounter will delete the counter of your choice

Command Name `/creategiveaway` & `/endgiveaway `
- Will create a popup that will help you make a giveaway where you can speciy the prize, duration and number of winners, and /endgiveaway will allow you to select a giveaway you want to end early

Command Name `/setlogchannel`
- Sets the channel that all whitelisted users information is saved to

Command Name `/showsteamusers`
- Creates an embed that shows all the users connected to the database listing out the discord account connected to the SteamID

Command Name `/sync_whitelist `
- Will take your hub.db and move all the users prevously whitelisted to that to your whitelist.db

Command Name `/updaterequirementscore`
- Allows you to set a new score for a Tier, so if you wanted to update Whiteline from 1 million points to 2 million you would put /updaterequirementscore tier:Whiteline score:2M

Command Name `/ticketbuilder `
- Sets the Channel where you want to put the ticket drop down


# ✨ Customize
This bot is fully customizable, and you’re free to modify almost anything.

That said, altering parts of the code beyond embeds, message text, destination channels, or similar non-functional changes may cause features or commands to break. (If the code breaks I am not responsible) 

All code is free to use without requiring permission from My Self, in accordance with the MIT License:
https://github.com/X8Future/Assetto-Hub-bot/blob/main/LICENSE

If you have any questions specifically about customization or other features, feel free to DM me on Discord: @mex8future
