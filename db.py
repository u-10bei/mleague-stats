import itertools
import os
import sqlite3

import pandas as pd
import streamlit as st

# konoui/m-league-game-db を正データとして使う。
# get_connection() は補完DB (mleague_local.db) に接続し、konoui 配布DB を
# `src` として ATTACH したうえで互換ビューを TEMP で構築して返す。
from db_konoui import (  # noqa: F401
    get_connection,
    get_konoui_db_path,
    is_slim_db,
    FULL_DB_PATH,
    SLIM_DB_PATH,
    LOCAL_DB_PATH,
    KonouiDatabaseNotFound,
)

from ui import inject_responsive_css

# 旧 DB_PATH 互換 (書き込み先は補完DB)
DB_PATH = LOCAL_DB_PATH


def is_admin_enabled():
    """補完データ管理ページを有効にするか。

    デフォルトは無効。Streamlit Community Cloud のような公開環境へ
    そのままデプロイしても管理機能が露出しないよう、安全側に倒している。

    有効にするには次のいずれか:
      - 環境変数      MLEAGUE_ADMIN=1 streamlit run app.py
      - secrets.toml  enable_admin = true   (.streamlit/secrets.toml)

    公開環境では書き込んでもコンテナ再起動で消えるため、
    そもそも補完データ管理を出す意味がない。
    """
    env = os.environ.get("MLEAGUE_ADMIN")
    if env is not None:
        return env.strip().lower() in ("1", "true", "yes", "on")
    try:
        return bool(st.secrets.get("enable_admin", False))
    except Exception:
        # secrets.toml が無い環境では例外になる
        return False


def require_admin():
    """補完データ管理ページの先頭で呼ぶガード。

    サイドバーからリンクを外すだけでは URL 直打ちで到達できてしまうため、
    ページ側でも明示的に止める。
    """
    if is_admin_enabled():
        return
    st.title("🔒 補完データ管理は無効です")
    st.info(
        "このページは公開環境では無効化されています。\n\n"
        "ローカルで有効にするには環境変数を付けて起動してください:\n"
        "```bash\n"
        "MLEAGUE_ADMIN=1 streamlit run app.py\n"
        "```"
    )
    st.stop()


def hide_default_sidebar_navigation():
    """Streamlit のデフォルトサイドバーナビゲーションを非表示にする。

    ついでに、スマホ・タブレット向けの CSS もここで流し込む。
    全ページが show_sidebar_navigation() を 1 回ずつ呼んでいるので、
    各ページを触らずに全画面へ届く。
    """
    st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
    """, unsafe_allow_html=True)
    inject_responsive_css()

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
    st.sidebar.page_link("pages/19_player_character_sheet.py",
                         label="🎴 キャラクターシート")
    if is_admin_enabled():
        st.sidebar.markdown("---")
        st.sidebar.page_link("pages/18_local_data_admin.py",
                             label="🛠️ 補完データ管理")

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


def get_current_team_names():
    """team_id -> 最新シーズンのチーム名のマッピング。

    チーム名はシーズンごとに変わりうる（例: BEAST Japanext -> BEAST X）。
    複数シーズンをまたいで集計するときに team_name で束ねると同一チームが
    分裂するため、集計キーは team_id にして表示名だけここから引く。
    """
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT tn.team_id, tn.team_name
        FROM team_names tn
        JOIN (
            SELECT team_id, MAX(season) AS season
            FROM team_names
            GROUP BY team_id
        ) latest ON latest.team_id = tn.team_id AND latest.season = tn.season
    """, conn)
    conn.close()
    return dict(zip(df["team_id"], df["team_name"]))


def get_roster_player_ids(season=None):
    """指定シーズンにチーム登録がある選手の player_id 集合。

    season を省略すると最新シーズンを使う。進行中の連続記録のように
    「いま在籍している選手」に絞りたい場面で使う。
    """
    conn = get_connection()
    if season is None:
        df = pd.read_sql_query("""
            SELECT player_id FROM player_teams
            WHERE season = (SELECT MAX(season) FROM player_teams)
        """, conn)
    else:
        df = pd.read_sql_query(
            "SELECT player_id FROM player_teams WHERE season = ?",
            conn, params=(season,))
    conn.close()
    return set(df["player_id"])


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


