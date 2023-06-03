# cog to interact with Serveme and their API
# reserves North American servers

import aiohttp
from datetime import datetime, timedelta
from enum import StrEnum, auto
from nextcord import ButtonStyle, Embed, Interaction, SelectOption, SlashOption, slash_command
from nextcord.ext.application_checks import has_any_role
from nextcord.ext.commands import Cog
from nextcord.interactions import Interaction
from nextcord.ui import View, Button, Select, button
from nextcord.utils import format_dt, get, utcnow
from os import getenv
from random import choices, randint

from bot import TF2CCBot
from staticvars import TF2CC, COMP_MAPS


SERVEME_BASE_URL = "https://na.serveme.tf/api/reservations/"
SERVEME_API_HEADERS = {
	"Content-Type": "application/json",
	"Authorization": f"Token token={getenv('SERVEME_API_KEY')}"
}


class Region(StrEnum):
	NA_WEST = auto()
	NA_CENTRAL = auto()
	NA_EAST = auto()
	EU = auto()
    

class ReservationInfo:
	# converts JSON dict into something useable
	def __init__(self, info: dict):
		self.server_ip: str = info["server"]["ip"]
		self.server_port: str = info["server"]["port"]
		self.server_ip_and_port: str = info["server"]["ip_and_port"]

		self.stv_port: str = str(int(self.server_port) + 5)
		self.stv_ip_and_port = f"{self.server_ip}:{self.stv_port}"

		self.server_password: str = info["password"]
		self.stv_password: str = info["tv_password"]
		self.rcon_password: str = info["rcon"]

		self.reservation_id: int = info["id"]


class ServemeSelect(Select):
	view: "ServemeView"
	# Discord drop down menu
	# used to display different serveme options
	def __init__(self, *, custom_id: str, placeholder: str, options: list[SelectOption], row: int):
		super().__init__(cutom_id = custom_id, placeholder = placeholder, options = options, row = row)

		# intentionally set to None
		# this will be edited in the callback when the user chooses something
		self.item_id: str = None


	async def callback(self, intr: Interaction):
		# set the selected item on this select menu
		value = self.values[0]
		for option in self.options:
			option.default = option.value == value

		value, self.item_id = value.split("|")

		# edit the embed to show the selected option
		embed = intr.message.embeds[0]
		embed.set_field_at(
			self.row + 2,
			name = self.custom_id[:-len("Select")],
			value = value
		)
		await intr.edit(embed = embed, view = self.view)

		# check if all selects have a value
		all_chosen = True
		for item in self.view.children:
			if isinstance(item, Button):
				continue

			if not item.item_id:
				all_chosen = False
				break

		# enable confirm button if all selects have a value
		if not all_chosen:
			return

		self.view.all_chosen = all_chosen
		for item in self.view.children:
			if not isinstance(item, Button):
				continue

			if item.label == "Confirm":
				item.disabled = False
				break
		await intr.edit(view = self.view)


class ServemeView(View):
	children: list[Button | ServemeSelect]
	def __init__(self, *, user_id: int, timeout: int = 60):
		super().__init__(timeout = timeout)
		self.user_id = user_id
		self.all_chosen = False
		self.make_request = None
		self.autoend = False # change this to True if you want autoend enabled on server reservations

	# only allow the person who started this reservation to interact with it
	async def interaction_check(self, intr: Interaction) -> bool:
		return intr.user.id == self.user_id
	
	@button(label = "Confirm", emoji = "✅", style = ButtonStyle.green, row = 4, disabled = True)
	async def confirm_button(self, button: Button, intr: Interaction):
		self.make_request = True
		self.stop()

	@button(label = "Cancel", emoji = "⛔", style = ButtonStyle.red, row = 4)
	async def confirm_button(self, button: Button, intr: Interaction):
		self.make_request = False
		self.stop()


def get_random_password() -> str:
	# this gives a random server and rcon password
	# change lines in step 3 of creating the reservation if you want to use a set password
	keys = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
	return "".join(choices(keys, k = randint(10,20)))


