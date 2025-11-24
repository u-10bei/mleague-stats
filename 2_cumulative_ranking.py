import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="累積ランキング | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide"
)

st.title("🏆 累積ポイントランキング")

# データ読み込み
season_df = pd.read_csv("data/team_season_points.csv")
teams_df = pd.read_csv("data/teams.csv")

# チームカラーのマッピング
team_colors = dict(zip(teams_df["team_name"], teams_df["color"]))

# 累積ポイント計算
cumulative_df = season_df.groupby("team")["points"].sum().reset_index()
cumulative_df.columns = ["team", "total_points"]
cumulative_df = cumulative_df.sort_values("total_points", ascending=False).reset_index(drop=True)
cumulative_df["rank"] = range(1, len(cumulative_df) + 1)

# 参加シーズン数
season_count = season_df.groupby("team")["season"].count().reset_index()
season_count.columns = ["team", "seasons"]
cumulative_df = cumulative_df.merge(season_count, on="team")

# 平均ポイント
cumulative_df["avg_points"] = cumulative_df["total_points"] / cumulative_df["seasons"]

st.markdown("## 全シーズン通算成績")

col1, col2 = st.columns([2, 1])

with col1:
    # 累積ポイント棒グラフ
    fig = go.Figure()
    
    for _, row in cumulative_df.sort_values("total_points", ascending=True).iterrows():
        color = team_colors.get(row["team"], "#888888")
        fig.add_trace(go.Bar(
            y=[row["team"]],
            x=[row["total_points"]],
            orientation="h",
            marker_color=color,
            name=row["team"],
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
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # 順位表
    st.markdown("### 通算順位表")
    
    display_df = cumulative_df[["rank", "team", "total_points", "seasons", "avg_points"]].copy()
    display_df.columns = ["順位", "チーム", "累積pt", "参加", "平均pt"]
    display_df["累積pt"] = display_df["累積pt"].apply(lambda x: f"{x:+.1f}")
    display_df["平均pt"] = display_df["平均pt"].apply(lambda x: f"{x:+.1f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.markdown("---")

# 累積ポイント推移
st.subheader("📈 累積ポイント推移")

# シーズンごとの累積を計算
seasons = sorted(season_df["season"].unique())
teams = season_df["team"].unique()

cumulative_by_season = []
for team in teams:
    team_data = season_df[season_df["team"] == team].sort_values("season")
    cum_points = 0
    for _, row in team_data.iterrows():
        cum_points += row["points"]
        cumulative_by_season.append({
            "team": team,
            "season": row["season"],
            "cumulative_points": cum_points
        })

cum_df = pd.DataFrame(cumulative_by_season)

fig2 = go.Figure()

for team in teams:
    team_data = cum_df[cum_df["team"] == team]
    color = team_colors.get(team, "#888888")
    fig2.add_trace(go.Scatter(
        x=team_data["season"],
        y=team_data["cumulative_points"],
        mode="lines+markers",
        name=team,
        line=dict(color=color, width=2),
        marker=dict(size=8)
    ))

fig2.update_layout(
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

st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# チーム別詳細
st.subheader("📋 チーム別シーズン成績")

selected_team = st.selectbox("チームを選択", sorted(teams))

team_history = season_df[season_df["team"] == selected_team].sort_values("season", ascending=False)
team_info = teams_df[teams_df["team_name"] == selected_team].iloc[0]

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

history_display = team_history[["season", "points", "rank"]].copy()
history_display.columns = ["シーズン", "ポイント", "順位"]
history_display["ポイント"] = history_display["ポイント"].apply(lambda x: f"{x:+.1f}")
history_display["順位"] = history_display["順位"].apply(lambda x: f"{x}位")

st.dataframe(history_display, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("※ データはサンプルです。実際のMリーグ公式記録とは異なる場合があります。")
