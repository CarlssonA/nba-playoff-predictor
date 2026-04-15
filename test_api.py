from nba_api.stats.endpoints import leaguestandings

# Teste verschiedene Saison-Formate
for season in ["2025-26", "2024-25", "2025"]:
    try:
        standings = leaguestandings.LeagueStandings(season=season)
        df = standings.get_data_frames()[0]
        print(f"✅ Saison {season} funktioniert! Zeilen: {len(df)}")
        break
    except Exception as e:
        print(f"❌ Saison {season} fehlgeschlagen: {e}")