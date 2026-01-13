import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os
import logging

logging.basicConfig(level=logging.INFO)

DATABASE = # Full path of hub Ex:'/root/Bot-File/Hub.db'
ALLOWED_ROLE_ID =  # Allowed role ID that can use this command 
MAX_ATTEMPTS = 0 # Sets the number of attempts used to 0 (DO NOT TOUCH)
LOG_CHANNEL_ID =  # Set the channel ID you want it to be logged in here

class DatabaseAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = None

    async def cog_load(self):
        if not os.path.exists(DATABASE):
            logging.warning(f"Database file not found at {DATABASE}")
        self.db = await aiosqlite.connect(DATABASE)

    async def reset_user_whitelist(self, discord_id: int):
        async with self.db.execute(
            "SELECT steam_id, attempts FROM whitelist WHERE discord_id = ?", (discord_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False, None
            old_steam_id, old_attempts = row
        await self.db.execute(
            "UPDATE whitelist SET steam_id = NULL, attempts = ? WHERE discord_id = ?",
            (MAX_ATTEMPTS, discord_id)
        )
        await self.db.commit()
        return True, old_steam_id

    @app_commands.command(
        name="remove_whitelist",
        description="Reset a user's Steam ID and attempts in the whitelist database."
    )
    @app_commands.describe(user="Select the Discord user to reset.")
    async def remove_whitelist(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command must be used in a server.", ephemeral=True
            )
            return

        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            try:
                member = await interaction.guild.fetch_member(interaction.user.id)
            except:
                member = None

        if not member or all(role.id != ALLOWED_ROLE_ID for role in member.roles):
            await interaction.response.send_message(
                "⚠️ You do not have permission to use this command.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        success, old_steam_id = await self.reset_user_whitelist(user.id)

        if not success:
            await interaction.followup.send(
                f"⚠️ **{user}** (Discord ID: `{user.id}`) was not found in the whitelist database.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Whitelist Reset",
            color=0x2f3136
        )
        embed.add_field(name="User", value=f"{user} (`{user.id}`)", inline=False)
        embed.add_field(name="Previous Steam ID", value=f"{old_steam_id}", inline=False)
        embed.add_field(name="Staff Member", value=f"<@{interaction.user.id}>", inline=False)
        embed.set_footer(text="Whitelist reset performed")
        embed.set_thumbnail(url=user.display_avatar.url)

        await interaction.followup.send(embed=embed, ephemeral=True)

        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(DatabaseAdmin(bot))

