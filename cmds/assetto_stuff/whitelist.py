import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite, aiohttp, asyncio, os, paramiko, aiofiles, json
from datetime import datetime
from zoneinfo import ZoneInfo

STEAM_API_KEY = "" # Your Steam API Key
DATABASE = "whitelist.db"
MAX_ATTEMPTS = 2 # Set the total number of attempts a user can take to whitelist
MAX_CONCURRENT_STEAM = 5
INPUT_TIMEOUT = 120
UPLOAD_RETRIES = 3
UPLOAD_RETRY_DELAY = 1
ADMIN_ROLE_ID = # Allowed role ID that can use this command (just the ID, no quotes)
ROLE_TXT_DIR = "./steam_roles/"
CHANNEL_JSON = "log_channel.json"

ROLE_MAPPING = {
    "Lifetime": [, ],
    "Tier 2": [, ,],
    "Tier 1": [, ],
}
# Mapping for VIP tiers to be done instantly

TIER_PRIORITY = ["Lifetime", "Tier 2", "Tier 1"]
# Set priority so that users with multiple roles will only get the highest role

ENDPOINTS = [
    {"host": "37.27.32.68", "username": "root", "password": "", "remote_path": "/root/Bot-File"},
]
# Hub endpoint required to upload the txt's 

class WhitelistCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.session = None
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_STEAM)
        self.sftp_lock = asyncio.Lock()
        self.dirty_files: set[str] = set()
        self.role_task = None
        self.upload_task = None
        self.log_channel_id = None
        if os.path.exists(CHANNEL_JSON):
            with open(CHANNEL_JSON, "r") as f:
                self.log_channel_id = json.load(f).get("channel_id")

    async def cog_load(self):
        os.makedirs(ROLE_TXT_DIR, exist_ok=True)
        for role in ROLE_MAPPING:
            path = os.path.join(ROLE_TXT_DIR, f"{role}.txt")
            self.dirty_files.add(path)
            if not os.path.exists(path):
                async with aiofiles.open(path, "w") as f:
                    await f.write("")

        self.db = await aiosqlite.connect(DATABASE)
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS whitelist (
                discord_id INTEGER PRIMARY KEY,
                steam_id TEXT UNIQUE,
                roles TEXT,
                attempts INTEGER DEFAULT 0
            )
        """)
        await self.db.commit()
        self.session = aiohttp.ClientSession()
        self.bot.add_view(self.StartView(self))
        self.role_task = asyncio.create_task(self.periodic_role_checker())
        self.upload_task = asyncio.create_task(self.periodic_upload_checker())
        await self.bot.tree.sync()

    async def write_steam_to_correct_tiers(self, steam_id: str, member: discord.Member):
        for tier in ROLE_MAPPING:
            path = os.path.join(ROLE_TXT_DIR, f"{tier}.txt")
            async with aiofiles.open(path, "r") as f:
                lines = set(l.strip() for l in await f.readlines() if l.strip())
            lines.discard(steam_id)
            async with aiofiles.open(path, "w") as f:
                await f.write("\n".join(sorted(lines)))
            self.dirty_files.add(path)

        for tier, role_ids in ROLE_MAPPING.items():
            if any(role.id in role_ids for role in member.roles):
                path = os.path.join(ROLE_TXT_DIR, f"{tier}.txt")
                async with aiofiles.open(path, "r") as f:
                    lines = set(l.strip() for l in await f.readlines() if l.strip())
                lines.add(steam_id)
                async with aiofiles.open(path, "w") as f:
                    await f.write("\n".join(sorted(lines)))
                self.dirty_files.add(path)

    async def periodic_role_checker(self):
        while True:
            async with self.db.execute("SELECT discord_id, steam_id FROM whitelist") as c:
                users = await c.fetchall()
            for discord_id, steam_id in users:
                for guild in self.bot.guilds:
                    member = guild.get_member(discord_id)
                    if member:
                        await self.write_steam_to_correct_tiers(steam_id, member)
            await asyncio.sleep(300)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            async with self.db.execute("SELECT steam_id FROM whitelist WHERE discord_id=?", (after.id,)) as c:
                row = await c.fetchone()
            if row:
                await self.write_steam_to_correct_tiers(row[0], after)

    async def periodic_upload_checker(self):
        while True:
            if not self.dirty_files:
                await asyncio.sleep(5)
                continue
            async with self.sftp_lock:
                files = list(self.dirty_files)
                self.dirty_files.clear()
                for file in files:
                    filename = os.path.basename(file)
                    all_success = True
                    for ep in ENDPOINTS:
                        success = False
                        for attempt in range(1, UPLOAD_RETRIES + 1):
                            transport = None
                            sftp = None
                            try:
                                transport = paramiko.Transport((ep["host"], 22))
                                transport.connect(username=ep["username"], password=ep["password"])
                                sftp = paramiko.SFTPClient.from_transport(transport)
                                remote = f"{ep['remote_path'].rstrip('/')}/{filename}"
                                await asyncio.to_thread(sftp.put, file, remote)
                                success = True
                                break
                            except:
                                if attempt < UPLOAD_RETRIES:
                                    await asyncio.sleep(UPLOAD_RETRY_DELAY)
                            finally:
                                if sftp: sftp.close()
                                if transport: transport.close()
                        if not success:
                            all_success = False
                    if not all_success:
                        self.dirty_files.add(file)
            await asyncio.sleep(5)

    class SteamIDModal(discord.ui.Modal, title="Enter your Steam ID"):
        steam_id = discord.ui.TextInput(label="Steam ID")

        def __init__(self, cog, user_id, attempts, row, input_view):
            super().__init__()
            self.cog = cog
            self.user_id = user_id
            self.attempts = attempts
            self.row = row
            self.input_view = input_view

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            steam_id = self.steam_id.value.strip()
            async with self.cog.semaphore:
                async with self.cog.session.get(
                    f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&steamids={steam_id}"
                ) as r:
                    data = await r.json()
            if not data.get("response", {}).get("players"):
                embed = discord.Embed(
                    title="Steam Whitelist Verification",
                    description="This is an invalid Steam ID. Please check your ID and try again.\n\n"
                                "If you need help finding your Steam ID check here: https://discord.com/channels/1176727481634541608/1240318276840460380",
                    color=0x2f3136
                )
                embed.set_footer(text="Presented by Future Crew")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            player = data["response"]["players"][0]
            profile_name = player.get("personaname", "Unknown")
            profile_avatar = player.get("avatarfull", None)
            profile_url = player.get("profileurl", "")

            async with self.cog.db.execute("SELECT discord_id, attempts FROM whitelist WHERE steam_id=?", (steam_id,)) as c:
                existing = await c.fetchone()
            if existing:
                await interaction.followup.send("❌ Steam ID is already linked to another account. If you think this is a misatake, contact Staff via our ticket system.", ephemeral=True)
                return

            member = interaction.guild.get_member(self.user_id)
            roles = ",".join(str(r.id) for r in member.roles if r != interaction.guild.default_role)
            attempts_used = self.row[0] + 1 if self.row else 1

            if self.row:
                await self.cog.db.execute(
                    "UPDATE whitelist SET steam_id=?, roles=?, attempts=attempts+1 WHERE discord_id=?",
                    (steam_id, roles, self.user_id)
                )
            else:
                await self.cog.db.execute(
                    "INSERT INTO whitelist (discord_id, steam_id, roles, attempts) VALUES (?, ?, ?, 1)",
                    (self.user_id, steam_id, roles)
                )
            await self.cog.db.commit()
            await self.cog.write_steam_to_correct_tiers(steam_id, member)

            embed = discord.Embed(
                title="Success!",
                description="✅ You have been successfully Whitelisted onto Future Crew Servers!\n\n"
                            "The complete whitelist may take up to 15 minutes to get across all our Servers.\n\n"
                            "If issues persist contact Staff via our Tickets.",
                color=0x2f3136
            )
            embed.set_footer(text="Presented by Future Crew")
            await interaction.followup.send(embed=embed, ephemeral=True)

            if self.cog.log_channel_id:
                log_channel = interaction.guild.get_channel(self.cog.log_channel_id)
                if log_channel:
                    log_embed = discord.Embed(
                        title="Steam Account Linked",
                        color=0x2f3136
                    )
                    log_embed.set_author(name=member.name, icon_url=member.display_avatar.url)
                    if profile_avatar:
                        log_embed.set_thumbnail(url=profile_avatar)
                    log_embed.add_field(name="Steam Profile", value=f"[{profile_name}]({profile_url})", inline=False)
                    log_embed.add_field(name="Steam ID", value=steam_id, inline=False)
                    log_embed.add_field(name="Discord Tag", value=member.mention, inline=False)
                    log_embed.add_field(name="Discord ID", value=str(member.id), inline=False)
                    log_embed.add_field(name="Number of Attempts", value=f"{attempts_used}/{MAX_ATTEMPTS}", inline=False)

                    la_now = datetime.now(ZoneInfo("America/Los_Angeles"))
                    footer_text = la_now.strftime("%m/%d/%Y %I:%M %p") + " • Presented by Future Crew"
                    log_embed.set_footer(text=footer_text)

                    await log_channel.send(embed=log_embed)

    class StartView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="Start Steam ID verification", style=discord.ButtonStyle.success, custom_id="persistent_start_verification")
        async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
            async with self.cog.db.execute("SELECT attempts FROM whitelist WHERE discord_id=?", (interaction.user.id,)) as c:
                row = await c.fetchone()
            attempts = row[0] if row else 0
            remaining = MAX_ATTEMPTS - attempts
            if remaining <= 0:
                embed = discord.Embed(
                    title="Steam Whitelist Verification",
                    description=f"Hello {interaction.user.mention}, you no longer have any attempts remaining to whitelist.\n\nIf you need help whitelisting a new ID, please contact Staff via the Ticket Channel.",
                    color=0x2f3136
                )
                embed.set_footer(text="Presented by Future Crew")
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            embed = discord.Embed(
                title="Steam Whitelist Verification",
                description=f"Hello {interaction.user.mention}, you have `{remaining}` attempt(s) remaining to whitelist.\n\nTo start, press the **Whitelist Your Steam ID** button below.",
                color=0x2f3136
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="Presented by Future Crew")
            view = WhitelistCog.InputView(self.cog, interaction.user.id, attempts, row)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    class InputView(discord.ui.View):
        def __init__(self, cog, user_id, attempts, row):
            super().__init__(timeout=INPUT_TIMEOUT)
            self.cog = cog
            self.user_id = user_id
            self.attempts = attempts
            self.row = row

        @discord.ui.button(label="Whitelist your Steam ID", style=discord.ButtonStyle.primary)
        async def input(self, interaction: discord.Interaction, button: discord.ui.Button):
            modal = WhitelistCog.SteamIDModal(self.cog, self.user_id, self.attempts, self.row, self)
            await interaction.response.send_modal(modal)

    @app_commands.command(name="whitelist", description="Create a new whitelist embed in a specified channel")
    @app_commands.describe(channel="Select the channel where the whitelist embed will be sent")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_whitelist_embed(self, interaction: discord.Interaction, channel: discord.TextChannel):
        embed = discord.Embed(
            title="Whitelist Steam ID Verification",
            description="Press the button below to start the process.\n\nHave your Steam ID ready.\n\nFind it here: https://discord.com/channels/1176727481634541608/1240318276840460380",
            color=0x2f3136
        )
        embed.set_footer(text="Presented by Future Crew")
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/264328934353666048/1006907923135484024/download.gif")
        await channel.send(embed=embed, view=self.StartView(self))
        await interaction.response.send_message(f"✅ Whitelist embed created in {channel.mention}", ephemeral=True)

    @app_commands.command(name="setlogchannel", description="Set the logging channel for whitelist actions")
    @app_commands.describe(channel="Select the channel to log whitelist actions")
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message("❌ You do not have permission to set the log channel.", ephemeral=True)
            return
        self.log_channel_id = channel.id
        with open(CHANNEL_JSON, "w") as f:
            json.dump({"channel_id": self.log_channel_id}, f)
        await interaction.response.send_message(f"✅ Log channel set to {channel.mention}", ephemeral=True)

    async def cog_unload(self):
        if self.session:
            await self.session.close()
        if self.db:
            await self.db.close()
        if self.role_task:
            self.role_task.cancel()
        if self.upload_task:
            self.upload_task.cancel()

async def setup(bot):
    await bot.add_cog(WhitelistCog(bot))


