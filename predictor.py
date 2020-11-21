from settings import *
from sympy.solvers import solve
from sympy import Symbol
from flask import g


class Predictor():
    def __init__(self, match_id, team1_id, team2_id, w_h2h=1, w_home=1, w_ext=1):
        self.match_id = match_id
        self.team1_id = team1_id
        self.team2_id = team2_id
        self.w_h2h = w_h2h
        self.w_home = w_home
        self.w_ext = w_ext
        self.w_tot = w_h2h + w_home + w_ext
        self.result = {}
        self.result["matchId"] = self.match_id
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
        return list(r.table(RDB_RAW_TABLE).between(r.epoch_time(start_time), r.epoch_time(end_time), index='Date').filter({
            "T1Id": team_id,
        }).run(g.connection_raw))

    def _get_matches_ext(self, team_id):
        return list(r.table(RDB_RAW_TABLE).between(r.epoch_time(start_time), r.epoch_time(end_time), index='Date').filter({
            "T2Id": team_id,
        }).run(g.connection_raw))

    def _get_matches_h2h(self):
        return list(r.table(RDB_RAW_TABLE).between(r.epoch_time(start_time), r.epoch_time(end_time), index='Date').filter({
            "T1Id": self.team1_id,
            "T2Id": self.team2_id,
        }).run(g.connection_raw))

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

    def set_odds(self):
        x = Symbol('x')
        self._set_winrate()
        self._adjust_winrate("home")
        self._adjust_winrate("ext")
        self._adjust_drawrate()
        factor = solve(
            x*self.result[self.team1_id]["adjusted_winrate"] + x*self.result[self.team2_id]["adjusted_winrate"] + x*self.result["draw"]["adjusted_drawrate"] - 1, x)[0]
        factor = float(factor)

        for outcome in [self.team1_id, self.team2_id, "draw"]:
            if outcome == "draw":
                self.result[outcome]["balanced_drawrate"] = self.result[outcome]["adjusted_drawrate"] * factor
                self.result[outcome]["min_odds"] = 1 / \
                    self.result[outcome]["balanced_drawrate"]
            else:
                self.result[outcome]["balanced_winrate"] = self.result[outcome]["adjusted_winrate"] * factor
                self.result[outcome]["min_odds"] = 1 / \
                    self.result[outcome]["balanced_winrate"]
            self.result[outcome]["ok_odds"] = self.result[outcome]["min_odds"] * 1.2
            self.result[outcome]["good_odds"] = self.result[outcome]["min_odds"] * 1.3
            self.result[outcome]["great_odds"] = self.result[outcome]["min_odds"] * 1.4
            self.result[outcome]["warn_odds"] = self.result[outcome]["min_odds"] * 1.5

    def write_prediction_to_db(self):
        r.table(RDB_PREDICTOR_TABLE).insert(
            self.result).run(g.connection_predictor)

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
            if isinstance(stats, dict):
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

    @staticmethod
    def get_match_prediction(match_id):
        result = r.table(RDB_PREDICTOR_TABLE).get(
            match_id).run(g.connection_predictor)
        return result
