"""Offline tests for fetch.py with NBA.com / ESPN shaped fixtures: python3 -m unittest nba_boxscores/test_fetch.py"""

import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
import fetch  # noqa: E402

# name, starter, minutes, fgm, fga, tpm, tpa, ftm, fta, orb, drb, ast, stl, blk, tov, pf
DEN = [
    ("Jamal Murray", 1, "PT36M45.00S", 2, 11, 0, 1, 2, 4, 2, 8, 3, 1, 0, 6, 2),
    ("Nikola Jokić", 1, "PT35M19.00S", 5, 19, 1, 7, 2, 4, 1, 6, 5, 1, 1, 2, 3),
    ("Christian Braun", 1, "PT32M34.00S", 3, 10, 1, 6, 0, 0, 3, 3, 1, 1, 0, 2, 3),
    ("Aaron Gordon", 1, "PT29M28.00S", 6, 9, 3, 4, 5, 6, 3, 3, 1, 2, 1, 2, 3),
    ("Cam Johnson", 1, "PT11M20.00S", 2, 3, 1, 1, 0, 0, 0, 2, 1, 0, 0, 0, 2),
    ("DeMar DeRozan", 0, "PT28M12.00S", 5, 9, 0, 1, 3, 6, 1, 1, 0, 0, 0, 5, 3),
    ("Julian Strawther", 0, "PT21M58.00S", 2, 4, 0, 2, 0, 0, 0, 2, 3, 1, 0, 0, 0),
    ("Trevon Brazile", 0, "PT18M27.00S", 1, 6, 0, 4, 2, 2, 3, 9, 0, 0, 0, 1, 2),
    ("Marvin Bagley III", 0, "PT10M58.00S", 1, 3, 0, 0, 0, 0, 2, 1, 1, 0, 0, 2, 2),
    ("Tyus Jones", 0, "PT9M32.00S", 1, 3, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1),
    ("Ryan Nembhard", 0, "PT1M43.00S", 2, 3, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0),
    ("DaRon Holmes", 0, "PT1M43.00S", 1, 2, 1, 2, 0, 0, 1, 0, 1, 0, 0, 0, 0),
    ("Bryce Hopkins", 0, "PT1M41.00S", 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0),
]
OKC = [
    ("Shai Gilgeous-Alexander", 1, "PT34M37.00S", 6, 19, 3, 11, 2, 2, 0, 2, 3, 0, 1, 0, 0),
    ("Jalen Williams", 1, "PT33M13.00S", 7, 15, 2, 6, 5, 6, 0, 5, 3, 0, 0, 1, 3),
    ("Chet Holmgren", 1, "PT27M51.00S", 5, 9, 0, 1, 2, 2, 9, 8, 2, 1, 4, 3, 4),
    ("Cason Wallace", 1, "PT23M59.00S", 3, 8, 3, 6, 0, 0, 0, 1, 1, 4, 0, 0, 4),
    ("Isaiah Hartenstein", 1, "PT22M46.00S", 3, 10, 0, 0, 0, 0, 3, 3, 2, 0, 1, 2, 2),
    ("Ajay Mitchell", 0, "PT23M00.00S", 5, 11, 0, 4, 2, 2, 0, 0, 0, 5, 1, 3, 2),
    ("Alex Caruso", 0, "PT19M36.00S", 3, 7, 1, 5, 0, 0, 1, 3, 5, 1, 1, 0, 2),
    ("Jared McCain", 0, "PT18M04.00S", 1, 6, 0, 3, 2, 2, 0, 0, 1, 0, 0, 2, 1),
    ("Jaylin Williams", 0, "PT15M07.00S", 1, 4, 1, 4, 0, 0, 0, 7, 3, 0, 0, 0, 2),
    ("Aday Mara", 0, "PT12M41.00S", 1, 3, 0, 0, 0, 0, 3, 0, 0, 1, 1, 1, 1),
    ("Kenrich Williams", 0, "PT5M37.00S", 1, 2, 1, 2, 0, 0, 0, 1, 1, 0, 0, 0, 1),
    ("Brooks Barnhizer", 0, "PT1M43.00S", 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0),
    ("Bennett Stirtz", 0, "PT1M46.00S", 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0),
]


