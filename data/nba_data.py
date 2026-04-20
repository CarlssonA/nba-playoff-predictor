from nba_api.stats.endpoints import (
    leaguestandings, teamgamelog, playergamelog,
    commonteamroster, playoffpicture, ScheduleLeagueV2
)
from nba_api.stats.static import teams
import pandas as pd
import time

SEASON = "2025-26"


def _get_schedule_df():
    """Lädt den kompletten Liga-Schedule als DataFrame."""
    time.sleep(0.5)
    schedule = ScheduleLeagueV2(season=SEASON)
    df = schedule.get_data_frames()[0]
    return df


def get_playoff_teams():
    standings = leaguestandings.LeagueStandings(season=SEASON)
    df = standings.get_data_frames()[0]
    cols = ['TeamID', 'TeamName', 'Conference', 'PlayoffRank', 'WINS', 'LOSSES', 'WinPCT']
    cols = [c for c in cols if c in df.columns]
    df = df[cols]
    df['PlayoffRank'] = pd.to_numeric(df['PlayoffRank'], errors='coerce')
    return df[df['PlayoffRank'] <= 10].copy()


def get_team_stats(team_id):
    time.sleep(0.5)
    gamelog = teamgamelog.TeamGameLog(team_id=team_id, season=SEASON)
    df = gamelog.get_data_frames()[0]
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'], errors='coerce')
    df = df.sort_values('GAME_DATE').reset_index(drop=True)
    return df.tail(10).reset_index(drop=True)


def get_team_players(team_id):
    time.sleep(0.5)
    roster = commonteamroster.CommonTeamRoster(team_id=team_id, season=SEASON)
    return roster.get_data_frames()[0]


def get_player_stats(player_id):
    time.sleep(0.5)
    gamelog = playergamelog.PlayerGameLog(player_id=player_id, season=SEASON)
    df = gamelog.get_data_frames()[0]
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'], errors='coerce')
    df = df.sort_values('GAME_DATE').reset_index(drop=True)
    return df.tail(10).reset_index(drop=True)


def get_playoff_picture():
    time.sleep(0.5)
    picture = playoffpicture.PlayoffPicture(season_id="22025")
    frames = picture.get_data_frames()
    east = frames[0][['CONFERENCE', 'HIGH_SEED_RANK', 'HIGH_SEED_TEAM',
                       'LOW_SEED_RANK', 'LOW_SEED_TEAM',
                       'HIGH_SEED_SERIES_W', 'HIGH_SEED_SERIES_L']]
    west = frames[1][['CONFERENCE', 'HIGH_SEED_RANK', 'HIGH_SEED_TEAM',
                       'LOW_SEED_RANK', 'LOW_SEED_TEAM',
                       'HIGH_SEED_SERIES_W', 'HIGH_SEED_SERIES_L']]
    total_games = east['HIGH_SEED_SERIES_W'].sum() + east['HIGH_SEED_SERIES_L'].sum()
    return {"east": east, "west": west, "playoffs_started": total_games > 0}


def get_playoff_bracket():
    """
    First-Round Bracket aus ScheduleLeagueV2.
    #8 Seeds die noch nicht feststehen (NaN) werden als 'TBD' angezeigt.
    """
    df = _get_schedule_df()
    playoffs = df[df['gameId'].str.startswith('004')].copy()

    if playoffs.empty:
        return {"east": pd.DataFrame(), "west": pd.DataFrame(), "playoffs_started": False}

    playoffs['round'] = playoffs['gameId'].str[7].astype(int)
    first_round = playoffs[playoffs['round'] == 1].copy()

    # Nur Game 1 jeder Serie
    game1s = first_round[first_round['seriesGameNumber'] == 'Game 1'].copy()

    # FIX: NaN Seeds als 0 behandeln (= TBD), keine Zeilen wegfiltern
    game1s['homeTeam_seed'] = pd.to_numeric(game1s['homeTeam_seed'], errors='coerce').fillna(0).astype(int)
    game1s['awayTeam_seed'] = pd.to_numeric(game1s['awayTeam_seed'], errors='coerce').fillna(0).astype(int)
    game1s['awayTeam_teamName'] = game1s['awayTeam_teamName'].fillna('TBD')

    # Konferenz bestimmen
    try:
        standings = get_playoff_teams()
        east_names = set(standings[standings['Conference'] == 'East']['TeamName'].tolist())
    except Exception:
        east_names = {
            'Pistons', 'Celtics', '76ers', 'Knicks', 'Hawks',
            'Cavaliers', 'Raptors', 'Magic', 'Hornets', 'Bucks',
            'Heat', 'Nets', 'Wizards', 'Bulls', 'Pacers'
        }

    east = game1s[game1s['homeTeam_teamName'].isin(east_names)].copy()
    west = game1s[~game1s['homeTeam_teamName'].isin(east_names)].copy()

    east = east.sort_values('homeTeam_seed').reset_index(drop=True)
    west = west.sort_values('homeTeam_seed').reset_index(drop=True)

    playoffs_started = playoffs['gameStatus'].astype(str).isin(['2', '3']).any()
    return {"east": east, "west": west, "playoffs_started": playoffs_started}


