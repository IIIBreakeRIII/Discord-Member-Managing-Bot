from discord.ext import commands
from discord import app_commands

# Master, Organizer만 사용할 수 있는 명령어를 만들어주는 Decorator

def is_master_or_organizer():
    async def predicate(ctx):
        allowed_roles = {"Master", "Organizer"}
        user_roles = {role.name for role in getattr(ctx.author, "roles", [])}
        return bool(allowed_roles & user_roles) or ctx.author.guild_permissions.administrator
    return commands.check(predicate)

def is_master_or_organizer_appcmd():
    async def predicate(interaction):
        allowed_roles = {"Master", "Organizer"}
        user_roles = {role.name for role in getattr(interaction.user, "roles", [])}
        return bool(allowed_roles & user_roles) or interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

# Member 이상 사용 가능 (Master/Organizer 포함)
def is_member_or_above_appcmd():
    async def predicate(interaction):
        allowed_roles = {"Master", "Organizer", "Member"}
        user_roles = {role.name for role in getattr(interaction.user, "roles", [])}
        return bool(allowed_roles & user_roles) or interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)
