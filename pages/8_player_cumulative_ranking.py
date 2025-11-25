import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
sys.path.append("..")
from db import get_player_cumulative_stats, get_player_history, get_players, get_player_all_stats, hide_default_sidebar_navigation

st.set_page_config(
    page_title="累積選手ランキング | Mリーグダッシュボード",
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
st.sidebar.markdown("---")
st.sidebar.page_link("pages/3_admin.py", label="⚙️ データ管理")
st.sidebar.page_link("pages/4_player_admin.py", label="👤 選手管理")
st.sidebar.page_link("pages/5_season_update.py", label="🔄 シーズン更新")
st.sidebar.page_link("pages/6_player_stats_input.py", label="📊 選手成績入力")

st.title("🏆 累積選手ランキング")

# データ読み込み
cumulative_df = get_player_cumulative_stats()

if cumulative_df.empty:
    st.warning("選手成績データがありません。「選手成績入力」ページで成績を登録してください。")
    st.stop()

st.markdown("## 全シーズン通算成績")

col1, col2 = st.columns([2, 1])

with col1:
    # 累積ポイント棒グラフ（上位20名）
    fig = go.Figure()
    
    display_df = cumulative_df.head(20).sort_values("total_points", ascending=True)
    
    for _, row in display_df.iterrows():
        fig.add_trace(go.Bar(
            y=[row["player_name"]],
            x=[row["total_points"]],
            orientation="h",
            marker_color="#4A90E2",
            name=row["player_name"],
            text=f"{row['total_points']:+.1f}",
            textposition="outside",
            showlegend=False,
            hovertemplate=f"<b>{row['player_name']}</b><br>" +
                         f"{row['team_name']}<br>" +
                         f"累積pt: {row['total_points']:+.1f}<br>" +
                         f"参加: {int(row['seasons'])}シーズン<br>" +
                         f"平均pt: {row['avg_points']:+.1f}<br>" +
                         "<extra></extra>"
        ))
    
    fig.update_layout(
        title="選手別 累積ポイント（上位20名）",
        xaxis_title="累積ポイント",
        yaxis_title="",
        height=600,
        margin=dict(l=150, r=100, t=50, b=50),
        xaxis=dict(zeroline=True, zerolinecolor="gray", zerolinewidth=2)
    )
    
    st.plotly_chart(fig, width="stretch")

with col2:
    # 通算順位表（上位10名）
    st.markdown("### 🏆 通算順位 TOP10")
    
    display_df = cumulative_df.head(10)[["rank", "player_name", "team_name", "total_points", 
                                          "seasons", "avg_points"]].copy()
    display_df.columns = ["順位", "選手名", "所属", "累積pt", "参加", "平均pt"]
    display_df["累積pt"] = display_df["累積pt"].apply(lambda x: f"{x:+.1f}")
    display_df["平均pt"] = display_df["平均pt"].apply(lambda x: f"{x:+.1f}")
    
    st.dataframe(display_df, hide_index=True, height=400)
    
    # 統計情報
    st.markdown("### 📈 統計情報")
    st.metric("登録選手数", f"{len(cumulative_df)}名")
    st.metric("総試合数", f"{int(cumulative_df['total_games'].sum())}試合")
    st.metric("平均参加", f"{cumulative_df['seasons'].mean():.1f}シーズン")

st.markdown("---")

# 累積ポイント推移
st.subheader("📈 累積ポイント推移")

all_stats = get_player_all_stats()

if not all_stats.empty:
    # 上位10名の選手を取得
    top_players = cumulative_df.head(10)['player_id'].tolist()
    
    # 累積ポイントを計算
    cumulative_by_season = []
    for player_id in top_players:
        player_data = all_stats[all_stats['player_id'] == player_id].sort_values('season')
        if not player_data.empty:
            player_name = player_data.iloc[0]['player_name']
            cum_points = 0
            for _, row in player_data.iterrows():
                cum_points += row['points']
                cumulative_by_season.append({
                    'player_id': player_id,
                    'player_name': player_name,
                    'season': row['season'],
                    'cumulative_points': cum_points
                })
    
    cum_df = pd.DataFrame(cumulative_by_season)
    
    fig2 = go.Figure()
    
    for player_id in top_players:
        player_data = cum_df[cum_df['player_id'] == player_id]
        if not player_data.empty:
            player_name = player_data.iloc[0]['player_name']
            fig2.add_trace(go.Scatter(
                x=player_data['season'],
                y=player_data['cumulative_points'],
                mode='lines+markers',
                name=player_name,
                line=dict(width=2),
                marker=dict(size=8)
            ))
    
    fig2.update_layout(
        title="選手別 累積ポイント推移（上位10名）",
        xaxis_title="シーズン",
        yaxis_title="累積ポイント",
        height=500,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        ),
        yaxis=dict(zeroline=True, zerolinecolor="gray", zerolinewidth=1)
    )
    
    st.plotly_chart(fig2, width="stretch")

