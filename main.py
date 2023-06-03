# this is the file that will run the bot
# all settings should be edited in this file

from logging import DEBUG, INFO
from nextcord import Intents, Interaction
from os import getenv, listdir

from bot import TF2CCBot


version = "2.5.2"
persistent_views_count = 2


# intents are required for the bot to function
# each intent enables a different feature
# e.g.
# 	guild intent populates guild info in the bot's cache
# 	member intent populates member info in the bot's cache
# 	message_content populates message info in the bot's cache
# most of these intents are "priviliged" intents and may be revoked by Discord at any time
intents = Intents(
    guilds = True,
    members = True,
    messages = True,
    message_content = True,
    voice_states = True
)


# only allow the bot to join these guilds
# add or remove IDs as necessary
valid_guild_ids = (
	727627956058325052, # TF2CC
	651588344584601605 # Jamil Test Server
)
test_guild_id = 651588344584601605


# prepare the cog file paths to add to the bot
cog_location = "cogs"
cogs = list()
for cog_name in listdir(cog_location):
	if not cog_name.endswith("Cog.py"):
		continue

	cogs.append(f"{cog_location}.{cog_name[:-3]}")


bot = TF2CCBot(
	version = version,
	debug_level = INFO,
	valid_guild_ids = valid_guild_ids,
	cogs = tuple(cogs),
	#activity = Game(f"{COMMAND_PREFIXhelp for more info}")
	command_prefix = None, # currently no command prefix - this would be for prefix commands
	help_command = None, # remove the default help command
	intents = intents,
	case_insensitive = True, # can be upper or lower case command prefix
	max_messages = None # do not store any messages in the cache
)
bot.persistent_views_count = persistent_views_count


@bot.slash_command(name = "stop", guild_ids = [test_guild_id])
async def stop_bot(intr: Interaction):
	# shut down the bot
	bot.log.debug("stop slash cmd - Stopping TF2CC Bot")
	await intr.send("Stopping TF2CC Bot", ephemeral = True)
	await bot.close()


@bot.slash_command(name = "reload_cog", guild_ids = [test_guild_id])
async def reload_cog(intr: Interaction, cog_name: str):
	# reload a cog
	# if changes were made in the cog file, then they will reflect on the bot after reloading the cog
	if cog_name not in bot.loaded_cogs:
		await intr.send(f"Invalid cog name: `{cog_name}`.", ephemeral = True)
		return
	
	await intr.response.defer(ephemeral = True)
	bot.reload_extension(cog_name)
	await bot.sync_application_commands()
	bot.log.debug(f"reloaded cog {cog_name!r}")
	await intr.send(f"Reloaded `{cog_name}`.")

@reload_cog.on_autocomplete("cog_name")
async def reload_cog_autocomplete(intr: Interaction, cog_name: str):
	cog_names = bot.loaded_cogs[:]
	if cog_name:
		cog_names = [cog for cog in cog_names if cog_name.lower() in cog.lower()]
	cog_names = cog_names[:25] # can only have 25 options
	await intr.response.send_autocomplete(cog_names)


if __name__ == "__main__":
	bot.run(getenv("BOT_TOKEN"))
