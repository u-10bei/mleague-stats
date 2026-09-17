import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db import (
    get_player_cumulative_stats,
    get_player_history,
    get_players,
    get_player_all_stats,
    get_connection,
    show_sidebar_navigation
)
from ui import fit_chart, metric_row
sys.path.append("..")

st.set_page_config(
    page_title="累積選手ランキング | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide"
)


# サイドバーナビゲーション
show_sidebar_navigation()

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

    display_df = cumulative_df.head(20).sort_values(
        "total_points", ascending=True)

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
        xaxis=dict(zeroline=True, zerolinecolor="gray", zerolinewidth=2)
    )

    fit_chart(fig, horizontal=True)
    st.plotly_chart(fig, width='stretch')

with col2:
    # 通算順位表（上位10名）
    st.markdown("### 🏆 通算順位 TOP10")

    # 幅の広い「所属」は右端へ。狭い画面でも、最初に見えるところに
    # 順位・選手名・累積pt が入るようにする。
    display_df = cumulative_df.head(10)[["rank", "player_name", "total_points",
                                         "avg_points", "seasons",
                                         "team_name"]].copy()
    display_df.columns = ["順位", "選手名", "累積pt", "平均pt", "参加", "所属"]
    display_df["累積pt"] = display_df["累積pt"].apply(lambda x: f"{x:+.1f}")
    display_df["平均pt"] = display_df["平均pt"].apply(lambda x: f"{x:+.1f}")

    st.dataframe(display_df, hide_index=True, height=400)

    # 統計情報
    st.markdown("### 📈 統計情報")
    st.metric("登録選手数", f"{len(cumulative_df)}名")
    st.metric("総試合数", f"{int(cumulative_df['total_games'].sum())}試合")
    st.metric("平均参加", f"{cumulative_df['seasons'].mean():.1f}シーズン")

st.markdown("---")

# 全シーズン順位推移グラフ（ポイント順位）
st.subheader("📈 全シーズン順位推移（ポイント順位）")

all_stats = get_player_all_stats()

