import streamlit as st
import pandas as pd
from datetime import datetime
from db import get_connection, hide_default_sidebar_navigation

st.set_page_config(
    page_title="半荘別成績分析 | Mリーグダッシュボード",
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
st.sidebar.markdown("### 👤 選手成績")
st.sidebar.page_link("pages/7_player_season_ranking.py", label="📊 年度別ランキング")
st.sidebar.page_link("pages/8_player_cumulative_ranking.py", label="🏆 累積ランキング")
st.sidebar.page_link("pages/12_game_results_analysis.py", label="📈 半荘別成績分析")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/3_admin.py", label="⚙️ データ管理")
st.sidebar.page_link("pages/4_player_admin.py", label="👤 選手管理")
st.sidebar.page_link("pages/9_team_master_admin.py", label="🏢 チーム管理")
st.sidebar.page_link("pages/5_season_update.py", label="🔄 シーズン更新")
st.sidebar.page_link("pages/6_player_stats_input.py", label="📊 選手成績入力")
st.sidebar.page_link("pages/11_game_results_input.py", label="🎮 半荘記録入力")

st.title("📈 半荘別成績分析")

st.markdown("""
半荘記録から全選手の成績をランキング表で表示します。
- 月別ランキング（累積ポイント・平均順位）
- 席順別ランキング（累積ポイント・平均順位）
- 試合番号別ランキング（累積ポイント・平均順位）
""")

# ========== データ取得 ==========
conn = get_connection()
cursor = conn.cursor()

# 利用可能なシーズンを取得
cursor.execute("""
    SELECT DISTINCT season 
    FROM game_results 
    ORDER BY season DESC
""")
seasons = [row[0] for row in cursor.fetchall()]

if not seasons:
    st.warning("半荘記録データがありません。先に「🎮 半荘記録入力」でデータを登録してください。")
    conn.close()
    st.stop()

# ========== フィルター設定 ==========
st.markdown("---")
st.subheader("🔍 分析条件")

col1, col2 = st.columns(2)

with col1:
    period_options = ["全期間"] + seasons
    selected_period = st.selectbox("期間", period_options, key="period_select")

with col2:
    st.info(f"選択中: **{selected_period}**")

# ========== データ取得 ==========
if selected_period == "全期間":
    query = """
        SELECT 
            gr.player_id,
            p.player_name,
            gr.season,
            gr.game_date,
            gr.game_number,
            gr.seat_name,
            gr.points,
            gr.rank
        FROM game_results gr
        JOIN players p ON gr.player_id = p.player_id
        ORDER BY gr.season, gr.game_date, gr.game_number
    """
    cursor.execute(query)
else:
    query = """
        SELECT 
            gr.player_id,
            p.player_name,
            gr.season,
            gr.game_date,
            gr.game_number,
            gr.seat_name,
            gr.points,
            gr.rank
        FROM game_results gr
        JOIN players p ON gr.player_id = p.player_id
        WHERE gr.season = ?
        ORDER BY gr.game_date, gr.game_number
    """
    cursor.execute(query, (selected_period,))

results = cursor.fetchall()
conn.close()

if not results:
    st.warning("選択した期間に該当するデータがありません。")
    st.stop()

# DataFrameに変換
df = pd.DataFrame(results, columns=[
    'player_id', 'player_name', 'season', 'game_date', 
    'game_number', 'seat_name', 'points', 'rank'
])

# 月の情報を追加
df['month'] = pd.to_datetime(df['game_date']).dt.to_period('M').astype(str)

st.markdown("---")
st.info(f"📊 データ件数: {len(df)}対局 / {df['player_name'].nunique()}選手")

# ========== 月別ランキング ==========
st.markdown("---")
st.subheader("📅 月別ランキング")

# 月ごとの統計を計算
months = sorted(df['month'].unique())

tab_cumulative, tab_avg_rank = st.tabs(["累積ポイントランキング", "平均順位ランキング"])

with tab_cumulative:
    st.markdown("### 月別 累積ポイントランキング")
    
    for month in months:
        with st.expander(f"📅 {month}", expanded=False):
            month_df = df[df['month'] == month]
            
            # 選手ごとの統計
            player_stats = month_df.groupby(['player_id', 'player_name']).agg({
                'points': ['sum', 'mean', 'count'],
                'rank': 'mean'
            }).reset_index()
            
            player_stats.columns = ['player_id', 'player_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']
            
            # 順位計算
            player_stats = player_stats.sort_values('cumulative_points', ascending=False)
            player_stats.insert(0, '順位', range(1, len(player_stats) + 1))
            
            # 1位〜4位の回数を計算
            rank_counts = month_df.groupby('player_id')['rank'].value_counts().unstack(fill_value=0)
            for i in range(1, 5):
                if i not in rank_counts.columns:
                    rank_counts[i] = 0
            rank_counts = rank_counts[[1, 2, 3, 4]]
            rank_counts.columns = ['1位', '2位', '3位', '4位']
            
            # マージ
            player_stats = player_stats.merge(
                rank_counts,
                left_on='player_id',
                right_index=True,
                how='left'
            ).fillna(0)
            
            # 1位率を計算
            player_stats['1位率'] = (player_stats['1位'] / player_stats['games'] * 100).round(1)
            
            # 表示用に整形
            display_df = player_stats[[
                '順位', 'player_name', 'cumulative_points', 'avg_points', 
                'games', 'avg_rank', '1位', '2位', '3位', '4位', '1位率'
            ]].copy()
            
            display_df.columns = [
                '順位', '選手名', '累積pt', '平均pt', 
                '対局数', '平均順位', '1位', '2位', '3位', '4位', '1位率(%)'
            ]
            
            # フォーマット
            display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
            display_df['平均pt'] = display_df['平均pt'].apply(lambda x: f"{x:+.1f}")
            display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
            display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.1f}")
            
            st.dataframe(display_df, width='stretch', hide_index=True, height=400)

