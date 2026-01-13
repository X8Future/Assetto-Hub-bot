import discord
from discord.ext import commands
from discord import app_commands
import paramiko
import os

BLACKLIST_FILE = "blacklist.txt"
ENDPOINTS = [
    {"host": "5.78.113.173", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Spec/blacklist.txt"},
    {"host": "5.78.103.54", "username": "root", "password": "Puppo4pres", "remote_path": "/root/FDR/blacklist.txt"},
    {"host": "5.78.93.251", "username": "root", "password": "Puppo4pres", "remote_path": "/root/C&R/blacklist.txt"},
    {"host": "5.78.93.251", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Content Preview/blacklist.txt"},
    {"host": "5.78.93.251", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Whiteline/blacklist.txt"},
    {"host": "5.78.115.40", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Drift SRP/blacklist.txt"},
    {"host": "5.78.115.40", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Drift/blacklist.txt"},
    {"host": "91.99.6.152", "username": "root", "password": "Puppo4pres", "remote_path": "/root/FDR/blacklist.txt"},
    {"host": "91.99.6.152", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Hamburg C&R/blacklist.txt"},
    {"host": "91.99.6.152", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Hamburg Public/blacklist.txt"},
    {"host": "65.108.249.168", "username": "root", "password": "Puppo4pres", "remote_path": "/root/EU SRP/blacklist.txt"},
    {"host": "65.108.249.168", "username": "root", "password": "Puppo4pres", "remote_path": "/root/EU DLC Server/blacklist.txt"},
    {"host": "5.78.103.54", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Horizon/blacklist.txt"},
    {"host": "5.78.129.133", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Freeroam/blacklist.txt"},
    {"host": "5.78.129.133", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Sandbox/blacklist.txt"},
    {"host": "5.78.75.101", "username": "root", "password": "Puppo4pres", "remote_path": "/root/German/blacklist.txt"},
    {"host": "5.78.75.101", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Hamburg Public/blacklist.txt"},
    {"host": "5.78.75.101", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Hamburg C&R/blacklist.txt"},
    {"host": "5.78.46.52", "username": "root", "password": "Puppo4pres", "remote_path": "/root/NA Non DLC/blacklist.txt"},
    {"host": "5.78.46.52", "username": "root", "password": "Puppo4pres", "remote_path": "/root/SRP/blacklist.txt"},
    {"host": "5.78.113.173", "username": "root", "password": "Puppo4pres", "remote_path": "/root/JDM/blacklist.txt"},
    {"host": "37.27.32.68", "username": "root", "password": "Puppo4pres", "remote_path": "/root/Bot-File/blacklist.txt"},
]

class ChangeTxt(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.sync_commands())

    async def sync_commands(self):
        await self.bot.wait_until_ready()
        guild_id = 1176727481634541608
        guild = discord.Object(id=guild_id)
        await self.bot.tree.sync(guild=guild)

    @app_commands.command(name="blacklist_remove", description="Remove a Steam ID from the blacklist and upload.")
    @app_commands.describe(steam_id="The Steam ID to remove from blacklist")
    async def blacklist_remove(self, interaction: discord.Interaction, steam_id: str):
        if interaction.guild is None:
            await interaction.response.send_message("This command cannot be used in DMs.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)

        if self.remove_steam_id_from_blacklist(steam_id):
            self.upload_file_to_all_endpoints(BLACKLIST_FILE)
            embed = discord.Embed(
                title="User Unbanned",
                description=f"Steam ID `{steam_id}` removed from blacklist and uploaded.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"Steam ID `{steam_id}` was not found in the blacklist.", ephemeral=True)

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

    def remove_steam_id_from_blacklist(self, steam_id: str) -> bool:
        if not os.path.exists(BLACKLIST_FILE):
            return False

        with open(BLACKLIST_FILE, "r") as f:
            lines = f.readlines()

        updated_lines = [line for line in lines if line.strip() != steam_id]

        if len(lines) == len(updated_lines):
            return False

        with open(BLACKLIST_FILE, "w") as f:
            f.writelines(updated_lines)
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
    await bot.add_cog(ChangeTxt(bot))
