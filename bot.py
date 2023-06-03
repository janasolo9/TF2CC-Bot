from logging import FileHandler, Formatter, getLogger, DEBUG
from nextcord import Guild, Interaction
from nextcord.ext.commands import Bot, Context

class TF2CCBot(Bot):
	def __init__(
		self,
		version: str = None,
		debug_level: int = DEBUG,
		valid_guild_ids: tuple[int] = None,
		cogs: tuple[str] = None,
		*args, **kwargs
	):
		super().__init__(*args, **kwargs)
		self.version = version
		self.valid_guild_ids = valid_guild_ids or tuple()
		self.persistent_views_count = 0

		# set up logging to be used in all cogs
		self.log = getLogger("debug")
		logging_format = "[{asctime}][{filename}][{lineno:3}][{funcName}][{levelname}] {message}"
		log_format = Formatter(logging_format, style = "{")
		log_handler = FileHandler("./tf2cc_debug_logs.log")
		log_handler.setFormatter(log_format)
		self.log.addHandler(log_handler)
		self.log.setLevel(debug_level)

		# add cogs to the bot
		if not cogs:
			return

		self.log.debug(f"Loading {len(cogs)} cogs")
		try:
			self.load_extensions(cogs)
		except Exception as error:
			raise error
		finally:
			self.loaded_cogs = cogs
		self.log.debug(f"Loaded cogs\n{self.loaded_cogs}")


	async def on_ready(self):
		# this is called whenever the bot is ready to do things
		# it may be called multiple times while the bot is alive
		self.log.debug(f"{self.user} ready")

		# leave any guild that the bot should not be in
		for guild in self.guilds:
			if guild.id not in self.valid_guild_ids:
				await guild.leave()


	async def on_guild_join(self, guild: Guild):
		# leave any guild that the bot should not be in
		if guild.id not in self.valid_guild_ids:
			await guild.leave()


	async def on_command_error(self, context: Context, exception: Exception):
		# this is called whenever a prefix command raises an error
		# Jamillia chose not to handle errors in the main bot handler, but in cog handlers instead
		return
	

	async def on_application_command_error(self, interaction: Interaction, exception: Exception):
		# this is called whenever a slash command raises an error
		# Jamillia chose not to handle errors in the main bot handler, but in cog handlers instead
		return
