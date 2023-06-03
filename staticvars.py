# any hard coded variables / settings go here

# TF2 RGL competitive maps
# these will need to be updated every season
COMP_MAPS = [
	"cp_granary_pro_rc8",
	"cp_gullywash_f9",
	"cp_metalworks_f4",
	"cp_process_f12",
	"cp_snakewater_final1",
	"cp_steel_f12",
	"cp_sultry_b8",
	"cp_sunshine",
	"koth_ashville_final",
	"koth_bagel_rc5",
	"koth_cascade",
	"koth_clearcut_b15d",
	"koth_lakeside_r2",
	"koth_product_final",
	"koth_proot_b5a",
	"pl_swiftwater_final1",
	"pl_upward_f10",
	"pl_vigil_rc9"
]

# LOGS API
LOGS_API_GET_LOG = "https://logs.tf/json/{log_id}"
LOGS_API_GET_LOG_IDS = "https://logs.tf/api/v1/log?player={steam_ids}&limit=1"

# TF2CC Guild Info
class TF2CC:
	guild_id = 727627956058325052
	icon_url = "https://static-cdn.jtvnw.net/jtv_user_pictures/20cb89d0-42fc-4bc9-b083-91c9c895b782-profile_image-70x70.png"

	# support channels
	support_category_id = 930255481807720478
	ticket_channel_id = 930255788717510707

	# roles
	verified_rid = 728650647410311208

	# staff roles
	pug_runner_rid = 894345215857541160
	event_runner_rid = 736307593114550303
	coach_rid = 727677448417968211
	moderator_rid = 727677507725164544
	admin_rid = 730453127513243751
	owner_rid = 727677404473983027

	# staff channels
	event_runner_cid = 736314342043156490
	bot_commands_cid = 844343298977693706
	mod_chat_cid = 743553564659548262

	# pug roles
	level0_rid = 757387934327504937
	level1_rid = 757387898952876132
	level2_rid = 757387972084498433
	level3_rid = 757388007190822913
	pug_strike1_rid = 745457573876072478 # strike 1
	pug_strike2_rid = 820053700881809428 # strike 2
	pug_strike3_rid = 820053777096507432 # pug ban
	pug_rid = 736462589906911235
	steam_linked_rid = 948079021818773544

	scout_ban_rid = 830652013695467530
	soldier_ban_rid = 830652108868157451
	demoman_ban_rid = 830652154062176296
	sniper_ban_rid = 830652244226867200
	spy_ban_rid = 830652623837200416
	medic_lock_rid = 830652292709220353

	# pug channels
	pug_strike_cid = 747482111262457946
	pug_log_cid = 736465109345370223

	reg_pug_waiting_cid = 736240304000335924
	reg_pug_next_game_cid = 736305576652308621
	reg_pug_red1_cid = 736241159009075271
	reg_pug_red2_cid = 736310067833470986
	reg_pug_blu1_cid = 736241231327264838
	reg_pug_blu2_cid = 736310082081521695

	new_pug_waiting_cid = 932730588182499368
	new_pug_next_game_cid = 932730639587881061
	new_pug_red1_cid = 932730500362154034
	new_pug_blu1_cid = 932730478811820052
	new_pug_red2_cid = 972252472154411040
	new_pug_blu2_cid = 972252554115285064

	# other pug info
	first_strike_duration = 45
	strike2_duration = 7
	class_emojis = {
		"1": "<:scout:736686300291268669>",
		"2": "<:soldier:736689552915300475>",
		"4": "<:demo:736690362579550308>",
		"7": "<:medic:736695729850023986>",
		"8": "<:sniper:736698205315661864>",
		"9": "<:spy:736695847429079051>"
	}
