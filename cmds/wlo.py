import discord
from discord.ext import commands
import sqlite3
import aiohttp

# Configuration
STEAM_API_KEY = "90F58ADF94ED68134923FA78E07F7486"
STEAM_API_URL = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
DB_PATH = '/root/Bot-File/Hub.db'

ALLOWED_ROLE_ID = 1251377219910242365


class WLOCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def validate_steam_id(self, steam_id: str) -> bool:
        if not steam_id.isdigit() or len(steam_id) != 17:
            return False

        url = f"{STEAM_API_URL}?key={STEAM_API_KEY}&steamids={steam_id}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return False
                    data = await resp.json()
                    players = data.get("response", {}).get("players", [])
                    return bool(players)
        except:
            return False

    def get_current_steam_id(self, discord_id: int) -> str | None:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT player_id FROM players_discord WHERE discord_userid = ?", (str(discord_id),))
                result = cursor.fetchone()
                return result[0] if result else None
        except:
            return None

    def update_or_insert_steam_id(self, discord_id: int, new_steam_id: str) -> None:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM players_discord WHERE discord_userid = ?", (str(discord_id),))
                if cursor.fetchone():
                    cursor.execute("UPDATE players_discord SET player_id = ? WHERE discord_userid = ?", (new_steam_id, str(discord_id)))
                else:
                    cursor.execute("INSERT INTO players_discord (discord_userid, player_id) VALUES (?, ?)", (str(discord_id), new_steam_id))
                conn.commit()
        except:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        pass  # no logs as you asked

    @commands.command(hidden=True)
    async def sync(self, ctx):
        synced = await ctx.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands.")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.bot.tree.sync(guild=guild)

    @discord.app_commands.command(name="wlo", description="Override a user's Steam ID in the whitelist.")
    async def wlo(self, interaction: discord.Interaction, user: discord.User, new_steam_id: str):
        if not interaction.guild:
            await interaction.response.send_message("⚠️ This command must be used in a server.", ephemeral=True)
            return

        member = await interaction.guild.fetch_member(interaction.user.id)

        if ALLOWED_ROLE_ID not in [role.id for role in member.roles]:
            await interaction.response.send_message("⚠️ You do not have permission to use this command.", ephemeral=True)
            return

        # Defer response with ephemeral=False so success is public
        await interaction.response.defer(ephemeral=False)

        is_valid = await self.validate_steam_id(new_steam_id)
        if not is_valid:
            await interaction.followup.send("⚠️ Invalid or private Steam ID. Please check and try again.", ephemeral=True)
            return

        discord_id = user.id
        current_steam_id = self.get_current_steam_id(discord_id)

        if current_steam_id == new_steam_id:
            await interaction.followup.send("⚠️ This user already has the same Steam ID.", ephemeral=True)
            return

        self.update_or_insert_steam_id(discord_id, new_steam_id)

        embed = discord.Embed(
            title="✅ Steam ID Overridden",
            description=f"{user.mention} is now connected to Steam ID: `{new_steam_id}`.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Whitelist Update Successful")

        await interaction.followup.send(embed=embed, ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(WLOCog(bot))
