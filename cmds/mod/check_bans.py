import discord
from discord.ext import commands
import paramiko

ALLOWED_ROLE_ID = 1251377219910242365

class CheckBans(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="bannedlist", description="Shows all banned Steam IDs from remote blacklist.txt")
    async def bannedlist(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("⚠️ This command cannot be used in DMs.", ephemeral=True)
            return

        member = interaction.user  # Safely get member in slash command context
        if ALLOWED_ROLE_ID not in [role.id for role in member.roles]:
            await interaction.response.send_message("⚠️ You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer()

        HOST = "37.27.32.68"
        USERNAME = "root"
        PASSWORD = "Puppo4pres"
        REMOTE_PATH = "/root/Bot-File/blacklist.txt"

        try:
            transport = paramiko.Transport((HOST, 22))
            transport.connect(username=USERNAME, password=PASSWORD)
            sftp = paramiko.SFTPClient.from_transport(transport)

            with sftp.file(REMOTE_PATH, 'r') as remote_file:
                content = remote_file.read().decode('utf-8')

            sftp.close()
            transport.close()

            steam_ids = [line.strip() for line in content.splitlines() if line.strip()]
            if not steam_ids:
                await interaction.followup.send("No banned Steam IDs found in the blacklist.")
                return

            embed = discord.Embed(title="🚫 Banned Steam IDs", color=discord.Color.red())
            desc = "\n".join(f"`{sid}`" for sid in steam_ids)

            if len(desc) > 4096:
                desc = desc[:4090] + "..."

            embed.description = desc
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"Failed to fetch banned Steam IDs: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(CheckBans(bot))
