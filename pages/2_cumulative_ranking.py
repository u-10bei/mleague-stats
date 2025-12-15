import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
sys.path.append("..")
from db import get_team_colors, get_season_points, get_cumulative_points, get_team_history, get_teams, get_connection, hide_default_sidebar_navigation

st.set_page_config(
    page_title="累積ランキング | Mリーグダッシュボード",
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

st.title("🏆 累積ポイントランキング")

# データ読み込み
team_colors = get_team_colors()
cumulative_df = get_cumulative_points()

if cumulative_df.empty:
    st.warning("データがありません")
    st.stop()

st.markdown("## 全シーズン通算成績")

col1, col2 = st.columns([2, 1])

with col1:
    # 累積ポイント棒グラフ
    fig = go.Figure()
    
    for _, row in cumulative_df.sort_values("total_points", ascending=True).iterrows():
        color = team_colors.get(row["team_id"], "#888888")
        fig.add_trace(go.Bar(
            y=[row["team_name"]],
            x=[row["total_points"]],
            orientation="h",
            marker_color=color,
            name=row["team_name"],
            text=f"{row['total_points']:+.1f}",
            textposition="outside",
            showlegend=False
        ))
    
    fig.update_layout(
        title="チーム別 累積ポイント",
        xaxis_title="累積ポイント",
        yaxis_title="",
        height=400,
        margin=dict(l=20, r=100, t=50, b=50),
        xaxis=dict(zeroline=True, zerolinecolor="gray", zerolinewidth=2)
    )
    
    st.plotly_chart(fig)

with col2:
    # 順位表
    st.markdown("### 通算順位表")
    
    display_df = cumulative_df[["rank", "team_name", "total_points", "seasons", "avg_points"]].copy()
    display_df.columns = ["順位", "チーム", "累積pt", "参加", "平均pt"]
    display_df["累積pt"] = display_df["累積pt"].apply(lambda x: f"{x:+.1f}")
    display_df["平均pt"] = display_df["平均pt"].apply(lambda x: f"{x:+.1f}")
    
    st.dataframe(display_df, hide_index=True)

st.markdown("---")

# 全シーズン順位推移グラフ
st.subheader("📈 全シーズン順位推移")

season_df = get_season_points()
rank_pivot = season_df.pivot(index="season", columns="team_id", values="rank")

fig2 = go.Figure()

# team_idからチーム名へのマッピング（最新シーズンの名前を使用）
latest_names = season_df[season_df["season"] == season_df["season"].max()].set_index("team_id")["team_name"].to_dict()

for team_id in rank_pivot.columns:
    color = team_colors.get(team_id, "#888888")
    team_name = latest_names.get(team_id, f"Team {team_id}")
    fig2.add_trace(go.Scatter(
        x=rank_pivot.index,
        y=rank_pivot[team_id],
        mode="lines+markers",
        name=team_name,
        line=dict(color=color, width=2),
        marker=dict(size=8)
    ))

fig2.update_layout(
    title="チーム別順位推移",
    xaxis_title="シーズン",
    yaxis_title="順位",
    yaxis=dict(autorange="reversed", dtick=1),
    height=500,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.3,
        xanchor="center",
        x=0.5
    )
)

st.plotly_chart(fig2)

st.markdown("---")

# 累積ポイント推移
st.subheader("📈 累積ポイント推移")

season_df = get_season_points()
seasons = sorted(season_df["season"].unique())
team_ids = season_df["team_id"].unique()

# 最新のチーム名マッピング
latest_names = cumulative_df.set_index("team_id")["team_name"].to_dict()

cumulative_by_season = []
for team_id in team_ids:
    team_data = season_df[season_df["team_id"] == team_id].sort_values("season")
    cum_points = 0
    for _, row in team_data.iterrows():
        cum_points += row["points"]
        cumulative_by_season.append({
            "team_id": team_id,
            "season": row["season"],
            "cumulative_points": cum_points
        })

cum_df = pd.DataFrame(cumulative_by_season)

fig3 = go.Figure()

for team_id in team_ids:
    team_data = cum_df[cum_df["team_id"] == team_id]
    color = team_colors.get(team_id, "#888888")
    team_name = latest_names.get(team_id, f"Team {team_id}")
    fig3.add_trace(go.Scatter(
        x=team_data["season"],
        y=team_data["cumulative_points"],
        mode="lines+markers",
        name=team_name,
        line=dict(color=color, width=2),
        marker=dict(size=8)
    ))

