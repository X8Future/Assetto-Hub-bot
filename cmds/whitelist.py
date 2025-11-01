import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite, aiohttp, asyncio, os, paramiko, logging, aiofiles

logging.getLogger("paramiko").setLevel(logging.WARNING)
logging.getLogger("paramiko").disabled = True

STEAM_API_KEY = ""
DATABASE = "whitelist.db"
MAX_ATTEMPTS = 2
DARK_MODE_COLOR = 0x2f3136
MAX_CONCURRENT_STEAM = 5
BATCH_SIZE = 5
BATCH_DELAY = 2
LOG_CHANNEL_ID = # Channel you want all your logs to go to
INPUT_TIMEOUT = 120
ROLE_TXT_DIR = "./steam_roles/"
ROLE_MAPPING = {
    "Lifetime": [, ],  # Role ID's you want the bot to look for the file groups 
    "Tier 2": [, ],
    "Tier 1": [, ],
}
ENDPOINTS = [
    {"host": "5.78.113.173", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Spec"},
    {"host": "5.78.103.54", "username": "root", "password": "Puppo4pres", "remote_path": "/root/FDR"},
    {"host": "5.78.93.251", "username": "root", "password": "Puppo4pres", "remote_path": "/root/C&R"},
    {"host": "5.78.93.251", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Content_Preview"},
    {"host": "5.78.93.251", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Whiteline"},
    {"host": "5.78.115.40", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Drift SRP"},
    {"host": "5.78.115.40", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Drift"},
    {"host": "91.99.6.152", "username": "root", "password": "Puppo4pres", "remote_path": "/root/FDR"},
    {"host": "91.99.6.152", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Hamburg C&R"},
    {"host": "91.99.6.152", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Hamburg Public"},
    {"host": "65.108.249.168", "username": "root", "password": "Puppo4pres", "remote_path": "/root/EU_SRP"},
    {"host": "65.108.249.168", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Non_DLC_Server"},
    {"host": "5.78.103.54", "username": "root", "password": "Puppo4pres", "remote_path": "/root/tgassp"},
    {"host": "5.78.129.133", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Freeroam"},
    {"host": "5.78.129.133", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Sandbox"},
    {"host": "5.78.75.101", "username": "root", "password": "Puppo4pres", "remote_path": "/root/German"},
    {"host": "5.78.75.101", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Hamburg Public"},
    {"host": "5.78.75.101", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Hamburg C&R"},
    {"host": "5.78.46.52", "username": "root", "password": "Puppo4pres", "remote_path": "/root/NA Non DLC"},
    {"host": "5.78.46.52", "username": "root", "password": "Puppo4pres", "remote_path": "/root/SRP"},
    {"host": "5.78.113.173", "username": "root", "password": "Puppo4pres", "remote_path": "/root/JDM"},
    {"host": "37.27.32.68", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Bot-File"},
]

class WhitelistCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_STEAM)
        self.db: aiosqlite.Connection | None = None
        self.session: aiohttp.ClientSession | None = None
        self.sftp_lock = asyncio.Lock()
        self.background_task = None
        self.upload_task = None
        self.dirty_files: set[str] = set()

    async def cog_load(self):
        os.makedirs(ROLE_TXT_DIR, exist_ok=True)
        for role_name in ROLE_MAPPING:
            file_path = os.path.join(ROLE_TXT_DIR, f"{role_name}.txt")
            if not os.path.exists(file_path):
                async with aiofiles.open(file_path, "w") as f:
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
        self.background_task = asyncio.create_task(self.periodic_role_checker())
        self.upload_task = asyncio.create_task(self.periodic_upload_checker())

    async def periodic_role_checker(self):
        while True:
            async with self.db.execute("SELECT discord_id FROM whitelist") as cursor:
                users = await cursor.fetchall()
            for i in range(0, len(users), BATCH_SIZE):
                batch = users[i:i + BATCH_SIZE]
                for (discord_id,) in batch:
                    for guild in self.bot.guilds:
                        member = guild.get_member(discord_id)
                        if member:
                            roles = [str(r.id) for r in member.roles if r != guild.default_role]
                            await self.mark_role_dirty(member, roles)
                await asyncio.sleep(BATCH_DELAY)
            await asyncio.sleep(300 - ((len(users) // BATCH_SIZE) * BATCH_DELAY))

    async def mark_role_dirty(self, member, roles):
        async with self.db.execute("SELECT steam_id FROM whitelist WHERE discord_id = ?", (member.id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return
        steam_id = row[0]
        for role_name, role_ids in ROLE_MAPPING.items():
            file_path = os.path.join(ROLE_TXT_DIR, f"{role_name}.txt")
            lines = []
            if os.path.exists(file_path):
                async with aiofiles.open(file_path, "r") as f:
                    lines = [l.strip() for l in await f.readlines() if l.strip()]
            has_role = any(int(r) in role_ids for r in roles)
            if has_role and steam_id not in lines:
                lines.append(steam_id)
            elif not has_role and steam_id in lines:
                lines.remove(steam_id)
            async with aiofiles.open(file_path, "w") as f:
                await f.write("\n".join(lines))
            self.dirty_files.add(file_path)

    async def periodic_upload_checker(self):
        while True:
            if not self.dirty_files:
                await asyncio.sleep(5)
                continue
            files_to_upload = list(self.dirty_files)
            self.dirty_files.clear()
            await self.upload_files(files_to_upload)
            await asyncio.sleep(5)

    async def upload_files(self, files_to_upload: list[str]):
        async with self.sftp_lock:
            log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
            if not log_channel:
                return

            embed = discord.Embed(title="Steam TXT Upload Status", color=DARK_MODE_COLOR)
            failed_files = []

            for file_path in files_to_upload:
                file_name = os.path.basename(file_path)
                file_failures = []

                for ep in ENDPOINTS:
                    transport = None
                    sftp = None
                    try:
                        transport = paramiko.Transport((ep["host"], 22))
                        transport.connect(username=ep["username"], password=ep["password"])
                        sftp = paramiko.SFTPClient.from_transport(transport)
                        remote_file = f"{ep['remote_path'].rstrip('/')}/{file_name}"
                        # Run blocking put in thread to avoid heartbeat blocking
                        await asyncio.to_thread(sftp.put, file_path, remote_file)
                    except Exception:
                        file_failures.append(ep["host"])
                    finally:
                        if sftp: sftp.close()
                        if transport: transport.close()

                if file_failures:
                    failed_files.append(file_name)
                    embed.add_field(name=f"{file_name} ❌ Failed", value=", ".join(file_failures), inline=False)
                else:
                    embed.add_field(name=f"{file_name} ✅ Uploaded", value="All endpoints", inline=False)

            await log_channel.send(embed=embed)

            if failed_files:
                await log_channel.send(f"<@807746550113370132> ⚠️ Some files failed to upload: {', '.join(failed_files)}")



    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            roles = [str(r.id) for r in after.roles if r != after.guild.default_role]
            await self.mark_role_dirty(after, roles)

    class SteamIDModal(discord.ui.Modal, title="Enter your Steam ID"):
        steam_id = discord.ui.TextInput(label="Steam ID", placeholder="Enter your Steam ID here")
        def __init__(self, cog, user_id, attempts, row):
            super().__init__()
            self.cog = cog
            self.user_id = user_id
            self.attempts = attempts
            self.row = row

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            steam_id = self.steam_id.value.strip()
            async with self.cog.semaphore:
                async with self.cog.session.get(
                    f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&steamids={steam_id}"
                ) as r:
                    data = await r.json()
                    players = data.get("response", {}).get("players", [])
                    if not players:
                        await interaction.followup.send("❌ Invalid Steam ID.", ephemeral=True)
                        return
                    player = players[0]

            async with self.cog.db.execute("SELECT discord_id FROM whitelist WHERE steam_id = ?", (steam_id,)) as cursor:
                existing = await cursor.fetchone()
            if existing:
                await interaction.followup.send(
                    "❌ SteamID already linked to another account. Contact an admin if this is yours.",
                    ephemeral=True
                )
                return

            guild = interaction.guild
            member = guild.get_member(self.user_id) or await guild.fetch_member(self.user_id)
            roles = ",".join([str(r.id) for r in member.roles if r != guild.default_role]) if member else ""
            if self.row:
                await self.cog.db.execute(
                    "UPDATE whitelist SET steam_id = ?, roles = ?, attempts = attempts + 1 WHERE discord_id = ?",
                    (steam_id, roles, self.user_id))
                attempts_used = self.attempts + 1
            else:
                await self.cog.db.execute(
                    "INSERT INTO whitelist (discord_id, steam_id, roles, attempts) VALUES (?, ?, ?, 1)",
                    (self.user_id, steam_id, roles))
                attempts_used = 1
            await self.cog.db.commit()
            if member:
                member_roles = [str(r.id) for r in member.roles if r != guild.default_role]
                await self.cog.mark_role_dirty(member, member_roles)

            embed = discord.Embed(
                title="✅ Steam ID Saved",
                description="Your Steam ID has been successfully linked!\n\n"
                            "It may take up to 15 minutes for verification to be fully completed",
                color=DARK_MODE_COLOR
            )
            embed.add_field(name="Discord Account", value=f"<@{interaction.user.id}> (`{self.user_id}`)", inline=False)
            embed.add_field(name="Steam ID", value=steam_id, inline=False)
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await interaction.followup.send(embed=embed, ephemeral=True)

            log_channel = self.cog.bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(title="Steam Account Linked", color=DARK_MODE_COLOR)
                embed.set_author(name=interaction.user, icon_url=interaction.user.display_avatar.url)
                embed.add_field(name="Steam Profile",
                                value=f"[{player.get('personaname', 'Unknown')}]({f'https://steamcommunity.com/profiles/{steam_id}'})",
                                inline=False)
                embed.add_field(name="Steam ID", value=steam_id, inline=False)
                embed.add_field(name="Discord Tag", value=f"<@{interaction.user.id}>", inline=False)
                embed.add_field(name="Attempts Used", value=str(attempts_used), inline=False)
                embed.set_thumbnail(url=player.get("avatarfull"))
                await log_channel.send(embed=embed)

    class StartView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog
            self.add_item(self.StartButton(cog))

        class StartButton(discord.ui.Button):
            def __init__(self, cog):
                super().__init__(label="Start Steam ID verification",
                                 style=discord.ButtonStyle.success,
                                 emoji="✅",
                                 custom_id="persistent_start_verification")
                self.cog = cog

            async def callback(self, interaction: discord.Interaction):
                await interaction.response.defer(ephemeral=True)
                user_id = interaction.user.id
                async with self.cog.db.execute("SELECT attempts FROM whitelist WHERE discord_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                attempts = row[0] if row else 0
                if attempts >= MAX_ATTEMPTS:
                    await interaction.followup.send("❌ Max attempts reached.", ephemeral=True)
                    return
                embed = discord.Embed(
                    title="Steam ID Whitelist Verification",
                    description=f"{interaction.user.mention}, you have **`{MAX_ATTEMPTS - attempts}` attempts** left.\n\n Click the button below to whitelist your Steam ID.",
                    color=DARK_MODE_COLOR
                )
                view = self.cog.InputView(self.cog, user_id, attempts, row)
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    class InputView(discord.ui.View):
        def __init__(self, cog, user_id, attempts, row):
            super().__init__(timeout=INPUT_TIMEOUT)
            self.cog = cog
            self.user_id = user_id
            self.attempts = attempts
            self.row = row

        @discord.ui.button(label="Whitelist your Steam ID", style=discord.ButtonStyle.primary, custom_id="input_steam_button")
        async def input_steam(self, interaction: discord.Interaction, button: discord.ui.Button):
            modal = self.cog.SteamIDModal(self.cog, self.user_id, self.attempts, self.row)
            await interaction.response.send_modal(modal)

        async def on_timeout(self):
            for child in self.children:
                child.disabled = True
            user = self.cog.bot.get_user(self.user_id)
            if user:
                embed = discord.Embed(
                    title="⏰ Verification Timed Out",
                    description="Your Steam ID input session expired. Please try again.",
                    color=DARK_MODE_COLOR
                )
                try:
                    await user.send(embed=embed)
                except:
                    pass

    async def cog_unload(self):
        if self.session:
            await self.session.close()
        if self.db:
            await self.db.close()
        if self.background_task:
            self.background_task.cancel()
        if self.upload_task:
            self.upload_task.cancel()

async def setup(bot):
    await bot.add_cog(WhitelistCog(bot))

