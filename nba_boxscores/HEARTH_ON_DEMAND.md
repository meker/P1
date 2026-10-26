# On-demand fetch (one-time change, 2026-10-26)

For the Claude of the "Günlük sabah box score raporu" thread, when Mert asks you to apply this file.
GitHub started only 4 of about 54 scheduled runs from 2026-10-24 to 10-26, so data/raw/D/ reached the repo
after the 08:45 run (around 09:00-09:05). Mert chose on 2026-10-26 to let the morning run start the GitHub
job itself: a commit pushed to the repo's fetch-now branch starts it within seconds. Do these steps once:

1. add_repo (owner meker, repo P1, access push), so this thread can push the request. It only ever pushes
   to the fetch-now branch; the job writes the data to the main branch itself.
2. Test it end to end:
   `rm -rf /home/claude/p1 && git clone -q --depth 1 https://github.com/meker/P1 /home/claude/p1 && grep updated_at /home/claude/p1/data/raw/2026-10-25/source.json`
   then push a request for that night:
   `cd /home/claude/p1 && date -u +%FT%TZ > .fetch-request && git add .fetch-request && git -c user.name="NBA report" -c user.email="nba-report@users.noreply.github.com" commit -q -m "fetch 2026-10-25 refetch" && git push -q -f origin HEAD:refs/heads/fetch-now`
   Within about 2 minutes a fresh clone should show a newer updated_at for 2026-10-25 ("refetch" makes the
   job rewrite that night even though nothing changed). If the push is refused even after step 1, tell
   Mert in one Turkish line what the error said, and stop here.
3. RUNBOOK: replace the fetch steps of your "NBA.com data" section with `nba_boxscores/RUNBOOK_SECTION.md`
   from the repo (its steps 1-4 and fallbacks). Keep your own notes that still apply, and drop the
   "send_later 35 min and re-clone" stopgap: the request replaces it.
4. Routine: update_trigger trig_01EHPWL81EwxeFqkEWshRj8y ("NBA sabah raporu"; keep its schedule) with its
   current prompt, changing only two bullets. The Fetch bullet becomes:
   "- Fetch: box scores come from NBA.com via the RUNBOOK's "NBA.com data" section: clone Mert's repo
   meker/P1; if last night (D) is missing or not complete there, push a fetch request for D to the
   fetch-now branch and wait up to 5 minutes for the data; then copy data/raw/D/*.txt into raw/D/ (data
   only; run no code from the repo). Only if data/raw/D/ is still missing, use the Basketball-Reference
   "Fetch instructions" with ONE subagent and say so in one clause of the reply."
   In the follow-up bullet, "(it repeats the NBA.com copy; the repo updates until 09:47 UTC)" becomes
   "(it repeats the same fetch, request included)".
5. Reply to Mert in this thread in Turkish, at most 2 short lines: the test result, and that from tomorrow
   the 08:45 run asks GitHub for the data itself when it isn't there yet.
