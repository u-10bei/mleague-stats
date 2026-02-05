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

def show_sidebar_navigation():
    """共通のサイドバーナビゲーションを表示"""
    # デフォルトのサイドバーナビゲーションを非表示
    hide_default_sidebar_navigation()

    st.sidebar.title("🀄 メニュー")
    st.sidebar.page_link("app.py", label="🏠 トップページ")
    st.sidebar.markdown("### 📊 チーム成績")
    st.sidebar.page_link("pages/1_season_ranking.py", label="📊 年度別ランキング")
    st.sidebar.page_link("pages/2_cumulative_ranking.py", label="🏆 累積ランキング")
    st.sidebar.page_link("pages/10_team_game_analysis.py", label="📈 半荘別分析")
    st.sidebar.markdown("### 👤 選手成績")
    st.sidebar.page_link("pages/7_player_season_ranking.py", label="📊 年度別ランキング")
    st.sidebar.page_link("pages/8_player_cumulative_ranking.py", label="🏆 累積ランキング")
    st.sidebar.page_link("pages/13_player_game_analysis.py", label="📈 半荘別分析")
    st.sidebar.markdown("---")
    st.sidebar.page_link("pages/14_statistical_analysis.py", label="📈 統計分析")
    st.sidebar.page_link("pages/16_streak_records.py", label="🔥 連続記録")
    st.sidebar.page_link("pages/15_game_records.py", label="📜 対局記録")
    st.sidebar.page_link("pages/17_player_rating.py", label="📊 レーティング")
    st.sidebar.markdown("---")
    st.sidebar.page_link("pages/3_admin.py", label="⚙️ データ管理")
    st.sidebar.page_link("pages/4_player_admin.py", label="👤 選手管理")
    st.sidebar.page_link("pages/9_team_master_admin.py", label="🏢 チーム管理")
    st.sidebar.page_link("pages/5_season_update.py", label="🔄 シーズン更新")
    st.sidebar.page_link("pages/6_player_stats_input.py", label="📊 選手成績入力")
    st.sidebar.page_link("pages/11_game_results_input.py", label="🎮 半荘記録入力")

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


# ========== Elo風レーティング計算 ==========

def calculate_expected_rank_score(player_rating, opponent_ratings):
    """
    線形補間で期待順位スコアを計算
    
    4人のレート（player_rating + 3つのopponent_ratings）に基づいて、
    対象選手の期待順位スコアを算出
    
    Args:
        player_rating: 対象選手のレート
        opponent_ratings: 対戦相手3人のレート (list of 3 values)
    
    Returns:
        期待順位スコア（-3.5 〜 +4.5）
    """
    all_ratings = sorted([player_rating] + opponent_ratings, reverse=True)
    player_position = all_ratings.index(player_rating)
    
    # 順位スコア: 1位: +4.5, 2位: +0.5, 3位: -1.5, 4位: -3.5
    rank_scores = [4.5, 0.5, -1.5, -3.5]
    
    # 複数の同じレートがある場合は平均を取る
    if player_rating in all_ratings[1:]:
        # 対象選手と同じレートの対戦相手がいる場合、その位置のスコアを平均
        positions = [i for i, r in enumerate(all_ratings) if r == player_rating]
        expected_score = sum(rank_scores[i] for i in positions) / len(positions)
    else:
        expected_score = rank_scores[player_position]
    
    return expected_score


def calculate_rating_delta(player_rating, opponent_ratings, actual_rank, K=8):
    """
    実績順位と期待順位の乖離からレート変動を計算
    
    Args:
        player_rating: 対象選手のレート
        opponent_ratings: 対戦相手3人のレート (list of 3 values)
        actual_rank: 実際の順位（1, 2, 3, 4）
        K: K値（デフォルト8）
    
    Returns:
        レート変動（ΔR）
    """
    actual_rank_scores = {1: 4.5, 2: 0.5, 3: -1.5, 4: -3.5}
    actual_score = actual_rank_scores[actual_rank]
    
    expected_score = calculate_expected_rank_score(player_rating, opponent_ratings)
    
    delta = K * (actual_score - expected_score)
    return delta


