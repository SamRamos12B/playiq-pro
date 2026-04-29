import pandas as pd

MIN_PLAYS = 5


def concept_performance(df):

    result = (
        df.groupby("concept")
        .agg(
            plays=("concept", "count"),
            avg_yards=("yards_gained", "mean"),
            avg_epa=("epa", "mean"),
            success_rate=("epa", lambda x: (x > 0).mean()),
        )
        .query(f"plays >= {MIN_PLAYS}")
        .sort_values("avg_epa", ascending=False)
        .round({"avg_yards": 2, "avg_epa": 3, "success_rate": 3})
    )

    return result


def concept_vs_coverage(df):

    result = (
        df[df["coverage"] != "Unknown"]
        .groupby(["concept", "coverage"])
        .agg(
            plays=("concept", "count"),
            avg_epa=("epa", "mean"),
            avg_yards=("yards_gained", "mean"),
            success_rate=("epa", lambda x: (x > 0).mean()),
        )
        .reset_index()
        .query(f"plays >= {MIN_PLAYS}")
        .sort_values("avg_epa", ascending=False)
        .round({"avg_yards": 2, "avg_epa": 3, "success_rate": 3})
    )

    return result


def formation_vs_formation(df):

    if "def_formation" not in df.columns:
        return pd.DataFrame()

    result = (
        df.groupby(["formation_label", "def_formation"])
        .agg(
            plays=("concept", "count"),
            avg_epa=("epa", "mean"),
            avg_yards=("yards_gained", "mean"),
            success_rate=("epa", lambda x: (x > 0).mean()),
        )
        .reset_index()
        .query(f"plays >= {MIN_PLAYS}")
        .sort_values("avg_epa", ascending=False)
        .round({"avg_yards": 2, "avg_epa": 3, "success_rate": 3})
    )

    return result


def third_down_analysis(df):

    third_down = df[df["down"] == 3].copy()

    if third_down.empty:
        return pd.DataFrame()

    third_down["converted"] = (
        third_down["yards_gained"] >= third_down["ydstogo"].fillna(0)
    )

    result = (
        third_down.groupby("concept")
        .agg(
            plays=("concept", "count"),
            avg_epa=("epa", "mean"),
            avg_yards=("yards_gained", "mean"),
            success_rate=("epa", lambda x: (x > 0).mean()),
            conversion_rate=("converted", "mean"),
        )
        .query(f"plays >= {MIN_PLAYS}")
        .sort_values("avg_epa", ascending=False)
        .round({"avg_yards": 2, "avg_epa": 3, "success_rate": 3, "conversion_rate": 3})
    )

    return result