import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import asyncio
import io
import json
import os

ROLE_IDS = {1196681600977616927, 1229301507233550419}
TICKET_CATEGORY_ID = 1192401489180770365
CLOSED_CATEGORY_ID = 1192402261003993118
RESTRICTED_ROLE_ID = 1186779915501187072
TRANSCRIPT_LOG_CHANNEL_ID = 1256764032048693270
PERSIST_FILE = "/root/Files/ticket_metadata.json"

PING_COOLDOWN_HOURS = 4
channel_creation_times = {}
user_open_tickets = {}
channel_metadata = {}

def user_is_staff(member: discord.Member) -> bool:
    return any(role.id in ROLE_IDS for role in member.roles)

def user_is_restricted(member: discord.Member) -> bool:
    return RESTRICTED_ROLE_ID in [role.id for role in member.roles] and not user_is_staff(member)

async def save_metadata():
    with open(PERSIST_FILE, "w") as f:
        json.dump(channel_metadata, f)

async def load_metadata():
    global channel_metadata
    if os.path.exists(PERSIST_FILE):
        with open(PERSIST_FILE, "r") as f:
            channel_metadata = json.load(f)
    else:
        channel_metadata = {}

async def create_ticket_channel(interaction: discord.Interaction, embed: discord.Embed, copyable_text: str):
    guild = interaction.guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    for role_id in ROLE_IDS:
        role = guild.get_role(role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    channel_name = f"ticket-{interaction.user.name}".lower().replace(" ", "-")[:90]
    category = guild.get_channel(TICKET_CATEGORY_ID)
    channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        category=category,
        reason=f"Ticket created by {interaction.user}"
    )

    channel_creation_times[channel.id] = datetime.utcnow()
    user_open_tickets[interaction.user.id] = channel.id

    role_mentions = " ".join(f"<@&{r_id}>" for r_id in ROLE_IDS)
    await channel.send(f"{role_mentions}\n\nHello {interaction.user.mention}, our admin team has been notified.")

    top_view = TicketTopButtons(interaction.user)
    main_msg = await channel.send(embed=embed, view=top_view)

    channel_metadata[str(channel.id)] = {
        "owner_id": interaction.user.id,
        "top_msg_id": main_msg.id,
        "last_closed_msg": None,
        "last_grey_msg": None
    }
    await save_metadata()
    return channel

class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Game Crashing", description="Report a problem about your game", emoji="⚠️"),
            discord.SelectOption(label="Discord or Maps", description="Map or Discord related issue", emoji="📍"),
            discord.SelectOption(label="Other", description="Other issues not in the above groups", emoji="⁉️")
        ]
        super().__init__(placeholder="Select a ticket category...", options=options, custom_id="ticket_category_select")

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id in user_open_tickets:
            channel_id = user_open_tickets[interaction.user.id]
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                await interaction.response.send_message(
                    f"❌ You already have an open ticket: {channel.mention}. Please close or delete it first.",
                    ephemeral=True
                )
                return
            else:
                del user_open_tickets[interaction.user.id]

        choice = self.values[0]
        modal = (
            GameCrashModal() if choice == "Game Crashing"
            else DiscordMapsModal() if choice == "Discord or Maps"
            else OtherIssueModal()
        )
        await interaction.response.send_modal(modal)

class TicketCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())

