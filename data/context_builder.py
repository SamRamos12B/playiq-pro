import pandas as pd

def build_scout_context(filtros: dict, df: pd.DataFrame) -> str:
    if df.empty:
        return "No hay datos disponibles para los filtros seleccionados."

    total_plays  = len(df)
    epa_avg      = round(df["epa"].mean(), 3) if "epa" in df.columns else "N/A"
    success_rate = round((df["epa"] > 0).mean() * 100, 1) if "epa" in df.columns else "N/A"
    yards_avg    = round(df["yards_gained"].mean(), 1) if "yards_gained" in df.columns else "N/A"

    # Contexto táctico enriquecido
    top_concepts = (
        df.groupby("concept")["epa"].mean()
        .nlargest(3).round(3).to_dict()
        if "concept" in df.columns else {}
    )
    top_coverages = (
        df.groupby("coverage")["epa"].mean()
        .nlargest(3).round(3).to_dict()
        if "coverage" in df.columns else {}
    )
    top_matchups = (
        df.groupby(["concept", "coverage"])["epa"].mean()
        .nlargest(3).round(3).to_dict()
        if all(c in df.columns for c in ["concept", "coverage"]) else {}
    )
    third_down = (
        df[df["down"] == 3]["epa"].mean()
        if "down" in df.columns else None
    )

    active = []
    if filtros.get("teams"):
        active.append(f"Equipo(s): {', '.join(filtros['teams'])}")
    if filtros.get("concepts"):
        active.append(f"Concepto(s): {', '.join(filtros['concepts'])}")
    if filtros.get("coverages"):
        active.append(f"Cobertura(s): {', '.join(filtros['coverages'])}")
    if filtros.get("downs"):
        active.append(f"Down(s): {filtros['downs']}")

    return f"""
Eres PlayIQ Scout, un analista experto en táctica y estadísticas de la NFL.
Respondes de forma concisa, directa y táctica. Máximo 3 párrafos.
Usa datos concretos cuando puedas.

=== CONTEXTO DEL DASHBOARD ===

Filtros activos: {', '.join(active) if active else 'Ninguno (dataset completo)'}

Estadísticas generales:
- Total jugadas: {total_plays:,}
- EPA promedio: {epa_avg}
- Success rate (EPA > 0): {success_rate}%
- Yardas promedio: {yards_avg}

Análisis táctico:
- Top 3 conceptos por EPA: {top_concepts}
- Top 3 coberturas por EPA: {top_coverages}
- Top 3 matchups concepto/cobertura: {top_matchups}
- EPA en 3rd down: {round(third_down, 3) if third_down else 'N/A'}

=== FIN DE CONTEXTO ===

Responde la pregunta basándote en estos datos. Si la pregunta va
más allá de los datos disponibles, indícalo y responde con tu
conocimiento general de NFL.
"""