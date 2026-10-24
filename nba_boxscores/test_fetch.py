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

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 24, 5, 27, tzinfo=UTC)

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
    ("DaRon Holmes II", 0, "PT1M43.00S", 1, 2, 1, 2, 0, 0, 1, 0, 1, 0, 0, 0, 0),
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
# a smaller CLE@PHI game, served in the box score page's historical format
CLE = [
    ("Donovan Mitchell", 1, "PT48M00.00S", 11, 19, 2, 4, 8, 11, 0, 10, 3, 2, 1, 5, 3),
    ("Evan Mobley", 1, "PT48M00.00S", 7, 13, 1, 4, 3, 3, 1, 7, 2, 0, 0, 1, 4),
    ("James Harden", 1, "PT48M00.00S", 5, 12, 3, 6, 3, 4, 0, 3, 5, 1, 0, 6, 2),
    ("Peyton Watson", 1, "PT48M00.00S", 2, 7, 0, 3, 4, 4, 0, 1, 2, 2, 1, 5, 2),
    ("Jarrett Allen", 1, "PT48M00.00S", 6, 10, 0, 0, 2, 4, 3, 4, 0, 0, 2, 1, 1),
]
PHI = [
    ("Tyrese Maxey", 1, "PT48M00.00S", 12, 23, 2, 7, 6, 8, 1, 2, 6, 2, 0, 2, 4),
    ("Jaylen Brown", 1, "PT48M00.00S", 10, 20, 1, 3, 0, 0, 1, 7, 4, 1, 0, 4, 4),
    ("Joel Embiid", 1, "PT48M00.00S", 8, 16, 1, 4, 7, 9, 0, 7, 1, 0, 0, 1, 3),
    ("LeBron James", 1, "PT48M00.00S", 5, 14, 1, 4, 6, 7, 1, 9, 5, 3, 1, 5, 3),
    ("VJ Edgecombe", 1, "PT48M00.00S", 4, 11, 1, 4, 2, 3, 3, 4, 6, 3, 0, 1, 2),
]


def pts(r):
    return 2 * r[3] + r[5] + r[7]


def live_player(row, order):
    name, starter, mins, fgm, fga, tpm, tpa, ftm, fta, orb, drb, ast, stl, blk, tov, pf = row
    first, _, family = name.partition(" ")
    return {"status": "ACTIVE", "order": order, "personId": 1000 + order, "starter": str(starter),
            "oncourt": "0", "played": "1", "name": name, "firstName": first, "familyName": family,
            "statistics": {"minutes": mins, "fieldGoalsMade": fgm, "fieldGoalsAttempted": fga,
                           "threePointersMade": tpm, "threePointersAttempted": tpa,
                           "freeThrowsMade": ftm, "freeThrowsAttempted": fta,
                           "reboundsOffensive": orb, "reboundsDefensive": drb, "reboundsTotal": orb + drb,
                           "assists": ast, "steals": stl, "blocks": blk, "turnovers": tov,
                           "foulsPersonal": pf, "points": pts(row)}}


def team_stats(rows, minutes):
    col = lambda i: sum(r[i] for r in rows)  # noqa: E731
    return {"fieldGoalsMade": col(3), "fieldGoalsAttempted": col(4), "threePointersMade": col(5),
            "threePointersAttempted": col(6), "freeThrowsMade": col(7), "freeThrowsAttempted": col(8),
            "reboundsOffensive": col(9), "reboundsDefensive": col(10), "assists": col(11), "steals": col(12),
            "blocks": col(13), "turnovers": col(14), "foulsPersonal": col(15),
            "points": sum(pts(r) for r in rows), "minutes": minutes}


def live_team(tricode, rows, extra, inactives=()):
    st = team_stats(rows, "PT240M00.00S")
    st.update({"reboundsPersonal": st["reboundsOffensive"] + st["reboundsDefensive"], "reboundsTeam": 7,
               "reboundsTotal": st["reboundsOffensive"] + st["reboundsDefensive"] + 7,
               "turnoversTeam": 1, "turnoversTotal": st["turnovers"] + 1})
    return {"teamTricode": tricode, "score": st["points"], "statistics": st,
            "players": [live_player(r, i + 1) for i, r in enumerate(rows)] + list(extra),
            "inactives": list(inactives)}


