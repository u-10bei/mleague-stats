"""
Mリーグダッシュボード データベース初期化スクリプト

このスクリプトは以下を実行します：
1. データベースの作成（既存の場合は削除）
2. 全テーブルの作成
3. チームマスターデータの投入
4. チーム名の投入（2024シーズン）
5. サンプルデータの投入（オプション）

使い方:
  python init_db.py              # チームマスターのみ投入
  python init_db.py --with-sample # サンプルデータも投入
"""

import sqlite3
import os
import sys

DB_PATH = "data/mleague.db"

def init_database(with_sample=False):
    """データベースを初期化"""
    
    # データディレクトリの作成
    os.makedirs("data", exist_ok=True)
    
    # 既存のデータベースを削除
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"既存のデータベース {DB_PATH} を削除しました")
    
    # 接続を作成
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("データベーステーブルを作成中...")
    
    # ========== チーム関連テーブル ==========
    
    # チームマスターテーブル
    cursor.execute("""
        CREATE TABLE teams (
            team_id INTEGER PRIMARY KEY,
            short_name TEXT NOT NULL,
            color TEXT NOT NULL,
            established INTEGER NOT NULL
        )
    """)
    print("✓ teams テーブルを作成しました")
    
    # チーム名履歴テーブル
    cursor.execute("""
        CREATE TABLE team_names (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            team_name TEXT NOT NULL,
            FOREIGN KEY (team_id) REFERENCES teams (team_id) ON DELETE CASCADE,
            UNIQUE (team_id, season)
        )
    """)
    print("✓ team_names テーブルを作成しました")
    
    # チームシーズンポイントテーブル
    cursor.execute("""
        CREATE TABLE team_season_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            points REAL NOT NULL,
            rank INTEGER NOT NULL,
            FOREIGN KEY (team_id) REFERENCES teams (team_id) ON DELETE CASCADE,
            UNIQUE (season, team_id)
        )
    """)
    print("✓ team_season_points テーブルを作成しました")
    
    # ========== 選手関連テーブル ==========
    
    # 選手マスターテーブル
    cursor.execute("""
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL UNIQUE,
            birth_date TEXT,
            pro_org TEXT
        )
    """)
    print("✓ players テーブルを作成しました")
    
    # 選手所属チームテーブル
    cursor.execute("""
        CREATE TABLE player_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players (player_id) ON DELETE CASCADE,
            FOREIGN KEY (team_id) REFERENCES teams (team_id) ON DELETE CASCADE,
            UNIQUE (player_id, season)
        )
    """)
    print("✓ player_teams テーブルを作成しました")
    
    # 選手シーズン成績テーブル
    cursor.execute("""
        CREATE TABLE player_season_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            games INTEGER DEFAULT 0,
            points REAL DEFAULT 0,
            rank_1st INTEGER DEFAULT 0,
            rank_2nd INTEGER DEFAULT 0,
            rank_3rd INTEGER DEFAULT 0,
            rank_4th INTEGER DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players (player_id) ON DELETE CASCADE,
            UNIQUE (player_id, season)
        )
    """)
    print("✓ player_season_stats テーブルを作成しました")
    
    print("\nチームマスターデータを投入中...")
    
    # ========== チームデータ投入 ==========
    
    teams_data = [
        # team_id, short_name, color, established
        (1, "ドリブンズ", "#e8f6fd", 2018),
        (2, "風林火山", "#800000", 2018),
        (3, "麻雀格闘倶楽部", "#ff6d8b", 2018),
        (4, "ABEMAS", "#E48D7A", 2018),
        (5, "フェニックス", "#F27100", 2018),
        (6, "雷電", "#8628b3", 2018),
        (7, "Pirates", "#161666", 2018),
        (8, "サクラナイツ", "#ffc5f5", 2019),
        (9, "BEAST", "#009FA0", 2023),
        (10, "JETS", "#626046", 2025),
    ]
    
    cursor.executemany("""
        INSERT INTO teams (team_id, short_name, color, established)
        VALUES (?, ?, ?, ?)
    """, teams_data)
    
    print(f"✓ {len(teams_data)}チームのマスターデータを投入しました")
    
    # ========== チーム名データ投入（2018シーズン） ==========
    
    print("\nチーム名データを投入中...")
    
    team_names_data = [
        # team_id, season, team_name
        (1, 2018, "赤坂ドリブンズ"),
        (2, 2018, "EX風林火山"),
        (3, 2018, "KONAMI麻雀格闘倶楽部"),
        (4, 2018, "渋谷ABEMAS"),
        (5, 2018, "セガサミーフェニックス"),
        (6, 2018, "TEAM RAIDEN / 雷電"),
        (7, 2018, "U-NEXT Pirates"),
    ]
    
    cursor.executemany("""
        INSERT INTO team_names (team_id, season, team_name)
        VALUES (?, ?, ?)
    """, team_names_data)
    
    print(f"✓ {len(team_names_data)}チームの名前データを投入しました（2018シーズン）")
    
    # ========== サンプルデータ投入（オプション） ==========
    
    if with_sample:
        print("\n" + "="*60)
        print("サンプルデータを投入中...")
        print("="*60)
        
        # チームシーズンポイント（2018シーズン）
        print("\nチームシーズンポイントを投入中...")
        sample_team_points = [
            # season, team_id, points, rank
            (2018, 1, 123.4, 1),
            (2018, 2, 89.2, 2),
            (2018, 3, 67.8, 3),
            (2018, 4, 45.6, 4),
            (2018, 5, 34.5, 5),
            (2018, 6, -12.3, 6),
            (2018, 7, -34.5, 7),
        ]
        
        cursor.executemany("""
            INSERT INTO team_season_points (season, team_id, points, rank)
            VALUES (?, ?, ?, ?)
        """, sample_team_points)
        
        print(f"✓ {len(sample_team_points)}件のチームポイントを投入しました")
        
        # サンプル選手データ（各チーム4名）
        print("\nサンプル選手データを投入中...")
        sample_players = [
            # player_name, birth_date, pro_org
            ("選手A-1", "1990-01-01", "日本プロ麻雀協会"),
            ("選手A-2", "1991-02-02", "日本プロ麻雀協会"),
            ("選手A-3", "1992-03-03", "日本プロ麻雀連盟"),
            ("選手A-4", "1993-04-04", "最高位戦日本プロ麻雀協会"),
            ("選手B-1", "1990-05-05", "日本プロ麻雀協会"),
            ("選手B-2", "1991-06-06", "日本プロ麻雀連盟"),
            ("選手B-3", "1992-07-07", "最高位戦日本プロ麻雀協会"),
            ("選手B-4", "1993-08-08", "RMU"),
        ]
        
        cursor.executemany("""
            INSERT INTO players (player_name, birth_date, pro_org)
            VALUES (?, ?, ?)
        """, sample_players)
        
        print(f"✓ {len(sample_players)}名の選手データを投入しました")
        
        # 選手所属データ（2018シーズン）
        print("\n選手所属データを投入中...")
        sample_player_teams = [
            # player_id, team_id, season
            (1, 1, 2018), (2, 1, 2018), (3, 1, 2018), (4, 1, 2018),  # 赤坂ドリブンズ
            (5, 2, 2018), (6, 2, 2018), (7, 2, 2018), (8, 2, 2018),  # EX風林火山
        ]
        
        cursor.executemany("""
            INSERT INTO player_teams (player_id, team_id, season)
            VALUES (?, ?, ?)
        """, sample_player_teams)
        
        print(f"✓ {len(sample_player_teams)}件の選手所属データを投入しました")
        
        # 選手成績データ（2018シーズン）
        print("\n選手成績データを投入中...")
        sample_player_stats = [
            # player_id, season, games, points, rank_1st, rank_2nd, rank_3rd, rank_4th
            (1, 2018, 48, 156.3, 15, 14, 12, 7),
            (2, 2018, 48, 89.7, 12, 15, 13, 8),
            (3, 2018, 48, 45.2, 10, 16, 14, 8),
            (4, 2018, 48, -23.4, 8, 14, 15, 11),
            (5, 2018, 48, 123.5, 14, 15, 12, 7),
            (6, 2018, 48, 67.8, 11, 16, 13, 8),
            (7, 2018, 48, 34.2, 9, 15, 15, 9),
            (8, 2018, 48, -12.3, 8, 13, 16, 11),
        ]
        
        cursor.executemany("""
            INSERT INTO player_season_stats (player_id, season, games, points, rank_1st, rank_2nd, rank_3rd, rank_4th)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_player_stats)
        
        print(f"✓ {len(sample_player_stats)}件の選手成績データを投入しました")
    
    # コミットして接続を閉じる
    conn.commit()
    conn.close()
    
    print("\n" + "="*60)
    print("✅ データベースの初期化が完了しました！")
    print("="*60)
    print(f"\nデータベース: {DB_PATH}")
    print("\n【投入されたデータ】")
    print(f"  • チーム: {len(teams_data)}チーム")
    print(f"  • チーム名: {len(team_names_data)}件（2018シーズン）")
    
    if with_sample:
        print(f"  • チームポイント: {len(sample_team_points)}件（2018シーズン）")
        print(f"  • 選手: {len(sample_players)}名")
        print(f"  • 選手所属: {len(sample_player_teams)}件（2018シーズン）")
        print(f"  • 選手成績: {len(sample_player_stats)}件（2018シーズン）")
    
    print("\n【次のステップ】")
    if with_sample:
        print("  1. アプリを起動: streamlit run app.py")
        print("  2. 年度別チームランキングで2018シーズンのサンプルデータを確認")
        print("  3. 年度別選手ランキングで2018シーズンのサンプルデータを確認")
        print("  4. シーズン更新ページで2019, 2020...と順次追加")
        print("  5. データ管理ページで各シーズンのポイントを入力")
    else:
        print("  1. アプリを起動: streamlit run app.py")
        print("  2. データ管理ページで2018シーズンのポイントを入力")
        print("  3. 選手管理ページで2018シーズンの選手を登録")
        print("  4. 選手成績入力ページで2018シーズンの選手成績を入力")
        print("  5. シーズン更新ページで2019シーズンを追加")
        print("  6. 上記を繰り返して2020, 2021...と順次追加")
    print("\n" + "="*60)

if __name__ == "__main__":
    # コマンドライン引数をチェック
    with_sample = "--with-sample" in sys.argv or "-s" in sys.argv
    
    if with_sample:
        print("📝 サンプルデータ付きで初期化します")
    else:
        print("📝 チームマスターデータのみで初期化します")
        print("   （サンプルデータも投入する場合: python init_db.py --with-sample）")
    
    print()
    init_database(with_sample=with_sample)
