import discord
from discord.ext import commands, tasks
import requests
import asyncio

class ServerEmbedUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_info = []  # Store server info for each API endpoint
        self.embed = None  # The embed to update
        self.update_task.start()

    @commands.command(name="serveradd")
    async def server_add(self, ctx, *api_endpoints):
        """
        Add server APIs and generate an embed.
        :param api_endpoints: Multiple API endpoints (optional)
        """

        if not api_endpoints:
            await ctx.send("Please provide at least one API endpoint.")
            return
        
        self.server_info = []
        for endpoint in api_endpoints:
            data = await self.fetch_server_info(endpoint)
            if data:
                self.server_info.append(data)
        
        if not self.server_info:
            await ctx.send("Failed to retrieve any server info. Please check your API endpoints.")
            return
        
        self.embed = await self.create_server_embed()
        
        # Send the embed initially
        await ctx.send(embed=self.embed)
        
    async def fetch_server_info(self, api_endpoint):
        """Fetch data from the provided API endpoint."""
        try:
            response = requests.get(api_endpoint)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching from {api_endpoint}: {response.status_code}")
        except Exception as e:
            print(f"Exception occurred for {api_endpoint}: {e}")
        return None

    async def create_server_embed(self):
        """Create an embed displaying server data."""
        embed = discord.Embed(title="Server Info", color=0x42E3F5)
        row = 0

        # For each server info, create a field in the embed
        for idx, data in enumerate(self.server_info):
            server_number = idx + 1  # Number the servers (1️⃣, 2️⃣, 3️⃣,...)
            ip, port = data["address"].split(":")
            clients = data["clients"]  # Assuming the key "clients" holds the number of clients
            
            embed.add_field(
                name=f"{server_number}️⃣ {data['serverName']}",
                value=f"🟢 Public Slots: {clients} / {data['max_clients']}\n"
                      f":InThat: VIP Cars: {data['vip_cars']} / {data['max_vip_cars']}\n"
                      f"▶ ENTER HERE! [Connect Link](https://acstuff.ru/s/q:race/online/join?ip={ip}&httpPort={port})",
                inline=True
            )

        embed.timestamp = discord.utils.utcnow()
        return embed

    @tasks.loop(minutes=1)
    async def update_task(self):
        """Check every minute to update the embed if needed."""
        if not self.server_info:
            return
        
        updated_embed = await self.create_server_embed()

        # Check if the client count has changed and if so, update the embed
        for idx, data in enumerate(self.server_info):
            new_clients = data["clients"]
            old_clients = self.embed.fields[idx].value.split("\n")[0].split(":")[1].strip()

            if new_clients != int(old_clients):
                # If client count changed, update that particular field
                updated_embed.set_field_at(
                    idx,
                    name=self.embed.fields[idx].name,
                    value=self.embed.fields[idx].value.replace(old_clients, str(new_clients))
                )

        # If anything changed, update the message
        if updated_embed != self.embed:
            self.embed = updated_embed
            await self.update_embed_message(updated_embed)

    async def update_embed_message(self, embed):
        """Update the embed message in the same channel."""
        for channel in self.bot.guilds[0].text_channels:  # Change this to select the correct channel
            if channel.name == "your-channel-name":  # Change to your desired channel name
                messages = await channel.history(limit=1).flatten()
                if messages:
                    await messages[0].edit(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ServerEmbedUpdater(bot))

