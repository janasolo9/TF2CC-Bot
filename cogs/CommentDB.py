from sqlite3 import OperationalError
from typing import Dict, List, Union
from nextcord import Guild, Role, User
from nextcord.utils import utcnow
from .static import COMMENT_TABLE_VALUES, VALID_ROLES_TABLE_VALUES, CommentInfo, UserComments, get_db


async def new_comment_table(*, user_id: int = None, user: User = None):
	"""Creates a new table for the specified User if a table doesn't exist."""
	assert user_id or user, "new_comment_table error - user_id or user must be specified."
	db = get_db(user_id, user, is_comment = True)
	await db.make_table()
	#JBOTLOG.debug(f"new comment table for {user_id or user.id}")


async def del_comment_table(*, user_id: int = None, user: User = None):
	"""Deletes the table for the specified User."""
	assert user_id or user, "del_comment_table error - user_id or user must be specified."
	db = get_db(user_id, user, is_comment = True)
	await db.drop_table()
	#JBOTLOG.debug(f"dropped comment table for {user_id or user.id}")


async def new_comment(*, user_id: int = None, user: User = None, **payload: Dict[str, Union[int, str]]):
	"""Adds a new comment. `payload` must contain the `guild_id`, `staff_id`, and `comment`."""
	assert user_id or user, "new_comment error - user_id or user must be specified."
	assert COMMENT_TABLE_VALUES[1] in payload, f"new_comment error - {COMMENT_TABLE_VALUES[1]} must be provided."
	assert COMMENT_TABLE_VALUES[2] in payload, f"new_comment error - {COMMENT_TABLE_VALUES[2]} must be provided."
	assert COMMENT_TABLE_VALUES[4] in payload, f"new_comment error - {COMMENT_TABLE_VALUES[4]} must be provided."

	user_comments = await get_all_comments(user_id = user_id, user = user)
	last_comment = user_comments.last_comment
	next_comment_id = last_comment.comment_id + 1 if last_comment else 1
	db = get_db(user_id, user, is_comment = True)
	try:
		await db.new_entry((
			next_comment_id,
			payload.get(COMMENT_TABLE_VALUES[1]),
			payload.get(COMMENT_TABLE_VALUES[2]),
			int(utcnow().timestamp()),
			payload.get(COMMENT_TABLE_VALUES[4])
		))
	except OperationalError:
		await new_comment_table(user_id = user_id, user = user)
		await db.new_entry((
			next_comment_id,
			payload.get(COMMENT_TABLE_VALUES[1]),
			payload.get(COMMENT_TABLE_VALUES[2]),
			int(utcnow().timestamp()),
			payload.get(COMMENT_TABLE_VALUES[4])
		))
	#JBOTLOG.debug(f"added new comment to {user_id or user.id}")


async def get_all_comments(*, user_id: int = None, user: User = None) -> UserComments:
	assert user_id or user, "get_all_comments error - user_id or user must be specified."
	db = get_db(user_id, user, is_comment = True)
	try:
		all_comment_dicts = await db.get_all_entries()
	except OperationalError:
		all_comment_dicts = list()
	#JBOTLOG.debug(f"getting all comments for {user_id or user.id}")
	return UserComments([CommentInfo(info) for info in all_comment_dicts])


async def edit_comment(*, user_id: int = None, user: User = None, override: bool = False, **payload: Dict[str, Union[int, str]]) -> int:
	"""Edits a comment. `payload` must contain the `comment_id`, `guild_id`, `staff_id`, and new `comment`.

	Returns `0` on success, `1` if the `comment_id` provided was invalid, `2` if the staff member cannot edit this comment, `3` if there are no comments."""
	assert user_id or user, "edit_comment error - user_id or user must be specified."
	assert COMMENT_TABLE_VALUES[0] in payload, f"edit_comment error - {COMMENT_TABLE_VALUES[0]} must be provided."
	assert COMMENT_TABLE_VALUES[1] in payload, f"edit_comment error - {COMMENT_TABLE_VALUES[1]} must be provided."
	assert COMMENT_TABLE_VALUES[2] in payload, f"edit_comment error - {COMMENT_TABLE_VALUES[2]} must be provided."
	assert COMMENT_TABLE_VALUES[4] in payload, f"edit_comment error - {COMMENT_TABLE_VALUES[4]} must be provided."

	user_comments = await get_all_comments(user_id = user_id, user = user)
	if not user_comments.comment_count(payload.get(COMMENT_TABLE_VALUES[1])):
		return 3
	comment_info = user_comments.get_comment(payload.get(COMMENT_TABLE_VALUES[0]))

	if not comment_info:
		#JBOTLOG.debug("edit_comment - invalid comment_id")
		return 1

	elif not override and (comment_info.staff_id != payload.get(COMMENT_TABLE_VALUES[2]) or comment_info.guild_id != payload.get(COMMENT_TABLE_VALUES[1])):
		#JBOTLOG.debug("edit_comment - could not edit comment")
		return 2

	db = get_db(user_id, user, is_comment = True)
	new_payload = {
		COMMENT_TABLE_VALUES[4]: payload.get(COMMENT_TABLE_VALUES[4])
	}
	await db.edit_entry(
		COMMENT_TABLE_VALUES[0],
		payload.get(COMMENT_TABLE_VALUES[0]),
		**new_payload
	)
	#JBOTLOG.debug(f"edited comment for {user_id or user.id}")
	return 0


