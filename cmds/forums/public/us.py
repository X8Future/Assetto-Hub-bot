import discord
from discord.ext import commands, tasks
import aiohttp

class USForumPostUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.forum_channel_id = 1268666206810931210
        self.api_urls = [
            "http://5.78.46.52:8081/INFO",
            "http://5.78.46.52:8080/INFO"
        ]
        self.image_links = {
            0: "https://media.discordapp.net/attachments/1187595037937250315/1340159084732878930/0.png",
            1: "https://media.discordapp.net/attachments/1187595037937250315/1340159085475008512/1.png",
            2: "https://media.discordapp.net/attachments/1187595037937250315/1340159086163132446/2.png",
            3: "https://media.discordapp.net/attachments/1187595037937250315/1340159079368232980/3.png",
            4: "https://media.discordapp.net/attachments/1187595037937250315/1340159080257421353/4.png",
            5: "https://media.discordapp.net/attachments/1187595037937250315/1340159080916058163/5.png",
            6: "https://media.discordapp.net/attachments/1187595037937250315/1340159081737883729/6.png",
            7: "https://media.discordapp.net/attachments/1187595037937250315/1340159082463494205/7.png",
            8: "https://media.discordapp.net/attachments/1187595037937250315/1340159083222925312/8.png",
            9: "https://media.discordapp.net/attachments/1187595037937250315/1340159084078301216/9.png",
            10: "https://media.discordapp.net/attachments/1187595037937250315/1340159296037589074/10.png",
            11: "https://media.discordapp.net/attachments/1187595037937250315/1340159296809205840/11.png",
            12: "https://media.discordapp.net/attachments/1187595037937250315/1340159297559990292/12.png",
            13: "https://media.discordapp.net/attachments/1187595037937250315/1340159294393421864/13.png",
            14: "https://media.discordapp.net/attachments/1187595037937250315/1340159295211175977/14.png",
            15: "https://media.discordapp.net/attachments/1187595037937250315/1340159299120267328/15.png",
            16: "https://media.discordapp.net/attachments/1187595037937250315/1340159299888087072/16.png",
            17: "https://media.discordapp.net/attachments/1187595037937250315/1340159300634542141/17.png",
            18: "https://media.discordapp.net/attachments/1187595037937250315/1340159301364219999/18.png",
            19: "https://media.discordapp.net/attachments/1187595037937250315/1340159298289926185/19.png",
            20: "https://media.discordapp.net/attachments/1187595037937250315/1340159290971000941/20.png",
        }
        self.update_forum.start()

    @commands.Cog.listener()
    async def on_ready(self):
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
                except Exception:
                    pass
        return total_players

    async def update_forum_post(self):
        channel = await self.bot.fetch_channel(self.forum_channel_id)
        player_count = await self.get_player_count()
        image_url = self.image_links.get(player_count, self.image_links[0])

        for thread in channel.threads:
            async for message in thread.history(limit=100):
                if message.author == self.bot.user and any(url in message.content for url in self.image_links.values()):
                    try:
                        await message.edit(content=image_url)
                        return
                    except Exception:
                        return

        await self.create_new_thread(image_url)

    async def create_new_thread(self, image_url):
        channel = await self.bot.fetch_channel(self.forum_channel_id)
        try:
            thread = await channel.create_thread(name="US SRP Public")
            await thread.send(content=image_url)
        except Exception:
            pass

    @tasks.loop(minutes=1)
    async def update_forum(self):
        await self.update_forum_post()

async def setup(bot):
    await bot.add_cog(USForumPostUpdater(bot))
