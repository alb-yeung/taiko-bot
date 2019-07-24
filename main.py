#!/usr/bin/env python3
import datetime
import locale
import re
import sys
import threading

import apiReq
import config
import irccon
import pp
import rateLimiting

QUIT = False

conf = config.Config('bot.conf')

locale.setlocale(locale.LC_TIME, '')

api = apiReq.API(conf)

# Rounds a number and converts it back to a string.
def roundString(s: str, digits: int):
	n = round(float(s), digits)
	return str(n)

# IRC Setup

ircName = conf.get('username')

irc = irccon.IRC()
irc.server(conf.get('ircServer'), conf.get('port'))
irc.auth(ircName, conf.get('pw'))
irc.setRecvBufSize(conf.get('recv_buf'))
irc.setRateLimit(conf.get('rate_limit'))

# Rate limiting setup

rateLimiting.setBurstTime(conf.get('burst_time'))
rateLimiting.setMinuteLimit(conf.get('minute_count'))

# The main hook of the bot. This is called when a PRIVMSG is received.
# The function finds issued commands and responds correspondingly.
def msgHook(ircClient: irccon.IRC, line):
	user = line['user']
	msg: str = line['msg']

	# NEVER EVER REMOVE THIS!!!!! We can't have ANY messages sent to a channel!
	if msg.find('#') != -1:
		return
	
	elif msg.find('is listening') != -1:
		if rateLimiting.rateLimit(conf, user):
			irc.msg(user, 'Whoa! Slow down there, bud!')
			print(f'Rate limited user {user}.')
			return

		irc.msg(user, 'Please start playing the beatmap you want and then do /np!')
		print(f'User {user} listened to a beatmap!\n')
		return

	# If a user wants to know the pp of a map via /np.
	elif msg.find('is playing') != -1:
		if rateLimiting.rateLimit(conf, user):
			irc.msg(user, 'Whoa! Slow down there, bud!')
			print(f'Rate limited user {user}.')
			return

		diffnameRegex = re.compile(r'\[.*\[(.*)\]\]') # The regex finding the difficulty name, see 'diffname ='.
		setidRegex = re.compile(r'/b/([0-9]*)')       # The regex finding the set id, see 'setid ='.

		setid = setidRegex.search(msg).group(1)
		diffname = diffnameRegex.search(msg).group(1) # Search for [...], e.g. [Oni]
		isTaiko = bool(re.search(r'<Taiko>', msg))    # Determines whether the beatmap is in taiko mode or not.
												      # This will not filter out converts!

		modsVal = 0 # The binary number given to pp.calcPP() containing the enabled mods.
		mods = ''   # The string used for message building.

		for mod in pp.mods: # Loop through the mods and change the modsVal according to the enabled mods.
			if msg.find('+' + mod) != -1:
				modsVal += pp.mods[mod]
				mods = ' '.join([mods, f'+{mod}'])

		# Console logging
		print(f'{user} issued a request for beatmap set id {setid}, difficulty [{diffname}]{mods}, the beatmap was ', end='')
		if isTaiko:
			print('in taiko mode.')
		else:	
			print('not in taiko mode.')
							
		requestedBeatmap = None # Set to None to check if set later on.

		foundTaikoMap = False   # Was there a taiko map in the set?
		
		beatmapSet = api.getBeatmap(setid, modsVal)
		
		for beatmap in beatmapSet: # Loop through all the beatmaps in the set
			if beatmap['mode'] != '1': # Speed up the process for mixed-mode beatmap sets
				continue
			
			if beatmap['mode'] == '1': # 'mode' == 1 means the beatmap mode is osu!taiko.
				foundTaikoMap = True
			
			if beatmap['version'] != diffname: # Skip the difficulties with the wrong difficulty name.
				continue
			
			requestedBeatmap = beatmap
			conf.save(user, [beatmap, modsVal, 100.0, 0])
		
		if requestedBeatmap == None and foundTaikoMap == True:
			print(f'Beatmap set id {setid} with difficulty name [{diffname}] could not be found. Is there an error?')
			irc.msg(user, 'I\'m sorry, but the beatmap could not be found. Perhaps Bancho had an error?')
			return
		elif foundTaikoMap == False:
			print(f'Beatmap set id {setid} did not contain a Taiko difficulty.')
			irc.msg(user, 'The map you requested doesn\'t appear to be a taiko map. Converts are not (yet) supported, sorry.')
			return
		
		# Metadata collection for marginally easier to read code.
		artist = requestedBeatmap['artist']
		title = requestedBeatmap['title']
		diffName = requestedBeatmap['version']
		creator = requestedBeatmap['creator']
		stars = float(requestedBeatmap['difficultyrating'])
		starsRounded = roundString(stars, 2)
		maxCombo = int(requestedBeatmap['count_normal'])
		od = pp.scaleHPOD(float(requestedBeatmap['diff_overall']), modsVal)
		hp = pp.scaleHPOD(float(requestedBeatmap['diff_drain']), modsVal)
		bpm = requestedBeatmap['bpm'] # Not converted to int because we only use it for printing
		
		# The first line shown to the user containing general info about the difficulty.
		irc.msg(user, f'{artist} - {title} [{diffName}] by {creator}, {starsRounded}* {mods} OD{od} HP{hp} BPM: {bpm} FC: {maxCombo}')
		
		ppString = '' # The string shown to the user as the second line in the end.
		
		# Calculate the pp for the accuracies in the tuple
		for acc in (95.0, 96.0, 97.0, 98.0, 99.0, 100.0):
			ppVal = roundString(pp.calcPP(stars, maxCombo, maxCombo, pp.getHundreds(maxCombo, 0, acc), 0, acc, od, modsVal), 2)
			e = ' | ' # Separator
			if acc == 95.0: # Avoid a trailing ' | '.
				e = ''
			ppString = f'{ppString}{e}{acc}%: {ppVal}pp'

		# The second line.
		irc.msg(user, ppString)
		print(f'OD{od} {starsRounded}* FC: {maxCombo}x')
		print(ppString + '\n')

		conf.save(user, [requestedBeatmap, modsVal, 100, 0])

		return
	# Calculates the pp of the last /np'd map with a certain accuracy and miss count.
	elif msg.find('!with') != -1:
		if rateLimiting.rateLimit(conf, user):
			irc.msg(user, 'Whoa! Slow down there, bud!')
			print(f'Rate limited user {user}.')
			return

		try:
			userBeatmap = conf.load(user)
		except KeyError:
			irc.msg(user, 'Please select a beatmap first! (Type /np)')
			print(f'User {user} issued !with without a beatmap selected.')
			return

		lastBm = userBeatmap[0]
		mods = userBeatmap[1]

		artist = lastBm['artist']
		title = lastBm['title']
		diffName = lastBm['version']
		stars = float(lastBm['difficultyrating'])
		maxCombo = int(lastBm['count_normal'])
		od = pp.scaleHPOD(float(lastBm['diff_overall']), mods)

		arg1Regex = re.compile(r'!with ([^ ]*)? ') # Gets the first argument
		arg2Regex = re.compile(r'!with .*? ([^ ]*)?')

		accFloatRegex = re.compile(r'([0-9]{1,3})[\.\,]([0-9]{1,2})[%]*') # xx[x].yy[%] => Group 1: xx[x]; Group 2: yy
		accIntRegex = re.compile(r'([0-9]{1,3})[%]*') # xx[x][%] -> Group 1: xx[x]

		print(f'User {user} issued a !with command.')

		rawAcc = arg1Regex.search(msg)
		if rawAcc == None: # No first argument?
			irc.msg(user, 'Usage: !with <accuracy> <misses>')
			print(f'Printed usage for !with for {user}. (No arguments)')
			return

		accMatch = accFloatRegex.search(rawAcc.group(0))
		if accMatch == None: # Couldn't find the accuracy (xx[x].yy[%]).
			accMatch = accIntRegex.search(rawAcc.group(0))
			if accMatch == None: # Couldn't find the accuracy (xx[x][%]). -> Odd argument.
				irc.msg(user, 'Usage: !with <accuracy> <misses>')
				print(f'Printed usage for !with for {user}. (Odd accuracy)')
				return
			
			acc = float(accMatch.group(1))
		else:
			acc = float(accMatch.group(1) + '.' + accMatch.group(2)) # Two groups ignoring the floating point cuz localization.

		rawMisses = arg2Regex.search(msg)
		if rawMisses == None: # No second argument?
			irc.msg(user, 'Usage: !with <accuracy> <misses>')
			print(f'Printed usage for !with for {user}. (No second argument)')
			return

		missesMatch = re.search('([0-9]*)', rawMisses.group(1)) # Look if the second argument only contains numbers.
		if missesMatch == None:
			irc.msg(user, 'Usage: !with <accuracy> <misses>')
			print(f'Printed usage for !with for {user}. (Odd misses)')
			return

		misses = int(missesMatch.group(0))

		hundreds = pp.getHundreds(maxCombo, misses, acc)

		peppyPoints = roundString(pp.calcPP(stars, maxCombo, maxCombo - misses, hundreds, misses, acc, od, mods), 2)

		modString = pp.getModString(mods)

		irc.msg(user, f'{artist} - {title} [{diffName}]{modString} | {acc}%, {misses} misses: {peppyPoints}')
		print(f'{artist} - {title} [{diffName}]{modString} | {acc}%, {misses} misses: {peppyPoints}')

		conf.save(user, [lastBm, mods, acc, misses])

		return
	elif msg.find('!mods') != -1:
		if rateLimiting.rateLimit(conf, user):
			irc.msg(user, 'Whoa! Slow down there, bud!')
			print(f'Rate limited user {user}.')
			return

		try:
			mods = pp.getModVal(msg)

			userBeatmap = conf.load(user)
		except KeyError:
			irc.msg(user, 'Please select a beatmap first! (Type /np)')
			print(f'User {user} issued !with without a beatmap selected.')
			return
		except:
			print('Usage: mods <mod1> [mod2] [mod3]...')
			return

		lastBm = userBeatmap[0]
		acc = userBeatmap[2]
		misses = userBeatmap[3]

		artist = lastBm['artist']
		title = lastBm['title']
		diffName = lastBm['version']
		creator = lastBm['creator']
		stars = float(lastBm['difficultyrating'])
		starsRounded = roundString(stars, 2)
		maxCombo = int(lastBm['count_normal'])
		od = float(lastBm['diff_overall'])
		hp = pp.scaleHPOD(float(lastBm['diff_drain']), mods)
		bpm = lastBm['bpm'] # Not converted to int because we only use it for printing
		
		hundreds = pp.getHundreds(maxCombo, misses, acc)

		modString = pp.getModString(mods)
		
		irc.msg(user, f'{artist} - {title} [{diffName}] by {creator}, {starsRounded}* {modString} OD{od} HP{hp} BPM: {bpm} FC: {maxCombo}')

		ppString = ''

		# Calculate the pp for the accuracies in the tuple
		for acc in (95.0, 96.0, 97.0, 98.0, 99.0, 100.0):
			ppVal = roundString(pp.calcPP(stars, maxCombo, maxCombo, pp.getHundreds(maxCombo, 0, acc), 0, acc, od, mods), 2)
			e = ' | ' # Separator
			if acc == 95.0: # Avoid a trailing ' | '.
				e = ''
			ppString = f'{ppString}{e}{acc}%: {ppVal}pp'

		od = pp.scaleHPOD(od, mods)

		# The second line.
		irc.msg(user, ppString)
		print(f'OD{od} HP{hp} {starsRounded}* FC: {maxCombo}x')
		print(ppString + '\n')

		conf.save(user, [lastBm, mods, acc, misses])

		return
	elif msg.find('!discord') != -1:
		irc.msg(user, 'The place to talk about the bot or just chat: https://discord.gg/hKXQdm2')
		print(f'Printed discord invite for {user}.')

		return
	elif msg.find('!help') != -1:
		irc.msg(user, 'A list of commands can be found in the [GitHub wiki](https://github.com/SarahIsWeird/taiko-bot/wiki/Commands).')
		print(f'Printed command list for {user}.')

		return
	else:
		# A normal chat message, mostly for convenience. (Avoids tabbing a bit while developing)
		now = datetime.datetime.now()
		time = now.strftime('%r')
		print(f'{time} {user}: {msg}')

