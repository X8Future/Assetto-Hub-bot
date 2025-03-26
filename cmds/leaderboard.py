import discord
import aiosqlite
import json
from discord.ext import commands, tasks
from datetime import datetime
import pytz

DB_PATH = '/root/Bot-File/Hub.db'
TARGET_CHANNEL_ID = 1189659213337723030
MESSAGE_ID_PATH = "leaderboard_message_id.json"
MAX_FIELD_LENGTH = 1024

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leaderboard_message = None
        self.update_scores.start()

    async def fetch_leaderboard(self):
        """Fetches the leaderboard entries from the database asynchronously."""
        try:
            async with aiosqlite.connect(DB_PATH) as conn:
                cursor = await conn.cursor()
                await cursor.execute(""" 
                    SELECT 
                        o.overtake_n_leaderboard_entry_id,  
                        o.player_id, 
                        o.score, 
                        o.duration, 
                        COALESCE(c.friendly_name, c.model) AS car_name, 
                        pd.discord_userid  
                    FROM 
                        overtake_n_leaderboard_entries o
                    LEFT JOIN 
                        cars c ON o.car_id = c.car_id
                    LEFT JOIN 
                        players_discord pd ON o.player_id = pd.player_id
                    ORDER BY 
                        o.score DESC;
                """)
                data = await cursor.fetchall()
            return data
        except Exception as e:
            print(f"Database Error: {e}")
            return []

    async def fetch_player_name(self, player_id):
        """Fetches the player name asynchronously using the player ID."""
        try:
            async with aiosqlite.connect(DB_PATH) as conn:
                cursor = await conn.cursor()
                await cursor.execute(""" 
                    SELECT name 
                    FROM players 
                    WHERE player_id = ?;
                """, (player_id,))
                result = await cursor.fetchone()
            return result[0] if result else "Unknown Player"
        except Exception as e:
            print(f"Database Error: {e}")
            return "Unknown Player"

    async def get_position_suffix(self, position, for_button=False):
        """Returns the suffix for the position; different formatting for leaderboard and button."""
        if for_button:
            return f"Your {position} place on the leaderboard!"  # No emoji for button
        else:
            # Keep the emoji for leaderboard embed
            suffixes = {1: "🥇1st", 2: "🥈2nd", 3: "🥉3rd"}
            return suffixes.get(position, f"🏅{position}th")

    async def calculate_user_position(self, user_score, leaderboard_entries):
        """Calculates the user's position asynchronously based on their score."""
        position = 1
        for entry in leaderboard_entries:
            if entry[2] > user_score:
                position += 1
        return position

    async def save_message_id(self, message_id):
        """Save the leaderboard message ID to a file."""
        with open(MESSAGE_ID_PATH, "w") as f:
            json.dump({"message_id": message_id}, f)

    async def load_message_id(self):
        """Load the leaderboard message ID from a file."""
        try:
            with open(MESSAGE_ID_PATH, "r") as f:
                data = json.load(f)
                return data.get("message_id")
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    @discord.app_commands.command(name="leaderboard", description="Post the leaderboard embed.")
    async def leaderboard(self, interaction: discord.Interaction):
        """Handles the leaderboard command."""
        channel = self.bot.get_channel(TARGET_CHANNEL_ID)
        leaderboard_entries = await self.fetch_leaderboard()

        if not channel:
            await interaction.response.send_message("Invalid channel ID.", ephemeral=True)
            return

        await interaction.response.defer()

        embed = await self.create_leaderboard_embed()

        self.leaderboard_message = await channel.send(embed=embed, view=LeaderboardView(self))
        await self.save_message_id(self.leaderboard_message.id)

        await interaction.followup.send("Leaderboard embed created.", ephemeral=True)

    async def create_leaderboard_embed(self):
        """Creates and returns the leaderboard embed with individual fields for each position."""
        leaderboard_entries = await self.fetch_leaderboard()
        if not leaderboard_entries:
            return discord.Embed(title="Cut Up Leaderboard | Top 10", description="No scores available.", color=0x36393F)

        leaderboard_entries = leaderboard_entries[:10]  
        while len(leaderboard_entries) < 10:
            leaderboard_entries.append((None, None, 0, 0, "Unknown Car", None))  

        embed = discord.Embed(title="Cut Up Leaderboard | Top 10", color=0x6A0DAD)
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1187595037937250315/1330833298179752036/leaderboard.png")

        for idx, entry in enumerate(leaderboard_entries, start=1):
            entry_id, player_id, score, duration, car_name, discord_id = entry
            discord_mention = f"<@{discord_id}>" if discord_id else "** **"

            player_name = await self.fetch_player_name(player_id) if player_id else "No Player"
            minutes, seconds = divmod(duration // 1000, 60)
            formatted_duration = f"{minutes}m {seconds}s"
            position_with_suffix = await self.get_position_suffix(idx)

            formatted_score = f"{score:,}".replace(",", ".")  

            entry_text = f"**Player:** {player_name} | {discord_mention}\n**Score**: {formatted_score} Points\n**Duration:** {formatted_duration}\n**Car:** {car_name}"
            embed.add_field(name=f"**{position_with_suffix}**", value=entry_text, inline=False)

        la_time = datetime.now(pytz.timezone("America/Los_Angeles")).strftime("%I:%M %p")
        embed.set_footer(text=f"Updated every 60 seconds • Last updated: {la_time}")

        return embed

    @tasks.loop(minutes=1)
    async def update_scores(self):
        """Updates the leaderboard every 1 minute."""
        if self.leaderboard_message is None:
            return
        try:
            embed = await self.create_leaderboard_embed()
            await self.leaderboard_message.edit(embed=embed)
        except Exception as e:
            print(f"Error updating leaderboard: {e}")

    @update_scores.before_loop
    async def before_update_scores(self):
        """Waits until the bot is ready before starting the update loop."""
        await self.bot.wait_until_ready()
        message_id = await self.load_message_id()
        if message_id:
            channel = self.bot.get_channel(TARGET_CHANNEL_ID)
            if channel:
                try:
                    self.leaderboard_message = await channel.fetch_message(message_id)
                    await self.leaderboard_message.edit(view=LeaderboardView(self))
                except discord.NotFound:
                    print("Leaderboard message not found, it will need to be re-created.")

class FindScoreButton(discord.ui.Button):
    def __init__(self, leaderboard: Leaderboard):
        super().__init__(label="⭐ Find My Score", style=discord.ButtonStyle.primary)
        self.leaderboard = leaderboard

    async def callback(self, interaction: discord.Interaction):
        discord_id = interaction.user.id
        try:
            async with aiosqlite.connect(DB_PATH) as conn:
                cursor = await conn.cursor()
                await cursor.execute("SELECT player_id FROM players_discord WHERE discord_userid = ?", (discord_id,))
                result = await cursor.fetchone()

                if not result:
                    await interaction.response.send_message("You haven't been whitelisted.", ephemeral=True)
                    return

                player_id = result[0]

                leaderboard_entries = await self.leaderboard.fetch_leaderboard()

                await cursor.execute(""" 
                    SELECT score, duration, c.friendly_name, o.updated_at
                    FROM overtake_n_leaderboard_entries o
                    LEFT JOIN cars c ON o.car_id = c.car_id
                    WHERE o.player_id = ? 
                    ORDER BY o.score DESC LIMIT 1
                """, (player_id,))
                leaderboard_result = await cursor.fetchone()

                if not leaderboard_result:
                    await interaction.response.send_message("No runs found. Try playing first!", ephemeral=True)
                    return

                score, duration, car_name, updated_at = leaderboard_result

                formatted_score = f"{score:,}".replace(",", ".")
                minutes, seconds = divmod(duration // 1000, 60)
                formatted_duration = f"{minutes}m {seconds}s"
                run_date = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S").strftime("%B %d %Y")

                user_position = None
                for idx, entry in enumerate(leaderboard_entries, start=1):
                    if entry[1] == player_id: 
                        user_position = await self.leaderboard.get_position_suffix(idx, for_button=True)
                        break

                if user_position is None:
                    user_position = "Unranked"

                embed = discord.Embed(
                    title="Your place on the leaderboard",
                    description=f"Hello {interaction.user.mention}, {user_position}",
                    color=0x36393F
                )
                embed.add_field(name="**Score**", value=formatted_score, inline=True)
                embed.add_field(name="**Duration**", value=formatted_duration, inline=True)
                embed.add_field(name="**Car Used**", value=car_name, inline=True)
                embed.add_field(name="**Date Completed**", value=run_date, inline=True)
                embed.set_footer(text="Brought to you by Future Crew ™")

                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print(f"Database Error: {e}")
            await interaction.response.send_message("An error occurred while retrieving your score.", ephemeral=True)

class LeaderboardView(discord.ui.View):
    def __init__(self, leaderboard: Leaderboard):
        super().__init__(timeout=None)
        self.add_item(FindScoreButton(leaderboard))

async def setup(bot):
    leaderboard = Leaderboard(bot)
    await bot.add_cog(leaderboard)
