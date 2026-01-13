import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

DATABASE = "whitelist.db"
USERS_PER_PAGE = 25  # Max per embed due to Discord field limit
ADMIN_ROLE_ID = 1251377219910242365
PERSIST_FILE = "whitelist_pagination.json"
UPDATE_INTERVAL = 300  # 5 minutes


class ShowSteamUsersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.pagination_data = {}
        self.update_task.start()

    async def cog_load(self):
        self.db = await aiosqlite.connect(DATABASE)
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS whitelist(
                discord_id TEXT PRIMARY KEY,
                steam_id TEXT
            )
        """)
        await self.db.commit()
        if os.path.exists(PERSIST_FILE):
            with open(PERSIST_FILE, "r") as f:
                self.pagination_data = json.load(f)
        await self.restore_views()

    async def cog_unload(self):
        if self.db:
            await self.db.close()
        self.update_task.cancel()

    def save_pagination(self):
        with open(PERSIST_FILE, "w") as f:
            json.dump(self.pagination_data, f)

    async def restore_views(self):
        for guild_id_str, data in self.pagination_data.items():
            try:
                channel = self.bot.get_channel(data["channel_id"])
                if not channel:
                    continue
                message = await channel.fetch_message(data["message_id"])
                if not message:
                    continue

                pages = data["pages"]
                current_page = data["current_page"]

                def generate_embed(page_index):
                    page_data = pages[page_index]
                    embed = discord.Embed(
                        title=f"Whitelist Users (Page {page_index + 1}/{len(pages)})",
                        description="All users currently whitelisted:",
                        color=0x2f3136
                    )
                    for i, (discord_id, steam_id) in enumerate(page_data):
                        display_steam = steam_id if steam_id else "N/A"
                        embed.add_field(
                            name=f"User #{i+1}",
                            value=f"<@{discord_id}>\nSteam ID: {display_steam}",
                            inline=False
                        )
                    la_now = datetime.now(ZoneInfo("America/Los_Angeles"))
                    footer_text = la_now.strftime("%m/%d/%Y %I:%M %p") + " • Presented by Future Crew"
                    embed.set_footer(text=footer_text)
                    return embed

                class PaginationView(discord.ui.View):
                    def __init__(self, cog, channel, message, pages, current_page=0):
                        super().__init__(timeout=None)
                        self.cog = cog
                        self.channel = channel
                        self.message = message
                        self.pages = pages
                        self.total_pages = len(pages)
                        self.current_page = current_page
                        self.generate_embed = generate_embed
                        self.update_buttons()

                    def update_buttons(self):
                        for child in self.children:
                            if child.label == "⬅️ Previous":
                                child.disabled = self.current_page == 0
                            elif child.label == "➡️ Next":
                                child.disabled = self.current_page >= self.total_pages - 1

                    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
                    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                        if self.current_page > 0:
                            self.current_page -= 1
                            self.update_buttons()
                            await interaction.response.edit_message(embed=self.generate_embed(self.current_page), view=self)
                            await self.save_current()
                        else:
                            await interaction.response.defer()

                    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary)
                    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                        if self.current_page < self.total_pages - 1:
                            self.current_page += 1
                            self.update_buttons()
                            await interaction.response.edit_message(embed=self.generate_embed(self.current_page), view=self)
                            await self.save_current()
                        else:
                            await interaction.response.defer()

                    @discord.ui.button(label="🔍 Search", style=discord.ButtonStyle.primary)
                    async def search_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                        class SearchModal(discord.ui.Modal, title="Search Whitelisted Users"):
                            query = discord.ui.TextInput(label="Discord Name or Steam ID", required=True, max_length=100)

                            async def on_submit(self2, modal_interaction: discord.Interaction):
                                results = []
                                for page in pages:
                                    for discord_id, steam_id in page:
                                        user_obj = self.cog.bot.get_user(int(discord_id))
                                        username = user_obj.name if user_obj else "Unknown"
                                        if self2.query.value.lower() in username.lower() or (steam_id and self2.query.value in steam_id):
                                            results.append((discord_id, steam_id))
                                if not results:
                                    await modal_interaction.response.send_message("No matching users found.", ephemeral=True)
                                    return

                                temp_pages = [results[i:i + USERS_PER_PAGE] for i in range(0, len(results), USERS_PER_PAGE)]
                                temp_embed = discord.Embed(
                                    title=f"Search Results (Page 1/{len(temp_pages)})",
                                    description=f"Results for '{self2.query.value}':",
                                    color=0x2f3136
                                )
                                for i, (discord_id, steam_id) in enumerate(temp_pages[0]):
                                    display_steam = steam_id if steam_id else "N/A"
                                    temp_embed.add_field(
                                        name=f"User #{i+1}",
                                        value=f"<@{discord_id}>\nSteam ID: {display_steam}",
                                        inline=False
                                    )
                                temp_embed.set_footer(text="Search Results")
                                await modal_interaction.response.send_message(embed=temp_embed, ephemeral=True)

                        await interaction.response.send_modal(SearchModal())

                view = PaginationView(self, channel, message, pages, current_page)
                await message.edit(embed=generate_embed(current_page), view=view)

            except Exception:
                continue

    @tasks.loop(seconds=UPDATE_INTERVAL)
    async def update_task(self):
        await self.bot.wait_until_ready()
        for guild_id_str, data in self.pagination_data.items():
            try:
                channel = self.bot.get_channel(data["channel_id"])
                if not channel:
                    continue
                message = await channel.fetch_message(data["message_id"])
                async with self.db.execute("SELECT discord_id, steam_id FROM whitelist ORDER BY discord_id") as c:
                    rows = await c.fetchall()
                if not rows:
                    continue
                pages = [rows[i:i + USERS_PER_PAGE] for i in range(0, len(rows), USERS_PER_PAGE)]
                current_page = data.get("current_page", 0)
                if current_page >= len(pages):
                    current_page = len(pages) - 1 if pages else 0

                def generate_embed(page_index):
                    page_data = pages[page_index]
                    embed = discord.Embed(
                        title=f"Whitelist Users (Page {page_index + 1}/{len(pages)})",
                        description="All users currently whitelisted:",
                        color=0x2f3136
                    )
                    for i, (discord_id, steam_id) in enumerate(page_data):
                        display_steam = steam_id if steam_id else "N/A"
                        embed.add_field(
                            name=f"User #{i+1}",
                            value=f"<@{discord_id}>\nSteam ID: {display_steam}",
                            inline=False
                        )
                    la_now = datetime.now(ZoneInfo("America/Los_Angeles"))
                    footer_text = la_now.strftime("%m/%d/%Y %I:%M %p") + " • Presented by Future Crew"
                    embed.set_footer(text=footer_text)
                    return embed

                class PaginationView(discord.ui.View):
                    def __init__(self, cog, channel, message, pages, current_page=0):
                        super().__init__(timeout=None)
                        self.cog = cog
                        self.channel = channel
                        self.message = message
                        self.pages = pages
                        self.total_pages = len(pages)
                        self.current_page = current_page
                        self.generate_embed = generate_embed
                        self.update_buttons()

                    def update_buttons(self):
                        for child in self.children:
                            if child.label == "⬅️ Previous":
                                child.disabled = self.current_page == 0
                            elif child.label == "➡️ Next":
                                child.disabled = self.current_page >= self.total_pages - 1

                    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
                    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                        if self.current_page > 0:
                            self.current_page -= 1
                            self.update_buttons()
                            await interaction.response.edit_message(embed=self.generate_embed(self.current_page), view=self)
                            await self.save_current()
                        else:
                            await interaction.response.defer()

                    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary)
                    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                        if self.current_page < self.total_pages - 1:
                            self.current_page += 1
                            self.update_buttons()
                            await interaction.response.edit_message(embed=self.generate_embed(self.current_page), view=self)
                            await self.save_current()
                        else:
                            await interaction.response.defer()

                    async def save_current(self):
                        self.cog.pagination_data[str(self.channel.guild.id)] = {
                            "channel_id": self.channel.id,
                            "message_id": self.message.id,
                            "pages": self.pages,
                            "current_page": self.current_page
                        }
                        self.cog.save_pagination()

                view = PaginationView(self, channel, message, pages, current_page)
                await message.edit(embed=generate_embed(current_page), view=view)

            except Exception:
                continue

    @update_task.before_loop
    async def before_update_task(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="showsteamusers", description="List all whitelisted users in a channel")
    @app_commands.describe(channel="Select the channel to send the user list")
    async def show_steam_users(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return
        if isinstance(interaction.user, discord.Member):
            if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
                await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
                return
        else:
            await interaction.response.send_message("❌ Could not verify your roles.", ephemeral=True)
            return

        async with self.db.execute("SELECT discord_id, steam_id FROM whitelist ORDER BY discord_id") as c:
            rows = await c.fetchall()
        if not rows:
            await interaction.response.send_message("No users found in the database.", ephemeral=True)
            return

        pages = [rows[i:i + USERS_PER_PAGE] for i in range(0, len(rows), USERS_PER_PAGE)]
        current_page = 0

        def generate_embed(page_index):
            page_data = pages[page_index]
            embed = discord.Embed(
                title=f"Whitelist Users (Page {page_index + 1}/{len(pages)})",
                description="All users currently whitelisted:",
                color=0x2f3136
            )
            for i, (discord_id, steam_id) in enumerate(page_data):
                display_steam = steam_id if steam_id else "N/A"
                embed.add_field(
                    name=f"User #{i+1}",
                    value=f"<@{discord_id}>\nSteam ID: {display_steam}",
                    inline=False
                )
            la_now = datetime.now(ZoneInfo("America/Los_Angeles"))
            footer_text = la_now.strftime("%m/%d/%Y %I:%M %p") + " • Presented by Future Crew"
            embed.set_footer(text=footer_text)
            return embed

        embed = generate_embed(current_page)

        class PaginationView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                self.current_page = current_page
                self.pages = pages
                self.total_pages = len(pages)
                self.generate_embed = generate_embed
                self.update_buttons()

            def update_buttons(self):
                for child in self.children:
                    if child.label == "⬅️ Previous":
                        child.disabled = self.current_page == 0
                    elif child.label == "➡️ Next":
                        child.disabled = self.current_page >= self.total_pages - 1

            @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
            async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_page > 0:
                    self.current_page -= 1
                    self.update_buttons()
                    await interaction.response.edit_message(embed=self.generate_embed(self.current_page), view=self)
                    self.save_current()
                else:
                    await interaction.response.defer()

            @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary)
            async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_page < self.total_pages - 1:
                    self.current_page += 1
                    self.update_buttons()
                    await interaction.response.edit_message(embed=self.generate_embed(self.current_page), view=self)
                    self.save_current()
                else:
                    await interaction.response.defer()

            def save_current(self):
                self.cog.pagination_data[str(interaction.guild.id)] = {
                    "channel_id": channel.id,
                    "message_id": message.id,
                    "pages": pages,
                    "current_page": self.current_page
                }
                self.cog.save_pagination()

        view = PaginationView()
        view.cog = self
        message = await channel.send(embed=embed, view=view)
        view.message = message
        self.pagination_data[str(interaction.guild.id)] = {
            "channel_id": channel.id,
            "message_id": message.id,
            "pages": pages,
            "current_page": current_page
        }
        self.save_pagination()
        await interaction.response.send_message(f"✅ User list sent to {channel.mention}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ShowSteamUsersCog(bot))
