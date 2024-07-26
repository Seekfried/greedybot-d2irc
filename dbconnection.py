from model import *
from typing import List
import logging
from xonotic.utils import *
from ipaddress import ip_address

db_logger = logging.getLogger("dbConnector")

class DatabaseConnector:
    
    def __init__(self):
        db_logger.info("Initialize db connection")
        db.start()
        self.delete_active_games()

    def __del__(self):
        db.stop()

    def __get_active_games(self) -> PickupGames:
        games = PickupGames.select().where(PickupGames.isPlayed == False)
        return games

    def __get_active_player_entries(self, player) -> PickupEntries:
        if player is not None:
            return PickupEntries.select().join(PickupGames).where(PickupGames.isPlayed == False).where(PickupEntries.playerId == player)
        return None
    
    def __get_found_matchtext(self, puggame:PickupGames) -> dict:
        #excutes in case match is found and sends notification to all players
        result = {}
        has_teams: bool = False
        ircresult: str = ""
        discordresult: str = ""

        db_logger.info("found_match: puggame=%s", puggame)

        pugplayers = PickupEntries.select().where(PickupEntries.gameId == puggame.id)
        db_logger.info("found_match: pugplayers.count()=%s", pugplayers.count())
        if pugplayers.count() == puggame.gametypeId.playerCount:
            puggame.isPlayed = True
            puggame.save()
            if puggame.gametypeId.playerCount == puggame.gametypeId.teamCount or puggame.gametypeId.statsName is None:
                ircresult = puggame.gametypeId.title + " ready! Players are: "
                discordresult = puggame.gametypeId.title + " ready! Players are: "
                for pugplayer in pugplayers:
                    #self.__withdraw_player_from_all(pugplayer.playerId)
                    if pugplayer.addedFrom == "irc":
                        discordresult += pugplayer.playerId.ircName + " (" + pugplayer.playerId.statsDiscordName + ") "
                        ircresult += pugplayer.playerId.ircName + " (" + pugplayer.playerId.statsIRCName + ") "
                    else:
                        discordresult += pugplayer.playerId.discordMention + " (" + pugplayer.playerId.statsDiscordName + ") "
                        ircresult += pugplayer.playerId.discordName + " (" + pugplayer.playerId.statsIRCName + ") "
            else:
                has_teams = True
                team_result = self.__get_teamtext(pugplayers, puggame.gametypeId.teamCount, puggame.gametypeId.statsName)
                ircresult = team_result["irc"]
                discordresult = team_result["discord"]
                ircresult.insert(0, puggame.gametypeId.title + " ready! Players are: ", puggame.gametypeId.title + " ready! Players are: ")
                discordresult.insert(0, puggame.gametypeId.title + " ready! Players are: ", puggame.gametypeId.title + " ready! Players are: ")
            result = {"has_teams": has_teams, "irc": ircresult, "discord": discordresult}
        return result
    
    def __get_player(self, user, chattype) -> Players:
        player = None

        if chattype == "irc":
            player = Players.select().where(Players.ircName == user).first()
        else:
            player = Players.select().where(Players.discordName == user.name).first()
        return player
    
    def __get_player_subscriptions(self, player) -> Subscriptions:
        if player:
            return Subscriptions.select().where(Subscriptions.playerId == player)
        return None

    def __get_teamtext(self, players, teamcount, xongametype):
        #logger.info("found_match: players=%s, teamcount=%s, xongametype=%s", players, teamcount, xongametype)
        matchtext = {"irc":[],"discord":[]}
        teams = [[] for _ in range(teamcount)]
        total_elo = [0] * teamcount
        players_with_elo = []

        for player_entry in players:
            if player_entry.playerId.statsId:
                players_with_elo.append({"player": player_entry, "elo": get_gamestats(player_entry.playerId.statsId, xongametype)})
            else:
                players_with_elo.append({"player": player_entry, "elo": 0})

        # Sort players by elo rating in descending order
        players_with_elo.sort(key=lambda x: x['elo'], reverse=True)

        # Distribute players to teams
        for player in players_with_elo:
            # Assign the player to the team with the least total elo
            team_index = total_elo.index(min(total_elo))
            teams[team_index].append(player)
            total_elo[team_index] += player['elo']
    
        # Prepare the results with team information
        team_info = []

        for team in teams:
            if team:
                captain = max(team, key=lambda x: x['elo'])
                average_elo = sum(player['elo'] for player in team) / len(team)
                team_info.append({
                    'team': team,
                    'captain': captain,
                    'average_elo': average_elo
                })     

        # Format the Teamresult for irc and discord
        captains_discord = "Captains are: "
        captains_irc = "Captains are: "
        for index, team in enumerate(team_info, start=1):
            irc_entry = f"Team {index}: "
            discord_entry = f"Team {index}: "
            captain = team['captain']
            for team_member in team['team']:
                #self.__withdraw_player_from_all(team_member['player'].playerId)
                if team_member['player'].addedFrom == "irc":
                    discord_entry += team_member['player'].playerId.ircName + " (" + team_member['player'].playerId.statsName + ") "
                    irc_entry += team_member['player'].playerId.ircName + " (" + team_member['player'].playerId.statsIRCName + ") "
                else:
                    discord_entry += team_member['player'].playerId.discordMention + " (" + team_member['player'].playerId.statsName + ") "
                    irc_entry += team_member['player'].playerId.discordName + " (" + team_member['player'].playerId.statsIRCName + ") "

            captains_discord += f"{captain['player'].playerId.statsDiscordName} ({captain['elo']:.2f}) "
            discord_entry += f"Average Elo: {team['average_elo']:.2f} "
            captains_irc += f"{captain['player'].playerId.statsIRCName} ({captain['elo']:.2f}) "
            irc_entry += f"Average Elo: {team['average_elo']:.2f} "
            matchtext["irc"].append(irc_entry)
            matchtext["discord"].append(discord_entry)
        
        matchtext["irc"].append(captains_irc)
        matchtext["discord"].append(captains_discord)
        return matchtext
        
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
    
    def add_gametypes(gametypes) -> list[str]:
        messages = []
        if len(gametypes) == 5 and gametypes[2].isdigit() and gametypes[3].isdigit():
            try:
                game = GameTypes(title=gametypes[1], playerCount=gametypes[2], teamCount=gametypes[3], statsName=gametypes[4])
                game.save()
                messages.append("Gametype " + gametypes[1] + " added.")
            except:
                messages.append("Gametype already registered!")
        else:
            messages.append("To add gametype: !addgametype <gametypename> <playercount> <teamcount> <statsname>")
        return messages

    def add_player_to_games(self, user, gametypes:List[str], chattype) -> tuple[bool, list[str], dict]:
        db_logger.info("add_player_to_games: user=%s, gametypes=%s, chattype=%s", user, gametypes, chattype)
        result: bool = False
        error_message = []
        found_match = {}

        db.connect()
        
        #check where user added from
        player = self.__get_player(user,chattype)

        #!add without gametype
        if player:
            if len(gametypes) == 0:
                games = self.__get_active_games()

                #no pickup game found and show possible gametypes
                if not games.exists():
                    gametype_result = []
                    for gametype in GameTypes:
                        gametype_result.append(gametype.title)
                    error_message.append("No game found! Possible gametypes: " + ", ".join(gametype_result))
                #adds to all current active pickup games    
                else:
                    for game in games:
                        pickentry = PickupEntries.select().where(PickupEntries.playerId == player.id, PickupEntries.gameId == game.id).first()
                        if pickentry is None:
                            pickentry = PickupEntries(playerId=player.id, gameId=game.id, addedFrom=chattype)
                            pickentry.save()
                            result = True
                            found_match = self.__get_found_matchtext(game)
                        else:
                            error_message.append("Already added for " + pickentry.gameId.gametypeId.title)
                            return result, error_message
            #add with gametypes
            #example: !add duel 2v2tdm
            else:
                for gtypeentries in gametypes:
                    gtype = GameTypes.select().where(GameTypes.title == gtypeentries).first()
                    if gtype is not None:     
                        game = PickupGames.select().where(PickupGames.gametypeId == gtype.id, PickupGames.isPlayed == False).first()
                        if game is None:
                            game = PickupGames(gametypeId=gtype.id, isPlayed=False)
                            game.save()
                        pickentry = PickupEntries.select().where(PickupEntries.playerId == player.id, PickupEntries.gameId == game.id).first()
                        if pickentry is None:
                            pickentry = PickupEntries(playerId=player.id, gameId=game.id, addedFrom=chattype)
                            pickentry.save()
                            result = True
                            found_match = self.__get_found_matchtext(game)
                        else:
                            error_message.append("Already added for " + pickentry.gameId.gametypeId.title)
        else:
            error_message.append("You need to register first (!register) to add for games!")
        db.close()
        return result, error_message, found_match
    
    def add_server(serverlist) -> list[str]:
        messages = []

        if len(serverlist) == 3:            
            try:
                ip = serverlist[2].split(":")[0]
                ip_address(ip)
                try:
                    serv = Servers(serverName=serverlist[1],serverIp=serverlist[2])
                    serv.save()
                    messages.append("Server " + serverlist[1] + " added.")
                except:
                    messages.append("Server already registered!")
                
            except ValueError:
                messages.append("Not a valid IP-address! To add server: !addserver <servername> <ip:port>")
        else:
            messages.append( "To add server: !addserver <servername> <ip:port>")
        return messages

    def delete_active_games(self):
        #Delete pickgames that were not played
        db.connect()
        games = PickupGames.delete().where(PickupGames.isPlayed == False)
        games.execute()
        db.close()

    def delete_server(self, serverlist) -> list[str]:
        messages = []

        if serverlist:
            for serverentry in serverlist:
                gserver = Servers.select().where(Servers.serverName == serverentry).first()
                if gserver is not None:
                    gserver.delete_instance()
                    messages.append(serverentry + " deleted.")
                else:
                    messages.append(serverentry + " not found.")
        else:
            messages.append("To delete server: !removeserver [<servername>]")        
        return messages

    def delete_gametypes(gametypes) -> list[str]:
        messages = []

        if gametypes:
            for gametypeentry in gametypes:
                gtype = GameTypes.select().where(GameTypes.title == gametypeentry).first()
                if gtype is not None:
                    gtype.delete_instance()
                    messages.append(gametypeentry + " deleted.")
                else:
                    messages.append(gametypeentry + " not found.")
        else:
            messages.append("To delete gametype: !removegametype [<gametypename>]")
        return messages

    
    def get_gametype_list(self) -> List[str]:
        #Get a list of strings of all possible gametypes
        result = []

        for gametype in GameTypes:
            result.append(gametype.title)
        return result

    def get_lastgame(self, chattype) -> str:
        lastPickupGame = PickupGames.select().where(PickupGames.isPlayed == True).order_by(PickupGames.createdDate.desc()).first()
        lastPickupGamePlayers = lastPickupGame.addedplayers
        resultText = lastPickupGame.gametypeId.title + ", played on " + lastPickupGame.createdDate.strftime("%Y-%m-%d") + " was played with: "
        for player in lastPickupGamePlayers:
            if chattype == "irc":
                playername = player.playerId.ircName if player.playerId.ircName is not None else player.playerId.discordName
                resultText += playername + " " + ("("+player.playerId.statsIRCName + ") " if player.playerId.statsIRCName is not None else "")
            else:
                playername = player.playerId.discordName if player.playerId.discordName is not None else player.playerId.ircName
                resultText += playername + " " + ("("+player.playerId.statsDiscordName + ") " if player.playerId.statsDiscordName is not None else "")

    def get_pickuptext(self) -> tuple[bool, str]:
        #Get string of active pickups with gametype and number of players/player needed 
        #example: "2v2tdm (2/4)"
        db_logger.info("Build pickuptext")
        result: str = ""

        db.connect()
        games: List[PickupGames] = self.__get_active_games()

        for game in games:
            result += game.gametypeId.title + " (" + str(len(game.addedplayers)) + "/" + str(game.gametypeId.playerCount) + ") "
        
        db.close()
        return result
       
    def get_active_games_and_players(self) -> str:
        result: str = "No game added!"

        db.connect()
        games: List[PickupGames] = self.__get_active_games()
        if games.exists():
            result = ""
            for game in games:
                result += game.gametypeId.title + ": "
                playerentries: List[PickupEntries] = game.addedplayers
                existing_players = []
                for playerentry in playerentries:
                    if playerentry.addedFrom == "irc":
                        existing_players.append(playerentry.playerId.ircName)
                    else:
                        existing_players.append(playerentry.playerId.discordName)
                result += ", ".join(existing_players) + " "

        db.close()
        return result
    
    def get_server(self, servername = None) -> tuple[bool, str]:
        result: str = ""
        wrong_server: bool = False

        db.connect()
        if not servername:
            serverresult = []
            for gameserver in Servers:
                serverresult.append(gameserver.serverName)
            result = "Available servers: " + ", ".join(serverresult)
        else:
            server: Servers = Servers.select().where(Servers.serverName == servername).first()
            if server is not None:
                result = "Server: " + server.serverName + " with IP: " + server.serverIp
            else:
                wrong_server = True
                result = "Server: " + servername + " not found!"

        db.close()
        return wrong_server, result
    
    def has_active_games(self) -> bool:
        result: bool = False

        db.connect()
        games: List[PickupGames] = self.__get_active_games()
        result = games.exists()
        db.close()
        return result

    
    def register_player(self, user, xonstatId, chattype) -> tuple[str, str, str]:
        db_logger.info("register_player: user=%s, xonstatId=%s, chattype=%s", user, xonstatId, chattype)
        error_result: str = "No ID given!"
        irc_name: str = ""
        discord_name: str = ""

        db.connect()

        if xonstatId and xonstatId.isdigit():
            try:                
                xonstatscoloredname, xonstatsname = get_statsnames(xonstatId)
                pl = None
                if xonstatsname is None:
                    error_result = "No Player with this ID"
                    return
                if chattype == "irc":
                    pl = Players.select().where(Players.statsId == xonstatId).first()
                    if pl is None:
                        pl = Players(ircName = user, 
                                     statsId = xonstatId, 
                                     statsName = xonstatsname, 
                                     statsIRCName = irc_colors(xonstatscoloredname), 
                                     statsDiscordName = discord_colors(xonstatscoloredname))
                        pl.save()
                    else:
                        pl.ircName = user
                        pl.statsName = xonstatsname
                        pl.statsIRCName = irc_colors(xonstatscoloredname)
                        pl.statsDiscordName = discord_colors(xonstatscoloredname)
                        pl.save()
                else:
                    pl = Players.select().where(Players.statsId == xonstatId).first()
                    if pl is None:
                        pl = Players(discordName = user.name, 
                                     discordMention = user.mention, 
                                     statsId = xonstatId, 
                                     statsName = xonstatsname, 
                                     statsIRCName = irc_colors(xonstatscoloredname), 
                                     statsDiscordName = discord_colors(xonstatscoloredname))
                        pl.save()
                    else:
                        pl.discordName = user.name
                        pl.discordMention = user.mention
                        pl.statsName = xonstatsname
                        pl.statsIRCName = irc_colors(xonstatscoloredname)
                        pl.statsDiscordName = discord_colors(xonstatscoloredname)
                        pl.save()  
                irc_name = pl.statsIRCName
                discord_name = pl.statsDiscordName
                error_result = ""
            except Exception as e:
                db_logger.error("Error in command_register: ", e, "Reason: ", e.args)
                error_result = "Problem with XonStats"

        db.close()
        return error_result, discord_name, irc_name
    
    def renew_pickupentry(self, user, gametypes, chattype) -> str:
        gameentries = None
        player = None
        error_result: str = ""

        #check where user renewed from
        player = self.__get_player(user, chattype)

        #check if player is already in database
        if player is not None:
            gameentries = PickupEntries.select().join(PickupGames).where(PickupGames.isPlayed == False).where(PickupEntries.playerId == player)
        
        #send message if theres is no active pickup game
        if player is None or not gameentries.exists():
            error_result = "No game added!"

        #!renew without gametype, renew all pickups of player
        if not gametypes:
            for gameentry in gameentries:
                gameentry.addedDate = datetime.now()
                gameentry.save()

        #just renews gametypes that are given
        #example: !renew duel
        else:
            for gtypeentries in gametypes:
                gtype = GameTypes.select().where(GameTypes.title == gtypeentries).first()
                if gtype is not None:     
                    gameentry = gameentries.select().where(PickupEntries.gameId == gtype.id).first()
                    gameentry.addedDate = datetime.now()
                    gameentry.save()
        return error_result
    
    def withdraw_player_from_pickup(self, user, gametypes:List[str] = None, chattype = None) -> bool:
        db_logger.info("remove_player_from_pickup: user=%s, gametypes=%s, chattype=%s", user, gametypes, chattype)
        player = None        
        result: bool = False   

        db.connect()

        #check where user removed from
        if chattype:
            player = self.__get_player(user, chattype)
        else:
            player = Players.select().where((Players.ircName == user)|(Players.discordName == user)).first()
                
        #!remove without gametype, remove all entries and if only player removes pickup game completely
        if gametypes:
            result = self.__withdraw_player_from_all(player)
        
        #just removes gametypes that are given and if last player removes pickup game completely
        #example: !remove duel
        else:
            for gametype in gametypes:
                result = self.__withdraw_player_from_gametype(player, gametype)
        db.close()
        return result
    
    def set_irc_nickname(self, oldnick, newnick):
        db.connect()
        pl = Players.select().where(Players.ircName == oldnick).first()
        if pl is not None:
            pl.ircName = newnick
            pl.save()
        db.close()