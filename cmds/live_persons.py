import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import json
import os
import pytz
import traceback

SERVER_JSON = "server_embeds.json"
PERSIST_FILE = "live_server_embeds.json"

ALERT_CHANNEL_ID = # Where you want the bot to tell you a server has gone down
ALERT_ROLE_ID = # The role you want to get pinged when a server goes down
ALERT_USER = "<@>" # If you want a person to be pinged as well as as role

PACIFIC_TZ = pytz.timezone("America/Los_Angeles")


class LiveEmbedManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embeds_data = []
        self.player_timestamps = {}
        self.today_data = {}
        self.server_status = {}
        self.session = aiohttp.ClientSession()
        self.bot.loop.create_task(self.restore_embeds())
        self.update_task.start()
        self.check_servers_task.start()

    def save_embeds(self):
        with open(PERSIST_FILE, "w") as f:
            json.dump(self.embeds_data, f, indent=4)

    def load_embeds(self):
        if os.path.exists(PERSIST_FILE):
            try:
                with open(PERSIST_FILE, "r") as f:
                    self.embeds_data = json.load(f)
            except Exception:
                self.embeds_data = []

    async def restore_embeds(self):
        self.load_embeds()
        for embed_cfg in self.embeds_data:
            try:
                channel = self.bot.get_channel(embed_cfg["channel_id"])
                if not channel:
                    embed_cfg["can_update"] = False
                    continue
                try:
                    message = await channel.fetch_message(embed_cfg["message_id"])
                except discord.NotFound:
                    embed_cfg["can_update"] = False
                    continue

                cfgs = embed_cfg["cfgs"]
                servers_data_all = []
                flat_status = []

                for cfg in cfgs:
                    servers_data = []
                    for inv in cfg.get("invite_links", []):
                        api = self.convert_invite_to_api(inv)
                        s = await self.fetch_server_data(api)
                        servers_data.append(s)
                        flat_status.append(s is not None)
                    servers_data_all.append(servers_data)

                view = MultiServerEmbedView(self, cfgs, servers_data_all)
                view.screen = embed_cfg.get("screen", "main")
                view.server_page = embed_cfg.get("server_page", 0)
                view.player_page = embed_cfg.get("player_page", 0)
                view.today_page = embed_cfg.get("today_page", 0)
                view.update_buttons()
                await message.edit(view=view)

                self.server_status[embed_cfg["message_id"]] = flat_status
                embed_cfg["can_update"] = True
            except Exception:
                embed_cfg["can_update"] = False
                traceback.print_exc()
        self.save_embeds()

    def convert_invite_to_api(self, invite_url: str) -> str:
        parsed = urlparse(invite_url)
        query = parse_qs(parsed.query)
        ip = query.get("ip", [None])[0]
        port = query.get("httpPort", [None])[0]
        return f"http://{ip}:{port}/api/details" if ip and port else None

    async def fetch_server_data(self, api_url):
        if not api_url:
            return None
        try:
            async with self.session.get(api_url, timeout=5) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            return None
        return None

    async def create_main_embed(self, cfgs, servers_data_all):
        total_players, online_servers_count, offline_servers_list = 0, 0, []
        for cfg_idx, cfg in enumerate(cfgs):
            servers_data = servers_data_all[cfg_idx]
            emoji = cfg.get("emoji", "")
            for idx, s in enumerate(servers_data):
                server_name = cfg["custom_names"][idx] if idx < len(cfg["custom_names"]) else f"Server {idx+1}"
                if s:
                    players = len([c for c in s.get("players", {}).get("Cars", []) if c.get("IsConnected")])
                    total_players += players
                    online_servers_count += 1
                else:
                    offline_servers_list.append(f"{emoji} {server_name}")

        total_servers = sum(len(servers_data) for servers_data in servers_data_all)
        embed = discord.Embed(
            title=cfgs[0].get("main_title", "Live Servers Dashboard"), 
            color=0x36393F
        )
        embed.set_thumbnail(url="https://i.postimg.cc/509JQwD8/logo2.png")
        embed.add_field(name="🟢 Servers Online", value=f"{online_servers_count}/{total_servers} servers active", inline=False)
        embed.add_field(name=f"🔴 Servers Offline: {len(offline_servers_list)}", value="\n".join(offline_servers_list) or "None", inline=False)
        embed.add_field(name="👥 Total Number of Players Online", value=str(total_players), inline=False)
        embed.set_footer(text="Updates every 60 seconds")
        embed.timestamp = discord.utils.utcnow()
        return embed

    async def create_today_embed(self, page=0, per_page=5):
        now_pst = datetime.now(PACIFIC_TZ)
        today_key = now_pst.strftime("%Y-%m-%d")
        today_players = self.today_data.get(today_key, [])
        total_pages = max(1, (len(today_players) - 1)//per_page + 1)
        start, end = page*per_page, page*per_page+per_page

        embed = discord.Embed(title="Today's Player Activity", color=0x36393F)
        if not today_players:
            embed.description = "No players recorded today."
        else:
            for entry in today_players[start:end]:
                embed.add_field(
                    name=f"{entry['player']} - {entry['server']}",
                    value=f"Car: {entry['car']}\nConnected for: {entry['time']}",
                    inline=False
                )

        embed.set_footer(text=f"Page {page+1}/{total_pages} | Resets daily at midnight")
        embed.timestamp = discord.utils.utcnow()
        return embed

    async def create_server_list_embed(self, cfgs, servers_data_all, page=0, per_page=5):
        servers_flat = [
            (cfg["custom_names"][idx] if idx < len(cfg["custom_names"]) else f"Server {idx+1}", s)
            for cfg, servers_data in zip(cfgs, servers_data_all)
            for idx, s in enumerate(servers_data)
        ]
        total_pages = max(1, (len(servers_flat) - 1)//per_page + 1)
        start, end = page*per_page, page*per_page+per_page
        embed = discord.Embed(title="Server List", color=0x36393F)
        for name, s in servers_flat[start:end]:
            status = "🟢 Online" if s else "🔴 Offline"
            players = len([c for c in s.get("players", {}).get("Cars", []) if c.get("IsConnected")]) if s else 0
            embed.add_field(name=name, value=f"{status} | Players: {players}", inline=False)
        embed.set_footer(text=f"Page {page+1}/{total_pages} | Updates every 60 seconds")
        embed.timestamp = discord.utils.utcnow()
        return embed

    async def create_player_embed(self, cfgs, servers_data_all, page=0, per_page=5):
        players_flat = []
        now_pst = datetime.now(PACIFIC_TZ)
        today_key = now_pst.strftime("%Y-%m-%d")
        self.today_data.setdefault(today_key, [])

        for cfg_idx, cfg in enumerate(cfgs):
            servers_data = servers_data_all[cfg_idx]
            for idx, server in enumerate(servers_data):
                if not server:
                    continue
                server_name = cfg["custom_names"][idx] if idx < len(cfg["custom_names"]) else f"Server {idx+1}"
                for car in server.get("players", {}).get("Cars", []):
                    if car.get("IsConnected"):
                        players_flat.append((server_name, car))
                        car_id = car.get("ID") or f"{car.get('DriverName','Unknown')}-{car.get('Model','Unknown')}"
                        if car_id not in self.player_timestamps:
                            self.player_timestamps[car_id] = datetime.utcnow()
                            self.today_data[today_key].append({
                                "player": car.get("DriverName","Unknown"),
                                "server": server_name,
                                "car": car.get("Model","Unknown"),
                                "time": "Just joined"
                            })

        total_pages = max(1, (len(players_flat) - 1)//per_page + 1)
        start, end = page*per_page, page*per_page+per_page
        embed = discord.Embed(title="Player List", color=0x36393F)
        for server_name, car in players_flat[start:end]:
            car_id = car.get("ID") or f"{car.get('DriverName','Unknown')}-{car.get('Model','Unknown')}"
            delta = datetime.utcnow() - self.player_timestamps[car_id]
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{hours}h {minutes}m {seconds}s"
            slot = "Public" if car.get("IsEntryList", False) else "VIP"
            embed.add_field(
                name=f"{car.get('DriverName','Unknown')} ({slot}) - {server_name}",
                value=f"Model: {car.get('Model','Unknown')}\nSkin: {car.get('Skin','Default')}\nConnected: {time_str}",
                inline=False
            )
        embed.set_footer(text=f"Page {page+1}/{total_pages} | Updates every 60 seconds")
        embed.timestamp = discord.utils.utcnow()
        return embed

    @app_commands.command(name="liveembed", description="Create live server embed")
    async def liveembed(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.load_embeds()
        if not os.path.exists(SERVER_JSON):
            return await interaction.followup.send("No server JSON found.", ephemeral=True)
        with open(SERVER_JSON) as f:
            cfgs = json.load(f)

        servers_data_all = []
        flat_status = []
        for cfg in cfgs:
            servers_data = []
            for inv in cfg.get("invite_links", []):
                api = self.convert_invite_to_api(inv)
                s = await self.fetch_server_data(api)
                servers_data.append(s)
                flat_status.append(s is not None)
            servers_data_all.append(servers_data)

        embed = await self.create_main_embed(cfgs, servers_data_all)
        view = MultiServerEmbedView(self, cfgs, servers_data_all)

        sent = await interaction.channel.send(embed=embed, view=view)
        self.server_status[sent.id] = flat_status
        self.embeds_data.append({
            "channel_id": interaction.channel.id,
            "message_id": sent.id,
            "cfgs": cfgs,
            "screen": "main",
            "server_page": 0,
            "player_page": 0,
            "today_page": 0,
            "can_update": True
        })
        self.save_embeds()
        await interaction.followup.send("Live embed created.", ephemeral=True)

    @tasks.loop(seconds=60)
    async def update_task(self):
        for cfg_data in self.embeds_data.copy():
            if not cfg_data.get("can_update"):
                continue
            try:
                channel = self.bot.get_channel(cfg_data["channel_id"])
                if not channel:
                    cfg_data["can_update"] = False
                    continue
                try:
                    message = await channel.fetch_message(cfg_data["message_id"])
                except discord.NotFound:
                    cfg_data["can_update"] = False
                    continue

                servers_data_all = []
                for cfg in cfg_data["cfgs"]:
                    servers_data = [await self.fetch_server_data(self.convert_invite_to_api(inv)) for inv in cfg.get("invite_links", [])]
                    servers_data_all.append(servers_data)

                screen = cfg_data.get("screen", "main")
                server_page = cfg_data.get("server_page", 0)
                player_page = cfg_data.get("player_page", 0)
                today_page = cfg_data.get("today_page", 0)

                embed = (
                    await self.create_main_embed(cfg_data["cfgs"], servers_data_all)
                    if screen == "main" else
                    await self.create_server_list_embed(cfg_data["cfgs"], servers_data_all, server_page)
                    if screen == "server_list" else
                    await self.create_today_embed(today_page)
                    if screen == "today" else
                    await self.create_player_embed(cfg_data["cfgs"], servers_data_all, player_page)
                )

                view = MultiServerEmbedView(self, cfg_data["cfgs"], servers_data_all)
                view.screen = screen
                view.server_page = server_page
                view.player_page = player_page
                view.today_page = today_page
                view.update_buttons()
                await message.edit(embed=embed, view=view)

            except Exception:
                cfg_data["can_update"] = False
                traceback.print_exc()
        self.save_embeds()

    @tasks.loop(minutes=2)
    async def check_servers_task(self):
        for cfg_data in self.embeds_data:
            if not cfg_data.get("can_update"):
                continue
            flat_status = self.server_status.get(cfg_data["message_id"], [])
            for cfg_idx, cfg in enumerate(cfg_data["cfgs"]):
                for inv_idx, inv in enumerate(cfg.get("invite_links", [])):
                    api = self.convert_invite_to_api(inv)
                    s = await self.fetch_server_data(api)
                    new_status = s is not None
                    old_status = flat_status[inv_idx] if inv_idx < len(flat_status) else True

                    if old_status and not new_status:
                        emoji = cfg.get("emoji", "")
                        server_name = cfg["custom_names"][inv_idx] if inv_idx < len(cfg["custom_names"]) else f"Server {inv_idx+1}"
                        alert_channel = self.bot.get_channel(ALERT_CHANNEL_ID)
                        if alert_channel:
                            role = alert_channel.guild.get_role(ALERT_ROLE_ID)
                            role_mention = role.mention if role else ""
                            content = f"{role_mention} {ALERT_USER}\n⚠️ A Server Has Gone Offline: {emoji} `{server_name}`"
                            await alert_channel.send(content=content, view=AlertClearButtonView(self, cfg_data, cfg, inv_idx, api_url=api))

                    if inv_idx >= len(flat_status):
                        flat_status.append(new_status)
                    else:
                        flat_status[inv_idx] = new_status

            self.server_status[cfg_data["message_id"]] = flat_status

    @update_task.before_loop
    @check_servers_task.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

class MultiServerEmbedView(discord.ui.View):
    def __init__(self, cog, cfgs, servers_data_all):
        super().__init__(timeout=None)
        self.cog = cog
        self.cfgs = cfgs
        self.servers_data_all = servers_data_all
        self.screen = "main"
        self.server_page = 0
        self.player_page = 0
        self.today_page = 0

        self.screen_select = discord.ui.Select(
            placeholder="Select Page",
            options=[
                discord.SelectOption(label="Main", value="main"),
                discord.SelectOption(label="Server List", value="server_list"),
                discord.SelectOption(label="Players", value="player_list"),
                discord.SelectOption(label="Today", value="today")
            ]
        )
        self.screen_select.callback = self.select_screen
        self.add_item(self.screen_select)

        self.prev_btn = discord.ui.Button(label="Prev", style=discord.ButtonStyle.secondary)
        self.prev_btn.callback = self.prev_page
        self.add_item(self.prev_btn)

        self.next_btn = discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary)
        self.next_btn.callback = self.next_page
        self.add_item(self.next_btn)

        self.update_buttons()

    async def select_screen(self, interaction: discord.Interaction):
        self.screen = interaction.data["values"][0]
        self.update_buttons()
        await self.update_embed(interaction)

    async def prev_page(self, interaction: discord.Interaction):
        if self.screen == "server_list":
            self.server_page = max(0, self.server_page - 1)
        elif self.screen == "player_list":
            self.player_page = max(0, self.player_page - 1)
        elif self.screen == "today":
            self.today_page = max(0, self.today_page - 1)
        self.update_buttons()
        await self.update_embed(interaction)

    async def next_page(self, interaction: discord.Interaction):
        servers_flat = [(cfg["custom_names"][idx] if idx < len(cfg["custom_names"]) else f"Server {idx+1}", s)
                        for cfg, servers_data in zip(self.cfgs, self.servers_data_all)
                        for idx, s in enumerate(servers_data)]
        total_players = sum(len([c for c in s.get("players", {}).get("Cars", []) if c.get("IsConnected")])
                            for _, s in servers_flat if s)
        max_server = (len(servers_flat) - 1)//5
        max_player_page = max(0, (total_players - 1)//5)

        today_players = self.cog.today_data.get(datetime.now(PACIFIC_TZ).strftime("%Y-%m-%d"), [])
        max_today_page = max(0, (len(today_players) - 1)//5)

        if self.screen == "server_list":
            self.server_page = min(max_server, self.server_page + 1)
        elif self.screen == "player_list":
            self.player_page = min(max_player_page, self.player_page + 1)
        elif self.screen == "today":
            self.today_page = min(max_today_page, self.today_page + 1)

        self.update_buttons()
        await self.update_embed(interaction)

    def update_buttons(self):
        servers_flat = [(cfg["custom_names"][idx] if idx < len(cfg["custom_names"]) else f"Server {idx+1}", s)
                        for cfg, servers_data in zip(self.cfgs, self.servers_data_all)
                        for idx, s in enumerate(servers_data)]
        total_players = sum(len([c for c in s.get("players", {}).get("Cars", []) if c.get("IsConnected")])
                            for _, s in servers_flat if s)
        max_server = (len(servers_flat) - 1)//5
        max_player_page = max(0, (total_players - 1)//5)
        today_players = self.cog.today_data.get(datetime.now(PACIFIC_TZ).strftime("%Y-%m-%d"), [])
        max_today_page = max(0, (len(today_players) - 1)//5)

        if self.screen == "main":
            self.prev_btn.disabled = True
            self.next_btn.disabled = True
        elif self.screen == "server_list":
            self.prev_btn.disabled = self.server_page == 0
            self.next_btn.disabled = self.server_page >= max_server
        elif self.screen == "player_list":
            self.prev_btn.disabled = self.player_page == 0
            self.next_btn.disabled = self.player_page >= max_player_page
        elif self.screen == "today":
            self.prev_btn.disabled = self.today_page == 0
            self.next_btn.disabled = self.today_page >= max_today_page

    async def update_embed(self, interaction: discord.Interaction):
        embed = (
            await self.cog.create_main_embed(self.cfgs, self.servers_data_all)
            if self.screen == "main" else
            await self.cog.create_server_list_embed(self.cfgs, self.servers_data_all, self.server_page)
            if self.screen == "server_list" else
            await self.cog.create_today_embed(self.today_page)
            if self.screen == "today" else
            await self.cog.create_player_embed(self.cfgs, self.servers_data_all, self.player_page)
        )

        for cfg_data in self.cog.embeds_data:
            if cfg_data["message_id"] == interaction.message.id:
                cfg_data["screen"] = self.screen
                cfg_data["server_page"] = self.server_page
                cfg_data["player_page"] = self.player_page
                cfg_data["today_page"] = self.today_page
                self.cog.save_embeds()
                break

        if interaction.response.is_done():
            await interaction.edit_original_message(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)


class AlertClearButtonView(discord.ui.View):
    def __init__(self, cog, embed_cfg, cfg, server_idx, api_url):
        super().__init__(timeout=None)
        self.cog = cog
        self.embed_cfg = embed_cfg
        self.cfg = cfg
        self.server_idx = server_idx
        self.api_url = api_url

    @discord.ui.button(label="Check Server", style=discord.ButtonStyle.success, custom_id="alert_fix_btn")
    async def check_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if not self.api_url:
            return await interaction.followup.send("No API URL found.", ephemeral=True)

        server_data = await self.cog.fetch_server_data(self.api_url)
        server_name = self.cfg["custom_names"][self.server_idx] if self.server_idx < len(self.cfg["custom_names"]) else f"Server {self.server_idx+1}"

        if server_data:
            flat_status = self.cog.server_status.get(self.embed_cfg["message_id"], [])
            if self.server_idx < len(flat_status):
                flat_status[self.server_idx] = True
                self.cog.server_status[self.embed_cfg["message_id"]] = flat_status

            channel = self.cog.bot.get_channel(self.embed_cfg["channel_id"])
            if channel:
                try:
                    message = await channel.fetch_message(self.embed_cfg["message_id"])
                    servers_data_all = [
                        [await self.cog.fetch_server_data(self.cog.convert_invite_to_api(inv)) for inv in cfg.get("invite_links", [])]
                        for cfg in self.embed_cfg["cfgs"]
                    ]
                    view = MultiServerEmbedView(self.cog, self.embed_cfg["cfgs"], servers_data_all)
                    view.screen = self.embed_cfg.get("screen", "main")
                    view.server_page = self.embed_cfg.get("server_page", 0)
                    view.player_page = self.embed_cfg.get("player_page", 0)
                    view.today_page = self.embed_cfg.get("today_page", 0)
                    view.update_buttons()
                    await message.edit(embed=await self.cog.create_main_embed(self.embed_cfg["cfgs"], servers_data_all), view=view)
                except Exception:
                    traceback.print_exc()

            try:
                await interaction.message.delete()
            except Exception:
                pass

            await interaction.followup.send(f"✅ `{server_name}` is back online! Embed refreshed.", ephemeral=True)
        else:
            await interaction.followup.send(f"⚠️ `{server_name}` is still offline.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(LiveEmbedManager(bot))

