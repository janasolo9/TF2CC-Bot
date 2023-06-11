import re
from nextcord import ButtonStyle, ChannelType, Color, Embed, Interaction, Member, TextChannel, TextInputStyle, Thread, slash_command
from nextcord.ext.commands import Cog
from nextcord.ext.application_checks import has_any_role
from nextcord.ext.tasks import loop
from nextcord.interactions import Interaction
from nextcord.utils import utcnow
from nextcord.ui import Button, Modal, TextInput, View, button
from bot import TF2CCBot
from staticvars import TF2CC
from .SupportDB import del_ticket2, get_all_tickets2, get_ticket_by_channel2, get_ticket2, new_ticket2
from .static import SUPPORT2_DB, TICKET_EMBED


OWNER_NAME_REGEX = "\([\w\W]+[\d]{4}\)"
OWNER_PATTERN = re.compile(OWNER_NAME_REGEX)


def new_support_thread_name(owner: Member, topic: str = None) -> str:
	topic = topic or "TF2CC Support"
	# limiting thread name to 100 (95 with 5 buffer)
	topic_length_limit = 100 - 5 - (len(owner.name) + len(owner.discriminator))
	if len(topic) > topic_length_limit:
		raise ValueError(f"Topic may only be {topic_length_limit} characters for this thread.")
	return topic + f" ({owner.name}{owner.discriminator})"


def get_support_thread_name(thread: Thread) -> tuple[str, str] | None:
	# returns thread topic | owner name
	match = re.search(OWNER_PATTERN, thread.name)
	if not match:
		# no match, return
		return None
	first, last = match.span()
	# first is the index of (
	# last is the index of ) + 1
	# example: TF2CC Support (Jamillia4845)
	# so owner would be first + 1 : last - 1
	# so topic would be 0 : first - 2
	owner = thread.name[first + 1 : last - 1]
	topic = thread.name[:first - 2]
	return topic, owner


async def archive_support_ticket(thread: Thread, intr: Interaction):
	# if this gets past all of the checks, then archive this channel.
	embed = Embed(
		title = "Archiving TF2CC Support Ticket",
		description = "If your inquiry has not been resolved, then please open another TF2CC Support Ticket."
	).set_footer(
		text = "TF2CC Support",
		icon_url = TF2CC.icon_url
	)
	await intr.send(embed = embed)
	await thread.edit(archived = True, locked = True)

	# removed ticket from db
	await del_ticket2(intr.user.id)


class PersistentCloseButton(View):
	def __init__(self):
		super().__init__(timeout = None)
		self.valid_role_ids = (TF2CC.moderator_rid, TF2CC.event_runner_rid, TF2CC.admin_rid, TF2CC.owner_rid)

	async def interaction_check(self, intr: Interaction) -> bool:
		await intr.response.defer(ephemeral = True)

		# if user is event runner, mod, admin, owner, then ok
		for role_id in self.valid_role_ids:
			if intr.user.get_role(role_id):
				return True

		# if this channel is not a thread under support ticket channel, then bad
		if not isinstance(intr.channel, Thread):
			await intr.send("This is not a support thread.", ephemeral = True)
			return False
		thread: Thread = intr.channel
		if not thread.parent or thread.parent_id != TF2CC.ticket_channel_id:
			await intr.send("This is not a support thread.", ephemeral = True)
			return False

		# if user is ticket owner, then ok
		open_ticket = await get_ticket_by_channel2(thread.id)
		if not open_ticket:
			await intr.send(
				"Something went wrong when closing this ticket. Please contact <@138485643473977344> (Jamillia#4845).\n(Error 2: could not find the db entry)",
				ephemeral = True
			)
			return
		owner_id = open_ticket.owner_id
		if intr.user.id == owner_id:
			return True
		await intr.send("You are not allowed to close this ticket.", ephemeral = True)
		return False

	@button(label = "Close", style = ButtonStyle.red, custom_id = "persistent_support_view:close_ticket")
	async def close_support_ticket(self, button: Button, intr: Interaction):
		await archive_support_ticket(intr.channel, intr)