if not all_stats.empty:
    # 各シーズンでの順位を計算
    all_stats['season_rank'] = all_stats.groupby(
        'season')['points'].rank(ascending=False, method='min')

    # 上位10名の選手を取得（累積ポイントから）
    top_players = cumulative_df.head(10)['player_id'].tolist()

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
        title="選手別順位推移（累積上位10名）",
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

    fit_chart(fig2)
    st.plotly_chart(fig2, width='stretch')

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
        player_data = all_stats[all_stats['player_id']
                                == player_id].sort_values('season')
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

    fig3 = go.Figure()

    for player_id in top_players:
        player_data = cum_df[cum_df['player_id'] == player_id]
        if not player_data.empty:
            player_name = player_data.iloc[0]['player_name']
            fig3.add_trace(go.Scatter(
                x=player_data['season'],
                y=player_data['cumulative_points'],
                mode='lines+markers',
                name=player_name,
                line=dict(width=2),
                marker=dict(size=8)
            ))

    fig3.update_layout(
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

    fit_chart(fig3)
    st.plotly_chart(fig3, width='stretch')

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
    filtered_df = filtered_df[filtered_df['player_name'].str.contains(
        search_name, na=False)]

# 詳細データ表示
# 「所属」は幅を食うわりに読む頻度が低いので右端に回す。
detail_df = filtered_df[["rank", "player_name", "total_points", "avg_points",
                         "total_games", "total_1st", "total_2nd", "total_3rd",
                         "total_4th", "seasons", "team_name"]].copy()
detail_df.columns = ["順位", "選手名", "累積pt", "平均pt", "試合数",
                     "1位", "2位", "3位", "4位", "参加", "所属"]
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
# 末尾に足した平均順位を、所属より前に戻す
detail_df = detail_df[["順位", "選手名", "累積pt", "平均pt", "平均順位", "試合数",
                       "1位", "2位", "3位", "4位", "参加", "所属"]]

st.dataframe(
    detail_df,
    hide_index=True,
    column_config={
        "順位": st.column_config.NumberColumn(width=56),
        # 選手名は固定。横スクロールしても誰の行かを見失わない。
        "選手名": st.column_config.TextColumn(width=104, pinned=True),
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
player_options = {row["player_name"]: row["player_id"]
                  for _, row in players_df.iterrows()}

selected_player_name = st.selectbox("選手を選択", sorted(player_options.keys()))
selected_player_id = player_options[selected_player_name]

player_history = get_player_history(selected_player_id)

if not player_history.empty:
    # 選手の統計情報
    col1, col2, col3, col4 = metric_row(4)

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

    # 「所属チーム」は右端へ回して、シーズンとポイントを先に見せる
    history_display = player_history[["season", "points", "games",
                                      "rank_1st", "rank_2nd", "rank_3rd",
                                      "rank_4th", "team_name"]].copy()
    history_display.columns = ["シーズン", "ポイント", "試合数",
                               "1位", "2位", "3位", "4位", "所属チーム"]
    history_display["ポイント"] = history_display["ポイント"].apply(
        lambda x: f"{x:+.1f}")

    # 平均順位を計算
    player_history['avg_rank'] = (
        player_history['rank_1st'] * 1 +
        player_history['rank_2nd'] * 2 +
        player_history['rank_3rd'] * 3 +
        player_history['rank_4th'] * 4
    ) / player_history['games']
    history_display["平均順位"] = player_history['avg_rank'].apply(
        lambda x: f"{x:.2f}")
    # 末尾に足した平均順位を、所属チームより前に戻す
    history_display = history_display[
        ["シーズン", "ポイント", "平均順位", "試合数",
         "1位", "2位", "3位", "4位", "所属チーム"]]

    st.dataframe(history_display, hide_index=True)
else:
    st.info(f"{selected_player_name} の成績データがありません。")

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
    # 半荘記録から選手別月別成績を取得（年を考慮せず月のみ）
    query = """
        SELECT 
            CAST(strftime('%m', gr.game_date) AS INTEGER) as month,
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
        GROUP BY month, gr.player_id, p.player_name
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
                month_df = month_df.sort_values(
                    'total_points', ascending=False)
                month_df.insert(0, '順位', range(1, len(month_df) + 1))

                # 1位率を計算
                month_df['first_rate'] = (
                    month_df['rank_1st'] / month_df['games'] * 100).round(1)

                # 表示用に整形
                display_df = month_df[[
                    '順位', 'player_name', 'total_points', 'games', 'avg_rank',
                    'rank_1st', 'rank_2nd', 'rank_3rd', 'rank_4th', 'first_rate'
                ]].copy()

                display_df.columns = [
                    '順位', '選手名', '累積pt', '対局数', '平均順位',
                    '1位', '2位', '3位', '4位', '1位率(%)'
                ]

                display_df['累積pt'] = display_df['累積pt'].apply(
                    lambda x: f"{x:+.1f}")
                display_df['平均順位'] = display_df['平均順位'].apply(
                    lambda x: f"{x:.2f}")
                display_df['1位率(%)'] = display_df['1位率(%)'].apply(
                    lambda x: f"{x:.1f}")

                st.dataframe(display_df, hide_index=True, height=400)
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
        GROUP BY gr.seat_name, gr.player_id, p.player_name
        ORDER BY gr.seat_name, total_points DESC
    """

    seat_df = pd.read_sql_query(query, conn)

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
                        '順位', 'player_name', 'games', 'total_points', 'avg_points',
                        'avg_rank', 'rank_1st', 'rank_2nd', 'rank_3rd', 'rank_4th', 'first_rate'
                    ]].copy()

                    display_df.columns = [
                        '順位', '選手名', '対局数', '累積pt', '平均pt',
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
                                 hide_index=True, height=400)
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
        gr.player_id,
        p.player_name,
        gr.game_date,
        gr.game_number,
        gr.start_time,
        gr.end_time
    FROM game_results gr
    JOIN players p ON gr.player_id = p.player_id
    WHERE gr.start_time IS NOT NULL AND gr.end_time IS NOT NULL
"""

time_df = pd.read_sql_query(query, conn)
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
        except (ValueError, IndexError, TypeError):
            return None

    time_df['duration'] = time_df.apply(calc_duration, axis=1)
    time_df = time_df[time_df['duration'].notna()]

    if not time_df.empty:
        # 選手別の統計
        player_time_stats = time_df.groupby(['player_id', 'player_name']).agg({
            'duration': ['count', 'mean', 'min', 'max']
        }).reset_index()

        player_time_stats.columns = [
            'player_id', 'player_name', 'games', 'avg_duration', 'min_duration', 'max_duration']

        # 平均時間でソート
        player_time_stats = player_time_stats.sort_values(
            'avg_duration', ascending=True)
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
        st.info("有効な対局時間データがありません。")
else:
    st.info("対局時間データがありません。「🎮 半荘記録入力」ページで開始・終了時間を記録してください。")

st.markdown("---")
st.caption("※ データはデータベースに登録された情報を表示しています。")
