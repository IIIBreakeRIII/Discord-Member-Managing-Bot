from discord.ext import commands
from discord import RawReactionActionEvent, Member, Interaction, app_commands
from db.mongo import save_granted_role
from cogs import is_master_or_organizer_appcmd
import discord
import json
import os

CONFIG_FILE = "config.json"

MEMBER_ROLE_NAME = os.getenv("MEMBER_ROLE_NAME")
GUEST_ROLE_NAME = os.getenv("GUEST_ROLE_NAME")


def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def update_config(key: str, value: str):
    config = load_config()
    config[key] = value
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


class GrantAuthority(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        print(f"[DEBUG] ✅ reaction detected — message_id: {payload.message_id}, emoji: {payload.emoji.name}")
        if payload.emoji.name != "✅":
            print("❌ 이모지가 ✅ 아님 — 무시")
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member: Member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        # 메시지 ID 로드
        config = load_config()
        try:
            member_msg_id = int(config.get("MEMBER_NOTICE_MESSAGE_ID", 0))
            guest_msg_id = int(config.get("GUEST_NOTICE_MESSAGE_ID", 0))
        except ValueError:
            print("❌ config.json 메시지 ID가 숫자가 아님")
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
                print(f"[DEBUG] ✅ 역할 '{role_name}' 부여 완료")

                embed = discord.Embed(
                    title="💛Watchers💛 합류하신 것을 축하드려요!",
                    description=f"환영해요, `{member.display_name}` 님!\n`{role_name}` 역할이 부여되었어요!\n앞으로 열심히 활동해주세요!",
                    color=discord.Color.green()
                )
                try:
                    await member.send(embed=embed)
                    print("[DEBUG] 📩 DM 전송 성공")
                except discord.Forbidden:
                    print("[DEBUG] 📪 DM 전송 실패 (사용자 설정 또는 차단)")

                await save_granted_role(str(member.id), member.name, role_name)
                print("[DEBUG] 📝 DB 저장 완료")

            except discord.Forbidden:
                print(f"[ERROR] ❌ 봇 권한 부족으로 역할 부여 실패: '{role_name}'")
            except Exception as e:
                print(f"[ERROR] ❌ 예기치 않은 오류 발생: {e}")
        else:
            print(f"❌ 역할 '{role_name}' 을(를) 찾을 수 없습니다.")

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
    print("🔐 GrantAuthority Cog loaded")
