from logging.config import dictConfig
import argparse
import json
import os
import decimal
import time
import logging

from predictor import Predictor
from counselor import Counselor
from rethinkdb import RethinkDB
from rethinkdb.errors import RqlRuntimeError, RqlDriverError
from settings import *
from flask import Flask, g, jsonify, render_template, request, abort, Response


def dbSetup():
    connection_raw = r.connect(host=RDB_HOST, port=RDB_PORT,
                               db=RDB_RAW_DB, password=RDB_PASS)
    connection_predictor = r.connect(host=RDB_HOST, port=RDB_PORT,
                                     db=RDB_PREDICTOR_DB, password=RDB_PASS)

    try:
        r.db_create(RDB_PREDICTOR_DB).run(connection_predictor)
    except RqlRuntimeError:
        print(f'Predictor database {RDB_PREDICTOR_DB} already exists.')
    try:
        r.db(RDB_PREDICTOR_DB).table_create(
            RDB_PREDICTOR_TABLE, primary_key='match_id').run(connection_predictor)
        r.table(RDB_PREDICTOR_TABLE).index_create(
            'match_date').run(connection_predictor)
        print('Predictor table created !')
    except RqlRuntimeError:
        print(f'Predictor table {RDB_PREDICTOR_TABLE} already exists')
        print('Database setup completed. Now run the app without --setup.')
    finally:
        connection_raw.close()
        connection_predictor.close()


app = Flask(__name__)
app.config.from_object(__name__)


@app.before_request
def before_request():
    try:
        g.connection_raw = r.connect(host=RDB_HOST, port=RDB_PORT,
                                     db=RDB_RAW_DB, password=RDB_PASS)
    except RqlDriverError:
        abort(503, "No database connection could be established.")
    try:
        g.connection_predictor = r.connect(host=RDB_HOST, port=RDB_PORT,
                                           db=RDB_PREDICTOR_DB, password=RDB_PASS)
    except RqlDriverError:
        abort(503, "No database connection could be established.")


@app.teardown_request
def teardown_request(exception):
    try:
        g.connection_raw.close()
        g.connection_predictor.close()
    except AttributeError:
        pass


@ app.route("/prediction/<string:match_id>", methods=['GET'])
def get_prediction(match_id):
    response = Predictor.get_match_prediction(match_id)
    return jsonify(response)


def match_id_exists(match_id):
    match = Predictor.get_match_prediction(match_id)
    if match:
        return True
    return False


def calculate_prediction(match_id, team1, team2):
    predictor = Predictor(match_id, team1, team2, w_h2h=WEIGHT_H2H,
                          w_home=WEIGHT_HOME, w_ext=WEIGHT_EXT)
    app.logger.info("Set stats")
    predictor.set_stats_team(team1)
    predictor.set_stats_team(team2)
    predictor.set_stats_h2h()
    predictor.set_odds()
    app.logger.info("Write to db")
    predictor.write_prediction_to_db()


@ app.route("/prediction", methods=['POST'])
def post_prediction():
    match_id = request.json['matchId']
    if match_id_exists(match_id):
        return Response("Match already exists", 200)
    match_start = request.json['matchStart']
    team1 = request.json['team1']
    team2 = request.json['team2']
    if match_id == None or team1 == None or team2 == None:
        return {}
    app.logger.info("Init %s vs %s: match id %s", team1, team2, match_id)
    app.logger.info("Weights are H2H: %s, HOME: %s, EXT: %s", WEIGHT_H2H,
                    WEIGHT_HOME, WEIGHT_EXT)
    calculate_prediction(match_id, team1, team2)
    return Response(status=201)


def counseling():
    print(start_time, start_time + 86400 * 7)
    matches = list(r.table(RDB_RAW_TABLE).between(r.epoch_time(
        start_time), r.epoch_time(start_time + 86400 * 7), index='Date').run(g.connection_raw))
    for match in matches:
        counsel = Counselor(match)
        counsel.set_min_odds()
        app.logger.info(
            f"min odds: {counsel.team1_min_odds} ; {counsel.team2_min_odds} ; {counsel.draw_min_odds}")
        counsel.set_good_odds()
        app.logger.info(
            f"good odds: {counsel.team1_good_odds} ; {counsel.team2_good_odds} ; {counsel.draw_good_odds}")
        counsel.write_to_db()


@ app.route("/counsels", methods=['POST'])
def post_counsels():
    """
    Calculate min odds and good odds for all matches present in RAW_DB
    """
    counseling()
    return Response(status=201)


@ app.route("/counsels", methods=['GET'])
def get_counsels():
    counsels = list(r.table(RDB_PREDICTOR_TABLE).between(r.epoch_time(
        start_time), r.epoch_time(start_time) + 86400 * 7, index='match_date').run(g.connection_predictor))
    app.logger.info(counsels)
    return jsonify(counsels)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the Predictor app')
    parser.add_argument('--setup', dest='run_setup', action='store_true')

    args = parser.parse_args()
    if args.run_setup:
        dbSetup()
    else:
        app.run(debug=True, port=5005)
