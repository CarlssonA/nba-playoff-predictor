import streamlit as st
import pandas as pd
import plotly.express as px
from data.nba_data import get_playoff_teams, get_team_stats, get_all_teams, get_team_players, get_player_stats
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

                st.subheader("📈 Punkte Verlauf")
                chart_data = gamelog[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']].copy()

                chart_data['GAME_DATE'] = pd.to_datetime(chart_data['GAME_DATE'])
                chart_data = chart_data.sort_values('GAME_DATE').reset_index(drop=True)

                chart_data['GEGNER'] = chart_data['MATCHUP'].str.split(' ').str[-1]

                chart_data['DATUM'] = chart_data['GAME_DATE'].dt.strftime('%d.%m')

                chart_data['LABEL'] = chart_data['DATUM'] + '<br>' + chart_data['GEGNER']

                fig = px.bar(
                    chart_data,
                    x='GAME_DATE',
                    y='PTS',
                    color='WL',
                    color_discrete_map={'W': '#00C851', 'L': '#ff4444'},
                    labels={'PTS': 'Punkte', 'GAME_DATE': 'Datum', 'WL': 'Ergebnis'},
                    title=f"Punkte letzte 10 Spiele - {selected_team}",
                    text='PTS',
                    hover_data=['MATCHUP']
                )

                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                )

                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Fehler: {e}")

    elif page == "⭐ Spieler Statistiken":
        st.header("⭐ Spieler Statistiken")

        # Team auswählen
        team_names = standings['TeamName'].tolist()
        selected_team = st.selectbox("Team auswählen:", team_names)
        team_row = standings[standings['TeamName'] == selected_team].iloc[0]
        team_id = team_row['TeamID']

        # Roster laden
        with st.spinner("Spieler werden geladen..."):
            try:
                roster = get_team_players(team_id)
                player_names = roster['PLAYER'].tolist()
                selected_player = st.selectbox("Spieler auswählen:", player_names)

                # Spieler ID holen
                player_row = roster[roster['PLAYER'] == selected_player].iloc[0]
                player_id = player_row['PLAYER_ID']

                # Spieler Stats laden
                with st.spinner(f"{selected_player} Daten werden geladen..."):
                    player_stats = get_player_stats(player_id)

                    # Metriken
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Punkte Ø", round(player_stats['PTS'].mean(), 1))
                    col2.metric("Rebounds Ø", round(player_stats['REB'].mean(), 1))
                    col3.metric("Assists Ø", round(player_stats['AST'].mean(), 1))
                    col4.metric("FG% Ø", f"{player_stats['FG_PCT'].mean():.1%}")

                    # Tabelle
                    st.subheader(f"Letzte 10 Spiele - {selected_player}")
                    st.dataframe(
                        player_stats[['GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST', 'FG_PCT']],
                        use_container_width=True
                    )

                    # Chart
                    st.subheader("📈 Punkte Verlauf")
                    chart_data = player_stats[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']].copy()
                    chart_data['GAME_DATE'] = pd.to_datetime(chart_data['GAME_DATE'])
                    chart_data = chart_data.sort_values('GAME_DATE').reset_index(drop=True)
                    chart_data['GEGNER'] = chart_data['MATCHUP'].str.split(' ').str[-1]
                    chart_data['DATUM'] = chart_data['GAME_DATE'].dt.strftime('%d.%m.%y')

                    fig = px.bar(
                        chart_data,
                        x='DATUM',
                        y='PTS',
                        color='WL',
                        color_discrete_map={'W': '#00C851', 'L': '#ff4444'},
                        labels={'PTS': 'Punkte', 'DATUM': 'Datum', 'WL': 'Ergebnis'},
                        title=f"Punkte letzte 10 Spiele - {selected_player}",
                        text='PTS',
                        hover_data=['MATCHUP'],
                        category_orders={'DATUM': chart_data['DATUM'].tolist()}
                    )
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='white',
                    )
                    st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Fehler: {e}")
                import traceback
                st.code(traceback.format_exc())