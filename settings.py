from dotenv import load_dotenv
import os
import time
from logging.config import dictConfig
from rethinkdb import RethinkDB
from rethinkdb.errors import RqlRuntimeError, RqlDriverError

load_dotenv()

# Connections parameters
RDB_HOST = os.environ.get('RDB_HOST') or 'localhost'
RDB_PORT = os.environ.get('RDB_PORT') or 28015
RDB_PASS = os.environ.get('RDB_PASS') or ''
RDB_RAW_DB = os.environ.get('RDB_RAW_DB') or 'test'
RDB_RAW_TABLE = os.environ.get('RDB_RAW_TABLE') or 'matches'
RDB_PREDICTOR_DB = os.environ.get('RDB_PREDICTOR_DB') or 'test'
RDB_PREDICTOR_TABLE = os.environ.get('RDB_PREDICTOR_TABLE') or 'predictions'
# Weight parameters
WEIGHT_H2H = float(os.environ.get('WEIGHT_H2H')) or 1.5
WEIGHT_HOME = float(os.environ.get('WEIGHT_HOME')) or 1.2
WEIGHT_EXT = float(os.environ.get('WEIGHT_EXT')) or 0.8

r = RethinkDB()

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

# 2017-08-01 00:00:00 - Start of the 2017-2018 season
start_time = 1501545600

# Now
end_time = int(time.time())

print("Determining odds based on all matches played between",
      start_time, "and", end_time)
