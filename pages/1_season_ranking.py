import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db import (
    get_team_colors,
    get_seasons,
    get_season_data,
    get_connection,
    hide_default_sidebar_navigation
)
sys.path.append("..")

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
filtered_df = get_season_data(
    selected_season).sort_values("points", ascending=True)

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

    rank_df = filtered_df.sort_values(
        "rank")[["rank", "team_name", "points"]].copy()
    rank_df.columns = ["順位", "チーム", "ポイント"]
    rank_df["ポイント"] = rank_df["ポイント"].apply(lambda x: f"{x:+.1f}")
    rank_df = rank_df.reset_index(drop=True)

    st.dataframe(rank_df, hide_index=True)

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
    # 半荘記録からチーム別月別成績を取得
    query = """
        SELECT 
            strftime('%Y-%m', gr.game_date) as month,
            pt.team_id,
            tn.team_name,
            SUM(gr.points) as total_points,
            COUNT(*) as games,
            AVG(gr.rank) as avg_rank
        FROM game_results gr
        JOIN player_teams pt ON gr.player_id = pt.player_id AND gr.season = pt.season
        JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        WHERE gr.season = ?
        GROUP BY month, pt.team_id, tn.team_name
        ORDER BY month, total_points DESC
    """

    df = pd.read_sql_query(query, conn, params=(selected_season,))
    conn.close()

    if not df.empty:
        months = sorted(df['month'].unique())

        # タブで累積ポイントと平均順位を分ける
        tab_cumulative, tab_avg_rank = st.tabs(["累積ポイント推移", "平均順位推移"])

        with tab_cumulative:
            st.markdown("### 📈 月別累積ポイント推移")

            # 折れ線グラフ作成
            fig1 = go.Figure()

            teams = df['team_name'].unique()

            for team_name in sorted(teams):
                team_data = df[df['team_name'] ==
                               team_name].sort_values('month')

                fig1.add_trace(go.Scatter(
                    x=team_data['month'],
                    y=team_data['total_points'],
                    mode='lines+markers',
                    name=team_name,
                    line=dict(width=2),
                    marker=dict(size=8),
                    hovertemplate=(
                        f'<b>{team_name}</b><br>' +
                        '月: %{x}<br>' +
                        '累積pt: %{y:+.1f}<br>' +
                        '<extra></extra>'
                    )
                ))

            fig1.update_layout(
                title=f"{selected_season}シーズン 月別累積ポイント推移",
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

            # 最新月のランキング
            st.markdown("#### 🏆 最新月のランキング")

            latest_month = months[-1]
            latest_month_df = df[df['month'] == latest_month].sort_values(
                'total_points', ascending=False)
            latest_month_df = latest_month_df.reset_index(drop=True)
            latest_month_df.insert(0, '順位', range(1, len(latest_month_df) + 1))

            display_latest = latest_month_df[[
                '順位', 'team_name', 'total_points', 'avg_rank', 'games']].copy()
            display_latest.columns = ['順位', 'チーム名', '累積pt', '平均順位', '対局数']
            display_latest['累積pt'] = display_latest['累積pt'].apply(
                lambda x: f"{x:+.1f}")
            display_latest['平均順位'] = display_latest['平均順位'].apply(
                lambda x: f"{x:.2f}")

            st.caption(f"**{latest_month}**")
            st.dataframe(display_latest, hide_index=True, width='stretch')

        with tab_avg_rank:
            st.markdown("### 📈 月別平均順位推移")

            # 折れ線グラフ作成
            fig2 = go.Figure()

            teams = df['team_name'].unique()

            for team_name in sorted(teams):
                team_data = df[df['team_name'] ==
                               team_name].sort_values('month')

                fig2.add_trace(go.Scatter(
                    x=team_data['month'],
                    y=team_data['avg_rank'],
                    mode='lines+markers',
                    name=team_name,
                    line=dict(width=2),
                    marker=dict(size=8),
                    hovertemplate=(
                        f'<b>{team_name}</b><br>' +
                        '月: %{x}<br>' +
                        '平均順位: %{y:.2f}<br>' +
                        '<extra></extra>'
                    )
                ))

            fig2.update_layout(
                title=f"{selected_season}シーズン 月別平均順位推移",
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
                    'ベスト月': best_month,
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
        WHERE gr.season = ?
        GROUP BY gr.seat_name, pt.team_id, tn.team_name
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
                    seat_data['first_rate'] = (
                        seat_data['rank_1st'] / seat_data['games'] * 100).round(1)

                    # 順位を追加
                    seat_data = seat_data.sort_values(
                        'total_points', ascending=False)
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

                    display_df['累積pt'] = display_df['累積pt'].apply(
                        lambda x: f"{x:+.1f}")
                    display_df['平均pt'] = display_df['平均pt'].apply(
                        lambda x: f"{x:+.1f}")
                    display_df['平均順位'] = display_df['平均順位'].apply(
                        lambda x: f"{x:.2f}")
                    display_df['1位率(%)'] = display_df['1位率(%)'].apply(
                        lambda x: f"{x:.1f}")

                    st.dataframe(display_df, width='stretch',
                                 hide_index=True, height=300)
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
        pt.team_id,
        tn.team_name,
        gr.game_date,
        gr.game_number,
        gr.start_time,
        gr.end_time
    FROM game_results gr
    JOIN player_teams pt ON gr.player_id = pt.player_id AND gr.season = pt.season
    JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
    WHERE gr.season = ? AND gr.start_time IS NOT NULL AND gr.end_time IS NOT NULL
"""

time_df = pd.read_sql_query(query, conn, params=(selected_season,))
conn.close()

if not time_df.empty:
    # 対局時間（分）を計算
    def calc_duration(game_row):
        try:
            start_parts = game_row['start_time'].split(':')
            end_parts = game_row['end_time'].split(':')
            start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
            duration = end_minutes - start_minutes
            if duration < 0:
                duration += 24 * 60  # 日付をまたぐ場合
            return duration
        except (ValueError, IndexError, AttributeError):
            return None

    time_df['duration'] = time_df.apply(calc_duration, axis=1)
    time_df = time_df[time_df['duration'].notna()]

    if not time_df.empty:
        # チーム別の統計
        team_time_stats = time_df.groupby(['team_id', 'team_name']).agg({
            'duration': ['count', 'mean', 'min', 'max']
        }).reset_index()

        team_time_stats.columns = [
            'team_id', 'team_name', 'games', 'avg_duration', 'min_duration', 'max_duration']

        # 平均時間でソート
        team_time_stats = team_time_stats.sort_values(
            'avg_duration', ascending=True)
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
        st.info(f"{selected_season}シーズンの有効な対局時間データがありません。")
else:
    st.info(f"{selected_season}シーズンの対局時間データがありません。「🎮 半荘記録入力」ページで開始・終了時間を記録してください。")

st.markdown("---")
st.caption("※ データはサンプルです。実際のMリーグ公式記録とは異なる場合があります。")
