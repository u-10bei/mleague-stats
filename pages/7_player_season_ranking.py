import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
sys.path.append("..")
from db import get_player_seasons, get_player_season_ranking, get_connection, hide_default_sidebar_navigation

st.set_page_config(
    page_title="年度別選手ランキング | Mリーグダッシュボード",
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

st.title("📊 年度別選手ランキング")

# シーズン一覧を取得
seasons = get_player_seasons()

if not seasons:
    st.warning("選手成績データがありません。「選手成績入力」ページで成績を登録してください。")
    st.stop()

# シーズン選択
selected_season = st.selectbox("シーズンを選択", seasons)

# 選択シーズンのデータ
season_df = get_player_season_ranking(selected_season)

if season_df.empty:
    st.warning(f"{selected_season}シーズンの選手成績がありません。")
    st.stop()

st.markdown(f"## {selected_season}シーズン 選手成績")

col1, col2 = st.columns([2, 1])

with col1:
    # 横棒グラフ（上位20名）
    fig = go.Figure()
    
    display_df = season_df.head(20).sort_values("points", ascending=True)
    
    for _, row in display_df.iterrows():
        color = row["color"] if pd.notna(row["color"]) else "#888888"
        fig.add_trace(go.Bar(
            y=[row["player_name"]],
            x=[row["points"]],
            orientation="h",
            marker_color=color,
            name=row["player_name"],
            text=f"{row['points']:+.1f}",
            textposition="outside",
            showlegend=False,
            hovertemplate=f"<b>{row['player_name']}</b><br>" +
                         f"{row['team_name']}<br>" +
                         f"ポイント: {row['points']:+.1f}<br>" +
                         f"試合数: {row['games']}<br>" +
                         "<extra></extra>"
        ))
    
    fig.update_layout(
        title=f"{selected_season}シーズン 選手別ポイント（上位20名）",
        xaxis_title="ポイント",
        yaxis_title="",
        height=600,
        margin=dict(l=150, r=100, t=50, b=50),
        xaxis=dict(zeroline=True, zerolinecolor="gray", zerolinewidth=2)
    )
    
    st.plotly_chart(fig, width="stretch")

with col2:
    # ランキング表（上位10名）
    st.markdown("### 🏆 ランキング TOP10")
    
    rank_df = season_df.head(10)[["rank", "player_name", "team_name", "points", "games"]].copy()
    rank_df.columns = ["順位", "選手名", "所属", "ポイント", "試合数"]
    rank_df["ポイント"] = rank_df["ポイント"].apply(lambda x: f"{x:+.1f}")
    rank_df = rank_df.reset_index(drop=True)
    
    st.dataframe(rank_df, hide_index=True, height=400)
    
    # 統計情報
    st.markdown("### 📈 統計情報")
    st.metric("登録選手数", f"{len(season_df)}名")
    st.metric("総試合数", f"{season_df['games'].sum()}試合")
    st.metric("平均ポイント", f"{season_df['points'].mean():+.1f}pt")

st.markdown("---")

# 詳細ランキング表
st.subheader("📋 全選手ランキング")

# フィルター
col1, col2 = st.columns([1, 3])

with col1:
    min_games = st.number_input("最低試合数", min_value=0, value=0, step=1)

with col2:
    search_name = st.text_input("選手名で検索", placeholder="例: 園田")

# フィルター適用
filtered_df = season_df.copy()
if min_games > 0:
    filtered_df = filtered_df[filtered_df['games'] >= min_games]
if search_name:
    filtered_df = filtered_df[filtered_df['player_name'].str.contains(search_name, na=False)]

# 詳細データ表示
detail_df = filtered_df[["rank", "player_name", "team_name", "games", "points", 
                         "rank_1st", "rank_2nd", "rank_3rd", "rank_4th"]].copy()
detail_df.columns = ["順位", "選手名", "所属チーム", "試合数", "ポイント", "1位", "2位", "3位", "4位"]
detail_df["ポイント"] = detail_df["ポイント"].apply(lambda x: f"{x:+.1f}")

# 平均順位を計算
filtered_df['avg_rank'] = (
    filtered_df['rank_1st'] * 1 + 
    filtered_df['rank_2nd'] * 2 + 
    filtered_df['rank_3rd'] * 3 + 
    filtered_df['rank_4th'] * 4
) / filtered_df['games']
detail_df["平均順位"] = filtered_df['avg_rank'].apply(lambda x: f"{x:.2f}")

st.dataframe(
    detail_df,
    hide_index=True,
    column_config={
        "順位": st.column_config.NumberColumn(width="small"),
        "選手名": st.column_config.TextColumn(width="medium"),
        "所属チーム": st.column_config.TextColumn(width="medium"),
        "試合数": st.column_config.NumberColumn(width="small"),
        "ポイント": st.column_config.TextColumn(width="small"),
        "1位": st.column_config.NumberColumn(width="small"),
        "2位": st.column_config.NumberColumn(width="small"),
        "3位": st.column_config.NumberColumn(width="small"),
        "4位": st.column_config.NumberColumn(width="small"),
        "平均順位": st.column_config.TextColumn(width="small"),
    }
)

st.markdown(f"**表示件数: {len(filtered_df)}名**")

st.markdown("---")

# 月別ランキング
st.subheader(f"📅 {selected_season}シーズン 月別ランキング")

conn = get_connection()
cursor = conn.cursor()

# 半荘記録の存在確認
cursor.execute("""
    SELECT COUNT(*) 
    FROM game_results 
    WHERE season = ?
""", (selected_season,))

game_count = cursor.fetchone()[0]

if game_count > 0:
    # 半荘記録から選手別月別成績を取得
    query = """
        SELECT 
            strftime('%Y-%m', gr.game_date) as month,
            gr.player_id,
            p.player_name,
            SUM(gr.points) as total_points,
            COUNT(*) as games,
            AVG(gr.rank) as avg_rank,
            SUM(CASE WHEN gr.rank = 1 THEN 1 ELSE 0 END) as rank_1st,
            SUM(CASE WHEN gr.rank = 2 THEN 1 ELSE 0 END) as rank_2nd,
            SUM(CASE WHEN gr.rank = 3 THEN 1 ELSE 0 END) as rank_3rd,
            SUM(CASE WHEN gr.rank = 4 THEN 1 ELSE 0 END) as rank_4th
        FROM game_results gr
        JOIN players p ON gr.player_id = p.player_id
        WHERE gr.season = ?
        GROUP BY month, gr.player_id, p.player_name
        ORDER BY month, total_points DESC
    """
    
    df = pd.read_sql_query(query, conn, params=(selected_season,))
    conn.close()
    
    if not df.empty:
        months = sorted(df['month'].unique())
        
        st.markdown("### 月別ランキング（累積ポイント順）")
        
        for month in months:
            with st.expander(f"📅 {month}", expanded=False):
                month_df = df[df['month'] == month].copy()
                
                # 累積ポイント順に並べる
                month_df = month_df.sort_values('total_points', ascending=False)
                month_df.insert(0, '順位', range(1, len(month_df) + 1))
                
                # 1位率を計算
                month_df['first_rate'] = (month_df['rank_1st'] / month_df['games'] * 100).round(1)
                
                # 表示用に整形
                display_df = month_df[[
                    '順位', 'player_name', 'total_points', 'games', 'avg_rank',
                    'rank_1st', 'rank_2nd', 'rank_3rd', 'rank_4th', 'first_rate'
                ]].copy()
                
                display_df.columns = [
                    '順位', '選手名', '累積pt', '対局数', '平均順位',
                    '1位', '2位', '3位', '4位', '1位率(%)'
                ]
                
                display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
                display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
                display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.1f}")
                
                st.dataframe(display_df, width='stretch', hide_index=True, height=400)
    else:
        st.info(f"{selected_season}シーズンの半荘記録がありません。")
