import discord
from discord.ext import commands
import sqlite3
import logging
import os

# Set up logging to capture errors
logging.basicConfig(level=logging.INFO)

# Define allowed role IDs (replace with actual role IDs)
REQUIRED_ROLE_IDS = [1196681600977616927]  # Replace with actual role IDs

# Database connection and user deletion
def delete_user_from_players_discord(discord_id):
    """Deletes a user from the players_discord database based on their discord_id."""
    try:
        # Absolute path to Hub.db
        db_path = '/root/Bot-File/Hub.db'


        # Check if the database file exists
        if not os.path.exists(db_path):
            print(f"Database file not found at {db_path}")
        else:
            print(f"Database file found at {db_path}")

        try:
            # Connect to the Hub.db database using the absolute path
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()

            # Check if the user exists in the players_discord table using discord_id
            cursor.execute("SELECT * FROM players_discord WHERE discord_userid = ?", (discord_id,))
            user_data = cursor.fetchone()

            if user_data:
                # Extract the player_id (Steam ID) and discord_userid for confirmation
                steam_id = user_data[1]  # Assuming player_id (Steam ID) is in the second column
                discord_userid = user_data[0]  # Assuming discord_userid is in the first column

                # Perform deletion of the user from the players_discord table
                cursor.execute("DELETE FROM players_discord WHERE discord_userid = ?", (discord_id,))
                connection.commit()

                # Also delete from the whitelist_attempts table if needed
                cursor.execute("DELETE FROM whitelist_attempts WHERE discord_userid = ?", (discord_id,))
                connection.commit()

                connection.close()
                return True, steam_id, discord_userid  # Return steam_id and discord_userid if deletion was successful
            else:
                connection.close()
                return False, None, None  # Return None values if user wasn't found
        except Exception as e:
            logging.error(f"Error deleting user from players_discord: {e}")
            return False, None, None

    except Exception as e:
        logging.error(f"Error deleting user from players_discord: {e}")
        return False, None, None

# Slash command for deleting a user from the players_discord table
@discord.app_commands.command(name="delete_user_players", description="Delete a user from the database.")
@discord.app_commands.describe(user="Select the Discord user to remove from the database.")
async def delete_user_players(interaction: discord.Interaction, user: discord.Member):
    """Slash command to delete a user from the players_discord table based on discord_id."""

    # Check if the user has at least one of the required roles
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

# Extension setup function to add the command to the bot
async def setup(bot: commands.Bot):
    """Setup function to add the command to the bot."""
    try:
        bot.tree.add_command(delete_user_players)
        logging.info("delete_user_players command successfully added.")
    except Exception as e:
        logging.error(f"Error setting up command: {e}")
