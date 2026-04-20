"""
ml_features.py – Feature Engineering für NBA Playoff Vorhersagen
Speichern unter: data/ml_features.py
"""
from nba_api.stats.endpoints import (
    leaguestandings, teamgamelog, playergamelog,
    commonteamroster, leaguedashteamstats, leaguedashplayerstats
)
import pandas as pd
import numpy as np
import time

SEASON = "2025-26"


def get_team_advanced_stats(team_id: int) -> dict:
    """
    Holt erweiterte Team-Stats aus den letzten Spielen.
    Returns dict mit Features für ML Modell.
    """
    time.sleep(0.6)
    gamelog = teamgamelog.TeamGameLog(team_id=team_id, season=SEASON)
    df = gamelog.get_data_frames()[0]

    if df.empty:
        return {}

    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'], errors='coerce')
    df = df.sort_values('GAME_DATE')

    # Letzte 10 Spiele (reguläre Saison Form)
    last10 = df.tail(10)
    # Letzte 20 Spiele (längerfristiger Trend)
    last20 = df.tail(20)

    def win_pct(frame):
        if frame.empty:
            return 0.5
        return (frame['WL'] == 'W').sum() / len(frame)

    def avg(frame, col):
        if col not in frame.columns or frame.empty:
            return 0.0
        return float(frame[col].mean())

    # Home/Away Split
    home_games = df[df['MATCHUP'].str.contains('vs\.', na=False)]
    away_games = df[df['MATCHUP'].str.contains('@', na=False)]

    features = {
        # Form
        'win_pct_last10': win_pct(last10),
        'win_pct_last20': win_pct(last20),
        'win_pct_season': win_pct(df),

        # Offense
        'pts_avg_last10': avg(last10, 'PTS'),
        'pts_avg_season': avg(df, 'PTS'),
        'fg_pct_last10': avg(last10, 'FG_PCT'),
        'fg3_pct_last10': avg(last10, 'FG3_PCT'),
        'ft_pct_last10': avg(last10, 'FT_PCT'),
        'ast_avg_last10': avg(last10, 'AST'),

        # Defense / Rebounding
        'reb_avg_last10': avg(last10, 'REB'),
        'stl_avg_last10': avg(last10, 'STL'),
        'blk_avg_last10': avg(last10, 'BLK'),
        'tov_avg_last10': avg(last10, 'TOV'),

        # Point differential (wichtigstes Feature!)
        'plus_minus_avg_last10': avg(last10, 'PLUS_MINUS'),
        'plus_minus_avg_season': avg(df, 'PLUS_MINUS'),

        # Home/Away
        'home_win_pct': win_pct(home_games),
        'away_win_pct': win_pct(away_games),
    }

    return features


def get_top_players_stats(team_id: int, n_players: int = 3) -> dict:
    """
    Holt Stats der Top-N Spieler (nach Punkten) eines Teams.
    Returns dict mit aggregierten Features.
    """
    time.sleep(0.6)
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=team_id, season=SEASON)
        roster_df = roster.get_data_frames()[0]
    except Exception:
        return {}

    id_col = next((c for c in ['PLAYER_ID', 'PlayerId'] if c in roster_df.columns), None)
    name_col = next((c for c in ['PLAYER', 'PlayerName', 'PLAYER_NAME'] if c in roster_df.columns), None)

    if not id_col or not name_col:
        return {}

    player_stats_list = []
    for _, player in roster_df.head(12).iterrows():  # Nur erste 12 um API-Calls zu sparen
        try:
            time.sleep(0.4)
            gamelog = playergamelog.PlayerGameLog(
                player_id=player[id_col], season=SEASON
            )
            pdf = gamelog.get_data_frames()[0]
            if pdf.empty or len(pdf) < 5:
                continue
            player_stats_list.append({
                'name': player[name_col],
                'pts': float(pdf['PTS'].mean()),
                'reb': float(pdf['REB'].mean()),
                'ast': float(pdf['AST'].mean()),
                'fg_pct': float(pdf['FG_PCT'].mean()),
                'plus_minus': float(pdf['PLUS_MINUS'].mean()) if 'PLUS_MINUS' in pdf.columns else 0.0,
                'games': len(pdf),
            })
        except Exception:
            continue

    if not player_stats_list:
        return {}

    # Top N nach Punkten
    player_stats_list.sort(key=lambda x: x['pts'], reverse=True)
    top_n = player_stats_list[:n_players]

    features = {}
    for i, p in enumerate(top_n):
        prefix = f'star{i+1}'
        features[f'{prefix}_pts'] = p['pts']
        features[f'{prefix}_reb'] = p['reb']
        features[f'{prefix}_ast'] = p['ast']
        features[f'{prefix}_fg_pct'] = p['fg_pct']
        features[f'{prefix}_plus_minus'] = p['plus_minus']

    # Aggregierte Top-3 Features
    features['top3_pts_sum'] = sum(p['pts'] for p in top_n)
    features['top3_plus_minus_avg'] = np.mean([p['plus_minus'] for p in top_n])
    features['star_players'] = top_n  # Für Anzeige in App

    return features


