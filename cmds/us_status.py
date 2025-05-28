import discord
from discord.ext import commands, tasks
import aiohttp

class ForumUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.forum_channel_id =
        self.api_urls = [
            "http://.../INFO",
            "http://.../INFO"
        ]
        self.image_links = {
            0: "",
            1: "",
            2: "",
            3: "",
            4: "",
            5: "",
            6: "",
            7: "",
            8: "",
            9: "",
            10: "",
            11: "",
            12: "",
            13: "",
            14: "",
            15: "",
            16: "",
            17: "",
            18: "",
            19: "",
            20: "",
        }
        self.update_forum.start()

    @commands.Cog.listener()
    async def on_ready(self):
        print("ForumUpdater is ready.")
        await self.update_forum_post()

    async def get_player_count(self):
        total_players = 0
        async with aiohttp.ClientSession() as session:
            for url in self.api_urls:
                try:
                    async with session.get(url, timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            total_players += data.get("clients", 0)
                        else:
                            print(f"Failed to fetch {url}, status: {resp.status}")
                except Exception as e:
                    print(f"Error fetching {url}: {e}")
        return total_players

    async def update_forum_post(self):
        channel = await self.bot.fetch_channel(self.forum_channel_id)
        player_count = await self.get_player_count()
        image_url = self.image_links.get(player_count, self.image_links[0])

        # channel.threads is a normal list, so use regular for loop
        for thread in channel.threads:
            async for message in thread.history(limit=100):
                if message.author == self.bot.user and any(url in message.content for url in self.image_links.values()):
                    try:
                        await message.edit(content=image_url)
                        print(f"Updated message {message.id} in thread {thread.name}")
                        return
                    except Exception as e:
                        print(f"Failed to edit message {message.id}: {e}")
                        return

        print("No existing bot message found, creating new thread...")
        await self.create_new_thread(image_url)

    async def create_new_thread(self, image_url):
        channel = await self.bot.fetch_channel(self.forum_channel_id)
        try:
            thread = await channel.create_thread(name="US SRP Public")
            await thread.send(content=image_url)
            print(f"Created new thread {thread.id} and posted image.")
        except Exception as e:
            print(f"Error creating new thread: {e}")

    @tasks.loop(minutes=1)
    async def update_forum(self):
        await self.update_forum_post()

async def setup(bot):
    await bot.add_cog(ForumUpdater(bot))
