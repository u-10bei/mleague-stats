import streamlit as st
import pandas as pd
import sys
sys.path.append("..")
from db import get_connection, hide_default_sidebar_navigation

st.set_page_config(
    page_title="対局記録 | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide"
)

# デフォルトのサイドバーナビゲーションを非表示
hide_default_sidebar_navigation()

# サイドバーナビゲーション
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
st.sidebar.page_link("pages/15_game_records.py", label="📜 対局記録")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/3_admin.py", label="⚙️ データ管理")
st.sidebar.page_link("pages/4_player_admin.py", label="👤 選手管理")
st.sidebar.page_link("pages/9_team_master_admin.py", label="🏢 チーム管理")
st.sidebar.page_link("pages/5_season_update.py", label="🔄 シーズン更新")
st.sidebar.page_link("pages/6_player_stats_input.py", label="📊 選手成績入力")
st.sidebar.page_link("pages/11_game_results_input.py", label="🎮 半荘記録入力")

st.title("📜 対局記録")

st.markdown("""
半荘記録から、特筆すべき対局の記録を表示します。
- **試合時間記録**: 最短・最長対局のランキング
""")

# ========== データ取得 ==========
conn = get_connection()
cursor = conn.cursor()

# 利用可能なシーズンを取得
cursor.execute("""
    SELECT DISTINCT season 
    FROM game_results 
    WHERE start_time IS NOT NULL AND end_time IS NOT NULL
    ORDER BY season DESC
""")
seasons = [row[0] for row in cursor.fetchall()]

if not seasons:
    st.warning("試合時間が記録された対局データがありません。「🎮 半荘記録入力」で開始・終了時間を記録してください。")
    conn.close()
    st.stop()

conn.close()

# ========== フィルター設定 ==========
st.markdown("---")
st.subheader("🔍 表示期間")

col1, col2 = st.columns([1, 3])

with col1:
    period_options = ["全期間"] + seasons
    selected_period = st.selectbox("期間", period_options, key="period_select")

with col2:
    if selected_period == "全期間":
        st.info(f"📊 全期間のデータを表示します（{len(seasons)}シーズン）")
    else:
        st.info(f"📊 {selected_period}シーズンのデータを表示します")

# ========== 試合時間記録 ==========
st.markdown("---")
st.subheader("⏱️ 試合時間記録")

st.markdown("""
開始時間と終了時間が記録されている対局の中から、最短・最長対局をランキング表示します。
""")

# 対局時間を計算する関数
def calc_duration_minutes(start_time, end_time):
    """HH:MM形式の時刻から対局時間（分）を計算"""
    try:
        start_parts = start_time.split(':')
        end_parts = end_time.split(':')
        
        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
        
        duration = end_minutes - start_minutes
        
        # 日をまたぐ場合（負の値になる場合）
        if duration < 0:
            duration += 24 * 60
        
        return duration
    except:
        return None

def format_duration(minutes):
    """分を H:MM 形式に変換"""
    if minutes is None:
        return "-"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}:{mins:02d}"

# データ取得
conn = get_connection()

if selected_period == "全期間":
    query = """
        SELECT 
            gr.season,
            gr.game_date,
            gr.table_type,
            gr.game_number,
            gr.start_time,
            gr.end_time,
            GROUP_CONCAT(p.player_name, ', ') as players
        FROM game_results gr
        JOIN players p ON gr.player_id = p.player_id
        WHERE gr.start_time IS NOT NULL AND gr.end_time IS NOT NULL
        GROUP BY gr.season, gr.game_date, gr.table_type, gr.game_number
        ORDER BY gr.game_date, gr.game_number
    """
    cursor = conn.cursor()
    cursor.execute(query)
else:
    query = """
        SELECT 
            gr.season,
            gr.game_date,
            gr.table_type,
            gr.game_number,
            gr.start_time,
            gr.end_time,
            GROUP_CONCAT(p.player_name, ', ') as players
        FROM game_results gr
        JOIN players p ON gr.player_id = p.player_id
        WHERE gr.season = ? 
            AND gr.start_time IS NOT NULL 
            AND gr.end_time IS NOT NULL
        GROUP BY gr.season, gr.game_date, gr.table_type, gr.game_number
        ORDER BY gr.game_date, gr.game_number
    """
    cursor = conn.cursor()
    cursor.execute(query, (selected_period,))

results = cursor.fetchall()
conn.close()

if not results:
    st.warning("選択した期間に試合時間が記録された対局がありません。")
    st.stop()

# DataFrameに変換
df = pd.DataFrame(results, columns=[
    'season', 'game_date', 'table_type', 'game_number', 
    'start_time', 'end_time', 'players'
])

# 対局時間を計算
df['duration_minutes'] = df.apply(
    lambda row: calc_duration_minutes(row['start_time'], row['end_time']),
    axis=1
)

