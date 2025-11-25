import sqlite3

DB_PATH = "data/mleague.db"

def migrate_add_player_tables():
    """既存データを保持しつつ、選手関連テーブルを追加"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
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
    
    conn.commit()
    conn.close()
    print("選手関連テーブルを追加しました")

if __name__ == "__main__":
    migrate_add_player_tables()
