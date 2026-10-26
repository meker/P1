#!/usr/bin/env python3
"""Fetch NBA box scores from NBA.com (ESPN as fallback) in the daily report's raw format.

For every US game date D it writes, under <out>/<D>/:
  games.txt     one line per game: visitor|pts|home|pts|box URL|final (scores empty and
                "not final" while a game is unfinished), or the single line NO_GAMES
  <boxid>.txt   "Final: ..." line and a Basketball-Reference style TSV box score
  source.json   source, ids, status and self-check result of every game

NBA.com data comes from the public www.nba.com pages (the night's games page and each game's
box score page carry the official box score as page data); cdn.nba.com's JSON answers
"Access Denied" to cloud runners. Game ids and URLs keep Basketball-Reference's form
(YYYYMMDD0 + home code, e.g. 202610230MIL), so pipeline/build_day.py reads these files
exactly like the old ones. Standard library only, so it runs on a bare GitHub Actions runner.
"""

import argparse
import datetime as dt
import gzip
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

NBA_GAMES_URL = "https://www.nba.com/games?date={}"
NBA_BOX_URL = "https://www.nba.com/game/{}/box-score"
ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={}&limit=100"
ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={}"
ESPN_GAME_URL = "https://www.espn.com/nba/boxscore/_/gameId/{}"
BREF_BOX_URL = "https://www.basketball-reference.com/boxscores/{}.html"

# A final NBA.com box score is re-read for this long (stat corrections), then left alone.
REFRESH = dt.timedelta(hours=1)

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

# Basketball-Reference code and name for every NBA.com / ESPN abbreviation.
TEAMS = {}
for _codes, _bref, _name in (
    (("ATL",), "ATL", "Atlanta Hawks"),
    (("BOS",), "BOS", "Boston Celtics"),
    (("BKN", "BRK"), "BRK", "Brooklyn Nets"),
    (("CHA", "CHO"), "CHO", "Charlotte Hornets"),
    (("CHI",), "CHI", "Chicago Bulls"),
    (("CLE",), "CLE", "Cleveland Cavaliers"),
    (("DAL",), "DAL", "Dallas Mavericks"),
    (("DEN",), "DEN", "Denver Nuggets"),
    (("DET",), "DET", "Detroit Pistons"),
    (("GSW", "GS"), "GSW", "Golden State Warriors"),
    (("HOU",), "HOU", "Houston Rockets"),
    (("IND",), "IND", "Indiana Pacers"),
    (("LAC",), "LAC", "Los Angeles Clippers"),
    (("LAL",), "LAL", "Los Angeles Lakers"),
    (("MEM",), "MEM", "Memphis Grizzlies"),
    (("MIA",), "MIA", "Miami Heat"),
    (("MIL",), "MIL", "Milwaukee Bucks"),
    (("MIN",), "MIN", "Minnesota Timberwolves"),
    (("NOP", "NO"), "NOP", "New Orleans Pelicans"),
    (("NYK", "NY"), "NYK", "New York Knicks"),
    (("OKC",), "OKC", "Oklahoma City Thunder"),
    (("ORL",), "ORL", "Orlando Magic"),
    (("PHI",), "PHI", "Philadelphia 76ers"),
    (("PHX", "PHO"), "PHO", "Phoenix Suns"),
    (("POR",), "POR", "Portland Trail Blazers"),
    (("SAC",), "SAC", "Sacramento Kings"),
    (("SAS", "SA"), "SAS", "San Antonio Spurs"),
    (("TOR",), "TOR", "Toronto Raptors"),
    (("UTA", "UTAH"), "UTA", "Utah Jazz"),
    (("WAS", "WSH"), "WAS", "Washington Wizards"),
):
    for _c in _codes + (_bref,):
        TEAMS[_c] = (_bref, _name)

