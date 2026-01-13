import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio

class WhitelineForumPostUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.forum_channel_id = 1288026835233538091
        self.api_url = "http://5.78.93.251:8080/info"

        self.image_links = {i: f"https://futurecrew.sirv.com/images/whiteline/{i}.png" for i in range(23)}

        self.update_forum.start()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.update_forum_post()

    async def get_player_count(self):
        retries = 5
        delay = 1
        async with aiohttp.ClientSession() as session:
            for _ in range(retries):
                try:
                    async with session.get(self.api_url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data.get("clients", 0)
                except Exception:
                    await asyncio.sleep(delay)
        return 0

    async def update_forum_post(self):
        channel = await self.bot.fetch_channel(self.forum_channel_id)
        player_count = await self.get_player_count()
        image_url = self.image_links.get(player_count, self.image_links[0])

        for thread in channel.threads:
            async for message in thread.history(limit=200):
                if message.author == self.bot.user:
                    for url in self.image_links.values():
                        if url in message.content:
                            try:
                                await message.edit(content=image_url)
                                return
                            except Exception:
                                return

        await self.create_new_post(image_url)

    async def create_new_post(self, image_url):
        channel = await self.bot.fetch_channel(self.forum_channel_id)
        try:
            await channel.create_thread(
                name="Whiteline",
                content=image_url
            )
        except Exception:
            pass

    @tasks.loop(minutes=1)
    async def update_forum(self):
        try:
            await self.update_forum_post()
        except Exception:
            pass

async def setup(bot):
    cog = WhitelineForumPostUpdater(bot)
    await bot.add_cog(cog)
