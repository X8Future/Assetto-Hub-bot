import discord
from discord.ext import commands
import sqlite3
import os

DB_PATH = '/root/Files/whitelist.db'

async def setup(bot: commands.Bot):
    @bot.tree.command(
        name="check_whitelist",
        description="Check a user's whitelist info and Steam ID."
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
                CREATE TABLE IF NOT EXISTS whitelist (
                    discord_id TEXT PRIMARY KEY,
                    steam_id TEXT,
                    attempts INTEGER DEFAULT 2
                );
            """)
            conn.commit()

            cursor.execute("SELECT steam_id, attempts FROM whitelist WHERE discord_id = ?", (str(user.id),))
            row = cursor.fetchone()

            steam_id = row[0] if row and row[0] else "NA"
            attempts = row[1] if row else 2

            embed = discord.Embed(title="Whitelist Check", color=0x36393e)
            embed.add_field(name="Discord Tag", value=user.mention, inline=True)
            embed.add_field(name="Discord ID", value=user.id, inline=True)
            embed.add_field(name="Steam ID", value=steam_id, inline=False)
            embed.add_field(name="Number of attempts", value=f"{attempts}/2", inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=False)
            conn.close()

        except Exception as e:
            print(f"Error checking whitelist: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while checking the whitelist.", ephemeral=True
            )
