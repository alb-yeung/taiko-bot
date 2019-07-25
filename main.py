#!/usr/bin/env python3
import datetime
import locale
import re
import sys
import threading

from Utils import apiReq
from Utils import config
from Utils import irccon
from Utils import pp
from Utils import rateLimiting
from Utils import CommandHandler
from Utils import roundString

QUIT = False

conf = config.Config('bot.conf')

locale.setlocale(locale.LC_TIME, '')

api = apiReq.API(conf)

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
	
	if rateLimiting.rateLimit(conf, user):
		irc.msg(user, 'Whoa! Slow down there, bud!')
		print(f'Rate limited user {user}.')
		return

	CommandHandler.Handle(user, msg, ircClient)


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
				accStr = roundString.roundString(acc, 2)

				peppyPoints = roundString.roundString(pp.calcPP(stars, maxcombo, maxcombo - misses, hundreds, misses, acc, od, mods), 2)
				
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

				peppyPoints = roundString.roundString(pp.calcPP(stars, maxcombo, maxcombo - bm_misses, pp.getHundreds(maxcombo, bm_misses, bm_acc), bm_misses, bm_acc, od, pp.mods['noMod']), 2)

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

				peppyPoints = roundString.roundString(pp.calcPP(stars, maxCombo, maxCombo - misses, hundreds, misses, acc, od, mods), 2)

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
