import re
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions
import asyncio
import json
from configparser import ConfigParser

initFile = 'init.ini'
settingsFile = 'settings.json'
init = ConfigParser()
init.read(initFile)

STATUS = init.get('main', 'status')
PREFIX = init.get('main', 'prefix')
TOKEN = init.get('main', 'token')

#TODO Add new servers on join to settings

class DiscordBot(commands.Bot):

    def __init__(self, *args, **kwargs):
        print("----------------------------------------")
        print('Welcome to RoleAssist for Discord')
        print("----------------------------------------")
        print("Status Set: " + STATUS)
        print("Prefix Set: " + PREFIX)
        print("Token Set: " + TOKEN)
        try:
            print("Settings.json found...")
            with open(settingsFile) as settings:
                self.settings = json.load(settings)
        except:
            print("Failed to find settings.json, creating new file...")
            with open(settingsFile, 'w') as settings:
                json.dump({},settings,indent=4)
            self.settings = {}
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        print("Updating server listing...")

        for guild in self.guilds:
            if str(guild.id) not in self.settings:
                print(guild.name + ".........failed")
                self.settings[guild.id] = {}
            else:
                print(guild.name + ".........passed")
        self.save()
        print("Server listings finished...")

    def save(self):
        with open(settingsFile, 'w') as file:
            json.dump(self.settings, file, indent=4)
        self.reload()

    def reload(self):
        with open('settings.json') as file:
            self.settings = json.load(file)


discordbot = DiscordBot(command_prefix=PREFIX)


@discordbot.command(name="testCommand")
@has_permissions(administrator=True)
async def testcmd(ctx):
    sent = await ctx.send("test reply")
    print(str(sent.id))


@testcmd.error
async def test_error(ctx, error):
    print(error)
    if isinstance(error, MissingPermissions):
        print("not admin")


@discordbot.command(name="TrackMessage", aliases=["TM", "trackmessage", "trackmsg", "trackMsg", "TrackMsg", "tm", "track"])
@has_permissions(administrator=True)
async def track(ctx, msgid):
    trash_msg = [ctx.message]
    try:
        tracking = await ctx.fetch_message(int(msgid))
    except:
        await ctx.send("**Command must be run in the same channel as the message you wish to track**", delete_after=10)
        await ctx.channel.delete_messages(trash_msg)
        return
    if str(msgid) not in discordbot.settings[str(ctx.guild.id)]:
        discordbot.settings[str(ctx.guild.id)][str(msgid)] = {}
        discordbot.save()
    else:
        trash_msg.append(await ctx.send("*Message already tracked*"))
        while True:
            trash_msg.append(await ctx.send("*Erase current settings? (yes/no)*"))
            reply = await discordbot.wait_for("message", check=lambda message: message.author == ctx.author, timeout=30)
            trash_msg.append(reply)
            if reply.content.lower() in ["no", "n", ""]:
                trash_msg.append(await ctx.send("*Exiting message tracking..."))
                return
            elif reply.content.lower() in ["yes", "y"]:
                discordbot.settings[str(ctx.guild.id)][str(msgid)] = {}
                discordbot.save()
                break
    sent = await ctx.send("*Please react to this message with the emote(s) you'd like to track. Reply with \"done\" when finished.*")
    trash_msg.append(sent)
    trash_msg.append(await discordbot.wait_for("message", check=lambda message: message.author == ctx.author and message.content.lower() == "done", timeout=300))
    sent = await ctx.fetch_message(sent.id)
    reactions = sent.reactions
    for reaction in reactions:
        trash_msg.append(await ctx.send("*Please mention the role(s) you'd like to give for  {.emoji}. Note, you may need to temporarily make the roles mentionable in their settings.*".format(reaction)))
        roles = await discordbot.wait_for("message", check=lambda message: message.author == ctx.author, timeout=60)
        trash_msg.append(roles)
        if roles is not None:
            discordbot.settings[str(ctx.guild.id)][str(msgid)][str(reaction.emoji)] = []
            for role in roles.role_mentions:
                discordbot.settings[str(ctx.guild.id)][str(msgid)][str(reaction.emoji)].append(str(role.id))
        discordbot.save()
        await tracking.add_reaction(reaction.emoji)
    trash_msg.append(await ctx.send("*Now tracking message for role assignments.*"))

    while True:
        trash_msg.append(await ctx.send("*Would you like me to clear up the mess we made? (yes/no)*"))
        reply = await discordbot.wait_for("message", check=lambda message: message.author == ctx.author, timeout=30)
        trash_msg.append(reply)
        if reply.content.lower() in ["no", "n", ""]:
            return
        elif reply.content.lower() in ["yes", "y"]:
            await ctx.send("**GOODBYE**", delete_after=5)
            await asyncio.sleep(2)
            await ctx.channel.delete_messages(trash_msg)
            break


