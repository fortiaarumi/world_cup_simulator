"""
Reusable card components for the FIFA WC 2026 app.
"""
import streamlit as st
from ui.flags import team_with_flag, get_flag


def render_podium_card(position: str, team: str, probability: float,
                       css_class: str, secondaries: list[tuple[str, float]] | None = None):
    """Render a podium card (gold/silver/bronze) with optional secondary projections.

    Args:
        position: Display label (e.g. "Champion")
        team: Team name
        probability: Win probability as percentage
        css_class: One of wc-podium-gold, wc-podium-silver, wc-podium-bronze
        secondaries: List of (team, probability) tuples for 2nd/3rd projections
    """
    flag = get_flag(team)

    st.markdown(f"""
    <div class="{css_class}">
        <div class="wc-podium-position">{position}</div>
        <div class="wc-podium-flag">{flag}</div>
        <div class="wc-podium-team">{team}</div>
        <div class="wc-podium-prob">{probability:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

    if secondaries:
        for sec_team, sec_prob in secondaries:
            sec_flag = get_flag(sec_team)
            st.markdown(f"""
            <div class="wc-podium-secondary">
                <span>{sec_flag}</span>
                <span class="team-name">{sec_team}</span>
                <span class="prob">{sec_prob:.1f}%</span>
            </div>
            """, unsafe_allow_html=True)


def render_story_card(title: str, subtitle: str, content_html: str, css_class: str = "wc-podium-gold"):
    """Render a general story/superlative card for the landing page."""
    html = (
        f'<div class="{css_class}" style="min-height: 240px; display: flex; flex-direction: column; justify-content: center;">'
        f'<div class="wc-podium-position" style="font-size: 1.1rem; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 1px;">{title}</div>'
        f'<div style="font-size: 0.9rem; color: var(--wc-secondary); margin-bottom: 1rem; line-height: 1.3;">{subtitle}</div>'
        f'<div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center;">'
        f'{content_html}'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_stat_box(value: str, label: str):
    """Render a stat metric box."""
    st.markdown(f"""
    <div class="wc-stat-box">
        <div class="value">{value}</div>
        <div class="label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_match_card(team1: str, team2: str, probability: float, extra_info: str = ""):
    """Render a match card showing two teams and probability."""
    flag1 = get_flag(team1)
    flag2 = get_flag(team2)
    extra_html = f'<div style="font-size:0.8rem; color:var(--wc-secondary); margin-top:0.25rem;">{extra_info}</div>' if extra_info else ""
    st.markdown(f"""
    <div class="wc-match-card">
        <div class="wc-match-teams">
            <div class="wc-match-team">{flag1} {team1}</div>
            <div class="wc-match-vs">vs</div>
            <div class="wc-match-team">{flag2} {team2}</div>
        </div>
        <div class="wc-match-prob">
            Probability: <strong>{probability:.1f}%</strong>
        </div>
        {extra_html}
    </div>
    """, unsafe_allow_html=True)


def render_score_row(home_team: str, away_team: str, home_score: int, away_score: int,
                     winner: str, probability: float):
    """Render a single score result line."""
    flag_h = get_flag(home_team)
    flag_a = get_flag(away_team)
    h_class = "winner-indicator" if winner == home_team else ""
    a_class = "winner-indicator" if winner == away_team else ""
    st.markdown(f"""
    <div class="wc-score">
        <span class="team left {h_class}">{flag_h} {home_team}</span>
        <span class="goals">{home_score} - {away_score}</span>
        <span class="team right {a_class}">{flag_a} {away_team}</span>
        <span class="wc-badge wc-badge-turquoise" style="margin-left:0.5rem;">{probability:.1f}%</span>
    </div>
    """, unsafe_allow_html=True)


def render_probability_bar(probability: float, label: str = "", bar_class: str = "wc-prob-bar"):
    """Render a probability bar."""
    label_html = f'<span style="font-size:0.85rem; color:var(--wc-secondary);">{label}</span>' if label else ""
    st.markdown(f"""
    {label_html}
    <div class="wc-prob-bar-container">
        <div class="{bar_class}" style="width: {min(probability, 100)}%;"></div>
    </div>
    """, unsafe_allow_html=True)


def render_info_box(text: str):
    """Render an info/helper box."""
    st.markdown(f'<div class="wc-info-box">{text}</div>', unsafe_allow_html=True)


def render_group_standing_table(rows: list[dict], group_name: str,
                                probability: float | None = None, compact: bool = False):
    """Render a mini group standings table.

    Args:
        rows: List of dicts with keys: position, team, played, wins, draws, losses,
              goals_for, goals_against, goal_difference, points, advanced
        group_name: Group letter
        probability: Optional probability for this scenario
        compact: If True, show position, team, GD and Pts columns (for overview grids)
    """
    prob_html = f' <span class="wc-badge wc-badge-turquoise">{probability:.1f}%</span>' if probability is not None else ""
    header = f'<div class="wc-section-sub">Group {group_name}{prob_html}</div>'

    # Build complete table HTML without leading whitespace to avoid code block formatting
    table_html = '<div class="wc-card-flat"><table class="wc-group-table"><thead><tr>'
    if compact:
        table_html += '<th>#</th><th>Team</th><th>Pts</th><th>GD</th>'
    else:
        table_html += '<th>#</th><th>Team</th><th>P</th><th>W</th><th>D</th>'
        table_html += '<th>L</th><th>GD</th><th>Pts</th>'
    table_html += '</tr></thead><tbody>'

    # Add all rows
    for r in rows:
        flag = get_flag(r["team"])
        row_class = "advanced" if r.get("advanced") else "eliminated"
        table_html += f'<tr class="{row_class}">'
        table_html += f'<td>{r["position"]}</td>'
        table_html += f'<td>{flag} {r["team"]}</td>'
        if compact:
            table_html += f'<td><strong>{r.get("points", "-")}</strong></td>'
            table_html += f'<td>{r.get("goal_difference", "-")}</td>'
        else:
            table_html += f'<td>{r.get("played", "-")}</td>'
            table_html += f'<td>{r.get("wins", "-")}</td>'
            table_html += f'<td>{r.get("draws", "-")}</td>'
            table_html += f'<td>{r.get("losses", "-")}</td>'
            table_html += f'<td>{r.get("goal_difference", "-")}</td>'
            table_html += f'<td><strong>{r.get("points", "-")}</strong></td>'
        table_html += '</tr>'

    # Close table
    table_html += '</tbody></table></div>'

    # Render header and table as separate markdown calls
    st.markdown(header, unsafe_allow_html=True)
    st.markdown(table_html, unsafe_allow_html=True)


# Advancement tiers: (min_pct_inclusive, label, dot_color)
_ADV_TIERS = [
    (90.0, "Lock",     "#22C55E"),
    (70.0, "Safe",     "#4ADE80"),
    (50.0, "Likely",   "#FACC15"),
    (30.0, "Toss-up",  "#FB923C"),
    (0.0,  "Longshot", "#EF4444"),
]


def _adv_tier(pct: float) -> tuple[str, str]:
    """Return (label, color) for an advancement probability."""
    for threshold, label, color in _ADV_TIERS:
        if pct >= threshold:
            return label, color
    return _ADV_TIERS[-1][1], _ADV_TIERS[-1][2]


# Drama thresholds: gap in advancement probability between the 2nd and 3rd
# expected teams (the qualification cut line). Shared by the chip and the story
# so they never disagree.
_CLEAR_CUT_GAP = 28.0
_CONTESTED_GAP = 12.0


def _cutline_gap(rows: list[dict]) -> float:
    """Advancement-probability gap between the 2nd and 3rd expected teams."""
    return rows[1]["advance_pct"] - rows[2]["advance_pct"]


def _group_drama(rows: list[dict]) -> tuple[str, str]:
    """Classify a group's competitiveness from the qualification cut line.

    The two automatic qualifying spots are settled when the 2nd expected team
    is clearly separated from the 3rd. We measure that gap in advancement
    probability (rows are sorted best-first):

        gap = advance_pct(2nd) - advance_pct(3rd)

    A wide gap means the top two are safe -> clear-cut. A narrow gap means the
    second spot is genuinely up for grabs -> contested / group of death.

    Returns (label, color).
    """
    if len(rows) < 3:
        return "✅ Clear-cut", "#22C55E"
    gap = _cutline_gap(rows)
    if gap >= _CLEAR_CUT_GAP:
        return "✅ Clear-cut", "#22C55E"
    if gap >= _CONTESTED_GAP:
        return "⚡ Contested", "#FB923C"
    return "🔥 Group of Death", "#EF4444"


def _group_story(rows: list[dict]) -> str:
    """Generate a one-line narrative aligned with the drama classification.

    Uses the same qualification-cut-line gap as _group_drama so the story and
    the chip always tell a consistent tale. rows must be sorted best-first.
    """
    if len(rows) < 4:
        return f"{rows[0]['team']} lead the group." if rows else ""

    leader, second, third, fourth = rows[0], rows[1], rows[2], rows[3]
    name = lambda r: r["team"]
    gap = _cutline_gap(rows)

    if gap >= _CLEAR_CUT_GAP:
        # Top two clearly separated from the pack.
        return (f"{name(leader)} and {name(second)} are strong favourites to advance; "
                f"{name(third)} and {name(fourth)} are left chasing.")

    if gap >= _CONTESTED_GAP:
        # Leader fairly safe, second ticket fought over by 2nd and 3rd.
        return (f"{name(leader)} should go through, but {name(second)} and "
                f"{name(third)} will battle for the second spot.")

    # Group of death: cut line is razor-thin.
    if leader["advance_pct"] >= 80:
        return (f"{name(leader)} look safe — but {name(second)}, {name(third)} and "
                f"{name(fourth)} are all scrapping for the final ticket.")
    return (f"Anyone's group: {name(leader)}, {name(second)}, {name(third)} and "
            f"{name(fourth)} are separated by a whisker.")


def render_group_aggregate_card(group_name: str, rows: list[dict]):
    """Render a compact, representative group card for the overview grid.

    Instead of one lucky single-simulation standing (which collapses onto a
    draw-free 9-6-3-0), this shows distributional expectations: average points,
    average goal difference, and each team's probability of advancing — plus a
    drama chip and a one-line story for engagement.

    Args:
        group_name: Group letter.
        rows: List of dicts (sorted best-first) with keys:
              position, team, avg_pts, avg_gd, advance_pct.
    """
    drama_label, drama_color = _group_drama(rows)
    header = (
        f'<div class="wc-section-sub" style="display:flex; align-items:center; '
        f'justify-content:space-between; gap:0.4rem;">'
        f'<span>Group {group_name}</span>'
        f'<span style="font-size:0.65rem; font-weight:700; color:{drama_color}; '
        f'white-space:nowrap;">{drama_label}</span>'
        f'</div>'
    )

    table_html = '<div class="wc-card-flat"><table class="wc-group-table"><thead><tr>'
    table_html += '<th>#</th><th>Team</th><th>xPts</th><th>xGD</th><th>Adv</th>'
    table_html += '</tr></thead><tbody>'

    for r in rows:
        flag = get_flag(r["team"])
        adv = r["advance_pct"]
        _, color = _adv_tier(adv)
        row_class = "advanced" if adv >= 50.0 else "eliminated"
        gd = r["avg_gd"]
        gd_str = f"+{gd:.1f}" if gd > 0 else f"{gd:.1f}"
        adv_cell = (
            f'<span style="display:inline-block; width:7px; height:7px; '
            f'border-radius:50%; background:{color}; margin-right:4px;"></span>'
            f'<strong style="color:{color};">{adv:.0f}%</strong>'
        )
        table_html += f'<tr class="{row_class}">'
        table_html += f'<td>{r["position"]}</td>'
        table_html += f'<td>{flag} {r["team"]}</td>'
        table_html += f'<td><strong>{r["avg_pts"]:.1f}</strong></td>'
        table_html += f'<td>{gd_str}</td>'
        table_html += f'<td>{adv_cell}</td>'
        table_html += '</tr>'

    table_html += '</tbody></table></div>'

    story = _group_story(rows)
    story_html = (
        f'<div style="font-size:0.72rem; color:var(--wc-secondary); '
        f'font-style:italic; margin:0.3rem 0 0.25rem; line-height:1.3;">{story}</div>'
        if story else ""
    )

    st.markdown(header, unsafe_allow_html=True)
    st.markdown(table_html, unsafe_allow_html=True)
    st.markdown(story_html, unsafe_allow_html=True)


def render_position_probabilities_heatmap(df):
    """Render a heatmap table of finishing position probabilities.
    
    Args:
        df: DataFrame with team index and columns 1, 2, 3, 4 (probs).
    """
    if df.empty:
        return

    st.markdown('<div class="wc-section-sub" style="font-size:1rem; margin-top:1.5rem;">Finish Position Probabilities</div>', unsafe_allow_html=True)
    
    html = '<div class="wc-card-flat"><table class="wc-group-table" style="text-align:center;">'
    
    # Header
    html += '<thead><tr>'
    html += '<th style="text-align:left;">Team</th>'
    html += '<th>1st</th><th>2nd</th><th>3rd</th><th>4th</th>'
    html += '</tr></thead><tbody>'
    
    # Rows
    for team, row in df.iterrows():
        flag = get_flag(team)
        html += '<tr>'
        html += f'<td style="text-align:left;">{flag} {team}</td>'
        
        for pos in [1, 2, 3, 4]:
            prob = row.get(pos, 0.0)
            # Calculate opacity based on probability (0-100) -> (0.05 - 0.9)
            # Using a turquoise color: rgba(38, 230, 219, alpha)
            alpha = max(0.05, min(0.9, prob / 100.0 * 1.5)) # Scale up a bit so 50% is quite visible
            bg_style = f'background-color: rgba(38, 230, 219, {alpha:.2f}); color: {"#000" if alpha > 0.5 else "inherit"};'
            
            html += f'<td style="{bg_style} border-radius:4px;">{prob:.1f}%</td>'
            
        html += '</tr>'
        
    html += '</tbody></table></div>'
    
    st.markdown(html, unsafe_allow_html=True)
