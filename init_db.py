import sqlite3

DB_PATH = "data/mleague.db"

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # テーブル作成
    # チームマスター（チームIDで管理）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY,
            short_name TEXT NOT NULL,
            color TEXT NOT NULL,
            established INTEGER NOT NULL
        )
    """)
    
    # チーム名履歴（年度ごとのチーム名）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_names (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            team_name TEXT NOT NULL,
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            UNIQUE(team_id, season)
        )
    """)
    
    # シーズンポイント（team_idで管理）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_season_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            points REAL NOT NULL,
            rank INTEGER NOT NULL,
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            UNIQUE(season, team_id)
        )
    """)
    
    # 選手マスター
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            birth_date TEXT,
            pro_org TEXT
        )
    """)
    
    # 選手所属履歴（年度ごとの所属チーム）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players(player_id),
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            UNIQUE(player_id, season)
        )
    """)
    
    # 選手シーズン成績
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_season_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            games INTEGER DEFAULT 0,
            points REAL DEFAULT 0,
            rank_1st INTEGER DEFAULT 0,
            rank_2nd INTEGER DEFAULT 0,
            rank_3rd INTEGER DEFAULT 0,
            rank_4th INTEGER DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players(player_id),
            UNIQUE(player_id, season)
        )
    """)
    
    # チームデータ投入
    teams_data = [
        (1, "格闘倶楽部", "#FFD700", 2018),
        (2, "ドリブンズ", "#DC143C", 2018),
        (3, "ABEMAS", "#4169E1", 2018),
        (4, "フェニックス", "#FF4500", 2018),
        (5, "風林火山", "#228B22", 2018),
        (6, "Pirates", "#800080", 2018),
        (7, "雷電", "#000080", 2018),
        (8, "サクラナイツ", "#FF69B4", 2019),
    ]
    
    cursor.execute("DELETE FROM teams")
    cursor.executemany(
        "INSERT INTO teams (team_id, short_name, color, established) VALUES (?, ?, ?, ?)",
        teams_data
    )
    
    # チーム名履歴データ投入（年度ごとの正式名称）
    team_names_data = [
        # KONAMI麻雀格闘倶楽部
        (1, 2018, "KONAMI麻雀格闘倶楽部"),
        (1, 2019, "KONAMI麻雀格闘倶楽部"),
        (1, 2020, "KONAMI麻雀格闘倶楽部"),
        (1, 2021, "KONAMI麻雀格闘倶楽部"),
        (1, 2022, "KONAMI麻雀格闘倶楽部"),
        (1, 2023, "KONAMI麻雀格闘倶楽部"),
        # 赤坂ドリブンズ
        (2, 2018, "赤坂ドリブンズ"),
        (2, 2019, "赤坂ドリブンズ"),
        (2, 2020, "赤坂ドリブンズ"),
        (2, 2021, "赤坂ドリブンズ"),
        (2, 2022, "赤坂ドリブンズ"),
        (2, 2023, "赤坂ドリブンズ"),
        # 渋谷ABEMAS
        (3, 2018, "渋谷ABEMAS"),
        (3, 2019, "渋谷ABEMAS"),
        (3, 2020, "渋谷ABEMAS"),
        (3, 2021, "渋谷ABEMAS"),
        (3, 2022, "渋谷ABEMAS"),
        (3, 2023, "渋谷ABEMAS"),
        # セガサミーフェニックス
        (4, 2018, "セガサミーフェニックス"),
        (4, 2019, "セガサミーフェニックス"),
        (4, 2020, "セガサミーフェニックス"),
        (4, 2021, "セガサミーフェニックス"),
        (4, 2022, "セガサミーフェニックス"),
        (4, 2023, "セガサミーフェニックス"),
        # EX風林火山
        (5, 2018, "EX風林火山"),
        (5, 2019, "EX風林火山"),
        (5, 2020, "EX風林火山"),
        (5, 2021, "EX風林火山"),
        (5, 2022, "EX風林火山"),
        (5, 2023, "EX風林火山"),
        # U-NEXT Pirates
        (6, 2018, "U-NEXT Pirates"),
        (6, 2019, "U-NEXT Pirates"),
        (6, 2020, "U-NEXT Pirates"),
        (6, 2021, "U-NEXT Pirates"),
        (6, 2022, "U-NEXT Pirates"),
        (6, 2023, "U-NEXT Pirates"),
        # TEAM RAIDEN / 雷電
        (7, 2018, "TEAM RAIDEN / 雷電"),
        (7, 2019, "TEAM RAIDEN / 雷電"),
        (7, 2020, "TEAM RAIDEN / 雷電"),
        (7, 2021, "TEAM RAIDEN / 雷電"),
        (7, 2022, "TEAM RAIDEN / 雷電"),
        (7, 2023, "TEAM RAIDEN / 雷電"),
        # KADOKAWAサクラナイツ
        (8, 2019, "KADOKAWAサクラナイツ"),
        (8, 2020, "KADOKAWAサクラナイツ"),
        (8, 2021, "KADOKAWAサクラナイツ"),
        (8, 2022, "KADOKAWAサクラナイツ"),
        (8, 2023, "KADOKAWAサクラナイツ"),
    ]
    
    cursor.execute("DELETE FROM team_names")
    cursor.executemany(
        "INSERT INTO team_names (team_id, season, team_name) VALUES (?, ?, ?)",
        team_names_data
    )
    
    # シーズンポイントデータ投入（team_idで管理）
    season_points_data = [
        (2018, 1, 312.4, 1),
        (2018, 2, 189.7, 2),
        (2018, 3, 95.3, 3),
        (2018, 4, 48.2, 4),
        (2018, 5, -87.5, 5),
        (2018, 6, -234.1, 6),
        (2018, 7, -324.0, 7),
        (2019, 2, 275.8, 1),
        (2019, 3, 201.4, 2),
        (2019, 5, 156.2, 3),
        (2019, 4, 89.1, 4),
        (2019, 1, -45.3, 5),
        (2019, 6, -178.6, 6),
        (2019, 7, -256.9, 7),
        (2019, 8, -241.7, 8),
        (2020, 3, 453.2, 1),
        (2020, 8, 287.6, 2),
        (2020, 5, 134.8, 3),
        (2020, 4, 67.4, 4),
        (2020, 1, -89.2, 5),
        (2020, 2, -198.5, 6),
        (2020, 6, -267.3, 7),
        (2020, 7, -388.0, 8),
        (2021, 8, 398.7, 1),
        (2021, 3, 234.1, 2),
        (2021, 1, 178.5, 3),
        (2021, 4, 45.2, 4),
        (2021, 5, -67.8, 5),
        (2021, 2, -189.4, 6),
        (2021, 6, -287.6, 7),
        (2021, 7, -311.7, 8),
        (2022, 1, 356.8, 1),
        (2022, 3, 278.4, 2),
        (2022, 4, 189.3, 3),
        (2022, 8, 45.7, 4),
        (2022, 2, -78.2, 5),
        (2022, 5, -156.9, 6),
        (2022, 6, -298.4, 7),
        (2022, 7, -336.7, 8),
        (2023, 4, 412.5, 1),
        (2023, 3, 298.7, 2),
        (2023, 1, 167.3, 3),
        (2023, 8, 89.4, 4),
        (2023, 2, -45.8, 5),
        (2023, 5, -189.2, 6),
        (2023, 7, -312.6, 7),
        (2023, 6, -420.3, 8),
    ]
    
    cursor.execute("DELETE FROM team_season_points")
    cursor.executemany(
        "INSERT INTO team_season_points (season, team_id, points, rank) VALUES (?, ?, ?, ?)",
        season_points_data
    )
    
    conn.commit()
    conn.close()
    print("データベースを初期化しました: ", DB_PATH)

if __name__ == "__main__":
    init_database()