fig3.update_layout(
    title="チーム別 累積ポイント推移",
    xaxis_title="シーズン",
    yaxis_title="累積ポイント",
    height=500,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.3,
        xanchor="center",
        x=0.5
    ),
    yaxis=dict(zeroline=True, zerolinecolor="gray", zerolinewidth=1)
)

st.plotly_chart(fig3)

st.markdown("---")

# チーム別詳細
st.subheader("📋 チーム別シーズン成績")

# チーム選択（team_idと名前のマッピング）
teams_df = get_teams()
team_options = {latest_names.get(row["team_id"], f"Team {row['team_id']}"): row["team_id"] 
                for _, row in teams_df.iterrows()}

selected_team_name = st.selectbox("チームを選択", sorted(team_options.keys()))
selected_team_id = team_options[selected_team_name]

team_history = get_team_history(selected_team_id)

col1, col2, col3, col4 = st.columns(4)

with col1:
    total = team_history["points"].sum()
    st.metric("累積ポイント", f"{total:+.1f}")

with col2:
    avg = team_history["points"].mean()
    st.metric("平均ポイント", f"{avg:+.1f}")

with col3:
    best = team_history["rank"].min()
    st.metric("最高順位", f"{best}位")

with col4:
    wins = len(team_history[team_history["rank"] == 1])
    st.metric("優勝回数", f"{wins}回")

st.markdown("#### シーズン成績履歴")

history_display = team_history[["season", "team_name", "points", "rank"]].copy()
history_display.columns = ["シーズン", "チーム名", "ポイント", "順位"]
history_display["ポイント"] = history_display["ポイント"].apply(lambda x: f"{x:+.1f}")
history_display["順位"] = history_display["順位"].apply(lambda x: f"{x}位")

st.dataframe(history_display, hide_index=True)

st.markdown("---")

# 月別ランキング（全期間・年を考慮せず月のみ）
st.subheader("📅 月別ランキング（全期間）")
st.caption("※ 年に関係なく1月〜12月の月ごとに集計しています")

conn = get_connection()
cursor = conn.cursor()

# 半荘記録の存在確認
cursor.execute("SELECT COUNT(*) FROM game_results")
game_count = cursor.fetchone()[0]

