# grabs nba game logs from nba_api and caches them so I don't re-pull every time
# delete the cache folder to refresh

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import LeagueGameLog

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

DEFAULT_SEASONS = [f"{y}-{str(y + 1)[-2:]}" for y in range(2013, 2026)]

TEAM_CONFERENCE = {
    "ATL": "East", "BOS": "East", "BKN": "East", "CHA": "East", "CHI": "East",
    "CLE": "East", "DET": "East", "IND": "East", "MIA": "East", "MIL": "East",
    "NYK": "East", "ORL": "East", "PHI": "East", "TOR": "East", "WAS": "East",
    "DAL": "West", "DEN": "West", "GSW": "West", "HOU": "West", "LAC": "West",
    "LAL": "West", "MEM": "West", "MIN": "West", "NOP": "West", "OKC": "West",
    "PHX": "West", "POR": "West", "SAC": "West", "SAS": "West", "UTA": "West",
    "NOH": "West",  # historical alias for NOP
}

TEAM_LOCATION = {
    "ATL": (33.7573, -84.3963), "BOS": (42.3662, -71.0621),
    "BKN": (40.6826, -73.9754), "CHA": (35.2251, -80.8392),
    "CHI": (41.8807, -87.6742), "CLE": (41.4965, -81.6882),
    "DAL": (32.7905, -96.8104), "DEN": (39.7487, -105.0077),
    "DET": (42.3411, -83.0553), "GSW": (37.7680, -122.3877),
    "HOU": (29.7508, -95.3621), "IND": (39.7639, -86.1555),
    "LAC": (34.0430, -118.2673), "LAL": (34.0430, -118.2673),
    "MEM": (35.1382, -90.0506), "MIA": (25.7814, -80.1870),
    "MIL": (43.0451, -87.9173), "MIN": (44.9795, -93.2761),
    "NOP": (29.9490, -90.0820), "NOH": (29.9490, -90.0820),
    "NYK": (40.7505, -73.9934), "OKC": (35.4634, -97.5151),
    "ORL": (28.5392, -81.3839), "PHI": (39.9012, -75.1720),
    "PHX": (33.4457, -112.0712), "POR": (45.5316, -122.6668),
    "SAC": (38.6491, -121.5181), "SAS": (29.4271, -98.4375),
    "TOR": (43.6435, -79.3791), "UTA": (40.7683, -111.9011),
    "WAS": (38.8981, -77.0210),
}


def _cache_path(name: str) -> Path:
    return CACHE_DIR / f"{name}.parquet"


def _pull_season(season: str) -> pd.DataFrame:
    cache = _cache_path(f"gamelog_{season}")
    if cache.exists():
        return pd.read_parquet(cache)
    for attempt in range(3):
        try:
            df = LeagueGameLog(
                season=season,
                season_type_all_star="Regular Season",
                timeout=60,
            ).get_data_frames()[0]
            df.to_parquet(cache, index=False)
            time.sleep(0.6)
            return df
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _raw_logs(seasons=DEFAULT_SEASONS) -> pd.DataFrame:
    frames = [_pull_season(s).assign(season=s) for s in seasons]
    return pd.concat(frames, ignore_index=True)


def load_schedule(seasons=DEFAULT_SEASONS) -> pd.DataFrame:
    raw = _raw_logs(seasons)
    # MATCHUP looks like "OKC vs. DEN" (home) or "OKC @ DEN" (away)
    parts = raw["MATCHUP"].str.split(r"\s+(vs\.|@)\s+", regex=True, expand=True)
    raw["home"] = (parts[1] == "vs.").astype(int)
    raw["opponent"] = parts[2]
    df = pd.DataFrame({
        "gamedate": pd.to_datetime(raw["GAME_DATE"]),
        "season": raw["season"],
        "team": raw["TEAM_ABBREVIATION"],
        "opponent": raw["opponent"],
        "home": raw["home"],
        "win": (raw["WL"] == "W").astype(int),
    })
    df["conference"] = df["team"].map(TEAM_CONFERENCE)
    df["opp_conference"] = df["opponent"].map(TEAM_CONFERENCE)
    df["is_nonconf"] = (df["conference"] != df["opp_conference"]).astype(int)
    df = df.sort_values(["season", "team", "gamedate"]).reset_index(drop=True)
    df["game_number"] = df.groupby(["season", "team"]).cumcount() + 1
    return df


def load_game_data(seasons=DEFAULT_SEASONS) -> pd.DataFrame:
    raw = _raw_logs(seasons)
    base = raw[["GAME_ID", "TEAM_ABBREVIATION", "FGM", "FGA", "FG3M",
                "GAME_DATE", "season"]].copy()
    base.columns = ["game_id", "team", "fgm", "fga", "fg3m", "gamedate", "season"]
    base["gamedate"] = pd.to_datetime(base["gamedate"])
    opp = base[["game_id", "team", "fgm", "fga", "fg3m"]].rename(columns={
        "team": "opp_team", "fgm": "opp_fgm", "fga": "opp_fga", "fg3m": "opp_fg3m",
    })
    merged = base.merge(opp, on="game_id")
    merged = merged[merged["team"] != merged["opp_team"]]
    out = pd.DataFrame({
        "gamedate": merged["gamedate"],
        "season": merged["season"],
        "def_team": merged["team"],
        "opp_team": merged["opp_team"],
        "fgmade": merged["opp_fgm"],
        "fg3made": merged["opp_fg3m"],
        "fgattempted": merged["opp_fga"],
    })
    return out.sort_values(["season", "def_team", "gamedate"]).reset_index(drop=True)


def load_locations() -> pd.DataFrame:
    return pd.DataFrame(
        [(t, lat, lon) for t, (lat, lon) in TEAM_LOCATION.items()],
        columns=["team", "lat", "lon"],
    )


if __name__ == "__main__":
    # quick check on one season
    s = load_schedule(["2023-24"])
    print(len(s), "rows", list(s.columns))
    print(s.head().to_string(index=False))