def build_matchup_features(team1_id: int, team2_id: int,
                            team1_home: bool = True) -> tuple[dict, dict]:
    """
    Baut Feature-Vektoren für beide Teams eines Matchups.
    Returns (team1_features, team2_features) als dicts.
    """
    print(f"  Lade Team 1 Stats...")
    t1_team = get_team_advanced_stats(team1_id)
    print(f"  Lade Team 1 Spieler...")
    t1_players = get_top_players_stats(team1_id)

    print(f"  Lade Team 2 Stats...")
    t2_team = get_team_advanced_stats(team2_id)
    print(f"  Lade Team 2 Spieler...")
    t2_players = get_top_players_stats(team2_id)

    t1 = {**t1_team, **t1_players, 'is_home': 1 if team1_home else 0}
    t2 = {**t2_team, **t2_players, 'is_home': 0 if team1_home else 1}

    return t1, t2


def compute_win_probability(t1_features: dict, t2_features: dict) -> dict:
    """
    Berechnet Win-Wahrscheinlichkeiten basierend auf Feature-Differenzen.
    Verwendet gewichtete Formel statt trainiertem Modell
    (kein historischer Datensatz vorhanden).

    Returns dict mit Wahrscheinlichkeiten und Confidence.
    """
    def safe_diff(key, weight=1.0, higher_better=True):
        v1 = t1_features.get(key, 0) or 0
        v2 = t2_features.get(key, 0) or 0
        diff = (v1 - v2) if higher_better else (v2 - v1)
        return diff * weight

    # Gewichtete Feature-Differenzen (Team 1 Vorteil wenn positiv)
    score = 0.0
    score += safe_diff('plus_minus_avg_last10',  weight=3.0)   # Wichtigstes: Point Diff
    score += safe_diff('plus_minus_avg_season',   weight=1.5)
    score += safe_diff('win_pct_last10',          weight=4.0)   # Aktuelle Form
    score += safe_diff('win_pct_season',          weight=2.0)
    score += safe_diff('pts_avg_last10',          weight=0.05)
    score += safe_diff('fg_pct_last10',           weight=2.0)
    score += safe_diff('fg3_pct_last10',          weight=1.5)
    score += safe_diff('ast_avg_last10',          weight=0.3)
    score += safe_diff('reb_avg_last10',          weight=0.3)
    score += safe_diff('stl_avg_last10',          weight=0.5)
    score += safe_diff('blk_avg_last10',          weight=0.3)
    score += safe_diff('tov_avg_last10',          weight=0.5, higher_better=False)
    score += safe_diff('top3_pts_sum',            weight=0.08)  # Star Power
    score += safe_diff('top3_plus_minus_avg',     weight=1.0)
    score += safe_diff('star1_pts',               weight=0.1)

    # Home-Court Vorteil
    home_advantage = 0.3
    if t1_features.get('is_home'):
        score += home_advantage
    else:
        score -= home_advantage

    # Sigmoid → Wahrscheinlichkeit
    import math
    prob_t1 = 1 / (1 + math.exp(-score * 0.4))
    prob_t2 = 1 - prob_t1

    # Confidence: wie weit von 50/50 entfernt?
    distance = abs(prob_t1 - 0.5)
    if distance < 0.05:
        confidence = "Sehr knapp"
        confidence_color = "🟡"
    elif distance < 0.12:
        confidence = "Knapp"
        confidence_color = "🟡"
    elif distance < 0.20:
        confidence = "Moderat"
        confidence_color = "🟠"
    else:
        confidence = "Deutlich"
        confidence_color = "🔴"

    # Series Score Vorhersage (basierend auf Stärkeunterschied)
    def predict_series_score(win_prob):
        """Schätzt Series Score (4-x) basierend auf Win-Wahrscheinlichkeit."""
        if win_prob >= 0.80:
            return "4-0", "Sweep"
        elif win_prob >= 0.68:
            return "4-1", "dominant"
        elif win_prob >= 0.58:
            return "4-2", "klar"
        elif win_prob >= 0.52:
            return "4-3", "knapp"
        else:
            return "4-3", "sehr knapp"

    if prob_t1 >= prob_t2:
        winner = 't1'
        series_score, series_desc = predict_series_score(prob_t1)
    else:
        winner = 't2'
        series_score, series_desc = predict_series_score(prob_t2)

    return {
        'prob_t1': round(prob_t1, 3),
        'prob_t2': round(prob_t2, 3),
        'winner': winner,
        'series_score': series_score,
        'series_desc': series_desc,
        'confidence': confidence,
        'confidence_color': confidence_color,
        'raw_score': round(score, 3),
    }