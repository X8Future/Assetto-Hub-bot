import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction
import aiohttp, json, os, sqlite3, asyncio
from datetime import datetime
import pytz
from urllib.parse import urlparse, parse_qs

SERVER_JSON = "/root/Files/server_embeds.json"
PERSIST_FILE = "/root/Files/live_server_embeds.json"
DAILY_PLAYERS_FILE = "/root/Files/daily_players.json"
PACIFIC_TZ = pytz.timezone("America/Los_Angeles")
ALERT_ROLE_ID = 1176727481647112296
DARK_COLOR = 0x2f3136
TOTAL_SERVERS_PAGES = 3
HUB_DB = "/root/Bot-File/hub.db"

DRIVER_FLAGS = {
    "POL": "🇵🇱", "USA": "🇺🇸", "FRA": "🇫🇷", "GER": "🇩🇪", "ITA": "🇮🇹",
    "GBR": "🇬🇧", "ESP": "🇪🇸", "SWE": "🇸🇪", "NLD": "🇳🇱", "JPN": "🇯🇵"
}

def parse_acstuff_link(link):
    try:
        parsed = urlparse(link)
        query = parse_qs(parsed.query)
        ip, port = query.get("ip")[0], query.get("httpPort")[0]
        return f"http://{ip}:{port}/api/details"
    except:
        return None

