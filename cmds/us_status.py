import discord
from discord.ext import commands, tasks
import aiohttp

class ForumUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.forum_channel_id = 1268666206810931210 
        self.api_urls = [
            "http://5.78.46.52:8081/INFO",
            "http://5.78.46.52:8080/INFO"
        ]
        self.image_links = {
                0: "https://media.discordapp.net/attachments/1187595037937250315/1340159084732878930/0.png?ex=67b157e8&is=67b00668&hm=c932bf2d6f72f86ef7f591461b540f9f274e7c99529701547984c0554ac17414&=&format=webp&quality=lossless&width=1193&height=671",
                1: "https://media.discordapp.net/attachments/1187595037937250315/1340159085475008512/1.png?ex=67b157e8&is=67b00668&hm=9bff52cb812a90c5983c4e704162a672d445c89ecc11078be9ab765c9e12c574&=&format=webp&quality=lossless&width=1193&height=671",
                2: "https://media.discordapp.net/attachments/1187595037937250315/1340159086163132446/2.png?ex=67b157e9&is=67b00669&hm=1d135ac7d3c100aa493ccc78ebe234657a1a62dd9faedf65c9de04bef0b7e781&=&format=webp&quality=lossless&width=1193&height=671",
                3: "https://media.discordapp.net/attachments/1187595037937250315/1340159079368232980/3.png?ex=67b157e7&is=67b00667&hm=a1f600e59895fbf8a0f202d363e70d818383ead825d5786ca43f044606ce7283&=&format=webp&quality=lossless&width=1193&height=671",
                4: "https://media.discordapp.net/attachments/1187595037937250315/1340159080257421353/4.png?ex=67b157e7&is=67b00667&hm=c17f444a32174ebbc5c29bd94d61ae4ab22918065843e0150617aa938dabdf31&=&format=webp&quality=lossless&width=1193&height=671",
                5: "https://media.discordapp.net/attachments/1187595037937250315/1340159080916058163/5.png?ex=67b157e7&is=67b00667&hm=69b1c74c794f3ca105a339345569e353bd1f3a68e49c256e6c1682d0a0786901&=&format=webp&quality=lossless&width=1193&height=671",
                6: "https://media.discordapp.net/attachments/1187595037937250315/1340159081737883729/6.png?ex=67b157e8&is=67b00668&hm=f2a29ea6a2f0b5b7ffd978e8d012d085e2a64296da3ed5dc728b7fac1c4d6821&=&format=webp&quality=lossless&width=1193&height=671",
                7: "https://media.discordapp.net/attachments/1187595037937250315/1340159082463494205/7.png?ex=67b157e8&is=67b00668&hm=edb27697c3078bb0b513273c19b4fe21d6ee0d9db0dd09c2abc14d141e93c992&=&format=webp&quality=lossless&width=1193&height=671",
                8: "https://media.discordapp.net/attachments/1187595037937250315/1340159083222925312/8.png?ex=67b157e8&is=67b00668&hm=4279401842f99818a8e20e40a0c3106567f80d4e4fe77f48f3dbdb828e03e435&=&format=webp&quality=lossless&width=1193&height=671",
                9: "https://media.discordapp.net/attachments/1187595037937250315/1340159084078301216/9.png?ex=67b157e8&is=67b00668&hm=e8af24c985fbcbcd0f3447a173123b42d3925903c16224454c1e70b760a687f8&=&format=webp&quality=lossless&width=1193&height=671",
                10: "https://media.discordapp.net/attachments/1187595037937250315/1340159296037589074/10.png?ex=67b1581b&is=67b0069b&hm=c04a86d6e39adc4e005eb7249d27ec74a91516b8195722e8bbe98e99270e9f73&=&format=webp&quality=lossless&width=1193&height=671",
                11: "https://media.discordapp.net/attachments/1187595037937250315/1340159296809205840/11.png?ex=67b1581b&is=67b0069b&hm=2804053774d6db878849e5c0b3cd10cb2acb53034009e75035020bfe4e4a1932&=&format=webp&quality=lossless&width=1193&height=671",
                12: "https://media.discordapp.net/attachments/1187595037937250315/1340159297559990292/12.png?ex=67b1581b&is=67b0069b&hm=9b8c775cc70933c60c2e7accf8c21e0f32e6e09169fd61decd6872e7cd8b0472&=&format=webp&quality=lossless&width=1193&height=671",
                13: "https://media.discordapp.net/attachments/1187595037937250315/1340159294393421864/13.png?ex=67b1581a&is=67b0069a&hm=b3668f2e525d98306c856cb3d8502f1b569ce4a852ab187981774ed66dc7fdf5&=&format=webp&quality=lossless&width=1193&height=671",
                14: "https://media.discordapp.net/attachments/1187595037937250315/1340159295211175977/14.png?ex=67b1581a&is=67b0069a&hm=5fc60fda663ac684d314ea906d273e7c1d5139b8a90b6d7eb3ad2a5e55b73632&=&format=webp&quality=lossless&width=1193&height=671",
                15: "https://media.discordapp.net/attachments/1187595037937250315/1340159299120267328/15.png?ex=67b1581b&is=67b0069b&hm=965cacbf118605a32454a381a2e32073f35de37801d99012bf5853281743ed73&=&format=webp&quality=lossless&width=1193&height=671",
                16: "https://media.discordapp.net/attachments/1187595037937250315/1340159299888087072/16.png?ex=67b1581c&is=67b0069c&hm=4a1c3dc4ac48b8813573fdc234e4ce2a74919e21a291662d0bedfcaa9573d55e&=&format=webp&quality=lossless&width=1193&height=671",
                17: "https://media.discordapp.net/attachments/1187595037937250315/1340159300634542141/17.png?ex=67b1581c&is=67b0069c&hm=f552fc0e03261bba28d7630fe924c602ddd867f20f1d55a25510c7da993c20d3&=&format=webp&quality=lossless&width=1193&height=671",
                18: "https://media.discordapp.net/attachments/1187595037937250315/1340159301364219999/18.png?ex=67b1581c&is=67b0069c&hm=d7e7e6f0992701c96e1917fff5786bd22ee6fd57174285bd1ea1528d50c360ac&=&format=webp&quality=lossless&width=1193&height=671",
                19: "https://media.discordapp.net/attachments/1187595037937250315/1340159298289926185/19.png?ex=67b1581b&is=67b0069b&hm=e56d6ce13b7674f401bb2131ad83d0ac8fb9d0a9dd3c805ef9cf1092355d51e9&=&format=webp&quality=lossless&width=1193&height=671",
                20: "https://media.discordapp.net/attachments/1187595037937250315/1340159290971000941/20.png?ex=67b15819&is=67b00699&hm=684fa4f20a241182c96f9ded2435d2e2239673035ee54c81500c9b236196b4d6&=&format=webp&quality=lossless&width=1193&height=671"
        }
        self.update_forum.start()

    @commands.Cog.listener()
    async def on_ready(self):
        """Triggered when the bot is ready."""
        print("Bot is ready.")
        await self.update_forum_post()

    async def get_player_count(self):
        """Fetch the player count from both server APIs and sum them."""
        total_players = 0
        async with aiohttp.ClientSession() as session:
            for url in self.api_urls:
                try:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            total_players += data.get("clients", 0)  # Sum up clients from both APIs
                        else:
                            print(f"Error: Server responded with status code {response.status} for {url}")
                except Exception as e:
                    print(f"Error fetching data from {url}: {e}")
        return total_players

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
                name=f"US SRP Public",
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
    cog = ForumUpdater(bot)
    if not bot.get_cog("ForumUpdater"):
        await bot.load_extension("cmds.us_status")