class ConsoleThread(threading.Thread):
	currStr = ''

	currMode = 'menu'

	bm_id = None
	bm_acc = None
	bm_misses = None

	def run(self):
		print('<3 Welcome to Sarah\'s bot console! :D Here\'s a list of commands you can use:')
		print('<3  beatmap | bm: Test the beatmap feature!')
		print('<3 lastplay | lp: Calls /beatmap/ with your last played map!')
		print('<3     with |  w: Sets the accuracy and misses for the last queried map.')
		print('<3     quit |  q: Quit! D:')
		print('<3 Enter \'cancel\' at anytime to stop the current command!')
		print('')

		while True:
			consoleInput = input('').strip()

			bm_id = None
			bm_acc = None
			bm_misses = None

			if consoleInput == 'quit' or consoleInput == 'q':
				irc.queueEvent(irccon.IRCQuitEvent())
				return
			
			elif consoleInput == 'lastplay' or consoleInput == 'lp':
				lastPlay = api.getUserRecent(ircName)[0]

				fulls = int(lastPlay['count300'])
				hundreds = int(lastPlay['count100'])
				misses = int(lastPlay['countmiss'])
				mods = int(lastPlay['enabled_mods'])
				combo = int(lastPlay['maxcombo'])

				beatmap = api.getBeatmap(lastPlay['beatmap_id'], mods)[0]
				conf.save(ircName, [beatmap, mods])

				artist = beatmap['artist']
				title = beatmap['title']
				diffName = beatmap['version']
				stars = float(beatmap['difficultyrating'])
				od = float(beatmap['diff_overall'])
				maxcombo = int(beatmap['count_normal'])

				acc = (hundreds * 0.5 + fulls) / maxcombo * 100
				accStr = roundString(acc, 2)

				peppyPoints = roundString(pp.calcPP(stars, maxcombo, maxcombo - misses, hundreds,
					misses, acc, od, mods), 2)
				
				modStr = pp.getModString(mods)

				print(f'<3 {artist} - {title} [{diffName}]{modStr} | {accStr}%, {misses} misses, FC: {maxcombo}')
				print(f'<3 Highest Combo: {combo} | {peppyPoints}pp')

			elif consoleInput == 'beatmap' or consoleInput == 'bm':
				try:
					bm_id = input('<3 Awesome! First we need a beatmap id: ').strip()
					if bm_id == 'cancel':
						continue
					bm_id = int(bm_id)

					bm_acc = input('<3 Now the accuracy: ').strip()
					if bm_acc == 'cancel':
						continue
					bm_acc = float(bm_acc)
					
					bm_misses = input('<3 How many misses? ').strip()
					if bm_misses == 'cancel':
						continue
					bm_misses = int(bm_misses)

					# bm_mods = input('')
				except:
					if bm_id == None:
						print('<3 Please enter a valid beatmap id!')
					elif bm_acc == None:
						print('<3 Please enter a valid accuracy! (No percent sign!)')
					else:
						print('<3 Please enter a valid number of misses!')
					continue

				beatmap = api.getBeatmap(bm_id)[0]
				conf.save(ircName, [beatmap, pp.mods['noMod'], bm_acc, bm_misses])

				artist = beatmap['artist']
				title = beatmap['title']
				diffName = beatmap['version']
				stars = float(beatmap['difficultyrating'])
				od = int(beatmap['diff_overall'])
				maxcombo = int(beatmap['count_normal'])

				peppyPoints = roundString(pp.calcPP(stars, maxcombo, maxcombo - bm_misses, pp.getHundreds(maxcombo, bm_misses, bm_acc),
					bm_misses, bm_acc, od, pp.mods['noMod']), 2)

				print(f'<3 {artist} - {title} [{diffName}] | {bm_acc}%, {bm_misses} misses, FC: {maxcombo}')
				print(f'<3 {peppyPoints}pp')
			elif consoleInput.startswith('with ') or consoleInput.startswith('w '):
				splitInput = consoleInput.split(' ')

				try:
					acc = float(splitInput[1])
					misses = int(splitInput[2])

					userBeatmap = conf.load(ircName)
				except KeyError:
					print('Please select a beatmap first!')
					continue
				except:
					print('Usage: with <acc> <misses>')
					continue

				lastBm = userBeatmap[0]
				mods = userBeatmap[1]

				artist = lastBm['artist']
				title = lastBm['title']
				diffName = lastBm['version']
				stars = float(lastBm['difficultyrating'])
				maxCombo = int(lastBm['count_normal'])
				od = float(lastBm['diff_overall'])
				
				hundreds = pp.getHundreds(maxCombo, misses, acc)

				peppyPoints = roundString(pp.calcPP(stars, maxCombo, maxCombo - misses, hundreds, misses, acc, od, mods), 2)

				modString = pp.getModString(mods)

				print(f'{artist} - {title} [{diffName}]{modString} | {acc}%, {misses} misses: {peppyPoints}')

				conf.save(ircName, [lastBm, mods, acc, misses])
			elif consoleInput.startswith('mods ') or consoleInput.startswith('m '):
				splitInput = consoleInput.split(' ')

				try:
					mods = pp.getModVal(consoleInput)

					userBeatmap = conf.load(ircName)
				except KeyError:
					print('Please select a beatmap first!')
					continue
				except:
					print('Usage: mods <mod1> [mod2] [mod3]...')
					continue

				lastBm = userBeatmap[0]
				acc = userBeatmap[2]
				misses = userBeatmap[3]

				artist = lastBm['artist']
				title = lastBm['title']
				diffName = lastBm['version']
				stars = float(lastBm['difficultyrating'])
				maxCombo = int(lastBm['count_normal'])
				od = float(lastBm['diff_overall'])
				
				hundreds = pp.getHundreds(maxCombo, misses, acc)

				peppyPoints = roundString(pp.calcPP(stars, maxCombo, maxCombo - misses, hundreds, misses, acc, od, mods), 2)

				modString = pp.getModString(mods)

				print(f'{artist} - {title} [{diffName}]{modString} | {acc}%, {misses} misses: {peppyPoints}')
				conf.save(ircName, [lastBm, mods, acc, misses])

# Add the hook on a PRIVMSG to the client.
irc.addEventHook('PRIVMSG', msgHook)

consoleThread = ConsoleThread()
consoleThread.start()

while True:
	irc.receive()