# ========== レーティング ==========
#
# 着順スコア方式の Elo。
#
#   ΔR_i = K * (実際の着順スコア_i - E[着順スコア_i])
#
# 着順スコアは 1位 +4.5 / 2位 +0.5 / 3位 -1.5 / 4位 -3.5（合計 0）。
# トップとラスを重く、2位と3位の差を軽く見る配分。
#
# 期待値はレートだけから出す。Elo の多人数拡張である Plackett-Luce で
# 「選手 i が k 位になる確率」を求め、着順スコアの期待値を取る。
#
#   強さ w_i = 10^(R_i / 400)
#   1位から順に、残っている選手の w に比例して選ばれる
#   P(i が k 位) は 4 人なら 24 通りの順列を数え上げれば厳密に出る
#
# 各着順の確率の合計が 1 なので Σ_i E[スコア_i] = Σ_k スコア_k = 0。
# 実際の着順スコアの合計も 0 なので ΔR はゼロサムになる。
# 引数の並び順には依存しない。
# 全員同レートなら期待値が 0 になり ΔR = K × 着順スコア。
RATING_K = 8
INITIAL_RATING = 1500.0

# 着順スコア。同着は該当する着順のスコアを平均する（1224 方式）。
RANK_SCORES = {1: 4.5, 2: 0.5, 3: -1.5, 4: -3.5}

# 4 人分の順列。期待値の数え上げに使うので一度だけ作る。
_PERMUTATIONS = list(itertools.permutations(range(4)))


def _rank_probabilities(ratings):
    """Plackett-Luce で P(選手 i が k 位) を返す（probs[i][k]、k は 0 起点）。"""
    # レートをそのまま指数に載せると桁が大きくなるので平均を引いてから。
    mean = sum(ratings) / len(ratings)
    strengths = [10 ** ((r - mean) / 400) for r in ratings]
    probs = [[0.0] * 4 for _ in range(4)]
    for order in _PERMUTATIONS:
        p = 1.0
        remaining = sum(strengths)
        for player in order:
            p *= strengths[player] / remaining
            remaining -= strengths[player]
        for place, player in enumerate(order):
            probs[player][place] += p
    return probs


def calculate_expected_scores(ratings):
    """レートから決まる着順スコアの期待値（-3.5 〜 +4.5）。"""
    probs = _rank_probabilities(ratings)
    scores = [RANK_SCORES[k] for k in (1, 2, 3, 4)]
    return [sum(p * s for p, s in zip(row, scores)) for row in probs]


def _actual_scores(ranks):
    """実際の着順スコア。同着は該当する着順のスコアを平均する。"""
    by_rank = {}
    for i, rank in enumerate(ranks):
        by_rank.setdefault(rank, []).append(i)
    scores = [0.0] * len(ranks)
    for rank, indexes in by_rank.items():
        tied = [RANK_SCORES[r] for r in range(rank, rank + len(indexes))
                if r in RANK_SCORES]
        value = sum(tied) / len(tied) if tied else 0.0
        for i in indexes:
            scores[i] = value
    return scores


def calculate_rating_deltas(ratings, ranks, K=RATING_K):
    """4人分のレートと着順から ΔR を計算する。

    ratings, ranks は同じ並びの長さ4のリスト。
    """
    expected = calculate_expected_scores(ratings)
    actual = _actual_scores(ranks)
    return [K * (actual[i] - expected[i]) for i in range(len(ratings))]


def calculate_rating_delta(player_rating, opponent_ratings, actual_rank, K=RATING_K):
    """1人分の ΔR。対象選手を先頭にした4人分のレートから期待値を出す。"""
    expected = calculate_expected_scores([player_rating] + list(opponent_ratings))[0]
    return K * (RANK_SCORES[actual_rank] - expected)


