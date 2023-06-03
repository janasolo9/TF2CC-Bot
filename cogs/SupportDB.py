from nextcord import Thread, User
from typing import Optional
from .static import SUPPORT2_DB, TicketInfo2

async def new_ticket2(*, owner_id: int = None, owner: User = None, channel_id: int = None, channel: Thread = None):
	assert owner_id or owner, "new_ticket2 error - owner_id or owner must be specified."
	assert channel_id or channel, "new_ticket2 error - channel_id or channel msut be specified."
	await SUPPORT2_DB.new_entry(( (owner_id or owner.id), (channel_id or channel.id) ))


async def get_ticket2(owner_id: int, /) -> Optional[TicketInfo2]:
	info = await SUPPORT2_DB.get_entry(SUPPORT2_DB.table_column_names[0], owner_id)
	return TicketInfo2(info) if info else None


async def get_ticket_by_channel2(channel_id: int, /) -> Optional[TicketInfo2]:
	info = await SUPPORT2_DB.get_entry(SUPPORT2_DB.table_column_names[1], channel_id)
	return TicketInfo2(info) if info else None


async def get_all_tickets2() -> list[TicketInfo2]:
	infos = await SUPPORT2_DB.get_all_entries()
	return [TicketInfo2(info) for info in infos]


async def del_ticket2(owner_id: int, /):
	await SUPPORT2_DB.delete_entry(SUPPORT2_DB.table_column_names[0], owner_id)
