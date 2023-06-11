import aiohttp, traceback
from datetime import datetime, timedelta, timezone
from nextcord import ButtonStyle, ChannelType, Color, Embed, Interaction, Member, Message, PartialInteractionMessage, PartialMessageable, Role, User, TextChannel, VoiceChannel, HTTPException
from nextcord.ext.commands import Context, CommandError
from nextcord.ui import Button, View, button
from nextcord.utils import as_chunks, format_dt, utcnow
from random import randint, shuffle
from statistics import mean, median
from typing import Iterable, Optional, Union
from bot import TF2CCBot
from staticvars import TF2CC
from classes import send_menu_pages
from .static import LOGS_API_GET_LOG, LOGS_API_GET_LOG_IDS, PUG_TABLE_VALUES, RUNNER_DB, STRIKE_TABLE_VALUES, Player, PugEmbeds, Pugger, Team
from .TF2ccDB import edit_pug_entry, edit_runner_entry, edit_strike_entry, get_all_pug_entries, get_all_strike_entries, get_pug_entry, get_runner_entry, get_strike_entry, mass_edit_pug_entries, new_pug_entry, new_runner_entry, new_strike_entry
from .CommentDB import new_comment


# warn strike unstrike pugban pugunban
# view -> strikeinfo eloinfo
# viewall -> strikeinfo, eloinfo
# set -> level steam
# toggle -> classban
# move -> newbie regular
# genteams -> newbie regular


def get_user(info: Union[Context, Interaction]) -> Optional[Union[User, Member]]:
	if isinstance(info, Context):
		return info.author
	return info.user


def get_bot(info: Union[Context, Interaction]) -> TF2CCBot:
	if isinstance(info, Context):
		return info.bot
	return info.client


def get_audit_chan(info: Union[Context, Interaction], test: bool = False) -> PartialMessageable:
	return get_bot(info).get_partial_messageable(TF2CC.pug_strike_cid if not test else 651636588073189407, type = ChannelType.text)


def get_member_level_role(roles: list[Role]) -> Role:
	level_roles = list(filter(lambda role: "level" in role.name.lower(), roles))
	level_role = level_roles[0]
	for role in level_roles[1:]:
		if role < level_role:
			level_role = role
	return level_role


async def warn(info: Union[Context, Interaction], member: Member, reason: str):
	#JBOTLOG.debug(f"pug warning {member} ({member.id})")
	if isinstance(info, Interaction): await info.response.defer(ephemeral = True)
	# send message to channels
	staff = get_user(info)
	pugembeds = PugEmbeds(
		target = member,
		staff = staff,
		type = "warn",
		reason = reason
	)
	audit = get_audit_chan(info)
	try:
		await member.send(embed = pugembeds.get_user_embed())
	except:
		get_bot(info).log.warn(f"Could not send pug warning message to {member} ({member.id})")
	await audit.send(embed = pugembeds.get_record_embed())
	embed = Embed(description = f"Sent a pug warning to {member.mention} with reason `{reason}`")
	await info.send(embed = embed)

	# add comment to member
	await new_comment(
		user = member,
		guild_id = info.guild.id,
		staff_id = staff.id,
		comment = f"""{staff.mention} sent a Pug Warning to {member.mention}
Reason: {reason}"""
	)


async def strike(info: Union[Context, Interaction], member: Member, reason: str):
	#JBOTLOG.debug(f"pug striking {member} ({member.id})")
	if isinstance(info, Interaction): await info.response.defer(ephemeral = True)
	# update strike count in database
	await new_strike_entry(user = member)
	strike_info = await get_strike_entry(member.id)
	
	# if user is already pug banned, then don't do anything
	if strike_info.strike_count >= 3 or strike_info.permanent_ban:
		if isinstance(info, Interaction):
			await info.send(f"{member.mention} is already pug banned.", ephemeral = True)
		return

	strike_count = min(strike_info.strike_count + 1, 3)
	total_strike_count = strike_info.total_strike_count + 1
	payload = {
		STRIKE_TABLE_VALUES[1]: strike_count, # strike count
		STRIKE_TABLE_VALUES[2]: total_strike_count, # total strike count
		STRIKE_TABLE_VALUES[3]: int((utcnow() + timedelta(days = TF2CC.first_strike_duration)).timestamp()) if strike_count and total_strike_count == 1 else 0,
		STRIKE_TABLE_VALUES[4]: int((utcnow() + timedelta(days = TF2CC.strike2_duration)).timestamp()) if strike_count == 2 else 0,
		STRIKE_TABLE_VALUES[5]: 1 if strike_count > 0 else 0, # strike 1
		STRIKE_TABLE_VALUES[6]: 1 if strike_count > 1 else 0, # strike2
		STRIKE_TABLE_VALUES[7]: 1 if strike_count >= 2 else 0, # pug ban
		STRIKE_TABLE_VALUES[8]: 1 if strike_count > 2 else 0 # permanent pug ban
	}
	await edit_strike_entry(member.id, **payload)

	# add roles to user
	roles_to_add: list[Role] = []
	if strike_count:
		roles_to_add.append(info.guild.get_role(TF2CC.pug_strike1_rid)) # add strike 1 if strike count > 0
	if strike_count > 1:
		roles_to_add.append(info.guild.get_role(TF2CC.pug_strike2_rid)) # add strike 2 if strike count > 1
	if strike_count >= 2:
		roles_to_add.append(info.guild.get_role(TF2CC.pug_strike3_rid)) # add pug ban if strike count >= 2
	await member.add_roles(*roles_to_add, reason = "Received a pug strike via command", atomic = False)

	# send message to channels
	staff = get_user(info)
	pugembeds = PugEmbeds(
		target = member,
		staff = staff,
		type = "strike",
		reason = reason,
		strike_count = payload[STRIKE_TABLE_VALUES[1]],
		total_strike_count = payload[STRIKE_TABLE_VALUES[2]]
	)
	audit = get_audit_chan(info)
	try:
		await member.send(embed = pugembeds.get_user_embed())
	except:
		get_bot(info).log.warn(f"Could not send pug strike message to {member} ({member.id})")
	await audit.send(embed = pugembeds.get_record_embed())
	embed = Embed(description = f"Gave a pug strike to {member.mention} with reason `{reason}`")
	await info.send(embed = embed)

	# add comment to member
	await new_comment(
		user = member,
		guild_id = info.guild.id,
		staff_id = staff.id,
		comment = f"""{staff.mention} gave a Pug Strike to {member.mention}
Reason: {reason}"""
	)


