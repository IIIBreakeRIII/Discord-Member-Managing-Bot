from discord.ext import commands
from discord import Member
from db.mongo import save_join_time

class ServerJoinTime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        print(f"🚪 유저 서버 입장 감지됨: {member.name} ({member.id})")
        await save_join_time(str(member.id), member.name)

async def setup(bot):
    await bot.add_cog(ServerJoinTime(bot))
    print("📝[Background Cog] ServerJoinTime Cog loaded")
