import discord
from discord.ext import commands
import discord
import os
from discord.ext import commands
from dotenv import load_dotenv


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
load_dotenv()

async def load_extensions():
    await bot.load_extension("cmds.whitelist")
    await bot.load_extension("cmds.leaderboard")
    await bot.load_extension("cmds.wlo")
    await bot.load_extension("cmds.wc")
    await bot.load_extension("cmds.whitelist_delete")
    await bot.load_extension("cmds.add_run")
    await bot.load_extension("cmds.remove_player")
    await bot.load_extension("cmds.server_embed")
    await bot.load_extension("cmds.ban_user")
    await bot.load_extension("cmds.changetxt")
    await bot.load_extension("cmds.check_bans")
@bot.event
async def on_ready():
    await load_extensions()
    print(f'Logged in as {bot.user}')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

async def load_extensions():
    await bot.load_extension("cmds.whitelist")
    await bot.load_extension("cmds.leaderboard")
    await bot.load_extension("cmds.wlo")
    await bot.load_extension("cmds.wc")
    await bot.load_extension("cmds.whitelist_delete")
    await bot.load_extension("cmds.add_run")
    await bot.load_extension("cmds.remove_player")
    await bot.load_extension("cmds.server_embed")
    await bot.load_extension("cmds.ban_user")
    await bot.load_extension("cmds.changetxt")
    await bot.load_extension("cmds.check_bans")

@bot.event
async def on_ready():
    await load_extensions()
    print(f'Logged in as {bot.user}')

bot.run(os.getenv("DISCORD_TOKEN"))