async def unstrike(info: Union[Context, Interaction], member: Member, reason: str):
	#JBOTLOG.debug(f"pug unstriking {member} ({member.id})")
	if isinstance(info, Interaction): await info.response.defer(ephemeral = True)
	# update strike count in database
	await new_strike_entry(user = member)
	strike_info = await get_strike_entry(member.id)

	# if user doesn't have any pug strikes, then don't do anything
	if strike_info.strike_count <= 0:
		if isinstance(info, Interaction):
			await info.send(f"{member.mention} does not have any pug strikes.", ephemeral = True)
		return

	strike_count = max(strike_info.strike_count - 1, 0)
	total_strike_count = max(strike_info.total_strike_count - 1, 0)
	payload = {
		STRIKE_TABLE_VALUES[1]: strike_count, # strike count
		STRIKE_TABLE_VALUES[2]: total_strike_count, # total strike count
		STRIKE_TABLE_VALUES[5]: 1 if strike_count > 0 else 0, # strike 1
		STRIKE_TABLE_VALUES[6]: 1 if strike_count > 1 else 0, # strike 2
		STRIKE_TABLE_VALUES[7]: 0, # pug ban
		STRIKE_TABLE_VALUES[8]: 0 # permanent pug ban
	}
	await edit_strike_entry(member.id, **payload)

	# add roles to user
	# always remove pug ban role
	roles_to_remove: list[Role] = [info.guild.get_role(TF2CC.pug_strike3_rid)]
	if strike_count < 1:
		# removed the first strike
		roles_to_remove.append(info.guild.get_role(TF2CC.pug_strike1_rid))
	if strike_count < 2:
		# removed the second strike
		roles_to_remove.append(info.guild.get_role(TF2CC.pug_strike2_rid))

	await member.remove_roles(*roles_to_remove, reason = "Removing a pug strike via command", atomic = False)

	# send message to channels
	staff = get_user(info)
	pugembeds = PugEmbeds(
		target = member,
		staff = staff,
		type = "unstrike",
		reason = reason,
		strike_count = payload[STRIKE_TABLE_VALUES[1]]
	)
	audit = get_audit_chan(info)
	try:
		await member.send(embed = pugembeds.get_user_embed())
	except:
		get_bot(info).log.warn(f"Could not send pug unstrike message to {member} ({member.id})")
	await audit.send(embed = pugembeds.get_record_embed())
	embed = Embed(description = f"Removed a pug strike from {member.mention} with reason `{reason}`")
	await info.send(embed = embed)

	# add comment to member
	await new_comment(
		user = member,
		guild_id = info.guild.id,
		staff_id = staff.id,
		comment = f"""{staff.mention} removed a Pug Strike from {member.mention}
Reason: {reason}"""
	)


async def pugban(info: Union[Context, Interaction], member: Member, reason: str):
	#JBOTLOG.debug(f"pug banning {member} ({member.id})")
	if isinstance(info, Interaction): await info.response.defer(ephemeral = True)
	# update strike info in database
	await new_strike_entry(user = member)
	strike_info = await get_strike_entry(member.id)

	# if user is already pug banned, then don't do anything
	if strike_info.permanent_ban:
		if isinstance(info, Interaction):
			await info.send(f"{member.mention} is already pug banned.", ephemeral = True)
		return

	payload = {
		STRIKE_TABLE_VALUES[7]: 1, # pug ban
		STRIKE_TABLE_VALUES[8]: 1 # permanent pug ban
	}
	await edit_strike_entry(member.id, **payload)

	# edit roles for user
	pug_ban_role = info.guild.get_role(TF2CC.pug_strike3_rid)
	if not pug_ban_role:
		raise Exception("Could not find TF2CC Pug Ban role.")

	member_roles = member.roles
	for role_id in (TF2CC.level0_rid, TF2CC.level1_rid, TF2CC.level2_rid, TF2CC.level3_rid, TF2CC.pug_rid):
		role = member.get_role(role_id)
		if not role:
			continue
		member_roles.remove(role)
	member_roles.append(pug_ban_role)
	await member.edit(roles = member_roles, reason = "Immediate pug ban via command")

	# send message to channels
	staff = get_user(info)
	pugembeds = PugEmbeds(
		target = member,
		staff = staff,
		type = "pugban",
		reason = reason
	)
	audit = get_audit_chan(info)
	try:
		await member.send(embed = pugembeds.get_user_embed())
	except:
		get_bot(info).log.warn(f"Could not send pug ban message to {member} ({member.id})")
	await audit.send(embed = pugembeds.get_record_embed())
	embed = Embed(description = f"Gave a pug ban to {member.mention} with reason `{reason}`")
	await info.send(embed = embed)

	# add comment to member
	await new_comment(
		user = member,
		guild_id = info.guild.id,
		staff_id = staff.id,
		comment = f"""{staff.mention} gave a Pug Ban to {member.mention}
Reason: {reason}"""
	)


