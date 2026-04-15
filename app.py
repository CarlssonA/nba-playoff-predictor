import streamlit as st
import pandas as pd
from data.nba_data import get_playoff_teams, get_team_stats, get_all_teams
st.cache_data.clear()

st.set_page_config(
    page_title="NBA Playoff Predictor 2025-26",
    page_icon="🏀",
    layout = "wide"
)

st.title("🏀 NBA Playoff Predictor 2025-26")
st.markdown("---")

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Seite wählen:",
    ["🏆 Playoff Bracket", "📊 Team Statistiken", "⭐ Spieler Statistiken"]
)

@st.cache_data(ttl=3600)  # Cache für 1 Stunde
def load_standings():
    return get_playoff_teams()

with st.spinner("NBA Daten werden geladen..."):
    try:
        standings = load_standings()
        st.success("Daten erfolgreich geladen!")
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        import traceback
        st.code(traceback.format_exc())
        standings = None

if standings is not None:

    if page == "🏆 Playoff Bracket":
        st.header("🏆 Playoff Bracket")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Eastern Conference")
            east = standings[standings['Conference'] == 'East'].sort_values('PlayoffRank')
            for _, row in east.iterrows():
                seed = int(row['PlayoffRank'])
                emoji = "🥇" if seed == 1 else "🎯" if seed <= 6 else "⚡"
                label = "Play-In" if seed > 6 else "Playoffs"
                st.write(f"{emoji} **#{seed} {row['TeamName']}** — {int(row['WINS'])}-{int(row['LOSSES'])} ({label})")

        with col2:
            st.subheader("Western Conference")
            west = standings[standings['Conference'] == 'West'].sort_values('PlayoffRank')
            for _, row in west.iterrows():
                seed = int(row['PlayoffRank'])
                emoji = "🥇" if seed == 1 else "🎯" if seed <= 6 else "⚡"
                label = "Play-In" if seed > 6 else "Playoffs"
                st.write(f"{emoji} **#{seed} {row['TeamName']}** — {int(row['WINS'])}-{int(row['LOSSES'])} ({label})")
    
    elif page == "📊 Team Statistiken":
        st.header("📊 Team Statistiken")

        team_names = standings['TeamName'].tolist()
        selected_team = st.selectbox("Team auswählen:", team_names)

        team_row = standings[standings['TeamName'] == selected_team].iloc[0]
        team_id = team_row['TeamID']

        # Metriken anzeigen
        col1, col2, col3 = st.columns(3)
        col1.metric("Wins", int(team_row['WINS']))
        col2.metric("Losses", int(team_row['LOSSES']))
        col3.metric("Win %", f"{float(team_row['WinPCT']):.1%}")

        # Letzte 10 Spiele
        st.subheader(f"Letzte 10 Spiele - {selected_team}")
        with st.spinner("Spieldaten werden geladen..."):
            try:
                gamelog = get_team_stats(team_id)
                st.dataframe(
                    gamelog[['GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 'FG_PCT']],
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Fehler: {e}")

    elif page == "⭐ Spieler Statistiken":
        st.header("⭐ Spieler Statistiken")
        st.info("Kommt bald! 🚀")