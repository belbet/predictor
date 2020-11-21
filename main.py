from logging.config import dictConfig
import argparse
import json
import os
import decimal
import time
import logging

from rethinkdb import RethinkDB
from rethinkdb.errors import RqlRuntimeError, RqlDriverError
from sympy.solvers import solve
from sympy import Symbol
from flask import Flask, g, jsonify, render_template, request, abort
from dotenv import load_dotenv
load_dotenv()

# Connections parameters
RDB_HOST = os.environ.get('RDB_HOST') or 'localhost'
RDB_DB = os.environ.get('RDB_DB') or 'test'
RDB_TABLE = os.environ.get('RDB_TABLE') or 'matches'
RDB_PORT = os.environ.get('RDB_PORT') or 28015
RDB_PASS = os.environ.get('RDB_PASS') or ''
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


def dbSetup():
    connection = r.connect(host=RDB_HOST, port=RDB_PORT,
                           db=RDB_DB, password=RDB_PASS)
    try:
        r.db_create(RDB_DB).run(connection)
        r.db(RDB_DB).table_create('predictor').run(connection)
        print('Database setup completed. Now run the app without --setup.')
    except RqlRuntimeError:
        print('App database already exists. Run the app without --setup.')
    finally:
        connection.close()


# Weight parameters
WEIGHT_H2H = float(os.environ.get('WEIGHT_H2H')) or 1.5
WEIGHT_HOME = float(os.environ.get('WEIGHT_HOME')) or 1.2
WEIGHT_EXT = float(os.environ.get('WEIGHT_EXT')) or 0.8

app = Flask(__name__)
app.config.from_object(__name__)


@app.before_request
def before_request():
    try:
        g.connection = r.connect(host=RDB_HOST, port=RDB_PORT,
                                 db=RDB_DB, password=RDB_PASS)
    except RqlDriverError:
        abort(503, "No database connection could be established.")


@app.teardown_request
def teardown_request(exception):
    try:
        g.connection.close()
    except AttributeError:
        pass


@app.route("/prediction", methods=['GET'])
def get_prediction():
    team1 = request.args.get('team1')
    team2 = request.args.get('team2')
    if team1 == None or team2 == None:
        return {}
    app.logger.info("Init %s vs %s", team1, team2)
    app.logger.info("Weights are H2H: %s, HOME: %s, EXT: %s", WEIGHT_H2H,
                    WEIGHT_HOME, WEIGHT_EXT)
    predictor = Predictor(team1, team2, w_h2h=WEIGHT_H2H,
                          w_home=WEIGHT_HOME, w_ext=WEIGHT_EXT)
    predictor.set_stats_team(team1)
    predictor.set_stats_team(team2)
    predictor.set_stats_h2h()
    predictor.set_odds()
    return json.dumps(predictor.result, indent=4)


# 2017-08-01 00:00:00 - Start of the 2017-2018 season
start_time = 1501545600

# Now
end_time = int(time.time())

print("Determining odds based on all matches played between",
      start_time, "and", end_time)


