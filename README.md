# NBA box scores for the daily fantasy report

Data source for the "NBA Sabah Raporu" morning report (Yahoo NBA Fantasy Draft Helper project).
Basketball-Reference posts box scores up to a day late, so a GitHub Actions job reads them from
NBA.com instead, minutes after each game ends, and commits them here.

- `nba_boxscores/fetch.py` reads NBA.com's official box scores from the public www.nba.com pages
  (the night's games page and each game's box score page carry them as page data; `cdn.nba.com`'s JSON
  answers "Access Denied" to cloud runners). ESPN's API is the fallback for a game NBA.com cannot serve.
  A final game is re-read for an hour (stat corrections), then left alone. Standard library only.
- `.github/workflows/nba-boxscores.yml` runs it every 30 minutes from 01:00 to 09:30 UTC (04:00-12:30
  Turkey time) for last night and the night before, and commits only when data changed. GitHub starts
  scheduled runs late or skips them, so it also runs on demand: a commit named `fetch <dates> [refetch]`
  pushed to the `fetch-now` branch starts it within seconds for those dates (the morning report does this
  when last night is not complete yet). By hand: Actions tab, "Run workflow" (optional dates such as
  `2026-10-22,2026-10-23`).
- `data/raw/<YYYY-MM-DD>/` holds one US game night in the report pipeline's raw format:
  - `games.txt`: `visitor|pts|home|pts|box URL|final`, scores empty and `not final` while a game
    is unfinished, or the single line `NO_GAMES`;
  - `<boxid>.txt`: Basketball-Reference style TSV box score (starters, reserves, DNP rows, Team Totals).
    Ids and URLs keep Basketball-Reference's form (`202610230MIL`) so `build_day.py` reads them unchanged;
  - `source.json`: per game status, source (nba/espn), NBA.com game id and link, self-check problems.
    ESPN minutes are whole minutes, so a team's minutes can be a minute or two off 240 there.
- `nba_boxscores/RUNBOOK_SECTION.md`: the fetch steps the morning job follows. `nba_boxscores/HEARTH_SETUP.md`
  and `nba_boxscores/HEARTH_ON_DEMAND.md`: one-time changes the report thread applied (the switch to NBA.com,
  then the on-demand request).

Tests: `python3 -m unittest nba_boxscores/test_fetch.py`

GitHub pauses scheduled workflows of a public repo after 60 days without commits (for example over the
summer). Re-enable it from the Actions tab before the next season.
