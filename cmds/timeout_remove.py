import discord
from discord.ext import commands
from discord import app_commands

STRIKE_FILE = "strikes.json"
from datetime import datetime, timedelta
import json
import os

class RemoveTimeout(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_strikes(self):
        if os.path.exists(STRIKE_FILE):
            with open(STRIKE_FILE, "r") as f:
                data = json.load(f)
                for user_id, timestamps in data.items():
                    data[user_id] = [datetime.fromisoformat(ts) for ts in timestamps]
                return data
        return {}

    def save_strikes(self, strikes):
        data = {str(uid): [ts.isoformat() for ts in entries] for uid, entries in strikes.items()}
        with open(STRIKE_FILE, "w") as f:
            json.dump(data, f, indent=4)

    @app_commands.command(
        name="removetimeout",
        description="Remove a timeout from a member and remove a strike"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        member="The member to remove timeout from"
    )
    async def removetimeout(self, interaction: discord.Interaction, member: discord.Member):
        try:
            await member.timeout(None, reason="Timeout removed by moderator")
            strikes = self.load_strikes()
            user_id = str(member.id)
            if user_id in strikes and strikes[user_id]:
                strikes[user_id].pop()
                if not strikes[user_id]:
                    del strikes[user_id]
                self.save_strikes(strikes)
                await interaction.response.send_message(
                    f"✅ Timeout removed and latest strike removed from {member.mention}.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"✅ Timeout removed from {member.mention}, but no strikes were found.",
                    ephemeral=True
                )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I do not have permission to remove timeout from this user.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to remove timeout: {e}",
                ephemeral=True
            )

    @removetimeout.error
    async def removetimeout_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Error: {error}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(RemoveTimeout(bot))
