# greedybot-d2irc
A pickupbot for managing Xonotic pickup games

### Features:
- Managing pickup games over IRC and Discord (**maybe Matrix in the Future**)
- sync messages between IRC, Discord and Matrix, with command for users to disable bridge function (**privacy reasons**)
- saving Players/Games/Gametypes/Servers in sqlite (**through peewee mysql, postgresql and cockroachdb possible too**)

## Installation and usage

**Note**: greedybot-d2irc requires Python >= 3.9, as it depends on [numpy 2.0.0](https://numpy.org/) and [discord.py](https://github.com/Rapptz/discord.py).

Download the code from this repository and configure setting.yaml (see [Configuration](https://github.com/Seekfried/greedybot-d2irc#configuration))

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

The token is needed for the `settings.yaml` file.

To get the **server and channel ID** of your discord, just go to your discord server and write down the IDs found in the URL. **(Example below)**

![server-channel](https://i.imgur.com/MUbxESc.png)

### Settings.yaml
```yaml
bot:
  # Issue warning to renew pickup to player after x seconds
  pugtimewarning: 2400 
  # Delete player from pickup after x seconds
  pugtimeout: 3600

database:
  # Name of created SQLite file
  filename: "pickups.db"

# You can comment out/delete the following chattypes you dont need
irc:
  # IRC-Server address
  server: ""
  # IRC-Server port
  port: ""
  # IRC-Server auth password
  password: ""
  # IRC-Channelname
  channel: ""
  # IRC-Nickname for the bot
  nickname: ""
  # IRC-User that can close the bot with the !quit command
  botowner: ""
  # IRC quit message
  quitmsg: "Cya!"
  # Show messages if irc user left/joined the channel
  presence-update: false

discord:
  # Discord bot's token
  token: ""
  # Discord-User that can close the bot with the !quit command
  botowner: ""
  # Discord server ID
  server: ""
  # Discord channel ID
  channel: ""
  # Discord rolename to enable Admin/Moderator commands for users
  modrole: ""
  # Show messages if discord user goes offline/online
  presence-update: false

matrix:
  # Matrix server url
  server: ""
  # Matrix room ID
  room: ""
  # Matrix bot name
  botname: ""
  # Matrix bot password
  password: ""
```

You can create your own `settings.yaml` file based on the template `settings_template.yaml`.

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
*For discord-users with the role specific to `settings.yaml` (modrole) or IRC-users with OP*
- **!push**: add specific player to pickup games: `!push <player> [<gametype]>`
- **!pull**: remove specific player from pickup games: `!pull [<players>]`
- **!addgametype**: To add gametype: `!addgametype <gametypename> <playercount> <teamcount> <statsname>`
- **!addserver**: To add server: `!addserver <servername> <ip:port> [<ip:port>]`
- **!removegametype**: To delete gametype: `!removegametype [<gametypename>]`
- **!removeserver**: To delete server: `!removeserver [<servername>]`