async def pugunban(info: Union[Context, Interaction], member: Member, reason: str):
	#JBOTLOG.debug(f"pug unbanning {member} ({member.id})")
	if isinstance(info, Interaction): await info.response.defer(ephemeral = True)
	# update strike info in database
	await new_strike_entry(user = member)
	strike_info = await get_strike_entry(member.id)

	# if user is not pug banned, then don't do anything
	if not strike_info.permanent_ban and not strike_info.pugban:
		if isinstance(info, Interaction):
			await info.send(f"{member.mention} does not have a pug ban.", ephemeral = True)
		return

	payload = {
		STRIKE_TABLE_VALUES[1]: 2 if strike_info.strike_count >= 3 else strike_info.strike_count, # strike count
		STRIKE_TABLE_VALUES[4]: 0, # temp ban duration
		STRIKE_TABLE_VALUES[7]: 0, # pug ban
		STRIKE_TABLE_VALUES[8]: 0 # permanent pug ban
	}
	await edit_strike_entry(member.id, **payload)

	# add roles to user
	await member.remove_roles(info.guild.get_role(TF2CC.pug_strike3_rid), reason = "Immediate pug unban via command", atomic = False)

	# send message to channels
	staff = get_user(info)
	pugembeds = PugEmbeds(
		target = member,
		staff = staff,
		type = "pugunban",
		reason = reason
	)
	audit = get_audit_chan(info)
	try:
		await member.send(embed = pugembeds.get_user_embed())
	except:
		get_bot(info).log.warn(f"Could not send pug unban message to {member} ({member.id})")
	await audit.send(embed = pugembeds.get_record_embed())
	embed = Embed(description = f"Removed a pug ban from {member.mention} with reason `{reason}`")
	await info.send(embed = embed)

	# add comment to member
	await new_comment(
		user = member,
		guild_id = info.guild.id,
		staff_id = staff.id,
		comment = f"""{staff.mention} removed Pug Ban from {member.mention}
Reason: {reason}"""
	)


async def strikeinfo(info: Union[Context, Interaction], member: Member):
	strike_info = await get_strike_entry(member.id)
	if not strike_info:
		embed = Embed(description = f"{member.mention} does not have any strikes on record.")
		await info.send(embed = embed)
		return

	embed = Embed(
		description = member.mention,
		timestamp = utcnow()
	).set_thumbnail(
		url = member.display_avatar.url
	).add_field(
		name = "Current Strike Count",
		value = strike_info.strike_count
	).add_field(
		name = "Total Strike Count",
		value = strike_info.total_strike_count
	).add_field(
		name = "Currently Pug Banned",
		value = "Yes" if strike_info.pugban or strike_info.permanent_ban else "No"
	)
	if strike_info.total_strike_count == 1 and strike_info.strike1:
		embed.add_field(
			name = "First Strike Duration",
			value = format_dt(datetime.fromtimestamp(strike_info.first_strike_duration, tz = timezone.utc))
		)
	if strike_info.strike_count == 2 and strike_info.pugban and not strike_info.permanent_ban:
		embed.add_field(
			name = "Temp Ban Duration",
			value = format_dt(datetime.fromtimestamp(strike_info.second_strike_duration, tz = timezone.utc))
		)
	await info.send(embed = embed)


async def puginfo(info: Union[Context, Interaction], member: Member, newbie: bool):
	await new_pug_entry(user = member)
	pug_info = await get_pug_entry(member.id)
	level_role = get_member_level_role(member.roles)
	embed = Embed(
		description = member.mention,
		timestamp = utcnow(),
		color = Color.from_rgb(255, 255, 255)
	).set_thumbnail(
		url = member.display_avatar.url
	).add_field(
		name = "Level Role",
		value = level_role.mention if level_role else "None"
	).add_field(
		name = "Win Count",
		value = pug_info.win_count if not newbie else pug_info.newbie_win_count
	).add_field(
		name = "Lose Count",
		value = pug_info.lose_count if not newbie else pug_info.newbie_lose_count
	).add_field(
		name = "Tie Count",
		value = pug_info.tie_count if not newbie else pug_info.newbie_tie_count
	).add_field(
		name = "Elo",
		value = pug_info.elo if not newbie else pug_info.newbie_elo
	).add_field(
		name = "Class Restrictions",
		value = " ".join([TF2CC.class_emojis.get(class_num) for class_num in pug_info.class_bans]) if pug_info.class_bans else "None"
	).add_field(
		name = "Steam ID",
		value = pug_info.steam_id
	).add_field(
		name = "Last Active",
		value = pug_info.last_active
	)
	await info.send(embed = embed)


async def runnerinfo(info: Union[Context, Interaction], member: Member):
	runner_info = await get_runner_entry(member.id)
	assert runner_info is not None, f"{str(member)} is not a Pug Runner."
	embed = Embed(
		description = f"""
{member.mention}
**Became Pug Runner** - {format_dt(runner_info.became_runner_datetime) if runner_info.became_runner else "Unknown"}
**Currently Pug Runner** - {member.get_role(TF2CC.pug_runner_rid) is not None}

**\# of Newbie Pugs Ran** - `{runner_info.npugs}`
**Last Ran Newbie Pugs** - {format_dt(runner_info.npugs_datetime) if runner_info.npugs_last_ran else "Never"}

**\# of Regular Pugs Ran** - `{runner_info.rpugs}`
**Last Ran Regular Pugs** - {format_dt(runner_info.rpugs_datetime) if runner_info.rpugs_last_ran else "Never"}
""",
		timestamp = utcnow()
	).set_thumbnail(
		url = member.display_avatar.url
	)
	await info.send(embed = embed)


async def allstrikeinfo(info: Union[Context, Interaction]):
	entries = await get_all_strike_entries(conditional = "WHERE strike_count > 0 OR pugban > 0 OR permanent_ban > 0")
	if not len(entries):
		await info.send("There are no strike entries.")
		return
	entries.sort(key = lambda entry: (entry.permanent_ban, entry.pugban, entry.strike_count, entry.discord_id))

	data: list[tuple[str, str]] = list()
	for strike_info in entries:
		member = info.guild.get_member(strike_info.discord_id)
		if not member:
			continue

		name = str(member)
		value = f"""{member.mention}
Strike Count: {strike_info.strike_count}
Pug Ban: {bool(strike_info.pugban)}
Permanent Pug Ban: {bool(strike_info.permanent_ban)}"""
		if strike_info.total_strike_count == 1 and strike_info.strike1:
			value += f"\nFirst Strike Removed: {format_dt(datetime.fromtimestamp(strike_info.first_strike_duration, tz = timezone.utc), style = 'R')}"
		if strike_info.strike_count == 2 and strike_info.pugban and not strike_info.permanent_ban:
			value += f"\nTemp Ban Removed: {format_dt(datetime.fromtimestamp(strike_info.second_strike_duration, tz = timezone.utc), style = 'R')}"
		data.append((name, value))

	await send_menu_pages(
		data = data,
		info_obj = info,
		amnt_per_page = 9,
		embed_title = "List of All TF2CC Strikes"
	)


