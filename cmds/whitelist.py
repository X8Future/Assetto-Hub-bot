import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import requests
import os

# Configuration
STEAM_API_KEY = "90F58ADF94ED68134923FA78E07F7486"  # Replace with your Steam API key
STEAM_API_URL = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"

db_path = '/root/Bot-File/Hub.db'

# Check if the database file exists
if not os.path.exists(db_path):
    print(f"Database file not found at {db_path}")
else:
    print(f"Database file found at {db_path}")

# SQLite database setup
conn = sqlite3.connect(db_path)  # Connect to 'Hub.db' in the Bot-File directory
cursor = conn.cursor()

# Check if 'players_discord' table exists and create it if not
cursor.execute("""
CREATE TABLE IF NOT EXISTS players_discord (
    discord_userid TEXT PRIMARY KEY,
    player_id TEXT UNIQUE
)
""")

# Check if 'whitelist_attempts' table exists and create it if not
cursor.execute("""
CREATE TABLE IF NOT EXISTS whitelist_attempts (
    discord_userid TEXT PRIMARY KEY,
    attempts_left INTEGER DEFAULT 2
)
""")
conn.commit()

# Function to validate Steam ID
def validate_steam_id(steam_id):
    """Validates the Steam ID by making a request to the Steam API."""
    try:
        params = {"key": STEAM_API_KEY, "steamids": steam_id}
        response = requests.get(STEAM_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        players = data.get("response", {}).get("players", [])
        return len(players) > 0
    except requests.RequestException as e:
        print(f"Error validating Steam ID: {e}")
        return False

# Function to check if a Steam ID is already taken
def is_steam_id_taken(steam_id):
    """Checks if the provided Steam ID is already associated with a Discord user."""
    cursor.execute("SELECT discord_userid FROM players_discord WHERE player_id = ?", (steam_id,))
    return cursor.fetchone() is not None

# Function to get the remaining attempts for a user
def get_remaining_attempts(discord_id):
    """Gets the remaining attempts for the provided Discord ID."""
    cursor.execute("SELECT attempts_left FROM whitelist_attempts WHERE discord_userid = ?", (discord_id,))
    row = cursor.fetchone()
    if row is None:
        # Default to 2 attempts if no record exists
        cursor.execute("INSERT INTO whitelist_attempts (discord_userid, attempts_left) VALUES (?, ?)", (discord_id, 2))
        conn.commit()
        return 2
    return row[0]

# Function to decrement attempts
def decrement_attempts(discord_id):
    """Decreases the number of attempts left for the provided Discord ID."""
    remaining = get_remaining_attempts(discord_id)
    if remaining > 0:
        cursor.execute("UPDATE whitelist_attempts SET attempts_left = ? WHERE discord_userid = ?", (remaining - 1, discord_id))
        conn.commit()
        return remaining - 1
    return 0

# Function to assign a role after successful Steam ID validation
async def assign_role_to_user(discord_user: discord.User, role_id: str):
    """Assigns a specific role to the user after validation."""
    guild = discord_user.guild
    role = discord.utils.get(guild.roles, id=int(role_id))  # Convert the role_id to int if needed

    if role:
        # Add role to the user
        await discord_user.add_roles(role)
        print(f"Role '{role.name}' assigned to {discord_user.name}")
    else:
        print(f"Role with ID '{role_id}' not found in server.")

# Modal to collect Steam ID
class SteamIDModal(discord.ui.Modal, title="Enter Your Steam ID"):
    steam_id = discord.ui.TextInput(label="Steam ID", placeholder="Enter your Steam ID")

    async def on_submit(self, interaction: discord.Interaction):
        steam_id = self.steam_id.value.strip()
        discord_id = str(interaction.user.id)

        if is_steam_id_taken(steam_id):
            await interaction.response.send_message(
                "This Steam ID is already taken. Contact an administrator if you are sure it is yours.",
                ephemeral=True
            )
            return

        if validate_steam_id(steam_id):
            decrement_attempts(discord_id)
            # Save the Steam ID and Discord ID in the players_discord table
            cursor.execute(
                "INSERT OR REPLACE INTO players_discord (discord_userid, player_id) VALUES (?, ?)",
                (discord_id, steam_id),
            )
            conn.commit()

            # Assign the role after successful verification
            await assign_role_to_user(interaction.user, "1331534717626880112")  # Replace with your actual role ID
            
            await interaction.response.send_message("Successfully added to the whitelist!", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid Steam ID. Please try again.", ephemeral=True)

# Second view with a button to trigger the Steam ID modal
class ContinueView(discord.ui.View):
    def __init__(self, attempts_left):
        super().__init__(timeout=None)  # Set timeout to None to keep the button active forever
        self.attempts_left = attempts_left

    @discord.ui.button(label="Press here to whitelist your Steam ID", style=discord.ButtonStyle.blurple)
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SteamIDModal()
        await interaction.response.send_modal(modal)

# First view with a "Whitelist" button
class WhitelistView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Set timeout to None to keep the button active forever

    @discord.ui.button(label="✅ Start Steam ID verification", style=discord.ButtonStyle.blurple)
    async def whitelist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        discord_id = str(interaction.user.id)
        attempts_left = get_remaining_attempts(discord_id)

        if attempts_left > 0:
            embed = discord.Embed(
                title="Whitelist Steam ID Verification",
                description=(f"Hello {interaction.user.mention}. You have `{attempts_left}` more tries to whitelist yourself.\n\n"
                             "Let's begin your whitelist process.\n\n"
                             "Press the button below, and insert your Steam ID."),
                color=discord.Color.from_str("#36393F")
            )
            view = ContinueView(attempts_left)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.send_message(
                "You have used all of your whitelist attempts. Contact an administrator for further assistance.",
                ephemeral=True
            )

# Slash command to initiate the whitelist process
@app_commands.command(name="whitelist", description="Post the whitelist embed in a specified channel.")
@app_commands.describe(channel="Select the channel to post the whitelist embed")
async def whitelist(interaction: discord.Interaction, channel: discord.TextChannel):
    embed = discord.Embed(
        title="Whitelist Steam ID Verification",
        description=("Press the button below to start the process\n\n"
                      "Make sure to have your Steam ID at hand\n"
                      "Find it here: https://discord.com/channels/1176727481634541608/1240318276840460380\n\n"
                      "by Future Crew"),
        color=discord.Color.from_str("#36393F") 
    )
    embed.set_thumbnail(url="https://media.discordapp.net/attachments/264328934353666048/1006907923135484024/download.gif")
    view = WhitelistView()

    await channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"Whitelist embed has been posted in {channel.mention}.", ephemeral=True)

# Extension setup function
async def setup(bot: commands.Bot):
    bot.tree.add_command(whitelist)
