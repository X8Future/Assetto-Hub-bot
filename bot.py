import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)
GUILD_ID =  # Set your Guild ID (Also known as the server ID)
GUILD = discord.Object(id=GUILD_ID)


startup_cogs = [
    "cmds.assetto_stuff.staff",
    "cmds.assetto_stuff.overtake_roles",
    "cmds.assetto_stuff.transfer",
    "cmds.discord_stuff.user_list",
    "cmds.assetto_stuff.whitelist",
    "cmds.forums.tier1.bay_area",
    "cmds.forums.public.us",
    "cmds.forums.public.german",
    "cmds.forums.public.eu",
    "cmds.forums.public.hamburg",
    "cmds.forums.whiteline.whiteline",
    "cmds.forums.public.fdr",
    "cmds.assetto_stuff.leaderboard",
    "cmds.assetto_stuff.server_embed",
    "cmds.load_cogs",
    "cmds.discord_stuff.join",
    "cmds.discord_stuff.serverstats",
    "cmds.discord_stuff.tickets",
    "cmds.assetto_stuff.whitelist_delete",
    "cmds.discord_stuff.giveaway",
    "cmds.mod.spam_checker",
    "cmds.discord_stuff.dropdown_buttons"
]

async def load_startup_cogs(delay: float = 1.5):
    for cog in startup_cogs:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded {cog}")
        except Exception as e:
            print(f"❌ Failed to load {cog}: {e}")
        await asyncio.sleep(delay)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    if not getattr(bot, "startup_done", False):
        await load_startup_cogs()
        bot.startup_done = True

        try:
            bot.tree.copy_global_to(guild=GUILD)
            await bot.tree.sync(guild=GUILD)
            print(f"✅ Slash commands synced to guild {GUILD_ID}")
        except Exception as e:
            print(f"❌ Error syncing slash commands: {e}")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("❌ DISCORD_TOKEN not found in environment variables.")
    bot.run(token)