async def allpuginfo(info: Union[Context, Interaction], newbie: bool):
	entries = await get_all_pug_entries(conditional = f"""
WHERE 
	{PUG_TABLE_VALUES[1 if not newbie else 8]} > 0 OR 
	{PUG_TABLE_VALUES[2 if not newbie else 9]} > 0 
ORDER BY {PUG_TABLE_VALUES[4 if not newbie else 11]} DESC""")
	if len(entries) == 0:
		await info.send("There are no pug entries.")
		return

	data: list[tuple[str, str]] = list()
	for pug_info in entries:
		member = info.guild.get_member(pug_info.discord_id)
		if not member:
			continue
		role = get_member_level_role(member.roles)
		data.append((
			str(member),
			f"""{member.mention}
Level Role: {role.mention if role else "None"}
Win Count: {pug_info.win_count if not newbie else pug_info.newbie_win_count}
Lose Count: {pug_info.lose_count if not newbie else pug_info.newbie_lose_count}
Tie Count: {pug_info.tie_count if not newbie else pug_info.newbie_tie_count}
Elo: {pug_info.elo if not newbie else pug_info.newbie_elo}
Restrictions: {" ".join([TF2CC.class_emojis.get(class_num) for class_num in pug_info.class_bans]) if pug_info.class_bans else "None"}"""
		))

	await send_menu_pages(
		data = data,
		info_obj = info,
		amnt_per_page = 9,
		embed_title = "Top TF2CC Puggers",
		embed_color = Color.from_rgb(255, 255, 255)
	)


async def setlevel(info: Union[Context, Interaction], member: Member, level_role: Role):
	# remove other level roles
	roles_to_remove: list[Role] = []
	for role_id in (TF2CC.level0_rid, TF2CC.level1_rid, TF2CC.level2_rid, TF2CC.level3_rid):
		if role_id == level_role.id:
			continue
		role = member.get_role(role_id)
		if not role:
			continue
		roles_to_remove.append(role)
	new_roles = [role for role in member.roles if role not in roles_to_remove]
	new_roles.append(level_role)
	#new_roles.sort()

	# await member.remove_roles(*roles_to_remove, reason = "Changing level role via command")
	# if not member.get_role(level_role.id):
	# 	await member.add_roles(level_role, reason = "Changing level role via command")
	# removed at least one level role, so update member roles
	if roles_to_remove:
		await member.edit(roles = new_roles, reason = "Changing level role via command")

	embed = Embed(description = f"Set {member.mention} to {level_role.mention}.")
	await info.send(embed = embed)

	# add comment to member
	staff = get_user(info)
	await new_comment(
		user = member,
		guild_id = info.guild.id,
		staff_id = staff.id,
		comment = f"{staff.mention} updated the level role for {member.mention}\nSet level role to {level_role.mention}"
	)


async def setsteam(info: Union[Context, Interaction], member: Member, steamid: int):
	await new_pug_entry(user = member)
	payload = {
		PUG_TABLE_VALUES[6]: steamid
	}
	await edit_pug_entry(member.id, **payload)
	steam_linked_role = info.guild.get_role(TF2CC.steam_linked_rid)
	if not steam_linked_role:
		embed = Embed(description = "Could not find the `Steam Linked` role.")
		await info.send(embed = embed)
		return

	await member.add_roles(steam_linked_role, reason = "Linked Steam account via command", atomic = False)
	embed = Embed(description = f"Linked {member.mention} with Steam account <https://steamcommunity.com/profiles/{steamid}>")
	await info.send(embed = embed)


async def toggleclassban(info: Union[Context, Interaction], member: Member, classban_role: Role):
	if member.get_role(classban_role.id):
		await member.remove_roles(classban_role, reason = "Toggling class ban role via command", atomic = False)
		title = "Classban Removed"
	else:
		await member.add_roles(classban_role, reason = "Toggling class ban role via command", atomic = False)
		title = "Classban Added"

	embed = Embed(
		title = title,
		description = f"Toggled {classban_role.mention} for {member.mention}"
	)
	await info.send(embed = embed)

	# add comment to member
	staff = get_user(info)
	await new_comment(
		user = member,
		guild_id = info.guild.id,
		staff_id = staff.id,
		comment = f"""{staff.mention} updated the class bans for {member.mention}
{title[len("Classban "):]} {classban_role.mention}"""
	)


async def move_to_vc(members: Iterable[Member], vc: VoiceChannel, reason: str = None):
	for member in members:
		try:
			await member.move_to(vc, reason = reason)
		except HTTPException:
			pass


async def get_log(steam_id: int) -> Optional[int]:
	# get most recent log from steam_id
	async with aiohttp.ClientSession() as client:
		async with client.get(LOGS_API_GET_LOG_IDS.format(steam_ids = steam_id), ssl = False) as resp:
			resp.raise_for_status()
			log_dict: dict = await resp.json()
	# get the log list
	log_list: list[dict] = log_dict.get("logs", list())
	if not len(log_list):
		return None
	# get the log
	log = log_list[0]
	# if more than 5 minutes passed, then wrong log
	cur_time = utcnow()
	log_time = datetime.fromtimestamp(log.get("date", 0), tz = timezone.utc)
	if (cur_time - log_time).total_seconds() > 5 * 60:
		return None
	# possibly correct log otherwise
	return log.get("id", None)


async def get_log_info(log_id: int) -> dict:
	async with aiohttp.ClientSession() as client:
		async with client.get(LOGS_API_GET_LOG.format(log_id = log_id), ssl = False) as resp:
			resp.raise_for_status()
			return await resp.json()