@discordbot.command(name="UntrackMessage", aliases=["UM", "untrackmessage", "untrackmsg", "untrackMsg", "UnTrackMsg", "utm", "untrack", "UT", "ut"])
@has_permissions(administrator=True)
async def untrack(ctx, msgid):
    try:
        tracking = await ctx.fetch_message(int(msgid))
    except:
        await ctx.send("**Command must be run in the same channel as the message you wish to track**", delete_after=10)
        await ctx.channel.delete_messages([ctx.message])
        return
    try:
        del discordbot.settings[str(ctx.guild.id)][str(msgid)]
        discordbot.save()
        await tracking.clear_reactions()
        await ctx.send("*Message is no longer tracked.*", delete_after=5)
    except KeyError:
        await ctx.send("*Message was not being tracked.*", delete_after=5)
    await ctx.channel.delete_messages([ctx.message])


@discordbot.event
async def on_raw_reaction_add(payload):
    if str(payload.user_id) == str(discordbot.user.id):
        pass
    else:
        guild_id = str(payload.guild_id)
        guild = discordbot.get_guild(payload.guild_id)
        message = str(payload.message_id)
        emoji = str(payload.emoji)
        member = guild.get_member(payload.user_id)
        if guild_id in discordbot.settings:
            if message in discordbot.settings[guild_id]:
                if emoji in discordbot.settings[guild_id][message]:
                    roles = discordbot.settings[guild_id][message][emoji]
                    for role_id in roles:
                        await member.add_roles(discord.utils.get(guild.roles, id=int(role_id)), reason="Auto Assign")


@discordbot.event
async def on_raw_reaction_remove(payload):
    if str(payload.user_id) == str(discordbot.user.id):
        pass
    else:
        guild_id = str(payload.guild_id)
        guild = discordbot.get_guild(payload.guild_id)
        message = str(payload.message_id)
        emoji = str(payload.emoji)
        member = guild.get_member(payload.user_id)
        if guild_id in discordbot.settings:
            if message in discordbot.settings[guild_id]:
                if emoji in discordbot.settings[guild_id][message]:
                    roles = discordbot.settings[guild_id][message][emoji]
                    for role_id in roles:
                        await member.remove_roles(discord.utils.get(guild.roles, id=int(role_id)), reason="Auto Assign")


async def mainDiscord(bot):
    await bot.login(TOKEN, bot=True)
    await bot.connect()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.create_task(mainDiscord(discordbot))
        loop.run_forever()
    except discord.LoginFailure:
        print('RoleAssist Failed to Login: Invalid Credentials.\n'
              'This may be a temporary issue, consult Discords\n'
              'Login Server Status before attemping again.\n'
              'If servers are working properly, you may need\n'
              'a new token. Please replace the token in the\n'
              'GuildBot.ini file with a new token.\n')
    except KeyboardInterrupt:
        loop.run_until_complete(discordbot.logout())
    except Exception as e:
        print("Fatal exception, attempting graceful logout.\n{}".format(e))
        loop.run_until_complete(discordbot.logout())
    finally:
        loop.close()
        exit(1)