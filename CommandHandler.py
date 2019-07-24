import Commands

#   When new command is created in Commands folder, do the following
#     1. Add the import in Commands/__init__.py
#     2. Create a function here to call the function in Commands
#     3. Add the command trigger to CommandsList
#     4. Add trigger:function to CommandSwitch
def Handle(msg, ircClient):
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
    commandToRun(msg, ircClient)

def parseCommand(msg, commandList):
    for command in commandList:
        if (msg.find(command) != -1):
            return command
    return 'default'

def isListening(msg, ircClient):
    Commands.IsListening.run(msg, ircClient)

def isPlaying(msg, ircClient):
    Commands.IsPlaying.run(msg, ircClient)

def with_(msg, ircClient):
    Commands.With.run(msg, ircClient)

def mods(msg, ircClient):
    Commands.Mods.run(msg, ircClient)

def discord(msg, ircClient):
    Commands.Discord.run(msg, ircClient)

def help_(msg, ircClient):
    Commands.Help.run(msg, ircClient)

def default(msg, ircClient):
    Commands.Default.run(msg, ircClient)