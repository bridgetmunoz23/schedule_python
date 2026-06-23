# logistic model for schedule difficulty (SDS = predicted prob of losing a game)
# also has the "what if the schedule were league-average" wins counterfactual

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

NUMERIC_FEATURES = [
    "rest_days",
    "consecutive_away_games",
    "days_since_home_game",
    "opp_prior_win_pct",
]
BINARY_FEATURES = [
    "is_b2b",
    "is_3in4",
    "is_4in6",
    "is_away",
    "is_nonconference",
]
ALL_FEATURES = NUMERIC_FEATURES + BINARY_FEATURES

# the schedule-only features we swap for league means in the counterfactual
# (opp_prior_win_pct stays put, since you can't reschedule who plays whom)
SCHEDULE_FEATURES = [
    "rest_days",
    "consecutive_away_games",
    "days_since_home_game",
    "is_b2b",
    "is_3in4",
    "is_4in6",
    "is_away",
    "is_nonconference",
]


def _make_pipeline() -> Pipeline:
    return Pipeline([
        ("ct", ColumnTransformer([
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("bin", "passthrough", BINARY_FEATURES),
        ])),
        ("clf", LogisticRegression(max_iter=2000, C=1.0)),
    ])


def train_sds_model(features: pd.DataFrame, train_seasons: list[str]) -> Pipeline:
    train = features[features["season"].isin(train_seasons)].dropna(subset=ALL_FEATURES + ["win"])
    X = train[ALL_FEATURES]
    y = (1 - train["win"]).astype(int)  # 1 = loss
    if len(train) == 0:
        raise RuntimeError(f"No training data in seasons {train_seasons}")
    model = _make_pipeline()
    model.fit(X, y)
    return model


def score_sds(model: Pipeline, features: pd.DataFrame) -> pd.DataFrame:
    out = features.copy()
    mask = out[ALL_FEATURES].notna().all(axis=1)
    out["SDS"] = np.nan
    if mask.any():
        probs = model.predict_proba(out.loc[mask, ALL_FEATURES])[:, 1]
        out.loc[mask, "SDS"] = probs
    return out


def coefficient_table(model: Pipeline) -> pd.DataFrame:
    # coefficients + odds ratios, sorted by size
    clf = model.named_steps["clf"]
    coefs = clf.coef_[0]
    return (
        pd.DataFrame({"feature": ALL_FEATURES, "coef": coefs})
        .assign(odds_ratio=lambda d: np.exp(d["coef"]))
        .sort_values("coef", key=abs, ascending=False)
        .reset_index(drop=True)
    )


def schedule_driven_wins(
    model: Pipeline,
    features: pd.DataFrame,
    seasons: list[str],
    league_means: dict | None = None,
) -> pd.DataFrame:
    # per team-season: expected wins on the real schedule minus a league-average one
    df = features[features["season"].isin(seasons)].dropna(subset=ALL_FEATURES).copy()
    if league_means is None:
        league_means = df[SCHEDULE_FEATURES].mean().to_dict()

    actual = df[ALL_FEATURES].copy()
    neutral = df[ALL_FEATURES].copy()
    for col, val in league_means.items():
        neutral[col] = val

    p_loss_actual = model.predict_proba(actual)[:, 1]
    p_loss_neutral = model.predict_proba(neutral)[:, 1]
    df["exp_wins_actual"] = 1 - p_loss_actual
    df["exp_wins_neutral"] = 1 - p_loss_neutral
    df["schedule_wins"] = df["exp_wins_actual"] - df["exp_wins_neutral"]

    return (
        df.groupby(["season", "team"])
          .agg(
              games=("schedule_wins", "size"),
              exp_wins_actual=("exp_wins_actual", "sum"),
              exp_wins_neutral=("exp_wins_neutral", "sum"),
              schedule_wins=("schedule_wins", "sum"),
          )
          .reset_index()
          .sort_values("schedule_wins", ascending=False)
    )


if __name__ == "__main__":
    from data import load_schedule, DEFAULT_SEASONS
    from features import build_features

    feats = build_features(load_schedule(DEFAULT_SEASONS))

    train_seasons = DEFAULT_SEASONS[:-1]      # everything but the latest season
    score_season = DEFAULT_SEASONS[-1]

    model = train_sds_model(feats, train_seasons)

    print("\nCoefficient table (standardized numeric features):")
    print(coefficient_table(model).to_string(index=False))

    print(f"\nScoring {score_season}...")
    scored = score_sds(model, feats[feats["season"] == score_season])
    print(f"  rows scored: {scored['SDS'].notna().sum():,}")
    print(f"  SDS mean: {scored['SDS'].mean():.3f}, std: {scored['SDS'].std():.3f}")

    print(f"\nSchedule-driven wins over 2019-20 through {score_season}:")
    window = [s for s in DEFAULT_SEASONS if s >= "2019-20"]
    sched_wins = schedule_driven_wins(model, feats, window)
    print("Most helped by schedule:")
    print(sched_wins.head(5).to_string(index=False))
    print("\nMost hurt by schedule:")
    print(sched_wins.tail(5).to_string(index=False))
