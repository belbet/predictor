import argparse
import json
import os
import decimal

from rethinkdb import RethinkDB
from rethinkdb.errors import RqlRuntimeError, RqlDriverError
from sympy.solvers import solve
from sympy import Symbol

from dotenv import load_dotenv
load_dotenv()

RDB_HOST = os.environ.get('RDB_HOST') or 'localhost'
RDB_DB = os.environ.get('RDB_DB') or 'test'
RDB_PORT = os.environ.get('RDB_PORT') or 28015
RDB_PASS = os.environ.get('RDB_PASS') or ''
WEIGHT_H2H = float(os.environ.get('WEIGHT_H2H')) or 1.5
WEIGHT_HOME = float(os.environ.get('WEIGHT_HOME')) or 1.2
WEIGHT_EXT = float(os.environ.get('WEIGHT_EXT')) or 0.8
r = RethinkDB()

connection = r.connect(host=RDB_HOST, port=RDB_PORT,
                       db="test", password=RDB_PASS)
team1 = "dijon"
team2 = "lens"

# 2017-08-01 00:00:00
start_time = 1501545600

# Today 19 Nov 2020 16:16
end_time = 1605798958

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
        self.result[team1_id] = {}
        self.result[team1_id]["home"] = {}
        self.result[team1_id]["ext"] = {}
        self.result[team2_id] = {}
        self.result[team2_id]["home"] = {}
        self.result[team2_id]["ext"] = {}
        self.result["draw"] = {}
        # Overall
        # Team 1 Home
        self.result[team1_id]["home"]["played"] = 0
        self.result[team1_id]["home"]["win"] = 0
        self.result[team1_id]["home"]["loss"] = 0
        self.result[team1_id]["home"]["draw"] = 0
        # Team 1 Ext
        self.result[team1_id]["ext"]["played"] = 0
        self.result[team1_id]["ext"]["win"] = 0
        self.result[team1_id]["ext"]["loss"] = 0
        self.result[team1_id]["ext"]["draw"] = 0
        # Team 2 Home
        self.result[team2_id]["home"]["played"] = 0
        self.result[team2_id]["home"]["win"] = 0
        self.result[team2_id]["home"]["loss"] = 0
        self.result[team2_id]["home"]["draw"] = 0
        # Team 2 Ext
        self.result[team2_id]["ext"]["played"] = 0
        self.result[team2_id]["ext"]["win"] = 0
        self.result[team2_id]["ext"]["loss"] = 0
        self.result[team2_id]["ext"]["draw"] = 0
        # H2H
        # Team 1
        self.result[team1_id][team2_id] = {}
        self.result[team1_id][team2_id]["played"] = 0
        self.result[team1_id][team2_id]["win"] = 0
        self.result[team1_id][team2_id]["loss"] = 0
        self.result[team1_id][team2_id]["draw"] = 0
        # Team 2
        self.result[team2_id][team1_id] = {}
        self.result[team2_id][team1_id]["played"] = 0
        self.result[team2_id][team1_id]["win"] = 0
        self.result[team2_id][team1_id]["loss"] = 0
        self.result[team2_id][team1_id]["draw"] = 0
        print("Init teams", self.team1_id, "and", self.team2_id)
        print(self.team1_id, "is home")
        print(self.team2_id, "is ext")

    def _get_matches_home(self, team_id):
        return list(r.table("matches").between(r.epoch_time(start_time), r.epoch_time(end_time), index='Date').filter({
            "T1Id": team_id,
        }).run(connection))

    def _get_matches_ext(self, team_id):
        return list(r.table("matches").between(r.epoch_time(start_time), r.epoch_time(end_time), index='Date').filter({
            "T2Id": team_id,
        }).run(connection))

    def _get_matches_h2h(self):
        return list(r.table("matches").between(r.epoch_time(start_time), r.epoch_time(end_time), index='Date').filter({
            "T1Id": self.team1_id,
            "T2Id": self.team2_id,
        }).run(connection))

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
        # self.result[team_id]["home"]["winrate"] = self.result[team_id]["home"]["win"] / \
        #     self.result[team_id]["played"]
        # self.result[team_id]["home"]["drawrate"] = self.result[team_id]["home"]["draw"] / \
        #     self.result[team_id]["home"]["played"]

        # Match ext
        for m in matches_ext:
            self.result[team_id]["ext"]["played"] += 1
            if m["WinnerID"] == team_id:
                self.result[team_id]["ext"]["win"] += 1
            elif m["WinnerID"] != "":
                self.result[team_id]["ext"]["loss"] += 1
            elif m["WinnerID"] == "":
                self.result[team_id]["ext"]["draw"] += 1
        # self.result[team_id]["ext"]["winrate"] = self.result[team_id]["ext"]["win"] / \
        #     self.result[team_id]["ext"]["played"]
        # self.result[team_id]["ext"]["drawrate"] = self.result[team_id]["ext"]["draw"] / \
        #     self.result[team_id]["ext"]["played"]
        print(team_id, ":", "home")
        print("played:", self.result[team_id]["home"]["played"])
        print("win:", self.result[team_id]["home"]["win"])
        print("draw:", self.result[team_id]["home"]["draw"])
        print("loss:", self.result[team_id]["home"]["loss"])
        print(team_id, ":", "ext")
        print("played:", self.result[team_id]["ext"]["played"])
        print("win:", self.result[team_id]["ext"]["win"])
        print("draw:", self.result[team_id]["ext"]["draw"])
        print("loss:", self.result[team_id]["ext"]["loss"])

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

    def _set_winrate(self):
        # TEAM 1
        # Home
        self.result[self.team1_id]["home"]["winrate"] = self.result[self.team1_id]["home"]["win"] / \
            self.result[self.team1_id]["home"]["played"]
        self.result[self.team1_id]["home"]["drawrate"] = self.result[self.team1_id]["home"]["draw"] / \
            self.result[self.team1_id]["home"]["played"]
        # Ext
        self.result[self.team1_id]["ext"]["winrate"] = self.result[self.team1_id]["ext"]["win"] / \
            self.result[self.team1_id]["ext"]["played"]
        self.result[self.team1_id]["ext"]["drawrate"] = self.result[self.team1_id]["ext"]["draw"] / \
            self.result[self.team1_id]["ext"]["played"]
        # H2H
        self.result[self.team1_id][self.team2_id]["winrate"] = self.result[self.team1_id][self.team2_id]["win"] / \
            self.result[self.team1_id][self.team2_id]["played"]
        self.result[self.team1_id][self.team2_id]["drawrate"] = self.result[self.team1_id][self.team2_id]["draw"] / \
            self.result[self.team1_id][self.team2_id]["played"]

        # TEAM 2
        # Home
        self.result[self.team2_id]["home"]["winrate"] = self.result[self.team2_id]["home"]["win"] / \
            self.result[self.team2_id]["home"]["played"]
        self.result[self.team2_id]["home"]["drawrate"] = self.result[self.team2_id]["home"]["draw"] / \
            self.result[self.team2_id]["home"]["played"]
        # Ext
        self.result[self.team2_id]["ext"]["winrate"] = self.result[self.team2_id]["ext"]["win"] / \
            self.result[self.team2_id]["ext"]["played"]
        self.result[self.team2_id]["ext"]["drawrate"] = self.result[self.team2_id]["ext"]["draw"] / \
            self.result[self.team2_id]["ext"]["played"]

        # H2H
        self.result[self.team2_id][self.team1_id]["winrate"] = self.result[self.team2_id][self.team1_id]["win"] / \
            self.result[self.team2_id][self.team1_id]["played"]
        self.result[self.team2_id][self.team1_id]["drawrate"] = self.result[self.team2_id][self.team1_id]["draw"] / \
            self.result[self.team2_id][self.team1_id]["played"]

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

    def _set_winrate2(self):
        for team, stats in self.result.items():
            for key, content in stats.items():
                if isinstance(content, dict):
                    # Example
                    # self.result[self.team1_id]["home"]["winrate"] = self.result[self.team1_id]["home"]["win"] / \
                    #     self.result[self.team1_id]["home"]["played"]
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
        # self._set_winrate()
        self._set_winrate2()
        self._adjust_winrate("home")
        self._adjust_winrate("ext")
        self._adjust_drawrate()
        factor = solve(
            x*self.result[self.team1_id]["adjusted_winrate"] + x*self.result[self.team2_id]["adjusted_winrate"] + x*self.result["draw"]["adjusted_drawrate"] - 1, x)[0]
        factor = float(factor)

        self.result[self.team1_id]["adjusted_winrate"] = self.result[self.team1_id]["adjusted_winrate"] * factor
        self.result[self.team2_id]["adjusted_winrate"] = self.result[self.team2_id]["adjusted_winrate"] * factor
        self.result["draw"]["adjusted_drawrate"] = self.result["draw"]["adjusted_drawrate"] * factor

        # Minimum odds
        self.result[self.team1_id]["min_odds"] = 1 / \
            self.result[self.team1_id]["adjusted_winrate"]
        self.result[self.team2_id]["min_odds"] = 1 / \
            self.result[self.team2_id]["adjusted_winrate"]
        self.result["draw"]["min_odds"] = 1 / \
            self.result["draw"]["adjusted_drawrate"]

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


predictor = Predictor(team1, team2, w_h2h=WEIGHT_H2H,
                      w_home=WEIGHT_HOME, w_ext=WEIGHT_EXT)
predictor.set_stats_team(team1)
predictor.set_stats_team(team2)
predictor.set_stats_h2h()
predictor.set_odds()

output = json.dumps(predictor.result, indent=4)
print(output)
