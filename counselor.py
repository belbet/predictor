from settings import *
from sympy.solvers import solve
from sympy import Symbol
from flask import g


class Counselor():
    def __init__(self, match: dict):
        self.match_id = match["MatchID"],
        self.match_date = match["Date"]
        self.team1_id = match["T1Id"]
        self.team2_id = match["T2Id"]
        self.team1_name = match["T1Name"]
        self.team2_name = match["T2Name"]
        self.team1_proba = match["T1Proba"]
        self.team2_proba = match["T2Proba"]
        self.draw_proba = match["DrawProba"]

    def set_min_odds(self):
        self.team1_min_odds = 100 / self.team1_proba
        self.team2_min_odds = 100 / self.team2_proba
        self.draw_min_odds = 100 / self.draw_proba

    def set_good_odds(self):
        self.team1_good_odds = 120 / self.team1_proba
        self.team2_good_odds = 120 / self.team2_proba
        self.draw_good_odds = 120 / self.draw_proba

    def write_to_db(self):
        result = {"match_id": self.match_id,
                  "match_date": self.match_date,
                  "team1_id": self.team1_id,
                  "team2_id": self.team2_id,
                  "team1_name": self.team1_name,
                  "team2_name": self.team2_name,
                  "team1_proba": self.team1_proba,
                  "team2_proba": self.team2_proba,
                  "draw_proba": self.draw_proba,
                  "team1_min_odds": self.team1_min_odds,
                  "team2_min_odds": self.team2_min_odds,
                  "draw_min_odds": self.draw_min_odds,
                  "team1_good_odds": self.team1_good_odds,
                  "team2_good_odds": self.team2_good_odds,
                  "draw_good_odds": self.draw_good_odds
                  }
        r.table(RDB_PREDICTOR_TABLE).insert(result).run(g.connection_predictor)
