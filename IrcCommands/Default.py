import datetime

#Called when pm'd with anything that's not a function
def run(user, msg, ircClient):
	now = datetime.datetime.now()
	time = now.strftime('%r')
	print(f'{time} {user}: {msg}')