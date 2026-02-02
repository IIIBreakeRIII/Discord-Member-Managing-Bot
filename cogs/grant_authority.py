from discord.ext import commands
from discord import RawReactionActionEvent, Member, Interaction, app_commands
from db.mongo import save_granted_role
from cogs import is_master_or_organizer_appcmd
from settings import load_config, update_config, MEMBER_ROLE_NAME, GUEST_ROLE_NAME
import discord
from utils.logging_utils import log_bot


class GrantAuthority(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        log_bot("GrantAuthority", f"Reaction detected — message_id: {payload.message_id}, emoji: {payload.emoji.name}")
        if payload.emoji.name != "✅":
            log_bot("GrantAuthority", "Emoji is not target — ignored")
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member: Member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        # 메시지 ID 로드
        # Refactor: config load centralized; behavior unchanged
        config = load_config()
        try:
            member_msg_id = int(config.get("MEMBER_NOTICE_MESSAGE_ID", 0))
            guest_msg_id = int(config.get("GUEST_NOTICE_MESSAGE_ID", 0))
        except ValueError:
            log_bot("Error", "config.json message ID is not numeric")
            return

        # 메시지 ID에 따라 역할 결정
        role_name = None
        if payload.message_id == member_msg_id:
            role_name = MEMBER_ROLE_NAME
        elif payload.message_id == guest_msg_id:
            role_name = GUEST_ROLE_NAME
        else:
            return  # 대상 메시지가 아니면 무시

        if discord.utils.get(member.roles, name=role_name):
            return

        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            try:
                await member.add_roles(role)
                log_bot("GrantAuthority", f"Role '{role_name}' granted")

                embed = discord.Embed(
                    title="💛Watchers💛 합류하신 것을 축하드려요!",
                    description=f"환영해요, `{member.display_name}` 님!\n`{role_name}` 역할이 부여되었어요!\n앞으로 열심히 활동해주세요!",
                    color=discord.Color.green()
                )
                try:
                    await member.send(embed=embed)
                    log_bot("GrantAuthority", "DM sent")
                except discord.Forbidden:
                    log_bot("GrantAuthority", "DM failed (user settings or blocked)")

                log_id = log_bot("DB Writing", f"save granted role: {member.name}")
                await save_granted_role(str(member.id), member.name, role_name, log_id=log_id)
                log_bot("GrantAuthority", "DB saved")

            except discord.Forbidden:
                log_bot("Error", f"Missing permissions to grant role: '{role_name}'")
            except Exception as e:
                log_bot("Error", f"Unexpected error: {e}")
        else:
            log_bot("Error", f"Role not found: '{role_name}'")

    @app_commands.command(name="멤버-공지메시지id-설정", description="멤버 공지 메시지 ID를 설정합니다.")
    @is_master_or_organizer_appcmd()
    async def update_member_message_id(self, interaction: Interaction, message_id: str):
        update_config("MEMBER_NOTICE_MESSAGE_ID", message_id)
        embed = discord.Embed(
            title="📌 멤버 공지 메시지 ID 설정 완료",
            description=f"`MEMBER_NOTICE_MESSAGE_ID`가 `{message_id}`로 설정되었습니다.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="게스트-공지메시지id-설정", description="게스트 공지 메시지 ID를 설정합니다.")
    @is_master_or_organizer_appcmd()
    async def update_guest_message_id(self, interaction: Interaction, message_id: str):
        update_config("GUEST_NOTICE_MESSAGE_ID", message_id)
        embed = discord.Embed(
            title="📌 게스트 공지 메시지 ID 설정 완료",
            description=f"`GUEST_NOTICE_MESSAGE_ID`가 `{message_id}`로 설정되었습니다.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(GrantAuthority(bot))
    log_bot("Load Complete", "GrantAuthority Cog loaded")
