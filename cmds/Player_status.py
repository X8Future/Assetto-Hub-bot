import discord
from discord.ext import commands, tasks
import aiohttp

class ForumUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.forum_channel_id = 1268666206810931210  # Replace with your actual channel ID
        self.api_url = "http://5.78.103.54:8080/INFO"  # API to get player count
        self.image_links = {
            0: "https://media.discordapp.net/attachments/1187595037937250315/1340133950395387976/0.png?ex=67b14080&is=67afef00&hm=2e35f6f3f73e88be9171cf75fdf7192f6e795818b451852e458f4545e73c8db8&=&format=webp&quality=lossless&width=1193&height=671",
            1: "https://media.discordapp.net/attachments/1187595037937250315/1340133951049699328/1.png?ex=67b14080&is=67afef00&hm=011a610b737e0964e04674488d29bf80b12780b23ca72c810cb98c712b8253b9&=&format=webp&quality=lossless&width=1193&height=671",
            2: "https://media.discordapp.net/attachments/1187595037937250315/1340133951737696336/2.png?ex=67b14080&is=67afef00&hm=66f1c36f17cd3a68e52e20a7194d3486fd81fa09a036e948a1d3283f318eae3d&=&format=webp&quality=lossless&width=1193&height=671",
            3: "https://media.discordapp.net/attachments/1187595037937250315/1340133952500797480/3.png?ex=67b14080&is=67afef00&hm=70a6b06a9fe757ac8ea684409e3a606d2f54c41aaf77f3489e34bd7018525dd1&=&format=webp&quality=lossless&width=1193&height=671",
            4: "https://media.discordapp.net/attachments/1187595037937250315/1340133953180401684/4.png?ex=67b14080&is=67afef00&hm=1b5f65567f555514d4cfb73673afc63e82f55b380d340202a3ba70016948b6b6&=&format=webp&quality=lossless&width=1193&height=671",
            5: "https://media.discordapp.net/attachments/1187595037937250315/1340134022319444060/5.png?ex=67b14091&is=67afef11&hm=c6e77b130c462a8912a9841412443fa3e1648e6c512e355b691d56074b60b741&=&format=webp&quality=lossless&width=1193&height=671",
            6: "https://media.discordapp.net/attachments/1187595037937250315/1340133954027655178/6.png?ex=67b14081&is=67afef01&hm=bb857eb547e45fbe77dbe145fa1933b4e0c6151d8d23d4d16012a376bee9f966&=&format=webp&quality=lossless&width=1193&height=671",
            7: "https://media.discordapp.net/attachments/1187595037937250315/1340133954732429347/7.png?ex=67b14081&is=67afef01&hm=3c4f0969c98b46db039b71c1b6300ded4d0454cf031d184579a1b7b93a91633b&=&format=webp&quality=lossless&width=1193&height=671",
            8: "https://media.discordapp.net/attachments/1187595037937250315/1340133955445194792/8.png?ex=67b14081&is=67afef01&hm=2612ddb8543488e2ac0428f36b2b1dcb8ec3083efba9fead52bf4b77afb09c83&=&format=webp&quality=lossless&width=1193&height=671",
            9: "https://media.discordapp.net/attachments/1187595037937250315/1340133956137521274/9.png?ex=67b14081&is=67afef01&hm=af00dc90c80787c5838bddf6cb9ee4634ca60d5f3b0d6c1b44d3a0dd720c0a45&=&format=webp&quality=lossless&width=1193&height=671",
            10: "https://media.discordapp.net/attachments/1187595037937250315/1340133956854612070/10.png?ex=67b14081&is=67afef01&hm=068d688377e61e04a1ed855f89bad12bf7b9fdb59998bcc588dd29a66533e8e2&=&format=webp&quality=lossless&width=1193&height=671",
            11: "https://media.discordapp.net/attachments/1187595037937250315/1340134022960910418/11.png?ex=67b14091&is=67afef11&hm=f4b0c783851ca9e49a3e3d76949bcb4015700f2f2bb5c448626ef6dd2408418c&=&format=webp&quality=lossless&width=1193&height=671",
            12: "https://media.discordapp.net/attachments/1187595037937250315/1340134023565148211/12.png?ex=67b14091&is=67afef11&hm=354e238f104df83ffb30e79b6d4fc9a87c4e55101621bb3989831b345bac902e&=&format=webp&quality=lossless&width=1193&height=671",
            13: "https://media.discordapp.net/attachments/1187595037937250315/1340134024332709938/13.png?ex=67b14091&is=67afef11&hm=89b1d87b63df4a3a95b784bbd73051c3de7d79e74b2d6b5cfb98f4e8a6d35521&=&format=webp&quality=lossless&width=1193&height=671",
            14: "https://media.discordapp.net/attachments/1187595037937250315/1340134025045479484/14.png?ex=67b14092&is=67afef12&hm=99775faf17b6e2be4be042d33e0e078fd635b11dcb5e200b25266cfe966d6e6d&=&format=webp&quality=lossless&width=1193&height=671",
            15: "https://media.discordapp.net/attachments/1187595037937250315/1340134025846849646/15.png?ex=67b14092&is=67afef12&hm=93194b6a93abcc4839fec7c1fe5c8ce5465e7e53646f3f9928082ee9e15f1f9f&=&format=webp&quality=lossless&width=1193&height=671",
            16: "https://media.discordapp.net/attachments/1187595037937250315/1340134026509553764/16.png?ex=67b14092&is=67afef12&hm=42b39efef5b694130b7afe5a848695ef1e5c38c063a31cc24bbb0b3b27034a3a&=&format=webp&quality=lossless&width=1193&height=671",
            17: "https://media.discordapp.net/attachments/1187595037937250315/1340134027171991695/17.png?ex=67b14092&is=67afef12&hm=b1d989c5c38162cee3dfc681b4f2d396701d034ec991c2efe5d9d50a7f5c79d4&=&format=webp&quality=lossless&width=1193&height=671",
            18: "https://media.discordapp.net/attachments/1187595037937250315/1340134027889213532/18.png?ex=67b14092&is=67afef12&hm=fad8b4601af42d7537e0a8ad003c63b2fbfd741bbbea70225eb6b65b8fe8a4dd&=&format=webp&quality=lossless&width=1193&height=671",
            19: "https://media.discordapp.net/attachments/1187595037937250315/1340134028715757610/19.png?ex=67b14092&is=67afef12&hm=4b2996f4ed3da5052c69c14b4409e65d70b20b47b0a923875ec13a10be7fd416&=&format=webp&quality=lossless&width=1193&height=671",
            20: "https://media.discordapp.net/attachments/1187595037937250315/1340134064493039738/20.png?ex=67b1409b&is=67afef1b&hm=22d41849964f5f7aa8ed20215c1410b32c5ae39c38882595ad5f0e431cb36e97&=&format=webp&quality=lossless&width=1193&height=671",
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
                name=f"Nordschleife Tourist",
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
    await bot.add_cog(cog)
