from nextcord import Interaction, Member, SlashOption, TextChannel, VoiceChannel, slash_command
from nextcord.ext.application_checks import has_any_role
from nextcord.ext.application_checks import check as app_check
from nextcord.ext.commands import Bot, Cog, Context
from nextcord.ext.commands import check as prf_check
from nextcord.ext.commands.errors import CommandError
from nextcord.errors import ApplicationError
from typing import Union
from staticvars import TF2CC
from .TF2cchelper import allpuginfo, allstrikeinfo, genteams, movepuggers, pugban, puginfo, pugunban, runnerinfo, setlevel, setsteam, strike, strikeinfo, toggleclassban, unstrike, warn


VALID_ROLE_IDS = [TF2CC.owner_rid, TF2CC.admin_rid, TF2CC.moderator_rid, TF2CC.pug_runner_rid]


def used_in_bot_cmds(pref_cmd: bool = False):
	async def predicate(info: Union[Context, Interaction]):
		if info.channel.id != TF2CC.bot_commands_cid:
			error_msg = f"Command must be used in <#{TF2CC.bot_commands_cid}>"
			raise ApplicationError(error_msg) if isinstance(info, Interaction) else CommandError(error_msg)
		return True
	return app_check(predicate) if not pref_cmd else prf_check(predicate)


