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

@pytest.mark.parametrize("user, xonstatid, chat, error_result, discord_empty, irc_empty",
                         [(DiscordTestUser("seek_y", "@seek_y"), "110074", "discord", "", False, False), 
                          ("Seek-y", "110074", "irc", "", False, False),
                          ("Grunt", "110074", "irc", "Another player is registered with Xonstat account #110074", True, True),
                          ("Grunt", "22", "irc", "", False, False),
                          (DiscordTestUser("Grunt", "@Grunt"), "22", "discord", "", False, False),
                          ("Wrong_stat_player", "1", "irc", "Problem with XonStats", True, True),
                          (DiscordTestUser("Wrong_stat_player", "@Wrong_stat_player"), "11", "discord", "Problem with XonStats", True, True)])
def test_register(dbconnect:DatabaseConnector, user, xonstatid, chat, error_result, discord_empty, irc_empty):
    errormessage, discordname, ircname = dbconnect.register_player(user=user, xonstatId=xonstatid, chattype=chat)
    assert error_result == errormessage
    assert discord_empty == (len(discordname) == 0)
    assert irc_empty == (len(ircname) == 0)

###GameType Tests###

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
    for i in range(len(messages)):
        assert messages[i] == results[i]

def test_get_gametype_list(dbconnect:DatabaseConnector):
    message = dbconnect.get_gametype_list()
    assert message == ['duel', '2v2tdm', '4v4tdm', '3v3ctf', '4v4ctf', '5v5ctf', '2v2ca', '3v3ca', '4v4ca', '2v2ca3', '3v3ca3', '4v4ca3', '2v2ca4', '3v3ca4', '4v4ca4', 'l4d2']

###Server Command Tests###

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
    for i in range(len(messages)):
        assert messages[i] == results[i]