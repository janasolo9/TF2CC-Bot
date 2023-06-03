
from nextcord import Embed, Interaction, Role, User
from nextcord.ext.commands import Context
from typing import Dict, List, Union
from static.BaseVar import get_user, send_menu_pages
from .static import COMMENT_TABLE_VALUES
from .CommentDB import add_role, delete_comment, edit_comment, get_all_comments, get_all_role_ids, new_comment, remove_role


async def comment_role_add(info_obj: Union[Context, Interaction], role: Role):
	await add_role(guild = info_obj.guild, role = role)
	embed = Embed(description = f"Added {role.mention} to the whitelist.")
	await info_obj.send(embed = embed)


async def comment_role_remove(info_obj: Union[Context, Interaction], role: Role):
	await remove_role(guild = info_obj.guild, role = role)
	embed = Embed(description = f"Removed {role.mention} from the whitelist.")
	await info_obj.send(embed = embed)


async def comment_add(info_obj: Union[Context, Interaction], user: User, comment: str):
	payload: Dict[str, Union[int, str]] = {
		COMMENT_TABLE_VALUES[1]: info_obj.guild.id,
		COMMENT_TABLE_VALUES[2]: get_user(info_obj).id,
		COMMENT_TABLE_VALUES[4]: comment
	}
	await new_comment(user = user, **payload)
	embed = Embed(description = f"Added a new comment about {user.mention}\n\n{comment}")
	await info_obj.send(embed = embed)


async def comment_remove(info_obj: Union[Context, Interaction], user: User, comment_id: int):
	override = get_user(info_obj).guild_permissions.administrator
	payload = {
		COMMENT_TABLE_VALUES[0]: comment_id,
		COMMENT_TABLE_VALUES[1]: info_obj.guild.id,
		COMMENT_TABLE_VALUES[2]: get_user(info_obj).id
	}
	num = await delete_comment(user = user, override = override, **payload)
	if num == 1:
		await info_obj.send(f"Invalid `comment_id` provided: {comment_id}")
		return
	elif num == 2:
		await info_obj.send(f"You may not remove this comment.")
		return
	embed = Embed(description = f"Removed the comment with ID {comment_id} about {user.mention}.")
	await info_obj.send(embed = embed)


async def comment_edit(info_obj: Union[Context, Interaction], user: User, comment_id: int, new_comment: str):
	payload = {
		COMMENT_TABLE_VALUES[0]: comment_id,
		COMMENT_TABLE_VALUES[1]: info_obj.guild.id,
		COMMENT_TABLE_VALUES[2]: get_user(info_obj).id,
		COMMENT_TABLE_VALUES[4]: new_comment
	}
	num = await edit_comment(user = user, **payload)
	if num == 1:
		await info_obj.send(f"Invalid `comment_id` provided: {comment_id}")
		return
	elif num == 2:
		await info_obj.send(f"You may not edit this comment.")
		return
	embed = Embed(description = f"Edited the comment with ID {comment_id} about {user.mention}.\n\n{new_comment}")
	await info_obj.send(embed = embed)


async def comment_list(info_obj: Union[Context, Interaction], user: User):
	user_comments = await get_all_comments(user = user)
	if not user_comments.comment_count(info_obj.guild.id):
		embed = Embed(description = "There are no comments about this user.")
		await info_obj.send(embed = embed)
		return

	comments = user_comments.get_comments(info_obj.guild.id)
	data = []
	for comment in comments:
		staff = info_obj.guild.get_member(comment.staff_id)
		if not staff:
			continue
		data.append((f"Commenter: {str(staff)}", f"{comment.comment_id}. {comment.comment[:200]}"))

	await send_menu_pages(
		data = data,
		info_obj = info_obj,
		amnt_per_page = 10,
		embed_title = f"Comments about {str(user)}",
		embed_inline = False
	)


async def valid_roles_list(info_obj: Union[Context, Interaction]):
	role_ids = await get_all_role_ids(guild = info_obj.guild)
	roles: List[Role] = list()
	for role_id in role_ids:
		role = info_obj.guild.get_role(role_id)
		if role:
			roles.append(role)
	embed = Embed(
		title = "Valid Roles",
		description = " ".join(role.mention for role in roles) or None
	)
	await info_obj.send(embed = embed)
