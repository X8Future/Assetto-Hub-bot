import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import json
import os
import re
import asyncio
import aiofiles
import paramiko

SCORE_ROLE_IDS = {
    "whiteline": ,
    "verifiedwhiteline": ,
    "certifiedwhiteline": ,
}
# IDs of the roles you are matching them to in DISCORD 

PLACE_ROLES = {
    1: ,
    3: ,
    5: ,
    10: ,
}
# If you have roles based on place same thing, the role ID's your going to use

HUB_DB = # Full path of hub Ex:"/root/Bot-File/Hub.db"
WHITELIST_DB = "/root/Files/whitelist.db"
# Location where you whitelist.db file is located (should be in the main folder with all the other .jsons and bot.py file)
TXT_DIR = "./leaderboard_txts"
UPLOAD_RETRIES = 3
UPLOAD_RETRY_DELAY = 1

ENDPOINTS = [
    {
        "host": "37.27.32.68",
        "username": "root",
        "password": "",
        "remote_path": "/root/Bot-File",
    },
]
# Required Hub endpoint to send and get the roles to upload to all servers (only need hub endpoint)

SCORE_JSON_FILE = "score_requirements.json"

DEFAULT_SCORES = {
    "whiteline": 1_000_000,
    "verifiedwhiteline": 2_500_000,
    "certifiedwhiteline": 4_000_000,
}
# Set the default scores you want for the people to get these roles

POSITION_FILES = {
    "Top10": "top10.txt",
    "Top5": "top5.txt",
    "Top3": "top3.txt",
    "Champion": "champion.txt",
}
# The txt files you want uploaded (make sure they are the same that your servers are reading for the user groups)

def parse_score(value: str) -> int:
    value = value.upper().replace(",", "").strip()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([MBT]?)", value)
    if not match:
        raise ValueError
    number = float(match.group(1))
    suffix = match.group(2)
    multipliers = {"": 1, "M": 1_000_000, "B": 1_000_000_000, "T": 1_000_000_000_000}
    return int(number * multipliers[suffix])


def load_score_requirements():
    if os.path.exists(SCORE_JSON_FILE):
        with open(SCORE_JSON_FILE, "r") as f:
            return json.load(f)
    with open(SCORE_JSON_FILE, "w") as f:
        json.dump(DEFAULT_SCORES, f)
    return DEFAULT_SCORES.copy()


def save_score_requirements(data):
    with open(SCORE_JSON_FILE, "w") as f:
        json.dump(data, f)


