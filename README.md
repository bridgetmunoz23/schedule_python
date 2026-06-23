# NBA Schedule Difficulty

A side project on how much an NBA team's schedule (rest, travel, who they play) actually affects whether they win, using public game logs.

Short version: it pulls every regular season game from 2013-14 through 2025-26, builds some rest/travel features, fits a logistic regression to estimate a team's chance of losing each game, and then checks how much the schedule alone moves things. The answer is basically "a little, but team quality matters way more."

The full writeup with the charts is in `analysis.ipynb` (or the cleaned-up `portfolio.html`).

## Files

- `data.py` — pulls + caches the game logs from nba_api
- `features.py` — rest / travel / opponent features
- `model.py` — the logistic model + the "what if the schedule were league-average" comparison
- `analysis.ipynb` — the actual analysis and charts
- `build_portfolio.py` — turns the notebook export into the styled page
- `cache/` — local parquet cache (gitignored, fills in on first run)

## Running it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

First run pulls from nba.com and takes a few minutes. After that everything reads from `cache/` (delete it to refresh).

## Notes

Data is from nba_api (`LeagueGameLog`), regular season only. Team locations are just hardcoded in `data.py`.
