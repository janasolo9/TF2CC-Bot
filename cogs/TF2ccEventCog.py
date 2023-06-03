import traceback
from datetime import datetime, timedelta, timezone
from nextcord import AuditLogAction, Embed, Member, Role, TextChannel, HTTPException, NotFound
from nextcord.ext.commands import Bot, Cog
from nextcord.ext.tasks import loop
from nextcord.utils import utcnow, format_dt
from staticvars import TF2CC
from .static import PUG_DB, RUNNER_DB, STRIKE_DB, STRIKE_TABLE_VALUES, PugEmbeds
from .TF2ccDB import edit_pug_entry, edit_runner_entry, edit_strike_entry, get_all_runner_entries, get_all_strike_entries, get_pug_entry, get_runner_entry, get_strike_entry, new_runner_entry, new_strike_entry


MIDNIGHT = utcnow().time().replace(hour = 7, minute = 0, second = 0, microsecond = 0)


class TF2ccEventCog(Cog, name = "TF2CC Events"):
	def __init__(self, bot: Bot):
		self.bot = bot
		self.machu_log_cid = 747482111262457946
		if not self.update_strikes.get_task():
			self.update_strikes.start()
		if not self.remove_rcon_pins.get_task():
			self.remove_rcon_pins.start()
		if not self.dm_pug_runners_late_run.get_task():
			self.dm_pug_runners_late_run.start()


	@Cog.listener(name = "on_ready")
	async def on_ready(self):
		##JBOTLOG.debug("TF2CC Event Cog on_ready")
		await STRIKE_DB.make_table()
		await PUG_DB.make_table()
		await RUNNER_DB.make_table()
		self.guild = self.bot.get_guild(TF2CC.guild_id)
		self.audit: TextChannel = self.guild.get_channel(self.machu_log_cid)
		self.bot_cmds: TextChannel = self.guild.get_channel(TF2CC.bot_commands_cid)
		self.classban_roles = (
			self.guild.get_role(TF2CC.scout_ban_rid),
			self.guild.get_role(TF2CC.soldier_ban_rid),
			self.guild.get_role(TF2CC.demoman_ban_rid),
			self.guild.get_role(TF2CC.medic_lock_rid),
			self.guild.get_role(TF2CC.sniper_ban_rid),
			self.guild.get_role(TF2CC.spy_ban_rid),
		)
		self.level_roles = (
			self.guild.get_role(TF2CC.level0_rid),
			self.guild.get_role(TF2CC.level1_rid),
			self.guild.get_role(TF2CC.level2_rid),
			self.guild.get_role(TF2CC.level3_rid)
		)
		self.strike_roles = (
			self.guild.get_role(TF2CC.pug_strike1_rid),
			self.guild.get_role(TF2CC.pug_strike2_rid),
			self.guild.get_role(TF2CC.pug_strike3_rid)
		)


	@Cog.listener(name = "on_member_join")
	async def auto_roles_for_new_mem(self, member: Member):
		# member just joined guild, they might have existing info in DB
		# check guild
		if member.guild != self.guild:
			return

		roles_to_add: list[Role] = []
		# check pug entry
		pug_entry = await get_pug_entry(member.id)
		if pug_entry is not None:
			# check steam linked
			if pug_entry.steam_id is not None:
				steam_linked = member.guild.get_role(TF2CC.steam_linked_rid)
				roles_to_add.append(steam_linked)

			# check class bans
			if pug_entry.class_bans:
				if "1" in pug_entry.class_bans: # scout ban
					roles_to_add.append(self.classban_roles[0])
				if "2" in pug_entry.class_bans: # soldier ban
					roles_to_add.append(self.classban_roles[1])
				if "4" in pug_entry.class_bans: # demoman ban
					roles_to_add.append(self.classban_roles[2])
				if "7" in pug_entry.class_bans: # medic lock
					roles_to_add.append(self.classban_roles[3])
				if "8" in pug_entry.class_bans: # sniper ban
					roles_to_add.append(self.classban_roles[4])
				if "9" in pug_entry.class_bans: # spy ban
					roles_to_add.append(self.classban_roles[5])

			# check strike entry
			strike_entry = await get_strike_entry(member.id)
			if strike_entry is not None:
				if strike_entry.strike1: # strike 1
					roles_to_add.append(self.strike_roles[0])
				if strike_entry.strike2: # strike 2
					roles_to_add.append(self.strike_roles[1])
				if strike_entry.pugban or strike_entry.permanent_ban: # pug ban
					roles_to_add.append(self.strike_roles[2])

		await member.add_roles(*roles_to_add, reason = "From existing database info")


	@Cog.listener(name = "on_member_update")
	async def remove_pug_role(self, before: Member, after: Member):
		# if member has pug ban & pug role, remove pug role
		pug_role = after.get_role(TF2CC.pug_rid)
		ban_role = after.get_role(TF2CC.pug_strike3_rid)
		if not(pug_role and ban_role):
			return
		roles_to_remove = [pug_role] + list(self.level_roles)
		await after.remove_roles(*roles_to_remove, reason = "Pug Banned - removing pug roles", atomic = False)



	@Cog.listener(name = "on_member_update")
	async def edit_strike_roles(self, before: Member, after: Member):
		# updating strike roles
		role_diff = set(before.roles).symmetric_difference(after.roles)
		logs = await self.guild.audit_logs(action = AuditLogAction.member_role_update, limit = 1).flatten()
		if len(logs) == 0 or logs[0].user.bot:
			return # only care if human did this

		contains_strike = len(role_diff.intersection(self.strike_roles)) == 1
		if not contains_strike:
			return

		# member strike or pugban update
		await new_strike_entry(user = after)
		entry = await get_strike_entry(after.id) # get current info and set up payload
		payload = {
			STRIKE_TABLE_VALUES[1]: entry.strike_count,
			STRIKE_TABLE_VALUES[2]: entry.total_strike_count,
			STRIKE_TABLE_VALUES[3]: entry.first_strike_duration,
			STRIKE_TABLE_VALUES[4]: entry.second_strike_duration,
			STRIKE_TABLE_VALUES[5]: entry.strike1,
			STRIKE_TABLE_VALUES[6]: entry.strike1,
			STRIKE_TABLE_VALUES[7]: entry.pugban,
			STRIKE_TABLE_VALUES[8]: entry.permanent_ban
		}

		# check which role was added or removed
		# if first strike was added
		if self.strike_roles[0] in role_diff and self.strike_roles[0] in after.roles:
			cmd_type = "strike"
			# increase strike count
			payload[STRIKE_TABLE_VALUES[1]] += 1 # strike count
			payload[STRIKE_TABLE_VALUES[2]] += 1 # total strike count
			payload[STRIKE_TABLE_VALUES[5]] = 1 # strike1
			# set first strike duration if first strike
			if payload[STRIKE_TABLE_VALUES[2]] == 1:
				payload[STRIKE_TABLE_VALUES[3]] = int((utcnow() + timedelta(days = TF2CC.first_strike_duration)).timestamp())

		# if first strike was removed
		elif self.strike_roles[0] in role_diff and self.strike_roles[0] not in after.roles:
			cmd_type = "unstrike"
			# decrease strike count
			payload[STRIKE_TABLE_VALUES[1]] -= 1 # strike count
			payload[STRIKE_TABLE_VALUES[2]] -= 1 # total strike count
			payload[STRIKE_TABLE_VALUES[5]] = 0 # strike 1

		# if second strike was added
		elif self.strike_roles[1] in role_diff and self.strike_roles[1] in after.roles:
			cmd_type = "strike"
			# increase strike count
			payload[STRIKE_TABLE_VALUES[1]] += 1 # strike count
			payload[STRIKE_TABLE_VALUES[2]] += 1 # total strike count
			payload[STRIKE_TABLE_VALUES[6]] = 1 # strike2
			# set temp ban duration if second strike
			if payload[STRIKE_TABLE_VALUES[1]] == 2:
				payload[STRIKE_TABLE_VALUES[4]] = int((utcnow() + timedelta(days = TF2CC.strike2_duration)).timestamp())

		# if second strike was removed
		elif self.strike_roles[1] in role_diff and self.strike_roles[1] not in after.roles:
			cmd_type = "unstrike"
			# decrease strike count
			payload[STRIKE_TABLE_VALUES[1]] -= 1 # strike count
			payload[STRIKE_TABLE_VALUES[2]] -= 1 # total strike count
			payload[STRIKE_TABLE_VALUES[6]] = 0 # strike2

		# if pug ban was added
		elif self.strike_roles[2] in role_diff and self.strike_roles[2] in after.roles:
			cmd_type = "pugban"
			# this is considered a permanent ban
			payload[STRIKE_TABLE_VALUES[7]] = 1 # pug ban
			payload[STRIKE_TABLE_VALUES[8]] = 1 # permanent pug ban
			# remove pugs role from member
			pug_role = after.get_role(TF2CC.pug_rid)
			if pug_role:
				await after.remove_roles(pug_role, reason = "Pug Banned - removing Pugs role")

		# if pug ban was removed
		elif self.strike_roles[2] in role_diff and self.strike_roles[2] not in after.roles:
			cmd_type = "pugunban"
			# if this was third strike, then decrease strike count
			if payload[STRIKE_TABLE_VALUES[1]] == 3:
				payload[STRIKE_TABLE_VALUES[1]] -= 1
			payload[STRIKE_TABLE_VALUES[7]] = 0 # pug ban
			payload[STRIKE_TABLE_VALUES[8]] = 0 # permanent ban

		# unknown role - return
		else: return

		# fix strike counts if necessary
		payload[STRIKE_TABLE_VALUES[1]] = min(3, max(0, payload[STRIKE_TABLE_VALUES[1]])) # min 0 & max 3
		payload[STRIKE_TABLE_VALUES[2]] = max(0, payload[STRIKE_TABLE_VALUES[2]]) # min 0

		# update strike entry
		await edit_strike_entry(after.id, **payload)

		# prepare and send messages
		embeds = PugEmbeds(
			target = after,
			staff = logs[0].user,
			type = cmd_type,
			strike_count = payload[STRIKE_TABLE_VALUES[1]],
			total_strike_count = payload[STRIKE_TABLE_VALUES[2]]
		)
		try:
			#JBOTLOG.debug(f"sending strike embed to {after} ({after.id})")
			await after.send(embed = embeds.get_user_embed())
		except:
			#JBOTLOG.debug(f"could not send strike embed to {after} ({after.id})")
			pass # could not send message to the user
		await self.audit.send(embed = embeds.get_record_embed())
		#JBOTLOG.debug(f"updated strike role for {after}: {cmd_type} {list(role_diff)[0].name}")


	@Cog.listener(name = "on_member_update")
	async def level_role_changed(self, before: Member, after: Member):
		role_diff = set(before.roles).symmetric_difference(after.roles)
		logs = await self.guild.audit_logs(action = AuditLogAction.member_role_update, limit = 1).flatten()
		contains_level = len(role_diff.intersection(self.level_roles)) >= 1
		if not contains_level:
			return

		# someone changed a member's level role
		# prepare and send messages
		user = logs[0].user
		reason = logs[0].reason
		# determine which role
		level_roles: list[Role] = [role for role in role_diff if role in self.level_roles]
		level_roles.sort(key = lambda role: role.name)

		# multiple roles added and removed at same time
		temp = {
			"Added": list(),
			"Removed": list()
		}
		for role in level_roles:
			if after.get_role(role.id):
				temp["Added"].append(role)
			else:
				temp["Removed"].append(role)
		#added = after.get_role(level_roles[0].id) is not None
		#- {"Added" if added else "Removed"} {" ".join(role.mention for role in level_roles)}
		changed_roles = ""
		for key, vals in temp.items():
			if not vals:
				continue
			changed_roles += "\n" + f"- {key} {' '.join([role.mention for role in vals])}"

		embed = Embed(
			title = "Level Role Changed",
			description = f"""
{user.mention if user else "Unknown"} updated the level role of {after.mention} ({after}){changed_roles}
- Reason: `{reason}`
""",
			timestamp = utcnow()
		).set_footer(
			text = "TF2CC Pug Moderation",
			icon_url = "https://static-cdn.jtvnw.net/jtv_user_pictures/20cb89d0-42fc-4bc9-b083-91c9c895b782-profile_image-70x70.png"
		)
		await self.audit.send(embed = embed)
		#JBOTLOG.debug(f"updated level role for {after}: {temp}")


	@Cog.listener(name = "on_member_update")
	async def edit_class_ban_roles(self, before: Member, after: Member):
		role_diff = set(before.roles).symmetric_difference(after.roles)
		logs = await self.guild.audit_logs(action = AuditLogAction.member_role_update, limit = 1).flatten()
		contains_class_ban = len(role_diff.intersection(self.classban_roles)) >= 1
		if not contains_class_ban:
			return

		# someone changed a member's class bans
		class_bans: list[str] = []
		if self.classban_roles[0] in after.roles: # scout ban
			class_bans.append("1")
		if self.classban_roles[1] in after.roles: # soldier ban
			class_bans.append("2")
		if self.classban_roles[2] in after.roles: # demoman ban
			class_bans.append("4")
		if self.classban_roles[3] in after.roles: # medic lock
			class_bans.append("7")
		if self.classban_roles[4] in after.roles: # sniper ban
			class_bans.append("8")
		if self.classban_roles[5] in after.roles: # spy ban
			class_bans.append("9")

		new_bans = ",".join(class_bans)
		payload = {TF2CC.pug_table_values[7]: new_bans}
		 # update class restrictions
		await edit_pug_entry(after.id, **payload)

		# prepare and send messages
		staff = logs[0].user
		reason = logs[0].reason
		# determine which role
		classban_roles: list[Role] = [role for role in role_diff if role in self.classban_roles]
		classban_roles.sort(key = lambda role: role.name)

		# multiple roles added and removed at same time
		temp = {
			"Added": list(),
			"Removed": list()
		}
		for role in classban_roles:
			if after.get_role(role.id):
				temp["Added"].append(role)
			else:
				temp["Removed"].append(role)
		#added = after.get_role(level_roles[0].id) is not None
		#- {"Added" if added else "Removed"} {" ".join(role.mention for role in level_roles)}
		changed_roles = ""
		for key, vals in temp.items():
			if not vals:
				continue
			changed_roles += "\n" + f"- {key} {' '.join([role.mention for role in vals])}"

		embed = Embed(
			title = "Class Ban Role Update",
			description = f"""
{staff.mention if staff else "Unknown"} updated the class bans for {after.mention} ({after}){changed_roles}
- Reason: `{reason}`
""",
			timestamp = utcnow()
		).set_footer(
			text = "TF2CC Pug Moderation",
			icon_url = "https://static-cdn.jtvnw.net/jtv_user_pictures/20cb89d0-42fc-4bc9-b083-91c9c895b782-profile_image-70x70.png"
		)
		await self.audit.send(embed = embed)
		#JBOTLOG.debug(f"updated class ban roles for {after}: {class_bans}")


	@Cog.listener(name = "on_member_update")
	async def update_runner_info(self, before: Member, after: Member):
		# update runner db for became_runner time
		before_role = before.get_role(TF2CC.pug_runner_rid)
		after_role = after.get_role(TF2CC.pug_runner_rid)
		payload = {
			RUNNER_DB.table_column_names[5]: int(utcnow().timestamp())
		}
		if not before_role and after_role:
			# they got the pug runner role
			runner_info = await get_runner_entry(after.id)
			if not runner_info:
				await new_runner_entry(after.id, **payload)
			else:
				await edit_runner_entry(after.id, **payload)


	@loop(time = MIDNIGHT)
	async def update_strikes(self):
		await self.bot.wait_until_ready()
		entries = await get_all_strike_entries(
			conditional = f"WHERE {STRIKE_TABLE_VALUES[1]} > ? AND {STRIKE_TABLE_VALUES[1]} < ? AND {STRIKE_TABLE_VALUES[-1]} < ?",
			params = (0, 3, 1)
		)
		if not len(entries): return

		cur_time = utcnow()
		for entry in entries:
			# if member not in guild, skip
			user = self.guild.get_member(entry.discord_id)
			if user is None: continue

			# check first strike ever
			if entry.total_strike_count == 1 and entry.strike_count == 1:
				first_strike_ends = datetime.fromtimestamp(entry.first_strike_duration, tz = timezone.utc)
				if first_strike_ends > cur_time: # duration has not ended yet
					continue

				# duration has ended
				# remove first strike
				payload = {
					STRIKE_TABLE_VALUES[1]: max(entry.strike_count - 1, 0), # strike count
					STRIKE_TABLE_VALUES[3]: 0, # first strike duration
					STRIKE_TABLE_VALUES[5]: 0 # strike1
				}
				reason = f"{TF2CC.first_strike_duration} days have passed since first strike was given"

				#JBOTLOG.info(f"removing strike from {user}")
				await user.remove_roles(self.strike_roles[0], reason = reason)
				await edit_strike_entry(user.id, **payload)
				embeds = PugEmbeds(
					target = user,
					staff = self.bot.user,
					type = "unstrike",
					reason = reason,
					strike_count = payload[STRIKE_TABLE_VALUES[1]]
				)
				await self.audit.send(embed = embeds.get_record_embed())
				#JBOTLOG.info(f"removed strike from {user}")

			# check second strike temp ban
			elif entry.strike_count == 2 and entry.pugban:
				temp_ban_ends = datetime.fromtimestamp(entry.second_strike_duration, tz = timezone.utc)
				if temp_ban_ends > cur_time: # duration has not ended yet
					continue

				# duration has ended
				# remove temp pug ban
				payload = {
					STRIKE_TABLE_VALUES[4]: 0, # second strike duration
					STRIKE_TABLE_VALUES[7]: 0 # pugban
				}
				reason = f"{TF2CC.strike2_duration} days have passed since second strike was given"

				#JBOTLOG.info(f"removing temp pugban from {user}")
				await user.remove_roles(self.strike_roles[2], reason = reason)
				await edit_strike_entry(user.id, **payload)
				embeds = PugEmbeds(
					target = user,
					staff = self.bot.user,
					type = "pugunban",
					reason = reason
				)
				await self.audit.send(embed = embeds.get_record_embed())
				#JBOTLOG.info(f"removed temp pugban from {user}")


	@loop(time = MIDNIGHT)
	async def remove_rcon_pins(self):
		await self.bot.wait_until_ready()
		# get all pins in bot commands channel
		try:
			pins = await self.bot_cmds.pins()
		except HTTPException:
			return # getting pins failed

		# remove pins that are more than 1 day old
		cur_time = utcnow()
		delta = timedelta(days = 1)
		for pin in pins:
			diff = cur_time - pin.created_at
			if diff > delta:
				try:
					await pin.unpin(reason = "Info is outdated - unpinning")
				except NotFound:
					continue
				except HTTPException:
					continue
				except Exception as error:
					#JBOTLOG.error("".join(traceback.format_exception(type(error), error, error.__traceback__)))
					print("".join(traceback.format_exception(type(error), error, error.__traceback__)))


	@loop(time = MIDNIGHT)
	async def dm_pug_runners_late_run(self):
		await self.bot.wait_until_ready()
		# DM pug runners that haven't run newbie pugs in 3 weeks
		current_time = utcnow()
		delta = timedelta(weeks = 3)
		runner_role = self.guild.get_role(TF2CC.pug_runner_rid)
		all_info = await get_all_runner_entries(
			conditional = f"WHERE {RUNNER_DB.table_column_names[5]} <= ?",
			params = (int((current_time - delta).timestamp()),)
		)
		removed: list[tuple[Member, str]] = list()
		for runner_info in all_info:
			runner = self.guild.get_member(runner_info.discord_id)
			if not runner:
				continue
			elif not runner.get_role(TF2CC.pug_runner_rid):
				continue

			# compare last ran time to current time
			# if last ran > 3 weeks ago, then remove role
			last_ran_newbie_pugs = runner_info.npugs_datetime
			if last_ran_newbie_pugs + delta >= current_time:
				continue

			# runner did not run newbie pugs in 3 weeks
			# remove runner role
			await runner.remove_roles(
				runner_role,
				reason = "Has not run newbie pugs",
				atomic = False
			)
			removed.append((runner, format_dt(last_ran_newbie_pugs) if runner_info.npugs else "Never"))

		if removed:
			# send message to each runner
			runner_embed_description = """
You have not run Newbie Pugs within the last 3 weeks.
Message any moderator or open a TF2CC Support Ticket if you have attempted* to run Newbie Pugs to receive the Pug Runner role again.
*An attempt to run newbie pugs is defined as pinging for Newbie Pugs in <#932730775428800633> and waiting for players to join for at least 30 minutes.

Last Ran Newbie Pugs: {last_ran_dt}
"""
			for runner, last_ran_dt in removed:
				embed = Embed(
					title = "Pug Runner Role Removed",
					description = runner_embed_description.format(last_ran_dt = last_ran_dt)
				)
				try:
					await runner.send(embed = embed)
				except:
					# could not send message to runner
					pass

			# send message to mod chat
			mod_channel = self.bot.get_partial_messageable(743553564659548262)
			embed = Embed(title = "Pug Runner Role Removed")
			runner_mentions = f"Removed {runner_role.mention} from " + " ".join([runner.mention for runner, _ in removed])
			runner_descriptions = "\n".join([f"{runner.mention} last ran: {last_ran_dt}" for runner, last_ran_dt in removed])
			embed.description = runner_mentions + "\n" + runner_descriptions
			try:
				await mod_channel.send(embed = embed)
			except:
				# couldn't send message for some reason
				#JBOTLOG.error("couldn't send pug runner removal message")
				print("couldn't send pug runner removal message")



def setup(bot: Bot):
	bot.add_cog(TF2ccEventCog(bot))
