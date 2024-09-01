import peewee as pw
from peewee_migrate import Migrator
from contextlib import suppress
from model import GameTypes

with suppress(ImportError):
    pass

def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
  migrator.add_fields('players', matrixName=pw.CharField(unique=True, null=True), statsMatrixName=pw.CharField(null=True))
  
def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
  migrator.remove_fields('players', 'matrixName', 'statsMatrixName')

