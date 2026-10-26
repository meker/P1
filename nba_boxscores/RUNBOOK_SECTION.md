## NBA.com fetch via GitHub (regular season, from 2026-10-24)
Mert asked on 2026-10-24 to read box scores from NBA.com instead of Basketball-Reference, which posts
them up to a day late. curl to NBA.com/ESPN is blocked here and WebFetch drops rows, so a GitHub Actions
job in Mert's public repo meker/P1 reads NBA.com's official box scores (ESPN where NBA.com fails) every
30 minutes from 01:00 to 09:30 UTC and commits them in this pipeline's raw format under data/raw/D/
(same games.txt and <boxid>.txt files, Basketball-Reference style ids). No subagent, no WebFetch:
1. `rm -rf /home/claude/p1 && git clone -q --depth 1 https://github.com/meker/P1 /home/claude/p1`
   If git cannot reach GitHub, call add_repo (owner meker, repo P1, access read) and run the clone
   command it returns into /home/claude/p1.
2. `head -c 2000 /home/claude/p1/data/raw/D/source.json` shows final/pending games, sources and
   self-check problems. games.txt = NO_GAMES means both NBA.com's games page and ESPN's scoreboard list
   no games that night: no Basketball-Reference check needed.
3. `cd /mnt/project-files/daily-report && mkdir -p raw/D && cp /home/claude/p1/data/raw/D/*.txt raw/D/`
   (overwrites older Basketball-Reference files of the same games), then the usual --check and build.
   Games with source "espn" in source.json have whole-minute MP (Mert is fine with that, 2026-10-24): a
   --check minutes mismatch of up to 3 on them is rounding, not a missing player; don't retry or report it.
Pending games ("not final" lines) refresh in the repo every 30 minutes until 09:30 UTC: the follow-up run
repeats steps 1-3.
Fallbacks, each named in one clause of the reply:
- No clone works: ONE subagent WebFetches https://raw.githubusercontent.com/meker/P1/HEAD/data/raw/D/games.txt
  and every box file it lists (<boxid>.txt, the box URL's file name) with the prompt "Return this file's
  text exactly, byte for byte, no commentary", writes each verbatim to raw/D/ and runs --check.
- data/raw/D/ does not exist on GitHub (the Actions job stopped): the Basketball-Reference
  "Fetch instructions" below.
