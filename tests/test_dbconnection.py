from dbconnection import DatabaseConnector
import pytest
import os

class DiscordTestUser:
    def __init__(self, name, mention):
        self.__name = name
        self.__mention = mention

    @property
    def name(self):
        return self.__name
    
    @property
    def mention(self):
        return self.__mention
    

@pytest.fixture(scope="module")
def dbconnect():
    yield DatabaseConnector("test.db")
    os.remove("test.db") 

####### Register/Stats Tests ######

@pytest.mark.parametrize("user, xonstatid, chat, error_result, discord_empty, irc_empty",
                         [(DiscordTestUser("seek_y", "@seek_y"), "110074", "discord", "", False, False), 
                          ("Seek-y", "110074", "irc", "", False, False),
                          ("Grunt", "110074", "irc", "Another player is registered with Xonstat account #110074", True, True),
                          ("Grunt", "22", "irc", "", False, False),
                          (DiscordTestUser("Grunt", "@Grunt"), "22", "discord", "", False, False),
                          ("PureIrc", "130", "irc", "", False, False),                          
                          (DiscordTestUser("PureDiscord", "@PureDiscord"), "21", "discord", "", False, False),
                          ("Wrong_stat_player", "1", "irc", "Problem with XonStats", True, True),
                          (DiscordTestUser("Wrong_stat_player", "@Wrong_stat_player"), "11", "discord", "Problem with XonStats", True, True)])
def test_register(dbconnect:DatabaseConnector, user, xonstatid, chat, error_result, discord_empty, irc_empty):
    errormessage, discordname, ircname = dbconnect.register_player(user=user, xonstatId=xonstatid, chattype=chat)
    assert error_result == errormessage
    assert discord_empty == (len(discordname) == 0)
    assert irc_empty == (len(ircname) == 0)

@pytest.mark.parametrize("player_name, chat, result_empty", [("Seek-y", "irc", False),
                                               ("Seek-y", "discord", False),
                                               ("Wrong_player", "irc", True)])
def test_get_full_stats(dbconnect:DatabaseConnector, player_name, chat, result_empty):
    result = dbconnect.get_full_stats(player_name, chat)
    assert (len(result) == 0) == result_empty

####### Bridge Tests ######

@pytest.mark.parametrize("user, chat, result_irc, result_discord",
                         [("Seek-y", "irc", "Seek-y", "seek_y"),
                          (DiscordTestUser("Grunt", "@Grunt"), "discord", "Grunt", "Grunt"),
                          ("PureIrc", "irc", "PureIrc", None),
                          (DiscordTestUser("PureDiscord", "@PureDiscord"), "discord", None, "PureDiscord"),
                          ("Wrong_player", "irc", "", "")])
def test_toggle_player_bridge(dbconnect:DatabaseConnector, user, chat, result_irc, result_discord):
    irc_name, discord_name = dbconnect.toggle_player_bridge(user, chat)
    assert irc_name == result_irc
    assert discord_name == result_discord

@pytest.mark.parametrize("result_discord, result_irc", [(["seek_y", "Grunt", "PureDiscord"], ["Seek-y", "Grunt", "PureIrc"])])
def test_get_unbridged_players(dbconnect:DatabaseConnector, result_discord, result_irc):
    discord_users, irc_users = dbconnect.get_unbridged_players()
    assert irc_users == result_irc
    assert discord_users == result_discord

####### Pickup Tests #######

### Without Active Games ###

def test_get_active_games_and_players_nogame(dbconnect:DatabaseConnector):
    result = dbconnect.get_active_games_and_players()
    assert result == {}

@pytest.mark.parametrize("chat", [("irc"), ("discord")])
def test_get_lastgame_nogame(dbconnect:DatabaseConnector, chat):
    result = dbconnect.get_lastgame(chat)
    assert result == "No game played!"

def test_get_pickuptext_nogame(dbconnect:DatabaseConnector):
    result = dbconnect.get_pickuptext()
    assert result == ""

def test_has_active_games_nogame(dbconnect:DatabaseConnector):
    result = dbconnect.has_active_games()
    assert result == False

@pytest.mark.parametrize("gametypetitle, result, result_message, result_match", [("2v2tdm", False, "No active pickup game found!", {})])
def test_start_start_pickupgame_nogame(dbconnect:DatabaseConnector, gametypetitle, result, result_message, result_match):
    match_started, error_message, found_match = dbconnect.start_pickupgame(gametypetitle)
    assert match_started == result
    assert error_message == result_message
    assert found_match == result_match

@pytest.mark.parametrize("gametypes, result", 
                         [(["3v3ctf"], "No Games the last 30 days!"),
                          (["WrongGameType"], "Wrong gametype!"), 
                          (["duel", "2v2tdm"], "No Games the last 30 days!"), 
                          (["duel", "2v2tdm", "WrongGameType"], "No Games the last 30 days!")])
def test_get_top_ten_nogame(dbconnect:DatabaseConnector, gametypes, result):
    top_ten = dbconnect.get_top_ten(gametypes)
    assert top_ten == result