def load_json(path):
    return json.load(open(path)) if os.path.exists(path) else {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

def load_servers():
    if not os.path.exists(SERVER_JSON):
        return []
    data = load_json(SERVER_JSON)
    servers = []
    for entry in data:
        for i, link in enumerate(entry.get("invite_links", [])):
            name = entry.get("custom_names", [])[i] if i < len(entry.get("custom_names", [])) else f"Server {i+1}"
            api = parse_acstuff_link(link)
            if api:
                servers.append({"name": name, "api": api})
    return servers

async def safe_fetch_json(session, url):
    try:
        async with session.get(url, timeout=5) as r:
            data = await r.json(content_type=None)
            return data if isinstance(data, dict) else None
    except:
        return None

def format_time(seconds):
    h, m = divmod(int(seconds // 60), 60)
    return f"{h}h {m}m"

def get_friendly_car_name(model):
    try:
        conn = sqlite3.connect(HUB_DB)
        c = conn.cursor()
        c.execute("SELECT friendly_name FROM cars WHERE model=?", (model,))
        r = c.fetchone()
        conn.close()
        return r[0] if r else model
    except:
        return model

class ServerEmbedView(discord.ui.View):
    def __init__(self, bot, servers, alert_role):
        super().__init__(timeout=None)
        self.bot = bot
        self.servers = servers
        self.alert_role = alert_role
        self.current_page = "main"
        self.message = None
        self.server_cache = {s["name"]: None for s in servers}
        self.server_daily_count = {s["name"]: 0 for s in servers}
        self.offline_notifications = {}
        self.servers_page_index = 0
        self.last_embed_dict = None

        self.daily_players = load_json(DAILY_PLAYERS_FILE)
        self.daily_reset = None
        if "_date" in self.daily_players:
            try:
                self.daily_reset = datetime.fromisoformat(self.daily_players["_date"]).date()
            except:
                self.daily_reset = None

        for player, pdata in self.daily_players.items():
            if player == "_date": continue
            for sess in pdata.get("sessions", []):
                server_name = sess.get("server")
                if server_name in self.server_daily_count:
                    self.server_daily_count[server_name] += 1

        self.add_item(PageSelect(self))
        self.add_item(ButtonPage("◀️ Prev Page", "prev", self))
        self.add_item(ButtonPage("Next Page ▶️", "next", self))

        self.bot.loop.create_task(self.fetch_all_servers_cycle())
        self.bot.loop.create_task(self.daily_reset_task())

    async def fetch_server(self, server):
        async with aiohttp.ClientSession() as session:
            data = await safe_fetch_json(session, server["api"])
            self.server_cache[server["name"]] = data
            if server["name"] in self.offline_notifications and data:
                try: await self.offline_notifications.pop(server["name"]).delete()
                except: pass
            elif not data and server["name"] not in self.offline_notifications:
                await self.notify_offline(server)

    async def fetch_all_servers_cycle(self):
        while True:
            for s in self.servers:
                asyncio.create_task(self.fetch_server(s))
                await asyncio.sleep(2)
            await asyncio.sleep(max(60 - 2 * len(self.servers), 5))

    async def notify_offline(self, server):
        if not self.message: return

        class CheckServerButton(discord.ui.View):
            def __init__(self, parent, server):
                super().__init__(timeout=None)
                self.parent = parent
                self.server = server

            @discord.ui.button(label="Check Server", style=discord.ButtonStyle.green)
            async def check(self, i: Interaction, _):
                await self.parent.fetch_server(self.server)
                if self.parent.server_cache.get(self.server["name"]):
                    await i.response.send_message(f"✅ {self.server['name']} is back online!", ephemeral=True)
                    try: await i.message.delete()
                    except: pass
                    self.parent.offline_notifications.pop(self.server["name"], None)
                else:
                    await i.response.send_message(f"❌ {self.server['name']} is still offline.", ephemeral=True)

        view = CheckServerButton(self, server)
        msg = await self.message.channel.send(f"<@&{self.alert_role}> `{server['name']}` is offline!", view=view)
        self.offline_notifications[server["name"]] = msg

    async def update_daily_players(self):
        now_ts = datetime.now().timestamp()
        today = datetime.now(PACIFIC_TZ).date()
        if self.daily_reset != today:
            self.daily_players["_date"] = today.isoformat()
            self.server_daily_count = {s["name"]: 0 for s in self.servers}
            self.daily_reset = today
            save_json(DAILY_PLAYERS_FILE, self.daily_players)

        for s_name, data in self.server_cache.items():
            if not isinstance(data, dict): continue
            cars = data.get("players", {}).get("Cars", [])
            for c in cars:
                if not c.get("IsConnected"): continue
                self.server_daily_count[s_name] += 1
                user, model = c.get("DriverName", "Unknown"), c.get("Model", "Unknown")
                car = get_friendly_car_name(model)
                if user not in self.daily_players:
                    self.daily_players[user] = {"sessions": []}
                sess = next((x for x in self.daily_players[user]["sessions"] if x["server"] == s_name and x["car"] == car), None)
                if not sess:
                    sess = {"server": s_name, "car": car, "first_seen": now_ts, "last_seen": now_ts, "time_seconds": 0}
                    self.daily_players[user]["sessions"].append(sess)
                elapsed = now_ts - sess["last_seen"]
                sess["time_seconds"] += elapsed
                sess["last_seen"] = now_ts

        save_json(DAILY_PLAYERS_FILE, self.daily_players)

    async def daily_reset_task(self):
        await self.bot.wait_until_ready()
        while True:
            now = datetime.now(PACIFIC_TZ)
            if self.daily_reset != now.date():
                self.daily_players["_date"] = now.date().isoformat()
                self.server_daily_count = {s["name"]: 0 for s in self.servers}
                self.daily_reset = now.date()
                save_json(DAILY_PLAYERS_FILE, self.daily_players)
            await asyncio.sleep(60)

    def get_footer(self):
        return f"Updated every 1 min • {datetime.now(PACIFIC_TZ).strftime('%I:%M %p')}"

    def get_main_embed(self):
        online = sum(1 for d in self.server_cache.values() if isinstance(d, dict))
        offline = len(self.server_cache) - online
        total = sum(sum(1 for c in d.get("players", {}).get("Cars", []) if c.get("IsConnected"))
                    for d in self.server_cache.values() if isinstance(d, dict))
        e = discord.Embed(title="🏁 Future Crew | Assetto Corsa Servers", color=DARK_COLOR)
        e.add_field(name="🟢 Online", value=online)
        e.add_field(name="🔴 Offline", value=offline)
        e.add_field(name="👥 Players", value=total)
        e.set_footer(text=self.get_footer())
        return e

    def get_servers_embed(self):
        sorted_servers = sorted(
            self.server_cache.items(),
            key=lambda x: self.server_daily_count.get(x[0], 0),
            reverse=True
        )
        per_page = (len(sorted_servers) + TOTAL_SERVERS_PAGES - 1) // TOTAL_SERVERS_PAGES
        start, end = self.servers_page_index * per_page, (self.servers_page_index + 1) * per_page
        e = discord.Embed(title="🖥️ Server Status", color=DARK_COLOR)
        for n, d in sorted_servers[start:end]:
            if not isinstance(d, dict):
                e.add_field(name=n, value="❌ Offline", inline=False)
                continue
            total_today = self.server_daily_count.get(n, 0)
            clients = sum(1 for c in d.get("players", {}).get("Cars", []) if c.get("IsConnected"))
            e.add_field(name=n, value=f"Weather: {d.get('currentWeatherId','?')}\nOnline Now: {clients}\nToday: {total_today}", inline=False)
        e.set_footer(text=f"{self.get_footer()} • Page {self.servers_page_index+1}/{TOTAL_SERVERS_PAGES}")
        return e

    def get_players_embed(self):
        e = discord.Embed(title="👥 Players Online", color=DARK_COLOR)
        for s_name, d in self.server_cache.items():
            if not isinstance(d, dict): continue
            for c in d.get("players", {}).get("Cars", []):
                if not c.get("IsConnected"): continue
                name, model, nation = c.get("DriverName", "Unknown"), c.get("Model", "Unknown"), c.get("DriverNation", "Unknown")
                flag = DRIVER_FLAGS.get(nation, "")
                e.add_field(name=f"{name} {flag}", value=f"Car: {get_friendly_car_name(model)}\nServer: {s_name}", inline=False)
        e.set_footer(text=self.get_footer())
        return e

    def get_today_embed(self):
        e = discord.Embed(title="📅 Today's Players", color=DARK_COLOR)
        for player, pdata in self.daily_players.items():
            if player == "_date": continue
            value = ""
            for s in pdata.get("sessions", []):
                value += f"{s['server']}: {s['car']} - {format_time(s['time_seconds'])}\n"
            e.add_field(name=player, value=value or "No data", inline=False)
        e.set_footer(text=self.get_footer())
        return e

    async def update_embed(self):
        await self.update_daily_players()
        page_func = {"main": self.get_main_embed, "servers": self.get_servers_embed,
                     "players": self.get_players_embed, "today": self.get_today_embed}.get(self.current_page, self.get_main_embed)
        embed = page_func()
        if not self.message: return
        new_dict = embed.to_dict()
        if new_dict != self.last_embed_dict:
            self.last_embed_dict = new_dict
            try: await self.message.edit(embed=embed)
            except: pass

class PageSelect(discord.ui.Select):
    def __init__(self, view: ServerEmbedView):
        options = [
            discord.SelectOption(label="Main", value="main"),
            discord.SelectOption(label="Servers", value="servers"),
            discord.SelectOption(label="Players", value="players"),
            discord.SelectOption(label="Today", value="today"),
        ]
        super().__init__(placeholder="Select page", options=options, min_values=1, max_values=1)
        self.view_ref = view

    async def callback(self, interaction: Interaction):
        self.view_ref.current_page = self.values[0]
        await self.view_ref.update_embed()
        save_json(PERSIST_FILE, {"channel_id": self.view_ref.message.channel.id,
                                 "message_id": self.view_ref.message.id,
                                 "current_page": self.view_ref.current_page})
        await interaction.response.defer()

class ButtonPage(discord.ui.Button):
    def __init__(self, label, direction, view_ref):
        super().__init__(label=label, style=discord.ButtonStyle.blurple)
        self.direction = direction
        self.view_ref = view_ref

    async def callback(self, interaction: Interaction):
        if self.direction == "prev":
            self.view_ref.servers_page_index = max(0, self.view_ref.servers_page_index - 1)
        else:
            self.view_ref.servers_page_index += 1
        await self.view_ref.update_embed()
        await interaction.response.defer()

class ServerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.servers = load_servers()
        self.view_static = ServerEmbedView(bot, self.servers, ALERT_ROLE_ID)
        self.bot.loop.create_task(self.restore_embed())
        self.update_task.start()

    async def restore_embed(self):
        await self.bot.wait_until_ready()
        data = load_json(PERSIST_FILE)
        if not data: return
        try:
            ch = self.bot.get_channel(data["channel_id"])
            msg = await ch.fetch_message(data["message_id"])
            self.view_static.message = msg
            self.view_static.current_page = data.get("current_page", "main")
            await self.view_static.update_embed()
        except: pass

    @app_commands.command(name="server_embed", description="Send the live server embed to a channel")
    @app_commands.describe(channel="Select the channel to send the server embed in")
    async def server_embed(self, i: Interaction, channel: discord.TextChannel = None):
        channel = channel or i.channel
        interactive_view = ServerEmbedView(self.bot, self.servers, ALERT_ROLE_ID)
        message = await channel.send(embed=interactive_view.get_main_embed(), view=interactive_view)
        interactive_view.message = message
        save_json(PERSIST_FILE, {"channel_id": channel.id, "message_id": message.id, "current_page": interactive_view.current_page})
        await i.response.send_message(f"✅ Sent to {channel.mention}", ephemeral=True)

    @tasks.loop(seconds=60)
    async def update_task(self):
        if self.view_static.message:
            await self.view_static.update_embed()
            save_json(PERSIST_FILE, {"channel_id": self.view_static.message.channel.id,
                                     "message_id": self.view_static.message.id,
                                     "current_page": self.view_static.current_page})

    @update_task.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(ServerCog(bot))
