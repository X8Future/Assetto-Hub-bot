import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
from collections import defaultdict
from datetime import datetime, timedelta
import re
import json
import os

IMMUNE_ROLES = {1251377219910242365}
HARD_BAD_WORDS = [
    "fuck", "shit", "bitch", "asshole", "dick", "cunt", "nigger", "faggot", "slut", "whore",
    "porn", "sex", "cock", "pussy", "nigga", "hoe", "douche", "twat", "rape"
]
BAD_WORD_KEYWORDS = ["sex", "porn", "erotic", "hentai", "nude", "cam", "xxx"]
HARD_BLOCKED_DOMAINS = [
    "pornhub.com", "xvideos.com", "xnxx.com", "redtube.com", "youporn.com", "tube8.com",
    "spankbang.com", "adultfriendfinder.com", "beeg.com", "hentaihaven.org", "rule34.xxx", "onlyfans.com"
]
ADULT_SITE_KEYWORDS = ["porn", "xxx", "sex", "hentai", "adult", "tube", "erotic", "cam"]
WHITELISTED_INVITES = {
    "discord.gg/futurecrew",
    "discord.gg/nohesi",
    "discord.gg/teamgetactive",
    "discord.gg/5KjwpzrKyN",
    "discord.gg/shutokorevivalproject",
    "discord.gg/ETRpbujrJn",
    "discord.gg/highspeed",
    "discord.gg/D7f84sMNRg"
}
IMAGE_SPAM_LIMIT = 5
IMAGE_SPAM_INTERVAL = 10
WORD_SPAM_LIMIT = 5
WORD_SPAM_INTERVAL = 10
STRIKE_DURATION_DAYS = 90
BYPASS_CHANNELS = {1229329019850457118, 1229329089941340251, 1229329337400954911}
STRIKE_FILE = "strikes.json"
APPEALS_ROLE_ID = 1227668177106768003
APPEALS_CATEGORY_ID = 1418366472476168302


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_images = defaultdict(list)
        self.user_words = defaultdict(list)
        self.strikes = self.load_strikes()
        self.cleanup_task.start()

    def load_strikes(self):
        if os.path.exists(STRIKE_FILE):
            with open(STRIKE_FILE, "r") as f:
                data = json.load(f)
                upgraded = {}
                for user_id, strike_list in data.items():
                    new_list = []
                    for strike in strike_list:
                        if isinstance(strike, str):
                            new_list.append({
                                "reason": "Unknown (old format)",
                                "timestamp": datetime.fromisoformat(strike),
                                "proof": "No proof"
                            })
                        elif isinstance(strike, dict):
                            strike["timestamp"] = datetime.fromisoformat(strike["timestamp"])
                            if "proof" not in strike:
                                strike["proof"] = "No proof"
                            new_list.append(strike)
                    upgraded[user_id] = new_list
                return defaultdict(list, upgraded)
        return defaultdict(list)

    def save_strikes(self):
        data = {}
        for uid, strike_list in self.strikes.items():
            data[str(uid)] = [
                {"reason": s["reason"], "timestamp": s["timestamp"].isoformat(), "proof": s.get("proof", "No proof")}
                for s in strike_list
            ]
        with open(STRIKE_FILE, "w") as f:
            json.dump(data, f, indent=4)

    async def add_strike(self, member: discord.Member, reason: str, proof: str = "No proof", channel: discord.TextChannel = None):
        if any(role.id in IMMUNE_ROLES for role in member.roles):
            return

        now = datetime.utcnow()
        self.strikes[str(member.id)].append({
            "reason": reason,
            "timestamp": now,
            "proof": proof
        })

        self.strikes[str(member.id)] = [
            s for s in self.strikes[str(member.id)]
            if now - s["timestamp"] < timedelta(days=STRIKE_DURATION_DAYS)
        ]
        self.save_strikes()

        count = len(self.strikes[str(member.id)])
        msg = None

        if count == 1:
            msg = f"⚠️ Warning: {reason}"
        elif count == 2:
            try:
                await member.timeout(timedelta(minutes=10), reason=reason)
            except:
                pass
            msg = f"⏱️ Timed out 10 minutes: {reason}"
        elif count >= 3:
            try:
                await member.timeout(timedelta(days=7), reason=reason)
            except:
                pass
            role = member.guild.get_role(APPEALS_ROLE_ID)
            if role:
                await member.add_roles(role, reason="3 strikes reached")
            msg = "⏳ 3 strikes reached, moved to appeals."

        if channel and msg:
            await channel.send(f"{member.mention} {msg}", delete_after=15)

    @tasks.loop(hours=1)
    async def cleanup_task(self):
        now = datetime.utcnow()
        changed = False
        for uid, strikes in list(self.strikes.items()):
            self.strikes[uid] = [
                s for s in strikes
                if now - s["timestamp"] < timedelta(days=STRIKE_DURATION_DAYS)
            ]
            if not self.strikes[uid]:
                del self.strikes[uid]
                changed = True
        if changed:
            self.save_strikes()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        member = message.author
        if any(role.id in IMMUNE_ROLES for role in member.roles):
            return

        content = message.content
        proof_text = content
        if message.attachments:
            proof_text += "\nAttachments:\n" + "\n".join(a.url for a in message.attachments)

        channel = message.channel

        for word in HARD_BAD_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", content.lower()):
                await message.delete()
                await self.add_strike(member, "NSFW word detected", proof_text, channel)
                return

        for keyword in BAD_WORD_KEYWORDS + ADULT_SITE_KEYWORDS:
            if keyword in content.lower():
                await message.delete()
                await self.add_strike(member, "NSFW content detected", proof_text, channel)
                return
        for domain in HARD_BLOCKED_DOMAINS:
            if domain in content.lower():
                await message.delete()
                await self.add_strike(member, "NSFW website detected", proof_text, channel)
                return

        invites = re.findall(r"(?:https?://)?(?:www\.)?(discord\.gg/\S+)", content.lower())
        for inv in invites:
            if inv not in WHITELISTED_INVITES:
                await message.delete()
                await self.add_strike(member, "Unauthorized Discord invite", proof_text, channel)
                return

        if message.channel.id not in BYPASS_CHANNELS:
            images = [a for a in message.attachments if a.content_type and "image" in a.content_type]
            if images:
                now = datetime.utcnow()
                self.user_images[member.id] = [
                    ts for ts in self.user_images[member.id]
                    if now - ts < timedelta(seconds=IMAGE_SPAM_INTERVAL)
                ] + [now] * len(images)
                if len(self.user_images[member.id]) > IMAGE_SPAM_LIMIT:
                    await message.delete()
                    await self.add_strike(member, "Image spam", proof_text, channel)
                    self.user_images[member.id] = []

        now = datetime.utcnow()
        self.user_words[member.id] = [
            ts for ts in self.user_words[member.id]
            if now - ts < timedelta(seconds=WORD_SPAM_INTERVAL)
        ] + [now]
        if len(self.user_words[member.id]) > WORD_SPAM_LIMIT:
            await message.delete()
            await self.add_strike(member, "Message spam", proof_text, channel)
            self.user_words[member.id] = []

    @app_commands.command(name="appeal", description="Post the appeal info embed in a specific channel.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(channel="The channel to post the appeal embed in")
    async def appeal(self, interaction: discord.Interaction, channel: discord.TextChannel):
        embed = discord.Embed(
            title="Appeal Request",
            description=(
                "If you have been moved to the appeals role due to receiving 3 strikes, "
                "you can create a private appeal channel here. In this channel, you will be "
                "able to discuss your case with moderators.\n\n"
                "Click the button below to start your appeal."
            ),
            color=0x2f3136
        )
        view = AppealButtonView(self)
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Appeal embed posted in {channel.mention}", ephemeral=True)


class AppealButtonView(ui.View):
    def __init__(self, automod: AutoMod):
        super().__init__(timeout=None)
        self.add_item(AppealButton(automod))


class AppealButton(ui.Button):
    def __init__(self, automod: AutoMod):
        super().__init__(style=discord.ButtonStyle.primary, label="Start Appeal")
        self.automod = automod

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        category = guild.get_channel(APPEALS_CATEGORY_ID)

        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ Appeals category is not set correctly.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        for role_id in IMMUNE_ROLES:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await category.create_text_channel(
            f"appeal-{user.name.lower()}",
            overwrites=overwrites,
            reason="User appeal"
        )

        strikes = self.automod.strikes.get(str(user.id), [])
        desc = ""
        for i, s in enumerate(strikes):
            desc += f"**Strike {i+1}:** {s['reason']} at {s['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            desc += f"**Proof:** {s.get('proof', 'No proof')}\n\n"

        embed = discord.Embed(
            title=f"{user.display_name}'s Strikes",
            description=desc or "No strikes found.",
            color=0x2f3136
        )
        await channel.send(f"{user.mention}", embed=embed)
        await interaction.response.send_message(f"✅ Appeal channel created: {channel.mention}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