class LogInfo:
	def __init__(self, log: dict[str, Union[dict, int]], newbie = False):
		self.newbie = newbie
		self.blue_team = Team("blue", log["teams"]["Blue"])
		self.red_team = Team("red", log["teams"]["Red"])
		self._add_players_to_team(log)
		self.length: int = log["length"]
		self.total_rounds: int = self.blue_team.score + self.red_team.score
		if self.total_rounds == 0:
			self.total_rounds = 1

	def __str__(self):
		return f"""
		~~~ LOG INFO ~~~
		Red Rounds: {self.red_team.score} | {self.red_team_won}
		Blu Rounds: {self.blue_team.score} | {self.blu_team_won}
		Match Length: {self.length}
		~~~~~~~~~~~~~~~~
		"""

	@property
	def red_team_won(self):
		return self.red_team.score > self.blue_team.score

	@property
	def blu_team_won(self):
		return self.red_team.score < self.blue_team.score

	@property
	def teams_tied(self):
		return self.red_team.score == self.blue_team.score

	def _add_players_to_team(self, log: dict):
		players: dict[str, dict] = log["players"]
		for player_id, player_info in players.items():
			player_team_name: str = player_info.get("team", None)
			if player_team_name is None:
				continue
			player = Player(
				int(player_id[5:-1]),
				player_info,
				self.newbie
			)
			if player_team_name.lower() == self.red_team.name:
				self.red_team.add_player(player)
			elif player_team_name.lower() == self.blue_team.name:
				self.blue_team.add_player(player)

	def add_members_to_teams(self, puggers: Iterable[Pugger]):
		for pugger in puggers:
			player = self.red_team.get_player(pugger.steam_id) or self.blue_team.get_player(pugger.steam_id)
			if player is None:
				continue
			player.member = pugger.member
			player.pug_info = pugger.pug_info

	def _probability(self, team1_avg_elo: float, team2_avg_elo: float) -> float:
		# probability that team2 would win against team1
		return 1 / (1 + pow(10, (team1_avg_elo - team2_avg_elo) / 300))

	async def update_players_elo(self):
		red_elo_change, blu_elo_change = self.get_team_elo_changes(self.red_team.avg_elo, self.blue_team.avg_elo)

		for player in self.red_team.players:
			if player.member is None:
				continue
			await edit_pug_entry(
				user = player.member,
				win_count = player.win_count + 1 if self.red_team_won else player.win_count,
				lose_count = player.lose_count + 1 if self.blu_team_won else player.lose_count,
				elo = player.elo + red_elo_change
			)

		for player in self.blue_team.players:
			if player.member is None:
				continue
			await edit_pug_entry(
				user = player.member,
				win_count = player.win_count + 1 if self.blu_team_won else player.win_count,
				lose_count = player.lose_count + 1 if self.red_team_won else player.lose_count,
				elo = player.elo + blu_elo_change
			)

	async def get_team_elo_changes(self, avg_red_elo: float, avg_blu_elo: float) -> tuple[int, int]:
		base_elo_change = 40
		red_rounds_ratio = self.red_team.score / self.total_rounds
		blu_rounds_ratio = self.blue_team.score / self.total_rounds
		red_team_prob = self._probability(avg_blu_elo, avg_red_elo)
		blu_team_prob = self._probability(avg_red_elo, avg_blu_elo)
		#f"red_rounds_ratio: {red_rounds_ratio}")
		#LOG.debug(f"blu_rounds_ratio: {blu_rounds_ratio}")
		#LOG.debug(f"red_team_prob: {red_team_prob}")
		#LOG.debug(f"blu_team_prob: {blu_team_prob}")

		if self.length < 15 * 60 and (red_rounds_ratio == 0 or blu_rounds_ratio == 0):
			base_elo_change *= 1.2
		#LOG.debug(f"base_elo_change: {base_elo_change}")

		return (
			int(base_elo_change * (red_rounds_ratio - red_team_prob)),
			int(base_elo_change * (blu_rounds_ratio - blu_team_prob))
		)


async def move_elo_change(red_members: Iterable[Member], blu_members: Iterable[Member], log_channel: TextChannel, newbie: bool):
	red_team: list[Pugger] = list()
	blu_team: list[Pugger] = list()
	# get pug info -> make Pugger objects for both teams
	# the channels may contain different amount of members, so need two loops
	for member in red_members:
		pug_info = await get_pug_entry(member.id)
		if not pug_info:
			await new_pug_entry(user = member)
			pug_info = await get_pug_entry(member.id)
		red_team.append(Pugger(member, pug_info = pug_info))
	for member in blu_members:
		pug_info = await get_pug_entry(member.id)
		if not pug_info:
			await new_pug_entry(user = member)
			pug_info = await get_pug_entry(member.id)
		blu_team.append(Pugger(member, pug_info = pug_info))

	# get all steam ids from puggers
	steam_ids = [pugger.steam_id for pugger in red_team + blu_team if pugger.steam_id]
	if not len(steam_ids):
		return

	# get log based on one steam_id
	log_id = None
	for steam_id in steam_ids:
		log_id = await get_log(steam_id)
		if log_id: break
	if not log_id:
		return

	# send log to channel
	if log_channel:
		await log_channel.send(f"https://logs.tf/{log_id}")

	# get the log info
	log = await get_log_info(log_id)
	log_info = LogInfo(log, newbie)

	# calculate elo change value
	# the teams may contain different amount of members, so need two loops
	red_elo = list()
	blu_elo = list()
	for red_pugger in red_team:
		red_elo.append(red_pugger.newbie_elo if newbie else red_pugger.elo)
	for blu_pugger in blu_team:
		blu_elo.append(blu_pugger.newbie_elo if newbie else blu_pugger.elo)

	# if nothing found, return
	if not red_elo or not blu_elo:
		return

	red_elo_change, blu_elo_change = await log_info.get_team_elo_changes(
		mean(red_elo),
		mean(blu_elo)
	)

	# set up for mass edit in DB
	key_names = (
		PUG_TABLE_VALUES[1 if not newbie else 8], # win count
		PUG_TABLE_VALUES[2 if not newbie else 9], # lose count
		PUG_TABLE_VALUES[3 if not newbie else 10], # tie count
		PUG_TABLE_VALUES[4 if not newbie else 11], # elo
		PUG_TABLE_VALUES[0] # discord id
	)

	# get the new values to enter into the DB
	# the teams may contain different amount of members, so need two loops
	key_vals = list()
	for red_pugger in red_team:
		key_vals.append((
			(red_pugger.newbie_win_count if newbie else red_pugger.win_count) + (1 if log_info.red_team_won else 0), # win count
			(red_pugger.newbie_lose_count if newbie else red_pugger.lose_count) + (1 if log_info.blu_team_won else 0), # lose count
			(red_pugger.newbie_tie_count if newbie else red_pugger.tie_count) + (1 if log_info.teams_tied else 0), # tie count
			(red_pugger.newbie_elo if newbie else red_pugger.elo) + red_elo_change, # elo
			red_pugger.discord_id # discord_id
		))
	for blu_pugger in blu_team:
		key_vals.append((
			(blu_pugger.newbie_win_count if newbie else blu_pugger.win_count) + (1 if log_info.blu_team_won else 0), # win count
			(blu_pugger.newbie_lose_count if newbie else blu_pugger.lose_count) + (1 if log_info.red_team_won else 0), # lose count
			(blu_pugger.newbie_tie_count if newbie else blu_pugger.tie_count) + (1 if log_info.teams_tied else 0), # tie count
			(blu_pugger.newbie_elo if newbie else blu_pugger.elo) + blu_elo_change, # elo
			blu_pugger.discord_id # discord_id
		))

	# update elo values
	await mass_edit_pug_entries(key_names, tuple(key_vals))


