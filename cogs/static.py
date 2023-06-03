from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from nextcord import Color, Embed, Guild, Member, User
from nextcord.utils import format_dt, get, utcnow
from typing import Dict, List, Literal, Optional, Union
from statistics import mean

from classes import ADB
from staticvars import TF2CC

#
#
# COMMENT STATIC FILE
#
#

COMMENT_DB_NAME = "./db/comments.db"
COMMENT_TABLE_NAME = "comments{obj_id}"
COMMENT_TABLE_VALUES = ("comment_id", "guild_id", "staff_id", "created_at", "comment")
COMMENT_TABLE_VALUE_TYPES = ("INTEGER PRIMARY KEY", "INTEGER", "INTEGER", "INTEGER", "TEXT")
VALID_ROLES_TABLE_NAME = "valid_roles{obj_id}"
VALID_ROLES_TABLE_VALUES = ("role_id",)
VALID_ROLES_TABLE_VALUE_TYPES = ("INTEGER PRIMARY KEY",)


def get_table_name(obj_id: int = None, obj: Union[User, Guild] = None, *, is_comment: bool) -> str:
	assert obj_id or obj, "get_table_name error - user_id or user must be specified"
	return (COMMENT_TABLE_NAME if is_comment else VALID_ROLES_TABLE_NAME).format(obj_id = obj_id or obj.id)


def get_db(obj_id: int = None, obj: Union[User, Guild] = None, *, is_comment: bool) -> ADB:
	return ADB(
		COMMENT_DB_NAME,
		get_table_name(obj_id, obj, is_comment = is_comment),
		COMMENT_TABLE_VALUES if is_comment else VALID_ROLES_TABLE_VALUES,
		COMMENT_TABLE_VALUE_TYPES if is_comment else VALID_ROLES_TABLE_VALUE_TYPES
	)


@dataclass
class CommentInfo:
	_info: Dict[str, Union[int, str]]

	@property
	def comment_id(self) -> int:
		return self._info.get(COMMENT_TABLE_VALUES[0])

	@property
	def guild_id(self) -> int:
		return self._info.get(COMMENT_TABLE_VALUES[1])

	@property
	def staff_id(self) -> int:
		return self._info.get(COMMENT_TABLE_VALUES[2])

	@property
	def created_at(self) -> datetime:
		return datetime.fromtimestamp(self._info.get(COMMENT_TABLE_VALUES[3]), tz = timezone.utc)

	@property
	def comment(self) -> str:
		return self._info.get(COMMENT_TABLE_VALUES[4])

	def get_dict(self) -> Dict[str, Union[int, str]]:
		return self._info


@dataclass
class UserComments:
	_comments: List[CommentInfo]


	@property
	def last_comment(self) -> Optional[CommentInfo]:
		if not self._comments:
			return None

		largest_id = 0
		for comment in self._comments:
			if comment.comment_id > largest_id:
				largest_id = comment.comment_id
		return self.get_comment(largest_id)


	def comment_count(self, guild_id: int) -> int:
		total = 0
		for comment in self._comments:
			if comment.guild_id == guild_id:
				total += 1
		return total


	def get_comments(self, guild_id: int) -> List[CommentInfo]:
		comments: List[CommentInfo] = list()
		for comment in self._comments:
			if comment.guild_id == guild_id:
				comments.append(comment)
		return comments


	def get_comment(self, comment_id: int) -> Optional[CommentInfo]:
		return get(self._comments, comment_id = comment_id)



#
#
# TF2CC STATIC FILE
#
#

# ~~~ TF2CC STUFF ~~~
LOGS_API_GET_LOG = "https://logs.tf/json/{log_id}"
LOGS_API_GET_LOG_IDS = "https://logs.tf/api/v1/log?player={steam_ids}&limit=1"

TF2CC_DB_NAME = "./db/tf2cc.db"

STRIKE_TABLE_NAME = "user_strikes"
STRIKE_TABLE_VALUES = ("discord_id", "strike_count", "total_strike_count", "first_strike_duration", "second_strike_duration", "strike1", "strike2", "pugban", "permanent_ban")
STRIKE_DB = ADB(
	TF2CC_DB_NAME,
	STRIKE_TABLE_NAME,
	STRIKE_TABLE_VALUES,
	("INTEGER PRIMARY KEY", "INTEGER", "INTEGER", "INTEGER", "INTEGER", "INTEGER", "INTEGER", "INTEGER", "INTEGER")
)

