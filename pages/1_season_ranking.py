import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
sys.path.append("..")
from db import get_team_colors, get_season_points, get_seasons, get_season_data, hide_default_sidebar_navigation

st.set_page_config(
    page_title="年度別ランキング | Mリーグダッシュボード",
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



st.title("📊 年度別ポイントランキング")

# データ読み込み
team_colors = get_team_colors()
seasons = get_seasons()

if not seasons:
    st.warning("シーズンデータがありません")
    st.stop()

# シーズン選択
selected_season = st.selectbox("シーズンを選択", seasons)

# 選択シーズンのデータ
filtered_df = get_season_data(selected_season).sort_values("points", ascending=True)

st.markdown(f"## {selected_season}シーズン 結果")

col1, col2 = st.columns([2, 1])

with col1:
    # 横棒グラフ
    fig = go.Figure()
    
    for _, row in filtered_df.iterrows():
        color = team_colors.get(row["team_id"], "#888888")
        fig.add_trace(go.Bar(
            y=[row["team_name"]],
            x=[row["points"]],
            orientation="h",
            marker_color=color,
            name=row["team_name"],
            text=f"{row['points']:+.1f}",
            textposition="outside",
            showlegend=False
        ))
    
    fig.update_layout(
        title=f"{selected_season}シーズン チーム別ポイント",
        xaxis_title="ポイント",
        yaxis_title="",
        height=400,
        margin=dict(l=20, r=100, t=50, b=50),
        xaxis=dict(zeroline=True, zerolinecolor="gray", zerolinewidth=2)
    )
    
    st.plotly_chart(fig)

with col2:
    # 順位表
    st.markdown("### 順位表")
    
    rank_df = filtered_df.sort_values("rank")[["rank", "team_name", "points"]].copy()
    rank_df.columns = ["順位", "チーム", "ポイント"]
    rank_df["ポイント"] = rank_df["ポイント"].apply(lambda x: f"{x:+.1f}")
    rank_df = rank_df.reset_index(drop=True)
    
    st.dataframe(rank_df, hide_index=True)

st.markdown("---")

# 全シーズン推移グラフ
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
st.caption("※ データはサンプルです。実際のMリーグ公式記録とは異なる場合があります。")