st.markdown("---")

# 全選手ランキング表
st.subheader("📋 全選手通算ランキング")

# フィルター
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    min_seasons = st.number_input("最低参加シーズン", min_value=0, value=0, step=1)

with col2:
    min_games = st.number_input("最低試合数", min_value=0, value=0, step=1)

with col3:
    search_name = st.text_input("選手名で検索", placeholder="例: 園田")

# フィルター適用
filtered_df = cumulative_df.copy()
if min_seasons > 0:
    filtered_df = filtered_df[filtered_df['seasons'] >= min_seasons]
if min_games > 0:
    filtered_df = filtered_df[filtered_df['total_games'] >= min_games]
if search_name:
    filtered_df = filtered_df[filtered_df['player_name'].str.contains(search_name, na=False)]

# 詳細データ表示
detail_df = filtered_df[["rank", "player_name", "team_name", "total_games", "total_points", 
                         "total_1st", "total_2nd", "total_3rd", "total_4th", 
                         "seasons", "avg_points"]].copy()
detail_df.columns = ["順位", "選手名", "所属", "試合数", "累積pt", "1位", "2位", "3位", "4位", "参加", "平均pt"]
detail_df["累積pt"] = detail_df["累積pt"].apply(lambda x: f"{x:+.1f}")
detail_df["平均pt"] = detail_df["平均pt"].apply(lambda x: f"{x:+.1f}")

# 平均順位を計算
filtered_df['avg_rank'] = (
    filtered_df['total_1st'] * 1 + 
    filtered_df['total_2nd'] * 2 + 
    filtered_df['total_3rd'] * 3 + 
    filtered_df['total_4th'] * 4
) / filtered_df['total_games']
detail_df["平均順位"] = filtered_df['avg_rank'].apply(lambda x: f"{x:.2f}")

st.dataframe(
    detail_df,
    hide_index=True,
    column_config={
        "順位": st.column_config.NumberColumn(width="small"),
        "選手名": st.column_config.TextColumn(width="medium"),
        "所属": st.column_config.TextColumn(width="medium"),
        "試合数": st.column_config.NumberColumn(width="small"),
        "累積pt": st.column_config.TextColumn(width="small"),
        "1位": st.column_config.NumberColumn(width="small"),
        "2位": st.column_config.NumberColumn(width="small"),
        "3位": st.column_config.NumberColumn(width="small"),
        "4位": st.column_config.NumberColumn(width="small"),
        "参加": st.column_config.NumberColumn(width="small"),
        "平均pt": st.column_config.TextColumn(width="small"),
        "平均順位": st.column_config.TextColumn(width="small"),
    }
)

st.markdown(f"**表示件数: {len(filtered_df)}名**")

st.markdown("---")

# 選手別詳細
st.subheader("📋 選手別シーズン成績")

# 選手選択
players_df = get_players()
player_options = {row["player_name"]: row["player_id"] for _, row in players_df.iterrows()}

selected_player_name = st.selectbox("選手を選択", sorted(player_options.keys()))
selected_player_id = player_options[selected_player_name]

player_history = get_player_history(selected_player_id)

if not player_history.empty:
    # 選手の統計情報
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = player_history["points"].sum()
        st.metric("累積ポイント", f"{total:+.1f}")
    
    with col2:
        avg = player_history["points"].mean()
        st.metric("平均ポイント", f"{avg:+.1f}")
    
    with col3:
        total_games = player_history["games"].sum()
        st.metric("通算試合数", f"{int(total_games)}試合")
    
    with col4:
        seasons_count = len(player_history)
        st.metric("参加シーズン", f"{seasons_count}年")
    
    st.markdown("#### シーズン成績履歴")
    
    history_display = player_history[["season", "team_name", "games", "points", 
                                       "rank_1st", "rank_2nd", "rank_3rd", "rank_4th"]].copy()
    history_display.columns = ["シーズン", "所属チーム", "試合数", "ポイント", "1位", "2位", "3位", "4位"]
    history_display["ポイント"] = history_display["ポイント"].apply(lambda x: f"{x:+.1f}")
    
    # 平均順位を計算
    player_history['avg_rank'] = (
        player_history['rank_1st'] * 1 + 
        player_history['rank_2nd'] * 2 + 
        player_history['rank_3rd'] * 3 + 
        player_history['rank_4th'] * 4
    ) / player_history['games']
    history_display["平均順位"] = player_history['avg_rank'].apply(lambda x: f"{x:.2f}")
    
    st.dataframe(history_display, hide_index=True)
else:
    st.info(f"{selected_player_name} の成績データがありません。")

st.markdown("---")
st.caption("※ データはデータベースに登録された情報を表示しています。")