with tab_avg_rank:
    st.markdown("### 月別 平均順位ランキング")
    
    for month in months:
        with st.expander(f"📅 {month}", expanded=False):
            month_df = df[df['month'] == month]
            
            # 選手ごとの統計
            player_stats = month_df.groupby(['player_id', 'player_name']).agg({
                'points': ['sum', 'mean', 'count'],
                'rank': 'mean'
            }).reset_index()
            
            player_stats.columns = ['player_id', 'player_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']
            
            # 順位計算（平均順位の低い順）
            player_stats = player_stats.sort_values('avg_rank', ascending=True)
            player_stats.insert(0, '順位', range(1, len(player_stats) + 1))
            
            # 1位〜4位の回数を計算
            rank_counts = month_df.groupby('player_id')['rank'].value_counts().unstack(fill_value=0)
            for i in range(1, 5):
                if i not in rank_counts.columns:
                    rank_counts[i] = 0
            rank_counts = rank_counts[[1, 2, 3, 4]]
            rank_counts.columns = ['1位', '2位', '3位', '4位']
            
            # マージ
            player_stats = player_stats.merge(
                rank_counts,
                left_on='player_id',
                right_index=True,
                how='left'
            ).fillna(0)
            
            # 1位率を計算
            player_stats['1位率'] = (player_stats['1位'] / player_stats['games'] * 100).round(1)
            
            # 表示用に整形
            display_df = player_stats[[
                '順位', 'player_name', 'avg_rank', 'games',
                'cumulative_points', '1位', '2位', '3位', '4位', '1位率'
            ]].copy()
            
            display_df.columns = [
                '順位', '選手名', '平均順位', '対局数',
                '累積pt', '1位', '2位', '3位', '4位', '1位率(%)'
            ]
            
            # フォーマット
            display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
            display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
            display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.1f}")
            
            st.dataframe(display_df, width='stretch', hide_index=True, height=400)

# ========== 席順別ランキング ==========
st.markdown("---")
st.subheader("🧭 席順別ランキング")

seats = ['東', '南', '西', '北']

tab_seat_cumulative, tab_seat_avg_rank = st.tabs(["累積ポイントランキング", "平均順位ランキング"])