def nba_player(row, order):
    name, starter, mins, fgm, fga, tpm, tpa, ftm, fta, orb, drb, ast, stl, blk, tov, pf = row
    first, _, family = name.partition(" ")
    return {"status": "ACTIVE", "order": order, "personId": 1000 + order, "starter": str(starter),
            "oncourt": "0", "played": "1", "name": name, "firstName": first, "familyName": family,
            "statistics": {"minutes": mins, "fieldGoalsMade": fgm, "fieldGoalsAttempted": fga,
                           "threePointersMade": tpm, "threePointersAttempted": tpa,
                           "freeThrowsMade": ftm, "freeThrowsAttempted": fta,
                           "reboundsOffensive": orb, "reboundsDefensive": drb, "reboundsTotal": orb + drb,
                           "assists": ast, "steals": stl, "blocks": blk, "turnovers": tov,
                           "foulsPersonal": pf, "points": 2 * fgm + tpm + ftm}}


def nba_team(tricode, city, name, rows, extra):
    players = [nba_player(r, i + 1) for i, r in enumerate(rows)] + extra
    s = lambda f: sum(p["statistics"].get(f, 0) for p in players if p["played"] == "1")  # noqa: E731
    stats = {f: s(f) for f in ("fieldGoalsMade", "fieldGoalsAttempted", "threePointersMade",
                               "threePointersAttempted", "freeThrowsMade", "freeThrowsAttempted",
                               "assists", "steals", "blocks", "foulsPersonal", "points", "turnovers")}
    orb, drb = s("reboundsOffensive"), s("reboundsDefensive")
    stats.update({"minutes": "PT240M00.00S", "reboundsOffensive": orb, "reboundsDefensive": drb,
                  "reboundsPersonal": orb + drb, "reboundsTeam": 7, "reboundsTotal": orb + drb + 7,
                  "turnoversTeam": 1, "turnoversTotal": stats["turnovers"] + 1})
    return {"teamTricode": tricode, "teamCity": city, "teamName": name, "score": stats["points"],
            "players": players, "statistics": stats}


def dnp(name, reason, status="INACTIVE"):
    return {"status": status, "starter": "0", "played": "0", "name": name, "notPlayingReason": reason,
            "statistics": {"minutes": "PT00M00.00S", "points": 0}}


NBA_BOX = {"game": {
    "gameId": "0022600011", "gameStatus": 3, "gameStatusText": "Final", "period": 4,
    "awayTeam": nba_team("DEN", "Denver", "Nuggets", DEN, [dnp("Zeke Nnaji", "DNP_COACH", "ACTIVE")]),
    "homeTeam": nba_team("OKC", "Oklahoma City", "Thunder", OKC, [
        dnp("Nikola Topic", "INACTIVE_INJURY"), dnp("Two Way Guy", "INACTIVE_GLEAGUE_TWOWAY")]),
}}

SCHEDULE = {"leagueSchedule": {"gameDates": [
    {"gameDate": "10/22/2026 00:00:00", "games": [
        {"gameId": "0022600011", "gameCode": "20261022/DENOKC", "gameStatus": 3, "gameStatusText": "Final",
         "awayTeam": {"teamTricode": "DEN", "score": 84}, "homeTeam": {"teamTricode": "OKC", "score": 96}},
        {"gameId": "0022600010", "gameCode": "20261022/CLEPHI", "gameStatus": 3, "gameStatusText": "Final",
         "awayTeam": {"teamTricode": "CLE", "score": 106}, "homeTeam": {"teamTricode": "PHI", "score": 114}},
    ]},
    {"gameDate": "10/23/2026 00:00:00", "games": [
        {"gameId": "0022600020", "gameCode": "20261023/ATLCHA", "gameStatus": 2, "gameStatusText": "Q3 5:12",
         "awayTeam": {"teamTricode": "ATL", "score": 70}, "homeTeam": {"teamTricode": "CHA", "score": 66}},
        {"gameId": "0022600021", "gameCode": "20261023/LBNBKN", "gameStatus": 1, "gameStatusText": "7:30 pm ET",
         "awayTeam": {"teamTricode": "LBN", "score": 0}, "homeTeam": {"teamTricode": "BKN", "score": 0}},
    ]},
]}}


