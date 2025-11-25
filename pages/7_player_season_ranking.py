import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
sys.path.append("..")
from db import get_player_seasons, get_player_season_ranking, get_player_all_stats

st.set_page_config(
    page_title="年度別選手ランキング | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide"
)

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

# 全シーズン順位推移グラフ
st.subheader("📈 全シーズン順位推移（ポイント順位）")

all_stats = get_player_all_stats()

if not all_stats.empty:
    # 各シーズンでの順位を計算
    all_stats['season_rank'] = all_stats.groupby('season')['points'].rank(ascending=False, method='min')
    
    # 上位10名の選手を取得（最新シーズンの順位から）
    latest_season = seasons[0]
    top_players = season_df.head(10)['player_id'].tolist()
    
    # グラフ作成
    fig2 = go.Figure()
    
    for player_id in top_players:
        player_data = all_stats[all_stats['player_id'] == player_id]
        if not player_data.empty:
            player_name = player_data.iloc[0]['player_name']
            fig2.add_trace(go.Scatter(
                x=player_data['season'],
                y=player_data['season_rank'],
                mode='lines+markers',
                name=player_name,
                line=dict(width=2),
                marker=dict(size=8)
            ))
    
    fig2.update_layout(
        title="選手別順位推移（現シーズン上位10名）",
        xaxis_title="シーズン",
        yaxis_title="順位",
        yaxis=dict(autorange="reversed", dtick=5),
        height=500,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    st.plotly_chart(fig2, width="stretch")

st.markdown("---")
st.caption("※ データはデータベースに登録された情報を表示しています。")
