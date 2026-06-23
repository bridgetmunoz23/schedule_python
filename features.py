# builds the rest / travel / opponent features off the schedule

from __future__ import annotations

import numpy as np
import pandas as pd


def _rolling_count_in_window(dates: pd.Series, window_days: int) -> pd.Series:
    # games played in the last window_days days, per date
    s = pd.Series(1, index=pd.DatetimeIndex(dates))
    counts = s.rolling(f"{window_days}D").sum()
    return counts.values.astype(int)


def _add_rest(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["season", "team", "gamedate"]).copy()
    grp = out.groupby(["season", "team"], sort=False)
    out["rest_days"] = grp["gamedate"].diff().dt.days
    out["is_b2b"] = (out["rest_days"] == 1).astype(int)
    # rolling game counts for the 4-in-6 / 3-in-4 flags
    counts_6 = grp["gamedate"].transform(lambda s: _rolling_count_in_window(s, 6))
    counts_4 = grp["gamedate"].transform(lambda s: _rolling_count_in_window(s, 4))
    out["is_4in6"] = (counts_6 >= 4).astype(int)
    out["is_3in4"] = (counts_4 >= 3).astype(int)
    return out


def _add_travel(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["is_away"] = (1 - out["home"]).astype(int)
    out = out.sort_values(["season", "team", "gamedate"]).reset_index(drop=True)

    # how many away games in a row, resets when they're home
    away = out["is_away"].values
    season_team = (out["season"].astype(str) + "|" + out["team"]).values
    trip = np.zeros(len(out), dtype=int)
    prev_key, run = None, 0
    for i in range(len(out)):
        if season_team[i] != prev_key:
            run = 0
            prev_key = season_team[i]
        run = run + 1 if away[i] else 0
        trip[i] = run
    out["consecutive_away_games"] = trip

    # days since they last played at home (0 if this game is home)
    days_away = np.zeros(len(out), dtype=int)
    last_home = {}
    for i in range(len(out)):
        key = season_team[i]
        if away[i] == 0:
            last_home[key] = out["gamedate"].iloc[i]
            days_away[i] = 0
        else:
            lh = last_home.get(key)
            days_away[i] = 0 if lh is None else (out["gamedate"].iloc[i] - lh).days
    out["days_since_home_game"] = days_away
    return out


def _add_opp_prior_win_pct(df: pd.DataFrame) -> pd.DataFrame:
    # opponent's win pct going into each game
    out = df.sort_values(["season", "team", "gamedate"]).copy()
    grp = out.groupby(["season", "team"], sort=False)
    prior_wins = grp["win"].cumsum() - out["win"]
    prior_games = grp.cumcount()
    out["_prior_win_pct"] = np.where(
        prior_games > 0, prior_wins / prior_games, np.nan
    )
    # grab the opponent's own prior_win_pct by merging on the same game
    lookup = out[["season", "team", "gamedate", "_prior_win_pct"]].rename(
        columns={"team": "opponent", "_prior_win_pct": "opp_prior_win_pct"}
    )
    merged = out.merge(lookup, on=["season", "opponent", "gamedate"], how="left")
    merged = merged.drop(columns="_prior_win_pct")
    return merged.sort_values(["season", "team", "gamedate"]).reset_index(drop=True)


def build_features(schedule: pd.DataFrame) -> pd.DataFrame:
    # run all the feature steps
    out = _add_rest(schedule)
    out = _add_travel(out)
    out = _add_opp_prior_win_pct(out)
    out["is_nonconference"] = out["is_nonconf"]
    return out


if __name__ == "__main__":
    from data import load_schedule

    f = build_features(load_schedule(["2023-24"]))
    print(len(f), "rows")
    print([c for c in f.columns if c not in load_schedule(["2023-24"]).columns])
    feat_cols = ["is_b2b", "is_3in4", "is_4in6", "is_away",
                 "rest_days", "consecutive_away_games", "days_since_home_game",
                 "opp_prior_win_pct"]
    print(f[feat_cols].mean().round(3).to_string())
