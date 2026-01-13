import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
from urllib.parse import urlparse, parse_qs
import json
import os
import asyncio
from discord.errors import NotFound

PERSIST_FILE = "server_embeds.json"

class ServerEmbedUpdater(commands.Cog):
    WEATHER_MAP = {
        "Clear": "☀️ Clear", "FewClouds": "🌤️ Few Clouds", "ScatteredClouds": "⛅ Scattered Clouds",
        "BrokenClouds": "🌥️ Broken Clouds", "OvercastClouds": "☁️ Overcast Clouds", "Fog": "🌫️ Fog",
        "Mist": "🌫️ Mist", "Smoke": "💨 Smoke", "Haze": "🌫️ Haze", "Sand": "🏜️ Sand", "Dust": "🌪️ Dust",
        "Squalls": "🌬️ Squalls", "Tornado": "🌪️ Tornado", "Hurricane": "🌀 Hurricane",
        "Cold": "🥶 Cold", "Hot": "🥵 Hot", "Windy": "🌬️ Windy", "Hail": "🌨️ Hail",
        "LightThunderstorm": "⛈️ Light Thunderstorm", "Thunderstorm": "🌩️ Thunderstorm",
        "HeavyThunderstorm": "🌩️ Heavy Thunderstorm", "LightDrizzle": "🌦️ Light Drizzle",
        "Drizzle": "🌦️ Drizzle", "HeavyDrizzle": "🌧️ Heavy Drizzle",
        "LightRain": "🌦️ Light Rain", "Rain": "🌧️ Rain", "HeavyRain": "🌧️ Heavy Rain",
        "LightSnow": "🌨️ Light Snow", "Snow": "❄️ Snow", "HeavySnow": "❄️ Heavy Snow",
        "LightSleet": "🌨️ Light Sleet", "Sleet": "🌨️ Sleet", "HeavySleet": "🌨️ Heavy Sleet"
    }

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.active_embeds = []
        self.load_embeds()
        self.bot.loop.create_task(self.restore_embeds())
        self.update_task.start()

    def cog_unload(self):
        asyncio.create_task(self.session.close())

    def save_embeds(self):
        data = [{k: v for k, v in e.items() if k != "message_obj"} for e in self.active_embeds]
        if data:
            with open(PERSIST_FILE, "w") as f:
                json.dump(data, f, indent=4)

    def load_embeds(self):
        if os.path.exists(PERSIST_FILE):
            try:
                with open(PERSIST_FILE, "r") as f:
                    self.active_embeds = json.load(f)
            except Exception:
                self.active_embeds = []

    def convert_invite_to_api(self, invite):
        try:
            q = parse_qs(urlparse(invite).query)
            ip = q.get("ip", [None])[0]
            port = q.get("httpPort", [None])[0]
            if ip and port:
                return f"http://{ip}:{port}/api/details"
        except Exception:
            pass
        return None

    async def fetch_server_data(self, api):
        if not api:
            return None
        try:
            async with self.session.get(api, timeout=10) as r:
                if r.status == 200:
                    return await r.json(content_type=None)
        except Exception:
            pass
        return None

    async def restore_embeds(self):
        for cfg in self.active_embeds:
            channel = self.bot.get_channel(cfg["channel_id"])
            if not channel:
                continue
            try:
                cfg["message_obj"] = await channel.fetch_message(cfg["message_id"])
            except NotFound:
                cfg["message_obj"] = None

    async def get_message(self, cfg):
        channel = self.bot.get_channel(cfg["channel_id"])
        if not channel:
            return None
        try:
            return await channel.fetch_message(cfg["message_id"])
        except NotFound:
            return None

    def format_time(self, t):
        mins = int((t / 100) * 1440) % 1440
        h, m = divmod(mins, 60)
        suf = "AM" if h < 12 else "PM"
        dh = 12 if h % 12 == 0 else h % 12
        emoji = ["🕛","🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚"][dh % 12]
        return f"{emoji} {dh}:{m:02d} {suf}"

    async def create_embed(self, *, server_data, names, vip_slots, vip_only, title, color, thumbnail):
        embed = discord.Embed(title=title, color=color)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        nums = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]

        def status(c, t):
            if not t:
                return "🟢"
            r = c / t
            return "🔴" if r >= 1 else "🟡" if r >= 0.75 else "🟢"

        for i, (data, invite) in enumerate(server_data):
            name = names[i] or (data.get("ServerName") if data else "Unknown Server")
            if not data:
                embed.add_field(name=f"{nums[i]} {name}", value="🔴 Server Offline", inline=False)
                continue

            cars = data.get("players", {}).get("Cars", [])
            pub = [c for c in cars if c.get("IsEntryList")]
            vip = [c for c in cars if not c.get("IsEntryList") and "traffic" not in (c.get("Model") or "").lower()]

            pub_c = sum(c.get("IsConnected") for c in pub)
            vip_c = sum(c.get("IsConnected") for c in vip)

            lines = []

            if vip_only[i]:
                tot = len(pub) + len(vip)
                con = pub_c + vip_c
                lines.append(f"{status(con, tot)} Slots: {con}/{tot}")
            else:
                lines.append(f"{status(pub_c, len(pub))} Public Slots: {pub_c}/{len(pub)}")
                if vip_slots[i]:
                    lines.append(f"<:Tier2:1283467604098416661> VIP Slots: {vip_c}/{len(vip)}")

            if data.get("timeofday") is not None:
                lines.append(self.format_time(data["timeofday"]))

            w = self.WEATHER_MAP.get(data.get("currentWeatherId"))
            if w:
                lines.append(w)

            lines.append(f"▶ [ENTER SERVER HERE]({invite})")
            embed.add_field(name=f"{nums[i]} {name}", value="\n".join(lines), inline=False)

        embed.set_footer(text="Updates every 60 seconds")
        embed.timestamp = discord.utils.utcnow()
        return embed

    async def update_embed_cfg(self, cfg):
        msg = await self.get_message(cfg)
        if not msg:
            return

        apis = [self.convert_invite_to_api(i) for i in cfg["invite_links"]]
        data = [(await self.fetch_server_data(a), i) for a, i in zip(apis, cfg["invite_links"])]

        embed = await self.create_embed(
            server_data=data,
            names=cfg["custom_names"],
            vip_slots=cfg["vip_slots_enabled"],
            vip_only=cfg.get("vip_only", [False]*len(data)),
            title=cfg["custom_title"],
            color=cfg["embed_color"],
            thumbnail=cfg.get("thumbnail_url")
        )

        try:
            await msg.edit(embed=embed)
        except NotFound:
            pass

    @tasks.loop(minutes=1)
    async def update_task(self):
        for cfg in list(self.active_embeds):
            try:
                await self.update_embed_cfg(cfg)
            except NotFound:
                continue
            except Exception:
                continue

    @update_task.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="serverembed")
    async def server_embed(self, interaction: discord.Interaction,
                           invite1: str, invite2: str = None, invite3: str = None,
                           invite4: str = None, invite5: str = None,
                           title: str = "Live Server Status",
                           name1: str = None, name2: str = None, name3: str = None,
                           name4: str = None, name5: str = None,
                           color: str = None, thumbnail: str = None,
                           vip_slots1: bool = False, vip_slots2: bool = False,
                           vip_slots3: bool = False, vip_slots4: bool = False,
                           vip_slots5: bool = False,
                           vip_only1: bool = False, vip_only2: bool = False,
                           vip_only3: bool = False, vip_only4: bool = False,
                           vip_only5: bool = False):

        await interaction.response.defer(ephemeral=True)

        invites = [i for i in [invite1, invite2, invite3, invite4, invite5] if i]
        names = [n for n in [name1, name2, name3, name4, name5]][:len(invites)]
        vip_slots = [vip_slots1, vip_slots2, vip_slots3, vip_slots4, vip_slots5][:len(invites)]
        vip_only = [vip_only1, vip_only2, vip_only3, vip_only4, vip_only5][:len(invites)]
        col = int(color.lstrip("#"), 16) if color else 0x36393F

        apis = [self.convert_invite_to_api(i) for i in invites]
        data = [(await self.fetch_server_data(a), i) for a, i in zip(apis, invites)]

        embed = await self.create_embed(
            server_data=data,
            names=names,
            vip_slots=vip_slots,
            vip_only=vip_only,
            title=title,
            color=col,
            thumbnail=thumbnail
        )

        msg = await interaction.channel.send(embed=embed)

        self.active_embeds.append({
            "channel_id": interaction.channel.id,
            "message_id": msg.id,
            "invite_links": invites,
            "vip_slots_enabled": vip_slots,
            "vip_only": vip_only,
            "custom_names": names,
            "custom_title": title,
            "embed_color": col,
            "thumbnail_url": thumbnail,
            "thread_id": interaction.channel.id if isinstance(interaction.channel, discord.Thread) else None
        })

        self.save_embeds()
        await interaction.followup.send("✅ Server embed created.", ephemeral=True)

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        if before.locked and not after.locked:
            for cfg in self.active_embeds:
                if cfg.get("thread_id") == after.id:
                    await self.update_embed_cfg(cfg)
                    break

async def setup(bot):
    await bot.add_cog(ServerEmbedUpdater(bot))
