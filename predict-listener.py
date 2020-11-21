from rethinkdb import RethinkDB
from rethinkdb.errors import RqlRuntimeError, RqlDriverError
from dotenv import load_dotenv
import requests
import os
load_dotenv()

RDB_HOST = os.environ.get('RDB_HOST') or 'localhost'
RDB_PORT = os.environ.get('RDB_PORT') or 28015
RDB_PASS = os.environ.get('RDB_PASS') or ''
RDB_ECOUTOR_DB = os.environ.get('RDB_ECOUTOR_DB') or 'test'
RDB_ECOUTOR_TABLE = os.environ.get('RDB_ECOUTOR_TABLE') or 'ecoutor_matches'

r = RethinkDB()

connection = r.connect(host=RDB_HOST, port=RDB_PORT,
                       db=RDB_ECOUTOR_DB, password=RDB_PASS)

cursor = r.table(RDB_ECOUTOR_TABLE).changes().run(connection)
for document in cursor:
    if document["new_val"] != None:
        data = {'matchId': document["new_val"]["matchId"],
                'matchStart': document["new_val"]["matchStart"],
                'team1': document["new_val"]["club1Id"], 'team2': document["new_val"]["club2Id"]}
        print(data)
        r = requests.post('http://localhost:5000/prediction',
                          json=data)
