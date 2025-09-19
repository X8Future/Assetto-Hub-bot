import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
from urllib.parse import urlparse, parse_qs
import json
import os

PERSIST_FILE = "server_embeds.json"
REPORT_CHANNEL_ID = 1196681600977616927
PING_ROLE_ID = 1418082371051323472

class ServerEmbedUpdater(commands.Cog):
    WEATHER_MAP = {
        "Clear": "☀️ Clear", "FewClouds": "🌤️ Few Clouds", "ScatteredClouds": "⛅ Scattered Clouds",
        "BrokenClouds": "🌥️ Broken Clouds", "OvercastClouds": "☁️ Overcast Clouds", "Fog": "🌫️ Fog",
        "Mist": "🌫️ Mist", "Smoke": "💨 Smoke", "Haze": "🌫️ Haze", "Sand": "🏜️ Sand", "Dust": "🌪️ Dust",
        "Squalls": "🌬️ Squalls", "Tornado": "🌪️ Tornado", "Hurricane": "🌀 Hurricane", "Cold": "🥶 Cold",
        "Hot": "🥵 Hot", "Windy": "🌬️ Windy", "Hail": "🌨️ Hail", "LightThunderstorm": "⛈️ Light Thunderstorm",
        "Thunderstorm": "🌩️ Thunderstorm", "HeavyThunderstorm": "🌩️ Heavy Thunderstorm", "LightDrizzle": "🌦️ Light Drizzle",
        "Drizzle": "🌦️ Drizzle", "HeavyDrizzle": "🌧️ Heavy Drizzle", "LightRain": "🌦️ Light Rain", 
        "Rain": "🌧️ Rain", "HeavyRain": "🌧️ Heavy Rain", "LightSnow": "🌨️ Light Snow", "Snow": "❄️ Snow",
        "HeavySnow": "❄️ Heavy Snow", "LightSleet": "🌨️ Light Sleet", "Sleet": "🌨️ Sleet", "HeavySleet": "🌨️ Heavy Sleet"
    }

    def __init__(self, bot):
        self.bot = bot
        self.active_embeds = []
        self.load_embeds_from_file()
        self.bot.loop.create_task(self.restore_embeds())
        self.update_task.start()

    def save_embeds_to_file(self):
        with open(PERSIST_FILE, "w") as f:
            json.dump(self.active_embeds, f, indent=4)

    def load_embeds_from_file(self):
        if os.path.exists(PERSIST_FILE):
            with open(PERSIST_FILE, "r") as f:
                try:
                    self.active_embeds = json.load(f)
                except Exception:
                    self.active_embeds = []

    def convert_invite_to_api(self, invite_url: str) -> str:
        parsed = urlparse(invite_url)
        query = parse_qs(parsed.query)
        ip = query.get("ip", [None])[0]
        port = query.get("httpPort", [None])[0]
        if ip and port:
            return f"http://{ip}:{port}/api/details"
        return None

    async def restore_embeds(self):
        for embed_cfg in self.active_embeds:
            try:
                channel = self.bot.get_channel(embed_cfg["channel_id"])
                if not channel:
                    embed_cfg["can_update"] = False
                    continue
                await channel.fetch_message(embed_cfg["message_id"])
                embed_cfg["can_update"] = True
            except:
                embed_cfg["can_update"] = False
        self.save_embeds_to_file()

    @app_commands.command(name="serverembed", description="Track up to 5 servers by invite URLs")
    async def server_embed(self, interaction: discord.Interaction,
                           invite1: str, invite2: str = None, invite3: str = None, invite4: str = None, invite5: str = None,
                           title: str = "Live Server Status",
                           name1: str = None, name2: str = None, name3: str = None, name4: str = None, name5: str = None,
                           color: str = None,
                           thumbnail: str = None,
                           vip_slots1: bool = False, vip_slots2: bool = False, vip_slots3: bool = False,
                           vip_slots4: bool = False, vip_slots5: bool = False,
                           vip_only1: bool = False, vip_only2: bool = False, vip_only3: bool = False,
                           vip_only4: bool = False, vip_only5: bool = False):
        await interaction.response.defer(ephemeral=True)

        invite_links = [url for url in [invite1, invite2, invite3, invite4, invite5] if url]
        custom_names = [name.strip() if name else None for name in [name1, name2, name3, name4, name5]][:len(invite_links)]
        vip_slots_enabled = [vip_slots1, vip_slots2, vip_slots3, vip_slots4, vip_slots5][:len(invite_links)]
        vip_only_flags = [vip_only1, vip_only2, vip_only3, vip_only4, vip_only5][:len(invite_links)]
        embed_color = int(color.lstrip('#'), 16) if color else 0x42E3F5

        server_data = []
        server_info_to_save = []
        for idx, invite in enumerate(invite_links):
            api = self.convert_invite_to_api(invite)
            data = await self.fetch_server_data(api) if api else None
            server_data.append((data, invite))
            server_info_to_save.append({
                "invite": invite,
                "name": custom_names[idx] or (data.get("ServerName") if data else "Unknown Server"),
                "title": title,
                "color": embed_color,
                "vip_slots_enabled": vip_slots_enabled[idx],
                "vip_only": vip_only_flags[idx]
            })

        embed = await self.create_embed(
            server_data=server_data,
            custom_names=custom_names,
            vip_slots_enabled=vip_slots_enabled,
            vip_only=vip_only_flags,
            title=title,
            color=embed_color,
            thumbnail=thumbnail
        )

        sent_message = await interaction.channel.send(embed=embed)

        self.active_embeds.append({
            "channel_id": interaction.channel.id,
            "message_id": sent_message.id,
            "invite_links": invite_links,
            "vip_slots_enabled": vip_slots_enabled,
            "vip_only": vip_only_flags,
            "custom_names": custom_names,
            "custom_title": title,
            "embed_color": embed_color,
            "thumbnail_url": thumbnail,
            "thread_id": interaction.channel.id if isinstance(interaction.channel, discord.Thread) else None,
            "can_update": True,
            "servers_info": server_info_to_save
        })
        self.save_embeds_to_file()
        await interaction.followup.send("Server embed created.", ephemeral=True)

    async def fetch_server_data(self, api_url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except:
            pass
        return None

    def format_timeofday(self, timeofday):
        total_minutes = int((timeofday / 100) * 24 * 60) % 1440
        hours, minutes = divmod(total_minutes, 60)
        suffix = "AM" if hours < 12 else "PM"
        display_hour = 12 if hours % 12 == 0 else hours % 12
        clock_emojis = {1:"🕐",2:"🕑",3:"🕒",4:"🕓",5:"🕔",6:"🕕",7:"🕖",8:"🕗",9:"🕘",10:"🕙",11:"🕚",12:"🕛"}
        emoji = clock_emojis.get(display_hour, "🕐")
        return f"{emoji} {display_hour}:{minutes:02d} {suffix}"

    async def create_embed(self, *, server_data, custom_names, vip_slots_enabled, vip_only, title, color, thumbnail):
        embed = discord.Embed(title=title, color=color)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        number_emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]
        def get_emoji(connected, total):
            if not total:
                return "🟢"
            percent = connected / total
            if percent >= 1.0: return "🔴"
            if percent >= 0.75: return "🟡"
            return "🟢"

        for idx, (data, invite_url) in enumerate(server_data):
            address = custom_names[idx] or (data.get("ServerName") if data else "Unknown Server")
            if not data:
                embed.add_field(name=f"{number_emojis[idx]} {address}", value="🔴 Server Offline", inline=False)
                continue

            cars = data.get("players", {}).get("Cars", [])
            public_slots = sum(1 for car in cars if car.get("IsEntryList"))
            public_connected = sum(1 for car in cars if car.get("IsEntryList") and car.get("IsConnected"))

            total_vip = vip_connected = 0
            if vip_only[idx] or vip_slots_enabled[idx]:
                total_vip = sum(1 for car in cars if not car.get("IsEntryList") and "traffic" not in (car.get("Model") or "").lower())
                vip_connected = sum(1 for car in cars if not car.get("IsEntryList") and car.get("IsConnected") and "traffic" not in (car.get("Model") or "").lower())

            timeofday = data.get("timeofday")
            weather_id = data.get("currentWeatherId")
            weather_display = self.WEATHER_MAP.get(weather_id)

            lines = []
            if vip_only[idx]:
                total_combined = (public_slots or 0) + (total_vip or 0)
                connected_combined = (public_connected or 0) + (vip_connected or 0)
                emoji = get_emoji(connected_combined, total_combined)
                lines.append(f"{emoji} Slots: {connected_combined}/{total_combined}")
            else:
                lines.append(f"{get_emoji(public_connected, public_slots)} Public Slots: {public_connected}/{public_slots}")
                if vip_slots_enabled[idx]:
                    lines.append(f"<:Tier2:1283467604098416661> VIP Slots: {vip_connected}/{total_vip}")

            if timeofday is not None:
                lines.append(self.format_timeofday(timeofday))
            if weather_display:
                lines.append(weather_display)
            lines.append(f"▶ [ENTER SERVER HERE]({invite_url})")

            embed.add_field(name=f"{number_emojis[idx]} {address}", value="\n".join(lines), inline=False)

        embed.set_footer(text="Updates every 60 seconds")
        embed.timestamp = discord.utils.utcnow()
        return embed

    @tasks.loop(minutes=1)
    async def update_task(self):
        for embed_cfg in self.active_embeds.copy():
            try:
                channel = self.bot.get_channel(embed_cfg["channel_id"])
                if not channel:
                    embed_cfg["can_update"] = False
                    continue

                if isinstance(channel, discord.Thread) and (channel.locked or channel.archived):
                    embed_cfg["can_update"] = False
                    report_channel = self.bot.get_channel(REPORT_CHANNEL_ID)
                    if report_channel:
                        await report_channel.send(
                            f"<@&{PING_ROLE_ID}> The thread/forum `{channel.name}` has been closed!"
                        )
                    continue

                message = await channel.fetch_message(embed_cfg["message_id"])
                invite_links = embed_cfg["invite_links"]
                api_links = [self.convert_invite_to_api(inv) for inv in invite_links]

                server_data = [(await self.fetch_server_data(api), invite) for api, invite in zip(api_links, invite_links)]
                new_embed = await self.create_embed(
                    server_data=server_data,
                    custom_names=embed_cfg["custom_names"],
                    vip_slots_enabled=embed_cfg["vip_slots_enabled"],
                    vip_only=embed_cfg.get("vip_only", []),
                    title=embed_cfg["custom_title"],
                    color=embed_cfg["embed_color"],
                    thumbnail=embed_cfg.get("thumbnail_url")
                )
                await message.edit(embed=new_embed)
                embed_cfg["can_update"] = True

            except discord.NotFound:
                self.active_embeds.remove(embed_cfg)
            except Exception as e:
                embed_cfg["can_update"] = False
                report_channel = self.bot.get_channel(REPORT_CHANNEL_ID)
                if report_channel:
                    await report_channel.send(
                        f"<@&{PING_ROLE_ID}> Failed to update embed in channel `{embed_cfg['channel_id']}`, "
                        f"message `{embed_cfg['message_id']}`. Error: `{e}`"
                    )

        self.save_embeds_to_file()

    @update_task.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()


    @app_commands.command(name="refresh", description="Force update all tracked server embeds immediately")
    async def refresh_embeds(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.update_task()
        await interaction.followup.send("All server embeds have been refreshed.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ServerEmbedUpdater(bot))
