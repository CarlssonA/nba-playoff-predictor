from nba_api.stats.endpoints import leaguestandings, teamgamelog
from nba_api.stats.static import teams
import pandas as pd
import time

SEASON = "2025-26"

def get_playoff_teams():
    standings = leaguestandings.LeagueStandings(season=SEASON)
    df = standings.get_data_frames()[0]
    
    cols = ['TeamID', 'TeamName', 'Conference',
            'PlayoffRank', 'WINS', 'LOSSES', 'WinPCT']
    cols = [c for c in cols if c in df.columns]
    df = df[cols]
    
    df['PlayoffRank'] = pd.to_numeric(df['PlayoffRank'], errors='coerce')
    return df[df['PlayoffRank'] <= 10].copy()

def get_team_stats(team_id):
    time.sleep(0.5)
    gamelog = teamgamelog.TeamGameLog(
        team_id=team_id,
        season=SEASON
    )
    df = gamelog.get_data_frames()[0]
    return df.head(10)

def get_all_teams():
    return teams.get_teams()