class TicketTopButtons(discord.ui.View):
    def __init__(self, ticket_owner: discord.User):
        super().__init__(timeout=None)
        self.ticket_owner = ticket_owner

    async def interaction_check(self, interaction):
        return True

    @discord.ui.button(label="Close Ticket", emoji="🔒", style=discord.ButtonStyle.secondary, custom_id="ticket_close")
    async def close_ticket(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        guild = interaction.guild
        closed_category = guild.get_channel(CLOSED_CATEGORY_ID)
        await channel.edit(category=closed_category)
        await channel.set_permissions(self.ticket_owner, send_messages=False, read_messages=True)
        user_open_tickets.pop(self.ticket_owner.id, None)

        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

        closed_embed = discord.Embed(description=f"Ticket closed by {interaction.user.mention}", color=0xFFFF00)
        explanation_embed = discord.Embed(        description=(
            f"Hello {interaction.user.mention},\n\n"
            "If you no longer need help, this ticket will be deleted within 48 hours.\n"
            "If you need further help, use the Open Ticket button to re-open the ticket."
        ), color=0x808080)
        bottom_view = TicketBottomButtons(self.ticket_owner)

        closed_msg = await channel.send(embed=closed_embed)
        grey_msg = await channel.send(embed=explanation_embed, view=bottom_view)

        meta = channel_metadata.get(str(channel.id))
        if meta:
            meta["last_closed_msg"] = closed_msg.id
            meta["last_grey_msg"] = grey_msg.id
        await save_metadata()


    @discord.ui.button(label="Ping Staff", emoji="📣", style=discord.ButtonStyle.secondary, custom_id="ticket_ping")
    async def ping_staff(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        now = datetime.utcnow()
        channel = interaction.channel
        created_at = channel_creation_times.get(channel.id, now)
        delta = now - created_at

        if delta < timedelta(hours=PING_COOLDOWN_HOURS):
            remaining = timedelta(hours=PING_COOLDOWN_HOURS) - delta
            mins = int(remaining.total_seconds() // 60)
            await interaction.followup.send(
                f"⚠️ You can only ping staff every {PING_COOLDOWN_HOURS}h per ticket. Try again in {mins} minutes.",
                ephemeral=True
            )
            return

        channel_creation_times[channel.id] = now
        role_mentions = " ".join(f"<@&{r_id}>" for r_id in ROLE_IDS)
        await channel.send(f"{role_mentions} — {interaction.user.mention} has requested staff attention!")
        await interaction.followup.send("✅ Staff have been pinged.", ephemeral=True)

class TicketBottomButtons(discord.ui.View):
    def __init__(self, ticket_owner: discord.User):
        super().__init__(timeout=None)
        self.ticket_owner = ticket_owner

    async def interaction_check(self, interaction):
        return True

    @discord.ui.button(label="Delete Ticket", emoji="🗑️", style=discord.ButtonStyle.secondary, custom_id="ticket_delete")
    async def delete_ticket(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user != self.ticket_owner and not user_is_staff(interaction.user):
            await interaction.followup.send("❌ You do not have permission to delete this ticket.", ephemeral=True)
            return
        if user_is_restricted(interaction.user):
            await interaction.followup.send("❌ You cannot delete tickets.", ephemeral=True)
            return
        user_open_tickets.pop(self.ticket_owner.id, None)
        await interaction.followup.send("🗑️ Deleting ticket...", ephemeral=True)
        await asyncio.sleep(0.1)
        await interaction.channel.delete()

    @discord.ui.button(label="Transcript", emoji="📄", style=discord.ButtonStyle.secondary, custom_id="ticket_transcript")
    async def transcript_ticket(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user != self.ticket_owner and not user_is_staff(interaction.user):
            await interaction.followup.send("❌ You do not have permission to get the transcript.", ephemeral=True)
            return
        if user_is_restricted(interaction.user):
            await interaction.followup.send("❌ You cannot get transcripts.", ephemeral=True)
            return

        messages = []
        users_in_transcript = set()
        async for msg in interaction.channel.history(limit=1000, oldest_first=True):
            messages.append(msg)
            users_in_transcript.add(msg.author)

        transcript_data = [ {
            "author": str(msg.author),
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
            "attachments": [att.url for att in msg.attachments],
            "embeds": [embed.to_dict() for embed in msg.embeds]
        } for msg in messages]

        transcript_bytes = json.dumps(transcript_data, indent=2).encode("utf-8")
        transcript_file = discord.File(io.BytesIO(transcript_bytes), filename=f"transcript-{interaction.channel.name}.json")

        embed = discord.Embed(
            description=f"Direct Transcript Attached\nUsers in transcript: {len(users_in_transcript)}",
            color=0x1c1d22
        )
        embed.set_footer(text=f"Ticket Owner: {self.ticket_owner}", icon_url=self.ticket_owner.display_avatar.url if self.ticket_owner else None)

        try:
            await interaction.user.send(embed=embed, file=transcript_file)
        except discord.Forbidden:
            await interaction.followup.send("❌ Cannot DM you the transcript. Enable DMs from server members.", ephemeral=True)

        log_channel = interaction.guild.get_channel(TRANSCRIPT_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed, file=transcript_file)

        await interaction.followup.send("📄 Transcript sent.", ephemeral=True)

    @discord.ui.button(label="Open Ticket", emoji="🔓", style=discord.ButtonStyle.secondary, custom_id="ticket_open")
    async def open_ticket(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        guild = interaction.guild
        open_category = guild.get_channel(TICKET_CATEGORY_ID)
        await channel.edit(category=open_category)
        await channel.set_permissions(self.ticket_owner, read_messages=True, send_messages=True)
        user_open_tickets[self.ticket_owner.id] = channel.id

        meta = channel_metadata.get(str(channel.id))
        if meta:
            try:
                top_msg = await channel.fetch_message(meta.get("top_msg_id"))
                await top_msg.edit(view=TicketTopButtons(self.ticket_owner))

                if meta.get("last_grey_msg"):
                    try:
                        grey_msg = await channel.fetch_message(meta.get("last_grey_msg"))
                        await grey_msg.delete()
                        meta["last_grey_msg"] = None
                    except discord.NotFound:
                        pass

                reopen_embed = discord.Embed(description=f"Ticket re-opened by {interaction.user.mention}", color=0x1c1d22)
                await channel.send(embed=reopen_embed)
            except discord.NotFound:
                pass
        await save_metadata()

class GameCrashModal(discord.ui.Modal, title="Game Crash Ticket"):
    description = discord.ui.TextInput(label="Describe when your game crashes", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction):
        embed = discord.Embed(description=f"**Game Crash Issue:**\n```{self.description.value}```", color=0x1c1d22)
        embed.set_footer(text=f"User ID: {interaction.user.id}")
        await interaction.response.defer(ephemeral=True)
        await create_ticket_channel(interaction, embed, self.description.value)
        await interaction.followup.send("✅ Ticket created!", ephemeral=True)

class DiscordMapsModal(discord.ui.Modal, title="Discord or Maps Ticket"):
    description = discord.ui.TextInput(label="Describe your issue", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction):
        embed = discord.Embed(description=f"**Discord or Maps Issue:**\n```{self.description.value}```", color=0x1c1d22)
        embed.set_footer(text=f"User ID: {interaction.user.id}")
        await interaction.response.defer(ephemeral=True)
        await create_ticket_channel(interaction, embed, self.description.value)
        await interaction.followup.send("✅ Ticket created!", ephemeral=True)

class OtherIssueModal(discord.ui.Modal, title="Other Issue Ticket"):
    description = discord.ui.TextInput(label="Describe your issue", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction):
        embed = discord.Embed(description=f"**Other Issue:**\n```{self.description.value}```", color=0x1c1d22)
        embed.set_footer(text=f"User ID: {interaction.user.id}")
        await interaction.response.defer(ephemeral=True)
        await create_ticket_channel(interaction, embed, self.description.value)
        await interaction.followup.send("✅ Ticket created!", ephemeral=True)

class TicketEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(TicketCategoryView())
        self.bot.loop.create_task(self.rehydrate_views())

    async def rehydrate_views(self):
        await self.bot.wait_until_ready()
        await load_metadata()

        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                meta = channel_metadata.get(str(channel.id))
                if not meta:
                    continue
                owner = guild.get_member(meta.get("owner_id"))
                if not owner:
                    continue

                if meta.get("last_grey_msg"):
                    try:
                        msg = await channel.fetch_message(meta["last_grey_msg"])
                        self.bot.add_view(TicketBottomButtons(owner), message_id=msg.id)
                    except discord.NotFound:
                        pass

                if meta.get("top_msg_id"):
                    try:
                        msg = await channel.fetch_message(meta["top_msg_id"])
                        self.bot.add_view(TicketTopButtons(owner), message_id=msg.id)
                    except discord.NotFound:
                        pass

    @app_commands.command(name="ticketbuilder", description="Send the ticket builder embed to a channel")
    async def ticketbuilder(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if not user_is_staff(interaction.user):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return
        if channel is None:
            channel = interaction.channel

        embed = discord.Embed(
            description=(
                "Need help? Find the option that best describes your issue. Please allow up to 12 hours for a response!\n"
                "Use the Ping Staff button to request staff attention."
            ),
            color=0x1c1d22
        )
        await channel.send(embed=embed, view=TicketCategoryView())
        await interaction.response.send_message(f"✅ Ticket embed sent to {channel.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketEmbed(bot))