# NBA.com / ESPN spelling -> Basketball-Reference spelling. build_day.py keys players by a
# lowercase name without accents, suffixes (Jr., II, III), periods, apostrophes and hyphens,
# so only first-name differences matter here; add one when the report shows a split player.
NAME_ALIASES = {
    "Cam Johnson": "Cameron Johnson",
    "DaRon Holmes II": "DaRon Holmes",
    "Hansen Yang": "Yang Hansen",
    "Moe Wagner": "Moritz Wagner",
}
# Basketball-Reference keeps these accents; ESPN (and sometimes NBA.com) drops them.
ACCENTED_NAMES = (
    "Alperen Şengün", "Bogdan Bogdanović", "Chris Mañon", "Dario Šarić", "Dennis Schröder",
    "Egor Dëmin", "Hugo González", "Jonas Valančiūnas", "Jusuf Nurkić", "Karim López",
    "Karlo Matković", "Kasparas Jakučionis", "Kristaps Porziņģis", "Luka Dončić",
    "Moussa Cissé", "Moussa Diabaté", "Nikola Jokić", "Nikola Jović", "Nikola Topić",
    "Nikola Vučević", "Nolan Traoré", "Pacôme Dadiet", "Tidjane Salaün", "Tristan Vukčević",
    "Vasilije Micić", "Vít Krejčí", "Vlatko Čančar",
)

# Stat keys in TSV column order after MP, and the NBA.com field behind each.
STATS = ("fgm", "fga", "tpm", "tpa", "ftm", "fta", "orb", "drb", "trb", "ast", "stl", "blk", "tov", "pf", "pts")
NBA_FIELDS = {
    "fgm": "fieldGoalsMade", "fga": "fieldGoalsAttempted",
    "tpm": "threePointersMade", "tpa": "threePointersAttempted",
    "ftm": "freeThrowsMade", "fta": "freeThrowsAttempted",
    "orb": "reboundsOffensive", "drb": "reboundsDefensive", "trb": "reboundsTotal",
    "ast": "assists", "stl": "steals", "blk": "blocks", "tov": "turnovers",
    "pf": "foulsPersonal", "pts": "points",
}
TSV_HEADER = "team\tsection\tplayer\tMP\tFG\tFGA\t3P\t3PA\tFT\tFTA\tORB\tDRB\tTRB\tAST\tSTL\tBLK\tTOV\tPF\tPTS"


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def fold(s):
    """Lowercase ASCII form of a name, for accent-insensitive lookups."""
    s = unicodedata.normalize("NFKD", s.replace("Đ", "Dj").replace("đ", "dj"))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


ACCENTED_BY_FOLD = {fold(n): n for n in ACCENTED_NAMES}


def bref_name(name):
    name = " ".join((name or "").split())
    name = NAME_ALIASES.get(name, name)
    return ACCENTED_BY_FOLD.get(fold(name), name)


# --- HTTP --------------------------------------------------------------------------------

class NotPublished(Exception):
    """403/404: the page is not published (yet)."""


def get(url, accept="application/json", tries=3):
    """Body of `url` as text, retried on network errors and 5xx."""
    hdrs = {"User-Agent": BROWSER_UA, "Accept": accept, "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip"}
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
            return body.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                raise NotPublished(f"HTTP {e.code}: {url}") from None
            last = f"HTTP {e.code}"
        except (urllib.error.URLError, OSError) as e:
            last = repr(e)
        if attempt + 1 < tries:
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def get_json(url):
    try:
        return json.loads(get(url))
    except ValueError as e:
        raise RuntimeError(f"{url}: not JSON ({e})") from None


def page_data(url):
    """pageProps of a www.nba.com page (its Next.js page data)."""
    html = get(url, accept="text/html,application/xhtml+xml")
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError(f"{url}: no page data")
    try:
        return json.loads(m.group(1))["props"]["pageProps"]
    except (ValueError, KeyError) as e:
        raise RuntimeError(f"{url}: unexpected page data ({e!r})") from None


# --- NBA.com -----------------------------------------------------------------------------

