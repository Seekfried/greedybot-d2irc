import datetime
import peewee as pw
from peewee_migrate import Migrator
from contextlib import suppress

with suppress(ImportError):
    pass

def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    
    @migrator.create_model
    class Players(pw.Model):
        ircName = pw.CharField(unique=True, null=True)
        discordName = pw.CharField(unique=True, null=True)
        discordMention = pw.CharField(unique=True, null=True)
        statsName = pw.CharField(null=True)
        statsIRCName = pw.CharField(null=True)
        statsDiscordName = pw.CharField(null=True)
        statsId = pw.IntegerField(unique=True, null=True)
        shouldBridge = pw.BooleanField(default=True)

    @migrator.create_model
    class GameTypes(pw.Model):
        title = pw.CharField(unique=True)
        playerCount = pw.IntegerField(null=True)
        teamCount = pw.IntegerField(null=True)
        statsName = pw.CharField(null=True)

    @migrator.create_model
    class Servers(pw.Model):
        serverName = pw.CharField(unique=True)
        serverIp = pw.CharField(unique=True)

    @migrator.create_model
    class PickupGames(pw.Model):
        createdDate = pw.DateTimeField(default=datetime.datetime.now)
        gametypeId = pw.ForeignKeyField(GameTypes, backref='games', on_delete='CASCADE')
        isPlayed = pw.BooleanField(default=False)

    @migrator.create_model
    class PickupEntries(pw.Model):
        addedDate = pw.DateTimeField(default=datetime.datetime.now)
        addedFrom = pw.CharField(default='irc')
        playerId = pw.ForeignKeyField(Players, backref='addedgames', on_delete='CASCADE')
        gameId = pw.ForeignKeyField(PickupGames, backref='addedplayers', on_delete='CASCADE')
        isWarned = pw.BooleanField(default=False)

    @migrator.create_model
    class Subscriptions(pw.Model):
        playerId = pw.ForeignKeyField(Players, backref='playersubscription', on_delete='CASCADE')
        gametypeId = pw.ForeignKeyField(GameTypes, backref='gamesubscription', on_delete='CASCADE')
        
    def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
        migrator.remove_model('Subscriptions')
        migrator.remove_model('PickupEntries')
        migrator.remove_model('PickupGames')
        migrator.remove_model('Servers')
        migrator.remove_model('GameTypes')
        migrator.remove_model('Players')