PUG_TABLE_NAME = "pug_info"
PUG_TABLE_VALUES = ("discord_id", "regular_win_count", "regular_lose_count", "regular_tie_count", "regular_elo", "last_active", "steam_id", "class_bans", "newbie_win_count", "newbie_lose_count", "newbie_tie_count", "newbie_elo")
PUG_TABLE_VALUE_TYPES = ("INTEGER PRIMARY KEY", "INTEGER", "INTEGER", "INTEGER", "INTEGER", "INTEGER", "INTEGER", "TEXT", "INTEGER", "INTEGER", "INTEGER", "INTEGER")
PUG_DB = ADB(
	TF2CC_DB_NAME,
	PUG_TABLE_NAME,
	PUG_TABLE_VALUES,
	PUG_TABLE_VALUE_TYPES
)

RUNNER_DB = ADB(
	TF2CC_DB_NAME,
	"pug_runners",
	("discord_id", "rpugs", "rpugs_last_ran", "npugs", "npugs_last_ran", "became_runner"),
	("INTEGER PRIMARY KEY", "INTEGER", "INTEGER", "INTEGER", "INTEGER", "INTEGER")
)



@dataclass(eq = False, frozen = True)
class StrikeEntry:
	entry: Dict[str, int]

	def __post_init__(self):
		assert self.entry is not None, "StrikeEntry dict is None"

	@property
	def discord_id(self) -> int:
		return self.entry.get("discord_id")
	
	@property
	def strike_count(self) -> int:
		return self.entry.get("strike_count")
	
	@property
	def total_strike_count(self) -> int:
		return self.entry.get("total_strike_count")

	@property
	def first_strike_duration(self) -> int:
		return self.entry.get("first_strike_duration")

	@property
	def second_strike_duration(self) -> int:
		return self.entry.get("second_strike_duration")

	@property
	def strike1(self) -> int:
		return self.entry.get("strike1")

	@property
	def strike2(self) -> int:
		return self.entry.get("strike2")

	@property
	def pugban(self) -> int:
		return self.entry.get("pugban")

	@property
	def permanent_ban(self) -> int:
		return self.entry.get("permanent_ban")


@dataclass(eq = False)
class PugEntry:
	entry: Dict[str, int] = field(default_factory = dict)
	_class_bans: List[str] = field(init = False, repr = False)

	def __post_init__(self):
		temp = self.entry.get(PUG_TABLE_VALUES[7], "")
		self._class_bans = temp.split(",") if len(temp) > 0 else list()

	@property
	def discord_id(self) -> int:
		return self.entry.get(PUG_TABLE_VALUES[0], 0)

	@property
	def steam_id(self) -> Optional[int]:
		return self.entry.get(PUG_TABLE_VALUES[6], None)

	@property
	def win_count(self) -> int:
		return self.entry.get(PUG_TABLE_VALUES[1], 0)

	@property
	def newbie_win_count(self) -> int:
		return self.entry.get(PUG_TABLE_VALUES[8], 0)

	@property
	def lose_count(self) -> int:
		return self.entry.get(PUG_TABLE_VALUES[2], 0)

	@property
	def newbie_lose_count(self) -> int:
		return self.entry.get(PUG_TABLE_VALUES[9], 0)

	@property
	def tie_count(self) -> int:
		return self.entry.get(PUG_TABLE_VALUES[3], 0)

	@property
	def newbie_tie_count(self) -> int:
		return self.entry.get(PUG_TABLE_VALUES[10], 0)

	@property
	def elo(self) -> int:
		return self.entry.get(PUG_TABLE_VALUES[4], 1000)

	@property
	def newbie_elo(self) -> int:
		return self.entry.get(PUG_TABLE_VALUES[11], 1000)

	@property
	def last_active(self) -> str:
		return format_dt(datetime.fromtimestamp(self.entry.get(PUG_TABLE_VALUES[5], 0), tz = timezone.utc))

	@property
	def class_bans(self) -> List[str]:
		if self.medlocked:
			return ["7"]
		return self._class_bans

	@property
	def medlocked(self) -> bool:
		return "7" in self._class_bans

	def get_classbans(self) -> str:
		if self.medlocked:
			return f"\n- Class Locked: {TF2CC.class_emojis.get('7', 'None')}"
		elif len(self._class_bans):
			return f"\n- Class Ban: {''.join([TF2CC.class_emojis.get(class_num, 'None') for class_num in self._class_bans])}"
		else:
			return ""


