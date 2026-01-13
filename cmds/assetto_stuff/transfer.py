import sqlite3
import discord
from discord.ext import commands

HUB_DB_PATH = "/root/Bot-File/Hub.db"
WHITELIST_DB_PATH = "/root/Files/whitelist.db"
ADMIN_ROLE_ID = 1229301507233550419 


class SyncWhitelistCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(name="sync_whitelist", description="Sync Hub DB to Whitelist DB")
    async def sync_whitelist(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("⚠️ This command must be used in a server.", ephemeral=True)
            return

        try:
            member = await interaction.guild.fetch_member(interaction.user.id)
        except discord.NotFound:
            await interaction.response.send_message("⚠️ Could not fetch your member info.", ephemeral=True)
            return

        if ADMIN_ROLE_ID not in [role.id for role in member.roles]:
            await interaction.response.send_message("⚠️ You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Connect to databases
            hub_conn = sqlite3.connect(HUB_DB_PATH)
            hub_cursor = hub_conn.cursor()

            whitelist_conn = sqlite3.connect(WHITELIST_DB_PATH)
            whitelist_cursor = whitelist_conn.cursor()

            # Ensure whitelist table exists
            whitelist_cursor.execute("""
            CREATE TABLE IF NOT EXISTS whitelist (
                discord_id TEXT PRIMARY KEY,
                steam_id TEXT,
                roles TEXT,
                attempts INTEGER
            )
            """)

            # Fetch existing discord_ids in whitelist
            whitelist_cursor.execute("SELECT discord_id FROM whitelist")
            existing_ids = {row[0] for row in whitelist_cursor.fetchall()}

            # Fetch users from Hub DB
            hub_cursor.execute("SELECT discord_userid, player_id FROM players_discord")
            rows = hub_cursor.fetchall()
            processed_count = 0

            for discord_userid, player_id in rows:
                if discord_userid in existing_ids:
                    continue  # Skip users already in whitelist

                try:
                    user = await self.bot.fetch_user(int(discord_userid))
                    roles_str = ""
                    for guild in self.bot.guilds:
                        try:
                            member = await guild.fetch_member(user.id)
                            if member:
                                roles_str = ",".join([str(role.id) for role in member.roles if role.id != guild.id])
                                break
                        except discord.NotFound:
                            continue

                    whitelist_cursor.execute("""
                    INSERT INTO whitelist (discord_id, steam_id, roles, attempts)
                    VALUES (?, ?, ?, ?)
                    """, (discord_userid, player_id, roles_str, 1))

                    processed_count += 1
                except Exception as e:
                    print(f"Error processing user {discord_userid}: {e}")

            whitelist_conn.commit()
            hub_conn.close()
            whitelist_conn.close()

            await interaction.followup.send(f"✅ Sync complete. {processed_count} new users processed.", ephemeral=False)

        except Exception as e:
            await interaction.followup.send(f"⚠️ An error occurred during sync: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SyncWhitelistCog(bot))
