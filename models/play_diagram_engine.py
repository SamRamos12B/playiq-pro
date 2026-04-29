import math
import plotly.graph_objects as go

ROUTE_COLORS = ["#29B6F6", "#FF7043", "#66BB6A", "#CE93D8", "#FFA726", "#26C6DA"]

_DOWN_SUFFIX = {1: "st", 2: "nd", 3: "rd"}

# ── Position classification ────────────────────────────────────────────────
_DL_POS  = {"DE", "DT", "NT"}
_LB_POS  = {"LB", "MLB", "ILB", "OLB", "LOLB", "ROLB", "SAM", "WILL", "MIKE"}
_CB_POS  = {"CB"}
_S_POS   = {"S", "SS", "FS", "SAF"}
_RB_POS  = {"RB", "HB", "FB"}
_NOT_DEF = {"QB", "WR", "TE", "C", "G", "T", "OT", "OG", "K", "P", "LS",
            "RB", "HB", "FB", "SWR"}

# Each route is a list of (x, y) waypoints.
# x = yards from line of scrimmage (depth), y = field width (left/right)
ROUTES = {
    "Mesh": [
        [(0, 0),  (20, 0)],
        [(0, 10), (20, 10)],
    ],
    "Flood": [
        [(0, 0),  (30, 10)],
        [(0, 5),  (20, 5)],
        [(0, -5), (10, -5)],
    ],
    "Four Verticals": [
        [(0, 10), (34, 10)],
        [(0, 5),  (34, 5)],
        [(0, 0),  (34, 0)],
        [(0, -5), (34, -5)],
    ],
    "Slants": [
        [(0, 10),  (15, 5)],
        [(0, -10), (15, -5)],
    ],
    "Stick": [
        [(0, 5),  (10, 5)],
        [(0, -5), (10, -5)],
    ],
    "Drive": [
        [(0, 0),  (20, 0)],
        [(0, -5), (10, -5)],
    ],
    "Levels": [
        [(0, 5),  (20, 5)],
        [(0, 10), (30, 10)],
    ],
    "Smash": [
        [(0, 10), (30, 10)],
        [(0, 5),  (10, 5)],
    ],
    "Curl Flat": [
        [(0, 10), (15, 10), (10, 10)],
        [(0, -5), (5, -5)],
    ],
    "Screen": [
        [(0, 0), (5, 0)],
    ],
}


def _val(play, key, default=None):
    """Safe getter that treats NaN as missing."""
    v = play.get(key, default)
    try:
        if math.isnan(v):
            return default
    except TypeError:
        pass
    return v


def _spread_y(n, max_half=9.0, max_step=3.5):
    """Return n evenly-spaced y-values centered on 0."""
    if n == 0:
        return []
    if n == 1:
        return [0.0]
    step  = min(max_half * 2 / (n - 1), max_step)
    start = -(n - 1) * step / 2
    return [start + i * step for i in range(n)]


def _add_player_at(fig, label, x, y, color, symbol, size=15, textpos="top center"):
    """Offensive player: filled marker + text in one Scatter trace."""
    is_open = "open" in symbol
    fig.add_trace(go.Scatter(
        x=[x], y=[y],
        mode="markers+text",
        marker=dict(
            color="rgba(0,0,0,0)" if is_open else color,
            size=size, symbol=symbol,
            line=dict(color=color, width=2.5),
        ),
        text=[label],
        textposition=textpos,
        textfont=dict(color=color, size=9, family="Arial Black"),
        showlegend=False,
        hovertemplate=f"<b>{label}</b><extra></extra>",
    ))


def _add_def_player(fig, annotations, label, x, y, color):
    """
    Defensive player: open-circle marker (Scatter) + labeled annotation
    with a dark background so the text is legible on the green field.
    The textpos is automatically flipped toward the center of the field.
    """
    fig.add_trace(go.Scatter(
        x=[x], y=[y],
        mode="markers",
        marker=dict(
            color="rgba(0,0,0,0)", size=16, symbol="circle-open",
            line=dict(color=color, width=2.5),
        ),
        showlegend=False,
        hovertemplate=f"<b>{label}</b><extra></extra>",
    ))
    # Place the label toward the center of the field (away from the sideline)
    y_offset = -2.0 if y > 4 else (2.0 if y < -4 else -2.0)
    annotations.append(dict(
        x=x, y=y + y_offset,
        text=f"<b>{label}</b>",
        showarrow=False,
        font=dict(color=color, size=9, family="Arial Black"),
        bgcolor="rgba(15,35,15,0.80)",
        borderpad=2,
        xanchor="center",
        yanchor="middle",
    ))


