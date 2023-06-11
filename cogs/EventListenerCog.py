import traceback
from nextcord import BaseApplicationCommand, ChannelType, Embed, Interaction, PartialMessageable, ApplicationInvokeError, ApplicationError, ApplicationCheckFailure
from nextcord.ext.commands import Bot, Cog, Command, Context
from nextcord.ext.application_checks.errors import ApplicationMissingRole, ApplicationMissingAnyRole, ApplicationNotOwner
from nextcord.ext.commands.errors import CommandInvokeError, CommandError, CommandNotFound, MissingRole, MissingAnyRole, NotOwner
from nextcord.utils import utcnow
from typing import Union


TEST_GUILD_AUDIT_CHANNEL_ID = 651636588073189407 # Jamil's Test Server Audit Channel


def error_embed(command: Union[Command, BaseApplicationCommand], error: Exception) -> Embed:
	return Embed(
		title = f"{command.qualified_name if command else 'Other'} Error",
		description = f"{type(error)} - {error}",
		timestamp = utcnow()
	)


class EventListenerCog(Cog, name = "EventListener"):
	EMOJI = "⚙️"
	def __init__(self, bot: Bot):
		self.bot = bot


	@Cog.listener("on_command_error")
	async def command_error_handler(self, ctx: Context, error: Exception):
		#print(type(error), error)
		#traceback.print_exception(type(error), error, error.__traceback__)
		new_error: Exception = error
		if isinstance(error, CommandNotFound): return # ignore this error

		if isinstance(error, CommandInvokeError):
			new_error = getattr(error, "original", error) # get the original error

		if isinstance(error, (MissingRole, MissingAnyRole, NotOwner)):
			new_error = CommandError("You do not have permission to use this command.")

		embed = error_embed(ctx.command, new_error)
		await ctx.send(embed = embed)

		bot: Bot = ctx.bot
		audit_chan: PartialMessageable = bot.get_partial_messageable(
			TEST_GUILD_AUDIT_CHANNEL_ID,
			type = ChannelType.text
		) # test guild audit channel
		embed.description = "```" + "".join(traceback.format_exception(type(error), error, error.__traceback__)) + "```"
		await audit_chan.send(embed = embed)


	@Cog.listener("on_application_command_error")
	async def app_command_error_handler(self, intr: Interaction, error: Exception):
		#print(type(error), error)
		#traceback.print_exception(type(error), error, error.__traceback__)
		if isinstance(error, ApplicationCheckFailure): return

		new_error: Exception = error
		if isinstance(error, ApplicationInvokeError):
			new_error = getattr(error, "original", error) # get the original error

		if isinstance(error, (ApplicationMissingRole, ApplicationMissingAnyRole, ApplicationNotOwner)):
			new_error = ApplicationError("You do not have permission to use this command.")

		bot: Bot = intr.client
		audit_chan: PartialMessageable = bot.get_partial_messageable(
			TEST_GUILD_AUDIT_CHANNEL_ID,
			type = ChannelType.text
		) # test guild audit channel
		embed = error_embed(intr.application_command, new_error)
		# ephemeral if error is "commant must be used in bot commands"
		await intr.send(embed = embed, ephemeral = "#844343298977693706" in str(error))
		embed.description = "```" + "".join(traceback.format_exception(type(error), error, error.__traceback__)) + "```"
		await audit_chan.send(embed = embed)


def setup(bot: Bot):
	bot.add_cog(EventListenerCog(bot))