class RunnerEntry:
	def __init__(self, info: dict[str, int]):
		self.discord_id = info[RUNNER_DB.table_column_names[0]]
		self.rpugs = info[RUNNER_DB.table_column_names[1]]
		self.rpugs_last_ran = info[RUNNER_DB.table_column_names[2]]
		self.npugs = info[RUNNER_DB.table_column_names[3]]
		self.npugs_last_ran = info[RUNNER_DB.table_column_names[4]]
		self.became_runner = info[RUNNER_DB.table_column_names[5]]

	@property
	def rpugs_datetime(self) -> datetime:
		return datetime.fromtimestamp(self.rpugs_last_ran, tz = timezone.utc)

	@property
	def npugs_datetime(self) -> datetime:
		return datetime.fromtimestamp(self.npugs_last_ran, tz = timezone.utc)

	@property
	def became_runner_datetime(self) -> datetime:
		return datetime.fromtimestamp(self.became_runner, tz = timezone.utc)


@dataclass()
class Pugger:
	member: Member = field(repr = True, compare = True, kw_only = False)
	priority: bool = field(default = False, repr = True, compare = False, kw_only = True)
	pug_info: PugEntry = field(default_factory = PugEntry, repr = False, compare = True, kw_only = True)
	newbie: bool = field(default = False, repr = False, compare = False, kw_only = True)

	def __post_init__(self):
		self.level_roles = [role for role in self.member.roles if role.name.startswith("Level ")]

	def __str__(self):
		name = f"[{self.str_level}] {self.member.mention}"
		elo_info = f" ({self.win_count}/{self.lose_count}/{self.tie_count} | {self.elo})" if not self.newbie else f" ({self.newbie_win_count}/{self.newbie_lose_count}/{self.newbie_tie_count} | {self.newbie_elo})"
		priority = " \*\*" if self.priority else ""
		return f"{name}{elo_info}{priority}{self.pug_info.get_classbans()}"

	def __eq__(self, other: "Pugger"):
		return self.member == other.member

	def __lt__(self, other: "Pugger"):
		return self.int_level < other.int_level and self.elo < other.elo

	@property
	def discord_id(self) -> int:
		return self.member.id if self.member else self.pug_info.discord_id

	@property
	def str_level(self):
		return self.level_roles[-1].name[-1] if len(self.level_roles) > 0 else "x"

	@property
	def int_level(self):
		return int(self.level_roles[-1].name[-1]) if len(self.level_roles) > 0 else 0

	@property
	def elo(self):
		return self.pug_info.elo

	@property
	def win_count(self):
		return self.pug_info.win_count

	@property
	def lose_count(self):
		return self.pug_info.lose_count

	@property
	def tie_count(self):
		return self.pug_info.tie_count

	@property
	def newbie_elo(self):
		return self.pug_info.newbie_elo

	@property
	def newbie_win_count(self):
		return self.pug_info.newbie_win_count

	@property
	def newbie_lose_count(self):
		return self.pug_info.newbie_lose_count

	@property
	def newbie_tie_count(self):
		return self.pug_info.newbie_tie_count

	@property
	def total_count(self):
		return self.win_count + self.lose_count + self.tie_count

	@property
	def steam_id(self):
		return self.pug_info.steam_id

	@property
	def medlocked(self) -> bool:
		return self.pug_info.medlocked