class UndoMovePuggersView(View):
	def __init__(self, red_members: Iterable[Member], blu_members: Iterable[Member], red_team: VoiceChannel, blu_team: VoiceChannel, *, timeout = 30):
		super().__init__(timeout = timeout)
		self.red_members = red_members
		self.blu_members = blu_members
		self.red_team = red_team
		self.blu_team = blu_team
		self.msg: Union[Message, PartialInteractionMessage] = None

	async def on_timeout(self) -> None:
		if self.msg:
			await self.msg.edit(view = None, delete_after = 10)

	async def interaction_check(self, interaction: Interaction) -> bool:
		return any([
			interaction.user.get_role(TF2CC.pug_runner_rid),
			interaction.user.get_role(TF2CC.moderator_rid),
			interaction.user.get_role(TF2CC.admin_rid),
			interaction.user.get_role(TF2CC.owner_rid)
		])

	@button(label = "Move Them Back", emoji = "🔄", style = ButtonStyle.grey)
	async def move_back_to_teams(self, button: Button, interaction: Interaction):
		embed = interaction.message.embeds[0]
		embed.description = f"Moving members back to their teams."
		await interaction.edit(embed = embed, view = None)
		self.stop()
		# move members back to their teams
		await move_to_vc(self.red_members, self.red_team, "Undo move command")
		await move_to_vc(self.blu_members, self.blu_team, "Undo move command")
		await interaction.edit(delete_after = 10)

	@button(label = "Close", emoji = "⛔", style = ButtonStyle.red)
	async def close_button(self, button: Button, interaction: Interaction):
		await interaction.edit(view = None, delete_after = 10)
		self.stop()


class MovePuggersView(View):
	def __init__(self, next_game: VoiceChannel, waiting: VoiceChannel, red_team: VoiceChannel, blu_team: VoiceChannel, log_channel: TextChannel, newbie: bool, *, timeout = 120):
		super().__init__(timeout = timeout)
		self.next_game = next_game
		self.waiting = waiting
		self.red_team = red_team
		self.blu_team = blu_team
		self.log_channel = log_channel
		self.newbie = newbie

	async def on_error(self, error: Exception, item: Button, interaction: Interaction):
		# send to audit channel first
		embed = Embed(
			title = "Move Error",
			description = "```" + "".join(traceback.format_exception(type(error), error, error.__traceback__)) + "```",
			timestamp = utcnow()
		)
		audit = get_audit_chan(interaction, True)
		
		await audit.send(embed = embed)
		# then send error to interaction channel
		embed.description = f"{item.label}\n{type(error)} - {error}"
		await interaction.channel.send(embed = embed)

	async def interaction_check(self, interaction: Interaction) -> bool:
		return any([
			interaction.user.get_role(TF2CC.pug_runner_rid),
			interaction.user.get_role(TF2CC.moderator_rid),
			interaction.user.get_role(TF2CC.admin_rid),
			interaction.user.get_role(TF2CC.owner_rid)
		])

	@button(emoji = "✅", style = ButtonStyle.green)
	async def yes_move(self, button: Button, interaction: Interaction):
		embed = interaction.message.embeds[0]
		embed.description = f"Moving members from {self.waiting.mention} to {self.next_game.mention}."
		await interaction.edit(view = None)
		self.stop()

		# save a copy of the members before moving incase undo
		red_members = self.red_team.members[:]
		blu_members = self.blu_team.members[:]

		# move members from waiting to next game
		if len(self.waiting.members) > 0:
			await interaction.edit(embed = embed)
			await move_to_vc(self.waiting.members, self.next_game, "Moving members to next game vc")

		# move members from red team to waiting
		embed.description += f"\nDone.\n\nMoving members from {self.red_team.mention} to {self.waiting.mention}."
		await interaction.edit(embed = embed)
		await move_to_vc(self.red_team.members, self.waiting, "Moving members to waiting vc")

		# move members from blu team to waiting
		embed.description += f"\nDone.\n\nMoving members from {self.blu_team.mention} to {self.waiting.mention}."
		await interaction.edit(embed = embed)
		await move_to_vc(self.blu_team.members, self.waiting, "Moving members to waiting vc")

		# finished moving. offer an undo
		embed.description += "\nDone."
		undo_view = UndoMovePuggersView(red_members, blu_members, self.red_team, self.blu_team)
		undo_view.msg = interaction.message
		await interaction.edit(embed = embed, view = undo_view)

		# wait for undo to timeout or close
		# get log if amnt of puggers >4
		if len(red_members + blu_members) < 4:
			return

		# update elo for participants
		await move_elo_change(red_members, blu_members, self.log_channel, self.newbie)


	@button(emoji = "⛔", style = ButtonStyle.red)
	async def no_move(self, button: Button, interaction: Interaction):
		await interaction.edit(view = None, delete_after = 10)
		self.stop()