async def setup_view(user_id: int, reservation_info: dict, region: Region) -> ServemeView:
	# sets up the ServemeView class with the relevant information from Serveme
	servers: list[dict][str, str | int | bool] = reservation_info["servers"] # all of the currently available servers for this timeslot
	servers = list(filter(lambda server: not server["sdr"], servers))
	configs: list[dict[str, str | int]] = reservation_info["server_configs"] # all of the server configs
	whitelists: list[dict[str, str | int]] = reservation_info["whitelists"] # all of the whitelists
	view = ServemeView(user_id = user_id)

	# Create SelectOptions for all available servers. obama, chi, ks, la, taylor
	# Chicago will be highest priority
	# Kansas will be second highest
	# All others will be last
	sorted_server_options: dict[str, list[SelectOption]] = {
		"obama": list(),
		"chi": list(),
		"ks": list(),
		"dal": list(),
		"la": list(),
		"taylor": list()
	}
	for server in servers:
		option = SelectOption(
			label = server["name"],
			description = server["ip_and_port"],
			value = f"{server['name']}|{server['id']}"
		)
		if "obama" in server["ip"]:
			sorted_server_options["obama"].append(option)
		elif "chi" in server["ip"]:
			sorted_server_options["chi"].append(option)
		elif "ks" in server["ip"]:
			sorted_server_options["ks"].append(option)
		elif "dal" in server["ip"]:
			sorted_server_options["dal"].append(option)
		elif "la" in server["ip"]:
			sorted_server_options["la"].append(option)
		elif "taylor" in server["ip"]:
			sorted_server_options["taylor"].append(option)

	if region == Region.NA_WEST:
		skip_region = ("la",)
		server_options = sorted_server_options.get("la", list())
	elif region == Region.NA_CENTRAL:
		skip_region = ("obama", "chi", "ks", "dal")
		server_options = sorted_server_options.get("obama", list()) + sorted_server_options.get("chi", list()) + sorted_server_options.get("ks", list()) + sorted_server_options.get("dal", list())
	else:
		skip_region = ("taylor",)
		server_options = sorted_server_options.get("taylor", list())

	for server in sorted_server_options:
		if server in skip_region:
			continue
		server_options += sorted_server_options[server]

	if len(server_options) == 0:
		raise ValueError("There are no servers available at this time.")

	# Create SelectOptions for all available config files.
	# filter out only server configs that are RGL configs to place at the top
	config_options = [
		SelectOption(
			label = config["file"],
			value = f"{config['file']}|{config['id']}"
		)
		for config in configs if config["file"].startswith("rgl_")
	]

	# Create SelectOptions for all available config files.
	# filter out only whitelists that are RGL whitelists to place at the top
	whitelist_options = [
		SelectOption(
			label = whitelist["file"],
			value = f"{whitelist['file']}|{whitelist['id']}"
		)
		for whitelist in whitelists if whitelist["file"].startswith("rgl_")
	]


	map_options = [
		SelectOption(
			label = map_name,
			value = f"{map_name}|{map_name}"
		)
		for map_name in COMP_MAPS
	] # starting maps - these are defined at the top of the file. you can include or change any of the ones in the list

	for i, pair in enumerate(
		zip(
			(server_options, config_options, whitelist_options, map_options),
			("server", "config", "whitelist", "map")
		)
	):
		options, name = pair
		view.add_item(
			ServemeSelect(
				custom_id = name,
				placeholder = f"Choose a {name}...",
				options = options,
				row = i
			)
		)

	return view


