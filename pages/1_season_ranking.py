import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="年度別ランキング | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide"
)

# サイドバーナビゲーション
st.sidebar.title("🀄 メニュー")
st.sidebar.page_link("app.py", label="🏠 トップページ")
st.sidebar.page_link("pages/1_season_ranking.py", label="📊 年度別ランキング")
st.sidebar.page_link("pages/2_cumulative_ranking.py", label="🏆 累積ランキング")
st.sidebar.markdown("---")

st.title("📊 年度別ポイントランキング")

# データ読み込み
season_df = pd.read_csv("data/team_season_points.csv")
teams_df = pd.read_csv("data/teams.csv")

# チームカラーのマッピング
team_colors = dict(zip(teams_df["team_name"], teams_df["color"]))

# シーズン選択
seasons = sorted(season_df["season"].unique(), reverse=True)
selected_season = st.selectbox("シーズンを選択", seasons)

# 選択シーズンのデータ
filtered_df = season_df[season_df["season"] == selected_season].sort_values("points", ascending=True)

st.markdown(f"## {selected_season}シーズン 結果")

col1, col2 = st.columns([2, 1])

with col1:
    # 横棒グラフ
    fig = go.Figure()
    
    for _, row in filtered_df.iterrows():
        color = team_colors.get(row["team"], "#888888")
        fig.add_trace(go.Bar(
            y=[row["team"]],
            x=[row["points"]],
            orientation="h",
            marker_color=color,
            name=row["team"],
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
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # 順位表
    st.markdown("### 順位表")
    
    rank_df = filtered_df.sort_values("rank")[["rank", "team", "points"]].copy()
    rank_df.columns = ["順位", "チーム", "ポイント"]
    rank_df["ポイント"] = rank_df["ポイント"].apply(lambda x: f"{x:+.1f}")
    rank_df = rank_df.reset_index(drop=True)
    
    st.dataframe(rank_df, use_container_width=True, hide_index=True)

st.markdown("---")

# 全シーズン推移グラフ
st.subheader("📈 全シーズン順位推移")

# 順位推移のピボットテーブル
rank_pivot = season_df.pivot(index="season", columns="team", values="rank")

fig2 = go.Figure()

for team in rank_pivot.columns:
    color = team_colors.get(team, "#888888")
    fig2.add_trace(go.Scatter(
        x=rank_pivot.index,
        y=rank_pivot[team],
        mode="lines+markers",
        name=team,
        line=dict(color=color, width=2),
        marker=dict(size=8)
    ))

fig2.update_layout(
    title="チーム別順位推移",
    xaxis_title="シーズン",
    yaxis_title="順位",
    yaxis=dict(autorange="reversed", dtick=1),  # 1位が上
    height=500,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.3,
        xanchor="center",
        x=0.5
    )
)

st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.caption("※ データはサンプルです。実際のMリーグ公式記録とは異なる場合があります。")
