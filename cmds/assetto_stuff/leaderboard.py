import discord
import aiosqlite
import json
from datetime import datetime, timedelta
import pytz

from discord.ext import commands, tasks
from discord import app_commands, Interaction
import re

def clean_player_name(name: str) -> str:
    return re.sub(r'\s*\[.*?\]\s*', '', name).strip()


DB_PATH = '/root/Bot-File/Hub.db'
TARGET_CHANNEL_ID = 1189659213337723030
MESSAGE_ID_PATH = "leaderboard_message_id.json"
MAX_FIELD_LENGTH = 1024

ALLOWED_ROLE_IDS = [1251377219910242365]
ROLE_EMOJI_PRIORITY = [
    (1251377219910242365, "<:Staff:1394901391826485268>"),
    (1274637474471215201, "<:Lifetime:1394906121122353182>"),
    (1229907065074487362, "<:TIER2:1394903128595238992>"),
    (1234733909158264914, "<:TIER2:1394903128595238992>"),
    (1229900492759503002, "<:TIER1:1394901645128634419>"),
    (1234733594941849632, "<:TIER1:1394901645128634419>"),
    (1257423714614644956, "<:Whiteline:1346388225337589823>")
]


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leaderboard_message = None
        self.update_scores.start()

    async def fetch_leaderboard(self):
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
                        pd.discord_userid,
                        o.updated_at
                    FROM 
                        overtake_n_leaderboard_entries o
                    LEFT JOIN 
                        cars c ON o.car_id = c.car_id
                    LEFT JOIN 
                        players_discord pd ON o.player_id = pd.player_id
                    ORDER BY 
                        o.score DESC;
                """)
                return await cursor.fetchall()
        except Exception as e:
            print(f"Database Error: {e}")
            return []

    async def fetch_valid_timing_data(self, player_id: int, overtake_time: str):
        try:
            overtake_dt = datetime.strptime(overtake_time, "%Y-%m-%d %H:%M:%S")
            async with aiosqlite.connect(DB_PATH) as conn:
                cursor = await conn.cursor()
                await cursor.execute("""
                    SELECT created_at, tyre, controller_type 
                    FROM timing_leaderboard_entries 
                    WHERE player_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 1;
                """, (player_id,))
                result = await cursor.fetchone()

                if not result:
                    return "** **", "** **"

                timing_dt = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
                time_diff = abs((overtake_dt - timing_dt).total_seconds())

                if time_diff <= 3600:
                    tyre = result[1] or "** **"
                    controller_map = {1: "Keyboard", 2: "Controller", 3: "Wheel"}
                    controller_type = controller_map.get(result[2], "** **")
                    return tyre, controller_type
                else:
                    return "** **", "** **"
        except Exception as e:
            print(f"Timing Data Error: {e}")
            return "** **", "** **"

    async def fetch_player_name(self, player_id):
        try:
            async with aiosqlite.connect(DB_PATH) as conn:
                cursor = await conn.cursor()
                await cursor.execute("SELECT name FROM players WHERE player_id = ?;", (player_id,))
                result = await cursor.fetchone()
                return result[0] if result else "Unknown Player"
        except Exception as e:
            print(f"Database Error: {e}")
            return "Unknown Player"

    async def get_display_name(self, guild, discord_id, player_name):
        if discord_id is None:
            return player_name
        try:
            member = await guild.fetch_member(discord_id)
        except discord.NotFound:
            print(f"Member with ID {discord_id} not found in guild {guild.name}")
            return player_name
        except discord.Forbidden:
            print(f"Missing permissions to fetch member {discord_id} in guild {guild.name}")
            return player_name
        except Exception as e:
            print(f"Error fetching member: {e}")
            return player_name

        for role_id, emoji in ROLE_EMOJI_PRIORITY:
            if any(role.id == role_id for role in member.roles):
                return f"{emoji} {player_name}"

        return player_name

    async def get_position_suffix(self, position, for_button=False):
        if for_button:
            return f"Your {position} place on the leaderboard!"
        suffixes = {1: "🥇 1st", 2: "🥈 2nd", 3: "🥉 3rd"}
        return suffixes.get(position, f"🏅 {position}th")

    async def calculate_user_position(self, user_score, leaderboard_entries):
        position = 1
        for entry in leaderboard_entries:
            if entry[2] > user_score:
                position += 1
        return position

    async def save_message_id(self, message_id):
        with open(MESSAGE_ID_PATH, "w") as f:
            json.dump({"message_id": message_id}, f)

    async def load_message_id(self):
        try:
            with open(MESSAGE_ID_PATH, "r") as f:
                data = json.load(f)
                return data.get("message_id")
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    @app_commands.command(name="leaderboard", description="Post the leaderboard embed.")
    @app_commands.describe(channel="Select the channel to send the leaderboard to.")
    async def leaderboard(self, interaction: Interaction, channel: discord.TextChannel):
        if not any(role.id in ALLOWED_ROLE_IDS for role in interaction.user.roles):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer()
        embed = await self.create_leaderboard_embed(channel.guild)
        self.leaderboard_message = await channel.send(embed=embed, view=LeaderboardView(self))
        await self.save_message_id(self.leaderboard_message.id)
        await interaction.followup.send(f"Leaderboard embed sent to {channel.mention}.", ephemeral=True)

    async def create_leaderboard_embed(self, guild):
        leaderboard_entries = await self.fetch_leaderboard()
        if not leaderboard_entries:
            return discord.Embed(title="Cut Up Leaderboard | Top 10", description="No scores available.", color=0x36393F)

        leaderboard_entries = leaderboard_entries[:10]
        while len(leaderboard_entries) < 10:
            leaderboard_entries.append((None, None, 0, 0, "Unknown Car", None, None))

        embed = discord.Embed(title="Cut Up Leaderboard | Top 10", color=0x6A0DAD)
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1187595037937250315/1330833298179752036/leaderboard.png")

        for idx, entry in enumerate(leaderboard_entries, start=1):
            _, player_id, score, duration, car_name, discord_id, updated_at = entry
            discord_mention = f"<@{discord_id}>" if discord_id else "** **"
            raw_name = await self.fetch_player_name(player_id) if player_id else "No Player"
            clean_name = clean_player_name(raw_name)
            player_name = await self.get_display_name(guild, discord_id, clean_name)

            minutes, seconds = divmod(duration // 1000, 60)
            formatted_duration = f"{minutes}m {seconds}s"
            position_with_suffix = await self.get_position_suffix(idx)
            formatted_score = f"{score:,}".replace(",", ".")

            tyre, controller = await self.fetch_valid_timing_data(player_id, updated_at) if player_id and updated_at else ("** **", "** **")

            entry_text = (
                f"**Player:** {player_name} | {discord_mention}\n"
                f"**Score:** {formatted_score} Points\n"
                f"**Duration:** {formatted_duration}\n"
                f"**Car & Tyres:** {car_name} {tyre}\n"
                f"**Input:** {controller}"
            )
            embed.add_field(name=f"**{position_with_suffix}**", value=entry_text, inline=False)

        la_time = datetime.now(pytz.timezone("America/Los_Angeles")).strftime("%I:%M %p")
        embed.set_footer(text=f"Updated every 60 seconds • Last updated: {la_time}")
        return embed

    @tasks.loop(minutes=1)
    async def update_scores(self):
        if self.leaderboard_message is None:
            return
        try:
            embed = await self.create_leaderboard_embed(self.leaderboard_message.guild)
            await self.leaderboard_message.edit(embed=embed)
        except Exception as e:
            print(f"Error updating leaderboard: {e}")

    @update_scores.before_loop
    async def before_update_scores(self):
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

    async def callback(self, interaction: Interaction):
        discord_id = interaction.user.id
        try:
            async with aiosqlite.connect(DB_PATH) as conn:
                cursor = await conn.cursor()
                await cursor.execute("SELECT player_id FROM players_discord WHERE discord_userid = ?", (discord_id,))
                result = await cursor.fetchone()

                if not result:
                    embed = discord.Embed(
                        title="Not Whitelisted",
                        description=(
                            f"Hello {interaction.user.mention},\n\n"
                            "It seems you haven't been whitelisted yet.\n\n"
                            "Please head to https://discord.com/channels/1176727481634541608/1186581847732408401 to get whitelisted!"
                        ),
                        color=0x36393F
                    )
                    embed.set_footer(text="Brought to you by Future Crew™")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                player_id = result[0]
                leaderboard_entries = await self.leaderboard.fetch_leaderboard()
                entry_found = None
                user_position = "Unranked"

                for idx, entry in enumerate(leaderboard_entries, start=1):
                    if entry[1] == player_id:
                        entry_found = entry
                        user_position = await self.leaderboard.get_position_suffix(idx, for_button=True)
                        break

                if not entry_found:
                    embed = discord.Embed(
                        title="No Scores Found",
                        description=(
                            f"Hello {interaction.user.mention},\n\n"
                            "You do not have an entry in this leaderboard.\n\n"
                            "You can check again later, after you go ingame and get a new highscore!"
                        ),
                        color=0x36393F
                    )
                    embed.set_footer(text="Brought to you by Future Crew™")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

                _, _, score, duration, car_name, _, updated_at = entry_found
                formatted_score = f"{score:,}".replace(",", ".")
                minutes, seconds = divmod(duration // 1000, 60)
                formatted_duration = f"{minutes}m {seconds}s"

                tyre, controller = await self.leaderboard.fetch_valid_timing_data(player_id, updated_at)

                await cursor.execute("""
                    SELECT updated_at FROM overtake_n_leaderboard_entries 
                    WHERE player_id = ? ORDER BY score DESC LIMIT 1
                """, (player_id,))
                updated_at_result = await cursor.fetchone()
                run_date = datetime.strptime(updated_at_result[0], "%Y-%m-%d %H:%M:%S").strftime("%B %d %Y") if updated_at_result else "Unknown"

                embed = discord.Embed(
                    title="Your place on the leaderboard",
                    description=f"Hello {interaction.user.mention}, {user_position}",
                    color=0x36393F
                )
                embed.add_field(name="**Score**", value=formatted_score, inline=True)
                embed.add_field(name="**Duration**", value=formatted_duration, inline=True)
                embed.add_field(name="**Car Used**", value=car_name, inline=True)
                embed.add_field(name="**Tyres**", value=tyre, inline=True)
                embed.add_field(name="**Input**", value=controller, inline=True)
                embed.add_field(name="**Run Date**", value=run_date, inline=True)
                embed.set_footer(text="Brought to you by Future Crew™")

                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Database Error: {e}")
            await interaction.response.send_message("An error occurred while retrieving your score.", ephemeral=True)

class LeaderboardView(discord.ui.View):
    def __init__(self, leaderboard: Leaderboard):
        super().__init__(timeout=None)
        self.add_item(FindScoreButton(leaderboard))

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
