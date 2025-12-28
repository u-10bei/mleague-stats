import streamlit as st
import pandas as pd
from datetime import datetime
from db import get_connection, hide_default_sidebar_navigation

st.set_page_config(
    page_title="連続記録 | Mリーグダッシュボード",
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
st.sidebar.page_link("pages/16_streak_records.py", label="🔥 連続記録")
st.sidebar.page_link("pages/15_game_records.py", label="📜 対局記録")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/3_admin.py", label="⚙️ データ管理")
st.sidebar.page_link("pages/4_player_admin.py", label="👤 選手管理")
st.sidebar.page_link("pages/9_team_master_admin.py", label="🏢 チーム管理")
st.sidebar.page_link("pages/5_season_update.py", label="🔄 シーズン更新")
st.sidebar.page_link("pages/6_player_stats_input.py", label="📊 選手成績入力")
st.sidebar.page_link("pages/11_game_results_input.py", label="🎮 半荘記録入力")

st.title("🔥 連続記録")

st.markdown("""
選手の連続記録を分析します。
- **連勝**: 連続1位
- **連敗**: 連続4位
- **連続連対**: 連続2位以内
- **連続逆連対**: 連続3位以下
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
            gr.rank
        FROM game_results gr
        JOIN players p ON gr.player_id = p.player_id
        ORDER BY gr.player_id, gr.season, gr.game_date, gr.game_number
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
            gr.rank
        FROM game_results gr
        JOIN players p ON gr.player_id = p.player_id
        WHERE gr.season = ?
        ORDER BY gr.player_id, gr.game_date, gr.game_number
    """
    cursor.execute(query, (selected_period,))

results = cursor.fetchall()
conn.close()

if not results:
    st.warning("選択した期間に該当するデータがありません。")
    st.stop()

# DataFrameに変換
df = pd.DataFrame(results, columns=[
    'player_id', 'player_name', 'season', 'game_date', 'game_number', 'rank'
])

st.markdown("---")
st.info(f"📊 データ件数: {len(df)}対局 / {df['player_name'].nunique()}選手")


# ========== 連続記録計算関数 ==========
def calculate_streaks(df, condition_func, streak_name):
    """
    連続記録を計算する汎用関数
    
    Args:
        df: 対局データ（player_id, game_date, game_number, rank順にソート済み）
        condition_func: 条件判定関数（rankを受け取りTrueまたはFalseを返す）
        streak_name: 連続記録の名前（表示用）
    
    Returns:
        current_streaks: 現在進行中の連続記録のDataFrame
        all_time_streaks: 歴代最長記録のDataFrame
    """
    all_streaks = []
    
    for player_id, player_group in df.groupby('player_id'):
        player_name = player_group.iloc[0]['player_name']
        player_group = player_group.sort_values(['season', 'game_date', 'game_number'])
        
        current_streak = 0
        streak_start_date = None
        streak_start_season = None
        max_streak = 0
        max_streak_start = None
        max_streak_end = None
        max_streak_season_start = None
        max_streak_season_end = None
        max_streak_is_active = False  # 歴代最長が現在進行中かどうか
        
        for idx, row in player_group.iterrows():
            if condition_func(row['rank']):
                if current_streak == 0:
                    streak_start_date = row['game_date']
                    streak_start_season = row['season']
                current_streak += 1
            else:
                if current_streak > 0:
                    # 連続が途切れた
                    if current_streak > max_streak:
                        max_streak = current_streak
                        max_streak_start = streak_start_date
                        max_streak_end = player_group.iloc[player_group.index.get_loc(idx) - 1]['game_date']
                        max_streak_season_start = streak_start_season
                        max_streak_season_end = player_group.iloc[player_group.index.get_loc(idx) - 1]['season']
                        max_streak_is_active = False  # 途切れたので進行中ではない
                    
                    current_streak = 0
                    streak_start_date = None
        
        # 最後まで連続していた場合の処理
        is_currently_active = current_streak > 0
        if is_currently_active:
            if current_streak > max_streak:
                # 現在の連続が歴代最長を更新
                max_streak = current_streak
                max_streak_start = streak_start_date
                max_streak_end = player_group.iloc[-1]['game_date']
                max_streak_season_start = streak_start_season
                max_streak_season_end = player_group.iloc[-1]['season']
                max_streak_is_active = True
            elif current_streak == max_streak:
                # 現在の連続が歴代最長と同じ（稀だが可能性あり）
                max_streak_is_active = True
        
        # 記録がある場合のみ追加
        if max_streak > 0:
            all_streaks.append({
                'player_id': player_id,
                'player_name': player_name,
                'streak': max_streak,
                'start_date': max_streak_start,
                'end_date': max_streak_end,
                'season_start': max_streak_season_start,
                'season_end': max_streak_season_end,
                'is_active': max_streak_is_active,
                'current_streak': current_streak if is_currently_active else 0
            })
    
    streaks_df = pd.DataFrame(all_streaks)
    
    if streaks_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # 現在進行中の連続記録（current_streak > 0の選手のみ）
    current_streaks = streaks_df[streaks_df['current_streak'] > 0].copy()
    current_streaks = current_streaks.sort_values('current_streak', ascending=False).reset_index(drop=True)
    current_streaks['rank'] = range(1, len(current_streaks) + 1)
    
    # 歴代最長記録
    all_time_streaks = streaks_df.sort_values('streak', ascending=False).reset_index(drop=True)
    all_time_streaks['rank'] = range(1, len(all_time_streaks) + 1)
    
    return current_streaks, all_time_streaks


# ========== タブ構成 ==========
tab1, tab2, tab3, tab4 = st.tabs(["🔥 連勝記録", "💔 連敗記録", "🏆 連続連対", "😓 連続逆連対"])

# ========== タブ1: 連勝記録 ==========
with tab1:
    st.markdown("## 🔥 連勝記録（連続1位）")
    
    current_wins, alltime_wins = calculate_streaks(df, lambda rank: rank == 1, "連勝")
    
    if not current_wins.empty or not alltime_wins.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 現在進行中の連勝")
            
            if not current_wins.empty:
                display_current = current_wins.head(10)[['rank', 'player_name', 'current_streak', 'start_date']].copy()
                display_current.columns = ['順位', '選手名', '連勝数', '開始日']
                st.dataframe(display_current, hide_index=True, width='stretch')
            else:
                st.info("現在進行中の連勝記録はありません。")
        
        with col2:
            st.markdown("### 🏆 歴代最長連勝記録")
            
            if not alltime_wins.empty:
                display_alltime = alltime_wins.head(10)[['rank', 'player_name', 'streak', 'start_date', 'end_date', 'is_active']].copy()
                display_alltime.columns = ['順位', '選手名', '連勝数', '開始日', '終了日', '進行中']
                display_alltime['進行中'] = display_alltime['進行中'].apply(lambda x: '✅' if x else '')
                st.dataframe(display_alltime, hide_index=True, width='stretch')
            else:
                st.info("連勝記録がありません。")
    else:
        st.info("連勝記録データがありません。")

# ========== タブ2: 連敗記録 ==========
with tab2:
    st.markdown("## 💔 連敗記録（連続4位）")
    
    current_losses, alltime_losses = calculate_streaks(df, lambda rank: rank == 4, "連敗")
    
    if not current_losses.empty or not alltime_losses.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📉 現在進行中の連敗")
            
            if not current_losses.empty:
                display_current = current_losses.head(10)[['rank', 'player_name', 'current_streak', 'start_date']].copy()
                display_current.columns = ['順位', '選手名', '連敗数', '開始日']
                st.dataframe(display_current, hide_index=True, width='stretch')
            else:
                st.info("現在進行中の連敗記録はありません。")
        
        with col2:
            st.markdown("### 💀 歴代最長連敗記録")
            
            if not alltime_losses.empty:
                display_alltime = alltime_losses.head(10)[['rank', 'player_name', 'streak', 'start_date', 'end_date', 'is_active']].copy()
                display_alltime.columns = ['順位', '選手名', '連敗数', '開始日', '終了日', '進行中']
                display_alltime['進行中'] = display_alltime['進行中'].apply(lambda x: '✅' if x else '')
                st.dataframe(display_alltime, hide_index=True, width='stretch')
            else:
                st.info("連敗記録がありません。")
    else:
        st.info("連敗記録データがありません。")

# ========== タブ3: 連続連対記録 ==========
with tab3:
    st.markdown("## 🏆 連続連対記録（連続2位以内）")
    
    current_top2, alltime_top2 = calculate_streaks(df, lambda rank: rank <= 2, "連続連対")
    
    if not current_top2.empty or not alltime_top2.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 現在進行中の連続連対")
            
            if not current_top2.empty:
                display_current = current_top2.head(10)[['rank', 'player_name', 'current_streak', 'start_date']].copy()
                display_current.columns = ['順位', '選手名', '連続数', '開始日']
                st.dataframe(display_current, hide_index=True, width='stretch')
            else:
                st.info("現在進行中の連続連対記録はありません。")
        
        with col2:
            st.markdown("### 🏆 歴代最長連続連対記録")
            
            if not alltime_top2.empty:
                display_alltime = alltime_top2.head(10)[['rank', 'player_name', 'streak', 'start_date', 'end_date', 'is_active']].copy()
                display_alltime.columns = ['順位', '選手名', '連続数', '開始日', '終了日', '進行中']
                display_alltime['進行中'] = display_alltime['進行中'].apply(lambda x: '✅' if x else '')
                st.dataframe(display_alltime, hide_index=True, width='stretch')
            else:
                st.info("連続連対記録がありません。")
    else:
        st.info("連続連対記録データがありません。")

# ========== タブ4: 連続逆連対記録 ==========
with tab4:
    st.markdown("## 😓 連続逆連対記録（連続3位以下）")
    
    current_bottom2, alltime_bottom2 = calculate_streaks(df, lambda rank: rank >= 3, "連続逆連対")
    
    if not current_bottom2.empty or not alltime_bottom2.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📉 現在進行中の連続逆連対")
            
            if not current_bottom2.empty:
                display_current = current_bottom2.head(10)[['rank', 'player_name', 'current_streak', 'start_date']].copy()
                display_current.columns = ['順位', '選手名', '連続数', '開始日']
                st.dataframe(display_current, hide_index=True, width='stretch')
            else:
                st.info("現在進行中の連続逆連対記録はありません。")
        
        with col2:
            st.markdown("### 💀 歴代最長連続逆連対記録")
            
            if not alltime_bottom2.empty:
                display_alltime = alltime_bottom2.head(10)[['rank', 'player_name', 'streak', 'start_date', 'end_date', 'is_active']].copy()
                display_alltime.columns = ['順位', '選手名', '連続数', '開始日', '終了日', '進行中']
                display_alltime['進行中'] = display_alltime['進行中'].apply(lambda x: '✅' if x else '')
                st.dataframe(display_alltime, hide_index=True, width='stretch')
            else:
                st.info("連続逆連対記録がありません。")
    else:
        st.info("連続逆連対記録データがありません。")

st.markdown("---")
st.caption("※ 連続記録は対局の時系列順に基づいて計算されます。")
