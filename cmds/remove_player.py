import discord
from discord.ext import commands
import sqlite3
from discord import app_commands

DB_PATH = '/root/Bot-File/Hub.db'

class LeaderboardRemove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="remove_player", description="Removes a player from the leaderboard")
    @app_commands.describe(
        option="Choose whether to remove by Discord user or player ID",
        reason="Reason for removal",
        player_id="Player ID (if known)",
        discord_user="Discord user (if removing by Discord ID)"
    )
    @app_commands.choices(
        option=[
            app_commands.Choice(name="Discord User", value="discord_user"),
            app_commands.Choice(name="Steam ID", value="player_id"),
        ]
    )
    async def remove_player(
        self,
        interaction: discord.Interaction,
        option: app_commands.Choice[str],
        reason: str,
        player_id: str = None,  # Change player_id to str to accept Steam IDs as strings
        discord_user: discord.User = None
    ):
        # Option: Remove by Discord user
        if option.value == "discord_user" and discord_user is not None:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT player_id FROM players_discord WHERE discord_userid = ?", (discord_user.id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                player_id = result[0]
            else:
                await interaction.response.send_message("Player not found in the players_discord table.", ephemeral=True)
                return

        elif option.value == "player_id" and player_id is not None:
            pass  # Steam ID is valid as a string, no need for conversion
        else:
            await interaction.response.send_message("Invalid option or missing required arguments.", ephemeral=True)
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT player_id FROM overtake_n_leaderboard_entries WHERE player_id = ?", (player_id,))
        result = cursor.fetchone()

        if result:
            cursor.execute("DELETE FROM overtake_n_leaderboard_entries WHERE player_id = ?", (player_id,))
            conn.commit()
            conn.close()

            if option.value == "discord_user":
                if discord_user:
                    await discord_user.send(
                        f"Your run has been removed off the Future Crew leaderboard due to suspected cheating or tampering. "
                        f"Reason provided by Staff: {reason}. If you feel this is unfair please contact a Staff member via tickets and **NOT DIRECTLY**."
                    )

            await interaction.response.send_message(f"Player with ID `{player_id}` has been removed from the leaderboard.", ephemeral=False)
        else:
            await interaction.response.send_message("Player not found on the leaderboard.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardRemove(bot))
    await bot.tree.sync()
