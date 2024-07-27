from unittest import result
#from model import *
from bracket.bracketcreator import get_cuppicture
from ipaddress import ip_address
import threading
import requests
import random
import re
import logging
from datetime import datetime
import time
from ircconnection import IrcConnector
from discordconnection import DiscordConnector
from dbconnection import DatabaseConnector

logger = logging.getLogger("friedybot")

class FriedyBot:
    def __init__(self, settings, cmdresults, xonotic):
        self.pickupText = "Pickups: "
        self.picktimer = None
        self.settings = settings
        self.cmdresults = cmdresults
        self.xonotic = xonotic
        self.ircconnect = None
        self.discordconnect = None
        self.thread_lock = None
        self.topic = ""
        self.dbconnect = DatabaseConnector()

    def run(self):
        self.thread_lock = threading.Lock()
        self.ircconnect = IrcConnector(self.settings["irc"], self.thread_lock, self)
        self.discordconnect = DiscordConnector(self.settings["discord"], self.thread_lock, self)

        t1 = threading.Thread(target=self.ircconnect.run)
        t1.daemon = True                                    # Thread dies when main thread (only non-daemon thread) exits.
        t1.start()

        self.discordconnect.run()
        self.ircconnect.close()
    
    def start_pugtimer(self):
        #background timer to warn players of expiring pickup games or deletes old pickup games
        warntime = self.settings["bot"]["pugtimewarning"]
        deletetime = self.settings["bot"]["pugtimeout"]
        while True:
            mindiff = warntime
            currenttime = datetime.now()      
            if self.dbconnect.has_active_games(): #pugentries.exists():

                mindiff, has_break, has_new_text, warn_user = self.dbconnect.pugtimer_step(mindiff, currenttime, deletetime, warntime)
                
                #player was over the time and got remove from game
                if has_new_text:
                    self.build_pickuptext()

                #player gets notified: "Your added games will expire in 20 minutes, type !renew to renew your games"
                if warn_user:
                    if warn_user["chattype"] == "irc":
                        self.send_notice(warn_user["user"], self.cmdresults["misc"]["pugtimewarn"], warn_user["chattype"])
                    else:
                        self.send_notice(None, warn_user["user"] +  " " + self.cmdresults["misc"]["pugtimewarn"], warn_user["chattype"])

                if has_break:
                    break
                if not self.dbconnect.has_active_games():
                    return
                else:
                    time.sleep(mindiff)
            else:
                return

    def set_irc_topic(self):
        #sets the current pickups as irc topic
        logger.info("set_irc_topic")
        try:
            if  self.pickupText != "Pickups: ":
                self.ircconnect.connection.topic(self.settings["irc"]["channel"], new_topic=self.pickupText)
            else:
                self.ircconnect.connection.topic(self.settings["irc"]["channel"], new_topic=self.topic)
        except Exception as e:
            logger.error("Something wrong with topic: ", e)
    
    def send_command(self, user, argument, chattype, isadmin):
        #forwards commands from irc/discord to bot specific command
        logger.info("send_command: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        argument = argument.split()
        method_name = 'command_' + str(argument[0][1:].lower())
        method = getattr(self, method_name, self.wrong_command)
        with self.thread_lock:
            try:
                method(user, argument, chattype, isadmin)
            except Exception as e:
                self.send_notice(user, "Sorry, something went wrong", chattype)
                logger.error("Error in command:", e)

    def send_notice(self, user, message, chattype):
        #sends message to only discord or to specific irc-user (for future: send direct message to discord-user)
        logger.info("send_notice: user=%s, message=%s, chattype=%s", user, message, chattype)
        if chattype == "irc":
            self.ircconnect.send_single_message(user,message)
        else:
            self.discordconnect.send_my_message(message)

    def send_all(self, message, ircmessage = None):
        #sends message to all (irc and discord)
        logger.info("send_all: message=%s, ircmessage=%s", message, ircmessage)
        if ircmessage is not None:
            self.ircconnect.send_my_message(ircmessage)
        else:
            self.ircconnect.send_my_message(message)
        self.discordconnect.send_my_message(message)
    
    def wrong_command(self, user, argument, chattype, isadmin):
        #if user inputs wrong command
        logger.info("wrong_command: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        self.send_notice(user, self.cmdresults["misc"]["wrongcommand"], chattype)

    def change_name(self, oldnick, newnick):
        #changes irc-name of users in case of nickname changes
        logger.info("change_name: oldnick=%s, newnick=%s", oldnick, newnick)
        self.dbconnect.set_irc_nickname(oldnick, newnick)

    def remove_user_on_exit(self, user,chattype):
        #removes user from all pickups in case of disconnect
        logger.info("remove_user_on_exit: user=%s, chattype=%s", user, chattype)
        gameentries = None
        player = None
        
        try:                        
            result = self.dbconnect.withdraw_player_from_pickup(user, chattype=chattype)
            if result:
                self.build_pickuptext()
        except Exception as e:
            logger.error("Error in remove_user_on_exit: ", e)

    def build_pickuptext(self):
        #sends current pickup games to all channels
        #result: "Pickups: duel (1/2) 2v2tdm (1/4)"        
        logger.info("build_pickuptext")   
        games_exists = self.dbconnect.has_active_games()
        pickuptext_new = self.dbconnect.get_pickuptext()
        if not games_exists and self.pickupText == "Pickups: ":
            self.set_irc_topic()
            return

        if not games_exists and self.pickupText != "Pickups: ":            
            self.pickupText = "Pickups: " 
            self.send_all(self.pickupText)     
            self.set_irc_topic()  
        else:
            self.pickupText = "Pickups: "
            self.pickupText += pickuptext_new
            self.send_all(self.pickupText)
            self.set_irc_topic()
        return self.pickupText
    """
    Commands for IRC and discord
        Naming Convention for bot methods is command_yourcommand
        example:
            def command_hug(self, user, argument, chattype, isadmin):
                user: irc-username or discord author-object
                argument: array of user typed command for example: !add duel 2v2tdm -> [!add, duel, 2v2tdm]
                chattype: incoming message type ("irc"/"discord")
                isAdmin: is user in discord-moderator-role (see settings.json) or is irc-operator
    """

    def command_register(self, user, argument, chattype, isadmin):
        #command to connect player in database with their XonStats-account
        logger.info("command_register: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        xonstatsId: str = argument[1]
        error_message: str = ""
        discord_name: str = ""
        irc_name: str = ""
        error_message, discord_name, irc_name = self.dbconnect.register_player(user, xonstatsId, chattype)

        if error_message == "":                           
            if chattype == "irc":
                self.send_all(self.cmdresults["misc"]["registsuccess"].format(user, xonstatsId, discord_name), 
                              self.cmdresults["misc"]["registsuccess"].format(user, xonstatsId, irc_name))
            else:
                self.send_all(self.cmdresults["misc"]["registsuccess"].format(user.name, xonstatsId, discord_name), 
                              self.cmdresults["misc"]["registsuccess"].format(user.name, xonstatsId, irc_name))
        else: 
            self.send_notice(user, error_message, chattype)

    def command_add(self, user, argument, chattype, isadmin):
        # command to add player to pickup games
        logger.info("command_add: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        result: bool = False
        error_messages: list[str] = []
        found_match: dict = {}
        gametypes: list[str] = argument[1:]

        result, error_messages, found_match = self.dbconnect.add_player_to_games(user, gametypes, chattype)
        if result:
            # match found ready to notify player 
            if found_match:
                # match with teams and captains
                if found_match["has_teams"]:
                    for i in range(0,len(found_match["irc"])):
                        self.send_all(found_match["discord"][i], found_match["irc"][i])
                else:
                    self.send_all(found_match["discord"], found_match["irc"])

            #start the background timer to delete old pickup games
            if self.picktimer is None or not self.picktimer.is_alive():
                self.picktimer = threading.Thread(target=self.start_pugtimer, daemon=True)
                self.picktimer.start()
            self.build_pickuptext()
        
        for error_message in error_messages:
            self.send_notice(user, error_message, chattype)

    def command_pickups(self, user, argument, chattype, isadmin):
        # command to know all available game types
        logger.info("command_pickups: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        result: str = "Possible gametypes: "
        result += ", ".join(self.dbconnect.get_gametype_list())
        self.send_notice(user, result, chattype)

    def command_remove(self, user, argument, chattype, isadmin):
        # command to remove player from pickup games
        logger.info("command_remove: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        #TODO errormessages for wrong gametype
        gametypes = argument[1:]
        
        result = self.dbconnect.withdraw_player_from_pickup(user, gametypes, chattype)
        
        if result:            
            return self.build_pickuptext() 
        else:
            self.send_notice(user, "No game added!", chattype)

    def command_pull(self, user, argument, chattype, isadmin):
        # removes pickup player from games (just discord-moderators or irc-operators)
        logger.info("command_pull: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        if isadmin:
            if len(argument) > 1:
                result: bool = False
                not_existing_players = []
                for arg in argument[1:]:
                    result = self.dbconnect.withdraw_player_from_pickup(arg)
                    if not result:
                        not_existing_players.append(arg)
                
                if len(not_existing_players) > 0:
                    self.send_notice(user, "The following player(s) was/were not added! →" + ", ".join(not_existing_players), chattype)
                
                if len(not_existing_players) != len(argument[1:]):
                    self.build_pickuptext()
        else:
            self.send_notice(user, self.cmdresults["misc"]["restricted"], chattype)
        
    def command_renew(self, user, argument, chattype, isadmin):
        logger.info("command_renew: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        gametypes: list[str] = argument[1:]
        error_message: str = ""

        error_message = self.dbconnect.renew_pickupentry(user, gametypes, chattype)

        if error_message:
            self.send_notice(user, error_message, chattype)
        

    def command_who(self, user, argument, chattype, isadmin):
        # command that shows list of pickup games and their players
        logger.info("command_who: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        result = self.dbconnect.get_active_games_and_players()
        self.send_notice(user, result, chattype)

    def command_server(self, user, argument, chattype, isadmin):
        # !server without arguments shows all available servers
        logger.info("command_server: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        if len(argument) == 1:
            wrongs_server, resultText = self.dbconnect.get_server()
            self.send_all("Available servers: " + resultText)

        #shows specific servers from arguments
        #example: !server dogcity
        else:
            wrongs_server, resultText = self.dbconnect.get_server(argument[1])
            if wrongs_server:
                self.send_notice(user, resultText, chattype)
            else:
                self.send_all(resultText)

    def command_addserver(self, user, argument, chattype, isadmin):
        #command to add servers with their ip:port to database
        logger.info("command_addserver: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        message: str = ""
        server_name: str = argument[1] if len(argument) > 1 else None
        server_address: str = argument[2] if len(argument) > 2 else None
        
        if isadmin:
            if server_address:            
                try:
                    ip = server_address.split(":")[0]
                    sanitized_ip_and_port: str = server_address.replace('[','').replace(']','')
                    ip = ":".join(sanitized_ip_and_port.split(":")[:-1])
                    logger.info("command_addserver: ip=%s", ip)
                    ip_address(ip)
                    message = self.dbconnect.add_server(server_name, sanitized_ip_and_port)
                    self.send_notice(user, message, chattype) 
                except ValueError:
                    self.send_notice(user, "Not a valid IP-address! To add server: !addserver <servername> <ip:port>", chattype)
            else:
                self.send_notice(user, self.cmdresults["cmds"]["addserver"], chattype)
        else:
            self.send_notice(user, self.cmdresults["misc"]["restricted"],chattype)
    
    def command_addgametype(self, user, argument, chattype, isadmin):
        #command to add gametype to database (duel, 2v2tdm)
        #Usage: !addgametype <gametypetitle> <playercount> <teamcount> <statsname>
        #example: !addgametype 2v2v2ca 6 3 ca
        logger.info("command_addgametype: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        message: str = ""
        gt_title: str = argument[1] if len(argument) > 1 else None
        gt_playercount: str = argument[2] if len(argument) > 2 and argument[2].isdigit() else None
        gt_teamcount: str = argument[3] if len(argument) > 3 and argument[3].isdigit() else gt_playercount
        gt_xonstatname: str = argument[4] if len(argument) > 4 else None

        if isadmin:
            if gt_playercount:
                message = self.dbconnect.add_gametypes(gt_title, gt_playercount, gt_teamcount, gt_xonstatname)
            else:
                message = self.cmdresults["cmds"]["addgametype"]                
            self.send_notice(user, message, chattype) 
        else:
            self.send_notice(user, self.cmdresults["misc"]["restricted"], chattype)

    def command_removeserver(self, user, argument, chattype, isadmin):
        #command to remove server from database
        logger.info("command_removeserver: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        messages = []
        serverlist = argument[1:]

        if isadmin:
            messages = self.dbconnect.delete_server(serverlist)
            for message in messages:
                self.send_notice(user, message, chattype)            
        else:
            self.send_notice(user, self.cmdresults["misc"]["restricted"], chattype)
    
    def command_removegametype(self, user, argument, chattype, isadmin):
        #command to remove gametype from database
        logger.info("command_removegametype: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        messages = []
        gametypes = argument[1:]

        if isadmin:
            messages = self.dbconnect.delete_gametypes(gametypes)
            for message in messages:
                self.send_notice(user, message, chattype)
        else:
            self.send_notice(user, self.cmdresults["misc"]["restricted"], chattype)
    
    def command_help(self, user, argument, chattype, isadmin):
        #command for general overview of commands
        #or with arguments help for specific command
        logger.info("command_help: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        if isadmin:
            if len(argument) > 1 and self.cmdresults["cmds"][argument[1]] is not None:
                self.send_notice(user, self.cmdresults["cmds"][argument[1]], chattype)
            else:
                self.send_notice(user, self.cmdresults["misc"]["helpadmin"], chattype)
        else:
            if len(argument) > 1 and self.cmdresults["cmds"][argument[1]] is not None:
                self.send_notice(user, self.cmdresults["cmds"][argument[1]], chattype)
            else:
                self.send_notice(user, self.cmdresults["misc"]["help"], chattype)

    def command_kill(self, user, argument, chattype, isadmin):
        #command for marking users with xonotic flavour
        #example: !kill DrJaska
        #result: "DrJaska felt the electrifying air of Seek-y's Electro combo"
        logger.info("command_kill: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        killer = ""
        if chattype == "irc":
            killer = user
        else:
            killer = user.name

        if len(argument) > 1:    
            #get victim name        
            victim = argument[1]
            #fill user list with discord/irc users
            discord_users = self.discordconnect.get_online_members()
            irc_users = list(self.ircconnect.channels[self.settings["irc"]["channel"]]._users.keys())
            #random chance 
            is_random_chance = random.random() <= self.xonotic["chance"]
            #victim is real user
            is_real_irc_user = victim in irc_users
            is_real_discord_user = victim in discord_users
            is_real_user = is_real_irc_user or is_real_discord_user

            if is_random_chance or (victim == killer) or not is_real_user:
                self.send_all(random.choice(self.xonotic["suicides"]).format(killer))
            else:
                self.ircconnect.send_my_message(random.choice(self.xonotic["kills"]).format(killer, victim))                
                if is_real_discord_user:
                    victim = "@" + victim
                self.discordconnect.send_my_message_with_mention(random.choice(self.xonotic["kills"]).format(killer, victim))
        else:
            self.send_all(random.choice(self.xonotic["suicides"]).format(killer))

    def command_bridge(self, user, argument, chattype, isadmin):
        #toggle on/off if specific user-messages should be bridged (future)
        logger.info("command_bridge: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        #TODO: implement bridge command
    
    def command_cupstart(self, user, argument, chattype, isadmin):
        #creates cup brackets and uploads to discord
        #example: !cupstart seeky-cup Seek-y Grunt hotdog packer
        logger.info("command_cupstart: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
 
        cuppath = get_cuppicture(argument, self.settings["bot"]["browser"])
        self.discordconnect.send_my_file(cuppath)
        self.send_all("Generate Cup...")

    def command_online(self, user, argument, chattype, isadmin):
        logger.info("command_online: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)

        if chattype == "irc":
            self.ircconnect.send_my_message("Online are: " + ", ".join(self.discordconnect.get_online_members()))
        else:
            self.discordconnect.send_my_message("Online are: " + ", ".join(self.ircconnect.channels[self.settings["irc"]["channel"]]._users.keys()))

    def command_lastgame(self, user, argument, chattype, isadmin):
        logger.info("command_lastgame: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        result = self.dbconnect.get_lastgame(chattype)       
        self.send_notice(user, result, chattype)
        
    def command_subscribe(self, user, argument, chattype, isadmin):
        logger.info("command_subscribe: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        result: bool = False
        message: str = ""
        discord_name: str = ""
        gametype_args = set(argument[1:])
        new_subscriptions = []
        
        if gametype_args:
            for gametype_entry in gametype_args:
                result, message, discord_name = self.dbconnect.add_subscription(user, gametype_entry, chattype)

                if result:
                    new_subscriptions.append(gametype_entry)
                    if discord_name:
                        self.discordconnect.give_role(discord_name, gametype_entry)
                else:
                    self.send_notice(user, message, chattype)
            if not new_subscriptions:
                self.command_pickups(user, argument, chattype, isadmin)
            else:
                self.send_notice(user, "You are now subscribed to: " + ", ".join(new_subscriptions), chattype)
        else:
            subscriptions = self.dbconnect.get_subscriptions(user, chattype)
            if subscriptions:                
                self.send_notice(user, "You are subscribed to: " + ", ".join([x for x in subscriptions]), chattype)
            else:
                self.command_pickups(user, argument, chattype, isadmin)

    def command_unsubscribe(self, user, argument, chattype, isadmin):
        logger.info("command_unsubscribe: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        gametype_args = set(argument[1:])
        message: str = ""
        discord_name: str = ""

        if gametype_args:
            for gametype_entry in gametype_args:
                message, discord_name = self.dbconnect.delete_subscription(user, gametype_entry, chattype)
                if message:
                    self.send_notice(user, message, chattype)
                else:
                    if discord_name:
                        self.discordconnect.take_role(discord_name, gametype_entry)
                
        else:            
            subscriptions = self.dbconnect.get_subscriptions(user, chattype)
            for gametype_entry in subscriptions:
                message, discord_name = self.dbconnect.delete_subscription(user, gametype_entry, chattype)
                if message:                    
                    self.send_notice(user, message, chattype)                    
                else:
                    if discord_name:
                        self.discordconnect.take_role(discord_name, gametype_entry)

        subscriptions = self.dbconnect.get_subscriptions(user, chattype)

        if subscriptions:
            self.send_notice(user, "You are subscribed to: " + ", ".join([x for x in subscriptions]), chattype)
        else:
            self.send_notice(user, "You are subscribed to nothing!", chattype)

    def command_promote(self, user, argument, chattype, isadmin):
        logger.info("command_promote: user=%s, argument=%s, chattype=%s, isadmin=%s", user, argument, chattype, isadmin)
        #TODO promote for more than one gametype and also for irc
        self.discordconnect.send_my_message_with_mention("Add to play game @player_" + argument[1])

