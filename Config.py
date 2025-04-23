import os


class Config(object):
	BOT_TOKEN = os.environ.get("BOT_TOKEN","5088657122:AAGXARfg6sSX1p1ge876jknkrJizwH959b4")
	API_ID = int(os.environ.get("API_ID", "3335796"))
	API_HASH = os.environ.get("API_HASH","138b992a0e672e8346d8439c3f42ea78")