class TF2ccCog(Cog, name = "TF2CC"):
	def __init__(self, bot: Bot):
		self.bot = bot


	@Cog.listener("on_ready")
	async def tf2cc_on_ready(self):
		guild = self.bot.get_guild(TF2CC.guild_id)
		await guild.me.edit(nick = f"Machu {self.bot.version} TF2CC Bot")


	@slash_command(name = "pug", guild_ids = [TF2CC.guild_id])
	@has_any_role(*VALID_ROLE_IDS)
	async def pug_slash(self, intr: Interaction):
		pass


	@pug_slash.subcommand(name = "warn", description = "Warn a pugger for something they did", inherit_hooks = True)
	async def pug_warn(self, intr: Interaction, member: Member = SlashOption(description = "The member you want to warn"), reason: str = SlashOption(description = "The reason for warning this member.")):
		await warn(intr, member, reason)


	@pug_slash.subcommand(name = "strike", description = "Pug Strike a pugger", inherit_hooks = True)
	async def pug_strike(self, intr: Interaction, member: Member = SlashOption(description = "The member you want to pug strike"), reason: str = SlashOption(description = "The reason for pug striking this member.")):
		await strike(intr, member, reason)


	@pug_slash.subcommand(name = "unstrike", description = "Remove a strike from a pugger", inherit_hooks = True)
	async def pug_unstrike(self, intr: Interaction, member: Member = SlashOption(description = "The member you want to remove a pug strike from"), reason: str = SlashOption(description = "The reason for removing the pug strike from this member.")):
		await unstrike(intr, member, reason)


	@pug_slash.subcommand(name = "ban", description = "Pug Ban a pugger", inherit_hooks = True)
	async def pug_ban(self, intr: Interaction, member: Member = SlashOption(description = "The member you want to pug ban"), reason: str = SlashOption(description = "The reason for pug banning this member.")):
		await pugban(intr, member, reason)


	@pug_slash.subcommand(name = "unban", description = "Remove a pug ban from a pugger", inherit_hooks = True)
	async def pug_unban(self, intr: Interaction, member: Member = SlashOption(description = "The member you want to remove a pug ban from"), reason: str = SlashOption(description = "The reason for removing the pug ban from this member.")):
		await pugunban(intr, member, reason)


	# ~~~ VIEW & VIEW_ALL SUBGROUP ~~~
	@pug_slash.subcommand(name = "view", inherit_hooks = True)
	@used_in_bot_cmds()
	async def pug_view(self, intr: Interaction):
		pass


	@pug_view.subcommand(name = "strike_info", description = "View a member's basic strike info", inherit_hooks = True)
	async def pug_view_strikeinfo(self, intr: Interaction, member: Member):
		await strikeinfo(intr, member)


	@pug_view.subcommand(name = "pug_info", description = "View a member's pug info", inherit_hooks = True)
	async def pug_view_puginfo(self, intr: Interaction, member: Member, pug_type: int = SlashOption(
		choices = {"Regular Pugs": 0, "Newbie Pugs": 1},
		default = False
	)):
		await puginfo(intr, member, bool(pug_type))


	@pug_view.subcommand(name = "runner_info", description = "View a Pug Runner's basic info")
	@has_any_role(*(VALID_ROLE_IDS[:-1]))
	async def pug_view_runnerinfo(self, intr: Interaction, member: Member):
		await runnerinfo(intr, member)


	@pug_slash.subcommand(name = "view_all", inherit_hooks = True)
	@used_in_bot_cmds()
	async def pug_viewall(self, intr: Interaction):
		pass


	@pug_viewall.subcommand(name = "strike_info", description = "View all members' basic strike info", inherit_hooks = True)
	async def pug_viewall_strikeinfo(self, intr: Interaction):
		await allstrikeinfo(intr)


	@pug_viewall.subcommand(name = "pug_info", description = "View all members' pug info", inherit_hooks = True)
	async def pug_viewall_puginfo(self, intr: Interaction, pug_type: int = SlashOption(
		choices = {"Regular Pugs": 0, "Newbie Pugs": 1},
		default = False
	)):
		await allpuginfo(intr, bool(pug_type))


	# ~~~ SET SUBGROUP ~~~
	@pug_slash.subcommand(name = "set", inherit_hooks = True)
	async def pug_set(self, intr: Interaction):
		pass


	@pug_set.subcommand(name = "level", description = "Set the level role of a member", inherit_hooks = True)
	async def pug_set_level(self, intr: Interaction, member: Member, level: int = SlashOption(
		choices = {"Level 0": 0, "Level 1": 1, "Level 2": 2, "Level 3": 3}
	)):
		if level == 0:
			level_role_id = TF2CC.level0_rid
		if level == 1:
			level_role_id = TF2CC.level1_rid
		if level == 2:
			level_role_id = TF2CC.level2_rid
		else:
			level_role_id = TF2CC.level3_rid
		level_role = intr.guild.get_role(level_role_id)
		await setlevel(intr, member, level_role)


	@pug_set.subcommand(name = "steam", description = "Link a Steam account to a member", inherit_hooks = True)
	async def pug_set_steam(self, intr: Interaction, member: Member, steamid64: str = SlashOption(description = "The SteamID64 to link to the member. e.g. 76561197960265728")):
		if not steamid64.isdigit():
			await intr.send(f"Invalid SteamID64 provided: `{steamid64}`.")
			return
		steamID = int(steamid64)
		if steamID <= 0:
			await intr.send(f"Invalid SteamID64 provided: `{steamID}`.")
			return
		await setsteam(intr, member, steamID)


	# ~~~ TOGGLE SUBGROUP ~~~
	@pug_slash.subcommand(name = "toggle", inherit_hooks = True)
	async def pug_toggle(self, intr: Interaction):
		pass


	@pug_toggle.subcommand(name = "classban", description = "Toggle a pug class ban on a member", inherit_hooks = True)
	async def pug_toggle_classban(self, intr: Interaction, member: Member, class_restriction: str = SlashOption(
		choices = {
			"Scout Ban": str(TF2CC.scout_ban_rid),
			"Soldier Ban": str(TF2CC.soldier_ban_rid),
			"Demoman Ban": str(TF2CC.demoman_ban_rid),
			"Medic Lock": str(TF2CC.medic_lock_rid),
			"Sniper Ban": str(TF2CC.sniper_ban_rid),
			"Spy Ban": str(TF2CC.spy_ban_rid),
		}
	)):
		classban_rid = int(class_restriction)
		classban_role = intr.guild.get_role(classban_rid)
		await toggleclassban(intr, member, classban_role)


	# ~~~ MOVE & GENTEAMS ~~~
	@pug_slash.subcommand(name = "move", inherit_hooks = True)
	async def pug_move(self, intr: Interaction):
		pass


	@pug_move.subcommand(name = "newbie", description = "Move members in the Newbie Pugs VCs", inherit_hooks = True)
	@used_in_bot_cmds()
	async def pug_move_newbie(self, intr: Interaction, pug_type: str = SlashOption(choices = ["A Pugs", "B Pugs"])):
		red_team: VoiceChannel = intr.guild.get_channel(TF2CC.new_pug_red1_cid if "A" in pug_type else TF2CC.new_pug_red2_cid)
		blu_team: VoiceChannel = intr.guild.get_channel(TF2CC.new_pug_blu1_cid if "A" in pug_type else TF2CC.new_pug_blu2_cid)
		waiting: VoiceChannel = intr.guild.get_channel(TF2CC.new_pug_waiting_cid)
		next_game: VoiceChannel = intr.guild.get_channel(TF2CC.new_pug_next_game_cid)
		logs_chan: TextChannel = intr.guild.get_channel(TF2CC.pug_log_cid)
		await movepuggers(intr, (red_team, blu_team), waiting, next_game, logs_chan, True)


	@pug_move.subcommand(name = "regular", description = "Move members in the Regular Pugs VCs", inherit_hooks = True)
	@used_in_bot_cmds()
	async def pug_move_regular(self, intr: Interaction, pug_type: str = SlashOption(choices = ["A Pugs", "B Pugs"])):
		red_team: VoiceChannel = intr.guild.get_channel(TF2CC.reg_pug_red1_cid if "A" in pug_type else TF2CC.reg_pug_red2_cid)
		blu_team: VoiceChannel = intr.guild.get_channel(TF2CC.reg_pug_blu1_cid if "A" in pug_type else TF2CC.reg_pug_blu2_cid)
		waiting: VoiceChannel = intr.guild.get_channel(TF2CC.reg_pug_waiting_cid)
		next_game: VoiceChannel = intr.guild.get_channel(TF2CC.reg_pug_next_game_cid)
		logs_chan: TextChannel = intr.guild.get_channel(TF2CC.pug_log_cid)
		await movepuggers(intr, (red_team, blu_team), waiting, next_game, logs_chan, False)


	@pug_slash.subcommand(name = "genteams", inherit_hooks = True)
	async def pug_gt(self, intr: Interaction):
		pass


	@pug_gt.subcommand(name = "newbie", description = "Generate teams for Newbie Pugs", inherit_hooks = True)
	@used_in_bot_cmds()
	async def pug_gt_newbie(self, intr: Interaction, team_size: int = SlashOption(
		description = "The amount of players on each team (Default 6)",
		choices = [2, 3, 4, 5, 6, 7, 8, 9],
		default = 6
	)):
		red_team1: VoiceChannel = intr.guild.get_channel(TF2CC.new_pug_red1_cid)
		blu_team1: VoiceChannel = intr.guild.get_channel(TF2CC.new_pug_blu1_cid)
		red_team2: VoiceChannel = intr.guild.get_channel(TF2CC.new_pug_red2_cid)
		blu_team2: VoiceChannel = intr.guild.get_channel(TF2CC.new_pug_blu2_cid)
		waiting: VoiceChannel = intr.guild.get_channel(TF2CC.new_pug_waiting_cid)
		next_game: VoiceChannel = intr.guild.get_channel(TF2CC.new_pug_next_game_cid)
		await genteams(intr, (red_team1, blu_team1), (red_team2, blu_team2), waiting, next_game, team_size, True)


	@pug_gt.subcommand(name = "regular", description = "Generate teams for Regular Pugs", inherit_hooks = True)
	@used_in_bot_cmds()
	async def pug_gt_regular(self, intr: Interaction, team_size: int = SlashOption(
		description = "The amount of players on each team (Default 6)",
		choices = [2, 3, 4, 5, 6, 7, 8, 9],
		default = 6
	)):
		red_team1: VoiceChannel = intr.guild.get_channel(TF2CC.reg_pug_red1_cid)
		blu_team1: VoiceChannel = intr.guild.get_channel(TF2CC.reg_pug_blu1_cid)
		red_team2: VoiceChannel = intr.guild.get_channel(TF2CC.reg_pug_red2_cid)
		blu_team2: VoiceChannel = intr.guild.get_channel(TF2CC.reg_pug_blu2_cid)
		waiting: VoiceChannel = intr.guild.get_channel(TF2CC.reg_pug_waiting_cid)
		next_game: VoiceChannel = intr.guild.get_channel(TF2CC.reg_pug_next_game_cid)
		await genteams(intr, (red_team1, blu_team1), (red_team2, blu_team2), waiting, next_game, team_size, False)


	@pug_slash.subcommand(name = "dm", description = "DM a message to all members in a Voice Channel.", inherit_hooks = True)
	async def pug_dm(
		self,
		intr: Interaction,
		channel: str = SlashOption(
			description = "The Voice Channel to send the message to.",
			choices = {
				"Newbie Waiting Room": str(TF2CC.new_pug_waiting_cid),
				"Regular Waiting Room": str(TF2CC.reg_pug_waiting_cid),
				"Newbie A Pugs": f"{TF2CC.new_pug_red1_cid},{TF2CC.new_pug_blu1_cid}",
				"Newbie B Pugs": f"{TF2CC.new_pug_red2_cid},{TF2CC.new_pug_blu2_cid}",
				"Regular A Pugs": f"{TF2CC.reg_pug_red1_cid},{TF2CC.reg_pug_blu1_cid}",
				"Regular B Pugs": f"{TF2CC.reg_pug_red2_cid},{TF2CC.reg_pug_blu2_cid}"
			}
		),
		message: str = SlashOption(description = "The message that will be sent.")
	):
		await intr.response.defer(ephemeral = True)
		channel_ids: list[int] = [int(channel_id) for channel_id in channel.split(",")]
		vcs: list[VoiceChannel] = [intr.guild.get_channel(channel_id) for channel_id in channel_ids]
		if not all(vcs):
			await intr.send("Could not find that Voice Channel.", ephemeral = True)
			return

		members: list[Member] = list()
		failed: list[Member] = list()
		for vc in vcs:
			members += vc.members
		for member in members:
			try:
				await member.send(message)
			except:
				failed.append(member)
		content = f"Sent message `{message}` to all members in {vc.mention}."
		if failed:
			content += "\nCould not send the message to:\n-" + "\n-".join([member.mention for member in failed])
		await intr.send(content, ephemeral = True)


	# Move over stuff from the Serveme Cog


def setup(bot: Bot):
	bot.add_cog(TF2ccCog(bot))
