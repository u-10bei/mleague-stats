import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
sys.path.append("..")
from db import get_team_colors, get_season_points, get_cumulative_points, get_team_history, get_teams

st.set_page_config(
    page_title="累積ランキング | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide"
)

# サイドバーナビゲーション
st.sidebar.title("🀄 メニュー")
st.sidebar.page_link("app.py", label="🏠 トップページ")
st.sidebar.page_link("pages/1_season_ranking.py", label="📊 年度別ランキング")
st.sidebar.page_link("pages/2_cumulative_ranking.py", label="🏆 累積ランキング")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/3_admin.py", label="⚙️ データ管理")

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
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # 順位表
    st.markdown("### 通算順位表")
    
    display_df = cumulative_df[["rank", "team_name", "total_points", "seasons", "avg_points"]].copy()
    display_df.columns = ["順位", "チーム", "累積pt", "参加", "平均pt"]
    display_df["累積pt"] = display_df["累積pt"].apply(lambda x: f"{x:+.1f}")
    display_df["平均pt"] = display_df["平均pt"].apply(lambda x: f"{x:+.1f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

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

fig2 = go.Figure()

for team_id in team_ids:
    team_data = cum_df[cum_df["team_id"] == team_id]
    color = team_colors.get(team_id, "#888888")
    team_name = latest_names.get(team_id, f"Team {team_id}")
    fig2.add_trace(go.Scatter(
        x=team_data["season"],
        y=team_data["cumulative_points"],
        mode="lines+markers",
        name=team_name,
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

st.dataframe(history_display, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("※ データはサンプルです。実際のMリーグ公式記録とは異なる場合があります。")
