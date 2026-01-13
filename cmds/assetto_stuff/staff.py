import discord
from discord.ext import commands, tasks
import os
import aiofiles
import aiosqlite
import asyncio
import paramiko

DATABASE = "/root/Files/whitelist.db"
TXT_DIR = "./special_roles_txts"

SPECIAL_ROLES = {
    "Staff": 1251377219910242365,
    "Dev": 1229301507233550419,
    "Content Creator": 1252107734481113149
}

SPECIAL_ROLE_FILES = {
    "Staff": "staff.txt",
    "Dev": "dev.txt",
    "Content Creator": "content_creator.txt"
}

ENDPOINTS = [
    {
        "host": "37.27.32.68",
        "username": "root",
        "password": "Puppo4pres",
        "remote_path": "/root/Bot-File/special_roles",
    },
]

UPLOAD_RETRIES = 3
UPLOAD_RETRY_DELAY = 1

class SpecialRoleWhitelist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sftp_lock = asyncio.Lock()
        self.dirty_files: set[str] = set()

        os.makedirs(TXT_DIR, exist_ok=True)
        for file in SPECIAL_ROLE_FILES.values():
            path = os.path.join(TXT_DIR, file)
            if not os.path.exists(path):
                open(path, "w").close()
            self.dirty_files.add(path)

        self.update_task.start()
        self.upload_task.start()

    def cog_unload(self):
        self.update_task.cancel()
        self.upload_task.cancel()

    @tasks.loop(minutes=2)
    async def update_task(self):
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute("SELECT discord_id FROM whitelist") as c:
                whitelist_users = await c.fetchall()

        for guild in self.bot.guilds:
            for discord_id, in whitelist_users:
                member = guild.get_member(discord_id)
                if not member:
                    continue

                for role_name, role_id in SPECIAL_ROLES.items():
                    path = os.path.join(TXT_DIR, SPECIAL_ROLE_FILES[role_name])

                    async with aiofiles.open(path, "r") as f:
                        current = set(l.strip() for l in await f.readlines() if l.strip())

                    changed = False
                    if any(r.id == role_id for r in member.roles):
                        if str(discord_id) not in current:
                            current.add(str(discord_id))
                            changed = True
                    else:
                        if str(discord_id) in current:
                            current.remove(str(discord_id))
                            changed = True

                    if changed:
                        self.dirty_files.add(path)
                        async with aiofiles.open(path, "w") as f:
                            await f.write("\n".join(sorted(current)))

    @tasks.loop(seconds=10)
    async def upload_task(self):
        if not self.dirty_files:
            return

        async with self.sftp_lock:
            files = list(self.dirty_files)
            self.dirty_files.clear()

            for file in files:
                filename = os.path.basename(file)
                for ep in ENDPOINTS:
                    success = False
                    for attempt in range(1, UPLOAD_RETRIES + 1):
                        transport = None
                        sftp = None
                        try:
                            transport = paramiko.Transport((ep["host"], 22))
                            transport.connect(username=ep["username"], password=ep["password"])
                            sftp = paramiko.SFTPClient.from_transport(transport)
                            remote_path = f"{ep['remote_path'].rstrip('/')}/{filename}"
                            await asyncio.to_thread(sftp.put, file, remote_path)
                            success = True
                            break
                        except Exception:
                            if attempt < UPLOAD_RETRIES:
                                await asyncio.sleep(UPLOAD_RETRY_DELAY)
                        finally:
                            if sftp:
                                sftp.close()
                            if transport:
                                transport.close()

                    if not success:
                        self.dirty_files.add(file)

async def setup(bot):
    await bot.add_cog(SpecialRoleWhitelist(bot))