if game_count > 0:
    # 半荘記録からチーム別月別成績を取得（年を考慮せず月のみ）
    query = """
        SELECT 
            CAST(strftime('%m', gr.game_date) AS INTEGER) as month,
            pt.team_id,
            tn.team_name,
            SUM(gr.points) as total_points,
            COUNT(*) as games,
            AVG(gr.rank) as avg_rank
        FROM game_results gr
        JOIN player_teams pt ON gr.player_id = pt.player_id AND gr.season = pt.season
        JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        GROUP BY month, pt.team_id, tn.team_name
        ORDER BY month, total_points DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if not df.empty:
        months = sorted(df['month'].unique())
        month_names = ['1月', '2月', '3月', '4月', '5月', '6月', 
                      '7月', '8月', '9月', '10月', '11月', '12月']
        
        st.markdown("### 月別ランキング（累積ポイント順）")
        
        for month in months:
            with st.expander(f"📅 {month_names[month-1]}", expanded=False):
                month_df = df[df['month'] == month].copy()
                
                # 累積ポイント順に並べる
                month_df = month_df.sort_values('total_points', ascending=False)
                month_df.insert(0, '順位', range(1, len(month_df) + 1))
                
                # 表示用に整形
                display_df = month_df[[
                    '順位', 'team_name', 'total_points', 'games', 'avg_rank'
                ]].copy()
                
                display_df.columns = [
                    '順位', 'チーム名', '累積pt', '対局数', '平均順位'
                ]
                
                display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
                display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
                
                st.dataframe(display_df, width='stretch', hide_index=True, height=300)
    else:
        st.info("半荘記録がありません。")
else:
    st.info("半荘記録がありません。「🎮 半荘記録入力」ページで対局結果を記録してください。")
    conn.close()

st.markdown("---")

# 席順別統計
st.subheader("🧭 席順別統計（全期間）")

conn = get_connection()
cursor = conn.cursor()

# 半荘記録の存在確認
cursor.execute("SELECT COUNT(*) FROM game_results")
game_count = cursor.fetchone()[0]

if game_count > 0:
    # 席順別統計を取得（全期間）
    query = """
        SELECT 
            gr.seat_name,
            pt.team_id,
            tn.team_name,
            COUNT(*) as games,
            SUM(gr.points) as total_points,
            AVG(gr.points) as avg_points,
            AVG(gr.rank) as avg_rank,
            SUM(CASE WHEN gr.rank = 1 THEN 1 ELSE 0 END) as rank_1st,
            SUM(CASE WHEN gr.rank = 2 THEN 1 ELSE 0 END) as rank_2nd,
            SUM(CASE WHEN gr.rank = 3 THEN 1 ELSE 0 END) as rank_3rd,
            SUM(CASE WHEN gr.rank = 4 THEN 1 ELSE 0 END) as rank_4th
        FROM game_results gr
        JOIN player_teams pt ON gr.player_id = pt.player_id AND gr.season = pt.season
        JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        GROUP BY gr.seat_name, pt.team_id
        ORDER BY gr.seat_name, total_points DESC
    """
    
    seat_df = pd.read_sql_query(query, conn)
    
    if not seat_df.empty:
        # 最新のチーム名を取得
        latest_names_dict = cumulative_df.set_index("team_id")["team_name"].to_dict()
        seat_df['team_name'] = seat_df['team_id'].map(latest_names_dict)
        
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
                        '順位', 'team_name', 'games', 'total_points', 'avg_points',
                        'avg_rank', 'rank_1st', 'rank_2nd', 'rank_3rd', 'rank_4th', 'first_rate'
                    ]].copy()
                    
                    display_df.columns = [
                        '順位', 'チーム名', '対局数', '累積pt', '平均pt',
                        '平均順位', '1位', '2位', '3位', '4位', '1位率(%)'
                    ]
                    
                    display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
                    display_df['平均pt'] = display_df['平均pt'].apply(lambda x: f"{x:+.1f}")
                    display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
                    display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.1f}")
                    
                    st.dataframe(display_df, width='stretch', hide_index=True, height=300)
                else:
                    st.info(f"{seat}家のデータがありません")
    else:
        st.info("席順別データがありません。")
else:
    st.info("半荘記録がありません。")

conn.close()

st.markdown("---")

# 対局時間ランキング
st.subheader("⏱️ 対局時間ランキング（全期間）")

conn = get_connection()
cursor = conn.cursor()

# 対局時間データを取得（全期間）
query = """
    SELECT 
        pt.team_id,
        gr.game_date,
        gr.game_number,
        gr.start_time,
        gr.end_time
    FROM game_results gr
    JOIN player_teams pt ON gr.player_id = pt.player_id AND gr.season = pt.season
    WHERE gr.start_time IS NOT NULL AND gr.end_time IS NOT NULL
"""

time_df = pd.read_sql_query(query, conn)
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
        # チーム別の統計
        team_time_stats = time_df.groupby('team_id').agg({
            'duration': ['count', 'mean', 'min', 'max']
        }).reset_index()
        
        team_time_stats.columns = ['team_id', 'games', 'avg_duration', 'min_duration', 'max_duration']
        
        # 最新のチーム名を追加
        team_time_stats['team_name'] = team_time_stats['team_id'].map(latest_names_dict)
        
        # 平均時間でソート
        team_time_stats = team_time_stats.sort_values('avg_duration', ascending=True)
        team_time_stats.insert(0, '順位', range(1, len(team_time_stats) + 1))
        
        # 時間を時:分形式に変換
        def format_duration(minutes):
            hours = int(minutes // 60)
            mins = int(minutes % 60)
            return f"{hours}:{mins:02d}"
        
        # 表示用に整形
        display_df = team_time_stats[[
            '順位', 'team_name', 'games', 'avg_duration', 'min_duration', 'max_duration'
        ]].copy()
        
        display_df.columns = [
            '順位', 'チーム名', '対局数', '平均時間', '最短時間', '最長時間'
        ]
        
        display_df['平均時間'] = display_df['平均時間'].apply(format_duration)
        display_df['最短時間'] = display_df['最短時間'].apply(format_duration)
        display_df['最長時間'] = display_df['最長時間'].apply(format_duration)
        
        st.dataframe(display_df, width='stretch', hide_index=True)
        
        st.info("💡 対局時間は「開始時間」から「終了時間」までの所要時間です。時間が記録されている対局のみが対象となります。")
    else:
        st.info("有効な対局時間データがありません。")
else:
    st.info("対局時間データがありません。「🎮 半荘記録入力」ページで開始・終了時間を記録してください。")

st.markdown("---")
st.caption("※ データはサンプルです。実際のMリーグ公式記録とは異なる場合があります。")