async def movepuggers(info: Union[Context, Interaction], team_vcs: tuple[VoiceChannel], waiting_vc: VoiceChannel, next_game_vc: VoiceChannel, logs_chan: TextChannel, newbie: bool):
	red_team = team_vcs[0]
	blu_team = team_vcs[1]
	embed = Embed(
		title = "Moving Members",
		description = f"Are you sure? This will move members from {red_team.mention} and {blu_team.mention} to {waiting_vc.mention}"
	)
	await info.send(embed = embed, view = MovePuggersView(next_game_vc, waiting_vc, red_team, blu_team, logs_chan, newbie))


def genteams_exchange_medlocked(med_locked: list[Pugger], final_list: list[Pugger], pool: list[Pugger], newbie: bool):
	# removes players from the pool and exchanges them in place on the final list
	# raise error if there is no one in the pool
	if not len(pool):
		raise CommandError("Could not generate teams. There are too many med locked players.")

	# get a random med locked pugger
	med_locked_pugger = med_locked.pop(randint(0, len(med_locked) - 1))

	# find a replacement in the pool
	closest: Pugger = None
	smallest_elo_diff: int = 10000
	for pugger in pool:
		# skip if medlocked
		if pugger.medlocked:
			continue

		elo_diff = abs(med_locked_pugger.elo if not newbie else med_locked_pugger.newbie_elo)
		if elo_diff < smallest_elo_diff:
			closest = pugger
			smallest_elo_diff = elo_diff

	# raise error if no replacement is found
	if not closest:
		raise CommandError("Could not generate teams. Could not find a replacement for a med locked player.")

	# make the exchange inplace
	exchange_pugger = pool.pop(pool.index(closest))
	final_list[final_list.index(med_locked_pugger)] = exchange_pugger
	#pool.append(med_locked_pugger)


def genteams_random_team_algo(puggers: Iterable[Pugger], amnt_per_team: int, newbie: bool) -> tuple[tuple[Pugger]]:
	# generate two teams of the given size if possible
	final_list: list[Pugger] = puggers[:amnt_per_team * 2] # get first 12 puggers
	pool: list[Pugger] = puggers[amnt_per_team * 2:] # the remaining if any

	# check for >2 med locked players
	med_locked = [pugger for pugger in final_list if pugger.medlocked]
	while len(med_locked) > 2: genteams_exchange_medlocked(med_locked, final_list, pool, newbie)

	# remove the 2 med locked players from the list
	if len(med_locked) == 2:
		final_list.remove(med_locked[0])
		final_list.remove(med_locked[1])

	# shuffle the puggers
	final: list[Pugger] = list()
	for i in range(4): # for level 0, 1, 2, 3
		temp = [pugger for pugger in final_list if pugger.int_level == i]
		shuffle(temp)
		final.extend(temp)

	# add on the med locked players
	if len(med_locked) == 2:
		shuffle(med_locked)
		final.extend(med_locked)

	# teams are created in ABBA BAAB order
	team1: list[Pugger] = list()
	team2: list[Pugger] = list()
	iteration = 0
	chunk: list[Pugger]
	for chunk in as_chunks(final, 4): # possible team sizes - 2, 3, 4, 5, 6, 7, 8, 9
		iteration += 1
		if len(chunk) == 2: # uneven team size - these are the left overs
			shuffle(chunk)
			team1.append(chunk[0])
			team2.append(chunk[1])

		elif iteration % 2:
			# ABBA
			if len(chunk) == 4:
				team1.append(chunk[0])
				team2.append(chunk[1])
				team2.append(chunk[2])
				team1.append(chunk[3])

		else:
			# BAAB
			if len(chunk) == 4:
				team2.append(chunk[0])
				team1.append(chunk[1])
				team1.append(chunk[2])
				team2.append(chunk[3])

	return (tuple(team1), tuple(team2))


async def genteams_setup(next_game: VoiceChannel, waiting_room: VoiceChannel, amnt_per_team: int, newbie: bool) -> tuple[tuple[Pugger]]:
	# generate teams
	all_puggers: list[Pugger] = list()
	pug_banned: list[Member] = list()
	for member in next_game.members + waiting_room.members:
		# if member is pug banned, skip
		if member.get_role(TF2CC.pug_strike3_rid):
			pug_banned.append(member)
			continue

		# make and get pug entry
		await new_pug_entry(user = member)
		pug_info = await get_pug_entry(member.id)
		all_puggers.append(
			Pugger(
				member,
				priority = member in next_game.members,
				pug_info = pug_info,
				newbie = newbie
			)
		)

	if len(all_puggers) < amnt_per_team:
		error = f"Not enough people in pug voice channels: `{len(all_puggers)} / {amnt_per_team * 2}` people."
		if len(pug_banned):
			error += "\n" + ", ".join([member.mention for member in pug_banned]) + f" {'is' if len(pug_banned) == 1 else 'are'} Pug Banned."
		raise ValueError(error)

	priority = [pugger for pugger in all_puggers if pugger.priority]
	regular = [pugger for pugger in all_puggers if not pugger.priority]
	return genteams_random_team_algo(priority + regular, amnt_per_team, newbie)


def genteams_embed(team1: Iterable[Pugger], team2: Iterable[Pugger], newbie: bool) -> Embed:
	red_elo: list[int] = list()
	blu_elo: list[int] = list()
	for red_pugger, blu_pugger in zip(team1, team2):
		red_elo.append(red_pugger.elo if not newbie else red_pugger.newbie_elo)
		blu_elo.append(blu_pugger.elo if not newbie else blu_pugger.newbie_elo)

	return Embed(title = f"Random Team Lists").add_field(
		name = f"🔴 Red Team\n{int(mean(red_elo))} avg elo | {int(median(red_elo))} median",
		value = "\n".join([str(pugger) for pugger in team1])
	).add_field(
		name = f"🔵 Blu Team\n{int(mean(blu_elo))} avg elo | {int(median(blu_elo))} median",
		value = "\n".join([str(pugger) for pugger in team2])
	)