async def reserve_server(intr: Interaction, start: datetime, end: datetime, region: Region):
	user = intr.user

	# reserve the Serveme server given start, end, and region
	embed = Embed(
		title = "Reservation Information",
		description = "Please wait - gathering serveme information."
	).add_field(
		name = "Start Time",
		value = format_dt(start, style = "t")
	).add_field(
		name = "End Time",
		value = format_dt(end, style = "t")
	).set_author(name = f"{user}", icon_url = user.display_avatar.url)
	msg = await intr.send(embed = embed) # update this message throughout the command

	async with aiohttp.ClientSession() as session:
		async with session.post(
			SERVEME_BASE_URL + "find_servers",
			json = {
				"reservation": {
					"starts_at": str(start),
					"ends_at": str(end)
				}
			},
			headers = SERVEME_API_HEADERS
		) as response: # step 2: fill in all relevent reservation details
			response.raise_for_status()
			res_info = await response.json() # filled in reservation details with other information to use

	# set up the view with 4 selects for servers, configs, whitelists, and maps
	view = await setup_view(user.id, res_info, region)

	# set up the embed
	embed.description = "**__Choose a server, config, whitelist, and map.__**"
	embed.add_field(
		name = "Server",
		value = "None Selected"
	).add_field(
		name = "Config",
		value = "None Selected"
	).add_field(
		name = "Whitelist",
		value = "None Selected"
	).add_field(
		name = "Map",
		value = "None Selected"
	)

	# wait for user responses
	msg = await msg.edit(embed = embed, view = view)
	if await view.wait(): # if the user didn't choose anything after 60 seconds, timeout and return
		embed.description = "**Session Timed Out - cancelling request**"
		embed.clear_fields()
		await msg.edit(embed = embed, view = None, delete_after = 15)
		return
	else: # move onto the next step
		embed = msg.embeds[0]
		if view.make_request: # pressed confirm button
			embed.description = "Please wait..."
			await msg.edit(embed = embed, view = None)
		else: # pressed cancel button
			embed.description = "**Session Cancelled - cancelling request**"
			embed.clear_fields()
			await msg.edit(embed = embed, view = None, delete_after = 15)
			return
		
	selects = [item for item in view.children if isinstance(item, ServemeSelect)]
	server_select = get(selects, custom_id = "server")
	config_select = get(selects, custom_id = "config")
	whitelist_select = get(selects, custom_id = "whitelist")
	map_select = get(selects, custom_id = "map")

	async with aiohttp.ClientSession() as session:
		async with session.post(
			SERVEME_BASE_URL,
			json = {
				"reservation": {
					"starts_at": str(start),
					"ends_at": str(end),
					"server_id": int(server_select.item_id), # from view server select
					"password": get_random_password(), # random password
					"rcon": get_random_password(), # random rcon
					"first_map": map_select.item_id, # from view map select
					"tv_password": "tv",
					"tv_relaypassword": "tv",
					"server_config_id": int(config_select.item_id), # from view config select
					"whitelist_id": int(whitelist_select.item_id), # from view whitelist select
					"custom_whitelist_id": None,
					"auto_end": view.autoend,
					"enable_plugins": True,
					"enable_demos_tf": True
				}
			},
			headers = SERVEME_API_HEADERS
		) as response: # step 3: create the reservation
			response.raise_for_status()
			res_info = await response.json() # final reservation details

	# post message with reservation details
	reservation_info = ReservationInfo(res_info["reservation"])
	embed.description = f"""
Successfully created reservation.

__Connect Info__
connect {reservation_info.server_ip_and_port}; password "{reservation_info.server_password}"
steam://connect/{reservation_info.server_ip_and_port}/{reservation_info.server_password}

__STV Info__
connect {reservation_info.stv_ip_and_port}; password "{reservation_info.stv_password}"
steam://connect/{reservation_info.stv_ip_and_port}/{reservation_info.stv_password}

__RCON Info__
rcon_address {reservation_info.server_ip_and_port}; rcon_password "{reservation_info.rcon_password}"

**To end the reservation prematurely, use `/serveme end {reservation_info.reservation_id}`**
"""
	await msg.edit(embed = embed) # final message
	if intr.channel_id == TF2CC.bot_commands_cid:
		await msg.pin()


