import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import asyncio
from datetime import datetime, timedelta

CATEGORY_ID = 1196682996514836541
STAFF_ROLE_ID = 1196681600977616927
CHANNEL_IDS_FILE = "server_status_channels.json"
MIN_UPDATE_INTERVAL = 120 

class ServerStatusVoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_ids: dict[str, int] = {}
        self.last_update: dict[int, datetime] = {}
        self.bot.loop.create_task(self.startup())
        self.update_loop.start()

    async def startup(self):
        await self.load_channel_ids()
        await self.update_all_channels()

    async def load_channel_ids(self):
        if os.path.exists(CHANNEL_IDS_FILE):
            try:
                with open(CHANNEL_IDS_FILE, "r") as f:
                    self.channel_ids = {k: int(v) for k, v in json.load(f).items()}
            except Exception:
                self.channel_ids = {}
        else:
            self.channel_ids = {}

    async def save_channel_ids(self):
        try:
            with open(CHANNEL_IDS_FILE, "w") as f:
                json.dump(self.channel_ids, f)
        except Exception:
            pass

    async def get_total_members_stat(self, guild: discord.Guild) -> str:
        if not guild.chunked:
            await guild.chunk(cache=True)
        return f"❮🔴❯│ All members: {len(guild.members)}"

    async def get_staff_online_stat(self, guild: discord.Guild) -> str:
        staff_role = guild.get_role(STAFF_ROLE_ID)
        if not staff_role:
            return "❮🟢❯│ Staff Online: Role not found"

        if not guild.chunked:
            await guild.chunk(cache=True)

        online_statuses = {discord.Status.online, discord.Status.idle, discord.Status.dnd}
        total_staff = len(staff_role.members)
        online_staff = sum(1 for m in staff_role.members if m.status in online_statuses)
        return f"❮🟢❯│ Staff Online: {online_staff}/{total_staff}"

    async def update_channel_name(self, channel: discord.VoiceChannel, stat_type: str):
        now = datetime.utcnow()
        last_time = self.last_update.get(channel.id)
        if last_time and (now - last_time).total_seconds() < MIN_UPDATE_INTERVAL:
            return

        new_name = None
        guild = channel.guild
        if stat_type == "total":
            new_name = await self.get_total_members_stat(guild)
        elif stat_type == "staff":
            new_name = await self.get_staff_online_stat(guild)

        if new_name and new_name != channel.name:
            try:
                await channel.edit(name=new_name)
                self.last_update[channel.id] = datetime.utcnow()
            except Exception:
                pass

    async def update_all_channels(self):
        to_remove = []
        for stat_type, channel_id in self.channel_ids.items():
            channel = self.bot.get_channel(channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                to_remove.append(stat_type)
                continue
            await self.update_channel_name(channel, stat_type)
        for stat_type in to_remove:
            self.channel_ids.pop(stat_type, None)
            await self.save_channel_ids()

    @tasks.loop(seconds=30)
    async def update_loop(self):
        await self.update_all_channels()

    async def create_status_channel(self, guild: discord.Guild, category: discord.CategoryChannel, stat_type: str, name: str):
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
            guild.me: discord.PermissionOverwrite(connect=True)
        }
        channel = await guild.create_voice_channel(
            name=name,
            category=category,
            overwrites=overwrites,
            reason=f"New server status voice channel created for {stat_type}"
        )
        self.channel_ids[stat_type] = channel.id
        self.last_update[channel.id] = datetime.utcnow()
        await self.save_channel_ids()
        return channel

    @app_commands.command(name="serverstatus")
    @app_commands.describe(
        track_total="Show total members count",
        track_staff_online="Show staff online count"
    )
    async def ServerStatus(
        self,
        interaction: discord.Interaction,
        track_total: bool = True,
        track_staff_online: bool = True,
    ):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("You must be an admin to use this command.", ephemeral=True)
            return
        category = guild.get_channel(CATEGORY_ID)
        if not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send("Category not found.", ephemeral=True)
            return
        if not (track_total or track_staff_online):
            await interaction.followup.send("You must track at least one stat.", ephemeral=True)
            return

        created_channels = []
        tasks_to_run = []
        if track_total:
            tasks_to_run.append(self.get_total_members_stat(guild))
        if track_staff_online:
            tasks_to_run.append(self.get_staff_online_stat(guild))

        results = await asyncio.gather(*tasks_to_run, return_exceptions=True)
        idx = 0
        if track_total:
            name = results[idx]
            idx += 1
            ch = await self.create_status_channel(guild, category, "total", name)
            created_channels.append(ch.mention)
        if track_staff_online:
            name = results[idx]
            ch = await self.create_status_channel(guild, category, "staff", name)
            created_channels.append(ch.mention)

        await interaction.followup.send(
            f"Created server status voice channels: {', '.join(created_channels)}",
            ephemeral=True
        )

    @app_commands.command(name="deletecounter")
    @app_commands.describe(channel_or_stat="Voice channel mention/ID or stat name (total, staff)")
    async def deletecounter(self, interaction: discord.Interaction, channel_or_stat: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an admin to use this command.", ephemeral=True)
            return

        arg = channel_or_stat.strip()
        channel = None
        stat = arg.lower()

        if stat in self.channel_ids:
            channel = self.bot.get_channel(self.channel_ids[stat])
        elif arg.startswith("<#") and arg.endswith(">") and arg[2:-1].isdigit():
            channel = self.bot.get_channel(int(arg[2:-1]))
        elif arg.isdigit():
            channel = self.bot.get_channel(int(arg))

        if not channel:
            await interaction.response.send_message("Could not find a matching stat or voice channel.", ephemeral=True)
            return

        found_stat = next((s for s, cid in self.channel_ids.items() if cid == channel.id), None)
        if not found_stat:
            await interaction.response.send_message("This channel is not a tracked status counter.", ephemeral=True)
            return

        try:
            await channel.delete(reason="Server status counter deleted by admin")
            self.channel_ids.pop(found_stat, None)
            self.last_update.pop(channel.id, None)
            await self.save_channel_ids()
            await interaction.response.send_message(f"Deleted server status counter channel: {channel.name}", ephemeral=True)
        except Exception:
            await interaction.response.send_message("Failed to delete the channel.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ServerStatusVoiceCog(bot))
