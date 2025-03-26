import discord
from discord.ext import commands
import sqlite3
import logging
import os

logging.basicConfig(level=logging.INFO)

REQUIRED_ROLE_IDS = []  # Replace with role ID that can use this command

# Database connection and user deletion
def delete_user_from_players_discord(discord_id):
    """Deletes a user from the players_discord database based on their discord_id."""
    try:
        db_path = '/root/Bot-File/Hub.db'


        if not os.path.exists(db_path):
            print(f"Database file not found at {db_path}")
        else:
            print(f"Database file found at {db_path}")

        try:
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()

            cursor.execute("SELECT * FROM players_discord WHERE discord_userid = ?", (discord_id,))
            user_data = cursor.fetchone()

            if user_data:
                steam_id = user_data[1] 
                discord_userid = user_data[0]

                cursor.execute("DELETE FROM players_discord WHERE discord_userid = ?", (discord_id,))
                connection.commit()

                cursor.execute("DELETE FROM whitelist_attempts WHERE discord_userid = ?", (discord_id,))
                connection.commit()

                connection.close()
                return True, steam_id, discord_userid
            else:
                connection.close()
                return False, None, None
        except Exception as e:
            logging.error(f"Error deleting user from players_discord: {e}")
            return False, None, None

    except Exception as e:
        logging.error(f"Error deleting user from players_discord: {e}")
        return False, None, None

@discord.app_commands.command(name="delete_user_players", description="Delete a user from the database.")
@discord.app_commands.describe(user="Select the Discord user to remove from the database.")
async def delete_user_players(interaction: discord.Interaction, user: discord.Member):
    """Slash command to delete a user from the players_discord table based on discord_id."""

    if not any(role.id in REQUIRED_ROLE_IDS for role in interaction.user.roles):
        await interaction.response.send_message("⚠️ You do not have permission to use this command.", ephemeral=True)
        return

    try:
        discord_id = user.id
        success, steam_id, discord_userid = delete_user_from_players_discord(discord_id)

        if success:
            await interaction.response.send_message(
                f"✅ Successfully removed **{user.name}** (Discord ID: {discord_userid}, Steam ID: {steam_id}) from the database.",
                ephemeral=False,
            )
        else:
            await interaction.response.send_message(
                f"⚠️ **{user.name}** (Discord ID: {discord_id}) was not found in the database.",
                ephemeral=True,
            )
    except Exception as e:
        logging.error(f"Error in slash command: {e}")
        await interaction.response.send_message("⚠️ An error occurred while trying to delete the user from the database.", ephemeral=True)

async def setup(bot: commands.Bot):
    """Setup function to add the command to the bot."""
    try:
        bot.tree.add_command(delete_user_players)
        logging.info("delete_user_players command successfully added.")
    except Exception as e:
        logging.error(f"Error setting up command: {e}")
