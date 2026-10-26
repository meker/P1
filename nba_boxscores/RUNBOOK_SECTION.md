## NBA.com fetch via GitHub (regular season, from 2026-10-24)
Mert asked on 2026-10-24 to read box scores from NBA.com instead of Basketball-Reference, which posts
them up to a day late. curl to NBA.com/ESPN is blocked here and WebFetch drops rows, so a GitHub Actions
job in Mert's public repo meker/P1 reads NBA.com's official box scores (ESPN where NBA.com fails) and
commits them in this pipeline's raw format under data/raw/D/ (same games.txt and <boxid>.txt files,
Basketball-Reference style ids). It runs on a schedule (every 30 minutes, 01:00-09:30 UTC), but GitHub
starts scheduled runs late or skips them (2026-10-25/26 the data came only at ~06:00 UTC), so this run asks
for the job itself when last night is not complete. No subagent, no WebFetch, no code from the repo is run:
1. `rm -rf /home/claude/p1 && git clone -q --depth 1 https://github.com/meker/P1 /home/claude/p1`
2. Ready check, exit 0 = every game of D is final (a night without games counts as ready):
   `python3 -c "import json,sys; m=json.load(open('/home/claude/p1/data/raw/D/source.json')); print(m['updated_at'], m['final'], 'of', m['games'], 'final'); sys.exit(m['pending'] > 0)"`
3. Not ready (exit 1, or no source.json yet): ask the job for D and wait for it.
   `cd /home/claude/p1 && date -u +%FT%TZ > .fetch-request && git add .fetch-request && git -c user.name="NBA report" -c user.email="nba-report@users.noreply.github.com" commit -q -m "fetch D" && git push -q -f origin HEAD:refs/heads/fetch-now`
   This pushes one commit to the fetch-now branch (never to the main branch); the job starts within seconds
   and commits D to the main branch about a minute later. If the push is refused, call add_repo (owner meker,
   repo P1, access push) and push again. Several nights: "fetch D1 D2".
   Then repeat steps 1-2 every 20 seconds for up to 5 minutes (Bash timeout 400000), stopping at exit 0:
   `for i in $(seq 1 15); do sleep 20; rm -rf /home/claude/p1 && git clone -q --depth 1 https://github.com/meker/P1 /home/claude/p1 && python3 -c "<step 2>" && break; done`
   Games still not final after that are really unfinished, or NBA.com and ESPN have not posted them: go on.
4. `cd /mnt/project-files/daily-report && mkdir -p raw/D && cp /home/claude/p1/data/raw/D/*.txt raw/D/`
   (overwrites older Basketball-Reference files of the same games), then the usual --check and build.
   games.txt = NO_GAMES means both NBA.com's games page and ESPN's scoreboard list no games that night: no
   Basketball-Reference check needed. Games with source "espn" in source.json have whole-minute MP (Mert is
   fine with that, 2026-10-24): a --check minutes mismatch of up to 3 on them is rounding, not a missing
   player; don't retry or report it.
Pending games ("not final" lines): the follow-up run repeats steps 1-4, request included.
Fallbacks, each named in one clause of the reply:
- No clone works: ONE subagent WebFetches https://raw.githubusercontent.com/meker/P1/HEAD/data/raw/D/games.txt
  and every box file it lists (<boxid>.txt, the box URL's file name) with the prompt "Return this file's
  text exactly, byte for byte, no commentary", writes each verbatim to raw/D/ and runs --check.
- data/raw/D/ still missing after the request (the GitHub job is broken): the Basketball-Reference
  "Fetch instructions" below.
