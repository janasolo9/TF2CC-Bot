from aiosqlite import Row, connect
from nextcord import ButtonStyle, Color, Embed, Interaction
from nextcord.ext.commands import Context
from nextcord.ext.menus import ButtonMenuPages, ListPageSource, MenuPagesBase, MenuPaginationButton
from typing import Optional, Union


def get_tuple_vals(itr1: tuple, itr2: tuple) -> tuple[tuple]:
	"""Takes two tuples `itr1` and `itr2` and returns a new tuple with zipped values."""
	assert len(itr1) == len(itr2), "get_tuple_vals error - All iterables must be the same length"
	return tuple([(itm1, itm2) for itm1, itm2 in zip(itr1, itr2)])


class ADB:
	def __init__(self, db_name: str, table_name: str, table_values: tuple[str], table_value_types: tuple[str]):
		self.db_name = db_name
		self.table_name = table_name
		self.table_column_names = table_values
		self.table_column_types = table_value_types


	async def make_table(self):
		"""Creates the database file and table associated with this object."""
		table_vals = get_tuple_vals(self.table_column_names, self.table_column_types)
		exec_str = f"""
CREATE TABLE IF NOT EXISTS {self.table_name} 
	({", ".join([f"{col_name} {col_type}" for col_name, col_type in table_vals])})
"""
		async with connect(self.db_name) as conn:
			await conn.execute(exec_str)
			await conn.commit()


	async def drop_table(self):
		"""Deletes the database table associated with this object."""
		async with connect(self.db_name) as conn:
			await conn.execute(f"DROP TABLE {self.table_name}")
			await conn.commit()


	async def reset_table(self):
		"""Removes all entries in the database table."""
		async with connect(self.db_name) as conn:
			await conn.execute(f"DELETE FROM {self.table_name}")
			await conn.commit()


	async def new_entry(self, starting_values: tuple[Union[str, int]], replace: bool = False):
		"""Adds a new entry to the database table. Optionally overwrites an existing entry if it exists."""
		exec_str = f"""
INSERT OR {"REPLACE" if replace else "IGNORE"} INTO {self.table_name} 
VALUES ({",".join(["?"] * len(starting_values))})
"""
		async with connect(self.db_name) as conn:
			await conn.execute(exec_str, starting_values)
			await conn.commit()


	async def get_entry(self, primary_key_name: str, primary_key_val: Union[str, int]) -> Optional[dict]:
		"""Returns an entry in the database table or `None` if it doesn't exist."""
		exec_str = f"""
SELECT * FROM {self.table_name} 
WHERE {primary_key_name} = ?
"""
		async with connect(self.db_name) as conn:
			conn.row_factory = Row
			rows = await conn.execute_fetchall(exec_str, (primary_key_val,))
		return dict(rows[0]) if rows else None


	async def get_all_entries(self, conditional: str = "", params: tuple[Union[str, int]] = None) -> list[dict]:
		"""Returns all entries in the database table in a list."""
		exec_str = f"SELECT * FROM {self.table_name} " + conditional
		async with connect(self.db_name) as conn:
			conn.row_factory = Row
			if params:
				rows = await conn.execute_fetchall(exec_str, params)
			else:
				rows = await conn.execute_fetchall(exec_str)
		return [dict(row) for row in rows]


	async def edit_entry(self, primary_key_name: str, primary_key_val: Union[str, int], **kwargs):
		"""Edits an existing entry in the database table. If the entry does not exist, then an error is thrown."""
		exec_str = f"""
UPDATE {self.table_name} 
SET {",".join([f"{col_name} = ?" for col_name, _ in kwargs.items()])} 
WHERE {primary_key_name} = ?
"""
		async with connect(self.db_name) as conn:
			await conn.execute(exec_str, tuple(kwargs.values()) + (primary_key_val,))
			await conn.commit()


	async def mass_edit_entry(self, key_names: tuple[str], key_vals: tuple[tuple[Union[str, int]]]):
		'''Primary key name goes last in the `key_names` arg.'''
		exec_str = f"""
UPDATE {self.table_name} 
SET {",".join([f"{key_name} = ?" for key_name in key_names[:-1]])} 
WHERE {key_names[-1]} = ?
"""
		async with connect(self.db_name) as conn:
			await conn.executemany(exec_str, key_vals)
			await conn.commit()


	async def delete_entry(self, primary_key_name: str, primary_key_val: Union[str, int]):
		"""Deletes an entry from the database table."""
		exec_str = f"DELETE FROM {self.table_name} WHERE {primary_key_name} = ?"
		async with connect(self.db_name) as conn:
			await conn.execute(exec_str, (primary_key_val,))
			await conn.commit()


	async def mass_delete_entry(self, key_names: tuple[str], key_vals: tuple[tuple[Union[str, int]]]):
		exec_str = f"""
DELETE FROM {self.table_name} 
WHERE {" AND ".join([f"{key_name} = ?" for key_name in key_names])}
"""
		async with connect(self.db_name) as conn:
			await conn.executemany(exec_str, key_vals)
			await conn.commit()