class PersistentSupport2(View):
	def __init__(self):
		super().__init__(timeout=None)

	@button(label = "New Ticket", style = ButtonStyle.primary, emoji = "❗", custom_id = "persistent_view:new_ticket")
	async def new_support_ticket(self, button: Button, intr: Interaction):
		# check if open ticket exists
		# if ticket exists, return
		if open_ticket := await get_ticket2(intr.user.id):
			# check if ticket is already closed
			open_ticket_channel: Thread = intr.guild.get_channel_or_thread(open_ticket.channel_id)

			# ticket was not already closed
			if open_ticket_channel and not (open_ticket_channel.archived or open_ticket_channel.locked):
				await intr.send(
					"You already have an open ticket " + open_ticket_channel.mention,
					ephemeral = True
				)
				return
			
			# could not find channel or it was already closed
			# delete ticket in DB and make new
			await del_ticket2(intr.user.id)

		# no open ticket exists -> create a new one
		# get support ticket channel
		support_ticket_channel: TextChannel = intr.guild.get_channel(TF2CC.ticket_channel_id)
		if not support_ticket_channel:
			# could not find support ticket channel
			await intr.send(
				"Could not create a support ticket. Please contact <@138485643473977344> (Jamillia#4845).\n(Error 1: could not find support channel)",
				ephemeral = True
			)
			return

		# create a new private thread
		thread_name = new_support_thread_name(intr.user)
		thread = await support_ticket_channel.create_thread(
			name = thread_name,
			type = ChannelType.private_thread,
			reason = "Opening support ticket"
		)

		# save it in the DB
		await new_ticket2(owner = intr.user, channel = thread)

		# add people to the thread
		await thread.send(f"<@&{TF2CC.moderator_rid}>", delete_after = 1)
		msg = await thread.send(intr.user.mention, embed = TICKET_EMBED, view = PersistentCloseButton())
		await msg.pin()