async def delete_comment(*, user_id: int = None, user: User = None, override: bool = False, **payload: Dict[str, Union[int, str]]) -> int:
	"""Deletes a comment. `payload` must contain the `comment_id`, `guild_id`, and `staff_id`.

	Returns `0` on success, `1` if the `comment_id` provided was invalid, `2` if the staff member cannot edit this comment, `3` if there are no comments."""
	assert user_id or user, "delete_comment error - user_id or user must be specified."
	assert COMMENT_TABLE_VALUES[0] in payload, f"delete_comment error - {COMMENT_TABLE_VALUES[0]} must be provided."
	assert COMMENT_TABLE_VALUES[1] in payload, f"delete_comment error - {COMMENT_TABLE_VALUES[1]} must be provided."
	assert COMMENT_TABLE_VALUES[2] in payload, f"delete_comment error - {COMMENT_TABLE_VALUES[2]} must be provided."

	user_comments = await get_all_comments(user_id = user_id, user = user)
	if not user_comments.comment_count(payload.get(COMMENT_TABLE_VALUES[1])):
		return 3
	comment_info = user_comments.get_comment(payload.get(COMMENT_TABLE_VALUES[0]))

	if not comment_info:
		#JBOTLOG.debug("delete_comment - invalid comment_id")
		return 1

	elif not override and (comment_info.staff_id != payload.get(COMMENT_TABLE_VALUES[2]) or comment_info.guild_id != payload.get(COMMENT_TABLE_VALUES[1])):
		#JBOTLOG.debug("delete_comment - could not delete comment")
		return 2

	db = get_db(user_id, user, is_comment = True)
	await db.delete_entry(COMMENT_TABLE_VALUES[0], payload.get(COMMENT_TABLE_VALUES[0]))
	#JBOTLOG.debug(f"deleted comment for {user_id or user.id}")
	return 0


async def new_roles_table(*, guild_id: int = None, guild: Guild = None):
	assert guild_id or guild, "new_roles_table error - guild_id or guild must be specified."
	db = get_db(guild_id, guild, is_comment = False)
	await db.make_table()
	#JBOTLOG.debug(f"new roles table for {guild_id or guild.id}")


async def get_all_role_ids(*, guild_id: int = None, guild: Guild = None) -> List[int]:
	assert guild_id or guild, "get_all_role_ids error - guild_id or guild must be specified."
	db = get_db(guild_id, guild, is_comment = False)
	try:
		all_role_dicts = await db.get_all_entries()
	except OperationalError:
		all_role_dicts = list()
	role_ids = list()
	for role_dict in all_role_dicts:
		role_id = role_dict.get(VALID_ROLES_TABLE_VALUES[0], None)
		if not role_id:
			continue
		role_ids.append(role_id)
	#JBOTLOG.debug(f"getting all roles for {guild_id or guild.id}")
	return role_ids


async def add_role(*, guild_id: int = None, guild: Guild = None, role_id: int = None, role: Role = None):
	assert guild_id or guild, "add_role error - guild_id or guild must be specified."
	assert role_id or role, "add_role error - role_id or role must be specified."
	db = get_db(guild_id, guild, is_comment = False)
	try:
		await db.new_entry((role_id or role.id,))
	except OperationalError:
		await new_roles_table(guild_id = guild_id, guild = guild)
		await db.new_entry((role_id or role.id,))
	#JBOTLOG.debug(f"adding role {role_id or role.id} to guild {guild_id or guild.id} whitelist")


async def remove_role(*, guild_id: int = None, guild: Guild = None, role_id: int = None, role: Role = None):
	assert guild_id or guild, "remove_role error - guild_id or guild must be specified."
	assert role_id or role, "remove_role error - role_id or role must be specified."
	db = get_db(guild_id, guild, is_comment = False)
	try:
		await db.delete_entry(VALID_ROLES_TABLE_VALUES[0], role_id or role.id)
	except OperationalError:
		pass
	#JBOTLOG.debug(f"removing role {role_id or role.id} from guild {guild_id or guild.id} whitelist")
