import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
from urllib.parse import urlparse

class ServerEmbedUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_links = []
        self.vip_slots_enabled = []
        self.server_data = []
        self.embed = None
        self.sent_message = None
        self.custom_title = "Live Server Status"
        self.custom_names = []
        self.embed_color = 0x42E3F5
        self.thumbnail_url = None
        self.update_task.start()

    WEATHER_MAP = {
        "LightThunderstorm": "⛈️ Light Thunderstorm",
        "Thunderstorm": "🌩️ Thunderstorm",
        "HeavyThunderstorm": "🌩️ Heavy Thunderstorm",
        "LightDrizzle": "🌦️ Light Drizzle",
        "Drizzle": "🌦️ Drizzle",
        "HeavyDrizzle": "🌧️ Heavy Drizzle",
        "LightRain": "🌦️ Light Rain",
        "Rain": "🌧️ Rain",
        "HeavyRain": "🌧️ Heavy Rain",
        "LightSnow": "🌨️ Light Snow",
        "Snow": "❄️ Snow",
        "HeavySnow": "❄️ Heavy Snow",
        "LightSleet": "🌨️ Light Sleet",
        "Sleet": "🌨️ Sleet",
        "HeavySleet": "🌨️ Heavy Sleet",
        "Clear": "☀️ Clear",
        "FewClouds": "🌤️ Few Clouds",
        "ScatteredClouds": "⛅ Scattered Clouds",
        "BrokenClouds": "🌥️ Broken Clouds",
        "OvercastClouds": "☁️ Overcast Clouds",
        "Fog": "🌫️ Fog",
        "Mist": "🌫️ Mist",
        "Smoke": "💨 Smoke",
        "Haze": "🌫️ Haze",
        "Sand": "🏜️ Sand",
        "Dust": "🌪️ Dust",
        "Squalls": "🌬️ Squalls",
        "Tornado": "🌪️ Tornado",
        "Hurricane": "🌀 Hurricane",
        "Cold": "🥶 Cold",
        "Hot": "🥵 Hot",
        "Windy": "🌬️ Windy",
        "Hail": "🌨️ Hail"
    }

    @app_commands.command(name="serverembed", description="Track up to 5 servers by API URLs")
    @app_commands.describe(
        color="Hex color code for the embed (e.g. #42E3F5)",
        thumbnail="Thumbnail image URL for the embed",
        vip_slots1="Include VIP slots in status for server 1",
        vip_slots2="Include VIP slots in status for server 2",
        vip_slots3="Include VIP slots in status for server 3",
        vip_slots4="Include VIP slots in status for server 4",
        vip_slots5="Include VIP slots in status for server 5"
    )
    async def server_embed(self, interaction: discord.Interaction, 
                           api1: str, api2: str = None, api3: str = None,
                           api4: str = None, api5: str = None,
                           title: str = "Live Server Status",
                           name1: str = None, name2: str = None, name3: str = None,
                           name4: str = None, name5: str = None,
                           color: str = None,
                           thumbnail: str = None,
                           vip_slots1: bool = False,
                           vip_slots2: bool = False,
                           vip_slots3: bool = False,
                           vip_slots4: bool = False,
                           vip_slots5: bool = False):
        await interaction.response.defer(ephemeral=True)

        apis = [api for api in [api1, api2, api3, api4, api5] if api]
        self.api_links = apis

        names_raw = [name1, name2, name3, name4, name5]
        self.custom_names = [name.strip() if name else None for name in names_raw][:len(apis)]

        self.custom_title = title

        if color:
            try:
                self.embed_color = int(color.lstrip('#'), 16)
            except Exception:
                self.embed_color = 0x42E3F5
        else:
            self.embed_color = 0x42E3F5

        self.thumbnail_url = thumbnail
        self.server_data = []

        vip_flags = [vip_slots1, vip_slots2, vip_slots3, vip_slots4, vip_slots5]
        self.vip_slots_enabled = vip_flags[:len(apis)]

        for url in self.api_links:
            data = await self.fetch_server_data(url)
            if data:
                self.server_data.append((data, url))
            else:
                await interaction.followup.send(f"Failed to fetch data from: {url}", ephemeral=True)

        if not self.server_data:
            await interaction.followup.send("Failed to fetch data from all provided APIs.", ephemeral=True)
            return

        self.embed = await self.create_embed()
        self.sent_message = await interaction.channel.send(embed=self.embed)
        await interaction.followup.send("Server embed created.", ephemeral=True)

    async def fetch_server_data(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            print(f"Error fetching data from {url}: {e}")
        return None

    def format_timeofday(self, timeofday):
        total_minutes = int((timeofday / 100) * 24 * 60)
        total_minutes = total_minutes % 1440
        hours = total_minutes // 60
        minutes = total_minutes % 60
        emoji_map = {
            0: "🕛", 1: "🕐", 2: "🕑", 3: "🕒", 4: "🕓",
            5: "🕔", 6: "🕕", 7: "🕖", 8: "🕗", 9: "🕘",
            10: "🕙", 11: "🕚", 12: "🕛"
        }
        suffix = "AM"
        display_hour = hours
        if hours == 0:
            display_hour = 12
        elif 1 <= hours < 12:
            display_hour = hours
        elif hours == 12:
            suffix = "PM"
            display_hour = 12
        else:
            display_hour = hours - 12
            suffix = "PM"
        emoji = emoji_map.get(display_hour if display_hour != 0 else 12, "🕛")
        return f"{emoji} {display_hour}:{minutes:02d} {suffix}"

    async def create_embed(self):
        embed = discord.Embed(title=self.custom_title or "Live Server Status", color=self.embed_color)

        if self.thumbnail_url:
            embed.set_thumbnail(url=self.thumbnail_url)

        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

        for idx, (data, api_url) in enumerate(self.server_data):
            cars = data.get("players", {}).get("Cars", [])

            public_slots = sum(1 for car in cars if car.get("IsEntryList") is True)
            public_connected = sum(1 for car in cars if car.get("IsEntryList") is True and car.get("IsConnected") is True)

            if self.vip_slots_enabled[idx]:
                total_vip = sum(1 for car in cars if car.get("IsEntryList") is False and "traffic" not in car.get("Model", "").lower())
                vip_connected = sum(1 for car in cars if car.get("IsEntryList") is False and car.get("IsConnected") is True and "traffic" not in car.get("Model", "").lower())
            else:
                total_vip = vip_connected = None

            timeofday = data.get("timeofday", None)
            weather_id = data.get("currentWeatherId", None)
            weather_display = self.WEATHER_MAP.get(weather_id, None)

            address = self.custom_names[idx] if idx < len(self.custom_names) and self.custom_names[idx] else data.get("ServerName", "Unknown Server")

            parsed = urlparse(api_url)
            netloc = parsed.netloc
            ip, port = (netloc.split(":") + ["8081"])[:2]
            join_link = f"https://acstuff.ru/s/q:race/online/join?ip={ip}&httpPort={port}"

            server_num_emoji = number_emojis[idx] if idx < len(number_emojis) else f"{idx+1}️⃣"

            value_lines = [
                f"🟢 Public Slots: {public_connected}/{public_slots}",
            ]

            if self.vip_slots_enabled[idx]:
                value_lines.append(f"<:Tier2:1283467604098416661> VIP Slots: {vip_connected}/{total_vip}")

            if timeofday is not None:
                value_lines.append(self.format_timeofday(timeofday))
            if weather_display is not None:
                value_lines.append(weather_display)

            value_lines.append(f"▶ [ENTER SERVER HERE]({join_link})")

            embed.add_field(
                name=f"{server_num_emoji} {address}",
                value="\n".join(value_lines),
                inline=False
            )

        embed.set_footer(text="Updates every 60 seconds")
        embed.timestamp = discord.utils.utcnow()
        return embed

    @tasks.loop(minutes=1)
    async def update_task(self):
        if not self.api_links or not self.sent_message:
            return

        self.server_data = []
        for url in self.api_links:
            data = await self.fetch_server_data(url)
            if data:
                self.server_data.append((data, url))

        new_embed = await self.create_embed()
        await self.sent_message.edit(embed=new_embed)
        self.embed = new_embed

    @update_task.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(ServerEmbedUpdater(bot))
    print("[LOG] ServerEmbedUpdater Cog loaded and slash command registered.")
