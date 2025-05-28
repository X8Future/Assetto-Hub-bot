import discord
from discord.ext import commands
import sqlite3
from discord import app_commands

DB_PATH = '/root/Bot-File/Hub.db'
ALLOWED_ROLE_IDS = [1251377219910242365]

class LeaderboardRemove(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="remove_player", description="Removes a player from the leaderboard.")
    @app_commands.describe(
        option="Choose whether to remove by Discord user or Steam ID",
        reason="Reason for removal (DMs the user if applicable)",
        player_id="Steam ID (used if option is Steam ID)",
        discord_user="Discord user (used if option is Discord User)"
    )
    @app_commands.choices(option=[
        app_commands.Choice(name="Discord User", value="discord_user"),
        app_commands.Choice(name="Steam ID", value="player_id")
    ])
    async def remove_player(
        self,
        interaction: discord.Interaction,
        option: app_commands.Choice[str],
        reason: str,
        player_id: str = None,
        discord_user: discord.User = None
    ):
        # Permission check
        if interaction.guild is None:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        member = interaction.guild.get_member(interaction.user.id)
        if not member or not any(role.id in ALLOWED_ROLE_IDS for role in member.roles):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)  # Defer early to allow DB time

        # Get player_id from discord_user if selected
        if option.value == "discord_user":
            if not discord_user:
                await interaction.followup.send("❌ Please provide a Discord user.", ephemeral=True)
                return

            try:
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT player_id FROM players_discord WHERE discord_userid = ?", (str(discord_user.id),))
                    result = cursor.fetchone()

                if not result:
                    await interaction.followup.send("❌ Player not found in the `players_discord` table.", ephemeral=True)
                    return

                player_id = result[0]
            except Exception as e:
                print(f"[ERROR] Database lookup failed: {e}")
                await interaction.followup.send("⚠️ Error fetching player ID from the database.", ephemeral=True)
                return

        elif option.value == "player_id":
            if not player_id:
                await interaction.followup.send("❌ Please provide a Steam ID.", ephemeral=True)
                return

        # Final check
        if not player_id:
            await interaction.followup.send("⚠️ No player ID resolved. Cannot proceed.", ephemeral=True)
            return

        # Remove the player from the leaderboard
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT player_id FROM overtake_n_leaderboard_entries WHERE player_id = ?", (player_id,))
                entry = cursor.fetchone()

                if not entry:
                    await interaction.followup.send("❌ Player not found on the leaderboard.", ephemeral=True)
                    return

                cursor.execute("DELETE FROM overtake_n_leaderboard_entries WHERE player_id = ?", (player_id,))
                conn.commit()

        except Exception as e:
            print(f"[ERROR] Failed to delete player: {e}")
            await interaction.followup.send("⚠️ Error removing player from the leaderboard.", ephemeral=True)
            return

        # Try to DM the user if removed via Discord
        if option.value == "discord_user" and discord_user:
            try:
                await discord_user.send(
                    f"🚫 Your run has been removed from the **Future Crew Leaderboard**.\n"
                    f"**Reason:** {reason}\n\n"
                    "If you believe this was a mistake, please open a ticket. **Do not DM staff directly.**"
                )
            except discord.Forbidden:
                await interaction.followup.send("✅ Player removed. ⚠️ Could not DM the user (DMs disabled).", ephemeral=True)
                return

        await interaction.followup.send(f"✅ Player with Steam ID `{player_id}` has been removed from the leaderboard.", ephemeral=True)

# Setup function
async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardRemove(bot))
    await bot.tree.sync()