def get_series_standings():
    """
    Aktueller Stand jeder Playoff-Serie.
    FIX: Serien mit NaN Teamnamen (Placeholder) werden übersprungen.
    """
    df = _get_schedule_df()
    playoffs = df[df['gameId'].str.startswith('004')].copy()

    if playoffs.empty:
        return {}

    playoffs['round'] = playoffs['gameId'].str[7].astype(int)
    playoffs['series_id'] = playoffs['gameId'].str[:9]

    series = {}
    for series_id, grp in playoffs.groupby('series_id'):
        first = grp.sort_values('seriesGameNumber').iloc[0]
        home_name = first['homeTeam_teamName']
        away_name = first['awayTeam_teamName']

        # FIX: Phantom-Einträge ohne echte Teams überspringen
        if pd.isna(home_name) or pd.isna(away_name):
            continue
        if str(home_name).strip() == '' or str(away_name).strip() == '':
            continue

        rnd = int(first['gameId'][7])
        played = grp[grp['gameStatus'].astype(str) == '3']

        home_wins = 0
        away_wins = 0
        for _, game in played.iterrows():
            h_pts = game.get('homeTeam_score', 0) or 0
            a_pts = game.get('awayTeam_score', 0) or 0
            if h_pts > a_pts:
                home_wins += 1
            elif a_pts > h_pts:
                away_wins += 1

        if home_wins == 0 and away_wins == 0:
            series_text = "Series tied 0-0"
        elif home_wins == away_wins:
            series_text = f"Series tied {home_wins}-{away_wins}"
        elif home_wins > away_wins:
            series_text = f"{home_name} leads {home_wins}-{away_wins}"
        else:
            series_text = f"{away_name} leads {away_wins}-{home_wins}"

        if home_wins == 4:
            series_text = f"{home_name} wins 4-{away_wins}"
        elif away_wins == 4:
            series_text = f"{away_name} wins 4-{home_wins}"

        series[series_id] = {
            "home": home_name, "away": away_name,
            "home_wins": home_wins, "away_wins": away_wins,
            "games_played": home_wins + away_wins,
            "series_text": series_text, "round": rnd,
        }
    return series


def get_upcoming_playoff_games(n: int = 10):
    """Nächste n geplante Playoff-Spiele (gameStatus == 1)."""
    df = _get_schedule_df()
    playoffs = df[df['gameId'].str.startswith('004')].copy()

    if playoffs.empty:
        return pd.DataFrame()

    playoffs['round'] = playoffs['gameId'].str[7].astype(int)

    # FIX: Spiele ohne Teamnamen (TBD Slots) herausfiltern
    playoffs = playoffs[
        playoffs['homeTeam_teamName'].notna() &
        playoffs['awayTeam_teamName'].notna()
    ].copy()

    upcoming = playoffs[playoffs['gameStatus'].astype(str) == '1'].copy()
    upcoming = upcoming.sort_values('gameDateTimeUTC').reset_index(drop=True)

    # Seed NaN → 0 (wird in app.py als "TBD" angezeigt)
    for col in ['homeTeam_seed', 'awayTeam_seed']:
        if col in upcoming.columns:
            upcoming[col] = pd.to_numeric(upcoming[col], errors='coerce').fillna(0).astype(int)

    cols = [c for c in [
        'gameId', 'gameDateTimeUTC', 'gameStatusText',
        'homeTeam_teamName', 'homeTeam_seed',
        'awayTeam_teamName', 'awayTeam_seed',
        'seriesText', 'round'
    ] if c in upcoming.columns]

    return upcoming[cols].head(n)


def get_all_teams():
    return teams.get_teams()