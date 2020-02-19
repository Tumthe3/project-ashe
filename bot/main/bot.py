# -*- coding: utf-8 -*-
import datetime
import logging
import re
import discord

import psycopg2
from imgurpython import ImgurClient

from main import commands
from main import database
from main import settings

class Bot(object):
    """
    Args:
        client (discord.Bot): The bot instance.
        
    """
    
    def __init__(self, logger=None, **options):
        self.logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        command_prefix = ";"
        description = settings.DESCRIPTION

        self.client = discord.ext.commands.Bot(command_prefix=command_prefix, description=description, **options)

    def run(self):
        database.setup()
        self.set_events()
        self.set_commands()
        self.client.run(settings.CLIENT_TOKEN, reconnect=True)

    def event_ready(self):
        async def on_ready():
            prefix = ";"
            self.logger.info(f"{self.client.user.name} (ID: {self.client.user.id}) is now online.")
            status = f"DDR | {prefix}help for help"
            await self.client.change_presence(activity=discord.Game(name=status))

        return on_ready

    def event_message(self):
        async def on_message(message):
            async def check_content(message, check, custom_message):
                if check:
                    content = message.clean_content
                    try:
                        await message.delete()
                    except (discord.Forbidden, discord.HTTPException) as e:
                        self.logger.warning(f"Unable to delete message at {message.jump_url}. {e}")
                    else:
                        await self.say(message.author, f"{custom_message}\nYour message: ```{content}```")
                        return True

                return False

            user = message.author
            roles = {
                5: 533369804334039061,
                10: 533369803965071381,
                20: 533369912207474706,
                30: 533369949591175169,
                50: 573702137918390272
            }
            servers = {
                533368376148361216: {
                    "roles": {
                        5: 533369804334039061,
                        10: 533369803965071381,
                        20: 533369912207474706,
                        30: 533369949591175169,
                        50: 573702137918390272
                    },
                    "pics-only": {
                        #548737482108174337: f"To keep #selfies clean, only posts with pictures are allowed. Feel free to post comments in #general!",
                        538110190902312976: f"To keep #lets-draw clean, only posts with pictures are allowed. Discuss art in #lets-draw-discussion!"
                    },
                    "no-pics": {
                        533377545865789441: f"To keep #general clean, posts with pictures are put in #memes-links-pics instead!",
                        535908960713310220: f"To keep #nsfw-chat clean, posts with pictures are put in #nsfw-memes-links-pics instead!"
                    },
                    "no-links": {
                        533377545865789441: f"To keep #general clean, posts with links are put in #memes-links-pics instead!",
                        535908960713310220: f"To keep #nsfw-chat clean, posts with links are put in #nsfw-memes-links-pics instead!"
                    }
                },
                662365002556243993: {
                    "roles": {
                        5: 668184294983991316,
                        8: 662394541202079744
                    },
                    "pics-only": {}
                }
            }
            if message.guild:
                self.logger.info(f"({message.guild.name} - {message.channel.name}) {user.name}: {message.content}")
            else:
                try:
                    self.logger.info(f"({message.channel.name}) {user.name}: {message.content}")
                except AttributeError:
                    self.logger.info(f"({user.name}) {message.content}")
                finally:
                    return
            
            if user.id == 159985870458322944 and message.guild.id in servers:  # MEE6 Bot
                result = re.compile(r"GG <@(?:.+)>, you just advanced to level ([0-9]+)!").match(message.content)
                if result:
                    mentioned = message.mentions[0]
                    level = int(result.group(1))
                    self.logger.info(f"{mentioned.name} reached level {level}")

                    roles = servers[message.guild.id].get("roles")
                    for r in roles:
                        if level >= r:
                            role = discord.utils.get(message.guild.roles, id=roles[r])
                            await mentioned.add_roles(role, reason=f"User reached level {r}")
            else:
                guild = message.guild
                channel = message.channel

                if guild.id in servers and channel.id in servers[guild.id]["pics-only"]:
                    if await check_content(
                        message,
                        not message.attachments,
                        servers[guild.id]["pics-only"][channel.id]
                    ):
                        return
                """
                if guild.id in servers and channel.id in servers[guild.id]["no-pics"]:
                    if await check_content(
                        message,
                        message.attachments,
                        servers[guild.id]["no-pics"][channel.id]
                    ):
                        return
                if guild.id in servers and channel.id in servers[guild.id]["no-links"]:
                    if await check_content(
                        message,
                        re.search(URL_REGEX, message.clean_content),
                        servers[guild.id]["no-links"][channel.id]
                    ):
                        return
                """

            await self.client.process_commands(message)

        return on_message

    def event_edit(self):
        async def on_message_edit(before, after):
            def log_message(message, content):
                if message.guild:
                    self.logger.info(f"({message.guild.name} - {message.channel.name}){content}")
                else:
                    try:
                        self.logger.info(f"({message.channel.name}){content}")
                    except AttributeError:
                        self.logger.info(f"({message.author.name}){content}")


            if before.pinned and not after.pinned:
                log_message(after, f"<Unpinned> {after.author.display_name}: {after.content}")
            elif not before.pinned and after.pinned:
                log_message(after, f"<Pinned> {after.author.display_name}: {after.content}")

            if before.content != after.content:
                log_message(after, f"<Old message> {after.author.display_name}: {before.content}")
                log_message(after, f"<Edited> {after.author.display_name}: {after.content}")

        return on_message_edit
    
    def event_member_update(self):
        async def on_member_update(before, after):
            servers = {
                533368376148361216: {
                    "welcome": {
                        "role": 533499454964105245,
                        "channel": "general-chat"
                    }
                },
                662365002556243993: {
                    "welcome": {
                        "role": 662376437168472094,
                        "channel": "general-chat"
                    }
                },
                670671037343727646: {
                    "welcome": {
                        "role": 670675588683399189,
                        "channel": "general-chat"
                    }
                }
            }

            if after.guild.id in servers:
                before_roles = [r.id for r in before.roles]
                after_roles = [r.id for r in after.roles]
                welcome_info = servers[after.guild.id]["welcome"]
                if welcome_info["role"] not in before_roles and welcome_info["role"] in after_roles:
                    welcome_channel = discord.utils.get(after.guild.channels, name=welcome_info["channel"])
                    
                    # Say welcome message
                    welcome_message = ""
                    if after.guild.id == 533368376148361216:
                        guide_channel = discord.utils.get(after.guild.channels, id=675172372323762178)
                        help_channel = discord.utils.get(after.guild.channels, id=615047779701620776)
                        welcome_message = f"Welcome to the server, {after.mention}! Be sure to check out {guide_channel.mention} If you have any questions, feel free to message a moderator or post in {help_channel.mention}."
                    elif after.guild.id == 662365002556243993:
                        intro_channel = discord.utils.get(after.guild.channels, id=662366496215007257)
                        roles_channel = discord.utils.get(after.guild.channels, id=662365391968010260)
                        welcome_message = f"Greetings, {after.mention}. State thy intro in {intro_channel.mention} and declare thy titles in {roles_channel.mention}."
                    elif after.guild.id == 670671037343727646:
                        roles_channel = discord.utils.get(after.guild.channels, name="roles")
                        welcome_message = f"Welcome to {after.guild.name}, {after.mention}! Grab some {roles_channel.mention} and have fun."

                    await self.say(welcome_channel, welcome_message)
            
            return
        
        return on_member_update

    async def say(self, channel, message, context=None):
        await channel.send(content=message)
    
    def set_commands(self, *cmds):
        self.client.add_cog(commands.Admin(self))
        self.client.add_cog(commands.Statistics(self))

        for c in cmds:
            self.client.add_cog(c)
        
    def set_events(self, *events):
        self.client.event(self.event_ready())
        self.client.event(self.event_message())
        self.client.event(self.event_edit())
        self.client.event(self.event_member_update())

        for e in events:
            self.client.event(e)
