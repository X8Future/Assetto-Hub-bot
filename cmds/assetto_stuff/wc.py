import discord
from discord.ext import commands
import sqlite3
import os

DB_PATH = # Full path of hub Ex:'/root/Bot-File/Hub.db'

async def setup(bot: commands.Bot):
    @bot.tree.command(
        name="check_whitelist",
        description="Check a user's whitelist attempts and Steam ID."
    )
    async def check_whitelist(interaction: discord.Interaction, user: discord.User):
        if interaction.guild is None:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        if not os.path.exists(DB_PATH):
            await interaction.response.send_message("❌ Database not found.", ephemeral=True)
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS players_discord (
                    discord_userid TEXT PRIMARY KEY,
                    player_id TEXT UNIQUE
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS whitelist_attempts (
                    discord_userid TEXT PRIMARY KEY,
                    attempts_left INTEGER DEFAULT 2
                );
            """)
            conn.commit()

            cursor.execute("SELECT player_id FROM players_discord WHERE discord_userid = ?", (str(user.id),))
            row = cursor.fetchone()

            if row:
                steam_id = row[0]

                cursor.execute("SELECT attempts_left FROM whitelist_attempts WHERE discord_userid = ?", (str(user.id),))
                attempts = cursor.fetchone()
                attempts_left = attempts[0] if attempts else 2

                embed = discord.Embed(
                    title=f"Whitelist Info for {user.name}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Discord User", value=user.mention, inline=True)
                embed.add_field(name="Steam ID", value=steam_id, inline=True)
                embed.add_field(name="Attempts Left", value=attempts_left, inline=False)

                await interaction.response.send_message(embed=embed, ephemeral=False)
            else:
                embed = discord.Embed(
                    title="User Not Found",
                    description=f"{user.mention} is not in the whitelist database.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=False)

            conn.close()

        except Exception as e:
            print(f"Error checking whitelist: {e}")
            await interaction.response.send_message("❌ An error occurred while checking the whitelist.", ephemeral=True)