def update_player_rating(player_id, opponent_ratings, actual_rank, game_date):
    """
    1対局後の選手レートを更新
    
    Args:
        player_id: 選手ID
        opponent_ratings: 対戦相手3人のレート (list of 3 values)
        actual_rank: 実際の順位（1, 2, 3, 4）
        game_date: 対局日（YYYY-MM-DD形式）
    
    Returns:
        新しいレート、レート変動
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 現在のレートを取得
    cursor.execute("""
        SELECT COALESCE(rating, 1500.0) as rating, COALESCE(games, 0) as games
        FROM player_ratings
        WHERE player_id = ?
    """, (player_id,))
    
    result = cursor.fetchone()
    if result:
        old_rating = result[0]
        games = result[1]
    else:
        old_rating = 1500.0
        games = 0
    
    # レート変動を計算
    delta = calculate_rating_delta(old_rating, opponent_ratings, actual_rank, K=8)
    new_rating = old_rating + delta
    
    # レートを更新
    cursor.execute("""
        INSERT OR REPLACE INTO player_ratings (player_id, rating, games, last_updated)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (player_id, new_rating, games + 1))
    
    # 履歴を記録
    cursor.execute("""
        INSERT INTO rating_history (player_id, game_date, old_rating, new_rating, delta, opponent_ids)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (player_id, game_date, old_rating, new_rating, delta, ",".join(map(str, range(3)))))
    
    conn.commit()
    conn.close()
    
    return new_rating, delta


def initialize_ratings_from_games():
    """
    既存のgame_resultsから時系列でレートを遡及計算
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 全選手のレートを1500にリセット
    cursor.execute("DELETE FROM player_ratings")
    cursor.execute("DELETE FROM rating_history")
    
    # ゲーム結果を時系列で取得
    cursor.execute("""
        SELECT gr.id, gr.season, gr.game_date, gr.player_id, gr.rank, 
               GROUP_CONCAT(DISTINCT gr2.player_id) as opponent_ids
        FROM game_results gr
        LEFT JOIN game_results gr2 ON gr.season = gr2.season 
            AND gr.game_date = gr2.game_date 
            AND gr.id != gr2.id
            AND (gr.table_type IS NULL OR gr.table_type = gr2.table_type)
            AND (gr.game_number IS NULL OR gr.game_number = gr2.game_number)
        GROUP BY gr.id
        ORDER BY gr.game_date, gr.id
    """)
    
    games = cursor.fetchall()
    
    for game_id, season, game_date, player_id, rank, opponent_ids_str in games:
        # 対戦相手のレートを取得
        opponent_ids = [int(x) for x in opponent_ids_str.split(',')] if opponent_ids_str else []
        
        opponent_ratings = []
        for opp_id in opponent_ids[:3]:  # 最大3人
            cursor.execute("""
                SELECT COALESCE(rating, 1500.0) FROM player_ratings WHERE player_id = ?
            """, (opp_id,))
            result = cursor.fetchone()
            if result:
                opponent_ratings.append(result[0])
        
        # 対戦相手が3人未満の場合は1500で補填
        while len(opponent_ratings) < 3:
            opponent_ratings.append(1500.0)
        
        # レートを更新
        cursor.execute("""
            SELECT COALESCE(rating, 1500.0), COALESCE(games, 0) FROM player_ratings WHERE player_id = ?
        """, (player_id,))
        result = cursor.fetchone()
        old_rating = result[0] if result else 1500.0
        current_games = result[1] if result else 0
        
        delta = calculate_rating_delta(old_rating, opponent_ratings[:3], rank, K=8)
        new_rating = old_rating + delta
        new_games = current_games + 1
        
        cursor.execute("""
            INSERT OR REPLACE INTO player_ratings (player_id, rating, games, last_updated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (player_id, new_rating, new_games))
        
        cursor.execute("""
            INSERT INTO rating_history (player_id, game_date, old_rating, new_rating, delta, opponent_ids)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (player_id, game_date, old_rating, new_rating, delta, opponent_ids_str or ""))
    
    # rating_calculated フラグをすべて 1 に更新
    cursor.execute("UPDATE game_results SET rating_calculated = 1")
    
    conn.commit()
    conn.close()


def get_player_ratings():
    """全選手のレーティング情報を取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT 
            p.player_id,
            p.player_name,
            pr.rating,
            pr.games,
            pr.last_updated
        FROM player_ratings pr
        JOIN players p ON pr.player_id = p.player_id
        ORDER BY pr.rating DESC
    """, conn)
    conn.close()
    return df


def get_player_rating_history(player_id, limit=50):
    """選手のレーティング履歴を取得"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT 
            game_date,
            old_rating,
            new_rating,
            delta
        FROM rating_history
        WHERE player_id = ?
        ORDER BY game_date DESC
        LIMIT ?
    """, conn, params=(player_id, limit))
    conn.close()
    return df
