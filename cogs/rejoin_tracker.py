from discord.ext import commands
from db.quit_db import move_user_to_quitlogs, quitlogs
from utils.time_utils import to_kst, KST_DISPLAY_FORMAT
from settings import ALERT_CHANNEL_ID, ROLE_MASTER_MENTION, ROLE_ORGANIZER_MENTION
from utils.logging_utils import log_bot

# Refactor: constants moved to settings; values unchanged

class RejoinTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # quitlogs에서 해당 유저의 기록 조회
        doc = await quitlogs.find_one({"user_id": str(member.id)})
        if doc:
            channel = member.guild.get_channel(ALERT_CHANNEL_ID)
            if channel:
                joined_at = doc.get("joined_at_server", "알 수 없음")
                quit_time = doc.get("quit_time", "알 수 없음")
                times = doc.get("times", 1)
                # 날짜 포맷 변환
                if joined_at != "알 수 없음":
                    joined_at = to_kst(joined_at).strftime(KST_DISPLAY_FORMAT)
                if quit_time != "알 수 없음":
                    quit_time = to_kst(quit_time).strftime(KST_DISPLAY_FORMAT)
                await channel.send(
                    f"{ROLE_MASTER_MENTION} {ROLE_ORGANIZER_MENTION}\n"
                    f"**{member.mention}** 님은 이전에 `{joined_at}`에 서버에 입장했고, "
                    f"`{quit_time}`에 퇴장한 기록이 있습니다.\n"
                    f"총 {times}번 나갔습니다."
                )

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        log_id = log_bot("DB Writing", f"move user to quitlogs: {member.name}")
        await move_user_to_quitlogs(str(member.id), log_id=log_id)

async def setup(bot):
    await bot.add_cog(RejoinTracker(bot))
    log_bot("Load Complete", "RejoinTracker Cog loaded")
