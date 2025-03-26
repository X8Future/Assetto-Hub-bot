import discord
import aiosqlite
from discord.ext import commands
from discord import app_commands
import re  
import random  
from datetime import datetime 
import requests

DB_PATH = 'Path to data base file for hub. EX: /root/Bot-File/Hub.db'
STEAM_API_KEY = 'API Key from steam https://steamcommunity.com/dev/apikey '

class LeaderboardManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_valid_player_id(self, player_id):
        """Check if the provided player ID is valid (must be a 17-digit number)."""
        return bool(re.match(r'^\d{16}$', player_id))

    def parse_time(self, time):
        """Convert time format like '8m 20s' to total milliseconds.""" 
        minutes = 0
        seconds = 0

        time_parts = time.split(" ")
        for part in time_parts:
            if "m" in part:
                minutes = int(part.replace("m", ""))
            elif "s" in part:
                seconds = int(part.replace("s", ""))

        total_milliseconds = (minutes * 60 + seconds) * 1000
        return total_milliseconds

    async def get_steam_username(self, steam_id):
        """Fetches the Steam username using Steam Web API."""
        try:
            url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&steamids={steam_id}"
            response = requests.get(url)
            data = response.json()

            if "response" in data and "players" in data["response"]:
                players = data["response"]["players"]
                if len(players) > 0:
                    return players[0]["personaname"] 
                else:
                    return None
            return None
        except Exception as e:
            print(f"Error fetching Steam username: {e}")
            return None

    async def add_player_to_leaderboard(self, steam_id: str, score: int, time: str, car_name: str):
        """Adds a player to the leaderboard or updates their entry."""
        try:
            async with aiosqlite.connect(DB_PATH) as conn:
                cursor = await conn.cursor()

                if not self.is_valid_player_id(steam_id):
                    return False, "Invalid Player ID format."

                await cursor.execute("SELECT 1 FROM players_discord WHERE player_id = ?", (steam_id,))
                player_result = await cursor.fetchone()

                if not player_result:
                    return False, "Player ID not found in the database."

                await cursor.execute("SELECT car_id FROM cars WHERE friendly_name = ?", (car_name,))
                car_result = await cursor.fetchone()

                if not car_result:
                    return False, f"Car '{car_name}' not found in the database."

                car_id = car_result[0]

                duration_ms = self.parse_time(time)

                # Fetch Steam username only when needed
                steam_username = await self.get_steam_username(steam_id)
                if not steam_username:
                    return False, "Invalid Steam ID or no Steam profile found."

                current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Check if the player already exists in the leaderboard and update if found
                await cursor.execute("""
                    SELECT overtake_n_leaderboard_entry_id 
                    FROM overtake_n_leaderboard_entries 
                    WHERE player_id = ?
                """, (steam_id,))
                existing_entry = await cursor.fetchone()

                if existing_entry:
                    # Update existing entry
                    await cursor.execute("""
                        UPDATE overtake_n_leaderboard_entries 
                        SET score = ?, duration = ?, car_id = ?, updated_at = ?
                        WHERE player_id = ?
                    """, (score, duration_ms, car_id, current_datetime, steam_id))
                    await conn.commit()
                    return True, f"Leaderboard entry updated: Player ID `{steam_id}` | Score: `{score}` | Time: `{duration_ms}ms` | Car: `{car_name}` | Steam Username: `{steam_username}`"
                else:
                    # Add new entry
                    overtake_n_leaderboard_entry_id = random.randint(100000, 999999)

                    await cursor.execute("""
                        INSERT INTO overtake_n_leaderboard_entries 
                        (overtake_n_leaderboard_id, overtake_n_leaderboard_entry_id, player_id, score, duration, car_id, created_at, updated_at) 
                        VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                    """, (overtake_n_leaderboard_entry_id, steam_id, score, duration_ms, car_id, current_datetime, current_datetime))

                    await conn.commit()
                    return True, f"New leaderboard entry added: Player ID `{steam_id}` | Score: `{score}` | Time: `{duration_ms}ms` | Car: `{car_name}` | Steam Username: `{steam_username}`"

        except Exception as e:
            print(f"Error adding or updating player to leaderboard: {e}")
            return False, str(e)

    @app_commands.command(name="add_player_run", description="Add or update a player to the leaderboard.")
    async def add_player_run(self, interaction: discord.Interaction, steam_id: str, score: int, time: str, car_name: str):
        """Handles slash command to add or update a run in the leaderboard."""
        success, message = await self.add_player_to_leaderboard(steam_id, score, time, car_name)

        if success:
            await interaction.response.send_message(message)
        else:
            await interaction.response.send_message(f"Error: {message}")

async def setup(bot: commands.Bot):
    leaderboard_management = LeaderboardManagement(bot)
    await bot.add_cog(leaderboard_management)
    await bot.tree.sync()
