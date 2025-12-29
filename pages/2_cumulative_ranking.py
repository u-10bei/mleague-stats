import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db import (
    get_team_colors,
    get_season_points,
    get_cumulative_points,
    get_team_history,
    get_teams,
    get_connection,
    hide_default_sidebar_navigation
)
sys.path.append("..")

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
st.sidebar.page_link("pages/16_streak_records.py", label="🔥 連続記録")
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

    display_df = cumulative_df[["rank", "team_name",
                                "total_points", "seasons", "avg_points"]].copy()
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
latest_names = season_df[season_df["season"] == season_df["season"].max(
)].set_index("team_id")["team_name"].to_dict()

for team_id in rank_pivot.columns:
    color = team_colors.get(team_id, "#888888")
    team_name = latest_names.get(team_id, f"Team {team_id}")
    fig2.add_trace(go.Scatter(
        x=rank_pivot.index,
        y=rank_pivot[team_id],
        mode="lines+markers",
        name=team_name,
        line=dict(color=color, width=2),
        marker=dict(size=8, color=color)
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
    team_data = season_df[season_df["team_id"]
                          == team_id].sort_values("season")
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
        marker=dict(size=8, color=color)
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

history_display = team_history[[
    "season", "team_name", "points", "rank"]].copy()
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

        # タブで累積ポイントと平均順位を分ける
        tab_cumulative, tab_avg_rank = st.tabs(["累積ポイント推移", "平均順位推移"])

        with tab_cumulative:
            st.markdown("### 📈 月別累積ポイント推移")

            # 折れ線グラフ作成
            fig1 = go.Figure()

            teams = df['team_name'].unique()

            # チーム名からteam_idへのマッピングを作成
            team_name_to_id = df.drop_duplicates('team_name').set_index('team_name')[
                'team_id'].to_dict()

            for team_name in sorted(teams):
                team_data = df[df['team_name'] ==
                               team_name].sort_values('month')
                team_id = team_name_to_id.get(team_name)
                color = team_colors.get(team_id, "#888888")

                # 月名を使用
                x_labels = [month_names[m-1] for m in team_data['month']]

                fig1.add_trace(go.Scatter(
                    x=x_labels,
                    y=team_data['total_points'],
                    mode='lines+markers',
                    name=team_name,
                    line=dict(color=color, width=2),
                    marker=dict(size=8, color=color),
                    hovertemplate=(
                        f'<b>{team_name}</b><br>' +
                        '月: %{x}<br>' +
                        '累積pt: %{y:+.1f}<br>' +
                        '<extra></extra>'
                    )
                ))

            fig1.update_layout(
                title="チーム別 月別累積ポイント推移（全期間）",
                xaxis_title="月",
                yaxis_title="累積ポイント",
                height=500,
                hovermode='x unified',
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                ),
                yaxis=dict(zeroline=True, zerolinecolor="gray",
                           zerolinewidth=1)
            )

            st.plotly_chart(fig1, width='stretch')

            # 統計サマリー
            st.markdown("#### 📊 統計情報")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("対象月数", f"{len(months)}ヶ月")

            with col2:
                total_games = df['games'].sum()
                st.metric("総対局数", f"{int(total_games)}対局")

            with col3:
                avg_games_per_month = total_games / \
                    len(months) if len(months) > 0 else 0
                st.metric("月平均対局数", f"{avg_games_per_month:.1f}対局")

            # 最もデータが多い月のランキング
            st.markdown("#### 🏆 対局数最多月のランキング")

            # 月ごとの対局数を計算
            month_games = df.groupby('month')['games'].sum().reset_index()
            most_games_month = month_games.loc[month_games['games'].idxmax(
            ), 'month']

            most_games_month_df = df[df['month'] == most_games_month].sort_values(
                'total_points', ascending=False)
            most_games_month_df = most_games_month_df.reset_index(drop=True)
            most_games_month_df.insert(
                0, '順位', range(1, len(most_games_month_df) + 1))

            display_most = most_games_month_df[[
                '順位', 'team_name', 'total_points', 'avg_rank', 'games']].copy()
            display_most.columns = ['順位', 'チーム名', '累積pt', '平均順位', '対局数']
            display_most['累積pt'] = display_most['累積pt'].apply(
                lambda x: f"{x:+.1f}")
            display_most['平均順位'] = display_most['平均順位'].apply(
                lambda x: f"{x:.2f}")

            st.caption(
                f"**{month_names[most_games_month-1]}** ({int(month_games[month_games['month']==most_games_month]['games'].values[0])}対局)")
            st.dataframe(display_most, hide_index=True, width='stretch')

        with tab_avg_rank:
            st.markdown("### 📈 月別平均順位推移")

            # 折れ線グラフ作成
            fig2 = go.Figure()

            teams = df['team_name'].unique()

            # チーム名からteam_idへのマッピングを作成
            team_name_to_id = df.drop_duplicates('team_name').set_index('team_name')[
                'team_id'].to_dict()

            for team_name in sorted(teams):
                team_data = df[df['team_name'] ==
                               team_name].sort_values('month')
                team_id = team_name_to_id.get(team_name)
                color = team_colors.get(team_id, "#888888")

                # 月名を使用
                x_labels = [month_names[m-1] for m in team_data['month']]

                fig2.add_trace(go.Scatter(
                    x=x_labels,
                    y=team_data['avg_rank'],
                    mode='lines+markers',
                    name=team_name,
                    line=dict(color=color, width=2),
                    marker=dict(size=8, color=color),
                    hovertemplate=(
                        f'<b>{team_name}</b><br>' +
                        '月: %{x}<br>' +
                        '平均順位: %{y:.2f}<br>' +
                        '<extra></extra>'
                    )
                ))

            fig2.update_layout(
                title="チーム別 月別平均順位推移（全期間）",
                xaxis_title="月",
                yaxis_title="平均順位",
                height=500,
                hovermode='x unified',
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                ),
                yaxis=dict(
                    autorange="reversed",  # 順位は小さいほうが良い
                    dtick=0.5,
                    zeroline=False
                )
            )

            st.plotly_chart(fig2, width='stretch')

            # 最良平均順位の月を表示
            st.markdown("#### 🏆 平均順位ベスト月")

            best_rank_data = []
            for team_name in teams:
                team_data = df[df['team_name'] == team_name]
                best_month_idx = team_data['avg_rank'].idxmin()
                best_month = team_data.loc[best_month_idx, 'month']
                best_rank = team_data.loc[best_month_idx, 'avg_rank']
                best_points = team_data.loc[best_month_idx, 'total_points']

                best_rank_data.append({
                    'チーム名': team_name,
                    'ベスト月': month_names[best_month-1],
                    '平均順位': best_rank,
                    '累積pt': best_points
                })

            best_rank_df = pd.DataFrame(best_rank_data).sort_values('平均順位')
            best_rank_df['平均順位'] = best_rank_df['平均順位'].apply(
                lambda x: f"{x:.2f}")
            best_rank_df['累積pt'] = best_rank_df['累積pt'].apply(
                lambda x: f"{x:+.1f}")

            st.dataframe(best_rank_df, hide_index=True, width='stretch')
    else:
        st.info("半荘記録がありません。")
else:
    st.info("半荘記録がありません。「🎮 半荘記録入力」ページで対局結果を記録してください。")
    conn.close()

st.markdown("---")
st.caption("※ データはサンプルです。実際のMリーグ公式記録とは異なる場合があります。")