### With Active Games ###

@pytest.mark.parametrize("user, gametypes, chat, recipient, result, result_messages, result_match_empty", 
                         [("Wrong_player", ["duel"], "irc", None, False, ["You need to register first (!register) to add for games!"], True),
                          ("Seek-y", ["duel"], "irc", "Wrong_player", False, ["Wrong_player needs to register first (!register) to be added for games!"], True),
                          ("Seek-y", [], "irc", None, False, ["No game found! Possible gametypes: duel, 2v2tdm, 4v4tdm, 3v3ctf, 4v4ctf, 5v5ctf, 2v2ca, 3v3ca, 4v4ca, 2v2ca3, 3v3ca3, 4v4ca3, 2v2ca4, 3v3ca4, 4v4ca4, l4d2"], True),
                          ("Seek-y", ["WrongGameType"], "irc", None, False, [], True),
                          ("Seek-y", ["duel"], "irc", None, True, [], True),
                          ("Seek-y", ["duel"], "irc", None, False, ["Already added for duel"], True),
                          ("Grunt", ["duel"], "irc", None, True, [], False)])
def test_add_player_to_games(dbconnect:DatabaseConnector, user, gametypes, chat, recipient, result, result_messages, result_match_empty):
    got_added, error_messages, found_match = dbconnect.add_player_to_games(user, gametypes, chat, recipient)
    assert got_added == result
    assert error_messages == result_messages
    assert (not found_match) == result_match_empty

@pytest.mark.parametrize("chat", [("irc"), ("discord")])
def test_get_lastgame_withgame(dbconnect:DatabaseConnector, chat):
    result = dbconnect.get_lastgame(chat)
    assert result.find("duel, played on") != -1

def test_get_pickuptext_withgame(dbconnect:DatabaseConnector):
    result = dbconnect.get_pickuptext()
    assert result == ""

def test_has_active_games_withgame(dbconnect:DatabaseConnector):
    result = dbconnect.has_active_games()
    assert result == False

@pytest.mark.parametrize("gametypetitle, result, result_message, result_match", [("2v2tdm", False, "No active pickup game found!", {})])
def test_start_start_pickupgame_withgame(dbconnect:DatabaseConnector, gametypetitle, result, result_message, result_match):
    match_started, error_message, found_match = dbconnect.start_pickupgame(gametypetitle)
    assert match_started == result
    assert error_message == result_message
    assert found_match == result_match

@pytest.mark.parametrize("gametypes, result", 
                         [(["3v3ctf"], "No Games the last 30 days!"),
                          (["WrongGameType"], "Wrong gametype!"), 
                          (["duel"], "Top 10 players for last 30 days (duel):"), 
                          (["2v2tdm", "duel"], "Top 10 players for last 30 days (2v2tdm, duel):"),
                          (["duel", "2v2tdm", "WrongGameType"], "Top 10 players for last 30 days (duel, 2v2tdm):"),
                          ([], "Top 10 players for last 30 days (all games):")])
def test_get_top_ten_withgame(dbconnect:DatabaseConnector, gametypes, result):
    top_ten = dbconnect.get_top_ten(gametypes)
    assert top_ten.find(result) != -1

####### GameType Tests #######

@pytest.mark.parametrize("gt_title, gt_playercount, gt_teamcount, gt_xonstatname, result",
                         [("dm5", "5", None, None, "Gametype dm5 added."),
                          ("2v2tdm3", "6", "3", "tdm", "Gametype 2v2tdm3 added."),
                          ("2v2ca3", "6", "3", "ca", "Gametype already registered!")])
def test_add_gametype(dbconnect:DatabaseConnector, gt_title, gt_playercount, gt_teamcount, gt_xonstatname, result):
    message = dbconnect.add_gametypes(gt_title, gt_playercount, gt_teamcount, gt_xonstatname)
    assert message == result

@pytest.mark.parametrize("gametypes, results",
                         [(["dm5", "2v2tdm3"], ["dm5 deleted.", "2v2tdm3 deleted."]),
                          (["2v2tdm3"], ["2v2tdm3 not found."]),
                          (None, ["To delete gametype: !removegametype [<gametypename>]"])])
def test_delete_gametypes(dbconnect:DatabaseConnector, gametypes, results):
    messages = dbconnect.delete_gametypes(gametypes)
    assert messages == results

def test_get_gametype_list(dbconnect:DatabaseConnector):
    message = dbconnect.get_gametype_list()
    assert message == ['duel', '2v2tdm', '4v4tdm', '3v3ctf', '4v4ctf', '5v5ctf', '2v2ca', '3v3ca', '4v4ca', '2v2ca3', '3v3ca3', '4v4ca3', '2v2ca4', '3v3ca4', '4v4ca4', 'l4d2']

####### Server Tests #######

