import datetime

def run(user, msg, ircClient):
	now = datetime.datetime.now()
	time = now.strftime('%r')
	print(f'{time} {user}: {msg}')