import pandas as pd

def build_scout_context(filtros: dict, df: pd.DataFrame) -> str:
    """
    Construye el contexto que le pasamos a Claude.
    Toma los filtros activos y un resumen del dataframe actual.
    """
    if df.empty:
        return "No hay datos disponibles para los filtros seleccionados."

    # Métricas clave del dataframe actual
    total_plays = len(df)
    
    # EPA (Expected Points Added) — métrica central en NFL analytics
    epa_summary = {}
    if "epa" in df.columns:
        epa_summary = {
            "promedio": round(df["epa"].mean(), 3),
            "total":    round(df["epa"].sum(), 3),
            "top_5_jugadas": df.nlargest(5, "epa")[
                ["play_type", "yards_gained", "epa", "down", "ydstogo"]
            ].to_dict("records") if all(
                c in df.columns for c in ["play_type", "yards_gained", "epa", "down", "ydstogo"]
            ) else []
        }

    # Distribución de tipos de jugada
    play_dist = {}
    if "play_type" in df.columns:
        play_dist = df["play_type"].value_counts().head(5).to_dict()

    # Yardas promedio
    yards_avg = round(df["yards_gained"].mean(), 1) if "yards_gained" in df.columns else "N/A"

    # Success rate (EPA > 0)
    success_rate = None
    if "epa" in df.columns:
        success_rate = round((df["epa"] > 0).mean() * 100, 1)

    context = f"""
Eres PlayIQ Scout, un analista experto en táctica y estadísticas de la NFL.
Respondes de forma concisa, directa y con perspectiva táctica real.
Máximo 3 párrafos por respuesta. Usa datos concretos cuando puedas.

=== CONTEXTO ACTUAL DEL DASHBOARD ===

Filtros activos:
- Equipo: {filtros.get('equipo', 'Todos')}
- Temporada: {filtros.get('temporada', 'N/A')}
- Semanas: {filtros.get('semanas', 'Todas')}
- Tipo de jugada: {filtros.get('tipo_play', 'Todas')}

Datos en pantalla:
- Total de jugadas analizadas: {total_plays}
- Yardas promedio por jugada: {yards_avg}
- EPA promedio: {epa_summary.get('promedio', 'N/A')}
- Success rate (EPA > 0): {success_rate}%
- Distribución de jugadas: {play_dist}
- Top 5 jugadas por EPA: {epa_summary.get('top_5_jugadas', [])}

=== FIN DE CONTEXTO ===

Responde la pregunta del usuario basándote en estos datos.
Si la pregunta va más allá de los datos disponibles, indícalo brevemente
y responde con tu conocimiento general de NFL.
"""
    return context