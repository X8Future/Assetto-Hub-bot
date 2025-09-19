import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
import re

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_duration(self, duration_str: str) -> timedelta:
        """Parses duration string like '1h 5m 10s' into a timedelta."""
        hours = minutes = seconds = 0
        pattern = r"(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?"
        match = re.fullmatch(pattern, duration_str.strip())
        if match:
            h, m, s = match.groups()
            hours = int(h) if h else 0
            minutes = int(m) if m else 0
            seconds = int(s) if s else 0
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)

    @app_commands.command(name="timeout", description="Timeout a user and optionally add a strike")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        member="The member to timeout",
        duration="Duration format: 1h 5m 10s (default 10m)",
        reason="Reason for timeout",
        add_strike="Whether to add a strike (default True)"
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str = "10m",
        reason: str = "No reason provided",
        add_strike: bool = True
    ):
        try:
            delta = self.parse_duration(duration)
            if delta.total_seconds() <= 0:
                await interaction.response.send_message("❌ Invalid duration.", ephemeral=True)
                return

            await member.timeout(delta, reason=reason)
            await interaction.response.send_message(
                f"✅ {member.mention} has been timed out for {duration}. Reason: {reason}",
                ephemeral=False
            )

            if add_strike:
                automod_cog = self.bot.get_cog("AutoMod")
                if automod_cog:
                    await automod_cog.add_strike(member, f"Manual timeout: {reason}")

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I do not have permission to timeout this user.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to timeout user: {e}",
                ephemeral=True
            )

    @timeout.error
    async def timeout_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
