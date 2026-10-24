## NBA.com fetch via GitHub (regular season, from 2026-10-24)
Mert asked on 2026-10-24 to read box scores from NBA.com instead of Basketball-Reference, which posts
them up to a day late. curl to NBA.com/ESPN is blocked here and WebFetch drops rows, so a GitHub Actions
job in Mert's public repo meker/P1 reads NBA.com's box score JSON (ESPN where NBA.com fails) every
20 minutes from 01:07 to 09:47 UTC and commits it in this pipeline's raw format under data/raw/D/
(same games.txt and <boxid>.txt files, Basketball-Reference style ids). No subagent, no WebFetch:
1. `rm -rf /home/claude/p1 && git clone -q --depth 1 https://github.com/meker/P1 /home/claude/p1`
   If git cannot reach GitHub, call add_repo (owner meker, repo P1, access read) and run the clone
   command it returns into /home/claude/p1.
2. `head -c 2000 /home/claude/p1/data/raw/D/source.json` shows final/pending games, sources and
   self-check problems. games.txt = NO_GAMES means there were no games.
3. `cd /mnt/project-files/daily-report && mkdir -p raw/D && cp /home/claude/p1/data/raw/D/*.txt raw/D/`
   (overwrites older Basketball-Reference files of the same games), then the usual --check and build.
Pending games ("not final" lines) refresh in the repo every 20 minutes until 09:47 UTC: the follow-up run
repeats steps 1-3. Only if GitHub cannot be reached or data/raw/D/ is missing, fall back to the
Basketball-Reference "Fetch instructions" below and say so in one clause of the reply.
