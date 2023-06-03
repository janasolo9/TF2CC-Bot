from nextcord import User
from typing import Optional
from .static import PUG_DB, RUNNER_DB, STRIKE_DB, PugEntry, RunnerEntry, StrikeEntry

# ~~~ Strike DB ~~~

async def new_strike_entry(*, user_id: int = None, user: User = None):
	assert user_id or user, "new_strike_entry error: user_id or user must be specified"
	await STRIKE_DB.new_entry((user_id or user.id, 0, 0, 0, 0, 0, 0, 0, 0))
	#JBOTLOG.debug(f"new strike entry for {user_id or user.id}")


async def get_strike_entry(discord_id: int) -> Optional[StrikeEntry]:
	info = await STRIKE_DB.get_entry(STRIKE_DB.table_column_names[0], discord_id)
	return StrikeEntry(info) if info else None


async def edit_strike_entry(discord_id: int, **kwargs):
	await STRIKE_DB.edit_entry(STRIKE_DB.table_column_names[0], discord_id, **kwargs)
	#JBOTLOG.debug(f"edit strike entry for {discord_id}: {kwargs}")


async def delete_strike_entry(discord_id: int):
	await STRIKE_DB.delete_entry(STRIKE_DB.table_column_names[0], discord_id)
	#JBOTLOG.debug(f"delete strike entry for {discord_id}")


async def get_all_strike_entries(conditional: str = "", params: tuple = None) -> list[StrikeEntry]:
	infos = await STRIKE_DB.get_all_entries(conditional, params)
	return [StrikeEntry(info) for info in infos]


async def mass_edit_strike_entries(key_names: tuple[str], key_vals: tuple[tuple[int]]):
	"""Primary key name goes last in the `key_names` arg."""
	await STRIKE_DB.mass_edit_entry(key_names, key_vals)
	#JBOTLOG.debug(f"mass edit strike entries for {len(key_vals)} entries")


async def mass_delete_strike_entries(key_names: tuple[str], key_vals: tuple[tuple[int]]):
	await STRIKE_DB.mass_delete_entry(key_names, key_vals)
	#JBOTLOG.debug(f"mass delete strike entries for {len(key_vals)} entries")

# ~~~ Pug DB ~~~

async def new_pug_entry(*, user_id: int = None, user: User = None):
	assert user_id or user, "new_pug_entry error: user_id or user must be specified"
	await PUG_DB.new_entry((user_id or user.id, 0, 0, 0, 1000, 0, None, "", 0, 0, 0, 1000))
	#JBOTLOG.debug(f"new pug entry for {user_id or user.id}")


async def get_pug_entry(discord_id: int) -> Optional[PugEntry]:
	info = await PUG_DB.get_entry(PUG_DB.table_column_names[0], discord_id)
	return PugEntry(info) if info else None


async def edit_pug_entry(discord_id: int, **kwargs):
	await PUG_DB.edit_entry(PUG_DB.table_column_names[0], discord_id, **kwargs)
	#JBOTLOG.debug(f"edit pug entry for {discord_id}: {kwargs}")


async def delete_pug_entry(discord_id: int):
	await PUG_DB.delete_entry(PUG_DB.table_column_names[0], discord_id)
	#JBOTLOG.debug(f"delete pug entry for {discord_id}")


async def get_all_pug_entries(conditional: str = "", params: tuple = None) -> list[PugEntry]:
	infos = await PUG_DB.get_all_entries(conditional, params)
	return [PugEntry(info) for info in infos]


async def mass_edit_pug_entries(key_names: tuple[str], key_vals: tuple[tuple[int]]):
	"""Primary key name goes last in the `key_names` arg."""
	await PUG_DB.mass_edit_entry(key_names, key_vals)
	#JBOTLOG.debug(f"mass edit pug entries for {len(key_vals)} entries")


async def mass_delete_pug_entries(key_names: tuple[str], key_vals: tuple[tuple[int]]):
	await PUG_DB.mass_delete_entry(key_names, key_vals)
	#JBOTLOG.debug(f"mass delete pug entries for {len(key_vals)} entries")

# ~~~ Pug Runner DB ~~~

async def new_runner_entry(discord_id: int, **payload):
	await RUNNER_DB.new_entry(
		(
			discord_id,
			payload.get(RUNNER_DB.table_column_names[1], 0), # rpugs
			payload.get(RUNNER_DB.table_column_names[2], 0), # rpugs_last_ran - 0 means never
			payload.get(RUNNER_DB.table_column_names[3], 0), # npugs
			payload.get(RUNNER_DB.table_column_names[4], 0), # npugs_last_ran - 0 means never
			payload.get(RUNNER_DB.table_column_names[5], 0) # became_runner
		)
	)
	#JBOTLOG.debug(f"new runner entry for {discord_id}: {payload}")


async def get_runner_entry(discord_id: int) -> Optional[RunnerEntry]:
	info = await RUNNER_DB.get_entry(RUNNER_DB.table_column_names[0], discord_id)
	return RunnerEntry(info) if info else None


async def edit_runner_entry(discord_id: int, **payload):
	await RUNNER_DB.edit_entry(RUNNER_DB.table_column_names[0], discord_id, **payload)
	#JBOTLOG.debug(f"edit runner entry for {discord_id}: {payload}")


async def delete_runner_entry(discord_id: int):
	await RUNNER_DB.delete_entry(RUNNER_DB.table_column_names[0], discord_id)
	#JBOTLOG.debug(f"delete runner entry for {discord_id}")


async def get_all_runner_entries(conditional: str = "", params: tuple = None) -> list[RunnerEntry]:
	infos = await RUNNER_DB.get_all_entries(conditional, params)
	return [RunnerEntry(info) for info in infos]

