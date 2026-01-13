import discord
from discord.ext import commands, tasks
import aiohttp

class HamburgForumPostUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.forum_channel_id = 1268666206810931210
        self.api_url = "http://5.78.75.101:8082/INFO"
        self.image_links = {
            0: "https://media.discordapp.net/attachments/1187595037937250315/1342715428291477626/0.png?",
            1: "https://media.discordapp.net/attachments/1187595037937250315/1342715428840935474/1.png?",
            2: "https://media.discordapp.net/attachments/1187595037937250315/1342715429335994469/2.png?",
            3: "https://media.discordapp.net/attachments/1187595037937250315/1342715429948358710/3.png?",
            4: "https://media.discordapp.net/attachments/1187595037937250315/1342715430682497147/4.png?",
            5: "https://media.discordapp.net/attachments/1187595037937250315/1342715431206654004/5.png?",
            6: "https://media.discordapp.net/attachments/1187595037937250315/1342715431739461664/6.png?",
            7: "https://media.discordapp.net/attachments/1187595037937250315/1342715432234258514/7.png?",
            8: "https://media.discordapp.net/attachments/1187595037937250315/1342715432762871921/8.png?",
            9: "https://media.discordapp.net/attachments/1187595037937250315/1342715433303674911/9.png?",
            10: "https://media.discordapp.net/attachments/1187595037937250315/1342715433458995312/10.png?",
            11: "https://media.discordapp.net/attachments/1187595037937250315/1342715433949597717/11.png?",
            12: "https://media.discordapp.net/attachments/1187595037937250315/1342715434679402587/12.png?",
            13: "https://media.discordapp.net/attachments/1187595037937250315/1342715432427327610/13.png?",
            14: "https://media.discordapp.net/attachments/1187595037937250315/1342715432947159051/14.png?",
            15: "https://media.discordapp.net/attachments/1187595037937250315/1342715451809075220/15.png?",
            16: "https://media.discordapp.net/attachments/1187595037937250315/1342715452308066417/16.png?",
            17: "https://media.discordapp.net/attachments/1187595037937250315/1342715452786475009/17.png?",
            18: "https://media.discordapp.net/attachments/1187595037937250315/1342715453319024730/18.png?",
            19: "https://media.discordapp.net/attachments/1187595037937250315/1342715453805432862/19.png?",
            20: "https://media.discordapp.net/attachments/1187595037937250315/1342715454329716737/20.png?",
        }
        self.update_forum.start()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.update_forum_post()

    async def get_player_count(self):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.api_url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("clients", 0) 
                    else:
                        return 0
            except Exception:
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
                                await message.edit(content=f"{image_url}")
                                return
                            except Exception:
                                return

        await self.create_new_post(image_url)

    async def create_new_post(self, image_url):
        channel = await self.bot.fetch_channel(self.forum_channel_id)
        try:
            await channel.create_thread(
                name=f"Hamburg Public Servers",
                content=f"{image_url}"
            )
        except Exception:
            pass

    @tasks.loop(minutes=1)
    async def update_forum(self):
        await self.update_forum_post()

async def setup(bot):
    cog = HamburgForumPostUpdater(bot)
    await bot.add_cog(cog)