class MyPageSource(ListPageSource):
	def __init__(self, data: list[Union[str, tuple[str, str]]], per_page: int, *, embed_title: str = None, embed_inline: bool = None, embed_color: Color = None):
		assert per_page <= 25, "MyPageSource error - per_page must be <= 25"
		super().__init__(data, per_page = per_page)
		self.embed_title = embed_title
		self.embed_inline = embed_inline
		self.embed_color = embed_color if embed_color else Color.dark_grey()

	async def format_page(self, menu: MenuPagesBase, entries: list[Union[str, tuple[str, str]]]) -> Embed:
		embed = Embed(title = self.embed_title or "", color = self.embed_color)
		if isinstance(entries[0], str):
			embed.description = "\n".join(entries)
		else:
			for field_name, field_value in entries:
				embed.add_field(name = field_name, value = field_value, inline = self.embed_inline if self.embed_inline is not None else True)
		embed.set_footer(text = f"Page {menu.current_page + 1} / {self.get_max_pages()}")
		return embed



class MyButtonMenuPages(ButtonMenuPages, inherit_buttons = False):
	def __init__(self, *, source: ListPageSource, timeout: int, delete_after: int, delete_message_after: bool, clear_buttons_after: bool):
		super().__init__(source, timeout = timeout, delete_message_after = delete_message_after, clear_buttons_after = clear_buttons_after)
		self.add_item(MenuPaginationButton(emoji = self.FIRST_PAGE, style = ButtonStyle.blurple))
		self.add_item(MenuPaginationButton(emoji = self.PREVIOUS_PAGE, style = ButtonStyle.blurple))
		self.add_item(MenuPaginationButton(emoji = self.STOP, style = ButtonStyle.red))
		self.add_item(MenuPaginationButton(emoji = self.NEXT_PAGE, style = ButtonStyle.blurple))
		self.add_item(MenuPaginationButton(emoji = self.LAST_PAGE, style = ButtonStyle.blurple))
		self._disable_unavailable_buttons()
		self.delete_after = delete_after

	async def finalize(self, timed_out: bool):
		if not self.delete_message_after and self.delete_after:
			await self.message.delete(delay = self.delete_after)

	async def interaction_check(self, interaction: Interaction) -> bool:
		user = self.ctx.author if self.ctx else interaction.user
		return interaction.user == user


async def send_menu_pages(data: list[Union[str, tuple[str, str]]], info_obj: Union[Context, Interaction], amnt_per_page: int, **kwargs):
	"""`data` must be a list of strings or a list of tuples of strings.\n
`info_obj` - Union[Context, Interaction]
`amnt_per_page` must be an integer <= 25.\n
Possible `kwargs` include:\n
- `embed_title` - str (default: None)\n
- `embed_inline` - bool (default: True)\n
- `embed_color` - nextcord.Color (default: dark_grey)\n
- `timeout` - int (default: 60)\n
- `ephemeral` - bool (default: False)\n
- `wait` - bool (default: False)\n
- `delete_after` - int (default: 0)\n
- `delete_message_after` - bool (default: False)\n
- `clear_buttons_after` - bool (default: True)
	"""
	assert isinstance(data[0], str) or (isinstance(data[0], tuple) and len(data[0]) == 2 and isinstance(data[0][0], str) and isinstance(data[0][1], str)), "send_menu_pages error - data must be either a list of str or a list of tuple of str"
	menu = MyButtonMenuPages(
		source = MyPageSource(
			data,
			per_page = amnt_per_page,
			embed_title = kwargs.get("embed_title", None),
			embed_inline = kwargs.get("embed_inline", None),
			embed_color = kwargs.get("embed_color", None)
		),
		timeout = kwargs.get("timeout", 60),
		delete_after = kwargs.get("delete_after", 0),
		delete_message_after = kwargs.get("delete_message_after", False),
		clear_buttons_after = kwargs.get("clear_buttons_after", True)
	)
	await menu.start(
		ctx = info_obj if isinstance(info_obj, Context) else None,
		interaction = info_obj if isinstance(info_obj, Interaction) else None,
		ephemeral = kwargs.get("ephemeral", False),
		wait = kwargs.get("wait", False)
	)