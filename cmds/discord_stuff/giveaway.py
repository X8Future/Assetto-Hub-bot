import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import json, os, asyncio, random

GIVEAWAYS_FILE = "giveaways.json"
EMBED_COLOR = 0x36393F

def load_giveaways():
    if os.path.exists(GIVEAWAYS_FILE):
        try:
            with open(GIVEAWAYS_FILE, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            return {}
        giveaways = {}
        for k, v in data.items():
            v["entries"] = set(v.get("entries", []))
            v["end_time"] = datetime.fromisoformat(v["end_time"])
            giveaways[int(k)] = v
        return giveaways
    return {}

def save_giveaways(giveaways):
    to_save = {}
    for k, v in giveaways.items():
        v_copy = v.copy()
        v_copy["entries"] = list(v_copy["entries"])
        v_copy["end_time"] = v_copy["end_time"].isoformat()
        to_save[str(k)] = v_copy
    with open(GIVEAWAYS_FILE, "w") as f:
        json.dump(to_save, f, indent=2)

class GiveawayModal(discord.ui.Modal, title="Create Giveaway"):
    prize = discord.ui.TextInput(label="Prize", style=discord.TextStyle.short, required=True)
    duration = discord.ui.TextInput(label="Duration (days:hours:minutes)", style=discord.TextStyle.short, required=True)
    winners = discord.ui.TextInput(label="Number of Winners", style=discord.TextStyle.short, required=True)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            days, hours, minutes = map(int, self.duration.value.split(":"))
            duration_td = timedelta(days=days, hours=hours, minutes=minutes)
        except:
            await interaction.response.send_message("❌ Invalid duration format. Use days:hours:minutes", ephemeral=True)
            return

        try:
            num_winners = int(self.winners.value)
            if num_winners < 1:
                raise ValueError()
        except:
            await interaction.response.send_message("❌ Number of winners must be a positive integer.", ephemeral=True)
            return

        end_time = datetime.utcnow() + duration_td
        giveaway = {
            "prize": self.prize.value,
            "host_id": interaction.user.id,
            "host_mention": interaction.user.mention,
            "channel_id": interaction.channel.id,
            "message_id": None,
            "end_time": end_time,
            "entries": set(),
            "num_winners": num_winners
        }

        view = GiveawayView(giveaway, self.bot)
        embed = view.get_embed()
        await interaction.response.defer()
        message = await interaction.channel.send(embed=embed, view=view)
        giveaway["message_id"] = message.id
        self.bot.active_giveaways[message.id] = giveaway
        save_giveaways(self.bot.active_giveaways)
        view.message = message
        asyncio.create_task(view.wait_for_end())
        await interaction.followup.send(f"✅ Giveaway created in {interaction.channel.mention}", ephemeral=True)

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.giveaway = giveaway
        self.message = None

    async def wait_for_end(self):
        now = datetime.utcnow()
        delta = (self.giveaway["end_time"] - now).total_seconds()
        if delta > 0:
            await asyncio.sleep(delta)
        await self.end_giveaway()

    def get_embed(self):
        timestamp = int(self.giveaway["end_time"].timestamp())
        embed = discord.Embed(
            title="🎉 Giveaway!",
            description=f"Prize: **{self.giveaway['prize']}**\nHosted by: {self.giveaway['host_mention']}",
            color=EMBED_COLOR
        )
        embed.add_field(name="Total Entries", value=str(len(self.giveaway["entries"])))
        embed.add_field(name="Ends", value=f"<t:{timestamp}:R>")
        return embed

    @discord.ui.button(label="Enter Giveaway", style=discord.ButtonStyle.success)
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.giveaway["entries"]:
            await interaction.response.send_message("You already entered!", ephemeral=True)
            return
        self.giveaway["entries"].add(interaction.user.id)
        save_giveaways(self.bot.active_giveaways)
        await self.message.edit(embed=self.get_embed())
        await interaction.response.send_message(f"You entered the giveaway **{self.giveaway['prize']}**!", ephemeral=True)

    async def end_giveaway(self, early=False):
        if self.message.id not in self.bot.active_giveaways:
            return

        entries = list(self.giveaway["entries"])
        winners = []
        if entries:
            winners = random.sample(entries, min(self.giveaway["num_winners"], len(entries)))

        winner_mentions = [self.message.guild.get_member(w).mention if self.message.guild.get_member(w) else f"User ID {w}" for w in winners]
        winner_text = ", ".join(winner_mentions) if winners else "No winners"

        ended_embed = discord.Embed(
            title="🎉 Giveaway Ended!",
            description=f"Prize: **{self.giveaway['prize']}**\nHosted by: {self.giveaway['host_mention']}",
            color=EMBED_COLOR
        )
        ended_embed.add_field(name="Ended", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
        ended_embed.add_field(name="Total Entries", value=str(len(self.giveaway["entries"])))
        ended_embed.add_field(name="Winners", value=winner_text)
        ended_embed.set_footer(text=f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

        for child in self.children:
            child.disabled = True

        await self.message.edit(embed=ended_embed, view=self)
        self.bot.active_giveaways.pop(self.message.id)
        save_giveaways(self.bot.active_giveaways)

        if winners:
            await self.message.channel.send(f"🎉 Congratulations {winner_text}! You won the **{self.giveaway['prize']}**!")

class EndGiveawaySelect(discord.ui.Select):
    def __init__(self, bot):
        options = []
        for g in bot.active_giveaways.values():
            options.append(discord.SelectOption(
                label=g["prize"][:100],
                description=f"Hosted by {g['host_mention']}",
                value=str(g["message_id"])
            ))
        super().__init__(placeholder="Select a giveaway to end...", min_values=1, max_values=1, options=options)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        message_id = int(self.values[0])
        giveaway = self.bot.active_giveaways.get(message_id)
        if not giveaway:
            await interaction.response.send_message("❌ Giveaway not found.", ephemeral=True)
            return
        channel = self.bot.get_channel(giveaway["channel_id"])
        message = await channel.fetch_message(giveaway["message_id"])
        view = GiveawayView(giveaway, self.bot)
        view.message = message
        await view.end_giveaway(early=True)
        await interaction.response.send_message(f"✅ Giveaway **{giveaway['prize']}** ended early.", ephemeral=True)

class EndGiveawayView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(EndGiveawaySelect(bot))

class SimpleGiveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.active_giveaways = load_giveaways()
        self.bot.loop.create_task(self.rehydrate_views())
        self.update_loop.start()

    async def rehydrate_views(self):
        await self.bot.wait_until_ready()
        for giveaway in list(self.bot.active_giveaways.values()):
            channel = self.bot.get_channel(giveaway["channel_id"])
            if not channel:
                continue
            try:
                message = await channel.fetch_message(giveaway["message_id"])
            except:
                continue
            view = GiveawayView(giveaway, self.bot)
            view.message = message
            self.bot.add_view(view, message_id=message.id)
            asyncio.create_task(view.wait_for_end())

    @tasks.loop(seconds=60)
    async def update_loop(self):
        for giveaway in list(self.bot.active_giveaways.values()):
            channel = self.bot.get_channel(giveaway["channel_id"])
            if not channel:
                continue
            try:
                message = await channel.fetch_message(giveaway["message_id"])
            except:
                continue
            view = GiveawayView(giveaway, self.bot)
            view.message = message
            await message.edit(embed=view.get_embed())

    @app_commands.command(name="creategiveaway", description="Create a giveaway using a popup form")
    async def creategiveaway(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GiveawayModal(self.bot))

    @app_commands.command(name="endgiveaway", description="End an active giveaway via selection")
    async def endgiveaway(self, interaction: discord.Interaction):
        if not self.bot.active_giveaways:
            await interaction.response.send_message("❌ There are no active giveaways.", ephemeral=True)
            return
        view = EndGiveawayView(self.bot)
        await interaction.response.send_message("Select a giveaway to end:", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(SimpleGiveaway(bot))
