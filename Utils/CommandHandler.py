import IrcCommands

#   When new command is created in IrcCommands folder, do the following
#     1. Add the import in IrcCommands/__init__.py
#     2. Create a function here to call the function in IrcCommands
#     3. Add the command trigger to CommandsList
#     4. Add trigger:function to CommandSwitch
def handle(user, msg, ircClient, conf, api):
    commandsList = [
        "is listening",
        "is playing",
        "!with",
        "!mods",
        "!discord",
        "!help"
    ]
    commandSwitch = {
        "is listening" : isListening,
        "is playing" : isPlaying,
        "!with" : with_,
        "!mods" : mods,
        "!discord" : discord,
        "!help" : help_,
        "default" : default
    }
    actualCommand = parseCommand(msg, CommandsList)
    commandToRun = commandSwitch[actualCommand]
    commandToRun(user, msg, ircClient, conf, api)

def parseCommand(msg, commandList):
    if command in msg:
        return command
    return 'default'

def isListening(user, msg, ircClient, conf, api):
    IrcCommands.IsListening.run(user, msg, ircClient, conf, api)

def isPlaying(user, msg, ircClient, conf, api):
    IrcCommands.IsPlaying.run(user, msg, ircClient, conf, api)

def with_(user, msg, ircClient, conf, api):
    IrcCommands.With.run(user, msg, ircClient, conf, api)

def mods(user, msg, ircClient, conf, api):
    IrcCommands.Mods.run(user, msg, ircClient, conf, api)

def discord(user, msg, ircClient, conf, api):
    IrcCommands.Discord.run(user, msg, ircClient, conf, api)

def help_(user, msg, ircClient, conf, api):
    IrcCommands.Help.run(user, msg, ircClient, conf, api)

def default(user, msg, ircClient, conf, api):
    IrcCommands.Default.run(user, msg, ircClient, conf, api)