class SupportTicketCog(Cog, name = "Support Ticket"):
	def __init__(self, bot: TF2CCBot):
		self.bot = bot
		self.valid_role_ids = (TF2CC.moderator_rid, TF2CC.event_runner_rid, TF2CC.admin_rid, TF2CC.owner_rid)
		if not self._check_all_open_tickets.get_task():
			self._check_all_open_tickets.start()

	@Cog.listener(name = "on_ready")
	async def support_on_ready(self):
		await SUPPORT2_DB.make_table()
		if len(self.bot.persistent_views) < self.bot.persistent_views_count:
			self.bot.add_view(PersistentSupport2())
			self.bot.add_view(PersistentCloseButton())
			self.bot.log.debug("added support persistent views")


	@loop(time = utcnow().time().replace(hour = 0, minute = 0, second = 0, microsecond = 0))
	async def _check_all_open_tickets(self):
		# get support ticket channel
		support_ticket_channel: TextChannel = self.bot.get_channel(TF2CC.ticket_channel_id)
		if not support_ticket_channel:
			return
		
		open_threads = filter(lambda thread: not (thread.archived or thread.locked),support_ticket_channel.threads)
		open_thread_ids = {thread.id for thread in open_threads}

		# remove any threads from DB that are closed
		tickets = await get_all_tickets2()
		for ticket in tickets:
			if ticket.channel_id not in open_thread_ids:
				await del_ticket2(ticket.owner_id)


	@slash_command(name = "ticket", guild_ids = [TF2CC.guild_id])
	async def ticket_slash(self, intr: Interaction):
		pass


	@ticket_slash.subcommand(name = "close", description = "Closes the TF2CC Support Ticket.")
	async def ticket_close(self, intr: Interaction):
		# need to go through the same checks as the close button
		await intr.response.defer()

		# if user is event runner, mod, admin, owner, then ok
		for role_id in self.valid_role_ids:
			if intr.user.get_role(role_id):
				await archive_support_ticket(intr.channel, intr)
				return

		# if this channel is not a thread under support ticket channel, then bad
		if not isinstance(intr.channel, Thread):
			await intr.send("This is not a support thread.", ephemeral = True)
			return
		thread: Thread = intr.channel
		if not thread.parent or thread.parent_id != TF2CC.ticket_channel_id:
			await intr.send("This is not a support thread.", ephemeral = True)
			return

		# if user is ticket owner, then ok
		open_ticket = await get_ticket_by_channel2(thread.id)
		if not open_ticket:
			await intr.send(
				"Something went wrong when closing this ticket. Please contact <@138485643473977344> (Jamillia#4845).\n(Error 2: could not find the db entry)",
				ephemeral = True
			)
			return
		owner_id = open_ticket.owner_id
		if intr.user.id == owner_id:
			await archive_support_ticket(intr.channel, intr)
			return
		await intr.send("You are not allowed to close this ticket.", ephemeral = True)


	@ticket_slash.subcommand(name = "topic", description = "Change the topic of the Support Ticket.")
	@has_any_role("Moderators", "Admins", "Owners")
	async def ticket_topic(self, intr: Interaction, new_topic: str):
		# this command can only be used by staff
		await intr.response.defer(ephemeral = True)

		# if this channel is not a thread under support ticket channel, then bad
		thread = intr.channel
		if not isinstance(thread, Thread):
			await intr.send("This is not a support thread.", ephemeral = True)
			return
		if not thread.parent or thread.parent_id != TF2CC.ticket_channel_id:
			await intr.send("This is not a support thread.", ephemeral = True)
			return

		# get current topic and owner name
		info = get_support_thread_name(thread)
		if not info:
			await intr.send("Something went wrong when changing the topic. Please contact <@138485643473977344> (Jamillia#4845).\n(Error 3: no match in thread name)")
			return

		# get the thread owner
		ticket_info = await get_ticket_by_channel2(thread.id)
		if not ticket_info:
			await intr.send("Something went wrong when changing the topic. Please contact <@138485643473977344> (Jamillia#4845).\n(Error 4: could not find ticket in db)", ephemeral = True)
			return
		owner = intr.guild.get_member(ticket_info.owner_id)
		if not owner:
			await intr.send("Something went wrong when changing the topic. Please contact <@138485643473977344> (Jamillia#4845).\n(Error 4: could not find ticket in db)", ephemeral = True)
			return

		try:
			# change thread name
			thread_name = new_support_thread_name(owner, new_topic)
			await thread.edit(name = thread_name)
			await intr.send("Changing the topic.", ephemeral = True)
			embed = Embed(
				f"{intr.user.mention} changed the topic of the channel to **{new_topic}**"
			)
			await thread.send(embed = embed)
		except ValueError as err:
			await intr.send(f"Could not change the topic: `{str(err)}`", ephemeral = True)
		except Exception as err:
			await intr.send(f"Some error just occured.\n{type(err)} - {str(err)}", ephemeral = True)


	@ticket_slash.subcommand(name = "message", description = "Sends a persistent button message.")
	@has_any_role("Moderators", "Admins", "Owners")
	async def ticket_message(self, intr: Interaction):
		class EmbedModal(Modal):
			def __init__(self):
				super().__init__("Embed Maker")
				self.embed_title = TextInput(
					"Embed Title",
					max_length = 128,
					required = True,
					default_value = "TF2CC Support",
					placeholder = "Enter embed title here..."
				)
				self.add_item(self.embed_title)

				self.embed_description = TextInput(
					"Embed Description",
					style = TextInputStyle.paragraph,
					max_length = 4000,
					required = True,
					default_value = """Press the button below to create a new Support Ticket. You may use your ticket for any problems you have within the TF2CC Discord server.

__Note: you may only have one ticket open at a time, so re-use the same ticket if you have multiple queries.__""",
					placeholder = "Enter embed description here..."
				)
				self.add_item(self.embed_description)

			async def callback(self, interaction: Interaction):
				embed = Embed(
					title = self.embed_title.value,
					description = self.embed_description.value,
					color = Color.from_rgb(225, 83, 76)
				)
				view = PersistentSupport2()
				await interaction.send("Sending new message with persistent button.", ephemeral = True)
				await interaction.channel.send(embed = embed, view = view)

		await intr.response.send_modal(EmbedModal())


def setup(bot: TF2CCBot):
	bot.add_cog(SupportTicketCog(bot))
