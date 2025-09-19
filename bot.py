import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

startup_cogs = [
    "cmds.us_status",
    "cmds.eu_status",
    "cmds.hamburg",
    "cmds.leaderboard",
    "cmds.live_persons",
    "cmds.server_embed",
    "cmds.load_cogs", 
    "cmds.automod",
    "cmds.remove_strike"
]

async def load_startup_cogs():
    for cog in startup_cogs:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded {cog}")
        except Exception as e:
            print(f"❌ Failed to load {cog}: {e}")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    if not hasattr(bot, 'startup_done'):
        await load_startup_cogs()
        bot.startup_done = True
        try:
            await bot.tree.sync()
            print("✅ Slash commands synced.")
        except Exception as e:
            print(f"❌ Error syncing slash commands: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