def _target_route_index(routes, pass_location):
    """Return the route index most likely targeted given pass_location."""
    if not routes or not pass_location:
        return None
    if pass_location == "right":
        return max(range(len(routes)), key=lambda i: routes[i][0][1])
    if pass_location == "left":
        return min(range(len(routes)), key=lambda i: routes[i][0][1])
    if pass_location == "middle":
        return min(range(len(routes)), key=lambda i: abs(routes[i][0][1]))
    return None


def _classify_routes(routes, te_count):
    """
    Routes with the smallest |y| start positions → TE (aligns inside).
    The rest → WR.
    """
    types = ["WR"] * len(routes)
    if te_count > 0 and routes:
        by_abs_y = sorted(range(len(routes)), key=lambda i: abs(routes[i][0][1]))
        for j in range(min(te_count, len(routes))):
            types[by_abs_y[j]] = "TE"
    return types


def draw_play(play) -> go.Figure:
    concept      = _val(play, "concept", "")
    ydstogo      = _val(play, "ydstogo")
    yards_gained = _val(play, "yards_gained")
    coverage     = _val(play, "coverage", "")
    formation    = _val(play, "formation_label", "")
    down         = _val(play, "down")
    team         = _val(play, "posteam", "")
    epa          = _val(play, "epa")

    # ── Receiver / route intel ─────────────────────────────────────────────
    pass_location = _val(play, "pass_location", "") or ""
    route_run     = _val(play, "route", "")
    route_label   = route_run.replace("_", " ").title() if isinstance(route_run, str) and route_run else ""

    # ── Parse positions ────────────────────────────────────────────────────
    off_raw  = _val(play, "offense_positions", "")
    off_pos  = [p.strip() for p in off_raw.split(";")] if isinstance(off_raw, str) and off_raw else []
    te_count = off_pos.count("TE")

    def_raw = _val(play, "defense_positions", "")
    def_pos = [p.strip() for p in def_raw.split(";")] if isinstance(def_raw, str) and def_raw else []
    def_pos = [p for p in def_pos if p not in _NOT_DEF]

    routes      = ROUTES.get(concept, [])
    route_types = _classify_routes(routes, te_count)
    target_idx  = _target_route_index(routes, pass_location)

    fig         = go.Figure()
    shapes      = []
    annotations = []

    # ── Field: sidelines ──────────────────────────────────────────────────
    for y_side in [14, -14]:
        shapes.append(dict(
            type="line", x0=-7, y0=y_side, x1=38, y1=y_side,
            line=dict(color="rgba(255,255,255,0.5)", width=2),
            layer="below",
        ))

    # ── Hash marks ────────────────────────────────────────────────────────
    for y_hash in [6, -6]:
        shapes.append(dict(
            type="line", x0=-7, y0=y_hash, x1=38, y1=y_hash,
            line=dict(color="rgba(255,255,255,0.10)", width=1),
            layer="below",
        ))

    # ── Yard lines + numbers ───────────────────────────────────────────────
    for yard in range(5, 38, 5):
        shapes.append(dict(
            type="line", x0=yard, y0=-14, x1=yard, y1=14,
            line=dict(color="rgba(255,255,255,0.15)", width=1),
            layer="below",
        ))
        annotations.append(dict(
            x=yard, y=0, text=str(yard),
            showarrow=False,
            font=dict(color="rgba(255,255,255,0.20)", size=20, family="Arial Black"),
            xanchor="center", yanchor="middle",
        ))

    # ── Pass location zone (subtle shading on the target side) ────────────
    zone_bands = {
        "right":  (3,  14),
        "left":   (-14, -3),
        "middle": (-3,   3),
    }
    if pass_location in zone_bands:
        z0, z1 = zone_bands[pass_location]
        shapes.append(dict(
            type="rect",
            x0=0, y0=z0, x1=38, y1=z1,
            fillcolor="rgba(255,255,255,0.05)",
            line=dict(width=0), layer="below",
        ))
        loc_text = {"right": "→ RIGHT", "left": "LEFT ←", "middle": "↕ MIDDLE"}[pass_location]
        # Anchor label inside the zone, near the far end of the field
        label_y = (z1 - 1.8) if z1 > 0 else (z0 + 1.8)
        annotations.append(dict(
            x=37, y=label_y,
            text=f"<b>{loc_text}</b>",
            showarrow=False,
            font=dict(color="rgba(255,255,255,0.40)", size=8, family="Arial Black"),
            xanchor="right",
        ))

    # ── Line of scrimmage ──────────────────────────────────────────────────
    shapes.append(dict(
        type="line", x0=0, y0=-14, x1=0, y1=14,
        line=dict(color="#FFD600", width=2.5, dash="dash"),
    ))
    annotations.append(dict(
        x=0.5, y=12.5, text="LOS",
        showarrow=False,
        font=dict(color="#FFD600", size=10, family="Arial Black"),
        xanchor="left",
    ))

    # ── First down line ────────────────────────────────────────────────────
    if ydstogo:
        shapes.append(dict(
            type="line", x0=ydstogo, y0=-14, x1=ydstogo, y1=14,
            line=dict(color="#FF1744", width=2),
        ))
        annotations.append(dict(
            x=ydstogo + 0.4, y=11.5,        # lowered from 12.5 to avoid CB overlap
            text=f"1st & {int(ydstogo)}",
            showarrow=False,
            font=dict(color="#FF1744", size=9),
            xanchor="left",
        ))

    # ── Yards gained marker ────────────────────────────────────────────────
    if yards_gained is not None:
        gain_color = "#00E676" if yards_gained >= 0 else "#FF5252"
        shapes.append(dict(
            type="line", x0=yards_gained, y0=-14, x1=yards_gained, y1=14,
            line=dict(color=gain_color, width=2, dash="dot"),
        ))
        annotations.append(dict(
            x=yards_gained + 0.4, y=9.5,
            text=f"{yards_gained:+g} yds",
            showarrow=False,
            font=dict(color=gain_color, size=9),
            xanchor="left",
        ))

    # ── Offensive Line — compact row at x=-1.5 ────────────────────────────
    for label, y in zip(["T", "G", "C", "G", "T"], [-4.5, -2.2, 0, 2.2, 4.5]):
        _add_player_at(fig, label, -1.5, y,
                       color="rgba(255,255,255,0.70)",
                       symbol="square", size=11,
                       textpos="middle center")

    # ── QB ─────────────────────────────────────────────────────────────────
    is_shotgun = any(k in formation for k in ("Shotgun", "Pistol", "Empty"))
    qb_x = -5.5 if is_shotgun else -2.5
    _add_player_at(fig, "QB", qb_x, 0,
                   color="#FFD600", symbol="square", size=17,
                   textpos="middle center")

    # ── RBs / FBs ─────────────────────────────────────────────────────────
    rbs = [p for p in off_pos if p in _RB_POS]
    if not rbs:
        if "I-Form" in formation:
            rbs = ["FB", "HB"]
        elif formation not in ("Empty",):
            rbs = ["RB"]
    if rbs:
        if is_shotgun:
            rb_xs = [qb_x + 1.5] * len(rbs)
            rb_ys = [-3.5] if len(rbs) == 1 else _spread_y(len(rbs), max_half=3.5, max_step=3.5)
        else:
            rb_xs = [qb_x - 2.0] * len(rbs)
            rb_ys = _spread_y(len(rbs), max_half=2.5, max_step=2.5)
        for label, rx, ry in zip(rbs, rb_xs, rb_ys):
            _add_player_at(fig, label, rx, ry,
                           color="rgba(255,255,255,0.85)",
                           symbol="circle", size=15,
                           textpos="middle center")

    # ── Throw line: QB → targeted receiver endpoint ────────────────────────
    if target_idx is not None:
        target_end = routes[target_idx][-1]
        fig.add_trace(go.Scatter(
            x=[qb_x, target_end[0]],
            y=[0,     target_end[1]],
            mode="lines",
            line=dict(color="rgba(255,255,255,0.25)", width=1.5, dash="dot"),
            showlegend=False,
            hoverinfo="skip",
        ))

    # ── Routes & Receivers ─────────────────────────────────────────────────
    has_te = any(t == "TE" for t in route_types)

    for i, waypoints in enumerate(routes):
        color     = ROUTE_COLORS[i % len(ROUTE_COLORS)]
        is_target = (i == target_idx)
        is_te     = (route_types[i] == "TE")
        label     = f"R{i + 1}"
        symbol    = "diamond" if is_te else "circle"
        pos_tag   = "TE" if is_te else "WR"

        # Route line
        fig.add_trace(go.Scatter(
            x=[p[0] for p in waypoints],
            y=[p[1] for p in waypoints],
            mode="lines",
            line=dict(color=color, width=4.5 if is_target else 2.5),
            showlegend=False,
            hovertemplate=f"<b>{label} ({pos_tag})</b>  Depth: %{{x}} yds<extra></extra>",
        ))

        # Arrow at endpoint
        if len(waypoints) >= 2:
            annotations.append(dict(
                x=waypoints[-1][0],  y=waypoints[-1][1],
                ax=waypoints[-2][0], ay=waypoints[-2][1],
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=2, arrowsize=1.5,
                arrowwidth=3.0 if is_target else 2.0,
                arrowcolor=color, text="",
            ))

        start = waypoints[0]

        # Target highlight ring
        if is_target:
            fig.add_trace(go.Scatter(
                x=[start[0]], y=[start[1]],
                mode="markers",
                marker=dict(color="rgba(0,0,0,0)", size=26, symbol="circle",
                            line=dict(color="white", width=2.5)),
                showlegend=False, hoverinfo="skip",
            ))

        # Receiver dot
        fig.add_trace(go.Scatter(
            x=[start[0]], y=[start[1]],
            mode="markers+text",
            marker=dict(color=color, size=16 if is_target else 13,
                        symbol=symbol,
                        line=dict(color="white", width=1.5)),
            text=[label],
            textposition="middle left",
            textfont=dict(color=color, size=11, family="Arial Black"),
            showlegend=False,
            hovertemplate=(f"<b>{label}</b> — {pos_tag}"
                           + (" · TARGET" if is_target else "")
                           + "<extra></extra>"),
        ))

        # Route name badge on targeted receiver (clamped inside field)
        if is_target and route_label:
            end = waypoints[-1]
            # Offset label toward the center of field to stay inside bounds
            y_offset = -2.5 if end[1] > 0 else 2.5
            label_y  = max(-12.5, min(12.5, end[1] + y_offset))
            annotations.append(dict(
                x=end[0], y=label_y,
                text=f"<b>{route_label}</b>",
                showarrow=False,
                font=dict(color="white", size=9, family="Arial Black"),
                bgcolor="rgba(0,0,0,0.70)",
                bordercolor=color,
                borderwidth=1.5,
                borderpad=4,
                xanchor="center",
            ))

    # ── No diagram fallback ────────────────────────────────────────────────
    if not routes:
        annotations.append(dict(
            x=18, y=0,
            text=f'No diagram for "{concept}"',
            showarrow=False,
            font=dict(color="rgba(255,255,255,0.6)", size=13),
            xanchor="center",
        ))

    # ── Defense ────────────────────────────────────────────────────────────
    if def_pos:
        dl  = [p for p in def_pos if p in _DL_POS]
        lb  = [p for p in def_pos if p in _LB_POS]
        cbs = [p for p in def_pos if p in _CB_POS]
        saf = [p for p in def_pos if p in _S_POS]
        known_def = _DL_POS | _LB_POS | _CB_POS | _S_POS
        lb += [p for p in def_pos if p not in known_def]

        for label, y in zip(dl, _spread_y(len(dl), max_half=5.5, max_step=2.5)):
            _add_def_player(fig, annotations, label, 2.0, y, "#EF5350")

        for label, y in zip(lb, _spread_y(len(lb), max_half=7.0, max_step=3.0)):
            _add_def_player(fig, annotations, label, 5.0, y, "#FF8A65")

        if cbs:
            cb_ys = ([-10.0, 10.0] if len(cbs) == 2
                     else [-10.5, 0.0, 10.5] if len(cbs) == 3
                     else _spread_y(len(cbs), max_half=11.0, max_step=4.0))
            cb_x  = 3.5 if any(c in coverage for c in ("Cover 0", "Cover 1", "Man")) else 7.0
            for label, y in zip(cbs, cb_ys):
                _add_def_player(fig, annotations, label, cb_x, y, "#FFCA28")

        saf_x = 11.0 if len(saf) >= 2 else 12.0
        for label, y in zip(saf, _spread_y(len(saf), max_half=4.0, max_step=3.5)):
            _add_def_player(fig, annotations, label, saf_x, y, "#80CBC4")

    # ── Bottom stats bar ───────────────────────────────────────────────────
    shapes.append(dict(
        type="rect", xref="paper", yref="paper",
        x0=0, y0=-0.01, x1=1, y1=-0.18,
        fillcolor="rgba(0,0,0,0.55)", line=dict(width=0), layer="above",
    ))

    if team:
        annotations.append(dict(
            xref="paper", yref="paper",
            x=0.02, y=-0.095,
            text=f"<b>{team}</b>",
            showarrow=False,
            font=dict(color="white", size=13, family="Arial Black"),
            xanchor="left", yanchor="middle",
        ))

    center_parts = []
    if down and ydstogo:
        suffix = _DOWN_SUFFIX.get(int(down), "th")
        center_parts.append(f"<b>{int(down)}{suffix} & {int(ydstogo)}</b>")
    if concept:
        center_parts.append(concept)
    if formation:
        center_parts.append(formation)
    if coverage:
        center_parts.append(f"vs {coverage}")
    if center_parts:
        annotations.append(dict(
            xref="paper", yref="paper",
            x=0.5, y=-0.095,
            text="  |  ".join(center_parts),
            showarrow=False,
            font=dict(color="rgba(255,255,255,0.85)", size=10),
            xanchor="center", yanchor="middle",
        ))

    right_parts = []
    if yards_gained is not None and ydstogo is not None:
        converted = yards_gained >= ydstogo
        right_parts.append(("✓ 1st Down" if converted else "✗ No conv.",
                             "#00E676" if converted else "#FF5252"))
    if epa is not None:
        right_parts.append((f"EPA: {epa:+.2f}", "#00E676" if epa >= 0 else "#FF5252"))

    right_x = 0.98
    for text, color in reversed(right_parts):
        annotations.append(dict(
            xref="paper", yref="paper",
            x=right_x, y=-0.095,
            text=f"<b>{text}</b>",
            showarrow=False,
            font=dict(color=color, size=11, family="Arial Black"),
            xanchor="right", yanchor="middle",
        ))
        right_x -= 0.10

    # ── Top legend (single consolidated annotation) ────────────────────────
    legend_parts = []
    if def_pos:
        legend_parts.append(
            "<span style='color:#EF5350'>● DL</span> "
            "<span style='color:#FF8A65'>● LB</span> "
            "<span style='color:#FFCA28'>● CB</span> "
            "<span style='color:#80CBC4'>● S</span>"
        )
    if routes:
        rec_parts = []
        if has_te:
            rec_parts.append("<span style='color:rgba(255,255,255,0.75)'>◆ TE</span>")
        rec_parts.append("<span style='color:rgba(255,255,255,0.75)'>● WR</span>")
        if target_idx is not None:
            rec_parts.append("<span style='color:rgba(255,255,255,0.75)'>⊙ Target</span>")
        legend_parts.append("  ".join(rec_parts))

    if legend_parts:
        annotations.append(dict(
            xref="paper", yref="paper",
            x=0.01, y=1.06,
            text="  ·  ".join(legend_parts),
            showarrow=False,
            font=dict(color="white", size=9),
            xanchor="left", yanchor="middle",
            bgcolor="rgba(0,0,0,0.35)",
            borderpad=4,
        ))

    # ── Layout ─────────────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text=f"<b>{concept}</b>",
            font=dict(color="white", size=17, family="Arial Black"),
            x=0.5, y=0.97, xanchor="center",
        ),
        showlegend=False,                        # all info is in the annotation legend
        plot_bgcolor="#2e7d32",
        paper_bgcolor="#1b5e20",
        xaxis=dict(visible=False, range=[-7, 38]),
        yaxis=dict(visible=False, range=[-15, 15]),
        shapes=shapes,
        annotations=annotations,
        height=500,
        margin=dict(l=10, r=10, t=50, b=80),
        hovermode="closest",
    )

    return fig