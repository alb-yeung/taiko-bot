import IrcCommands

#   When new command is created in Commands folder, do the following
#     1. Add the import in Commands/__init__.py
#     2. Create a function here to call the function in Commands
#     3. Add the command trigger to CommandsList
#     4. Add trigger:function to CommandSwitch
def Handle(user, msg, ircClient):
    CommandsList = [
        "is listening",
        "is playing",
        "!with",
        "!mods",
        "!discord",
        "!help"
    ]
    CommandSwitch = {
        "is listening" : isListening,
        "is playing" : isPlaying,
        "!with" : with_,
        "!mods" : mods,
        "!discord" : discord,
        "!help" : help_,
        "default" : default
    }
    actualCommand = parseCommand(msg, CommandsList)
    commandToRun = CommandSwitch.get(actualCommand)
    commandToRun(user, msg, ircClient)

def parseCommand(msg, commandList):
    for command in commandList:
        if (msg.find(command) != -1):
            return command
    return 'default'

def isListening(user, msg, ircClient):
    IrcCommands.IsListening.run(user, msg, ircClient)

def isPlaying(user, msg, ircClient):
    IrcCommands.IsPlaying.run(user, msg, ircClient)

def with_(user, msg, ircClient):
    IrcCommands.With.run(user, msg, ircClient)

def mods(user, msg, ircClient):
    IrcCommands.Mods.run(user, msg, ircClient)

def discord(user, msg, ircClient):
    IrcCommands.Discord.run(user, msg, ircClient)

def help_(user, msg, ircClient):
    IrcCommands.Help.run(user, msg, ircClient)

def default(user, msg, ircClient):
    IrcCommands.Default.run(user, msg, ircClient)