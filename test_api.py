"""
test_api.py – Testet get_playoff_bracket() und get_upcoming_playoff_games()
Ausführen: python test_api.py
"""
from data.nba_data import get_playoff_bracket, get_series_standings, get_upcoming_playoff_games
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

# ── Test 1: Playoff Bracket ────────────────────────────────────────────────────
print("=" * 60)
print("TEST 1: get_playoff_bracket()")
print("=" * 60)

data = get_playoff_bracket()
print(f"playoffs_started: {data['playoffs_started']}")

print("\nEAST First Round:")
if not data['east'].empty:
    cols = [c for c in ['homeTeam_teamName', 'homeTeam_seed',
                         'awayTeam_teamName', 'awayTeam_seed',
                         'seriesText', 'gameId'] if c in data['east'].columns]
    print(data['east'][cols].to_string(index=False))
else:
    print("  (leer – noch keine Daten)")

print("\nWEST First Round:")
if not data['west'].empty:
    cols = [c for c in ['homeTeam_teamName', 'homeTeam_seed',
                         'awayTeam_teamName', 'awayTeam_seed',
                         'seriesText', 'gameId'] if c in data['west'].columns]
    print(data['west'][cols].to_string(index=False))
else:
    print("  (leer – noch keine Daten)")

# ── Test 2: Series Stände ──────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("TEST 2: get_series_standings()")
print("=" * 60)

series = get_series_standings()
if series:
    for sid, s in series.items():
        print(f"  {s['home']} vs {s['away']} | {s['series_text']} | Round {s['round']}")
else:
    print("  (noch keine gespielten Spiele)")

# ── Test 3: Upcoming Games ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("TEST 3: get_upcoming_playoff_games(n=5)")
print("=" * 60)

upcoming = get_upcoming_playoff_games(n=5)
if not upcoming.empty:
    cols = [c for c in ['gameDateTimeUTC', 'homeTeam_teamName', 'homeTeam_seed',
                         'awayTeam_teamName', 'awayTeam_seed',
                         'seriesText', 'round'] if c in upcoming.columns]
    print(upcoming[cols].to_string(index=False))
else:
    print("  (keine anstehenden Spiele gefunden)")

print("\n✅ Alle Tests abgeschlossen.")