"""
bracket_simulator.py – Simuliert den kompletten NBA Playoff Bracket
Speichern unter: data/bracket_simulator.py
"""
import pandas as pd
import numpy as np
from data.ml_features import build_matchup_features, compute_win_probability
from data.nba_data import get_playoff_bracket, get_playoff_teams


def _get_team_id_map() -> dict:
    """Gibt {TeamName: TeamID} für alle Playoff-Teams zurück."""
    standings = get_playoff_teams()
    return {row['TeamName']: int(row['TeamID']) for _, row in standings.iterrows()}


def simulate_series(team1_name: str, team1_id: int,
                    team2_name: str, team2_id: int,
                    team1_home: bool = True,
                    progress_cb=None) -> dict:
    """
    Simuliert eine einzelne Serie zwischen zwei Teams.
    Gibt zurück:
    {
        winner_name, loser_name,
        winner_id, loser_id,
        prob_winner, series_score,
        series_desc, confidence, confidence_color
    }
    """
    if progress_cb:
        progress_cb(f"Analysiere: {team1_name} vs {team2_name}...")

    try:
        t1_feat, t2_feat = build_matchup_features(team1_id, team2_id, team1_home)
        result = compute_win_probability(t1_feat, t2_feat)
    except Exception as e:
        # Fallback: Home-Team gewinnt wenn Fehler
        return {
            'winner_name': team1_name, 'loser_name': team2_name,
            'winner_id': team1_id, 'loser_id': team2_id,
            'prob_winner': 0.55, 'series_score': '4-3',
            'series_desc': 'knapp', 'confidence': 'Sehr knapp',
            'confidence_color': '🟡', 'error': str(e),
        }

    if result['winner'] == 't1':
        winner_name, winner_id = team1_name, team1_id
        loser_name, loser_id = team2_name, team2_id
        prob_winner = result['prob_t1']
    else:
        winner_name, winner_id = team2_name, team2_id
        loser_name, loser_id = team1_name, team1_id
        prob_winner = result['prob_t2']

    return {
        'winner_name': winner_name, 'winner_id': winner_id,
        'loser_name': loser_name, 'loser_id': loser_id,
        'prob_winner': prob_winner,
        'series_score': result['series_score'],
        'series_desc': result['series_desc'],
        'confidence': result['confidence'],
        'confidence_color': result['confidence_color'],
    }


def simulate_full_bracket(progress_cb=None) -> dict:
    """
    Simuliert den kompletten Playoff-Bracket Runde für Runde.

    Gibt zurück:
    {
        'east': {
            'round1': [serie1, serie2, serie3, serie4],
            'round2': [serie1, serie2],
            'round3': [serie1],
        },
        'west': { ... },
        'finals': serie,
        'champion': team_name,
    }
    """
    # ── Bracket laden ──────────────────────────────────────────────────────────
    if progress_cb:
        progress_cb("Lade Playoff Bracket...")

    bracket_data = get_playoff_bracket()
    team_id_map = _get_team_id_map()

    def get_id(name):
        return team_id_map.get(name, 0)

    def build_matchups(df):
        """Erstellt Liste von (home_name, home_id, away_name, away_id) aus DataFrame."""
        matchups = []
        for _, row in df.iterrows():
            home = row.get('homeTeam_teamName', 'TBD')
            away = row.get('awayTeam_teamName', 'TBD')
            if home == 'TBD' or away == 'TBD':
                continue
            matchups.append((home, get_id(home), away, get_id(away)))
        return matchups

    east_r1_matchups = build_matchups(bracket_data['east'])
    west_r1_matchups = build_matchups(bracket_data['west'])

    results = {'east': {}, 'west': {}}

    # ── Konferenz simulieren ───────────────────────────────────────────────────
    for conf, r1_matchups in [('east', east_r1_matchups), ('west', west_r1_matchups)]:

        # Round 1: 4 Serien
        if progress_cb:
            progress_cb(f"Simuliere {'Eastern' if conf=='east' else 'Western'} Conference First Round...")

        r1_results = []
        for home, home_id, away, away_id in r1_matchups:
            s = simulate_series(home, home_id, away, away_id,
                                team1_home=True, progress_cb=progress_cb)
            s['home_name'] = home
            s['away_name'] = away
            r1_results.append(s)
        results[conf]['round1'] = r1_results

        # Round 2: Semifinals – Gewinner 1v4 spielt gegen Gewinner 2v3
        if progress_cb:
            progress_cb(f"Simuliere {'Eastern' if conf=='east' else 'Western'} Conference Semifinals...")

        r2_results = []
        # Matchup: Gewinner Serie 1 (1v8) vs Gewinner Serie 4 (4v5)
        # Matchup: Gewinner Serie 2 (2v7) vs Gewinner Serie 3 (3v6)
        pairs = [(0, 3), (1, 2)]  # Indices in r1_results
        for i, j in pairs:
            if i < len(r1_results) and j < len(r1_results):
                w1 = r1_results[i]
                w2 = r1_results[j]
                # Höherer Seed hat Home Court (wer hatte niedrigere Seed-Nummer in R1)
                s = simulate_series(
                    w1['winner_name'], w1['winner_id'],
                    w2['winner_name'], w2['winner_id'],
                    team1_home=True, progress_cb=progress_cb
                )
                s['home_name'] = w1['winner_name']
                s['away_name'] = w2['winner_name']
                r2_results.append(s)
        results[conf]['round2'] = r2_results

        # Round 3: Conference Finals
        if progress_cb:
            progress_cb(f"Simuliere {'Eastern' if conf=='east' else 'Western'} Conference Finals...")

        if len(r2_results) >= 2:
            w1 = r2_results[0]
            w2 = r2_results[1]
            conf_final = simulate_series(
                w1['winner_name'], w1['winner_id'],
                w2['winner_name'], w2['winner_id'],
                team1_home=True, progress_cb=progress_cb
            )
            conf_final['home_name'] = w1['winner_name']
            conf_final['away_name'] = w2['winner_name']
            results[conf]['round3'] = [conf_final]
        else:
            results[conf]['round3'] = []

    # ── NBA Finals ─────────────────────────────────────────────────────────────
    if progress_cb:
        progress_cb("Simuliere NBA Finals...")

    east_finalist = results['east']['round3'][0] if results['east'].get('round3') else None
    west_finalist = results['west']['round3'][0] if results['west'].get('round3') else None

    if east_finalist and west_finalist:
        finals = simulate_series(
            east_finalist['winner_name'], east_finalist['winner_id'],
            west_finalist['winner_name'], west_finalist['winner_id'],
            team1_home=True, progress_cb=progress_cb
        )
        finals['home_name'] = east_finalist['winner_name']
        finals['away_name'] = west_finalist['winner_name']
        results['finals'] = finals
        results['champion'] = finals['winner_name']
    else:
        results['finals'] = None
        results['champion'] = 'TBD'

    return results