import discord
from discord.ext import commands, tasks
import aiohttp

class ForumPostUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.forum_channel_id = 1268666206810931210  # Replace with your actual channel ID
        self.api_url = "http://5.78.75.101:8082/INFO"
        self.image_links = {
            0: "https://media.discordapp.net/attachments/1187595037937250315/1342715428291477626/0.png?ex=67baa4b0&is=67b95330&hm=4c6d776f32963590e155fe7fb313180bc8b393cbf76d855fb3023ffdd1f65527&=&format=webp&quality=lossless&width=1193&height=671",
            1: "https://media.discordapp.net/attachments/1187595037937250315/1342715428840935474/1.png?ex=67baa4b0&is=67b95330&hm=cdc9abb8bd7bbea543054765c82d35952788712d7b34d0f823d47cfea58a58f2&=&format=webp&quality=lossless&width=1193&height=671",
            2: "https://media.discordapp.net/attachments/1187595037937250315/1342715429335994469/2.png?ex=67baa4b0&is=67b95330&hm=dc68c59de6df793376c0069f5529adde9245b7e9d6be5e292a8e0570fd04a312&=&format=webp&quality=lossless&width=1193&height=671",
            3: "https://media.discordapp.net/attachments/1187595037937250315/1342715429948358710/3.png?ex=67baa4b0&is=67b95330&hm=b54fac5184d9ea88c7c5f0c99e1e20b41283dab42b8044b074072d3a1d8cbc9b&=&format=webp&quality=lossless&width=1193&height=671",
            4: "https://media.discordapp.net/attachments/1187595037937250315/1342715430682497147/4.png?ex=67baa4b1&is=67b95331&hm=37c158541dc329b4f41a0754b88bb2ff49a8d804423d01956b1a4416de17a8a8&=&format=webp&quality=lossless&width=1193&height=671",
            5: "https://media.discordapp.net/attachments/1187595037937250315/1342715431206654004/5.png?ex=67baa4b1&is=67b95331&hm=14f2dba6033694b8f52cca24757736a9ae114dcbfdff4a1c5ed68c5036401c88&=&format=webp&quality=lossless&width=1193&height=671",
            6: "https://media.discordapp.net/attachments/1187595037937250315/1342715431739461664/6.png?ex=67baa4b1&is=67b95331&hm=1583182269e314baa9135f5d86c1d4bbc67d666e9b47a3f50f1dc8121a3cd849&=&format=webp&quality=lossless&width=1193&height=671",
            7: "https://media.discordapp.net/attachments/1187595037937250315/1342715432234258514/7.png?ex=67baa4b1&is=67b95331&hm=922730faa6aaf94d61deed468a0759ef4ceadbe8f384b569bd53666ddf100f3c&=&format=webp&quality=lossless&width=1193&height=671",
            8: "https://media.discordapp.net/attachments/1187595037937250315/1342715432762871921/8.png?ex=67baa4b1&is=67b95331&hm=3ca824ab328115c2f3966d61c7654c6c3d9d0d02f4d1179827401ea648d8699e&=&format=webp&quality=lossless&width=1193&height=671",
            9: "https://media.discordapp.net/attachments/1187595037937250315/1342715433303674911/9.png?ex=67baa4b1&is=67b95331&hm=3f3d8654408a8e6e3e90358c9f9e8ba9d59f1065053fad3d3bed5af88749aa95&=&format=webp&quality=lossless&width=1193&height=671",
            10: "https://media.discordapp.net/attachments/1187595037937250315/1342715433458995312/10.png?ex=67baa4b1&is=67b95331&hm=c683ec8efab6f655c5a036ed81eb6f17d730fb1f636fc24c6ce18e51b99ebc2b&=&format=webp&quality=lossless&width=1193&height=671",
            11: "https://media.discordapp.net/attachments/1187595037937250315/1342715433949597717/11.png?ex=67baa4b1&is=67b95331&hm=723417f4c83c7b8b6af62882b2335a021c70dd7e005d38645893464d05dd7f9b&=&format=webp&quality=lossless&width=1193&height=671",
            12: "https://media.discordapp.net/attachments/1187595037937250315/1342715434679402587/12.png?ex=67baa4b2&is=67b95332&hm=e8357e48272092fc5adedfc03b8c8f01761eb169e76bdadab2d29866ad39a439&=&format=webp&quality=lossless&width=1193&height=671",
            13: "https://media.discordapp.net/attachments/1187595037937250315/1342715432427327610/13.png?ex=67baa4b1&is=67b95331&hm=f5611fef8321228ea5447118029763684b022b43031744bbcde63527f3dbc178&=&format=webp&quality=lossless&width=1193&height=671",
            14: "https://media.discordapp.net/attachments/1187595037937250315/1342715432947159051/14.png?ex=67baa4b1&is=67b95331&hm=1058b991a79416429cf593a5f39dafa765b5693b4d711e7cb0f2245db56ca96f&=&format=webp&quality=lossless&width=1193&height=671",
            15: "https://media.discordapp.net/attachments/1187595037937250315/1342715451809075220/15.png?ex=67baa4b6&is=67b95336&hm=02887ae3e43783fcd047f56915639fcd4688dd3e9d3c6774267f79da438c8c7a&=&format=webp&quality=lossless&width=1193&height=671",
            16: "https://media.discordapp.net/attachments/1187595037937250315/1342715452308066417/16.png?ex=67baa4b6&is=67b95336&hm=7511b0bb2d613b10851e9ae7e73b4ac9a9f262eaee9a727fe15a3c0c7cf4713c&=&format=webp&quality=lossless&width=1193&height=671",
            17: "https://media.discordapp.net/attachments/1187595037937250315/1342715452786475009/17.png?ex=67baa4b6&is=67b95336&hm=cd5c7e410bfd960899dc5804b1f2692a48ab8a736b89e98974348bf405be30bd&=&format=webp&quality=lossless&width=1193&height=671",
            18: "https://media.discordapp.net/attachments/1187595037937250315/1342715453319024730/18.png?ex=67baa4b6&is=67b95336&hm=8b6e6eb918b7744f6ca1f83f9a19e16dac53e1f55e11fe7976fa9de0f853c2fe&=&format=webp&quality=lossless&width=1193&height=671",
            19: "https://media.discordapp.net/attachments/1187595037937250315/1342715453805432862/19.png?ex=67baa4b6&is=67b95336&hm=437b4f058e41a4129a7c3a92c4eed618e11981dba7b6546eb2582979d16dfe98&=&format=webp&quality=lossless&width=1193&height=671",
            20: "https://media.discordapp.net/attachments/1187595037937250315/1342715454329716737/20.png?ex=67baa4b6&is=67b95336&hm=f871479fa8d9c32a944c8d6a23b68e218bb1355080893bc489bfb94f3ff04a02&=&format=webp&quality=lossless&width=1193&height=671",
        }
        self.update_forum.start()

    @commands.Cog.listener()
    async def on_ready(self):
        """Triggered when the bot is ready."""
        print("Bot is ready.")
        await self.update_forum_post()

    async def get_player_count(self):
        """Fetch the player count from the server API."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.api_url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("clients", 0) 
                    else:
                        print(f"Error: Server responded with status code {response.status}")
                        return 0
            except Exception as e:
                print(f"Error fetching player count: {e}")
                return 0

    async def update_forum_post(self):
        """Update the bot's messages with the latest player count or create a new message if none exist."""
        channel = await self.bot.fetch_channel(self.forum_channel_id)
        player_count = await self.get_player_count()
        image_url = self.image_links.get(player_count, self.image_links[0])  # Default to 0 players

        # Check for threads (forum posts) within the channel
        for thread in channel.threads:
            # Check messages in each thread
            async for message in thread.history(limit=200):
                if message.author == self.bot.user:  # Only consider messages from the bot
                    for key, url in self.image_links.items():
                        if url in message.content:  # Check if the message contains an image URL
                            try:
                                await message.edit(content=f"{image_url}")
                                print(f"Updated message with ID {message.id}.")
                                return  # Exit after updating the message
                            except Exception as e:
                                print(f"Error updating message {message.id}: {e}")
                                return

        # If no matching message found, create a new one
        print("No matching messages found. Creating a new one.")
        await self.create_new_post(image_url)

    async def create_new_post(self, image_url):
        """Create a new post if no previous messages were found."""
        channel = await self.bot.fetch_channel(self.forum_channel_id)

        try:
            # Create a new thread (forum post)
            thread = await channel.create_thread(
                name=f"Hamburg",
                content=f"{image_url}"
            )
            print(f"Created new forum thread with ID {thread.id}")
        except Exception as e:
            print(f"Error creating new forum post: {e}")

    @tasks.loop(minutes=1)
    async def update_forum(self):
        """Check and update the bot's messages every minute."""
        await self.update_forum_post()

async def setup(bot):
    cog = ForumPostUpdater(bot)
    await bot.add_cog(cog)