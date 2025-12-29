import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "data/mleague.db"


def hide_default_sidebar_navigation():
    """Streamlitのデフォルトサイドバーナビゲーションを非表示にする"""
    st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
    """, unsafe_allow_html=True)


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
    cursor.execute(
        "SELECT DISTINCT season FROM team_season_points ORDER BY season DESC")
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

# ========== 選手関連 ==========


def get_players():
    """全選手を取得"""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM players ORDER BY player_id", conn)
    conn.close()
    return df


def get_player(player_id):
    """選手情報を取得"""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM players WHERE player_id = ?",
        conn,
        params=(player_id,)
    )
    conn.close()
    return df.iloc[0] if not df.empty else None


def get_player_teams(player_id):
    """選手の所属チーム履歴を取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT pt.season, pt.team_id, tn.team_name
        FROM player_teams pt
        JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        WHERE pt.player_id = ?
        ORDER BY pt.season DESC
    """, conn, params=(player_id,))
    conn.close()
    return df


def get_player_current_team(player_id):
    """選手の最新所属チームを取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pt.team_id, tn.team_name
        FROM player_teams pt
        JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        WHERE pt.player_id = ?
        ORDER BY pt.season DESC
        LIMIT 1
    """, (player_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else (None, None)


def get_player_season_stats(player_id):
    """選手のシーズン成績を取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT ps.*, pt.team_id, tn.team_name
        FROM player_season_stats ps
        LEFT JOIN player_teams pt ON ps.player_id = pt.player_id AND ps.season = pt.season
        LEFT JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        WHERE ps.player_id = ?
        ORDER BY ps.season DESC
    """, conn, params=(player_id,))
    conn.close()
    return df


def get_all_player_stats_for_season(season):
    """指定シーズンの全選手成績を取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT 
            p.player_id,
            p.player_name,
            ps.season,
            ps.games,
            ps.points,
            ps.rank_1st,
            ps.rank_2nd,
            ps.rank_3rd,
            ps.rank_4th,
            pt.team_id,
            tn.team_name
        FROM player_season_stats ps
        JOIN players p ON ps.player_id = p.player_id
        LEFT JOIN player_teams pt ON ps.player_id = pt.player_id AND ps.season = pt.season
        LEFT JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        WHERE ps.season = ?
        ORDER BY ps.points DESC
    """, conn, params=(season,))
    conn.close()
    return df


def get_players_by_team(team_id, season):
    """指定チーム・シーズンの所属選手を取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT p.player_id, p.player_name
        FROM player_teams pt
        JOIN players p ON pt.player_id = p.player_id
        WHERE pt.team_id = ? AND pt.season = ?
        ORDER BY p.player_name
    """, conn, params=(team_id, season))
    conn.close()
    return df

# ========== 選手成績関連（新規追加） ==========


def get_player_seasons():
    """選手成績が登録されているシーズン一覧を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT season FROM player_season_stats ORDER BY season DESC")
    seasons = [row[0] for row in cursor.fetchall()]
    conn.close()
    return seasons


def get_player_season_ranking(season):
    """指定シーズンの選手ランキングを取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT 
            p.player_id,
            p.player_name,
            ps.games,
            ps.points,
            ps.rank_1st,
            ps.rank_2nd,
            ps.rank_3rd,
            ps.rank_4th,
            tn.team_name,
            t.color
        FROM player_season_stats ps
        JOIN players p ON ps.player_id = p.player_id
        LEFT JOIN player_teams pt ON ps.player_id = pt.player_id AND ps.season = pt.season
        LEFT JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        LEFT JOIN teams t ON pt.team_id = t.team_id
        WHERE ps.season = ? AND ps.games > 0
        ORDER BY ps.points DESC
    """, conn, params=(season,))
    conn.close()

    # ランクを追加
    df['rank'] = range(1, len(df) + 1)
    return df


def get_player_cumulative_stats():
    """全選手の累積成績を取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT 
            p.player_id,
            p.player_name,
            SUM(ps.games) as total_games,
            SUM(ps.points) as total_points,
            SUM(ps.rank_1st) as total_1st,
            SUM(ps.rank_2nd) as total_2nd,
            SUM(ps.rank_3rd) as total_3rd,
            SUM(ps.rank_4th) as total_4th,
            COUNT(DISTINCT ps.season) as seasons,
            AVG(ps.points) as avg_points
        FROM player_season_stats ps
        JOIN players p ON ps.player_id = p.player_id
        WHERE ps.games > 0
        GROUP BY p.player_id, p.player_name
        ORDER BY total_points DESC
    """, conn)
    conn.close()

    # ランクを追加
    df['rank'] = range(1, len(df) + 1)

    # 最新所属チームを追加
    team_info = []
    for player_id in df['player_id']:
        team_id, team_name = get_player_current_team(player_id)
        team_info.append({
            'team_id': team_id,
            'team_name': team_name or '-'
        })

    df['team_name'] = [t['team_name'] for t in team_info]

    return df


def get_player_history(player_id):
    """選手のシーズン履歴を取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT 
            ps.season,
            tn.team_name,
            ps.games,
            ps.points,
            ps.rank_1st,
            ps.rank_2nd,
            ps.rank_3rd,
            ps.rank_4th
        FROM player_season_stats ps
        LEFT JOIN player_teams pt ON ps.player_id = pt.player_id AND ps.season = pt.season
        LEFT JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        WHERE ps.player_id = ?
        ORDER BY ps.season DESC
    """, conn, params=(player_id,))
    conn.close()
    return df


def get_player_all_stats():
    """全選手の全シーズン成績を取得（推移グラフ用）"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT 
            p.player_id,
            p.player_name,
            ps.season,
            ps.points
        FROM player_season_stats ps
        JOIN players p ON ps.player_id = p.player_id
        WHERE ps.games > 0
        ORDER BY ps.season, ps.points DESC
    """, conn)
    conn.close()
    return df
