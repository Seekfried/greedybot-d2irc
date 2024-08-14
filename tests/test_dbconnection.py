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

@pytest.fixture
def dbconnect():
    yield DatabaseConnector("test.db")
    os.remove("test.db")

@pytest.mark.parametrize("users",
                         [([{"user":DiscordTestUser("seek_y", "@seek_y"), "statid":"110074", "chat":"discord", "error_result":"", "discord_empty":False, "irc_empty":False}]), 
                          ([{"user":"Seek-y", "statid":"110074", "chat":"irc", "error_result":"", "discord_empty":False, "irc_empty":False}]),
                          ([{"user":DiscordTestUser("seek_y", "@seek_y"), "statid":"110074", "chat":"discord", "error_result":"", "discord_empty":False, "irc_empty":False}, 
                            {"user":"Seek-y", "statid":"110074", "chat":"irc", "error_result":"", "discord_empty":False, "irc_empty":False}]),
                          ([{"user":"Seek-y", "statid":"110074", "chat":"irc", "error_result":"", "discord_empty":False, "irc_empty":False},
                            {"user":DiscordTestUser("seek_y", "@seek_y"), "statid":"110074", "chat":"discord", "error_result":"", "discord_empty":False, "irc_empty":False}]),
                          ([{"user":"Seek-y", "statid":"110074", "chat":"irc", "error_result":"", "discord_empty":False, "irc_empty":False},
                            {"user":"Grunt", "statid":"110074", "chat":"irc", "error_result":"Another player is registered with Xonstat account #110074", "discord_empty":True, "irc_empty":True}]),
                          ([{"user":"Wrong_stat_player", "statid":"1", "chat":"irc", "error_result":"Problem with XonStats", "discord_empty":True, "irc_empty":True}])])
def test_register(dbconnect, users):
    for user in users:
        errormessage, discordname, ircname = dbconnect.register_player(user=user["user"], xonstatId=user["statid"], chattype=user["chat"])
        assert user["error_result"] == errormessage
        assert user["discord_empty"] == (len(discordname) == 0)
        assert user["irc_empty"] == (len(ircname) == 0)