# 計算できなかった行を除外
df = df[df['duration_minutes'].notna()].copy()

if df.empty:
    st.warning("試合時間を計算できる対局がありません。")
    st.stop()

# 対局時間をフォーマット
df['duration_formatted'] = df['duration_minutes'].apply(format_duration)

# ========== 最短対局トップ10 ==========
st.markdown("### 🏃 最短対局 TOP10")

shortest_df = df.nsmallest(10, 'duration_minutes').copy()

# 表示用に整形
shortest_display = shortest_df[[
    'game_date', 'table_type', 'start_time', 'end_time', 
    'duration_formatted', 'players'
]].copy()

shortest_display.columns = [
    '対局日', '卓区分', '開始', '終了', '対局時間', '対局者'
]

# ランクを追加
shortest_display.insert(0, '順位', range(1, len(shortest_display) + 1))

st.dataframe(
    shortest_display,
    hide_index=True,
    width='stretch',
    column_config={
        '順位': st.column_config.NumberColumn(width="small"),
        '対局日': st.column_config.TextColumn(width="medium"),
        '卓区分': st.column_config.TextColumn(width="small"),
        '開始': st.column_config.TextColumn(width="small"),
        '終了': st.column_config.TextColumn(width="small"),
        '対局時間': st.column_config.TextColumn(width="small"),
        '対局者': st.column_config.TextColumn(width="large"),
    }
)

# 統計情報
if not shortest_df.empty:
    fastest_game = shortest_df.iloc[0]
    st.info(f"💨 **最短記録**: {fastest_game['duration_formatted']} （{fastest_game['game_date']} {fastest_game['table_type']}）")

# ========== 最長対局トップ10 ==========
st.markdown("---")
st.markdown("### 🐢 最長対局 TOP10")

longest_df = df.nlargest(10, 'duration_minutes').copy()

# 表示用に整形
longest_display = longest_df[[
    'game_date', 'table_type', 'start_time', 'end_time', 
    'duration_formatted', 'players'
]].copy()

longest_display.columns = [
    '対局日', '卓区分', '開始', '終了', '対局時間', '対局者'
]

# ランクを追加
longest_display.insert(0, '順位', range(1, len(longest_display) + 1))

st.dataframe(
    longest_display,
    hide_index=True,
    width='stretch',
    column_config={
        '順位': st.column_config.NumberColumn(width="small"),
        '対局日': st.column_config.TextColumn(width="medium"),
        '卓区分': st.column_config.TextColumn(width="small"),
        '開始': st.column_config.TextColumn(width="small"),
        '終了': st.column_config.TextColumn(width="small"),
        '対局時間': st.column_config.TextColumn(width="small"),
        '対局者': st.column_config.TextColumn(width="large"),
    }
)

# 統計情報
if not longest_df.empty:
    slowest_game = longest_df.iloc[0]
    st.info(f"🐢 **最長記録**: {slowest_game['duration_formatted']} （{slowest_game['game_date']} {slowest_game['table_type']}）")

# ========== 全体統計 ==========
st.markdown("---")
st.markdown("### 📊 試合時間の統計")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_games = len(df)
    st.metric("記録対局数", f"{total_games}局")

with col2:
    avg_duration = df['duration_minutes'].mean()
    st.metric("平均時間", format_duration(int(avg_duration)))

with col3:
    min_duration = df['duration_minutes'].min()
    st.metric("最短時間", format_duration(int(min_duration)))

with col4:
    max_duration = df['duration_minutes'].max()
    st.metric("最長時間", format_duration(int(max_duration)))

# 時間分布の説明
st.markdown("---")
st.info("""
💡 **試合時間について**

- **記録対象**: 開始時間・終了時間の両方が記録されている対局のみ
- **計算方法**: 終了時間 - 開始時間（日をまたぐ場合にも対応）
- **表示形式**: H:MM（時間:分）

対局時間は対局の複雑さ、プレイヤーの思考時間、局面の難易度などによって変動します。
""")

# ========== 将来の拡張機能 ==========
st.markdown("---")
st.subheader("🚀 今後実装予定の記録")

st.markdown("""
以下の対局記録を今後追加予定です：

**🎯 得点記録**
- 最高得点対局（単独トップ得点）
- 最大点差対局（1位と4位の点差）
- 箱割れ記録（マイナス得点の記録）

**📊 順位記録**
- 連続トップ記録
- 連続ラス記録
- 連続同順位記録

**🎲 珍しい記録**
- オーラス逆転記録
- 同点記録
- 全員プラス/全員マイナス対局

データが蓄積されるにつれて、様々な記録を追加していきます。
""")

st.markdown("---")
st.caption("※ データは半荘記録から集計されています。")
