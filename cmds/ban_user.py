import discord
from discord.ext import commands
from discord import app_commands
import paramiko
import os

BLACKLIST_FILE = "blacklist.txt"
ENDPOINTS = [ # Where you want the bot to check for the txt to ban users, make as many as you want, the more you make the longer it will take the bot to run it
    {"host": "ServerIP", "username": "Whatyouusetosignin", "password": "Yourpasswordhere", "remote_path": "/root/Servername/blacklist.txt"},
]

class BanUser(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.sync_commands())

    async def sync_commands(self):
        await self.bot.wait_until_ready()
        guild_id = 1176727481634541608
        guild = discord.Object(id=guild_id)
        await self.bot.tree.sync(guild=guild)

    @app_commands.command(name="ban_user", description="Ban a user by Steam ID and send updated blacklist to servers.")
    @app_commands.describe(steam_id="The Steam ID to ban")
    async def ban_user(self, interaction: discord.Interaction, steam_id: str):
        if interaction.guild is None:
            await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if self.add_steam_id_to_blacklist(steam_id):
            self.upload_file_to_all_endpoints(BLACKLIST_FILE)
            embed = discord.Embed(
                title="User Banned",
                description=f"Steam ID `{steam_id}` banned and successfully uploaded to all endpoints.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            await interaction.followup.send(f"Steam ID `{steam_id}` is already in the blacklist.", ephemeral=True)

    def add_steam_id_to_blacklist(self, steam_id: str) -> bool:
        if not os.path.exists(BLACKLIST_FILE):
            with open(BLACKLIST_FILE, "w") as f:
                f.write(steam_id + "\n")
            return True

        with open(BLACKLIST_FILE, "r") as f:
            if steam_id in [line.strip() for line in f]:
                return False

        with open(BLACKLIST_FILE, "a") as f:
            f.write(steam_id + "\n")
        return True

    def upload_file_to_all_endpoints(self, local_path):
        for endpoint in ENDPOINTS:
            try:
                transport = paramiko.Transport((endpoint["host"], 22))
                transport.connect(username=endpoint["username"], password=endpoint["password"])
                sftp = paramiko.SFTPClient.from_transport(transport)
                sftp.put(local_path, endpoint["remote_path"])
                sftp.close()
                transport.close()
            except Exception as e:
                print(f"[UPLOAD ERROR] {endpoint['host']}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(BanUser(bot))
