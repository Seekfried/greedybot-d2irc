# greedybot-d2irc
A pickupbot for managing Xonotic pickup games

### Features:
- Managing pickup games over IRC and Discord (**maybe Matrix in the Future**)
- sync messages between IRC and Discord, with command for users to disable bridge function (**privacy reasons**)
- saving Players/Games/Gametypes/Servers in sqlite (**through peewee mysql, postgresql and cockroachdb possible too**)
- command for cup bracket generation (**needs chromium-based browser installed**)

## Installation and usage

**Note**: friedybot-d2irc requires Python >= 3.9, as it depends on [numpy 2.0.0](https://numpy.org/) and [discord.py](https://github.com/Rapptz/discord.py).

Download the code from this repository and configure setting.json (see [Configuration](https://github.com/Seekfried/friedybot-d2irc#configuration))

Install python dependencies
```bash
pip install -r requirements.txt
```

And run the bot:
```bash
python startbot.py
```

**NOTE**: In the first startup, it will create the `pickup.db` database file with the necessary tables. For
that, it will also read the `gametypes.json` file to populate the database with the predefined gametypes.

## Configuration

First you need to create a Discord bot user, which you can do by following the instructions [here](https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token).

The token is needed for the `settings.json` file.

To get the **server and channel ID** of your discord, just go to your discord server and write down the IDs found in the URL. **(Example below)**

![server-channel](https://i.imgur.com/MUbxESc.png)

### Settings.json
```js
{
    "irc": {
        "server": "",       //IRC-Server address
        "port": "",         //IRC-Server port
        "password": "",     //IRC-Server auth password
        "channel": "#",     //Your IRC-Channelname
        "nickname": "",     //IRC-Nickname for the bot
        "botowner": "",     //IRC-User that can close the bot with the !quit command
        "quitmsg": "Cya!"   //IRC quit message
    },
    "discord": {
        "token": "",        //Discord bot's token
        "botowner": "",     //Discord-User that can close the bot with the !quit command
        "server": "",       //Discord server ID
        "channel": "",      //Discord channel ID
        "modrole": "mods"   //Discord rolename to enable Admin/Moderator commands for users
    },
    "bot": {
        "pugtimewarning": 2400,     //time in seconds, to warn player that pickup is going to expire
        "pugtimeout": 3600,         //time in seconds, that pickup is expired
        "browser": "chrome"         //Browser used for cup generation "chrome", "edge", "chromium"
    },
    "database":{
        "filename": "pickups.db"     //Name of the SQLite File
    }
}
```

You can create your own `settings.json` file based on the template `settings_template.json`.

There are three other different setting files:
- **cmdresult.json**: command output texts and help texts
- **gametypes.json**: a collection of predefined game types 
- **xonotic.json**: xonotic flavoured messages for the !kill command

## Commands

### Player commands
- **!register**: Connect your account with your XonStats (stats.xonotic.org): `!register <xonstats-id>`
- **!pickups**: Shows all possible gametypes available for pickupgames: `!pickups`
- **!add**: Add to all current pickup games or specific games: `!add [gametype]`
- **!renew**: Renew pickup games
- **!remove**: Remove from all pickup games or specific games: `!remove [<gametype>]`
- **!server**: Show all available Xonotic servers or specific server and their IP: `!server <servername>`
- **!who**: List all current pickup games with players
- **!online**: List all current online discord-members for irc-users and vice versa
- **!info**: Show xonstat information about one player per playername or xonstats-id: `!info {<playername>|<statsid>}`
- **!subscribe**: Add to subscription to a specific gametype to get notified in !promote command:`!subscribe [<gametype>]`
- **!unsubscribe**: Remove from all gametype subscriptions or specific gametype subscription: `!unsubscribe [<gametype>]`
- **!promote**: Notify all players to gametype specific pickupgame: `!promote [<gametype>]`
- **!lastgame**: Show the last played pickupgame with date and players: `!lastgame`
- **!quote**: Get random quote from quoteDB or with playername from specific player: `!quote <playername>`
- **!serverinfo**: Get infos from server like name, map, player, gametype: `!serverinfo <servername>`
- **!kill**: Command for marking users with xonotic flavour (*see xonotic.json for more*)
- **!bridge**: Switch bridge functionality on or off (for yourself)
- **!start**: Force the start of a pickup game that doesn't have all the players yet: `!start <gametype>`
- **!top10**: Show the top 10 players who have participated the most in the last 30 days in the given game types. If no game types are provided, it returns the overall: `!top10 [<gametype>]`

### Admin/Moderator commands
*For discord-users with the role specific to `settings.json` (modrole) or IRC-users with OP*
- **!push**: add specific player to pickup games: `!push <player> [<gametype]>`
- **!pull**: remove specific player from pickup games: `!pull [<players>]`
- **!addgametype**: To add gametype: `!addgametype <gametypename> <playercount> <teamcount> <statsname>`
- **!addserver**: To add server: `!addserver <servername> <ip:port> [<ip:port>]`
- **!removegametype**: To delete gametype: `!removegametype [<gametypename>]`
- **!removeserver**: To delete server: `!removeserver [<servername>]`

### Cup Generation
- at the moment just direct cup generation with **!cupstart** (future feature -> with player signing in themselves)
- **!cupstart**: To generate cup brackets: `!cupstart <cuptitle> [<players/teams>]`

**example: !cupstart seeky-cup grunt hotdog ramses packer mirio**

![cup-generator](https://i.imgur.com/XqH5OXm.png)