else:
    st.info(f"{selected_season}シーズンの半荘記録がありません。「🎮 半荘記録入力」ページで対局結果を記録してください。")
    conn.close()

st.markdown("---")

# 席順別統計
st.subheader(f"🧭 {selected_season}シーズン 席順別統計")

conn = get_connection()
cursor = conn.cursor()

# 半荘記録の存在確認
cursor.execute("""
    SELECT COUNT(*) 
    FROM game_results 
    WHERE season = ?
""", (selected_season,))

game_count = cursor.fetchone()[0]

if game_count > 0:
    # 席順別統計を取得
    query = """
        SELECT 
            gr.seat_name,
            gr.player_id,
            p.player_name,
            COUNT(*) as games,
            SUM(gr.points) as total_points,
            AVG(gr.points) as avg_points,
            AVG(gr.rank) as avg_rank,
            SUM(CASE WHEN gr.rank = 1 THEN 1 ELSE 0 END) as rank_1st,
            SUM(CASE WHEN gr.rank = 2 THEN 1 ELSE 0 END) as rank_2nd,
            SUM(CASE WHEN gr.rank = 3 THEN 1 ELSE 0 END) as rank_3rd,
            SUM(CASE WHEN gr.rank = 4 THEN 1 ELSE 0 END) as rank_4th
        FROM game_results gr
        JOIN players p ON gr.player_id = p.player_id
        WHERE gr.season = ?
        GROUP BY gr.seat_name, gr.player_id, p.player_name
        ORDER BY gr.seat_name, total_points DESC
    """
    
    seat_df = pd.read_sql_query(query, conn, params=(selected_season,))
    
    if not seat_df.empty:
        seats = ['東', '南', '西', '北']
        
        for seat in seats:
            with st.expander(f"🧭 {seat}家", expanded=False):
                seat_data = seat_df[seat_df['seat_name'] == seat].copy()
                
                if not seat_data.empty:
                    # 1位率を計算
                    seat_data['first_rate'] = (seat_data['rank_1st'] / seat_data['games'] * 100).round(1)
                    
                    # 順位を追加
                    seat_data = seat_data.sort_values('total_points', ascending=False)
                    seat_data.insert(0, '順位', range(1, len(seat_data) + 1))
                    
                    # 表示用に整形
                    display_df = seat_data[[
                        '順位', 'player_name', 'games', 'total_points', 'avg_points',
                        'avg_rank', 'rank_1st', 'rank_2nd', 'rank_3rd', 'rank_4th', 'first_rate'
                    ]].copy()
                    
                    display_df.columns = [
                        '順位', '選手名', '対局数', '累積pt', '平均pt',
                        '平均順位', '1位', '2位', '3位', '4位', '1位率(%)'
                    ]
                    
                    display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
                    display_df['平均pt'] = display_df['平均pt'].apply(lambda x: f"{x:+.1f}")
                    display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
                    display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.1f}")
                    
                    st.dataframe(display_df, width='stretch', hide_index=True, height=400)
                else:
                    st.info(f"{seat}家のデータがありません")
    else:
        st.info(f"{selected_season}シーズンの席順別データがありません。")