# 共通: 4人分一括レーティング計算・保存
def update_ratings_for_game(player_ids, ranks, season, game_date, game_number, conn=None):
    """
    4人分のplayer_id, rank, season, game_date, game_numberを受け取り、
    ペアワイズ Elo で全員分のΔR・新レートを一括計算・保存する共通関数。
    conn: 既存コネクションを使う場合は指定（なければ内部で開閉）
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    cursor = conn.cursor()

    ratings = []
    for pid in player_ids:
        cursor.execute(
            "SELECT COALESCE(rating, ?) FROM ratings.player_ratings WHERE player_id = ?",
            (INITIAL_RATING, pid))
        result = cursor.fetchone()
        ratings.append(result[0] if result else INITIAL_RATING)

    deltas = calculate_rating_deltas(ratings, ranks)

    for i in range(len(player_ids)):
        old_rating = ratings[i]
        new_rating = old_rating + deltas[i]
        # last_updated は最終対局日。再計算しても対局が増えていなければ
        # 値が変わらないので、差分の有無で更新の要否を判定できる。
        cursor.execute("""
            INSERT OR REPLACE INTO ratings.player_ratings (player_id, rating, games, last_updated)
            VALUES (?, ?, COALESCE((SELECT games FROM ratings.player_ratings WHERE player_id = ?), 0) + 1, ?)
        """, (player_ids[i], new_rating, player_ids[i], game_date))
        cursor.execute("""
            INSERT INTO ratings.rating_history (player_id, game_date, old_rating, new_rating, delta, opponent_ids, season, game_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player_ids[i], game_date, old_rating, new_rating, deltas[i],
            ','.join(str(pid) for j, pid in enumerate(player_ids) if j != i),
            season, game_number
        ))
    if close_conn:
        conn.commit()
        conn.close()


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
        SELECT COALESCE(rating, ?) as rating, COALESCE(games, 0) as games
        FROM ratings.player_ratings
        WHERE player_id = ?
    """, (INITIAL_RATING, player_id))

    result = cursor.fetchone()
    if result:
        old_rating = result[0]
        games = result[1]
    else:
        old_rating = INITIAL_RATING
        games = 0
    
    delta = calculate_rating_delta(old_rating, opponent_ratings, actual_rank)
    new_rating = old_rating + delta
    
    # レートを更新
    cursor.execute("""
        INSERT OR REPLACE INTO ratings.player_ratings (player_id, rating, games, last_updated)
        VALUES (?, ?, ?, ?)
    """, (player_id, new_rating, games + 1, game_date))
    
    # 履歴を記録
    cursor.execute("""
        INSERT INTO ratings.rating_history (player_id, game_date, old_rating, new_rating, delta, opponent_ids)
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
    
    # 全選手のレートを初期値にリセット
    cursor.execute("DELETE FROM ratings.player_ratings")
    cursor.execute("DELETE FROM ratings.rating_history")
    cursor.execute("DELETE FROM ratings.rating_state")
    
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

    # rating_calculated フラグを補完テーブルへ記録する。
    # game_results は互換ビューのため UPDATE できない。
    cursor.execute("""
        INSERT INTO ratings.rating_state (game_id, calculated)
        SELECT game_id, 1 FROM game_results GROUP BY game_id
        ON CONFLICT(game_id) DO UPDATE SET calculated = 1
    """)
    conn.commit()
    # DELETE で空いたページが残るとファイルの中身が実行ごとにぶれる。
    # VACUUM で詰め直し、同じ対局群からは常に同じファイルが出るようにする。
    conn.execute("VACUUM ratings")
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
        FROM ratings.player_ratings pr
        JOIN players p ON pr.player_id = p.player_id
        ORDER BY pr.rating DESC
    """, conn)
    conn.close()
    return df


def get_player_rating_history(player_id, limit=50):
    """選手のレーティング履歴を直近 limit 件だけ取得する（古い順に並べて返す）。

    内側で新しい順に limit 件を切り出し、外側で時系列に並べ直す。
    ASC のまま LIMIT すると最古の limit 件になってしまう。
    """
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT game_date, game_number, old_rating, new_rating, delta
        FROM (
            SELECT game_date, game_number, old_rating, new_rating, delta, id
            FROM ratings.rating_history
            WHERE player_id = ?
            ORDER BY game_date DESC, game_number DESC, id DESC
            LIMIT ?
        )
        ORDER BY game_date ASC, game_number ASC, id ASC
    """, conn, params=(player_id, limit))
    conn.close()
    return df
