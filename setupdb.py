from model import *
import argparse
import json

def createDatabase():
    db.connect()
    db.create_tables([Players, GameTypes, Servers, PickupGames, PickupEntries, Subscriptions])
    db.close()

def createGameTypes():    
    db.connect()
    try:
        f = open("gametypes.json", encoding="utf-8")
        gametypes = json.loads(f.read()).items()
        f.close()
        for gametitle, gameinfo in gametypes:
            GameTypes.get_or_create(title=gametitle, playerCount=gameinfo["playerCount"], teamCount=gameinfo["teamCount"], statsName=gameinfo["statsName"])
    except:
        print("No table for gametypes found! Please execute 'createdb' first.")
    db.close()

def deleteGameTypes():
    db.connect()
    GameTypes.delete().execute()
    db.close()

def deletePickups():
    db.connect()
    PickupGames.delete().execute()
    db.close()

def main():
    parser = argparse.ArgumentParser(description="Commands for the pickup-database:")
    parser.add_argument('--createdb', help='Create database-file for the pickupbot', action='store_true')
    parser.add_argument('--creategametypes', help='Create common gametypes for the pickupbot', action='store_true')
    parser.add_argument('--deletegametypes', help='Delete gametypes from the database', action='store_true')
    parser.add_argument('--deletepickups', help='Delete past pickupgames from the database', action='store_true')
    args = parser.parse_args()
    if args.createdb:
        createDatabase()
    elif args.creategametypes:
        createGameTypes()
    elif args.deletegametypes:
        deleteGameTypes()
    elif args.deletepickups:
        deletePickups()

if __name__ == '__main__':
    main()