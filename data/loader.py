import pandas as pd
import streamlit as st

CSV_PATH = "data/processed/nfl_plays_slim.csv"

@st.cache_data(show_spinner="Cargando datos NFL...")
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    return df

def filter_data(
    df: pd.DataFrame,
    teams: list,
    concepts: list,
    coverages: list,
    formation: str,
    downs: list,
    seasons: list,
    weeks: list,
    defteam: str,
    def_formation: str,
) -> pd.DataFrame:
    filtered = df.copy()

    if teams:
        filtered = filtered[filtered["posteam"].isin(teams)]
    if concepts:
        filtered = filtered[filtered["concept"].isin(concepts)]
    if coverages:
        filtered = filtered[filtered["coverage"].isin(coverages)]
    if formation and formation != "All":
        filtered = filtered[filtered["formation_label"] == formation]
    if downs:
        filtered = filtered[filtered["down"].isin(downs)]
    if seasons:
        filtered = filtered[filtered["season"].isin(seasons)]
    if weeks:
        filtered = filtered[filtered["week"].isin(weeks)]
    if defteam and defteam != "All":
        filtered = filtered[filtered["defteam"] == defteam]
    if def_formation and def_formation != "All":
        filtered = filtered[filtered["def_formation"] == def_formation]

    return filtered.reset_index(drop=True)