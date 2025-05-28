import discord
from discord.ext import commands
import sqlite3
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)

DB_PATH = '/root/Bot-File/Hub.db'
REQUIRED_ROLE_IDS = [1251377219910242365]

class DatabaseAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def delete_user_from_players_discord(self, discord_id):
        try:
            if not os.path.exists(DB_PATH):
                logging.warning(f"Database file not found at {DB_PATH}")
                return False, None, None

            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM players_discord WHERE discord_userid = ?", (discord_id,))
                user_data = cursor.fetchone()

                if user_data:
                    steam_id = user_data[1]
                    discord_userid = user_data[0]

                    cursor.execute("DELETE FROM players_discord WHERE discord_userid = ?", (discord_id,))
                    cursor.execute("DELETE FROM whitelist_attempts WHERE discord_userid = ?", (discord_id,))
                    conn.commit()

                    return True, steam_id, discord_userid
                else:
                    return False, None, None

        except Exception as e:
            logging.error(f"DB error: {e}")
            return False, None, None

    @discord.app_commands.command(name="delete_user_players", description="Delete a user from the players_discord table.")
    @discord.app_commands.describe(user="Select the Discord user to remove from the database.")
    async def delete_user_players(self, interaction: discord.Interaction, user: discord.Member):
        if interaction.guild is None:
            await interaction.response.send_message("❌ Command must be used in a server.", ephemeral=True)
            return

        member = interaction.guild.get_member(interaction.user.id)
        if not member or not any(role.id in REQUIRED_ROLE_IDS for role in member.roles):
            await interaction.response.send_message("⚠️ You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        discord_id = user.id
        success, steam_id, discord_userid = self.delete_user_from_players_discord(discord_id)

        if success:
            await interaction.followup.send(
                f"✅ Removed **{user.name}** (Discord ID: `{discord_userid}`, Steam ID: `{steam_id}`) from the database.",
                ephemeral=False,
            )
        else:
            await interaction.followup.send(
                f"⚠️ **{user.name}** (Discord ID: `{discord_id}`) was not found in the database.",
                ephemeral=True,
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(DatabaseAdmin(bot))
    await bot.tree.sync()