with tab_seat_cumulative:
    st.markdown("### 席順別 累積ポイントランキング")
    
    seat_tabs = st.tabs([f"{seat}家" for seat in seats])
    
    for seat_idx, seat in enumerate(seats):
        with seat_tabs[seat_idx]:
            seat_df = df[df['seat_name'] == seat]
            
            if len(seat_df) == 0:
                st.info(f"{seat}家のデータがありません")
                continue
            
            # 選手ごとの統計
            player_stats = seat_df.groupby(['player_id', 'player_name']).agg({
                'points': ['sum', 'mean', 'count'],
                'rank': 'mean'
            }).reset_index()
            
            player_stats.columns = ['player_id', 'player_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']
            
            # 順位計算
            player_stats = player_stats.sort_values('cumulative_points', ascending=False)
            player_stats.insert(0, '順位', range(1, len(player_stats) + 1))
            
            # 1位〜4位の回数を計算
            rank_counts = seat_df.groupby('player_id')['rank'].value_counts().unstack(fill_value=0)
            for i in range(1, 5):
                if i not in rank_counts.columns:
                    rank_counts[i] = 0
            rank_counts = rank_counts[[1, 2, 3, 4]]
            rank_counts.columns = ['1位', '2位', '3位', '4位']
            
            # マージ
            player_stats = player_stats.merge(
                rank_counts,
                left_on='player_id',
                right_index=True,
                how='left'
            ).fillna(0)
            
            # 1位率を計算
            player_stats['1位率'] = (player_stats['1位'] / player_stats['games'] * 100).round(1)
            
            # 表示用に整形
            display_df = player_stats[[
                '順位', 'player_name', 'cumulative_points', 'avg_points', 
                'games', 'avg_rank', '1位', '2位', '3位', '4位', '1位率'
            ]].copy()
            
            display_df.columns = [
                '順位', '選手名', '累積pt', '平均pt', 
                '対局数', '平均順位', '1位', '2位', '3位', '4位', '1位率(%)'
            ]
            
            # フォーマット
            display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
            display_df['平均pt'] = display_df['平均pt'].apply(lambda x: f"{x:+.1f}")
            display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
            display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.1f}")
            
            st.dataframe(display_df, width='stretch', hide_index=True, height=400)

with tab_seat_avg_rank:
    st.markdown("### 席順別 平均順位ランキング")
    
    seat_tabs = st.tabs([f"{seat}家" for seat in seats])
    
    for seat_idx, seat in enumerate(seats):
        with seat_tabs[seat_idx]:
            seat_df = df[df['seat_name'] == seat]
            
            if len(seat_df) == 0:
                st.info(f"{seat}家のデータがありません")
                continue
            
            # 選手ごとの統計
            player_stats = seat_df.groupby(['player_id', 'player_name']).agg({
                'points': ['sum', 'mean', 'count'],
                'rank': 'mean'
            }).reset_index()
            
            player_stats.columns = ['player_id', 'player_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']
            
            # 順位計算（平均順位の低い順）
            player_stats = player_stats.sort_values('avg_rank', ascending=True)
            player_stats.insert(0, '順位', range(1, len(player_stats) + 1))
            
            # 1位〜4位の回数を計算
            rank_counts = seat_df.groupby('player_id')['rank'].value_counts().unstack(fill_value=0)
            for i in range(1, 5):
                if i not in rank_counts.columns:
                    rank_counts[i] = 0
            rank_counts = rank_counts[[1, 2, 3, 4]]
            rank_counts.columns = ['1位', '2位', '3位', '4位']
            
            # マージ
            player_stats = player_stats.merge(
                rank_counts,
                left_on='player_id',
                right_index=True,
                how='left'
            ).fillna(0)
            
            # 1位率を計算
            player_stats['1位率'] = (player_stats['1位'] / player_stats['games'] * 100).round(1)
            
            # 表示用に整形
            display_df = player_stats[[
                '順位', 'player_name', 'avg_rank', 'games',
                'cumulative_points', '1位', '2位', '3位', '4位', '1位率'
            ]].copy()
            
            display_df.columns = [
                '順位', '選手名', '平均順位', '対局数',
                '累積pt', '1位', '2位', '3位', '4位', '1位率(%)'
            ]
            
            # フォーマット
            display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
            display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
            display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.1f}")
            
            st.dataframe(display_df, width='stretch', hide_index=True, height=400)

# ========== 試合番号別ランキング ==========
st.markdown("---")
st.subheader("🎮 試合番号別ランキング")

