import sqlite3
import pandas as pd

DB_PATH = "data/mleague.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_teams():
    """チームマスター情報を取得"""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM teams ORDER BY team_id", conn)
    conn.close()
    return df

def get_team_colors():
    """チームIDとカラーのマッピングを取得"""
    teams_df = get_teams()
    return dict(zip(teams_df["team_id"], teams_df["color"]))

def get_team_name(team_id, season):
    """指定シーズンのチーム名を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT team_name FROM team_names WHERE team_id = ? AND season = ?",
        (team_id, season)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]
    
    # 見つからない場合は最新のチーム名を返す
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT team_name FROM team_names WHERE team_id = ? ORDER BY season DESC LIMIT 1",
        (team_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else f"Team {team_id}"

def get_current_team_name(team_id):
    """チームの最新の名前を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT team_name FROM team_names WHERE team_id = ? ORDER BY season DESC LIMIT 1",
        (team_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else f"Team {team_id}"

def get_team_names_for_season(season):
    """指定シーズンの全チーム名を取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT tn.team_id, tn.team_name, t.short_name, t.color
        FROM team_names tn
        JOIN teams t ON tn.team_id = t.team_id
        WHERE tn.season = ?
    """, conn, params=(season,))
    conn.close()
    return df

def get_all_team_names():
    """全チーム名履歴を取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT tn.*, t.short_name, t.color
        FROM team_names tn
        JOIN teams t ON tn.team_id = t.team_id
        ORDER BY tn.team_id, tn.season
    """, conn)
    conn.close()
    return df

def get_season_points():
    """全シーズンポイントをチーム名付きで取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT 
            sp.season,
            sp.team_id,
            tn.team_name,
            sp.points,
            sp.rank
        FROM team_season_points sp
        JOIN team_names tn ON sp.team_id = tn.team_id AND sp.season = tn.season
        ORDER BY sp.season DESC, sp.rank
    """, conn)
    conn.close()
    return df

def get_seasons():
    """シーズン一覧を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT season FROM team_season_points ORDER BY season DESC")
    seasons = [row[0] for row in cursor.fetchall()]
    conn.close()
    return seasons

def get_season_data(season):
    """指定シーズンのデータを取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT 
            sp.season,
            sp.team_id,
            tn.team_name,
            sp.points,
            sp.rank
        FROM team_season_points sp
        JOIN team_names tn ON sp.team_id = tn.team_id AND sp.season = tn.season
        WHERE sp.season = ?
        ORDER BY sp.rank
    """, conn, params=(season,))
    conn.close()
    return df

def get_cumulative_points():
    """累積ポイントを取得（最新チーム名を使用）"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT 
            sp.team_id,
            SUM(sp.points) as total_points,
            COUNT(sp.season) as seasons,
            AVG(sp.points) as avg_points
        FROM team_season_points sp
        GROUP BY sp.team_id
        ORDER BY total_points DESC
    """, conn)
    conn.close()
    
    # 最新のチーム名を追加
    df["team_name"] = df["team_id"].apply(get_current_team_name)
    df["rank"] = range(1, len(df) + 1)
    return df

def get_team_history(team_id):
    """チームのシーズン履歴を取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT 
            sp.season,
            tn.team_name,
            sp.points,
            sp.rank
        FROM team_season_points sp
        JOIN team_names tn ON sp.team_id = tn.team_id AND sp.season = tn.season
        WHERE sp.team_id = ?
        ORDER BY sp.season DESC
    """, conn, params=(team_id,))
    conn.close()
    return df

def get_teams_for_display():
    """表示用のチーム一覧（最新名+色）を取得"""
    teams_df = get_teams()
    result = []
    for _, row in teams_df.iterrows():
        result.append({
            "team_id": row["team_id"],
            "team_name": get_current_team_name(row["team_id"]),
            "short_name": row["short_name"],
            "color": row["color"],
            "established": row["established"]
        })
    return pd.DataFrame(result)