def historical_team(tricode, rows, dnps):
    """The box score page's other format: no played/starter flags, mm:ss minutes, DNP comments."""
    players = []
    for r in rows:
        p = live_player(r, 0)
        players.append({"personId": p["personId"], "firstName": p["firstName"], "familyName": p["familyName"],
                        "nameI": "", "playerSlug": "", "position": "F" if r[1] else "", "comment": "",
                        "jerseyNum": "", "statistics": dict(p["statistics"], minutes=fetch.mp_text(fetch.secs(r[2])))})
    for name, comment in dnps:
        first, _, family = name.partition(" ")
        players.append({"firstName": first, "familyName": family, "position": "", "comment": comment,
                        "statistics": {"minutes": "", "points": 0}})
    st = team_stats(rows, "240:00")
    st["reboundsTotal"] = st["reboundsOffensive"] + st["reboundsDefensive"]
    return {"teamTricode": tricode, "score": st["points"], "statistics": st, "players": players}


def dnp(name, reason=None, status="ACTIVE"):
    p = {"status": status, "starter": "0", "played": "0", "name": name, "statistics": {"minutes": "PT00M00.00S"}}
    if reason:
        p["notPlayingReason"] = reason
    return p


BOX_OKC = {"game": {
    "gameId": "0022600011", "gameCode": "20261022/DENOKC", "gameStatus": 3, "gameStatusText": "Final", "period": 4,
    "awayTeam": live_team("DEN", DEN, [dnp("Zeke Nnaji")]),
    "homeTeam": live_team("OKC", OKC, [], inactives=[
        {"name": "Nikola Topic", "notPlayingReason": "INACTIVE_INJURY"},
        {"name": "Two Way Guy", "notPlayingReason": "INACTIVE_GLEAGUE_TWOWAY"}]),
}}
BOX_PHI = {"game": {
    "gameId": "0022600010", "gameCode": "20261022/CLEPHI", "gameStatus": 3, "gameStatusText": "Final", "period": 4,
    "awayTeam": historical_team("CLE", CLE, [("Thomas Bryant", "DNP - Coach's Decision")]),
    "homeTeam": historical_team("PHI", PHI, [("Kelly Oubre Jr.", "Inactive - Injury/Illness"),
                                             ("Dean Wade", "NWT - Personal"),
                                             ("Two Way Guy", "Inactive - G League - Two-Way")]),
}}
# seen on nba.com (HOU@SAS 2026-10-23): a stale DNP comment on a player who played
BOX_PHI["game"]["awayTeam"]["players"][4]["comment"] = "DNP - Coach's Decision"


def card(gid, code, status, away, a, home, h, text="Final"):
    return {"cardData": {"gameId": gid, "gameCode": code, "gameStatus": status, "gameStatusText": text,
                         "awayTeam": {"teamTricode": away, "score": a}, "homeTeam": {"teamTricode": home, "score": h}}}


def games_page(*cards):
    return {"gameCardFeed": {"modules": [{"moduleData": {}, "cards": [{"cardData": {"heroConfiguration": {}}}] + list(cards)}]}}


GAMES_1022 = games_page(card("0022600011", "20261022/DENOKC", 3, "DEN", 84, "OKC", 96),
                        card("0022600010", "20261022/CLEPHI", 3, "CLE", 88, "PHI", 105))
GAMES_1023 = games_page(card("0022600020", "20261023/ATLCHA", 2, "ATL", 70, "CHA", 66, "Q3 5:12"),
                        card("0022600021", "20261023/LBNBKN", 1, "LBN", 0, "BKN", 0, "7:30 pm ET"))


