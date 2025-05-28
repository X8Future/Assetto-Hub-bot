import discord
from discord.ext import commands, tasks
import aiohttp

class ForumUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.forum_channel_id = 1268666206810931210  # Replace with your actual channel ID
        self.api_url = [
            "http://65.108.249.168:8080/INFO",
            "http://65.108.249.168:8081/INFO"
        ]
        self.image_links = {
            0: "https://media.discordapp.net/attachments/1187595037937250315/1340166035956957184/0.png?ex=67b15e62&is=67b00ce2&hm=dd826781fe651dfe956bb31c8e6046a71b77b6a646df7147b6fa4ffb7907de3a&=&format=webp&quality=lossless&width=1193&height=671",
            1: "https://media.discordapp.net/attachments/1187595037937250315/1340166036711800852/1.png?ex=67b15e62&is=67b00ce2&hm=93d58999d62dc06d105350dcad95c14e34876d8d1546bf3e8127e7d476c52302&=&format=webp&quality=lossless&width=1193&height=671",
            2: "https://media.discordapp.net/attachments/1187595037937250315/1340166037378961481/2.png?ex=67b15e62&is=67b00ce2&hm=5bce75b3823490ec58cc260021909f7533565d1d05af1e3677275c5c5b99a858&=&format=webp&quality=lossless&width=1193&height=671",
            3: "https://media.discordapp.net/attachments/1187595037937250315/1340166038062501959/3.png?ex=67b15e62&is=67b00ce2&hm=4094a4dd884f1061e95beca4113b51fc551988523d334fc32d2483a5539207b9&=&format=webp&quality=lossless&width=1193&height=671",
            4: "https://media.discordapp.net/attachments/1187595037937250315/1340166038804762624/4.png?ex=67b15e62&is=67b00ce2&hm=a5329f61729bca2d910584522c9e87e45ed1597950a48367042c77e1cbb5ac9b&=&format=webp&quality=lossless&width=1193&height=671",
            5: "https://media.discordapp.net/attachments/1187595037937250315/1340166039467458690/5.png?ex=67b15e62&is=67b00ce2&hm=e864ba6e9abc510bddae7e943b9daf54d1899a07b660a01aaba3d9ad81a1a8c8&=&format=webp&quality=lossless&width=1193&height=671",
            6: "https://media.discordapp.net/attachments/1187595037937250315/1340166040168169633/6.png?ex=67b15e63&is=67b00ce3&hm=1e34999557716b936811900dc2249b1943f4057ac8f73e9ac53efc7e9ebf7ed9&=&format=webp&quality=lossless&width=1193&height=671",
            7: "https://media.discordapp.net/attachments/1187595037937250315/1340166040859967521/7.png?ex=67b15e63&is=67b00ce3&hm=208dfd2ed0d9e62d9ff9264950f31545f3aa6970e5b09b061e5b5c827fd065dd&=&format=webp&quality=lossless&width=1193&height=671",
            8: "https://media.discordapp.net/attachments/1187595037937250315/1340166041611014235/8.png?ex=67b15e63&is=67b00ce3&hm=cde50438683e7c2c6e6032ca6eef302db38e3b2c9062c572aded437167dfc7f7&=&format=webp&quality=lossless&width=1193&height=671",
            9: "https://media.discordapp.net/attachments/1187595037937250315/1340166035185074268/9.png?ex=67b15e61&is=67b00ce1&hm=5c2fdb721d9fc744f1d9a52a361a204a5c937c9ebfa45dad7dda568ed239153d&=&format=webp&quality=lossless&width=1193&height=671",
            10: "https://media.discordapp.net/attachments/1187595037937250315/1340166059248058408/14.png?ex=67b15e67&is=67b00ce7&hm=f21d1a6759ba2407dab73605c5b056181e14fe03a0a9fed254b131a2e4b6bc40&=&format=webp&quality=lossless&width=1193&height=671",
            11: "https://media.discordapp.net/attachments/1187595037937250315/1340166060011159572/10.png?ex=67b15e67&is=67b00ce7&hm=46ae5f05207993a235433408577d3364f0925f355bf690b21e1a0bc7814d1744&=&format=webp&quality=lossless&width=1193&height=671",
            12: "https://media.discordapp.net/attachments/1187595037937250315/1340166060715806791/11.png?ex=67b15e67&is=67b00ce7&hm=b1300d61552ae6ebe4c54c5af40a04752c452bba59886075d258d4508a1bb65c&=&format=webp&quality=lossless&width=1193&height=671",
            13: "https://media.discordapp.net/attachments/1187595037937250315/1340166061437222962/12.png?ex=67b15e68&is=67b00ce8&hm=77c52deb551cb4d9e10a8ef8f1e2abe00a228fa6bfa6ab10fc3efcef4d2a6ad8&=&format=webp&quality=lossless&width=1193&height=671",
            14: "https://media.discordapp.net/attachments/1187595037937250315/1340166062158905344/13.png?ex=67b15e68&is=67b00ce8&hm=0cafd4fe45c68ffdbad0ef06c630637c57548478eb90fe338cb8069adc07f42f&=&format=webp&quality=lossless&width=1193&height=671",
            15: "https://media.discordapp.net/attachments/1187595037937250315/1340166063022805022/19.png?ex=67b15e68&is=67b00ce8&hm=f44cd8ba0e6b9bbaa4fb3f6febbf2fc7a7231585521668cc45ebf3e8ca9b9ad8&=&format=webp&quality=lossless&width=1193&height=671",
            16: "https://media.discordapp.net/attachments/1187595037937250315/1340166063781838900/15.png?ex=67b15e68&is=67b00ce8&hm=1ef8d615826c1789f74c12d76e93cc831780dd02e4a4e3d625b00707eaf070dd&=&format=webp&quality=lossless&width=1193&height=671",
            17: "https://media.discordapp.net/attachments/1187595037937250315/1340166064734212106/16.png?ex=67b15e68&is=67b00ce8&hm=afba471b6e4d58d47dcfb56a55f57be3bc402d313dfd0cbba0bb84aad6e75b00&=&format=webp&quality=lossless&width=1193&height=671",
            18: "https://media.discordapp.net/attachments/1187595037937250315/1340166065451171933/17.png?ex=67b15e69&is=67b00ce9&hm=6bc8e74a50d6c1319b43493ed0634191659149cf3480cb145a9f75b4f03b034c&=&format=webp&quality=lossless&width=1193&height=671",
            19: "https://media.discordapp.net/attachments/1187595037937250315/1340166066306813993/18.png?ex=67b15e69&is=67b00ce9&hm=34e51358a7232242a368e8c7331408972a8d7bcc47642faf551cd7db35c96413&=&format=webp&quality=lossless&width=1193&height=671",
            20: "https://media.discordapp.net/attachments/1187595037937250315/1340166067770888343/20.png?ex=67b15e69&is=67b00ce9&hm=e2980fde16a2e4b5d74176b295b4b1ebc2538b453f358bbc85eabdcc18345fc2&=&format=webp&quality=lossless&width=1193&height=671"
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
            for url in self.api_url:
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
                name=f"EU SRP Public",
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
        await bot.load_extension("cmds.eu_status")
