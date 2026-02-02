from datetime import datetime, timedelta, timezone

import discord
from dateutil.relativedelta import relativedelta
from discord import app_commands, Interaction
from discord.ext import commands

from cogs import is_member_or_above_appcmd
from db.voice_sessions import (
    aggregate_month,
    aggregate_month_week,
    aggregate_range,
    cleanup_old_months,
)
from utils.logging_utils import log_bot
from utils.time_utils import to_kst


def format_duration(seconds: int) -> str:
    units = [
        ("년", 60 * 60 * 24 * 365),
        ("일", 60 * 60 * 24),
        ("시간", 60 * 60),
        ("분", 60),
        ("초", 1),
    ]
    parts = []
    for name, unit_seconds in units:
        value, seconds = divmod(seconds, unit_seconds)
        if value > 0 or (name == "초" and not parts):
            parts.append(f"{value}{name}")
    return " ".join(parts)


def week_of_month(year: int, month: int, day: int) -> int:
    first_day = datetime(year, month, 1)
    first_weekday = first_day.weekday()  # Monday=0
    return ((day + first_weekday - 1) // 7) + 1


def week_range_in_month(year: int, month: int, week: int):
    first_day = datetime(year, month, 1)
    first_weekday = first_day.weekday()  # Monday=0
    start_day = (week - 1) * 7 - first_weekday + 1
    end_day = start_day + 6

    # clamp to month boundaries
    last_day = (first_day + relativedelta(months=1) - timedelta(days=1)).day
    start_day = max(1, start_day)
    end_day = min(last_day, end_day)
    return start_day, end_day


def render_leaderboard(title: str, results, guild, header_line: str | None = None) -> discord.Embed:
    embed = discord.Embed(title=title, color=discord.Color.purple())
    if not results:
        if header_line:
            embed.description = f"{header_line}\n\n❌ 기록이 없습니다."
        else:
            embed.description = "❌ 기록이 없습니다."
        return embed

    lines = []
    if header_line:
        lines.append(header_line)
        lines.append("")
    for idx, row in enumerate(results, start=1):
        user_id = row.get("_id")
        username = row.get("username", "unknown")
        total_seconds = int(row.get("total_seconds", 0))
        member = guild.get_member(int(user_id)) if guild else None
        display_name = member.display_name if member else username
        lines.append(f"{idx}. **{display_name}** — {format_duration(total_seconds)}")

    embed.description = "\n".join(lines)
    return embed


def render_future_notice(title: str, header_line: str | None = None) -> discord.Embed:
    embed = discord.Embed(title=title, color=discord.Color.purple())
    lines = []
    if header_line:
        lines.append(header_line)
        lines.append("")
    lines.append("저에게 타임 스톤을 주신다면.. 미래를 봐드리지요..")
    embed.description = "\n".join(lines)
    return embed


class VoiceLeaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _cleanup(self):
        now_kst = to_kst(datetime.now(timezone.utc))
        log_id = log_bot("DB Writing", "cleanup old voice sessions")
        await cleanup_old_months(now_kst, keep_months=4, log_id=log_id)

    @app_commands.command(name="주간-음성-리더보드-오늘", description="오늘 기준 최근 7일간 음성채널 상주 시간 Top 10 멤버")
    @is_member_or_above_appcmd()
    async def weekly_leaderboard_today(self, interaction: Interaction):
        await interaction.response.defer(thinking=True)
        await self._cleanup()

        now_kst = to_kst(datetime.now(timezone.utc))
        start_date = (now_kst.date() - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = now_kst.date().strftime("%Y-%m-%d")

        log_id = log_bot("DB Reading", f"weekly leaderboard {start_date}~{end_date}")
        results = await aggregate_range(start_date, end_date, limit=10, log_id=log_id)
        title = "📅 음성 리더보드 (오늘 기준)"
        current_week = week_of_month(now_kst.year, now_kst.month, now_kst.day)
        header_line = f"이번 주차: {now_kst.year}년 {now_kst.month}월 {current_week}주차"
        embed = render_leaderboard(title, results, interaction.guild, header_line=header_line)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="월간-음성-리더보드-오늘", description="오늘 기준 최근 1개월 음성채널 상주 시간 Top 10 멤버")
    @is_member_or_above_appcmd()
    async def monthly_leaderboard_today(self, interaction: Interaction):
        await interaction.response.defer(thinking=True)
        await self._cleanup()

        now_kst = to_kst(datetime.now(timezone.utc))
        start_date = (now_kst.date() - relativedelta(months=1)).strftime("%Y-%m-%d")
        end_date = now_kst.date().strftime("%Y-%m-%d")

        log_id = log_bot("DB Reading", f"monthly leaderboard {start_date}~{end_date}")
        results = await aggregate_range(start_date, end_date, limit=10, log_id=log_id)
        title = "🗓️ 월간 음성 리더보드 (오늘 기준)"
        current_week = week_of_month(now_kst.year, now_kst.month, now_kst.day)
        header_line = f"이번 주차: {now_kst.year}년 {now_kst.month}월 {current_week}주차"
        embed = render_leaderboard(title, results, interaction.guild, header_line=header_line)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="주차별-음성-리더보드", description="최근 3개월 중 특정 주차의 음성채널 상주 시간 Top 10 멤버")
    @is_member_or_above_appcmd()
    async def week_leaderboard(self, interaction: Interaction, week: int):
        await interaction.response.defer(thinking=True)
        await self._cleanup()

        now_kst = to_kst(datetime.now(timezone.utc))
        year = now_kst.year
        month = now_kst.month
        current_week = week_of_month(year, month, now_kst.day)
        if week > current_week:
            title = f"📆 {year}년 {month}월 {week}주차 음성 리더보드"
            header_line = f"이번 주차: {year}년 {month}월 {current_week}주차"
            embed = render_future_notice(title, header_line=header_line)
            await interaction.followup.send(embed=embed)
            return

        log_id = log_bot("DB Reading", f"week leaderboard {year}-{month} W{week}")
        results = await aggregate_month_week(year, month, week, limit=10, log_id=log_id)
        start_day, end_day = week_range_in_month(year, month, week)
        title = f"📆 {year}년 {month}월 {week}주차 음성 리더보드 ({start_day}일~{end_day}일)"
        header_line = f"이번 주차: {year}년 {month}월 {current_week}주차"
        embed = render_leaderboard(title, results, interaction.guild, header_line=header_line)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="월별-음성-리더보드", description="최근 3개월 중 특정 월의 음성채널 상주 시간 Top 10 멤버")
    @is_member_or_above_appcmd()
    async def month_leaderboard(self, interaction: Interaction, month: int):
        await interaction.response.defer(thinking=True)
        await self._cleanup()

        now_kst = to_kst(datetime.now(timezone.utc))
        year = now_kst.year
        if month > now_kst.month:
            title = f"🗓️ {year}년 {month}월 음성 리더보드"
            current_week = week_of_month(now_kst.year, now_kst.month, now_kst.day)
            header_line = f"이번 주차: {year}년 {now_kst.month}월 {current_week}주차"
            embed = render_future_notice(title, header_line=header_line)
            await interaction.followup.send(embed=embed)
            return

        log_id = log_bot("DB Reading", f"month leaderboard {year}-{month}")
        results = await aggregate_month(year, month, limit=10, log_id=log_id)
        title = f"🗓️ {year}년 {month}월 음성 리더보드"
        current_week = week_of_month(now_kst.year, now_kst.month, now_kst.day)
        header_line = f"이번 주차: {now_kst.year}년 {now_kst.month}월 {current_week}주차"
        embed = render_leaderboard(title, results, interaction.guild, header_line=header_line)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(VoiceLeaderboard(bot))
    log_bot("Load Complete", "VoiceLeaderboard Cog loaded")