@pytest.mark.parametrize("servername, serveraddressIPv4, serveraddressIPv6, result",
                         [(None, None, None, "Missing data! servername is required!"),
                          ("TestServer1", None, None, "Missing data! serveraddressIPv4 or serveraddressIPv6 is required!"),
                          ("TestServer1", "1.1.1.1:11000", None, "Server TestServer1 added."),
                          ("TestServer1", "1.1.1.1:12000", None, "Server already registered!"),
                          ("TestServer2", "1.1.1.1:11000", None, "Server already registered!"),
                          ("TestServer2", None, "[2001:0db8:85a3:08d3:1319:8a2e:0370:7344]:11000", "Server TestServer2 added."),
                          ("TestServer2", "1.1.1.1:12000", "[2001:0db8:85a3:08d3:1319:8a2e:0370:7344]:11000", "Server already registered!"),
                          ("TestServer3", "91.134.143.13:26000", "[2001:0db8:85a3:08d3:1319:8a2e:0370:7345]:11000", "Server TestServer3 added.")])
def test_add_server(dbconnect:DatabaseConnector, servername: str, serveraddressIPv4: str, serveraddressIPv6: str, result):
    message = dbconnect.add_server(servername, serveraddressIPv4, serveraddressIPv6)
    assert message == result

@pytest.mark.parametrize("servername, result",
                         [(None, (False, "Available servers: TestServer1, TestServer2, TestServer3")),
                          ("TestServer9", (True, "Server: TestServer9 not found!")),
                          ("TestServer1", (False, "Server: TestServer1 with IPv4: 1.1.1.1:11000")),])
def test_get_server(dbconnect:DatabaseConnector, servername, result):
    message = dbconnect.get_server(servername)
    assert message == result

@pytest.mark.parametrize("servername, result, message_empty",
                         [("TestServer9", True, False),
                          ("TestServer1", True, False),
                          ("TestServer3", False, False)])
def test_get_server_info(dbconnect:DatabaseConnector, servername, result, message_empty):
    wrong_server, message = dbconnect.get_server_info(servername)
    assert wrong_server == result
    assert (len(message) == 0) == message_empty

@pytest.mark.parametrize("serverlist, results",
                         [(None,["To delete server: !removeserver [<servername>]"]),
                          (["TestServer1"],["TestServer1 deleted."]),
                          (["TestServer4"],["TestServer4 not found."]),
                          (["TestServer2", "TestServer3"],["TestServer2 deleted.", "TestServer3 deleted."])])
def test_delete_servers(dbconnect:DatabaseConnector, serverlist, results):    
    messages = dbconnect.delete_server(serverlist)
    assert messages == results

####### Subscription Tests #######

@pytest.mark.parametrize("user, gametypetitle, chat, result, result_message, result_name",
                        [("Seek-y", "2v2tdm", "irc", True, "", "seek_y"),
                         ("PureIrc", "2v2tdm", "irc", True, "", ""),
                         (DiscordTestUser("seek_y", "@seek_y"), "duel", "discord", True, "", "seek_y"),
                         (DiscordTestUser("Grunt", "@Grunt"), "duel", "discord", True, "", "Grunt"),
                         ("Grunt", "notAGame", "irc", False, "You can't subscribe to: notAGame", ""),
                         ("Wrong_player", "duel", "irc", False, "You need to register first (!register) to subscribe!", "")])
def test_add_subscription(dbconnect:DatabaseConnector, user, gametypetitle, chat, result, result_message, result_name):
    is_sub, message, discord_name = dbconnect.add_subscription(user, gametypetitle, chat)
    assert is_sub == result
    assert message == result_message
    assert discord_name == result_name

@pytest.mark.parametrize("user, chat, results",
                        [("Seek-y", "irc", ["2v2tdm", "duel"]),
                         (DiscordTestUser("Grunt", "@Grunt"), "discord", ["duel"]),
                         (DiscordTestUser("PureDiscord", "@PureDiscord"), "discord", [])])
def test_get_subscriptions(dbconnect:DatabaseConnector, user, chat, results):
    subs = dbconnect.get_subscriptions(user, chat)
    assert subs == results

@pytest.mark.parametrize("gametypetitle, results",
                         [("duel", ["Seek-y", "Grunt"]),
                          ("2v2tdm", ["Seek-y", "PureIrc"]),
                          ("3v3ctf", [])])
def test_get_subscribed_players(dbconnect:DatabaseConnector, gametypetitle, results):
    subs = dbconnect.get_subscribed_players(gametypetitle)
    assert subs == results

@pytest.mark.parametrize("user, gametypetitle, chat, result_message, result_name",
                        [("Seek-y", "duel", "irc", "", "seek_y"),
                         (DiscordTestUser("Grunt", "@Grunt"), "duel", "discord", "", "Grunt"),
                         ("PureIrc", "2v2tdm", "irc", "", ""),
                         ("Grunt", "2v2tdm", "irc", "You are not subscribed to: 2v2tdm", ""),
                         ("Wrong_player", "duel", "irc", "You need to register first (!register) to subscribe!", "")])
def test_delete_subscription(dbconnect:DatabaseConnector, user, gametypetitle, chat, result_message, result_name):
    message, discord_name = dbconnect.delete_subscription(user, gametypetitle, chat)
    assert message == result_message
    assert discord_name == result_name    