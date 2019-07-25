import ConsoleCommands

#   When new command is created in ConsoleCommands folder, do the following
#     1. Add the import in ConsoleCommands/__init__.py
#     2. Create a function here to call the function in ConsoleCommands
#     3. Add the command trigger to CommandsList
#     4. Add trigger:function to CommandSwitch
def Handle(msg, conf, api, ircName):
    CommandsList = [
        "beatmap", "bm",
        "lastplay", "lp",
        "with", "w"
    ]
    CommandSwitch = {
        "beatmap" : beatmap, "bm" : beatmap,
        "lastplay" : lastplay, "lp" : lastplay,
        "with" : with_, "w" : with_,
        "default" : default
    }
    actualCommand = parseCommand(msg, CommandsList)
    commandToRun = CommandSwitch.get(actualCommand)
    commandToRun(msg, conf, api, ircName)

def parseCommand(msg, commandList):
    for command in commandList:
        if (msg.startswith(command)):
            return command
    return 'default'

def beatmap(msg, conf, api, ircName):
    ConsoleCommands.Beatmap.run(msg, conf, api, ircName)

def lastplay(msg, conf, api, ircName):
    ConsoleCommands.LastPlay.run(msg, conf, api, ircName)

def with_(msg, conf, api, ircName):
    ConsoleCommands.With.run(msg, conf, api, ircName)

def default(msg, conf, api, ircName):
    print('Command not found')