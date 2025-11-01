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

class LoadCogSelect(discord.ui.Select):
    def __init__(self, options, bot):
        super().__init__(
            placeholder="Select a cog...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        cog_name = self.values[0]
        full_path = f"cmds.{cog_name}"
        await interaction.response.defer(ephemeral=True)

        if full_path in self.bot.extensions:
            await interaction.followup.send(f"⚠️ `{full_path}` is already loaded.", ephemeral=True)
            return

        try:
            await self.bot.load_extension(full_path)
            self.bot.tree.copy_global_to(guild=interaction.guild)
            await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send(f"✅ Loaded `{full_path}` and synced commands!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to load `{full_path}`: `{e}`", ephemeral=True)

class LoadCogView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=60)
        self.bot = bot
        options = [discord.SelectOption(label=cog, value=cog) for cog in dynamic_cogs]
        self.add_item(LoadCogSelect(options, bot))

class DynamicCogLoader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_views = []

    @app_commands.command(name="load_cog", description="Load a dynamic cog from a dropdown list")
    async def load_cog(self, interaction: discord.Interaction):
        view = LoadCogView(self.bot)
        self.active_views.append(view)
        await interaction.response.send_message("Select a cog to load:", view=view, ephemeral=True)

    @app_commands.command(name="unload_cog", description="Unload a dynamic cog")
    async def unload_cog(self, interaction: discord.Interaction, cog_name: str):
        full_path = f"cmds.{cog_name}"
        await interaction.response.defer(ephemeral=True)

        if full_path not in self.bot.extensions:
            await interaction.followup.send(f"⚠️ `{full_path}` is not loaded.", ephemeral=True)
            return

        try:
            await self.bot.unload_extension(full_path)
            await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send(f"✅ Unloaded `{full_path}` and synced commands!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to unload `{full_path}`: `{e}`", ephemeral=True)

    @app_commands.command(name="reload_cog", description="Reload a dynamic cog")
    async def reload_cog(self, interaction: discord.Interaction, cog_name: str):
        full_path = f"cmds.{cog_name}"
        await interaction.response.defer(ephemeral=True)

        try:
            if full_path in self.bot.extensions:
                await self.bot.reload_extension(full_path)
            else:
                await self.bot.load_extension(full_path)
            self.bot.tree.copy_global_to(guild=interaction.guild)
            await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send(f"✅ Reloaded `{full_path}` and synced commands!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to reload `{full_path}`: `{e}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(DynamicCogLoader(bot))
