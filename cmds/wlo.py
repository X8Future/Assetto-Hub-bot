import os
import discord
from discord.ext import commands
import sqlite3
import aiohttp

# Configuration
STEAM_API_KEY = ""  # Replace with your Steam API key
STEAM_API_URL = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"

db_path = 'Path to data base file for hub. EX: /root/Bot-File/Hub.db'

# The role ID that is allowed to use this command
ALLOWED_ROLE_ID =  

async def validate_steam_id(steam_id):
    """Validates the Steam ID by making a request to the Steam API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{STEAM_API_URL}?key={STEAM_API_KEY}&steamids={steam_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    players = data.get("response", {}).get("players", [])
                    if players:
                        return True  
                    else:
                        return False  
                else:
                    return False  
    except Exception as e:
        print(f"Error validating Steam ID: {e}")
        return False


def get_current_steam_id(discord_id):
    """Retrieves the current Steam ID (player_id) for the given Discord ID from the players_discord table."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()


        cursor.execute("SELECT player_id FROM players_discord WHERE discord_userid = ?", (discord_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return result[0]
        return None 
    except Exception as e:
        print(f"Error retrieving Steam ID from database: {e}")
        return None

def update_or_insert_steam_id(discord_id, new_steam_id):
    """Updates or inserts the Steam ID (player_id) for a given Discord ID in the players_discord table."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM players_discord WHERE discord_userid = ?", (discord_id,))
        result = cursor.fetchone()

        if result:
            cursor.execute("UPDATE players_discord SET player_id = ? WHERE discord_userid = ?", (new_steam_id, discord_id))
            print(f"Updated Steam ID for Discord user {discord_id}")
        else:
            cursor.execute("INSERT INTO players_discord (discord_userid, player_id) VALUES (?, ?)", (discord_id, new_steam_id))
            print(f"Inserted new Steam ID for Discord user {discord_id}")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating or inserting Steam ID in database: {e}")

async def setup(bot):
    @bot.tree.command(name="wlo", description="Override a user's Steam ID in the whitelist.")
    async def wlo(interaction: discord.Interaction, user: discord.User, new_steam_id: str):
        """Override a user's Steam ID with a new one, if valid and the user has the correct role."""

        if ALLOWED_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("⚠️ You do not have permission to use this command.", ephemeral=True)
            return

        is_valid = await validate_steam_id(new_steam_id)
        if not is_valid:
            await interaction.response.send_message("⚠️ Invalid Steam ID.", ephemeral=True)
            return

        discord_id = user.id
        current_steam_id = get_current_steam_id(discord_id)

        if current_steam_id == new_steam_id:
            await interaction.response.send_message("⚠️ Steam IDs match, try a different ID.", ephemeral=False)
            return

        update_or_insert_steam_id(discord_id, new_steam_id)

        embed = discord.Embed(
            title="Steam ID Overridden",
            description=f"{user.mention} is now connected to Steam ID: **{new_steam_id}**.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Whitelist Update Successful")

        await interaction.response.send_message(embed=embed, ephemeral=False)
