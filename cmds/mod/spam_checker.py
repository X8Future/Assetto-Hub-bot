import discord
from discord.ext import commands
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

SPAM_TIME_WINDOW = 5 
SPAM_MESSAGE_THRESHOLD = 3
TIMEOUT_DURATION = 86400 # How long they are timed out for in minutes
IMMUNE_ROLE_IDS = {1251377219910242365, 1176727481634541614} # Allowed role ID that can bypass the spam checker
DELETE_DELAY = 0.5

class AntiSpamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_messages = defaultdict(list)

    def parse_duration(self, seconds: int) -> timedelta:
        return timedelta(seconds=seconds)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if any(role.id in IMMUNE_ROLE_IDS for role in message.author.roles):
            return

        now = datetime.utcnow()
        user_id = message.author.id
        content = message.content or ""
        if message.attachments:
            content += " " + " ".join(att.url for att in message.attachments)

        self.user_messages[user_id].append((content, now, message))
        self.user_messages[user_id] = [
            (c, ts, msg_obj)
            for c, ts, msg_obj in self.user_messages[user_id]
            if (now - ts).total_seconds() <= SPAM_TIME_WINDOW
        ]

        content_groups = defaultdict(list)
        for c, ts, msg_obj in self.user_messages[user_id]:
            content_groups[c].append(msg_obj)

        for content_text, msgs in content_groups.items():
            if len(msgs) >= SPAM_MESSAGE_THRESHOLD:
                for msg in msgs:
                    if msg:
                        try:
                            await msg.delete()
                        except discord.HTTPException:
                            pass
                        await asyncio.sleep(DELETE_DELAY)

                self.user_messages[user_id] = [
                    (c, ts, m) for c, ts, m in self.user_messages[user_id] if c != content_text
                ]

                member = message.guild.get_member(user_id)
                if member:
                    try:
                        await member.timeout(self.parse_duration(TIMEOUT_DURATION), reason="Spamming repeated content")
                    except Exception:
                        pass

async def setup(bot):
    await bot.add_cog(AntiSpamCog(bot))