class GenteamsView(View):
	children: list[Button]
	def __init__(
		self,
		next_game: VoiceChannel, waiting: VoiceChannel,
		apugs: tuple[VoiceChannel], bpugs: tuple[VoiceChannel],
		staff: User,
		team1: Iterable[Pugger], team2: Iterable[Pugger],
		amnt_per_team: int, newbie: bool,
		*, timeout = 120
	):
		super().__init__(timeout = timeout)
		self.next_game = next_game
		self.waiting = waiting
		self.apugs = apugs
		self.bpugs = bpugs
		self.staff = staff
		self.team1 = team1
		self.team2 = team2
		self.amnt_per_team = amnt_per_team
		self.newbie = newbie
		self.msg: Union[Message, PartialInteractionMessage] = None

	async def on_timeout(self) -> None:
		if self.msg:
			await self.msg.edit(view = None, delete_after = 10)

	async def on_error(self, error: Exception, item: Button, interaction: Interaction) -> None:
		# send to audit channel first
		embed = Embed(
			title = "Genteams Error",
			description = "```" + "".join(traceback.format_exception(type(error), error, error.__traceback__)) + "```",
			timestamp = utcnow()
		)
		audit = get_audit_chan(interaction, True)
		
		await audit.send(embed = embed)
		# then send error to interaction channel
		embed.description = f"{item.label}\n{type(error)} - {error}"
		await interaction.channel.send(embed = embed)

	async def interaction_check(self, interaction: Interaction) -> bool:
		return interaction.user == self.staff

	async def _move_to_teams(self, intr: Interaction, vcs: tuple[VoiceChannel]):
		await intr.response.defer() # defer just in case

		# update runner info
		info = await get_runner_entry(intr.user.id)
		payload = {
			RUNNER_DB.table_column_names[1]: (info.rpugs + 1) if not self.newbie else info.rpugs, # rpugs
			RUNNER_DB.table_column_names[2]: int(utcnow().timestamp()) if not self.newbie else info.rpugs_last_ran, # rpugs_last_ran
			RUNNER_DB.table_column_names[3]: (info.npugs + 1) if self.newbie else info.npugs, # npugs
			RUNNER_DB.table_column_names[4]: int(utcnow().timestamp()) if self.newbie else info.npugs_last_ran, # npugs_last_ran
		}
		await edit_runner_entry(
			intr.user.id,
			**payload
		)

		await intr.edit(view = None)
		self.stop() # done with the view

		# update last active in pugger db
		cur_time = utcnow()
		timestamp = int(cur_time.timestamp())
		key_names = (PUG_TABLE_VALUES[5], PUG_TABLE_VALUES[0]) # last_active, discord_id
		query: list[tuple[int, int]] = list()
		pugger: Pugger
		for pugger in self.team1 + self.team2:
			query.append((timestamp, pugger.discord_id))
		await mass_edit_pug_entries(key_names, tuple(query))

		# if newbie pugs, send to audit channel
		'''
		if self.newbie:
			audit = get_audit_chan(intr, True)
			audit_embed = Embed(
				title = "Newbie Genteams Command",
				description = f"""{intr.user.mention} | {str(intr.user)} | {intr.user.id}
command used at {format_dt(cur_time)} ({format_dt(cur_time, style = "R")})"""
			)
			await audit.send(embed = audit_embed)
		'''

		# move puggers to vc
		await move_to_vc([pugger.member for pugger in self.team1], vcs[0], "Moving to pug team vc")
		await move_to_vc([pugger.member for pugger in self.team2], vcs[1], "Moving to pug team vc")

	@button(label = "Reroll Teams", emoji = "🎲", style = ButtonStyle.blurple)
	async def reroll_button(self, button: Button, interaction: Interaction):
		await interaction.response.defer()
		self.team1, self.team2 = await genteams_setup(self.next_game, self.waiting, self.amnt_per_team, self.newbie)
		await interaction.edit(embed = genteams_embed(self.team1, self.team2, self.newbie))

	@button(label = "Move To A-Pugs", emoji = "🅰️", style = ButtonStyle.green)
	async def move_to_red_button(self, button: Button, interaction: Interaction):
		await self._move_to_teams(interaction, self.apugs)

	@button(label = "Move To B-Pugs", emoji = "🅱️", style = ButtonStyle.green)
	async def move_to_blu_button(self, button: Button, interaction: Interaction):
		await self._move_to_teams(interaction, self.bpugs)

	@button(label = "Cancel", emoji = "⛔", style = ButtonStyle.red)
	async def cancel_button(self, button: Button, interaction: Interaction):
		await interaction.edit(view = None, delete_after = 10)
		self.stop()


async def genteams(
	info: Union[Context, Interaction],
	apugs: tuple[VoiceChannel],
	bpugs: tuple[VoiceChannel],
	waiting_vc: VoiceChannel,
	next_game_vc: VoiceChannel,
	amnt_per_team: int,
	newbie: bool
):
	mem = get_user(info)
	#await new_runner_entry(mem.id)
	team1, team2 = await genteams_setup(next_game_vc, waiting_vc, amnt_per_team, newbie)
	view = GenteamsView(
		next_game_vc, waiting_vc, # queued puggers
		apugs, bpugs, # team VCs
		mem, # staff
		team1, team2, # gen'd teams
		amnt_per_team, newbie # extra
	)

	# disable A Pugs button if there are people in A Pugs
	if len(apugs[0].members + apugs[1].members) > 0:
		view.children[1].disabled = True
	# disable B Pugs button if there are people in B Pugs
	if len(bpugs[0].members + bpugs[1].members) > 0:
		view.children[2].disabled = True

	msg = await info.send(embed = genteams_embed(team1, team2, newbie), view = view)
	view.msg = msg