else:
    st.info(f"{selected_season}シーズンの半荘記録がありません。")

conn.close()

st.markdown("---")

# 対局時間ランキング
st.subheader(f"⏱️ {selected_season}シーズン 対局時間ランキング")

conn = get_connection()
cursor = conn.cursor()

# 対局時間データを取得
query = """
    SELECT 
        gr.player_id,
        p.player_name,
        gr.game_date,
        gr.game_number,
        gr.start_time,
        gr.end_time
    FROM game_results gr
    JOIN players p ON gr.player_id = p.player_id
    WHERE gr.season = ? AND gr.start_time IS NOT NULL AND gr.end_time IS NOT NULL
"""

time_df = pd.read_sql_query(query, conn, params=(selected_season,))
conn.close()

if not time_df.empty:
    # 対局時間（分）を計算
    def calc_duration(row):
        try:
            start_parts = row['start_time'].split(':')
            end_parts = row['end_time'].split(':')
            start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
            duration = end_minutes - start_minutes
            if duration < 0:
                duration += 24 * 60  # 日付をまたぐ場合
            return duration
        except:
            return None
    
    time_df['duration'] = time_df.apply(calc_duration, axis=1)
    time_df = time_df[time_df['duration'].notna()]
    
    if not time_df.empty:
        # 選手別の統計
        player_time_stats = time_df.groupby(['player_id', 'player_name']).agg({
            'duration': ['count', 'mean', 'min', 'max']
        }).reset_index()
        
        player_time_stats.columns = ['player_id', 'player_name', 'games', 'avg_duration', 'min_duration', 'max_duration']
        
        # 平均時間でソート
        player_time_stats = player_time_stats.sort_values('avg_duration', ascending=True)
        player_time_stats.insert(0, '順位', range(1, len(player_time_stats) + 1))
        
        # 時間を時:分形式に変換
        def format_duration(minutes):
            hours = int(minutes // 60)
            mins = int(minutes % 60)
            return f"{hours}:{mins:02d}"
        
        # 表示用に整形
        display_df = player_time_stats[[
            '順位', 'player_name', 'games', 'avg_duration', 'min_duration', 'max_duration'
        ]].copy()
        
        display_df.columns = [
            '順位', '選手名', '対局数', '平均時間', '最短時間', '最長時間'
        ]
        
        display_df['平均時間'] = display_df['平均時間'].apply(format_duration)
        display_df['最短時間'] = display_df['最短時間'].apply(format_duration)
        display_df['最長時間'] = display_df['最長時間'].apply(format_duration)
        
        st.dataframe(display_df, width='stretch', hide_index=True)
        
        st.info("💡 対局時間は「開始時間」から「終了時間」までの所要時間です。時間が記録されている対局のみが対象となります。")
    else:
        st.info(f"{selected_season}シーズンの有効な対局時間データがありません。")
else:
    st.info(f"{selected_season}シーズンの対局時間データがありません。「🎮 半荘記録入力」ページで開始・終了時間を記録してください。")

st.markdown("---")
st.caption("※ データはデータベースに登録された情報を表示しています。")