class Predictor():
    def __init__(self, team1_id, team2_id, w_h2h=1, w_home=1, w_ext=1):
        self.team1_id = team1_id
        self.team2_id = team2_id
        self.w_h2h = w_h2h
        self.w_home = w_home
        self.w_ext = w_ext
        self.w_tot = w_h2h + w_home + w_ext
        self.result = {}
        self.result["draw"] = {}
        # Init result struct
        for team_id in [team1_id, team2_id]:
            self.result[team_id] = {}
            for keyword in ["home", "ext", team1_id, team2_id]:
                if team_id == keyword:
                    continue
                self.result[team_id][keyword] = {}
                for stat in ["played", "win", "loss", "draw"]:
                    self.result[team_id][keyword][stat] = 0

    def _get_matches_home(self, team_id):
        return list(r.table(RDB_TABLE).between(r.epoch_time(start_time), r.epoch_time(end_time), index='Date').filter({
            "T1Id": team_id,
        }).run(g.connection))

    def _get_matches_ext(self, team_id):
        return list(r.table(RDB_TABLE).between(r.epoch_time(start_time), r.epoch_time(end_time), index='Date').filter({
            "T2Id": team_id,
        }).run(g.connection))

    def _get_matches_h2h(self):
        return list(r.table(RDB_TABLE).between(r.epoch_time(start_time), r.epoch_time(end_time), index='Date').filter({
            "T1Id": self.team1_id,
            "T2Id": self.team2_id,
        }).run(g.connection))

    # Set stats for team
    def set_stats_team(self, team_id):
        matches_home = self._get_matches_home(team_id)
        matches_ext = self._get_matches_ext(team_id)
        # Match home
        for m in matches_home:
            self.result[team_id]["home"]["played"] += 1
            if m["WinnerID"] == team_id:
                self.result[team_id]["home"]["win"] += 1
            elif m["WinnerID"] != "":
                self.result[team_id]["home"]["loss"] += 1
            elif m["WinnerID"] == "":
                self.result[team_id]["home"]["draw"] += 1

        # Match ext
        for m in matches_ext:
            self.result[team_id]["ext"]["played"] += 1
            if m["WinnerID"] == team_id:
                self.result[team_id]["ext"]["win"] += 1
            elif m["WinnerID"] != "":
                self.result[team_id]["ext"]["loss"] += 1
            elif m["WinnerID"] == "":
                self.result[team_id]["ext"]["draw"] += 1

    def set_stats_h2h(self):
        matches_h2h = self._get_matches_h2h()
        for m in matches_h2h:
            self.result[self.team1_id][self.team2_id]["played"] += 1
            self.result[self.team2_id][self.team1_id]["played"] += 1
            if m["WinnerID"] == self.team1_id:
                self.result[self.team1_id][self.team2_id]["win"] += 1
                self.result[self.team2_id][self.team1_id]["loss"] += 1
            elif m["WinnerID"] == self.team2_id:
                self.result[self.team2_id][self.team1_id]["win"] += 1
                self.result[self.team1_id][self.team2_id]["loss"] += 1
            elif m["WinnerID"] == "":
                self.result[self.team2_id][self.team1_id]["draw"] += 1
                self.result[self.team1_id][self.team2_id]["draw"] += 1

    def _adjust_winrate(self, team=""):
        """
        Adjust winrates with weights
        """
        if team == "home":
            self.result[self.team1_id]["adjusted_winrate"] = self.result[self.team1_id]["home"]["winrate"] * \
                self.w_home + self.result[self.team1_id]["ext"]["winrate"] * \
                self.w_ext + \
                self.result[self.team1_id][self.team2_id]["winrate"] * self.w_h2h
            self.result[self.team1_id]["adjusted_winrate"] /= self.w_tot
        elif team == "ext":
            self.result[self.team2_id]["adjusted_winrate"] = self.result[self.team2_id]["ext"]["winrate"] * \
                self.w_home + self.result[self.team2_id]["home"]["winrate"] * \
                self.w_ext + \
                self.result[self.team2_id][self.team1_id]["winrate"] * self.w_h2h
            self.result[self.team2_id]["adjusted_winrate"] /= self.w_tot

    def _adjust_drawrate(self):
        """
        Adjusted drawrate is the average of drawrate of both teams. Weights are taken into account
        """
        # Team 2
        avg_drawrate1 = self.result[self.team1_id]["home"]["drawrate"] * \
            self.w_home + self.result[self.team1_id]["ext"]["drawrate"] * \
            self.w_ext + \
            self.result[self.team1_id][self.team2_id]["drawrate"] * self.w_h2h
        avg_drawrate1 /= self.w_tot
        self.result[self.team1_id]["avg_drawrate"] = avg_drawrate1

        # Team 2
        avg_drawrate2 = self.result[self.team2_id]["ext"]["drawrate"] * \
            self.w_home + self.result[self.team2_id]["home"]["drawrate"] * \
            self.w_ext + \
            self.result[self.team2_id][self.team1_id]["drawrate"] * self.w_h2h
        avg_drawrate2 /= self.w_tot
        self.result[self.team2_id]["avg_drawrate"] = avg_drawrate2

        # Adjusted
        avg_drawrate = avg_drawrate1 + avg_drawrate2
        avg_drawrate /= 2
        self.result["draw"]["adjusted_drawrate"] = avg_drawrate

    def _set_winrate(self):
        for team, stats in self.result.items():
            for key, content in stats.items():
                if isinstance(content, dict):
                    try:
                        self.result[team][key]["winrate"] = self.result[team][key]["win"] / \
                            self.result[team][key]["played"]
                    except ZeroDivisionError:
                        self.result[team][key]["winrate"] = 1
                    try:
                        self.result[team][key]["drawrate"] = self.result[team][key]["draw"] / \
                            self.result[team][key]["played"]
                    except ZeroDivisionError:
                        self.result[team][key]["drawrate"] = 1

    def set_odds(self):
        x = Symbol('x')
        self._set_winrate()
        self._adjust_winrate("home")
        self._adjust_winrate("ext")
        self._adjust_drawrate()
        factor = solve(
            x*self.result[self.team1_id]["adjusted_winrate"] + x*self.result[self.team2_id]["adjusted_winrate"] + x*self.result["draw"]["adjusted_drawrate"] - 1, x)[0]
        factor = float(factor)

        self.result[self.team1_id]["balanced_winrate"] = self.result[self.team1_id]["adjusted_winrate"] * factor
        self.result[self.team2_id]["balanced_winrate"] = self.result[self.team2_id]["adjusted_winrate"] * factor
        self.result["draw"]["balanced_winrate"] = self.result["draw"]["adjusted_drawrate"] * factor

        # Minimum odds
        self.result[self.team1_id]["min_odds"] = 1 / \
            self.result[self.team1_id]["balanced_winrate"]
        self.result[self.team2_id]["min_odds"] = 1 / \
            self.result[self.team2_id]["balanced_winrate"]
        self.result["draw"]["min_odds"] = 1 / \
            self.result["draw"]["balanced_winrate"]

        # Decent odds
        self.result[self.team1_id]["ok_odds"] = self.result[self.team1_id]["min_odds"] * 1.2
        self.result[self.team2_id]["ok_odds"] = self.result[self.team2_id]["min_odds"] * 1.2
        self.result["draw"]["ok_odds"] = self.result["draw"]["min_odds"] * 1.2
        # Good odds
        self.result[self.team1_id]["good_odds"] = self.result[self.team1_id]["min_odds"] * 1.3
        self.result[self.team2_id]["good_odds"] = self.result[self.team2_id]["min_odds"] * 1.3
        self.result["draw"]["good_odds"] = self.result["draw"]["min_odds"] * 1.3
        # Very good odds
        self.result[self.team1_id]["great_odds"] = self.result[self.team1_id]["min_odds"] * 1.4
        self.result[self.team2_id]["great_odds"] = self.result[self.team2_id]["min_odds"] * 1.4
        self.result["draw"]["great_odds"] = self.result["draw"]["min_odds"] * 1.4
        # Improbable odds
        self.result[self.team1_id]["warn_odds"] = self.result[self.team1_id]["min_odds"] * 1.5
        self.result[self.team2_id]["warn_odds"] = self.result[self.team2_id]["min_odds"] * 1.5
        self.result["draw"]["warn_odds"] = self.result["draw"]["min_odds"] * 1.5


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the Predictor app')
    parser.add_argument('--setup', dest='run_setup', action='store_true')

    args = parser.parse_args()
    if args.run_setup:
        dbSetup()
    else:
        app.run(debug=True)
