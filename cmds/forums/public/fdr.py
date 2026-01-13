import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio

class FDRForumPostUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.forum_channel_id = 1268666206810931210
        
        self.api_urls = [
            "http://5.78.103.54:8080/INFO",
            "http://91.99.6.152:8080/INFO"
        ]
        self.image_links = {i: f"https://futurecrew.sirv.com/images/fdr/{i}.png" for i in range(63)}
        self.update_forum.start()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.update_forum_post()

    async def get_total_players(self):
        total_players = 0
        retries = 5
        delay = 1

        async with aiohttp.ClientSession() as session:
            for url in self.api_urls:
                for attempt in range(retries):
                    try:
                        async with session.get(url, timeout=10) as response:
                            if response.status == 200:
                                data = await response.json()
                                total_players += data.get("clients", 0)
                                break
                    except Exception:
                        await asyncio.sleep(delay)
        return total_players

    async def update_forum_post(self):
        channel = await self.bot.fetch_channel(self.forum_channel_id)
        total_players = await self.get_total_players()
        image_url = self.image_links.get(total_players, self.image_links[0])

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
                name="FDR Public Servers",
                content=image_url
            )
        except Exception:
            pass

    @tasks.loop(minutes=1)
    async def update_forum(self):
        try:
            await self.update_forum_post()
        except Exception as e:
            print(f"Error in update_forum: {e}")

async def setup(bot):
    await bot.add_cog(FDRForumPostUpdater(bot))