game_numbers = sorted(df['game_number'].unique())

tab_game_cumulative, tab_game_avg_rank = st.tabs(["累積ポイントランキング", "平均順位ランキング"])

with tab_game_cumulative:
    st.markdown("### 試合番号別 累積ポイントランキング")
    
    for game_number in game_numbers:
        with st.expander(f"🎮 第{game_number}試合", expanded=False):
            game_df = df[df['game_number'] == game_number]
            
            # 選手ごとの統計
            player_stats = game_df.groupby(['player_id', 'player_name']).agg({
                'points': ['sum', 'mean', 'count'],
                'rank': 'mean'
            }).reset_index()
            
            player_stats.columns = ['player_id', 'player_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']
            
            # 順位計算
            player_stats = player_stats.sort_values('cumulative_points', ascending=False)
            player_stats.insert(0, '順位', range(1, len(player_stats) + 1))
            
            # 1位〜4位の回数を計算
            rank_counts = game_df.groupby('player_id')['rank'].value_counts().unstack(fill_value=0)
            for i in range(1, 5):
                if i not in rank_counts.columns:
                    rank_counts[i] = 0
            rank_counts = rank_counts[[1, 2, 3, 4]]
            rank_counts.columns = ['1位', '2位', '3位', '4位']
            
            # マージ
            player_stats = player_stats.merge(
                rank_counts,
                left_on='player_id',
                right_index=True,
                how='left'
            ).fillna(0)
            
            # 1位率を計算
            player_stats['1位率'] = (player_stats['1位'] / player_stats['games'] * 100).round(1)
            
            # 表示用に整形
            display_df = player_stats[[
                '順位', 'player_name', 'cumulative_points', 'avg_points', 
                'games', 'avg_rank', '1位', '2位', '3位', '4位', '1位率'
            ]].copy()
            
            display_df.columns = [
                '順位', '選手名', '累積pt', '平均pt', 
                '対局数', '平均順位', '1位', '2位', '3位', '4位', '1位率(%)'
            ]
            
            # フォーマット
            display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
            display_df['平均pt'] = display_df['平均pt'].apply(lambda x: f"{x:+.1f}")
            display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
            display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.1f}")
            
            st.dataframe(display_df, width='stretch', hide_index=True, height=400)

with tab_game_avg_rank:
    st.markdown("### 試合番号別 平均順位ランキング")
    
    for game_number in game_numbers:
        with st.expander(f"🎮 第{game_number}試合", expanded=False):
            game_df = df[df['game_number'] == game_number]
            
            # 選手ごとの統計
            player_stats = game_df.groupby(['player_id', 'player_name']).agg({
                'points': ['sum', 'mean', 'count'],
                'rank': 'mean'
            }).reset_index()
            
            player_stats.columns = ['player_id', 'player_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']
            
            # 順位計算（平均順位の低い順）
            player_stats = player_stats.sort_values('avg_rank', ascending=True)
            player_stats.insert(0, '順位', range(1, len(player_stats) + 1))
            
            # 1位〜4位の回数を計算
            rank_counts = game_df.groupby('player_id')['rank'].value_counts().unstack(fill_value=0)
            for i in range(1, 5):
                if i not in rank_counts.columns:
                    rank_counts[i] = 0
            rank_counts = rank_counts[[1, 2, 3, 4]]
            rank_counts.columns = ['1位', '2位', '3位', '4位']
            
            # マージ
            player_stats = player_stats.merge(
                rank_counts,
                left_on='player_id',
                right_index=True,
                how='left'
            ).fillna(0)
            
            # 1位率を計算
            player_stats['1位率'] = (player_stats['1位'] / player_stats['games'] * 100).round(1)
            
            # 表示用に整形
            display_df = player_stats[[
                '順位', 'player_name', 'avg_rank', 'games',
                'cumulative_points', '1位', '2位', '3位', '4位', '1位率'
            ]].copy()
            
            display_df.columns = [
                '順位', '選手名', '平均順位', '対局数',
                '累積pt', '1位', '2位', '3位', '4位', '1位率(%)'
            ]
            
            # フォーマット
            display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
            display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
            display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.1f}")
            
            st.dataframe(display_df, width='stretch', hide_index=True, height=400)