class LeaderboardRoleSync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.score_requirements = load_score_requirements()
        self.dirty_files: set[str] = set()
        self.sftp_lock = asyncio.Lock()
        os.makedirs(TXT_DIR, exist_ok=True)
        for tier in SCORE_ROLE_IDS:
            path = os.path.join(TXT_DIR, f"{tier}.txt")
            if not os.path.exists(path):
                open(path, "w").close()
            self.dirty_files.add(path)
        for name, file in POSITION_FILES.items():
            path = os.path.join(TXT_DIR, file)
            if not os.path.exists(path):
                open(path, "w").close()
            self.dirty_files.add(path)
        self.auto_sync.start()
        self.periodic_txt_upload.start()

    def cog_unload(self):
        self.auto_sync.cancel()
        self.periodic_txt_upload.cancel()

    def get_leaderboard(self):
        conn = sqlite3.connect(HUB_DB)
        cur = conn.cursor()
        cur.execute("SELECT player_id, score FROM overtake_n_leaderboard_entries ORDER BY score DESC")
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_discord_id(self, steam_id):
        conn = sqlite3.connect(WHITELIST_DB)
        cur = conn.cursor()
        cur.execute("SELECT discord_id FROM whitelist WHERE steam_id = ?", (steam_id,))
        row = cur.fetchone()
        conn.close()
        return int(row[0]) if row else None

    async def write_steam_to_correct_tier(self, steam_id: str, score: int):
        sorted_tiers = sorted(self.score_requirements.items(), key=lambda x: x[1])
        tiers_to_include = {tier for tier, req in sorted_tiers if score >= req}
        for tier in self.score_requirements:
            path = os.path.join(TXT_DIR, f"{tier}.txt")
            async with aiofiles.open(path, "r") as f:
                current = set(l.strip() for l in await f.readlines() if l.strip())
            if tier in tiers_to_include:
                current.add(steam_id)
            else:
                current.discard(steam_id)
            async with aiofiles.open(path, "w") as f:
                await f.write("\n".join(sorted(current)))
            self.dirty_files.add(path)

    async def write_position_files(self, leaderboard):
        await self._write_position_file("Top10", [str(l[0]) for l in leaderboard[:10]])
        await self._write_position_file("Top5", [str(l[0]) for l in leaderboard[:5]])
        await self._write_position_file("Top3", [str(l[0]) for l in leaderboard[:3]])
        champion_id = [str(leaderboard[0][0])] if leaderboard else []
        await self._write_position_file("Champion", champion_id)

    async def _write_position_file(self, name, steam_ids):
        path = os.path.join(TXT_DIR, POSITION_FILES[name])
        async with aiofiles.open(path, "w") as f:
            await f.write("\n".join(steam_ids))
        self.dirty_files.add(path)

    async def sync_roles_internal(self, guild: discord.Guild):
        leaderboard = self.get_leaderboard()
        await self.write_position_files(leaderboard)
        for index, (steam_id, score) in enumerate(leaderboard, start=1):
            discord_id = self.get_discord_id(steam_id)
            if not discord_id:
                continue
            member = guild.get_member(discord_id)
            if not member:
                continue
            for tier, req in self.score_requirements.items():
                role_id = SCORE_ROLE_IDS[tier]
                role = guild.get_role(role_id)
                if not role:
                    continue
                higher_tiers = [r for t, r in self.score_requirements.items() if r > req]
                if score >= req and all(score < r for r in higher_tiers):
                    if role not in member.roles:
                        await member.add_roles(role)
                else:
                    if role in member.roles:
                        await member.remove_roles(role)
            eligible_places = [role_id for max_place, role_id in PLACE_ROLES.items() if index <= max_place]
            if eligible_places:
                best_role_id = min(eligible_places, key=lambda r: next(p for p, rid in PLACE_ROLES.items() if rid == r))
                for role_id in PLACE_ROLES.values():
                    role = guild.get_role(role_id)
                    if not role:
                        continue
                    if role_id == best_role_id:
                        if role not in member.roles:
                            await member.add_roles(role)
                    else:
                        if role in member.roles:
                            await member.remove_roles(role)
            await self.write_steam_to_correct_tier(str(steam_id), score)

    @tasks.loop(minutes=1)
    async def auto_sync(self):
        for guild in self.bot.guilds:
            try:
                await self.sync_roles_internal(guild)
            except Exception as e:
                print(f"[AUTO SYNC ERROR] {guild.name}: {e}")

    @auto_sync.before_loop
    async def before_auto_sync(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=2)
    async def periodic_txt_upload(self):
        if not self.dirty_files:
            return
        async with self.sftp_lock:
            files = list(self.dirty_files)
            self.dirty_files.clear()
            for file in files:
                filename = os.path.basename(file)
                for ep in ENDPOINTS:
                    for attempt in range(UPLOAD_RETRIES):
                        transport = None
                        sftp = None
                        try:
                            transport = paramiko.Transport((ep["host"], 22))
                            transport.connect(username=ep["username"], password=ep["password"])
                            sftp = paramiko.SFTPClient.from_transport(transport)
                            remote = f"{ep['remote_path'].rstrip('/')}/{filename}"
                            await asyncio.to_thread(sftp.put, file, remote)
                            break
                        except Exception:
                            await asyncio.sleep(UPLOAD_RETRY_DELAY)
                        finally:
                            if sftp:
                                sftp.close()
                            if transport:
                                transport.close()

    @periodic_txt_upload.before_loop
    async def before_txt_upload(self):
        await self.bot.wait_until_ready()

    @commands.command(name="syncroles")
    @commands.has_permissions(administrator=True)
    async def sync_roles(self, ctx):
        await self.sync_roles_internal(ctx.guild)
        await ctx.send("✅ Leaderboard roles & TXT files synced.")

    @app_commands.command(name="updaterequirementscore")
    async def update_requirement_score(self, interaction: discord.Interaction, tier: str, score: str):
        tier = tier.lower()
        if tier not in self.score_requirements:
            await interaction.response.send_message("❌ Invalid tier.", ephemeral=True)
            return
        try:
            parsed = parse_score(score)
        except ValueError:
            await interaction.response.send_message("❌ Invalid score format.", ephemeral=True)
            return
        self.score_requirements[tier] = parsed
        save_score_requirements(self.score_requirements)
        await interaction.response.send_message(f"✅ `{tier}` updated to **{parsed:,}**. Syncing roles…", ephemeral=True)
        await self.sync_roles_internal(interaction.guild)


async def setup(bot):
    await bot.add_cog(LeaderboardRoleSync(bot))


