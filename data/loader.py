import nfl_data_py as nfl
import pandas as pd
import streamlit as st

@st.cache_data(ttl=3600, show_spinner="Cargando datos NFL...")
def load_pbp(season: int) -> pd.DataFrame:
    """
    Carga play-by-play de una temporada completa.
    Cache de 1 hora — no recarga en cada interacción del usuario.
    """
    cols = [
        "play_id", "game_id", "home_team", "away_team",
        "posteam", "defteam", "week", "season",
        "play_type", "yards_gained", "epa", "wpa",
        "down", "ydstogo", "yardline_100",
        "pass_attempt", "rush_attempt", "complete_pass",
        "passer_player_name", "rusher_player_name", "receiver_player_name",
        "air_yards", "yards_after_catch",
        "score_differential", "game_seconds_remaining",
        "shotgun", "no_huddle", "qb_dropback",
    ]
    
    try:
        df = nfl.import_pbp_data([season], columns=cols)
        # Limpiar jugadas irrelevantes
        df = df[df["play_type"].isin(["pass", "run", "punt", "field_goal"])]
        df = df.dropna(subset=["epa", "play_type"])
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

def filter_pbp(
    df: pd.DataFrame,
    equipo: str,
    semanas: tuple,
    tipo_play: str,
    lado: str  # "offense" o "defense"
) -> pd.DataFrame:
    """
    Aplica filtros al dataframe cargado.
    Separamos carga y filtrado para aprovechar el caché.
    """
    if df.empty:
        return df

    # Filtro de equipo
    if equipo != "Todos":
        if lado == "Offense":
            df = df[df["posteam"] == equipo]
        else:
            df = df[df["defteam"] == equipo]

    # Filtro de semanas
    df = df[df["week"].between(semanas[0], semanas[1])]

    # Filtro de tipo de jugada
    if tipo_play != "Todas":
        df = df[df["play_type"] == tipo_play]

    return df.reset_index(drop=True)

@st.cache_data(ttl=86400)  # Cache 24 horas
def get_teams(season: int) -> list:
    """Lista de equipos de la temporada."""
    try:
        df = nfl.import_team_desc()
        return sorted(df["team_abbr"].dropna().unique().tolist())
    except:
        # Fallback con equipos hardcodeados
        return [
            "ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE",
            "DAL","DEN","DET","GB","HOU","IND","JAX","KC",
            "LAC","LAR","LV","MIA","MIN","NE","NO","NYG",
            "NYJ","PHI","PIT","SEA","SF","TB","TEN","WAS"
        ]