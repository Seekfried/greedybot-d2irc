import peewee as pw
from peewee_migrate import Migrator
from contextlib import suppress
import json
from pathlib import Path
from model import GameTypes

with suppress(ImportError):
    pass

def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
  if Path("gametypes.json").exists():
    try:
        f = open("gametypes.json", encoding="utf-8")
        gametypes = json.loads(f.read()).items()
        f.close()
        for gametitle, gameinfo in gametypes:
            GameTypes.get_or_create(title=gametitle, playerCount=gameinfo["playerCount"], teamCount=gameinfo["teamCount"], statsName=gameinfo["statsName"])
    except Exception as e:
        print('Error: %s', repr(e))
  migrator.rename_column('servers', 'serverIp', 'serverIPv4')
  migrator.change_columns('servers', serverIPv4=pw.CharField(unique=True, null=True))
  migrator.add_fields('servers', serverIPv6=pw.CharField(unique=True, null=True))
  
def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
  migrator.drop_column('servers', 'serverIPv6')
  migrator.rename_column('servers', 'serverIPv4', 'serverIp')
  migrator.change_columns('servers', serverIp=pw.CharField(unique=True))