class Player:
	def __init__(self, player_id32: int, player_info: Dict[str, Union[str, int, Dict, List[Dict]]], newbie: bool):
		self.member: Member = None
		self.pug_info: PugEntry = None
		self._steam_id = 76561197960265728 + player_id32
		self._player_info = player_info
		self.newbie = newbie

	def __str__(self):
		return f"{self.steam_id} | {self.kills}/{self.assists}/{self.deaths} | {self.damage} / {self.damage_taken}"

	@property
	def steam_id(self):
		return self._steam_id

	@property
	def kills(self) -> int:
		return self._player_info.get("kills", 0)

	@property
	def assists(self) -> int:
		return self._player_info.get("assists", 0)

	@property
	def deaths(self) -> int:
		return self._player_info.get("deaths", 0)

	@property
	def damage(self) -> int:
		return self._player_info.get("dmg", 0)

	@property
	def damage_taken(self) -> int:
		return self._player_info.get("dt", 0)

	@property
	def ubers(self) -> int:
		return self._player_info.get("ubers", 0)

	@property
	def drops(self) -> int:
		return self._player_info.get("drops", 0)

	@property
	def elo(self):
		if self.pug_info:
			return self.pug_info.newbie_elo if self.newbie else self.pug_info.elo
		return 1000

	@property
	def win_count(self):
		if self.pug_info:
			return self.pug_info.newbie_win_count if self.newbie else self.pug_info.win_count
		return 0

	@property
	def lose_count(self):
		if self.pug_info:
			return self.pug_info.newbie_lose_count if self.newbie else self.pug_info.lose_count
		return 0

	@property
	def tie_count(self):
		if self.pug_info:
			return self.pug_info.newbie_tie_count if self.newbie else self.pug_info.tie_count
		return 0

	def _get_actual_time(self, *, minutes: Optional[float], seconds: Optional[float]) -> float:
		if minutes is not None and seconds is not None and minutes != (seconds / 60.0):
			raise ValueError(f"minutes ({minutes}) and seconds ({seconds}) do not match.")
		elif minutes is None and seconds is None:
			raise ValueError(f"missing required argument: minutes or seconds must be specified")
		if minutes is not None:
			return minutes
		elif seconds is not None:
			return seconds / 60.0

	def damage_per_time(self, *, minutes: float = None, seconds: float = None) -> float:
		time = self._get_actual_time(minutes = minutes, seconds = seconds)
		return self.damage / time

	def damage_taken_per_time(self, *, minutes: float = None, seconds: float = None) -> float:
		time = self._get_actual_time(minutes = minutes, seconds = seconds)
		return self.damage_taken / time


class Team:
	def __init__(self, team_name: str, team_info: Dict[str, int]):
		self._name = team_name.lower()
		self._team_info = team_info
		self._players: List[Player] = []

	@property
	def name(self):
		return self._name

	@property
	def caps(self):
		return self._team_info.get("caps", 0)

	@property
	def charges(self):
		return self._team_info.get("charges", 0)

	@property
	def damage(self):
		return self._team_info.get("dmg", 0)

	@property
	def first_caps(self):
		return self._team_info.get("firstcaps", 0)

	@property
	def kills(self):
		return self._team_info.get("kills", 0)

	@property
	def score(self):
		return self._team_info.get("score", 0)

	@property
	def avg_elo(self) -> float:
		return mean([player.elo for player in self.players])

	@property
	def players(self):
		return self._players

	def add_player(self, player: Player):
		self._players.append(player)

	def get_player(self, steam_id: Optional[int]) -> Optional[Player]:
		if steam_id is None:
			return None
		return get(self.players, steam_id = steam_id)