def espn_summary():
    keys = ["minutes", "points", "fieldGoalsMade-fieldGoalsAttempted",
            "threePointFieldGoalsMade-threePointFieldGoalsAttempted", "freeThrowsMade-freeThrowsAttempted",
            "rebounds", "assists", "turnovers", "steals", "blocks", "offensiveRebounds",
            "defensiveRebounds", "fouls", "plusMinus"]

    def team(abbr, rows, extra_dnp):
        athletes = []
        for name, starter, mins, fgm, fga, tpm, tpa, ftm, fta, orb, drb, ast, stl, blk, tov, pf in rows:
            m = round(fetch.iso_secs(mins) / 60)  # ESPN gives rounded whole minutes
            vals = [m, 2 * fgm + tpm + ftm, f"{fgm}-{fga}", f"{tpm}-{tpa}", f"{ftm}-{fta}", orb + drb, ast, tov,
                    stl, blk, orb, drb, pf, "+0"]
            athletes.append({"athlete": {"displayName": fetch.fold(name).title()}, "starter": bool(starter),
                             "didNotPlay": False, "stats": [str(v) for v in vals]})
        athletes += [{"athlete": {"displayName": n}, "starter": False, "didNotPlay": True, "reason": r, "stats": []}
                     for n, r in extra_dnp]
        col = lambda i: sum(r[i] for r in rows)  # noqa: E731
        orb, drb = col(9), col(10)
        # ESPN team totals count team rebounds and team turnovers
        totals = ["", str(sum(2 * r[3] + r[5] + r[7] for r in rows)), f"{col(3)}-{col(4)}", f"{col(5)}-{col(6)}",
                  f"{col(7)}-{col(8)}", str(orb + drb + 5), str(col(11)), str(col(14) + 1), str(col(12)),
                  str(col(13)), str(orb), str(drb), str(col(15)), ""]
        return {"team": {"abbreviation": abbr}, "statistics": [{"keys": keys, "athletes": athletes, "totals": totals}]}

    den, okc = team("DEN", DEN, [("Zeke Nnaji", "COACH'S DECISION")]), team("OKC", OKC, [])
    return {"header": {"competitions": [{
                "status": {"period": 4, "type": {"completed": True, "state": "post"}},
                "competitors": [{"homeAway": "away", "team": {"abbreviation": "DEN"}, "score": "84"},
                                {"homeAway": "home", "team": {"abbreviation": "OKC"}, "score": "96"}]}]},
            "boxscore": {"players": [den, okc]}}


ESPN_SCOREBOARD = {"events": [{"id": "401810011", "competitions": [{
    "status": {"type": {"completed": True, "state": "post", "shortDetail": "Final"}},
    "competitors": [{"homeAway": "away", "team": {"abbreviation": "DEN"}, "score": "84"},
                    {"homeAway": "home", "team": {"abbreviation": "OKC"}, "score": "96"}]}]}]}


def parse_tsv(text):
    """Read a box file back the way the pipeline does: TSV rows between the fences."""
    lines = text.split("```")[1].strip("\n").split("\n")
    header = lines[0].split("\t")
    return header, [dict(zip(header, ln.split("\t"))) for ln in lines[1:]]


class FakeHTTP:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, url, headers=None, tries=3):
        self.calls.append(url)
        for prefix, result in self.routes.items():
            if url.startswith(prefix):
                if isinstance(result, Exception):
                    raise result
                return json.loads(json.dumps(result))
        raise fetch.NotPublished(f"HTTP 403: {url}")


def routes(**over):
    r = {fetch.NBA_SCHEDULE_URLS[0]: SCHEDULE,
         fetch.NBA_BOX_URL.format("0022600011"): NBA_BOX,
         fetch.ESPN_SCOREBOARD_URL.format("20261022"): ESPN_SCOREBOARD,
         fetch.ESPN_SUMMARY_URL.format("401810011"): espn_summary()}
    r.update(over)
    return r


