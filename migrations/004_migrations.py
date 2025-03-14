import peewee as pw
from peewee_migrate import Migrator
from contextlib import suppress
from model import Players

with suppress(ImportError):
    pass

def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
  for player in Players.select():
    if not player.statsMatrixName:
        player.statsMatrixName = player.statsName
        player.save()
  
def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
  pass