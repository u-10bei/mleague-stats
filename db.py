# 共通: 4人分一括レーティング計算・保存
def update_ratings_for_game(player_ids, ranks, season, game_date, game_number, conn=None):
    """
    4人分のplayer_id, rank, season, game_date, game_numberを受け取り、
    Elo式で全員分のΔR・新レートを一括計算・保存する共通関数。
    conn: 既存コネクションを使う場合は指定（なければ内部で開閉）
    """
    import numpy as np
    from collections import defaultdict
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    cursor = conn.cursor()
    # 直前レート取得
    ratings = []
    for pid in player_ids:
        cursor.execute("SELECT COALESCE(rating, 1500.0) FROM player_ratings WHERE player_id = ?", (pid,))
        result = cursor.fetchone()
        ratings.append(result[0] if result else 1500.0)
    # 順位スコア
    rank_to_score = {1: 4.5, 2: 0.5, 3: -1.5, 4: -3.5}
    rank_scores = [rank_to_score[rk] for rk in ranks]
    # 期待スコア
    def win_expect(r1, r2):
        return 1 / (1 + 10 ** ((r2 - r1) / 400))
    win_probs = []
    for i in range(4):
        others = [ratings[j] for j in range(4) if j != i]
        prob = np.mean([win_expect(ratings[i], r) for r in others])
        win_probs.append(prob)
    expected_scores = [sum([p * s for p, s in zip(win_probs, np.roll(rank_scores, -i))]) for i in range(4)]
    mean_score = sum(expected_scores) / 4
    corrected_scores = [s - mean_score for s in expected_scores]
    # 実順位スコア（同順位平均対応）
    rank_count = defaultdict(list)
    for idx, rk in enumerate(ranks):
        rank_count[rk].append(idx)
    actual_scores = [0]*4
    for rk, idxs in rank_count.items():
        if len(idxs) == 1:
            actual = rank_to_score[rk]
            actual_scores[idxs[0]] = actual
        else:
            min_rank = rk
            max_rank = rk + len(idxs) - 1
            scores = [rank_to_score[r] for r in range(min_rank, max_rank+1) if r in rank_to_score]
            actual = sum(scores) / len(scores) if scores else 0
            for idx in idxs:
                actual_scores[idx] = actual
    # ΔR計算・保存
    K = 8
    for i in range(4):
        old_rating = ratings[i]
        expected_score = corrected_scores[i]
        actual_score = actual_scores[i]
        delta = K * (actual_score - expected_score)
        new_rating = old_rating + delta
        # player_ratings
        cursor.execute("""
            INSERT OR REPLACE INTO player_ratings (player_id, rating, games, last_updated)
            VALUES (?, ?, COALESCE((SELECT games FROM player_ratings WHERE player_id = ?), 0) + 1, CURRENT_TIMESTAMP)
        """, (player_ids[i], new_rating, player_ids[i]))
        # rating_history
        cursor.execute("""
            INSERT INTO rating_history (player_id, game_date, old_rating, new_rating, delta, opponent_ids, season, game_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player_ids[i], game_date, old_rating, new_rating, delta,
            ','.join(str(pid) for j, pid in enumerate(player_ids) if j != i),
            season, game_number
        ))
    if close_conn:
        conn.commit()
        conn.close()
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
    4人麻雀用の期待順位スコア（Elo式＋順位スコア補正）
    Args:
        player_rating: 対象選手のレート
        opponent_ratings: 対戦相手3人のレート (list of 3 values)
    Returns:
        期待順位スコア（-3.5 〜 +4.5）
    """
    import numpy as np
    all_ratings = [player_rating] + opponent_ratings
    def win_expect(r1, r2):
        return 1 / (1 + 10 ** ((r2 - r1) / 400))
    win_probs = []
    for i in range(4):
        others = [all_ratings[j] for j in range(4) if j != i]
        prob = np.mean([win_expect(all_ratings[i], r) for r in others])
        win_probs.append(prob)
    rank_scores = [4.5, 0.5, -1.5, -3.5]
    expected_scores = [sum([p * s for p, s in zip(win_probs, np.roll(rank_scores, -i))]) for i in range(4)]
    mean_score = sum(expected_scores) / 4
    corrected_scores = [s - mean_score for s in expected_scores]
    idx = 0
    for i, r in enumerate(all_ratings):
        if abs(r - player_rating) < 1e-8:
            idx = i
            break
    return corrected_scores[idx]


def calculate_rating_delta(player_rating, opponent_ratings, actual_rank, K=8):
    """
    実績順位と期待順位の乖離からレート変動を計算（K=8, 順位スコア4.5/0.5/-1.5/-3.5）
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
    
    # レート変動を計算（K=8, 順位スコア4.5/0.5/-1.5/-3.5）
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
    
    # 対局単位で4人まとめて処理
    cursor.execute("""
        SELECT season, game_date, COALESCE(game_number, 0) as game_number
        FROM game_results
        GROUP BY season, game_date, COALESCE(game_number, 0)
        ORDER BY game_date, game_number
    """)
    games = cursor.fetchall()


    from db import update_ratings_for_game
    for season, game_date, game_number in games:
        cursor.execute("""
            SELECT player_id, rank
            FROM game_results
            WHERE season = ? AND game_date = ? AND COALESCE(game_number, 0) = ?
            ORDER BY player_id
        """, (season, game_date, game_number))
        players = cursor.fetchall()
        if len(players) != 4:
            continue  # 4人未満はスキップ
        player_ids = [pid for pid, _ in players]
        ranks = [rk for _, rk in players]
        update_ratings_for_game(player_ids, ranks, season, game_date, game_number, conn=conn)

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
            game_number,
            old_rating,
            new_rating,
            delta
        FROM rating_history
        WHERE player_id = ?
        ORDER BY game_date ASC, game_number ASC, id ASC
        LIMIT ?
    """, conn, params=(player_id, limit))
    conn.close()
    return df