class FetchTest(unittest.TestCase):
    def setUp(self):
        fetch._SCHEDULE.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_day(self, day, http, source="auto"):
        with mock.patch.object(fetch, "get_json", http):
            games, err = fetch.collect(day, source)
        self.assertIsNone(err)
        return games

    def test_nba_final_game_files(self):
        http = FakeHTTP(routes())
        games = self.run_day("2026-10-22", http)
        self.assertEqual([g["boxid"] for g in games], ["202610220OKC", "202610220PHI"])
        okc = games[0]
        self.assertEqual(okc["source"], "nba")
        self.assertEqual(okc["problems"], [])
        changed, line = fetch.write_day(self.tmp.name, "2026-10-22", games)
        self.assertTrue(changed)
        self.assertEqual(line, "2026-10-22: 1/2 final (nba)")
        folder = os.path.join(self.tmp.name, "2026-10-22")
        with open(os.path.join(folder, "games.txt")) as f:
            self.assertEqual(f.read().splitlines(), [
                "Denver Nuggets|84|Oklahoma City Thunder|96|https://www.basketball-reference.com/boxscores/202610220OKC.html|final",
                # final on the schedule, box score not published: final scores, no box file
                "Cleveland Cavaliers|106|Philadelphia 76ers|114|https://www.basketball-reference.com/boxscores/202610220PHI.html|final",
            ])
        self.assertFalse(os.path.exists(os.path.join(folder, "202610220PHI.txt")))
        with open(os.path.join(folder, "202610220OKC.txt")) as f:
            text = f.read()
        self.assertTrue(text.startswith("Final: Denver Nuggets 84, Oklahoma City Thunder 96\n\n```\n"))
        header, rows = parse_tsv(text)
        self.assertEqual("\t".join(header), fetch.TSV_HEADER)
        den = [r for r in rows if r["team"] == "Denver Nuggets"]
        # starters by minutes, then reserves by minutes, then DNPs, then totals
        self.assertEqual([r["player"] for r in den[:5]],
                         ["Jamal Murray", "Nikola Jokić", "Christian Braun", "Aaron Gordon", "Cameron Johnson"])
        self.assertEqual(den[5]["player"], "DeMar DeRozan")
        self.assertEqual(den[6], {"team": "Denver Nuggets", "section": "Reserves", "player": "Julian Strawther",
                                  "MP": "21:58", "FG": "2", "FGA": "4", "3P": "0", "3PA": "2", "FT": "0", "FTA": "0",
                                  "ORB": "0", "DRB": "2", "TRB": "2", "AST": "3", "STL": "1", "BLK": "0",
                                  "TOV": "0", "PF": "0", "PTS": "4"})
        self.assertEqual((den[-2]["player"], den[-2]["MP"], len(den[-2])), ("Zeke Nnaji", "Did Not Play", 4))
        self.assertEqual(den[-1]["section"], "Totals")
        self.assertEqual((den[-1]["MP"], den[-1]["PTS"], den[-1]["TRB"], den[-1]["TOV"]), ("240", "84", "53", "21"))
        okc_rows = [r for r in rows if r["team"] == "Oklahoma City Thunder"]
        names = [r["player"] for r in okc_rows]
        self.assertIn("Nikola Topić", names)  # injured: listed as Did Not Dress, accents restored
        self.assertNotIn("Two Way Guy", names)  # G League two-way: left out like Basketball-Reference does
        # every column's player sum equals the Team Totals row (what build_day.py --check verifies)
        for team_rows in (den, okc_rows):
            played = [r for r in team_rows if r["section"] != "Totals" and ":" in r["MP"]]
            total = team_rows[-1]
            for col in ("FG", "FGA", "3P", "3PA", "FT", "FTA", "ORB", "DRB", "TRB", "AST", "STL", "BLK", "PF", "PTS"):
                self.assertEqual(sum(int(r[col]) for r in played), int(total[col]), col)
            secs = sum(int(r["MP"].split(":")[0]) * 60 + int(r["MP"].split(":")[1]) for r in played)
            self.assertAlmostEqual(secs / 60, 240, delta=1.5)
        with open(os.path.join(folder, "source.json")) as f:
            meta = json.load(f)
        self.assertEqual((meta["games"], meta["final"], meta["pending"], meta["problems"]), (2, 1, 1, 0))
        self.assertEqual(meta["list"][0]["url"], "https://www.nba.com/game/den-vs-okc-0022600011/box-score")
        self.assertEqual(meta["list"][1]["status"], "final, box score not published")
        # same data again: nothing rewritten, source.json keeps its timestamp
        changed, _ = fetch.write_day(self.tmp.name, "2026-10-22", games)
        self.assertFalse(changed)

    def test_unfinished_and_unknown_teams(self):
        games = self.run_day("2026-10-23", FakeHTTP(routes()))
        self.assertEqual(len(games), 1)  # the exhibition opponent "LBN" is skipped
        self.assertEqual(fetch.game_line("2026-10-23", games[0]), "Atlanta Hawks||Charlotte Hornets|||not final")
        fetch.write_day(self.tmp.name, "2026-10-23", games)
        with open(os.path.join(self.tmp.name, "2026-10-23", "source.json")) as f:
            self.assertEqual(json.load(f)["list"][0]["status"], "in progress")

    def test_no_games(self):
        games = self.run_day("2026-10-19", FakeHTTP(routes(**{fetch.ESPN_SCOREBOARD_URL.format("20261019"): {"events": []}})))
        self.assertEqual(games, [])
        changed, line = fetch.write_day(self.tmp.name, "2026-10-19", games)
        self.assertEqual(line, "2026-10-19: no games")
        with open(os.path.join(self.tmp.name, "2026-10-19", "games.txt")) as f:
            self.assertEqual(f.read(), "NO_GAMES\n")

    def test_espn_fallback_when_nba_box_breaks(self):
        http = FakeHTTP(routes(**{fetch.NBA_BOX_URL.format("0022600011"): RuntimeError("timeout")}))
        games = self.run_day("2026-10-22", http)
        okc = games[0]
        self.assertEqual(okc["source"], "espn")
        self.assertEqual(okc["espn_event_id"], "401810011")
        self.assertEqual(okc["problems"], [])
        text = fetch.box_text(okc["box"])
        _, rows = parse_tsv(text)
        jokic = next(r for r in rows if r["player"].startswith("Nikola Jok"))
        self.assertEqual((jokic["player"], jokic["MP"], jokic["FG"], jokic["FGA"]), ("Nikola Jokić", "35:00", "5", "19"))
        nnaji = next(r for r in rows if r["player"] == "Zeke Nnaji")
        self.assertEqual(nnaji["MP"], "Did Not Play")
        den_total = next(r for r in rows if r["team"] == "Denver Nuggets" and r["section"] == "Totals")
        self.assertEqual((den_total["TRB"], den_total["TOV"], den_total["PTS"]), ("53", "21", "84"))

    def test_espn_only_when_nba_schedule_down(self):
        http = FakeHTTP(routes(**{u: RuntimeError("down") for u in fetch.NBA_SCHEDULE_URLS}))
        games = self.run_day("2026-10-22", http)
        self.assertEqual([(g["boxid"], g["source"]) for g in games], [("202610220OKC", "espn")])

    def test_nothing_answers(self):
        http = FakeHTTP({u: RuntimeError("down") for u in fetch.NBA_SCHEDULE_URLS + (fetch.ESPN_SCOREBOARD_URL[:60],)})
        with mock.patch.object(fetch, "get_json", http):
            games, err = fetch.collect("2026-10-22", "auto")
        self.assertIsNone(games)
        self.assertIn("NBA schedule unavailable", err)

    def test_check_flags_missing_player(self):
        box = json.loads(json.dumps(NBA_BOX))
        box["game"]["awayTeam"]["players"] = [p for p in box["game"]["awayTeam"]["players"]
                                              if p["name"] != "Julian Strawther"]
        http = FakeHTTP(routes(**{fetch.NBA_BOX_URL.format("0022600011"): box}))
        problems = self.run_day("2026-10-22", http)[0]["problems"]
        self.assertIn("DEN pts: players 80 != team 84", problems)
        self.assertIn("DEN minutes: players 217.7 != team 240", problems)

    def test_helpers(self):
        self.assertEqual(fetch.iso_secs("PT36M45.00S"), 2205)
        self.assertEqual(fetch.iso_secs("PT00M04.50S"), 4)
        self.assertEqual(fetch.mp_text(2205), "36:45")
        self.assertEqual(fetch.mp_text(64), "1:04")
        self.assertEqual(fetch.bref_name("Alperen Sengun"), "Alperen Şengün")
        self.assertEqual(fetch.bref_name("Alex Sarr"), "Alexandre Sarr")
        self.assertEqual(fetch.bref_name("Nikola Djurisic"), "Nikola Đurišić")
        self.assertEqual(fetch.bref_name("Shai Gilgeous-Alexander"), "Shai Gilgeous-Alexander")
        self.assertEqual(fetch.boxid("2026-10-23", "PHX"), "202610230PHO")
        self.assertEqual(fetch.boxid("2026-10-23", "UTAH"), "202610230UTA")
        for reason, label in (("DNP_COACH", "Did Not Play"), ("INACTIVE_INJURY", "Did Not Dress"),
                              ("DND_INJURY", "Did Not Dress"), ("NWT_PERSONAL", "Not With Team"),
                              ("INACTIVE_SUSPENSION", "Player Suspended"), ("INACTIVE_GLEAGUE_TWOWAY", None),
                              (None, "Did Not Play")):
            self.assertEqual(fetch.nba_dnp(reason), label, reason)
        utc = dt.timezone.utc
        # 08:45 Istanbul = 05:45 UTC: last night is the previous US date
        self.assertEqual(fetch.default_dates(dt.datetime(2026, 10, 24, 5, 45, tzinfo=utc)), ["2026-10-23", "2026-10-22"])
        self.assertEqual(fetch.default_dates(dt.datetime(2026, 10, 24, 1, 7, tzinfo=utc)), ["2026-10-23", "2026-10-22"])
        self.assertEqual(fetch.default_dates(dt.datetime(2026, 12, 1, 9, 47, tzinfo=utc)), ["2026-11-30", "2026-11-29"])


if __name__ == "__main__":
    unittest.main()
