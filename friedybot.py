from unittest import result
from model import *
from bracket.bracketcreator import get_cuppicture
from ipaddress import ip_address
import threading
import requests
import random
from datetime import datetime
import time
from ircconnection import IrcConnector
from discordconnection import DiscordConnector

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

        db.connect()
        queryset = PickupGames.delete().where(PickupGames.isPlayed == False)
        queryset.execute()
        db.close()

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
            pugentries = PickupEntries.select().join(PickupGames).where(PickupGames.isPlayed == False).order_by(PickupEntries.addedDate.asc())
            if pugentries.exists():
                for pugentry in pugentries:
                    pugdiff = round((currenttime - pugentry.addedDate).total_seconds())
                    if pugdiff >= deletetime:
                        gid = pugentry.gameId
                        pugentry.delete_instance()
                        game = PickupGames.select().where(PickupGames.id == gid).first()
                        if len(game.addedplayers) == 0:
                            game.delete_instance()
                        self.build_pickuptext()
                    elif pugdiff >= warntime:
                        if mindiff > deletetime - pugdiff:
                            mindiff = deletetime - pugdiff  
                        if not pugentry.isWarned:
                            pugentry.isWarned = True
                            pugentry.save()
                            if pugentry.addedFrom == "irc":
                                self.send_notice(pugentry.playerId.ircName, self.cmdresults["misc"]["pugtimewarn"], "irc")
                            else:
                                self.send_notice(None, pugentry.playerId.discordMention +  " " + self.cmdresults["misc"]["pugtimewarn"], "discord")                                                             
                    else:
                        if mindiff > warntime - pugdiff:
                            mindiff = warntime - pugdiff
                        else:
                            break
                if not PickupGames.select().where(PickupGames.isPlayed == False).exists():
                    return
                else:
                    time.sleep(mindiff)
            else:
                return

    def get_statsname(self, id):
        #get clean XonStats nickname of player
        header =  {'Accept': 'application/json'}
        response = requests.get("https://stats.xonotic.org/player/" + str(id), headers=header)
        player = response.json()
        if response.status_code == 200:
            return player["player"]["stripped_nick"]
        else:
            return None

    def get_gamestats(self, id, gtype):
        elo = 0
        header =  {'Accept': 'application/json'}
        response = requests.get("https://stats.xonotic.org/player/" + str(id)+ "/skill?game_type_cd=" + gtype, headers=header)
        player = response.json()
        if response.status_code == 200:
            if len(player):
                elo = player[0]["mu"]
        return elo

    def found_match(self, puggame):
        #excutes in case match is found and sends notification to all players
        pugplayers = PickupEntries.select().where(PickupEntries.gameId == puggame.id)
        if pugplayers.count() == puggame.gametypeId.playerCount:
            puggame.isPlayed = True
            puggame.save()
            ircmatchtext = puggame.gametypeId.title + " ready! Players are: "
            matchtext = puggame.gametypeId.title + " ready! Players are: "
            for pugplayer in pugplayers:
                if pugplayer.addedFrom == "irc":
                    matchtext += pugplayer.playerId.ircName + " (" + pugplayer.playerId.statsName + ") "
                    ircmatchtext += pugplayer.playerId.ircName + " (" + pugplayer.playerId.statsName + ") "
                else:
                    matchtext += pugplayer.playerId.discordMention + " (" + pugplayer.playerId.statsName + ") "
                    ircmatchtext += pugplayer.playerId.discordName + " (" + pugplayer.playerId.statsName + ") "
            self.send_all(matchtext, ircmatchtext)
    
    def send_command(self, user, argument, chattype, isadmin):
        #forwards commands from irc/discord to bot specific command
        argument = argument.split()
        method_name = 'command_' + str(argument[0][1:].lower())
        method = getattr(self, method_name, self.wrong_command)
        with self.thread_lock:
            db.connect()
            try:
                method(user, argument, chattype, isadmin)
            except:
                self.send_notice(user, "Sorry, something went wrong", chattype)
            db.close()

    def send_notice(self, user, message, chattype):
        #sends message to only discord or to specific irc-user (for future: send direct message to discord-user)
        if chattype == "irc":
            self.ircconnect.send_single_message(user,message)
        else:
            self.discordconnect.send_my_message(message)

    def send_all(self, message, ircmessage = None):
        #sends message to all (irc and discord)
        if ircmessage is not None:
            self.ircconnect.send_my_message(ircmessage)
        else:
            self.ircconnect.send_my_message(message)
        self.discordconnect.send_my_message(message)
    
    def wrong_command(self, user, argument, chattype, isadmin):
        #if user inputs wrong command
        self.send_notice(user, self.cmdresults["misc"]["wrongcommand"], chattype)

    def change_name(self, oldnick, newnick):
        #changes irc-name of users in case of nickname changes
        with self.thread_lock:
            db.connect()
            pl = Players.select().where(Players.ircName == oldnick).first()
            if pl is not None:
                pl.ircName = newnick
                pl.save()
            db.close()

    def remove_user_on_exit(self, user,chattype):        
        gameentries = None
        player = None
        with self.thread_lock:
            db.connect()
            try:                
                #check where user removed from
                if chattype == "irc": 
                    player = Players.select().where(Players.ircName == user).first()
                else:
                    player = Players.select().where(Players.discordName == user.name).first()

                #check if player is already in database
                if player is not None:
                    gameentries = PickupEntries.select().join(PickupGames).where(PickupGames.isPlayed == False).where(PickupEntries.playerId == player)
                
                #send message if theres is no active pickup game
                if player is None or not gameentries.exists():
                    return
                else:                
                    #!remove without gametype, remove all entries and if only player removes pickup game completely
                    for gameentry in gameentries:
                        gid = gameentry.gameId
                        gameentry.delete_instance()
                        game = PickupGames.select().where(PickupGames.id == gid).first()
                        if len(game.addedplayers) == 0:
                            game.delete_instance()
                    self.build_pickuptext()
            except Exception as e:
                print("Error in remove_user_on_exit: ", e)
            db.close()


    def build_pickuptext(self):
        #sends current pickup games to all channels
        #result: "(1/2) duel (1/4) 2v2tdm"
        testgames = PickupGames.select().where(PickupGames.isPlayed == False) ## ToDo wenn letzter eintrag gelöscht wird 
        if not testgames.exists() and self.pickupText == "Pickups: ":
            return

        if not testgames.exists() and self.pickupText != "Pickups: ":            
            self.pickupText = "Pickups: " 
            self.send_all(self.pickupText)       
        else:
            self.pickupText = "Pickups: "
            for testgame in testgames:
                self.pickupText += testgame.gametypeId.title + " (" + str(len(testgame.addedplayers)) + "/" + str(testgame.gametypeId.playerCount) + ") "
            self.send_all(self.pickupText)
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
        if len(argument) > 1 and argument[1].isdigit():
            try:                
                xonstatsname = self.get_statsname(argument[1])
                if xonstatsname is None:
                    self.send_notice(user, "No Player with this ID", chattype)
                    return
                if chattype == "irc":
                    pl = Players.select().where(Players.statsId == argument[1]).first()
                    if pl is None:
                        pl, plcreated = Players.get_or_create(ircName=user)
                        pl.statsId = argument[1]
                        pl.statsName = xonstatsname                        
                        pl.save()
                    else:
                        pl.ircName = user
                        pl.statsName = xonstatsname
                        pl.save()
                else:
                    pl = Players.select().where(Players.statsId == argument[1]).first()
                    if pl is None:
                        pl, plcreated = Players.get_or_create(discordName=user.name)
                        pl.discordMention = user.mention
                        pl.statsId = argument[1]
                        pl.statsName = xonstatsname                        
                        pl.save()
                    else:
                        pl.discordName = user.name
                        pl.discordMention = user.mention
                        pl.statsName = xonstatsname
                        pl.save()                
                if chattype == "irc":
                    self.send_all(self.cmdresults["misc"]["registsuccess"].format(user,argument[1],xonstatsname))
                else:
                    self.send_all(self.cmdresults["misc"]["registsuccess"].format(user.name,argument[1],xonstatsname))
            except:
                self.send_notice(user, "Problem with XonStats", chattype)
        else: 
            self.send_notice(user,"No ID given!",chattype)

    def command_add(self, user, argument, chattype, isadmin):
        pl = None

        #check where user added from
        if chattype == "irc":
            pl, plcreated = Players.get_or_create(ircName=user)
        else:
            pl, plcreated = Players.get_or_create(discordName=user.name, discordMention=user.mention)
            
        #!add without gametype
        if len(argument) == 1:
            games = PickupGames.select().where(PickupGames.isPlayed == False)

            #no pickup game found and show possible gametypes
            if not games.exists():
                queryset = ""
                for gametype in GameTypes:
                    queryset += gametype.title + " "
                self.send_notice(user, self.cmdresults["misc"]["nogame"] + queryset, chattype)
            
            #adds to all current active pickup games
            else:
                for game in games:
                    pickentry = PickupEntries.select().where(PickupEntries.playerId == pl.id, PickupEntries.gameId == game.id).first()
                    if pickentry is None:
                        pickentry = PickupEntries(playerId=pl.id, gameId=game.id, addedFrom=chattype)
                        pickentry.save()
                        self.found_match(game)
                    else:
                        self.send_notice(user, "Already added for " + pickentry.gameId.gametypeId.title, chattype)
                        return
        
        #add with gametypes
        #example: !add duel 2v2tdm
        else:
            for gtypeentries in argument[1:]:
                gtype = GameTypes.select().where(GameTypes.title == gtypeentries).first()
                if gtype is not None:     
                    game, gamcreated = PickupGames.get_or_create(gametypeId=gtype.id, isPlayed=False)
                    pickentry = PickupEntries.select().where(PickupEntries.playerId == pl.id, PickupEntries.gameId == game.id).first()
                    if pickentry is None:
                        pickentry = PickupEntries(playerId=pl.id, gameId=game.id, addedFrom=chattype)
                        pickentry.save()
                        self.found_match(game)
                    else:
                        self.send_notice(user, "Already added for " + pickentry.gameId.gametypeId.title, chattype)

        #start the background timer to delete old pickup games
        if self.picktimer is None or not self.picktimer.is_alive():
            self.picktimer = threading.Thread(target=self.start_pugtimer, daemon=True)
            self.picktimer.start()
        self.build_pickuptext()

    def command_pickups(self, user, argument, chattype, isadmin):
        queryset = ""
        for gametype in GameTypes:
            queryset += gametype.title + " "
        self.send_notice(user, "Possible gametypes: " + queryset, chattype)


    def __get_active_player_entries(self, player) -> PickupEntries:
        if player is not None:
            return PickupEntries.select().join(PickupGames).where(PickupGames.isPlayed == False).where(PickupEntries.playerId == player)
        return None

    def __withdraw_player_from_all(self, player) -> bool:
        #check if player is already in database
        if player is not None:
            gameentries = self.__get_active_player_entries(player)

        if player is None or not gameentries.exists():
            return False
        
        for gameentry in gameentries:
            gid = gameentry.gameId
            gameentry.delete_instance()
            game = PickupGames.select().where(PickupGames.id == gid).first()
            if len(game.addedplayers) == 0:
                game.delete_instance()
        
        return True
        
    def __withdraw_player_from_gametype(self, player, gametypeId) -> bool:
        if player is None:
            return False
        
        gtype = GameTypes.select().where(GameTypes.title == gametypeId).first()
        if gtype is not None:     
            games = PickupGames.select().where(PickupGames.gametypeId == gtype.id, PickupGames.isPlayed == False)
            for game in games:
                PickupEntries.delete().where(PickupEntries.playerId == player, PickupEntries.gameId == game.id).execute()
                if len(game.addedplayers) == 0:
                    game.delete_instance()
                    
        return True

    def command_remove(self, user, argument, chattype, isadmin):
        player = None
        
        #check where user removed from
        if chattype == "irc": 
            player = Players.select().where(Players.ircName == user).first()
        else:
            player = Players.select().where(Players.discordName == user.name).first()
        
        result: bool = False
        
        #!remove without gametype, remove all entries and if only player removes pickup game completely
        if len(argument) == 1:
            result = self.__withdraw_player_from_all(player)
        
        #just removes gametypes that are given and if last player removes pickup game completely
        #example: !remove duel
        else:
            for gtypeentry in argument[1:]:
                result = self.__withdraw_player_from_gametype(player, gtypeentry)
        
        if not result:
            self.send_notice(user, "No game added!", chattype)
        else:
            self.build_pickuptext()   

    def command_pull(self, user, argument, chattype, isadmin):
        #todo removes pickup player from games (just discord-moderators or irc-operators)
        if isadmin:
            if len(argument) > 1:
                result: bool = False
                not_existing_players = []
                player = None
                for arg in argument[1:]:
                    player = Players.select().where((Players.ircName == arg)|(Players.discordName == arg)).first()
                    result = self.__withdraw_player_from_all(player)
                    if not result:
                        not_existing_players.append(arg)
                
                if len(not_existing_players) > 0:
                    self.send_notice(user, f"The following player(s) was/were not added! → {", ".join(not_existing_players)} ", chattype)
                
                if len(not_existing_players) != len(argument[1:]):
                    self.build_pickuptext()
        else:
            self.send_notice(user, self.cmdresults["misc"]["restricted"], chattype)
        
    def command_renew(self, user, argument, chattype, isadmin):
        gameentries = None
        player = None

        #check where user renewed from
        if chattype == "irc":
            player = Players.select().where(Players.ircName == user).first()
        else:
            player = Players.select().where(Players.discordName == user.name).first()

        #check if player is already in database
        if player is not None:
            gameentries = PickupEntries.select().join(PickupGames).where(PickupGames.isPlayed == False).where(PickupEntries.playerId == player)
        
        #send message if theres is no active pickup game
        if player is None or not gameentries.exists():
            self.send_notice(user, "No game added!", chattype)

        #!renew without gametype, renew all pickups of player
        if len(argument) == 1:
            for gameentry in gameentries:
                gameentry.addedDate = datetime.now()
                gameentry.save()

        #just renews gametypes that are given
        #example: !renew duel
        else:
            for gtypeentries in argument[1:]:
                gtype = GameTypes.select().where(GameTypes.title == gtypeentries).first()
                if gtype is not None:     
                    gameentry = gameentries.select().where(PickupEntries.gameId == gtype.id).first()
                    gameentry.addedDate = datetime.now()
                    gameentry.save()
        
        self.build_pickuptext()

    def command_who(self, user, argument, chattype, isadmin):
        #!who shows list of pickup games and their players

        games = PickupGames.select().where(PickupGames.isPlayed == False)
        if not games.exists():
            self.send_notice(user, "No game added!", chattype)
        else:
            resultText = ""
            for game in games:
                resultText += game.gametypeId.title + ": "
                playerentries = game.addedplayers
                for playerentry in playerentries:
                    if playerentry.addedFrom == "irc":
                        resultText += playerentry.playerId.ircName + " "
                    else:
                        resultText += playerentry.playerId.discordName + " "
            self.send_notice(user, resultText, chattype)

    def command_server(self, user, argument, chattype, isadmin):
        #!server without arguments shows all available servers
        if len(argument) == 1:
            resultText = ""
            for gameserver in Servers:
                resultText += gameserver.serverName + " "
            self.send_all("Available servers: " + resultText)

        #shows specific servers from arguments
        #example: !server dogcity
        else:
            gserver = Servers.select().where(Servers.serverName == argument[1]).first()
            if gserver is not None:
                self.send_all("Server: " + gserver.serverName + " with IP: " + gserver.serverIp)
            else:
                self.send_notice(user, "Server: " + argument[1] + " not found!", chattype)

    def command_addserver(self, user, argument, chattype, isadmin):
        #command to add servers with their ip:port to database
        if isadmin:
            if len(argument) == 3:            
                try:
                    ip = argument[2].split(":")[0]
                    ip_address(ip)
                    try:
                        serv = Servers(serverName=argument[1],serverIp=argument[2])
                        serv.save()
                    except:
                        self.send_notice(user, "Server already registered!", chattype)
                    self.send_notice(user, "Server " + argument[1] + " added.", chattype)
                    
                except ValueError:
                    self.send_notice(user, "Not a valid IP-address! To add server: !addserver <servername> <ip:port>", chattype)
            else:
                self.send_notice(user, "To add server: !addserver <servername> <ip:port>", chattype)
        else:
            self.send_notice(user, self.cmdresults["misc"]["restricted"],chattype)
    
    def command_addgametype(self, user, argument, chattype, isadmin):
        #command to add gametype to database (duel, 2v2tdm)
        #Usage: !addgametype <gametypetitle> <playercount> <teamcount> <statsname>
        #example: !addgametype 2v2v2ca 6 3 ca
        if isadmin:
            if len(argument) == 5 and argument[2].isdigit() and argument[3].isdigit():
                try:
                    game = GameTypes(title=argument[1], playerCount=argument[2], teamCount=argument[3], statsName=argument[4])
                    game.save()
                except:
                    self.send_notice(user, "Gametype already registered!", chattype)
                self.send_notice(user, "Gametype " + argument[1] + " added.", chattype)
            else:
                self.send_notice(user, "To add gametype: !addgametype <gametypename> <playercount> <teamcount> <statsname>", chattype)
        else:
            self.send_notice(user, self.cmdresults["misc"]["restricted"], chattype)

    def command_removeserver(self, user, argument, chattype, isadmin):
        #command to remove server from database
        if isadmin:
            if len(argument) > 1:
                resultText = ""
                for serverentry in argument[1:]:
                    gserver = Servers.select().where(Servers.serverName == serverentry).first()
                    if gserver is not None:
                        gserver.delete_instance()
                        resultText += serverentry + " deleted. "
                    else:
                        resultText += serverentry + " not found. "

                self.send_notice(user, resultText, chattype)
            else:
                self.send_notice(user, "To delete server: !removeserver [<servername>]", chattype)
        else:
            self.send_notice(user, self.cmdresults["misc"]["restricted"], chattype)
    
    def command_removegametype(self, user, argument, chattype, isadmin):
        #command to remove gametype from database
        if isadmin:
            if len(argument) > 1:
                resultText = ""
                for gametypeentry in argument[1:]:
                    gtype = GameTypes.select().where(GameTypes.title == gametypeentry).first()
                    if gtype is not None:
                        gtype.delete_instance()
                        resultText += gametypeentry + " deleted. "
                    else:
                        resultText += gametypeentry + " not found. "
                self.send_notice(user, resultText, chattype)
            else:
                self.send_notice(user, "To delete gametype: !removegametype [<gametypename>]", chattype)
        else:
            self.send_notice(user, self.cmdresults["misc"]["restricted"], chattype)
    
    def command_help(self, user, argument, chattype, isadmin):
        #command for general overview of commands
        #or with arguments help for specific command
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
        pass
    
    def command_cupstart(self, user, argument, chattype, isadmin):
        #creates cup brackets and uploads to discord
        #example: !cupstart seeky-cup Seek-y Grunt hotdog packer 
        cuppath = get_cuppicture(argument, self.settings["bot"]["browser"])
        self.discordconnect.send_my_file(cuppath)
        self.send_all("Generate Cup...")

    def command_online(self, user, argument, chattype, isadmin):
        if chattype == "irc":
            self.ircconnect.send_my_message("Online are: " + ", ".join(self.discordconnect.get_online_members()))
        else:
            self.discordconnect.send_my_message("Online are: " + ", ".join(self.ircconnect.channels[self.settings["irc"]["channel"]]._users.keys()))

