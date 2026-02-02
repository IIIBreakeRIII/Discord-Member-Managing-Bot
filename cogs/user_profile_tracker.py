from discord.ext import commands
from discord import app_commands, Interaction, Member
import discord
from db.mongo import get_user_profile
from utils.time_utils import to_kst, KST_DISPLAY_FORMAT
from cogs import is_master_or_organizer_appcmd
from utils.logging_utils import log_bot

# Refactor: unified KST parsing/formatting; behavior unchanged


def format_duration(seconds_input) -> str:
    try:
        if isinstance(seconds_input, list):
            seconds = int(sum(seconds_input))
        else:
            seconds = int(seconds_input)
    except Exception:
        return "❌ 시간 정보 없음"

    if seconds <= 0:
        return "0초"

    years, seconds = divmod(seconds, 60 * 60 * 24 * 365)
    days, seconds = divmod(seconds, 60 * 60 * 24)
    hours, seconds = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if years > 0:
        parts.append(f"{years}년")
    if days > 0:
        parts.append(f"{days}일")
    if hours > 0:
        parts.append(f"{hours}시간")
    if minutes > 0:
        parts.append(f"{minutes}분")
    if seconds > 0:
        parts.append(f"{seconds}초")

    return " ".join(parts)


class UserProfileTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="유저-정보", description="해당 유저의 정보를 데이터베이스에서 조회합니다.")
    @is_master_or_organizer_appcmd()
    async def user_profile(self, interaction: Interaction, user: Member):
        await interaction.response.defer()

        user_id = str(user.id)
        log_id = log_bot("DB Reading", f"get user profile: {user.display_name}")
        profile = await get_user_profile(user_id, log_id=log_id)

        if not profile:
            await interaction.followup.send(f"❌ `{user.display_name}` 님의 정보를 찾을 수 없습니다.", ephemeral=True)
            return

        # 필드 파싱
        server_nickname = profile.get("server_nickname", "❌ 없음")
        username = profile.get("username", "❌ 없음")
        user_id_str = profile.get("user_id", "❌ 없음")
        granted_role = profile.get("granted_role", [])
        if isinstance(granted_role, list):
            granted_role = granted_role[0] if granted_role else "❌ 없음"

        joined = profile.get("joined_at_server", "")
        joined_kst = to_kst(joined).strftime(KST_DISPLAY_FORMAT)

        last_active = profile.get("last_active", "")
        last_active_kst = to_kst(last_active).strftime(KST_DISPLAY_FORMAT)

        durations_raw = profile.get("durations", 0)

        if isinstance(durations_raw, dict):
            durations_value = durations_raw.get("total_seconds", 0)
        elif isinstance(durations_raw, list):
            durations_value = sum(durations_raw)
        else:
            try:
                durations_value = int(durations_raw)
            except Exception:
                durations_value = 0

        total_duration = format_duration(durations_value)


        embed = discord.Embed(
            title=f"🧾 {user.display_name} 님의 유저 정보",
            color=discord.Color.blue()
        )
        embed.add_field(name="📛 서버 닉네임", value=f"**{server_nickname}**", inline=False)
        embed.add_field(name="👤 유저명(Discord ID)", value=f"`{username}`", inline=False)
        embed.add_field(name="🆔 유저 ID", value=f"`{user_id_str}`", inline=False)
        embed.add_field(name="🎭 역할", value=f"**{granted_role}**", inline=False)
        embed.add_field(name="📥 서버 입장", value=f"`{joined_kst}`", inline=False)
        embed.add_field(name="🕓 마지막 활동", value=f"`{last_active_kst}`", inline=False)
        embed.add_field(name="🕒 음성 채널 누적 시간", value=f"**{total_duration}**", inline=False)

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(UserProfileTracker(bot))
    log_bot("Load Complete", "UserProfileTracker Cog loaded")
