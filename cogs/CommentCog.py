from nextcord import Interaction, Member, Role, slash_command, ApplicationError
from nextcord.ext.commands import Bot, Cog, Context
from nextcord.ext.commands import check as prf_check
from nextcord.ext.application_checks import check as app_check
from nextcord.ext.application_checks import guild_only as app_guild_only
from nextcord.ext.commands.errors import MissingAnyRole, CommandError, NoPrivateMessage
from nextcord.ext.application_checks.errors import ApplicationMissingAnyRole
from typing import Union
from .commenthelper import comment_add, comment_edit, comment_list, comment_remove, comment_role_add, comment_role_remove, valid_roles_list
from .CommentDB import get_all_role_ids


def check_user_roles(is_prefix_cmd: bool):
	async def predicate(info_obj: Union[Context, Interaction]):
		member = info_obj.author if isinstance(info_obj, Context) else info_obj.user
		if not isinstance(member, Member):
			raise NoPrivateMessage("This command can not be used in private messages.")
		if member.guild_permissions.manage_guild:
			return True
		guild_id = info_obj.guild.id
		role_ids = await get_all_role_ids(guild_id = guild_id)
		if not role_ids:
			err = "This guild has not permitted any roles to use this commands."
			raise CommandError(err) if isinstance(info_obj, Context) else ApplicationError(err)
		for role_id in role_ids:
			if member.get_role(role_id):
				return True
		raise MissingAnyRole(role_ids) if isinstance(info_obj, Context) else ApplicationMissingAnyRole(role_ids)
	return prf_check(predicate) if is_prefix_cmd else app_check(predicate)


class CommentCog(Cog, name = "User Comments"):
	def __init__(self, bot: Bot):
		self.bot = bot


	@slash_command(name = "comment", dm_permission = False)
	@app_guild_only()
	@check_user_roles(is_prefix_cmd = False)
	async def app_comment(self, interaction: Interaction):
		pass


	@app_comment.subcommand(name = "roles", inherit_hooks = True)
	async def app_comment_roles(self, interaction: Interaction):
		pass


	@app_comment_roles.subcommand(name = "add", description = "Allow a role to use the comment commands.", inherit_hooks = True)
	async def app_comment_roles_add(self, interaction: Interaction, role: Role):
		await comment_role_add(interaction, role)


	@app_comment_roles.subcommand(name = "remove", description = "Remove a role's access to the comment commands.", inherit_hooks = True)
	async def app_comment_roles_remove(self, interaction: Interaction, role: Role):
		await comment_role_remove(interaction, role)


	@app_comment_roles.subcommand(name = "list", description = "Display a list of roles that may use the comment commands.", inherit_hooks = True)
	async def app_comment_roles_list(Self, interaction: Interaction):
		await valid_roles_list(interaction)


	@app_comment.subcommand(name = "list", description = "Display a list of comments about the specified Discord user.", inherit_hooks = True)
	async def app_comment_list(self, interaction: Interaction, user: Member):
		await comment_list(interaction, user)


	@app_comment.subcommand(name = "add", description = "Add a comment about the specified Discord user.", inherit_hooks = True)
	async def app_comment_add(self, interaction: Interaction, user: Member, comment: str):
		await comment_add(interaction, user, comment)


	@app_comment.subcommand(name = "remove", description = "Remove your comment about the specified Discord user. People with admin perm may remove any comment.", inherit_hooks = True)
	async def app_comment_remove(self, interaction: Interaction, user: Member, comment_id: int):
		await comment_remove(interaction, user, comment_id)


	@app_comment.subcommand(name = "edit", description = "Edit your comment about the specified Discord user.", inherit_hooks = True)
	async def app_comment_edit(self, interaction: Interaction, user: Member, comment_id: int, new_comment: str):
		await comment_edit(interaction, user, comment_id, new_comment)


def setup(bot: Bot):
	bot.add_cog(CommentCog(bot))
