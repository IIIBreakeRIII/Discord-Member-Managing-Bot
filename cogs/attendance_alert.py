from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db.mongo import collection
from utils.time_utils import to_kst, KST_DISPLAY_FORMAT
from settings import ALERT_CHANNEL_ID, ROLE_MASTER_MENTION, ROLE_ORGANIZER_MENTION
from datetime import datetime, timezone
from apscheduler.triggers.cron import CronTrigger

import discord
from utils.logging_utils import log_bot

# Refactor: constants moved to settings; values unchanged

class AttendanceAlert(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(
            self.check_attendance,
            trigger=CronTrigger(hour=12, minute=0, timezone='Asia/Seoul')
        )
        self.scheduler.start()

    async def check_attendance(self):
        # 현재 시각을 KST datetime으로 생성
        now_kst = to_kst(datetime.now(timezone.utc))
        log_bot("Attendance", f"Check started: {now_kst.isoformat()}")
        async for user in collection.find({}):
            user_id = user.get("user_id")
            username = user.get("username", "알 수 없음")
            last_active_str = user.get("last_active")
            if not last_active_str:
                joined_at = user.get("joined_at_server", None)
                if not joined_at:
                    continue  # 입장 시간도 없으면 스킵
                try:
                    joined_at_kst = to_kst(joined_at)
                except Exception:
                    continue
                days_inactive = (now_kst - joined_at_kst).days
                if days_inactive == 14 or days_inactive == 30:
                    guilds = self.bot.guilds
                    for guild in guilds:
                        member = guild.get_member(int(user_id))
                        if member:
                            channel = guild.get_channel(ALERT_CHANNEL_ID)
                            if channel:
                                joined_at_kor = to_kst(joined_at).strftime(KST_DISPLAY_FORMAT)
                                embed = discord.Embed(
                                    title="⚠️ 접속 기록 없음 안내",
                                    description=(
                                        f"{ROLE_MASTER_MENTION} {ROLE_ORGANIZER_MENTION}\n"
                                        f"**{member.mention}** 님은 접속 기록이 아직 없습니다!\n"
                                        f"서버 입장 시간은 `{joined_at_kor}` 입니다.\n"
                                        f"{days_inactive}일 동안 접속 기록이 없습니다!"
                                    ),
                                    color=discord.Color.red()
                                )
                                await channel.send(embed=embed)
                continue
            try:
                last_active_kst = to_kst(last_active_str)
            except Exception:
                continue
            seconds_inactive = (now_kst - last_active_kst).total_seconds()
            days_inactive = (now_kst - last_active_kst).days
            if days_inactive == 14 or days_inactive == 30:
                guilds = self.bot.guilds
                for guild in guilds:
                    member = guild.get_member(int(user_id))
                    if member:
                        channel = guild.get_channel(ALERT_CHANNEL_ID)
                        if channel:
                            last_active_kor = to_kst(last_active_str).strftime(KST_DISPLAY_FORMAT)
                            embed = discord.Embed(
                                title="⚠️ 장기 미접속 안내",
                                description=(
                                    f"{ROLE_MASTER_MENTION} {ROLE_ORGANIZER_MENTION}\n"
                                    f"**{member.mention}** 님은 마지막 접속일이 `{last_active_kor}` 입니다.\n"
                                    f"{days_inactive}일 동안 접속하지 않았습니다!"
                                ),
                                color=discord.Color.red()
                            )
                            await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AttendanceAlert(bot))
    log_bot("Load Complete", "AttendanceAlert Cog loaded")
