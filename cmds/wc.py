import discord
from discord.ext import commands
import sqlite3

# Path to your Hub.db
db_path = 'Path to data base file for hub. EX: /root/Bot-File/Hub.db'

async def setup(bot):
    @bot.tree.command(name="check_whitelist", description="Check a user's whitelist attempts and Steam ID.")
    async def check_whitelist(interaction: discord.Interaction, user: discord.User):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players_discord';")
            table_exists = cursor.fetchone()

            if table_exists:
                cursor.execute("SELECT player_id, discord_userid FROM players_discord WHERE discord_userid = ?", (user.id,))
                result = cursor.fetchone()

                if result:
                    player_id, discord_userid = result
                    
                    cursor.execute("SELECT attempts_left FROM whitelist_attempts WHERE discord_userid = ?", (user.id,))
                    attempts_result = cursor.fetchone()

                    if attempts_result:
                        attempts_left = attempts_result[0]
                    else:
                        attempts_left = 2

                    embed = discord.Embed(
                        title=f"Whitelist Information for {user.name}",
                        color=discord.Color.blue()
                    )

                    embed.add_field(name="Discord User", value=user.mention, inline=True)
                    embed.add_field(name="Steam ID", value=player_id, inline=True)
                    embed.add_field(name="Attempts Left", value=attempts_left, inline=False)

                    await interaction.response.send_message(embed=embed, ephemeral=False)
                else:
                    embed = discord.Embed(
                    title="Failed to get attempts on user", 
                    description=f"{user.mention} has not whitelisted or isnt in the database.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=False)
            else:
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

                await interaction.response.send_message("The 'players_discord' and 'whitelist_attempts' tables were created.", ephemeral=True)

            conn.close()

        except Exception as e:
            print(f"Error checking whitelist info: {e}")
            await interaction.response.send_message("There was an error checking the whitelist info.", ephemeral=True)
