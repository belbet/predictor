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
RDB_RAW_DB = os.environ.get('RDB_RAW_DB') or 'raw'
RDB_RAW_TABLE = os.environ.get('RDB_RAW_TABLE') or 'fte_predictions'
RDB_PREDICTOR_DB = os.environ.get('RDB_PREDICTOR_DB') or 'predictor'
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

# Yesterday
start_time = int(time.time() - 86400)

# Now
# end_time = int(time.time())

print("Determining min odds and good odds based on fte predictions")