class PugEmbeds:
	def __init__(self, target: User, staff: User, type: Literal["warn", "strike", "unstrike", "pugban", "pugunban"], reason: str = None, **kwargs):
		self.target = target
		self.staff = staff
		self.type = type
		self.reason = reason
		self.strike_count: int = kwargs.get("strike_count")
		self.total_strike_count: int = kwargs.get("total_strike_count")

	def _get_title(self) -> str:
		title = "TF2CC Pug "
		if self.type == "warn": return title + "Warning"
		elif self.type == "strike": return title + "Strike"
		elif self.type == "unstrike": return title + "Strike Removed"
		elif self.type == "pugban": return title + "Ban"
		elif self.type == "pugunban": return title + "Ban Removed"

	def _get_user_desc(self) -> str:
		if self.type == "warn": return "You are being warned about some behaviour you have done in TF2CC pugs.\n"
		elif self.type == "strike": return "You have been pug striked.\n"
		elif self.type == "unstrike": return "Your pug strike has been removed.\n"
		elif self.type == "pugban": return "You have been pug banned from TF2CC pugs.\n"
		elif self.type == "pugunban": return "You have been unbanned from TF2CC pugs.\n"

	def _get_record_desc(self) -> str:
		if self.type == "warn": return f"{self.target.mention} ({str(self.target)}) was warned by {self.staff.mention}\n"
		elif self.type == "strike": return f"{self.target.mention} ({str(self.target)}) was pug striked by {self.staff.mention}\n"
		elif self.type == "unstrike": return f"Pug strike for {self.target.mention} ({str(self.target)}) was removed by {self.staff.mention}\n"
		elif self.type == "pugban": return f"{self.target.mention} ({str(self.target)}) was pug banned by {self.staff.mention}\n"
		elif self.type == "pugunban": return f"Pug ban for {self.target.mention} ({str(self.target)}) was removed by {self.staff.mention}\n"

	def _get_color(self) -> Color:
		if self.type == "warn": return Color.dark_red()
		elif self.type == "strike": return Color.red()
		elif self.type == "unstrike": return Color.green()
		elif self.type == "pugban": return Color.purple()
		elif self.type == "pugunban": return Color.magenta()

	def get_user_embed(self) -> Embed:
		embed = Embed(
			title = self._get_title(),
			description = self._get_user_desc(),
			color = self._get_color(),
			timestamp = utcnow()
		).set_footer(
			text = "TF2CC Pug Moderation",
			icon_url = TF2CC.icon_url
		)

		if self.type == "strike":
			embed.description += f"This is __strike #{self.strike_count}__.\n"
			embed.add_field(
				name = "Strike #1",
				value = "This is mostly a warning for your behavior. Reread and try not to break anymore pug rules.",
				inline = False
			).add_field(
				name = "Strike #2",
				value = f"This is your last warning before receiving a permanent pug ban. Temporary Ban: you can not play in pugs for a week.",
				inline = False
			).add_field(
				name = "Strike #3",
				value = "You are permanently banned from TF2CC pugs.",
				inline = False
			)
		elif self.type == "unstrike":
			embed.description += f"You now have __{self.strike_count} strike(s)__.\n"

		if self.reason is not None:
			embed.description += f"\nReason: {self.reason}"

		return embed

	def get_record_embed(self) -> Embed:
		embed = Embed(
			title = self._get_title(),
			description = self._get_record_desc(),
			color = self._get_color(),
			timestamp = utcnow()
		).set_footer(
			text = "TF2CC Pug Moderation",
			icon_url = TF2CC.icon_url
		)

		if self.type == "strike":
			embed.description += f"This is __strike #{self.strike_count}__.\n"
		elif self.type == "unstrike":
			embed.description += f"They now have __{self.strike_count} strike(s)__.\n"

		if self.strike_count is not None:
			time = utcnow().replace(hour = 0, minute = 0, second = 0, microsecond = 0)
			if self.strike_count == 1 and self.total_strike_count and self.total_strike_count == 1:
				embed.description += f"\n{self.target.mention}'s first strike will be removed {format_dt(time + timedelta(days = TF2CC.first_strike_duration), style = 'd')}.\n"
			elif self.strike_count == 2 and self.type == "strike":
				embed.description += f"\n{self.target.mention} now has a 7 day pug ban from TF2CC pugs.\nThe temporary pug ban will be removed {format_dt(time + timedelta(days = TF2CC.strike2_duration), style = 'd')}."
			elif self.strike_count > 2 and self.type == "strike":
				embed.description += f"\n{self.target.mention} is now permanently pug banned from TF2CC pugs.\n"

		if self.reason is not None:
			embed.description += f"\nReason: {self.reason}"

		return embed


# ~~~ SUPPORT TICKETS ~~~
SUPPORT2_TABLE_NAME = "support2"
SUPPORT2_TABLE_VALUES = ("owner_id", "channel_id")
SUPPORT2_TABLE_VALUE_TYPES = ("INTEGER", "INTEGER")
SUPPORT2_DB = ADB(
	TF2CC_DB_NAME,
	SUPPORT2_TABLE_NAME,
	SUPPORT2_TABLE_VALUES,
	SUPPORT2_TABLE_VALUE_TYPES
)

TICKET_EMBED = Embed(
	title = "TF2CC Support Ticket",
	description = f"""
Thank you for opening a ticket.
Please describe what issue(s) you are having and a staff member will attempt to resolve it.
If you have multiple issues, use this one support ticket for all of them.

If you know which staff member to ping for your issue, do not be afraid to do so.
"""
).set_footer(
	text = "TF2CC Support",
	icon_url = TF2CC.icon_url
)

class TicketInfo2:
	def __init__(self, info: dict[str, int]):
		self.info = info
		self.owner_id = info[SUPPORT2_TABLE_VALUES[0]]
		self.channel_id = info[SUPPORT2_TABLE_VALUES[1]]
