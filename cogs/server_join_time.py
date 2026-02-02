from discord.ext import commands
from discord import Member
from db.mongo import save_join_time
from utils.logging_utils import log_bot

class ServerJoinTime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        log_id = log_bot("DB Writing", f"save join time: {member.name}")
        await save_join_time(str(member.id), member.name, log_id=log_id)

async def setup(bot):
    await bot.add_cog(ServerJoinTime(bot))
    log_bot("Load Complete", "ServerJoinTime Cog loaded")
