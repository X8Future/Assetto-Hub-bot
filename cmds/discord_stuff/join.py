import discord
from discord.ext import commands
from discord import app_commands
import json
import os

WELCOME_FILE = "welcome_channels.json"

class InviteWelcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channels = {}
        self.load_channels()

    def save_channels(self):
        with open(WELCOME_FILE, "w") as f:
            json.dump(self.channels, f)

    def load_channels(self):
        if os.path.exists(WELCOME_FILE):
            with open(WELCOME_FILE, "r") as f:
                self.channels = json.load(f)
        else:
            self.channels = {}

    @app_commands.command(
        name="enablewelcome",
        description="Enable welcome messages and set the channel"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def enable_welcome(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        guild = interaction.guild
        guild_id = str(guild.id)

        if guild_id in self.channels:
            existing_channel = guild.get_channel(self.channels[guild_id])
            mention = existing_channel.mention if existing_channel else f"`{self.channels[guild_id]}`"
            await interaction.response.send_message(
                f"❌ Welcome messages are already enabled in {mention}. Use `/welcomeset` to change it.",
                ephemeral=True
            )
            return

        self.channels[guild_id] = channel.id
        self.save_channels()

        await interaction.response.send_message(
            f"✅ Welcome messages enabled in {channel.mention}",
            ephemeral=True
        )

    @app_commands.command(
        name="welcomeset",
        description="Change the welcome message channel"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcome_set(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        guild_id = str(interaction.guild.id)

        if guild_id not in self.channels:
            await interaction.response.send_message(
                "❌ Welcome messages are not enabled. Use `/enablewelcome` first.",
                ephemeral=True
            )
            return

        self.channels[guild_id] = channel.id
        self.save_channels()

        await interaction.response.send_message(
            f"✅ Welcome messages will now be sent in {channel.mention}",
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild_id = str(member.guild.id)

        if guild_id not in self.channels:
            return

        channel = member.guild.get_channel(self.channels[guild_id])
        if not channel:
            return

        await channel.send(f"{member.mention} has joined **Future Crew**!")

async def setup(bot: commands.Bot):
    await bot.add_cog(InviteWelcome(bot))
