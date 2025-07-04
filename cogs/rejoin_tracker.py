from discord.ext import commands
from db.quit_db import move_user_to_quitlogs, quitlogs
from db.mongo import format_korean_datetime_string
import discord

CHANNEL_ID = 1378740342953742417  # 메시지 보낼 채널 ID
ROLE_MASTER = "<@&1376452625972727808>"
ROLE_ORGANIZER = "<@&1205565991162089553>"

class RejoinTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # quitlogs에서 해당 유저의 기록 조회
        doc = await quitlogs.find_one({"user_id": str(member.id)})
        if doc:
            channel = member.guild.get_channel(CHANNEL_ID)
            if channel:
                joined_at = doc.get("joined_at_server", "알 수 없음")
                quit_time = doc.get("quit_time", "알 수 없음")
                times = doc.get("times", 1)
                # 날짜 포맷 변환
                if joined_at != "알 수 없음":
                    joined_at = format_korean_datetime_string(joined_at)
                if quit_time != "알 수 없음":
                    quit_time = format_korean_datetime_string(quit_time)
                await channel.send(
                    f"{ROLE_MASTER} {ROLE_ORGANIZER}\n"
                    f"**{member.mention}** 님은 이전에 `{joined_at}`에 서버에 입장했고, "
                    f"`{quit_time}`에 퇴장한 기록이 있습니다.\n"
                    f"총 {times}번 나갔습니다."
                )

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await move_user_to_quitlogs(str(member.id))

async def setup(bot):
    await bot.add_cog(RejoinTracker(bot))
    print("🔐[Background Cog] RejoinTracker Cog loaded")