class ServemeCog(Cog, name = "Serveme"):
	def __init__(self, bot: TF2CCBot):
		self.bot = bot

	@slash_command(name = "serveme")
	@has_any_role(
		TF2CC.pug_runner_rid,
		TF2CC.event_runner_rid,
		TF2CC.moderator_rid,
		TF2CC.admin_rid,
		TF2CC.owner_rid,
		"Admins" # role name in test server
	)
	async def serveme_slash(self, intr: Interaction):
		pass


	@serveme_slash.subcommand(name = "reserve", description = "Reserve an NA serveme server.", inherit_hooks = True)
	async def serveme_reserve(
		self,
		intr: Interaction,
		start_time: str = SlashOption(
			name = "start",
			description = "The time when the server should start. (must be in 24 hour form HH:MM)",
			required = False,
			min_length = 5,
			max_length = 5
		),
		tz: int = SlashOption(
			name = "timezone",
			description = "The timezone for the start time. (Default UTC-5 EST)",
			required = False,
			choices = {
				f"UTC {num}": num
				for num in range(-11, 12)
			},
			default = -5
		),
		duration: int = SlashOption(
			description = "How long to reserve the server for. (Default is 2 hours)",
			required = False,
			choices = [2, 3, 4, 5],
			default = 2
		),
		region: str = SlashOption(
			description = "The preferred region of the server. (Default is NA Central)",
			required = False,
			choices = ["NA West, NA Central, NA East"],
			default = "NA Central"
		)
	):
		await intr.response.defer()
		start = utcnow()

		# if user specified a start time, then need to adjust start
		if start_time:
			# error check start time
			# must be in the form HH:MM
			if ":" not in start_time:
				await intr.send(f"Invalid start time: `{start_time}`. Times must be in the 24 hour form HH:MM.", ephemeral = True)
				return
			hour, minute = start_time.split(":")
			if len(hour) != 2 and not hour.isdigit() and 0 <= int(hour) <= 23:
				await intr.send(f"Invalid start time: `{start_time}`. Hour must be a number between 00 and 23.", ephemeral = True)
				return
			elif len(minute) != 2 and not minute.isdigit() and 0 <= int(minute) <= 59:
				await intr.send(f"Invalid start time: `{start_time}`. Minute must be a number between 00 and 59.", ephemeral = True)
				return

			# move start according to user specified timezone
			# e.g. if using at 14:00 PST (UTC -8) then start will be 22:00 - 8:00 = 14:00
			shifted_start = start + timedelta(hours = tz)

			# since shifted_start should be in user's timezone, can easily get the start hour and start minute
			# 	e.g. start_time = 16:00
			# 	shifted_hour = 14 | shifted_minute = 0
			# 	start_hour   = 16 | start_minute   = 0
			shifted_hour, shifted_minute = shifted_start.hour, shifted_start.minute
			start_hour, start_minute = int(hour), int(minute)

			# calculate difference between user start and current (shifted) time
			# 	e.g. (16 - 14) * 3600 + (0 - 0) * 60 + (seconds)
			diff_seconds = (start_hour - shifted_hour) * 3600 + (start_minute - shifted_minute) * 60 + (0 - start.second)

			# user time must be after current time
			if diff_seconds < 0:
				await intr.send(f"Invalid start time: `{start_time}`. Start must be after the current time.", ephemeral = True)
				return

			time_offset = timedelta(seconds = diff_seconds)
			start += time_offset

		end = start + timedelta(hours = duration)

		if region == "NA West":
			pref_region = Region.NA_WEST
		elif region == "NA Central":
			pref_region = Region.NA_CENTRAL
		elif region == "NA East":
			pref_region = Region.NA_EAST
		else:
			pref_region = Region.EU

		await reserve_server(intr, start, end, pref_region)


	@serveme_slash.subcommand(name = "end", description = "End a serveme server created by this bot.", inherit_hooks = True)
	async def serveme_end(self, intr: Interaction, reservation_id: int):
		await intr.response.defer()

		async with aiohttp.ClientSession() as session:
			async with session.delete(SERVEME_BASE_URL + str(reservation_id), headers = SERVEME_API_HEADERS) as response:
				response.raise_for_status()
				if response.status == 200:
					resp = await response.json()
				elif response.status == 204:
					resp = None
				else:
					raise ValueError(f"Unknown response status: {response.status}")

		# valid response = 200 | no response = 204
		# server has been ended | server already ended
		if resp:
			embed = Embed(
				title = "Ending Reservation",
				description = f"Ending reservation with ID {reservation_id}"
			)
		else:
			embed = Embed(
				title = "Ended Reservation",
				description = f"Resevation with ID {reservation_id} has already ended."
			)
		await intr.send(embed = embed)


def setup(bot: TF2CCBot):
	bot.add_cog(ServemeCog(bot))
