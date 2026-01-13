import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

APPEALS_ROLE_ID = 1227668177106768003

class RemoveStrike(commands.Cog):
    def __init__(self, bot, automod_cog):
        self.bot = bot
        self.automod = automod_cog

    @app_commands.command(name="removestrike", description="Remove strikes from a user")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        member="The member to remove strikes from",
        count="Number of strikes to remove (default all)"
    )
    async def removestrike(self, interaction: discord.Interaction, member: discord.Member, count: int = None):
        strikes = self.automod.strikes
        user_id = str(member.id)

        if user_id not in strikes or not strikes[user_id]:
            await interaction.response.send_message(f"❌ {member.display_name} has no strikes.", ephemeral=True)
            return

        if count is None or count >= len(strikes[user_id]):
            removed = len(strikes[user_id])
            strikes[user_id] = []
        else:
            removed = count
            strikes[user_id] = strikes[user_id][:-count]

        self.automod.save_strikes()

        active_strikes = len(strikes.get(user_id, []))
        if active_strikes < 2:
            try:
                await member.remove_timeout()
            except:
                pass

        if active_strikes < 3:
            appeals_role = member.guild.get_role(APPEALS_ROLE_ID)
            if appeals_role and appeals_role in member.roles:
                await member.remove_roles(appeals_role, reason="Strikes reduced below 3")

        await interaction.response.send_message(
            f"✅ Removed {removed} strike(s) from {member.display_name} and cleared active punishments.", ephemeral=True
        )

async def setup(bot):
    automod_cog = bot.get_cog("AutoMod")
    if automod_cog is None:
        raise RuntimeError("AutoMod cog must be loaded before RemoveStrike.")
    await bot.add_cog(RemoveStrike(bot, automod_cog))
