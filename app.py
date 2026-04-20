import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pytz

from data.nba_data import (
    get_playoff_teams, get_team_stats, get_team_players,
    get_player_stats, get_playoff_bracket, get_series_standings,
    get_upcoming_playoff_games, get_all_teams,
)
from data.bracket_simulator import simulate_full_bracket

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="NBA Playoff Predictor", page_icon="🏀", layout="wide")
st.title("🏀 NBA Playoff Predictor 2025-26")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 Playoff Bracket",
    "📅 Upcoming Games",
    "🤖 ML Vorhersagen",
    "📊 Team Statistiken",
    "⭐ Spieler Statistiken",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – PLAYOFF BRACKET
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("🏆 Playoff Bracket")
    if st.button("🔄 Bracket aktualisieren", key="refresh_bracket"):
        st.cache_data.clear()

    @st.cache_data(ttl=300)
    def load_bracket():
        return get_playoff_bracket()

    @st.cache_data(ttl=300)
    def load_series():
        return get_series_standings()

    with st.spinner("Lade Playoff Bracket..."):
        try:
            bracket = load_bracket()
            series_data = load_series()
        except Exception as e:
            st.error(f"Fehler: {e}")
            st.stop()

    if bracket["east"].empty and bracket["west"].empty:
        st.info("⏳ Bracket noch nicht verfügbar.")
        st.stop()

    def render_bracket_side(df, conference):
        st.subheader(f"{'🔵' if conference == 'East' else '🔴'} {conference}ern Conference")
        if df.empty:
            st.info("Keine Daten.")
            return
        for _, row in df.iterrows():
            home = row.get("homeTeam_teamName", "TBD")
            away = row.get("awayTeam_teamName", "TBD")
            h_seed = int(row.get("homeTeam_seed", 0))
            a_seed = int(row.get("awayTeam_seed", 0))
            series_id = row.get("gameId", "")[:9]
            s = series_data.get(series_id, {})
            series_text = s.get("series_text", "Series tied 0-0")
            h_wins = s.get("home_wins", 0)
            a_wins = s.get("away_wins", 0)
            winner_home = h_wins == 4
            winner_away = a_wins == 4

            with st.container(border=True):
                col_home, col_vs, col_away, col_series = st.columns([3, 1, 3, 3])
                with col_home:
                    st.markdown(f"### {'🏆 ' if winner_home else ''}#{h_seed} {home}")
                    st.markdown(f"**Wins: {h_wins}**")
                with col_vs:
                    st.markdown("## vs")
                with col_away:
                    a_seed_str = str(a_seed) if a_seed > 0 else "?"
                    st.markdown(f"### {'🏆 ' if winner_away else ''}#{a_seed_str} {away}")
                    st.markdown(f"**Wins: {a_wins}**")
                with col_series:
                    if winner_home or winner_away:
                        st.success(series_text)
                    elif h_wins > 0 or a_wins > 0:
                        st.warning(series_text)
                    else:
                        st.info(series_text)
                    fig = go.Figure(go.Bar(
                        x=[h_wins, a_wins], y=[home, away], orientation='h',
                        marker_color=['#1d428a', '#c8102e'],
                        text=[h_wins, a_wins], textposition='inside',
                    ))
                    fig.update_layout(
                        height=80, margin=dict(l=0, r=0, t=0, b=0),
                        xaxis=dict(range=[0, 4], showticklabels=False),
                        showlegend=False,
                        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"bar_{series_id}")

    col_e, col_w = st.columns(2)
    with col_e:
        render_bracket_side(bracket["east"], "East")
    with col_w:
        render_bracket_side(bracket["west"], "West")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – UPCOMING GAMES
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("📅 Nächste Playoff Spiele")
    if st.button("🔄 Aktualisieren", key="refresh_upcoming"):
        st.cache_data.clear()

    @st.cache_data(ttl=300)
    def load_upcoming():
        return get_upcoming_playoff_games(n=20)

    with st.spinner("Lade Spielplan..."):
        try:
            upcoming = load_upcoming()
        except Exception as e:
            st.error(f"Fehler: {e}")
            st.stop()

    berlin_tz = pytz.timezone("Europe/Berlin")
    round_labels = {1: "First Round", 2: "Conference Semifinals",
                    3: "Conference Finals", 4: "NBA Finals"}

    if upcoming.empty:
        st.info("🏆 Keine anstehenden Spiele.")
    else:
        def fmt_dt(dt_str):
            try:
                dt = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
                return dt.astimezone(berlin_tz).strftime("%a %d.%m.%Y  %H:%M")
            except Exception:
                return str(dt_str)

        for rnd, grp in upcoming.groupby("round") if "round" in upcoming.columns else [(None, upcoming)]:
            st.subheader(f"🔹 {round_labels.get(rnd, f'Round {rnd}')}")
            for _, game in grp.iterrows():
                home = game.get("homeTeam_teamName", "TBD")
                away = game.get("awayTeam_teamName", "TBD")
                h_seed = int(game["homeTeam_seed"]) if pd.notna(game.get("homeTeam_seed")) and game.get("homeTeam_seed") > 0 else "?"
                a_seed = int(game["awayTeam_seed"]) if pd.notna(game.get("awayTeam_seed")) and game.get("awayTeam_seed") > 0 else "?"
                with st.container(border=True):
                    c1, c2, c3 = st.columns([4, 2, 3])
                    with c1:
                        st.markdown(f"**#{a_seed} {away}** @ **#{h_seed} {home}**")
                    with c2:
                        st.markdown(f"📅 {fmt_dt(game.get('gameDateTimeUTC', ''))} CET")
                    with c3:
                        info = game.get("seriesText", "") or game.get("gameStatusText", "")
                        if info:
                            st.caption(info)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – ML VORHERSAGEN (Bracket Simulator)
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("🤖 Playoff Bracket Simulator")
    st.caption("Simuliert den kompletten Playoff-Bracket Runde für Runde basierend auf Saison-Stats + Top-Spieler 2025-26.")

    simulate_btn = st.button("🔮 Kompletten Bracket simulieren", type="primary", use_container_width=True)
    st.info("⏳ Die Simulation dauert ca. 3-5 Minuten da für alle Teams Stats geladen werden. Ergebnis wird gecacht.")

    if simulate_btn:
        # Progress Status
        status_box = st.empty()
        progress_bar = st.progress(0)
        step = [0]
        total_steps = 15  # ~15 API-Aufrufe

        def update_progress(msg):
            step[0] += 1
            pct = min(int(step[0] / total_steps * 100), 99)
            status_box.info(f"⏳ {msg}")
            progress_bar.progress(pct)

        try:
            sim_result = simulate_full_bracket(progress_cb=update_progress)
            st.session_state['sim_result'] = sim_result
            progress_bar.progress(100)
            status_box.success("✅ Simulation abgeschlossen!")
        except Exception as e:
            status_box.error(f"Fehler: {e}")
            st.stop()

    # Ergebnis aus session_state anzeigen (bleibt nach Button-Klick erhalten)
    sim_result = st.session_state.get('sim_result')

    if sim_result:
        st.divider()

        # ── Champion ──────────────────────────────────────────────────────────
        champion = sim_result.get('champion', 'TBD')
        st.markdown(f"# 🏆 Vorhergesagter NBA Champion: **{champion}**")

        finals = sim_result.get('finals')
        if finals:
            fc1, fc2, fc3 = st.columns(3)
            fc1.metric("Finals Matchup", f"{finals['home_name']} vs {finals['away_name']}")
            fc2.metric("Vorhergesagter Score", finals['series_score'])
            fc3.metric("Confidence", f"{finals['confidence_color']} {finals['confidence']}")

        st.divider()

        # ── Bracket Runden ─────────────────────────────────────────────────────
        round_names = {
            'round1': '🔹 First Round',
            'round2': '🔸 Conference Semifinals',
            'round3': '🔶 Conference Finals',
        }

        def render_series_card(s, key_prefix):
            home = s.get('home_name', '?')
            away = s.get('away_name', '?')
            winner = s.get('winner_name', '?')
            loser = s.get('loser_name', '?')
            prob = s.get('prob_winner', 0.5)
            score = s.get('series_score', '4-?')
            conf_color = s.get('confidence_color', '🟡')
            conf = s.get('confidence', '')

            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 4, 3])
                with c1:
                    # Home Team
                    is_winner = home == winner
                    prefix = "✅ " if is_winner else "❌ "
                    st.markdown(f"**{prefix}{home}**")
                with c2:
                    # Away Team
                    is_winner = away == winner
                    prefix = "✅ " if is_winner else "❌ "
                    st.markdown(f"**{prefix}{away}**")
                with c3:
                    st.markdown(f"**{winner}** gewinnt **{score}**")
                    st.caption(f"{conf_color} {conf} · {prob*100:.0f}%")

                # Win-Prob Balken
                fig = go.Figure()
                h_prob = prob if home == winner else (1 - prob)
                a_prob = 1 - h_prob
                fig.add_trace(go.Bar(
                    x=[h_prob * 100], y=[""], orientation='h',
                    marker_color='#1d428a',
                    text=f"{home} {h_prob*100:.0f}%", textposition='inside',
                ))
                fig.add_trace(go.Bar(
                    x=[a_prob * 100], y=[""], orientation='h',
                    marker_color='#c8102e',
                    text=f"{a_prob*100:.0f}% {away}", textposition='inside',
                ))
                fig.update_layout(
                    barmode='stack', height=60,
                    margin=dict(l=0, r=0, t=0, b=0),
                    xaxis=dict(range=[0, 100], showticklabels=False),
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                )
                st.plotly_chart(fig, use_container_width=True, key=f"bar_{key_prefix}_{home}_{away}")

        # East + West nebeneinander
        for rnd_key, rnd_label in round_names.items():
            st.subheader(rnd_label)
            east_series = sim_result['east'].get(rnd_key, [])
            west_series = sim_result['west'].get(rnd_key, [])

            col_e, col_w = st.columns(2)
            with col_e:
                st.markdown("**🔵 Eastern Conference**")
                if east_series:
                    for i, s in enumerate(east_series):
                        render_series_card(s, f"e_{rnd_key}_{i}")
                else:
                    st.info("Keine Daten")
            with col_w:
                st.markdown("**🔴 Western Conference**")
                if west_series:
                    for i, s in enumerate(west_series):
                        render_series_card(s, f"w_{rnd_key}_{i}")
                else:
                    st.info("Keine Daten")

        # NBA Finals
        st.subheader("🏆 NBA Finals")
        if finals:
            render_series_card(finals, "finals")

        st.caption("⚠️ Vorhersagen basieren auf Saison-Stats der regulären Saison 2025-26 und sind keine Garantie.")



# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – TEAM STATISTIKEN
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("📊 Team Statistiken")

    @st.cache_data(ttl=600)
    def load_playoff_teams():
        return get_playoff_teams()

    with st.spinner("Lade Teams..."):
        try:
            standings = load_playoff_teams()
        except Exception as e:
            st.error(f"Fehler: {e}")
            st.stop()

    col1, col2 = st.columns(2)
    east_teams = standings[standings['Conference'] == 'East'].sort_values('PlayoffRank')
    west_teams = standings[standings['Conference'] == 'West'].sort_values('PlayoffRank')

    with col1:
        st.subheader("🔵 Eastern Conference")
        for _, row in east_teams.iterrows():
            st.write(f"#{int(row['PlayoffRank'])} {row['TeamName']} — "
                     f"{int(row['WINS'])}W {int(row['LOSSES'])}L ({float(row['WinPCT']):.3f})")
    with col2:
        st.subheader("🔴 Western Conference")
        for _, row in west_teams.iterrows():
            st.write(f"#{int(row['PlayoffRank'])} {row['TeamName']} — "
                     f"{int(row['WINS'])}W {int(row['LOSSES'])}L ({float(row['WinPCT']):.3f})")

    st.divider()
    team_options = {row['TeamName']: row['TeamID'] for _, row in standings.iterrows()}
    selected_team = st.selectbox("Team auswählen", list(team_options.keys()), key="team_sel")

    if selected_team:
        @st.cache_data(ttl=300)
        def load_team_stats(tid):
            return get_team_stats(tid)

        with st.spinner(f"Lade Stats für {selected_team}..."):
            try:
                team_stats = load_team_stats(team_options[selected_team])
            except Exception as e:
                st.error(f"Fehler: {e}")
                st.stop()

        st.subheader(f"Letzte 10 Spiele – {selected_team}")
        if 'WL' in team_stats.columns and 'PTS' in team_stats.columns:
            fig = px.bar(team_stats, x='GAME_DATE', y='PTS', color='WL',
                         color_discrete_map={'W': '#00c04b', 'L': '#e63946'},
                         title=f"{selected_team} – Punkte letzte 10 Spiele",
                         labels={'PTS': 'Punkte', 'GAME_DATE': 'Datum'})
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        show_cols = [c for c in ['GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG_PCT']
                     if c in team_stats.columns]
        st.dataframe(team_stats[show_cols], use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 – SPIELER STATISTIKEN
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("⭐ Spieler Statistiken")

    @st.cache_data(ttl=600)
    def load_teams_for_players():
        return get_playoff_teams()

    with st.spinner("Lade Teams..."):
        try:
            p_standings = load_teams_for_players()
        except Exception as e:
            st.error(f"Fehler: {e}")
            st.stop()

    team_opts = {row['TeamName']: row['TeamID'] for _, row in p_standings.iterrows()}
    sel_team = st.selectbox("Team auswählen", list(team_opts.keys()), key="player_team_sel")

    if sel_team:
        @st.cache_data(ttl=600)
        def load_roster(t):
            return get_team_players(t)

        with st.spinner("Lade Kader..."):
            try:
                roster = load_roster(team_opts[sel_team])
            except Exception as e:
                st.error(f"Fehler: {e}")
                st.stop()

        player_col = next((c for c in ['PLAYER', 'PlayerName', 'PLAYER_NAME'] if c in roster.columns), None)
        id_col = next((c for c in ['PLAYER_ID', 'PlayerId'] if c in roster.columns), None)

        if player_col and id_col:
            player_opts = dict(zip(roster[player_col], roster[id_col]))
            sel_player = st.selectbox("Spieler auswählen", list(player_opts.keys()))

            if sel_player:
                @st.cache_data(ttl=300)
                def load_player_stats(p):
                    return get_player_stats(p)

                with st.spinner(f"Lade Stats für {sel_player}..."):
                    try:
                        p_stats = load_player_stats(player_opts[sel_player])
                    except Exception as e:
                        st.error(f"Fehler: {e}")
                        st.stop()

                st.subheader(f"Letzte 10 Spiele – {sel_player}")
                if 'PTS' in p_stats.columns and 'GAME_DATE' in p_stats.columns:
                    fig2 = px.line(p_stats, x='GAME_DATE', y='PTS', markers=True,
                                   title=f"{sel_player} – Punkte letzte 10 Spiele",
                                   labels={'PTS': 'Punkte', 'GAME_DATE': 'Datum'})
                    st.plotly_chart(fig2, use_container_width=True)

                show_cols = [c for c in ['GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'FG_PCT', 'FG3_PCT']
                             if c in p_stats.columns]
                st.dataframe(p_stats[show_cols], use_container_width=True)