# Assetto-Hub-bot

# Future Crew Add on bot

An Assetto Corsa bot that connects to your Assetto Server Hub to make custom leaderboards, whitelist edits, and player count forums with the latest Discord.py

Connects to the Assetto Server Hub made by [Assetto Servers](https://assettoserver.org/patreon-docs/plugins/PatreonHubPlugin). Must have that to use the bot [information here](https://assettoserver.org/patreon-docs/assettoserver-hub/)

### Code is made and tested by Future Crew servers™, the code is written by an AMATEUR and should be treated as such, some parts may not make sense or be redundant

## Tested on Windows and Ubuntu systems

Currently running on an Ubuntu system but written on Windows 11


# Configuration
```
DISCORD_TOKEN= Your Bot Token from the discord developer dashboard
```

# Installation
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

Then you can start the Bot with
```
python bot.py
```
Normally it start spitting out a few things "connecting using a static token" connected to "bot user name" and a few other things. If you see that you should be good to go, if you are running the bot for the first time there will be a few errors just as it creates the first embeds for your server but it should be good from there.

# Commands
With /leaderboard you can add a leaderboard to your custom channel

With /wlo you can override someone's steam ID in the whitelist 

With /check_whitelist you can check someone's status on whitelist to see what ID they connected to or if they have attempted to whitelist

/delete_user_players: will remove a user from the database and give them a fresh chance to re-whitelist 

/add_player_run will add a player run to the leaderboard if you remove the run and it was legit or someone is missing a run

/remove_player will remove a leaderboard run based on a Discord ID or Steam ID and will DM the user to let them know that their run has been removed from the leaderboard. Make sure when choosing you put option for either steam ID or discord id so the bot will know what to look for, then select player_id for steam id or discord_user for a user already whitelisted

/Whitelist command is a WIP and is not complete and can be removed or edited to work, (adds a user to the whitelist but won't sync with the hub)


# Customize
To customize almost anything you want, you can edit the embeds, the way things are looked, or your own server info. Any questions about CUSTOMIZATION you can DM me on discord @mex8future


![example](https://media.discordapp.net/attachments/1187595037937250315/1342666951947849798/image.png?ex=67ba778a&is=67b9260a&hm=5612474b2f7f9439b85115a8f72ef47b645486000fed3d3a740f5b827f30cf09&=&format=webp&quality=lossless&width=347&height=671)

![example](https://media.discordapp.net/attachments/1187595037937250315/1342668345815601233/Screenshot_2025-02-21_171936.png?ex=67ba78d7&is=67b92757&hm=ee605fcf583857cecb7bad33e3804dfb5fc48ed198bf0fe827002aeffe12f69f&=&format=webp&quality=lossless)

![example](https://media.discordapp.net/attachments/1187595037937250315/1342668820627722301/Screenshot_2025-02-21_172017.png?ex=67ba7948&is=67b927c8&hm=e7c128c2adff0b7fd3108bb4a491841ea4258db65e7c26dcb89bb286aef6f9ae&=&format=webp&quality=lossless)

![example](https://media.discordapp.net/attachments/1187595037937250315/1342668038167728342/Screenshot_2025-02-21_172043.png?ex=67ba788d&is=67b9270d&hm=1aeb74e08673d1be68f3d0fad6920c75d9752d817bfa15cee899fe6bdab628e9&=&format=webp&quality=lossless)

![example](https://media.discordapp.net/attachments/1187595037937250315/1342667611070140507/image.png?ex=67ba7828&is=67b926a8&hm=6463f25ce234c665012c5fba76b45e67689efbaed978a8b350a36c549622a33c&=&format=webp&quality=lossless)
