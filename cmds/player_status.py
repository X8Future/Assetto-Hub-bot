import discord
from discord.ext import commands, tasks
import aiohttp

class ForumUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.forum_channel_id =   # Replace with your actual channel ID
        self.api_url = ""  # API to get player count from your server Ex: http://serverIP:Port/INFO
        self.image_links = { # add links to a cdn of images you want to use, each number represents a 1 more person in a server and can be expanded on up to how ever many you want, currently @ 20
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

        # If no matching message found, it will create a new one
        print("No matching messages found. Creating a new one.")
        await self.create_new_post(image_url)

    async def create_new_post(self, image_url):
        """Create a new post if no previous messages were found."""
        channel = await self.bot.fetch_channel(self.forum_channel_id)

        try:
            # Create a new thread (forum post)
            thread = await channel.create_thread(
                name=f"", # replace with the name of the server
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
