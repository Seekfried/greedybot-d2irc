import datetime
from peewee import *

db = SqliteDatabase(None) #'pickups.db', pragmas={'foreign_keys': 1})

class Players(Model):
    ircName = CharField(unique=True, null=True)
    discordName = CharField(unique=True, null=True)
    discordMention = CharField(unique=True, null=True)
    statsName = CharField(null=True)
    statsIRCName = CharField(null=True)
    statsDiscordName = CharField(null=True)
    statsId = IntegerField(unique=True, null=True)
    shouldBridge = BooleanField(default=True)

    class Meta:
        database = db

class GameTypes(Model):
    title = CharField(unique=True)
    playerCount = IntegerField(null=True)
    teamCount = IntegerField(null=True)
    statsName = CharField(null=True)

    class Meta:
        database = db

class Servers(Model):
    serverName = CharField(unique=True)
    serverIPv4 = CharField(unique=True, null=True)
    serverIPv6 = CharField(unique=True, null=True)

    class Meta:
        database = db

class PickupGames(Model):
    createdDate = DateTimeField(default=datetime.datetime.now)
    gametypeId = ForeignKeyField(GameTypes, backref='games', on_delete='CASCADE')
    isPlayed = BooleanField(default=False)

    class Meta:
        database = db

class PickupEntries(Model):
    addedDate = DateTimeField(default=datetime.datetime.now)
    addedFrom = CharField(default='irc')
    playerId = ForeignKeyField(Players, backref='addedgames', on_delete='CASCADE')
    gameId = ForeignKeyField(PickupGames, backref='addedplayers', on_delete='CASCADE')
    isWarned = BooleanField(default=False)

    class Meta:
        database = db

class Subscriptions(Model):
    playerId = ForeignKeyField(Players, backref='playersubscription', on_delete='CASCADE')
    gametypeId = ForeignKeyField(GameTypes, backref='gamesubscription', on_delete='CASCADE')

    class Meta:
        database = db