def secs(s):
    """'PT36M45.00S' or '36:45' -> 2205."""
    s = str(s or "")
    m = re.fullmatch(r"(\d+):(\d{1,2})", s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.fullmatch(r"PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", s)
    return int(m.group(1) or 0) * 60 + int(float(m.group(2) or 0)) if m else 0


def nba_dnp(reason):
    """NBA.com not-playing reason ("DNP_COACH", "INACTIVE_INJURY", "DND - Injury/Illness",
    ...) -> Basketball-Reference MP text; None = leave the player out."""
    r = (reason or "").upper()
    if "GLEAGUE" in r or "G LEAGUE" in r:  # two-way / assignment players: not part of the game's roster
        return None
    if "SUSPEN" in r:
        return "Player Suspended"
    if r.startswith("NWT") or "NOT_WITH_TEAM" in r or "NOT WITH TEAM" in r:
        return "Not With Team"
    if r.startswith(("DND", "INACTIVE")):
        return "Did Not Dress"
    return "Did Not Play"


def nba_games(day):
    """[(game id, away, home, status, status text, away score, home score)] on NBA.com's
    games page for US date `day`."""
    pp = page_data(NBA_GAMES_URL.format(day))
    try:
        modules = pp["gameCardFeed"]["modules"]
    except (KeyError, TypeError):
        raise RuntimeError("NBA games page: no game card feed") from None
    out, seen = [], set()
    for mod in modules or []:
        for card in mod.get("cards") or []:
            g = card.get("cardData") or {}
            gid = g.get("gameId")
            away, home = ((g.get(k) or {}).get("teamTricode") for k in ("awayTeam", "homeTeam"))
            if not gid or gid in seen or away not in TEAMS or home not in TEAMS:
                continue  # promo cards, All-Star or international exhibitions
            code = g.get("gameCode") or ""
            if re.match(r"\d{8}/", code) and code[:8] != day.replace("-", ""):
                continue
            seen.add(gid)
            out.append({"id": gid, "away": away, "home": home,
                        "status": int(g.get("gameStatus") or 1),
                        "status_text": (g.get("gameStatusText") or "").strip(),
                        "away_score": g["awayTeam"].get("score"), "home_score": g["homeTeam"].get("score")})
    return out


def nba_team(t):
    """One team of an NBA.com box score. The page carries either the live data format
    (starter/played flags, ISO minutes, inactive players listed apart) or the historical
    one (starters have a position, DNP reason in "comment", minutes as mm:ss)."""
    code, name = TEAMS[t["teamTricode"]]
    players = []
    for p in t.get("players", []):
        st = p.get("statistics") or {}
        row = {"name": bref_name(p.get("name") or f"{p.get('firstName', '')} {p.get('familyName', '')}")}
        if "played" in p:
            row["starter"] = str(p.get("starter")) == "1"
            played, reason = str(p["played"]) == "1", p.get("notPlayingReason")
        else:
            # the comment can say "DNP - Coach's Decision" for a player who did get minutes
            row["starter"] = bool(p.get("position"))
            played, reason = secs(st.get("minutes")) > 0, p.get("comment")
        if played:
            row["secs"] = secs(st.get("minutes"))
            row.update({k: int(st.get(f) or 0) for k, f in NBA_FIELDS.items()})
        else:
            row["dnp"] = nba_dnp(reason)
            if row["dnp"] is None:
                continue
        players.append(row)
    for p in t.get("inactives") or []:
        dnp = nba_dnp(p.get("notPlayingReason") or p.get("comment") or "INACTIVE")
        if dnp:
            players.append({"name": bref_name(p.get("name") or f"{p.get('firstName', '')} {p.get('familyName', '')}"),
                            "starter": False, "dnp": dnp})
    st = t.get("statistics") or {}
    played = [p for p in players if "dnp" not in p]
    tot = {k: int(st.get(NBA_FIELDS[k]) or 0) for k in ("fgm", "fga", "tpm", "tpa", "ftm", "fta", "ast", "stl", "blk", "pf", "pts")}
    # Basketball-Reference team totals: rebounds = players' sum (no team rebounds),
    # turnovers include team turnovers.
    for k in ("orb", "drb", "trb"):
        tot[k] = sum(p[k] for p in played)
    tov_players = sum(p["tov"] for p in played)
    if "turnoversTotal" in st:
        tot["tov"] = int(st["turnoversTotal"] or 0)
    else:
        tot["tov"] = max(int(st.get("turnovers") or 0), tov_players + int(st.get("turnoversTeam") or 0))
    tot["mp"] = round(secs(st.get("minutes")) / 60)
    return {"code": code, "name": name, "score": int(t.get("score") or 0), "players": players, "totals": tot}


def nba_box(game_id):
    """(box, status, status text) from a game's www.nba.com box score page; box is None
    while the game is not final."""
    g = page_data(NBA_BOX_URL.format(game_id)).get("game") or {}
    if g.get("gameId") != game_id:
        raise RuntimeError(f"NBA box score page of {game_id} has no game data")
    status, text = int(g.get("gameStatus") or 1), (g.get("gameStatusText") or "").strip()
    if status != 3:
        return None, status, text
    periods = int(g.get("period") or 4)
    box = {"away": nba_team(g["awayTeam"]), "home": nba_team(g["homeTeam"]), "periods": periods}
    for side in ("away", "home"):
        if not box[side]["totals"]["mp"]:
            box[side]["totals"]["mp"] = 240 + 25 * max(0, periods - 4)
    return box, status, text


# --- ESPN --------------------------------------------------------------------------------

ESPN_LABELS = {"MIN": "minutes", "PTS": "points", "FG": "fieldGoalsMade-fieldGoalsAttempted",
               "3PT": "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
               "FT": "freeThrowsMade-freeThrowsAttempted", "REB": "rebounds", "AST": "assists",
               "TO": "turnovers", "STL": "steals", "BLK": "blocks", "OREB": "offensiveRebounds",
               "DREB": "defensiveRebounds", "PF": "fouls"}
ESPN_SINGLE = {"points": "pts", "rebounds": "trb", "offensiveRebounds": "orb", "defensiveRebounds": "drb",
               "assists": "ast", "steals": "stl", "blocks": "blk", "turnovers": "tov", "fouls": "pf"}
ESPN_PAIRS = {"fieldGoalsMade-fieldGoalsAttempted": ("fgm", "fga"),
              "threePointFieldGoalsMade-threePointFieldGoalsAttempted": ("tpm", "tpa"),
              "freeThrowsMade-freeThrowsAttempted": ("ftm", "fta")}


def espn_games(day):
    data = get_json(ESPN_SCOREBOARD_URL.format(day.replace("-", "")))
    out = []
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        sides = {c.get("homeAway"): c for c in comp.get("competitors", [])}
        try:
            away, home = (sides[s]["team"]["abbreviation"] for s in ("away", "home"))
        except KeyError:
            continue
        if away not in TEAMS or home not in TEAMS:
            continue
        st = (comp.get("status") or ev.get("status") or {}).get("type", {})
        out.append({"id": ev["id"], "away": away, "home": home,
                    "status": 3 if st.get("completed") else (2 if st.get("state") == "in" else 1),
                    "status_text": st.get("shortDetail") or st.get("description") or "",
                    "away_score": sides["away"].get("score"), "home_score": sides["home"].get("score")})
    return out


def espn_values(keys, values):
    row = {}
    for key, val in zip(keys, values):
        val = (val or "").strip()
        if key in ESPN_SINGLE:
            row[ESPN_SINGLE[key]] = int(val) if re.fullmatch(r"-?\d+", val) else 0
        elif key in ESPN_PAIRS:
            m = re.fullmatch(r"(\d+)-(\d+)", val)
            made, att = ESPN_PAIRS[key]
            row[made], row[att] = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
        elif key == "minutes":
            row["secs"] = int(val) * 60 if val.isdigit() else 0
    return row


def espn_dnp(reason):
    r = (reason or "").upper()
    if "SUSPEN" in r:
        return "Player Suspended"
    if "NOT WITH TEAM" in r:
        return "Not With Team"
    if "COACH" in r or not r:
        return "Did Not Play"
    return "Did Not Dress"


def espn_box(event_id):
    data = get_json(ESPN_SUMMARY_URL.format(event_id))
    comp = (data.get("header", {}).get("competitions") or [{}])[0]
    st = comp.get("status", {})
    if not st.get("type", {}).get("completed"):
        return None, 2, st.get("type", {}).get("shortDetail", "")
    # the summary header usually has no period count; the per-period line scores do
    periods = max([int(st.get("period") or 0), 4] + [len(c.get("linescores") or []) for c in comp.get("competitors", [])])
    scores = {c["team"]["abbreviation"]: int(c.get("score") or 0) for c in comp.get("competitors", [])}
    sides = {c["homeAway"]: c["team"]["abbreviation"] for c in comp.get("competitors", [])}
    # team turnovers are only in the team stats block ("totalTurnovers" = players' + team's)
    total_tov = {}
    for t in data.get("boxscore", {}).get("teams", []):
        for s in t.get("statistics", []):
            if s.get("name") == "totalTurnovers" and str(s.get("displayValue", "")).isdigit():
                total_tov[t["team"]["abbreviation"]] = int(s["displayValue"])
    teams = {}
    for t in data.get("boxscore", {}).get("players", []):
        abbr = t["team"]["abbreviation"]
        block = t["statistics"][0]
        keys = block.get("keys") or [ESPN_LABELS.get(n, n) for n in (block.get("names") or block.get("labels") or [])]
        players = []
        for a in block.get("athletes", []):
            row = {"name": bref_name(a["athlete"]["displayName"]), "starter": bool(a.get("starter"))}
            if a.get("didNotPlay") or not a.get("stats"):
                row["dnp"] = espn_dnp(a.get("reason"))
            else:
                row.update({k: 0 for k in STATS})
                row.update(espn_values(keys, a["stats"]))
            players.append(row)
        played = [p for p in players if "dnp" not in p]
        tot = {k: 0 for k in STATS}
        tot.update(espn_values(keys, block.get("totals") or []))
        tot.pop("secs", None)
        for k in ("orb", "drb", "trb"):
            tot[k] = sum(p[k] for p in played)
        tot["tov"] = max(total_tov.get(abbr, tot["tov"]), sum(p["tov"] for p in played))
        tot["mp"] = 240 + 25 * max(0, periods - 4)
        code, name = TEAMS[abbr]
        teams[abbr] = {"code": code, "name": name, "score": scores.get(abbr, tot["pts"]),
                       "players": players, "totals": tot}
    return {"away": teams[sides["away"]], "home": teams[sides["home"]], "periods": periods}, 3, "Final"


# --- Collecting a night ------------------------------------------------------------------

def check(box, minutes_slack):
    """Self-check like build_day.py --check: players' sums against team totals and score."""
    problems = []
    for side in ("away", "home"):
        t = box[side]
        played = [p for p in t["players"] if "dnp" not in p]
        tot = t["totals"]
        for k in ("fgm", "fga", "tpm", "tpa", "ftm", "fta", "ast", "stl", "blk", "pf", "pts"):
            s = sum(p[k] for p in played)
            if s != tot[k]:
                problems.append(f"{t['code']} {k}: players {s} != team {tot[k]}")
        extra_tov = tot["tov"] - sum(p["tov"] for p in played)
        if not 0 <= extra_tov <= 8:
            problems.append(f"{t['code']} tov: team {tot['tov']} vs players {tot['tov'] - extra_tov}")
        mins = sum(p["secs"] for p in played) / 60
        if abs(mins - tot["mp"]) > minutes_slack:
            problems.append(f"{t['code']} minutes: players {mins:.1f} != team {tot['mp']}")
        if tot["pts"] != t["score"]:
            problems.append(f"{t['code']} points: team {tot['pts']} != score {t['score']}")
    return problems


def boxid(day, home):
    return day.replace("-", "") + "0" + TEAMS[home][0]


def utc_now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def settled(entry, folder, now):
    """True for a game saved as final from NBA.com more than REFRESH ago that passed the
    self-check, its file still on disk. A game with check problems is read again every run."""
    if (not entry or entry.get("source") != "nba" or entry.get("status") != "final" or not entry.get("final_at")
            or entry.get("problems") or entry.get("away_score") is None
            or not os.path.exists(os.path.join(folder, entry["boxid"] + ".txt"))):
        return False
    final_at = dt.datetime.strptime(entry["final_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    return now - final_at > REFRESH


def try_box(src, gid, label):
    """(box, status, status_text, broken) from one source; box is None while not final."""
    try:
        box, status, text = nba_box(gid) if src == "nba" else espn_box(gid)
        return box, status, text, False
    except NotPublished:
        return None, None, None, False
    except (RuntimeError, KeyError, IndexError, TypeError, ValueError) as e:
        log(f"  {label} {src}: {e!r}")
        return None, None, None, True


def collect(day, source, prev=None, folder=None, now=None, debug=False):
    """All games of `day` with their box scores: (games, error). games is None when no
    source could list the night's games. Games saved as final from NBA.com more than an hour
    ago are not fetched again ("kept": their files on disk stay as they are)."""
    now = now or utc_now()
    before = {g["boxid"]: g for g in (prev or {}).get("list", [])}
    listing, espn_listing, err = None, None, []
    if source in ("auto", "nba"):
        try:
            listing = [dict(g, src="nba") for g in nba_games(day)]
        except (NotPublished, RuntimeError) as e:
            err.append(f"NBA games page: {e}")
            log(f"  NBA games page: {e}")
    if source == "espn" or (source == "auto" and not listing):
        try:
            espn_listing = espn_games(day)
        except (NotPublished, RuntimeError) as e:
            err.append(f"ESPN scoreboard: {e}")
        if espn_listing is not None and (espn_listing or listing is None):
            listing = [dict(g, src="espn") for g in espn_listing]
    if listing is None:
        return None, "; ".join(err) or "no source"
    games = []
    for g in listing:
        bid = boxid(day, g["home"])
        old = before.get(bid)
        game = {"boxid": bid, "away": g["away"], "home": g["home"],
                "status": g["status"], "status_text": g["status_text"], "box": None, "kept": None,
                "source": None, "final_at": None, "problems": [],
                "nba_game_id": g["id"] if g["src"] == "nba" else (old or {}).get("nba_game_id"),
                "espn_event_id": g["id"] if g["src"] == "espn" else (old or {}).get("espn_event_id")}
        if folder and settled(old, folder, now):
            game.update(kept=old, source="nba", status=3, status_text=old.get("status_text", "Final"),
                        final_at=old["final_at"], problems=old.get("problems", []))
            games.append(game)
            continue
        box, broken = None, False
        if g["src"] == "espn" or game["status"] == 3:  # NBA.com: box score page only once final
            box, status, text, broken = try_box(g["src"], g["id"], bid)
            if status:
                game["status"], game["status_text"] = status, text
        src = g["src"]
        if not box and source == "auto" and g["src"] == "nba" and (broken or game["status"] == 3):
            # NBA.com's box score is broken, or missing for a game its games page calls final: ESPN
            try:
                if espn_listing is None:
                    espn_listing = espn_games(day)
                ev = next((e for e in espn_listing if TEAMS[e["home"]][0] == TEAMS[g["home"]][0]), None)
            except (NotPublished, RuntimeError) as e:
                log(f"  ESPN fallback for {bid}: {e}")
                ev = None
            if ev:
                game["espn_event_id"] = ev["id"]
                box, status, text, _ = try_box("espn", ev["id"], bid)
                if box:
                    game["status"], game["status_text"], src = status, text, "espn"
        if box:
            game["box"], game["source"] = box, src
            game["problems"] = check(box, 1.5 if src == "nba" else 6)
            if src == "nba":
                keep = old and old.get("source") == "nba" and old.get("status") == "final" and old.get("final_at")
                game["final_at"] = old["final_at"] if keep else iso(now)
            if debug:
                log(f"  {bid} ({src}) players " + ", ".join(
                    f"{box[s]['code']} {len(box[s]['players'])}" for s in ("away", "home")))
        elif game["status"] == 3:
            game["final_scores"] = (g.get("away_score"), g.get("home_score"))
        games.append(game)
    return games, None


# --- Output ------------------------------------------------------------------------------

def mp_text(s):
    return f"{s // 60}:{s % 60:02d}"


def box_text(box):
    lines = [f"Final: {box['away']['name']} {box['away']['score']}, {box['home']['name']} {box['home']['score']}",
             "", "```", TSV_HEADER]
    for side in ("away", "home"):
        t = box[side]
        played = [p for p in t["players"] if "dnp" not in p]
        order = (sorted((p for p in played if p["starter"]), key=lambda p: -p["secs"])
                 + sorted((p for p in played if not p["starter"]), key=lambda p: -p["secs"]))
        for p in order:
            lines.append("\t".join([t["name"], "Starters" if p["starter"] else "Reserves", p["name"],
                                    mp_text(p["secs"])] + [str(p[k]) for k in STATS]))
        for p in t["players"]:
            if "dnp" in p:
                lines.append("\t".join([t["name"], "Reserves", p["name"], p["dnp"]]))
        tot = t["totals"]
        lines.append("\t".join([t["name"], "Totals", "Team Totals", str(tot["mp"])] + [str(tot[k]) for k in STATS]))
    lines.append("```")
    return "\n".join(lines) + "\n"


def scores_of(g):
    if g["box"]:
        return g["box"]["away"]["score"], g["box"]["home"]["score"]
    if g["kept"]:
        return g["kept"]["away_score"], g["kept"]["home_score"]
    if g["status"] == 3 and all(s not in (None, "") for s in g.get("final_scores", (None, None))):
        return tuple(int(s) for s in g["final_scores"])
    return None, None


def game_line(day, g):
    away, home = TEAMS[g["away"]][1], TEAMS[g["home"]][1]
    a, h = scores_of(g)
    if a is None:
        return f"{away}||{home}|||not final"
    return f"{away}|{a}|{home}|{h}|{BREF_BOX_URL.format(g['boxid'])}|final"


def write_if_changed(path, text):
    try:
        with open(path, encoding="utf-8") as f:
            if f.read() == text:
                return False
    except FileNotFoundError:
        pass
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def read_meta(folder):
    try:
        with open(os.path.join(folder, "source.json"), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return None


def write_day(out, day, games):
    """Write the night's files; returns (changed, summary line)."""
    folder = os.path.join(out, day)
    os.makedirs(folder, exist_ok=True)
    changed = False
    if not games:
        changed |= write_if_changed(os.path.join(folder, "games.txt"), "NO_GAMES\n")
    else:
        changed |= write_if_changed(os.path.join(folder, "games.txt"),
                                    "".join(game_line(day, g) + "\n" for g in games))
        for g in games:
            if g["box"]:
                changed |= write_if_changed(os.path.join(folder, g["boxid"] + ".txt"), box_text(g["box"]))
    final = sum(1 for g in games if g["box"] or g["kept"])
    entries = []
    for g in games:
        a, h = scores_of(g)
        done = bool(g["box"] or g["kept"])
        entries.append({
            "boxid": g["boxid"], "away": TEAMS[g["away"]][0], "home": TEAMS[g["home"]][0],
            "status": "final" if done else ("final, box score not published" if g["status"] == 3 else
                                            "in progress" if g["status"] == 2 else "not started"),
            "status_text": g["status_text"], "source": g["source"],
            "away_score": a if done else None, "home_score": h if done else None,
            "final_at": g["final_at"], "nba_game_id": g["nba_game_id"], "espn_event_id": g["espn_event_id"],
            "url": (NBA_BOX_URL.format(g["nba_game_id"]) if g["source"] == "nba"
                    else ESPN_GAME_URL.format(g["espn_event_id"]) if g["source"] == "espn" else None),
            "problems": g["problems"],
        })
    meta = {"date": day, "games": len(games), "final": final, "pending": len(games) - final,
            "problems": sum(1 for g in games if g["problems"]),
            "sources": sorted({g["source"] for g in games if g["source"]}), "list": entries}
    old = read_meta(folder)
    if old:
        old.pop("updated_at", None)
    if changed or old != meta:
        meta = {"date": day, "updated_at": iso(utc_now()), **{k: v for k, v in meta.items() if k != "date"}}
        with open(os.path.join(folder, "source.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
            f.write("\n")
        changed = True
    if not games:
        return changed, f"{day}: no games"
    src = "+".join(meta["sources"]) or "-"
    return changed, (f"{day}: {final}/{len(games)} final ({src})"
                     + (f", {meta['problems']} with check problems" if meta["problems"] else ""))


def default_dates(now=None):
    """Last night (the US Eastern date of games that ended in the past hours) and the night before."""
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(ET)
    last = (now - dt.timedelta(hours=8)).date()
    return [str(last), str(last - dt.timedelta(days=1))]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default="data/raw", help="output folder (default: data/raw)")
    ap.add_argument("--dates", help="comma separated US game dates YYYY-MM-DD (default: last night and the night before)")
    ap.add_argument("--source", choices=("auto", "nba", "espn"), default="auto",
                    help="auto = NBA.com, ESPN where NBA.com fails (default)")
    ap.add_argument("--refetch", action="store_true", help="read final games again even if already saved")
    ap.add_argument("--summary", help="append one summary line per changed date to this file")
    ap.add_argument("--debug", action="store_true", help="log per-game details")
    args = ap.parse_args(argv)
    dates = [d.strip() for d in args.dates.split(",") if d.strip()] if args.dates else default_dates()
    for d in dates:
        dt.date.fromisoformat(d)
    now = utc_now()
    for d in dates:
        log(f"{d}:")
        folder = os.path.join(args.out, d)
        prev = None if args.refetch else read_meta(folder)
        if prev and prev.get("list") and all(settled(g, folder, now) for g in prev["list"]):
            log("  all games final and saved, not fetched again")
            continue
        games, err = collect(d, args.source, prev, folder, now, args.debug)
        if games is None:
            # A warning, not a failed run: scheduled runs every 30 minutes would mail a failure
            # each time, and the morning job falls back to Basketball-Reference anyway.
            print(f"::warning::{d}: no source answered ({err})", flush=True)
            continue
        changed, line = write_day(args.out, d, games)
        for g in games:
            for p in g["problems"]:
                log(f"  CHECK {g['boxid']}: {p}")
        log(f"  {line}{'' if changed else ' (unchanged)'}")
        if changed and args.summary:
            with open(args.summary, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