def espn_summary():
    keys = ["minutes", "points", "fieldGoalsMade-fieldGoalsAttempted",
            "threePointFieldGoalsMade-threePointFieldGoalsAttempted", "freeThrowsMade-freeThrowsAttempted",
            "rebounds", "assists", "turnovers", "steals", "blocks", "offensiveRebounds",
            "defensiveRebounds", "fouls", "plusMinus"]

    def team(abbr, rows, extra_dnp):
        athletes = []
        for r in rows:
            name, starter, mins, fgm, fga, tpm, tpa, ftm, fta, orb, drb, ast, stl, blk, tov, pf = r
            vals = [round(fetch.secs(mins) / 60), pts(r), f"{fgm}-{fga}", f"{tpm}-{tpa}", f"{ftm}-{fta}", orb + drb,
                    ast, tov, stl, blk, orb, drb, pf, "+0"]  # ESPN gives rounded whole minutes
            athletes.append({"athlete": {"displayName": fetch.fold(name).title()}, "starter": bool(starter),
                             "didNotPlay": False, "stats": [str(v) for v in vals]})
        athletes += [{"athlete": {"displayName": n}, "starter": False, "didNotPlay": True, "reason": r, "stats": []}
                     for n, r in extra_dnp]
        col = lambda i: sum(r[i] for r in rows)  # noqa: E731
        orb, drb = col(9), col(10)
        # ESPN's per-player totals row counts team rebounds but not team turnovers
        totals = ["", str(sum(pts(r) for r in rows)), f"{col(3)}-{col(4)}", f"{col(5)}-{col(6)}",
                  f"{col(7)}-{col(8)}", str(orb + drb + 5), str(col(11)), str(col(14)), str(col(12)),
                  str(col(13)), str(orb), str(drb), str(col(15)), ""]
        return {"team": {"abbreviation": abbr}, "statistics": [{"keys": keys, "athletes": athletes, "totals": totals}]}

    return {"header": {"competitions": [{
                "status": {"type": {"completed": True, "state": "post"}},
                "competitors": [{"homeAway": "away", "team": {"abbreviation": "DEN"}, "score": "84"},
                                {"homeAway": "home", "team": {"abbreviation": "OKC"}, "score": "96"}]}]},
            "boxscore": {"players": [team("DEN", DEN, [("Zeke Nnaji", "COACH'S DECISION")]), team("OKC", OKC, [])],
                         "teams": [{"team": {"abbreviation": "DEN"}, "statistics": [
                                       {"name": "turnovers", "displayValue": "20"},
                                       {"name": "totalTurnovers", "displayValue": "22"}]},
                                   {"team": {"abbreviation": "OKC"}, "statistics": [
                                       {"name": "totalTurnovers", "displayValue": "13"}]}]}}


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
    """Stands in for fetch.get: www.nba.com URLs answer an HTML page with the page data,
    others JSON. A route set to an exception raises it."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, url, accept="application/json", tries=3):
        self.calls.append(url)
        for prefix, result in self.routes.items():
            if url.startswith(prefix):
                if isinstance(result, Exception):
                    raise result
                if url.startswith("https://www.nba.com/"):
                    data = json.dumps({"props": {"pageProps": result}})
                    return f'<html><script id="__NEXT_DATA__" type="application/json">{data}</script></html>'
                return json.dumps(result)
        raise fetch.NotPublished(f"HTTP 404: {url}")


def routes(**over):
    r = {fetch.NBA_GAMES_URL.format("2026-10-22"): GAMES_1022,
         fetch.NBA_GAMES_URL.format("2026-10-23"): GAMES_1023,
         fetch.NBA_BOX_URL.format("0022600011"): BOX_OKC,
         fetch.NBA_BOX_URL.format("0022600010"): BOX_PHI,
         fetch.ESPN_SCOREBOARD_URL.format("20261022"): ESPN_SCOREBOARD,
         fetch.ESPN_SUMMARY_URL.format("401810011"): espn_summary()}
    r.update(over)
    return r


class FetchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def folder(self, day):
        return os.path.join(self.tmp.name, day)

    def run_day(self, day, http, source="auto", now=NOW):
        with mock.patch.object(fetch, "get", http):
            games, err = fetch.collect(day, source, fetch.read_meta(self.folder(day)), self.folder(day), now)
        self.assertIsNone(err)
        return games

    def read(self, day, name):
        with open(os.path.join(self.folder(day), name), encoding="utf-8") as f:
            return f.read()

    def test_nba_final_games(self):
        games = self.run_day("2026-10-22", FakeHTTP(routes()))
        self.assertEqual([(g["boxid"], g["source"], g["problems"]) for g in games],
                         [("202610220OKC", "nba", []), ("202610220PHI", "nba", [])])
        changed, line = fetch.write_day(self.tmp.name, "2026-10-22", games)
        self.assertEqual((changed, line), (True, "2026-10-22: 2/2 final (nba)"))
        self.assertEqual(self.read("2026-10-22", "games.txt").splitlines(), [
            "Denver Nuggets|84|Oklahoma City Thunder|96|https://www.basketball-reference.com/boxscores/202610220OKC.html|final",
            "Cleveland Cavaliers|88|Philadelphia 76ers|105|https://www.basketball-reference.com/boxscores/202610220PHI.html|final",
        ])
        text = self.read("2026-10-22", "202610220OKC.txt")
        self.assertTrue(text.startswith("Final: Denver Nuggets 84, Oklahoma City Thunder 96\n\n```\n"))
        header, rows = parse_tsv(text)
        self.assertEqual("\t".join(header), fetch.TSV_HEADER)
        den = [r for r in rows if r["team"] == "Denver Nuggets"]
        # starters by minutes, then reserves by minutes, then DNPs, then totals
        self.assertEqual([r["player"] for r in den[:5]],
                         ["Jamal Murray", "Nikola Jokić", "Christian Braun", "Aaron Gordon", "Cameron Johnson"])
        self.assertEqual(den[6], {"team": "Denver Nuggets", "section": "Reserves", "player": "Julian Strawther",
                                  "MP": "21:58", "FG": "2", "FGA": "4", "3P": "0", "3PA": "2", "FT": "0", "FTA": "0",
                                  "ORB": "0", "DRB": "2", "TRB": "2", "AST": "3", "STL": "1", "BLK": "0",
                                  "TOV": "0", "PF": "0", "PTS": "4"})
        self.assertIn("DaRon Holmes", [r["player"] for r in den])
        self.assertEqual((den[-2]["player"], den[-2]["MP"], len(den[-2])), ("Zeke Nnaji", "Did Not Play", 4))
        self.assertEqual((den[-1]["section"], den[-1]["MP"], den[-1]["PTS"], den[-1]["TRB"], den[-1]["TOV"]),
                         ("Totals", "240", "84", "53", "21"))  # rebounds without team rebounds, TOV with team TOV
        okc = {r["player"]: r for r in rows if r["team"] == "Oklahoma City Thunder"}
        self.assertEqual(okc["Nikola Topić"]["MP"], "Did Not Dress")  # injured, listed apart; accents restored
        self.assertNotIn("Two Way Guy", okc)  # G League two-way: left out like Basketball-Reference does
        # historical page format
        _, rows = parse_tsv(self.read("2026-10-22", "202610220PHI.txt"))
        phi = {r["player"]: r for r in rows if r["team"] == "Philadelphia 76ers"}
        self.assertEqual((phi["Tyrese Maxey"]["section"], phi["Tyrese Maxey"]["MP"], phi["Tyrese Maxey"]["PTS"]),
                         ("Starters", "48:00", "32"))
        self.assertEqual((phi["Kelly Oubre Jr."]["MP"], phi["Dean Wade"]["MP"]), ("Did Not Dress", "Not With Team"))
        self.assertNotIn("Two Way Guy", phi)
        cle = {r["player"]: r for r in rows if r["team"] == "Cleveland Cavaliers"}
        self.assertEqual((cle["Jarrett Allen"]["MP"], cle["Jarrett Allen"]["PTS"]), ("48:00", "14"))
        self.assertEqual(phi["Team Totals"]["MP"], "240")
        # every column's player sum equals the Team Totals row (what build_day.py --check verifies)
        for f in ("202610220OKC.txt", "202610220PHI.txt"):
            _, rows = parse_tsv(self.read("2026-10-22", f))
            for team in {r["team"] for r in rows}:
                team_rows = [r for r in rows if r["team"] == team]
                played = [r for r in team_rows if ":" in r["MP"]]
                total = team_rows[-1]
                for c in ("FG", "FGA", "3P", "3PA", "FT", "FTA", "ORB", "DRB", "TRB", "AST", "STL", "BLK", "PF", "PTS"):
                    self.assertEqual(sum(int(r[c]) for r in played), int(total[c]), (f, team, c))
                minutes = sum(fetch.secs(r["MP"]) for r in played) / 60
                self.assertAlmostEqual(minutes, 240, delta=1.5)
        meta = json.loads(self.read("2026-10-22", "source.json"))
        self.assertEqual((meta["games"], meta["final"], meta["pending"], meta["problems"]), (2, 2, 0, 0))
        first = meta["list"][0]
        self.assertEqual((first["url"], first["final_at"], first["away_score"], first["home_score"]),
                         ("https://www.nba.com/game/0022600011/box-score", "2026-10-24T05:27:00Z", 84, 96))
        # same data again: nothing rewritten, source.json keeps its timestamp
        self.assertFalse(fetch.write_day(self.tmp.name, "2026-10-22", self.run_day("2026-10-22", FakeHTTP(routes())))[0])

    def test_settled_games_are_not_fetched_again(self):
        fetch.write_day(self.tmp.name, "2026-10-22", self.run_day("2026-10-22", FakeHTTP(routes())))
        before = self.read("2026-10-22", "202610220OKC.txt")
        # within the hour: re-read (stat corrections), final_at kept
        http = FakeHTTP(routes())
        games = self.run_day("2026-10-22", http, now=NOW + dt.timedelta(minutes=40))
        self.assertIn(fetch.NBA_BOX_URL.format("0022600011"), http.calls)
        self.assertEqual(games[0]["final_at"], "2026-10-24T05:27:00Z")
        # later: only the games page is read, files stay
        http = FakeHTTP(routes())
        games = self.run_day("2026-10-22", http, now=NOW + dt.timedelta(hours=2))
        self.assertEqual(http.calls, [fetch.NBA_GAMES_URL.format("2026-10-22")])
        self.assertFalse(fetch.write_day(self.tmp.name, "2026-10-22", games)[0])
        self.assertEqual(self.read("2026-10-22", "202610220OKC.txt"), before)
        # and main() skips the settled night without any request
        http = FakeHTTP(routes())
        with mock.patch.object(fetch, "get", http), mock.patch.object(fetch, "utc_now", lambda: NOW + dt.timedelta(hours=2)):
            fetch.main(["--out", self.tmp.name, "--dates", "2026-10-22"])
        self.assertEqual(http.calls, [])

    def test_games_with_check_problems_stay_unsettled(self):
        box = json.loads(json.dumps(BOX_OKC))
        box["game"]["awayTeam"]["players"].pop(6)  # a player missing from NBA.com's first version
        fetch.write_day(self.tmp.name, "2026-10-22", self.run_day(
            "2026-10-22", FakeHTTP(routes(**{fetch.NBA_BOX_URL.format("0022600011"): box}))))
        http = FakeHTTP(routes())
        games = self.run_day("2026-10-22", http, now=NOW + dt.timedelta(hours=2))
        self.assertIn(fetch.NBA_BOX_URL.format("0022600011"), http.calls)  # read again, now complete
        self.assertNotIn(fetch.NBA_BOX_URL.format("0022600010"), http.calls)  # the clean game stays settled
        self.assertEqual(games[0]["problems"], [])

    def test_unfinished_and_unknown_teams(self):
        http = FakeHTTP(routes())
        games = self.run_day("2026-10-23", http)
        self.assertEqual(len(games), 1)  # the exhibition opponent "LBN" is skipped
        self.assertEqual(http.calls, [fetch.NBA_GAMES_URL.format("2026-10-23")])  # live game: no box score page
        self.assertEqual(fetch.game_line("2026-10-23", games[0]), "Atlanta Hawks||Charlotte Hornets|||not final")
        fetch.write_day(self.tmp.name, "2026-10-23", games)
        self.assertEqual(json.loads(self.read("2026-10-23", "source.json"))["list"][0]["status"], "in progress")

    def test_no_games(self):
        games = self.run_day("2026-10-19", FakeHTTP(routes(**{
            fetch.NBA_GAMES_URL.format("2026-10-19"): games_page(),
            fetch.ESPN_SCOREBOARD_URL.format("20261019"): {"events": []}})))
        self.assertEqual(games, [])
        self.assertEqual(fetch.write_day(self.tmp.name, "2026-10-19", games)[1], "2026-10-19: no games")
        self.assertEqual(self.read("2026-10-19", "games.txt"), "NO_GAMES\n")

    def test_espn_fallback_when_nba_box_breaks(self):
        games = self.run_day("2026-10-22", FakeHTTP(routes(**{fetch.NBA_BOX_URL.format("0022600011"): RuntimeError("timeout")})))
        okc = games[0]
        self.assertEqual((okc["source"], okc["espn_event_id"], okc["problems"], okc["final_at"]),
                         ("espn", "401810011", [], None))
        _, rows = parse_tsv(fetch.box_text(okc["box"]))
        jokic = next(r for r in rows if r["player"].startswith("Nikola Jok"))
        self.assertEqual((jokic["player"], jokic["MP"], jokic["FG"], jokic["FGA"]), ("Nikola Jokić", "35:00", "5", "19"))
        self.assertEqual(next(r for r in rows if r["player"] == "Zeke Nnaji")["MP"], "Did Not Play")
        den_total = next(r for r in rows if r["team"] == "Denver Nuggets" and r["section"] == "Totals")
        # rebounds = players' sum, turnovers include team turnovers (Basketball-Reference totals)
        self.assertEqual((den_total["TRB"], den_total["TOV"], den_total["PTS"]), ("53", "22", "84"))

    def test_espn_overtime_minutes_from_linescores(self):
        summary = espn_summary()
        for c in summary["header"]["competitions"][0]["competitors"]:
            c["linescores"] = [{"displayValue": "20"}] * 5  # ESPN's header has no period count
        with mock.patch.object(fetch, "get", FakeHTTP({fetch.ESPN_SUMMARY_URL.format("1"): summary})):
            box, status, _ = fetch.espn_box("1")
        self.assertEqual((status, box["periods"], box["away"]["totals"]["mp"]), (3, 5, 265))

    def test_espn_only_when_nba_page_down(self):
        games = self.run_day("2026-10-22", FakeHTTP(routes(**{fetch.NBA_GAMES_URL.format("2026-10-22"): RuntimeError("down")})))
        self.assertEqual([(g["boxid"], g["source"]) for g in games], [("202610220OKC", "espn")])

    def test_nothing_answers(self):
        http = FakeHTTP({fetch.NBA_GAMES_URL.format("2026-10-22"): RuntimeError("down"),
                         fetch.ESPN_SCOREBOARD_URL.format("20261022"): RuntimeError("down")})
        with mock.patch.object(fetch, "get", http):
            games, err = fetch.collect("2026-10-22", "auto")
        self.assertIsNone(games)
        self.assertIn("NBA games page", err)

    def test_check_flags_missing_player(self):
        box = json.loads(json.dumps(BOX_OKC))
        box["game"]["awayTeam"]["players"] = [p for p in box["game"]["awayTeam"]["players"]
                                              if p["name"] != "Julian Strawther"]
        problems = self.run_day("2026-10-22", FakeHTTP(routes(**{fetch.NBA_BOX_URL.format("0022600011"): box})))[0]["problems"]
        self.assertIn("DEN pts: players 80 != team 84", problems)
        self.assertIn("DEN minutes: players 217.7 != team 240", problems)

    def test_helpers(self):
        self.assertEqual(fetch.secs("PT36M45.00S"), 2205)
        self.assertEqual(fetch.secs("PT00M04.50S"), 4)
        self.assertEqual(fetch.secs("36:02"), 2162)
        self.assertEqual(fetch.secs(""), 0)
        self.assertEqual(fetch.mp_text(2205), "36:45")
        self.assertEqual(fetch.mp_text(64), "1:04")
        self.assertEqual(fetch.bref_name("Alperen Sengun"), "Alperen Şengün")
        self.assertEqual(fetch.bref_name("Alex Sarr"), "Alex Sarr")  # Basketball-Reference uses the short name
        self.assertEqual(fetch.bref_name("Cam Johnson"), "Cameron Johnson")
        self.assertEqual(fetch.bref_name("Hansen Yang"), "Yang Hansen")
        self.assertEqual(fetch.bref_name("Shai Gilgeous-Alexander"), "Shai Gilgeous-Alexander")
        self.assertEqual(fetch.boxid("2026-10-23", "PHX"), "202610230PHO")
        self.assertEqual(fetch.boxid("2026-10-23", "UTAH"), "202610230UTA")
        for reason, label in (("DNP_COACH", "Did Not Play"), ("INACTIVE_INJURY", "Did Not Dress"),
                              ("DND_INJURY", "Did Not Dress"), ("NWT_PERSONAL", "Not With Team"),
                              ("INACTIVE_SUSPENSION", "Player Suspended"), ("INACTIVE_GLEAGUE_TWOWAY", None),
                              ("DNP - Coach's Decision", "Did Not Play"), ("DND - Injury/Illness", "Did Not Dress"),
                              ("NWT - Personal", "Not With Team"), ("Inactive - G League - Two-Way", None),
                              ("Inactive - Injury/Illness", "Did Not Dress"), (None, "Did Not Play")):
            self.assertEqual(fetch.nba_dnp(reason), label, reason)
        # 08:45 Istanbul = 05:45 UTC: last night is the previous US date
        self.assertEqual(fetch.default_dates(dt.datetime(2026, 10, 24, 5, 45, tzinfo=UTC)), ["2026-10-23", "2026-10-22"])
        self.assertEqual(fetch.default_dates(dt.datetime(2026, 10, 24, 1, 7, tzinfo=UTC)), ["2026-10-23", "2026-10-22"])
        self.assertEqual(fetch.default_dates(dt.datetime(2026, 12, 1, 9, 47, tzinfo=UTC)), ["2026-11-30", "2026-11-29"])


if __name__ == "__main__":
    unittest.main()
