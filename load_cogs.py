import discord
from discord.ext import commands
from discord import app_commands

dynamic_cogs = [
    "whitelist",
    "wlo",
    "wc",
    "whitelist_delete",
    "add_run",
    "remove_player",
    "ban_user",
    "changetxt",
    "check_bans",
    "embedbuilder",
    "timeout",
    "automod",
    "timeout_remove",
    "remove_strike"
]

class LoadCogView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=60)
        self.bot = bot
        options = [discord.SelectOption(label=cog, value=cog) for cog in dynamic_cogs]
        self.add_item(LoadCogSelect(options, bot))

class LoadCogSelect(discord.ui.Select):
    def __init__(self, options, bot):
        super().__init__(placeholder="Select a cog to load...", min_values=1, max_values=1, options=options)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        cog_name = self.values[0]
        full_path = f"cmds.{cog_name}"
        if full_path in self.bot.extensions:
            await interaction.response.send_message(f"⚠️ {full_path} is already loaded.", ephemeral=True)
            return
        try:
            await self.bot.load_extension(full_path)
            await interaction.response.send_message(f"✅ Loaded {full_path}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to load {full_path}: {e}", ephemeral=True)

class DynamicCogLoader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="load_cog", description="Load a dynamic cog from a dropdown list")
    async def load_cog(self, interaction: discord.Interaction):
        """Slash command to show the cog dropdown"""
        view = LoadCogView(self.bot)
        await interaction.response.send_message("Select a cog to load:", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(DynamicCogLoader(bot))
