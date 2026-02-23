import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db import get_connection, show_sidebar_navigation

st.set_page_config(
    page_title="チーム半荘別分析 | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide"
)

# サイドバーナビゲーション
show_sidebar_navigation()

st.title("🎲 チーム半荘別分析")

st.markdown("""
半荘記録から各チームの成績を詳細に分析します。
- 席順別ランキング（累積ポイント・平均順位）
- 試合番号別ランキング（累積ポイント・平均順位）
- 直対ランキング（対チーム別の成績）
""")

# ========== データ取得 ==========
conn = get_connection()
cursor = conn.cursor()

# 利用可能なシーズンを取得
cursor.execute("""
    SELECT DISTINCT season 
    FROM game_results 
    ORDER BY season DESC
""")
seasons = [row[0] for row in cursor.fetchall()]

if not seasons:
    st.warning("半荘記録データがありません。先に「🎮 半荘記録入力」でデータを登録してください。")
    conn.close()
    st.stop()

# ========== フィルター設定 ==========
st.markdown("---")
st.subheader("🔍 分析条件")

col1, col2 = st.columns(2)

with col1:
    period_options = ["全期間"] + seasons
    selected_period = st.selectbox("期間", period_options, key="period_select")

with col2:
    st.info(f"選択中: **{selected_period}**")

# ========== データ取得 ==========
if selected_period == "全期間":
    query = """
        SELECT 
            gr.season,
            gr.game_date,
            gr.game_number,
            gr.seat_name,
            gr.points,
            gr.rank,
            pt.team_id,
            tn.team_name
        FROM game_results gr
        JOIN player_teams pt ON gr.player_id = pt.player_id AND gr.season = pt.season
        JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        ORDER BY gr.season, gr.game_date, gr.game_number
    """
    cursor.execute(query)
else:
    query = """
        SELECT 
            gr.season,
            gr.game_date,
            gr.game_number,
            gr.seat_name,
            gr.points,
            gr.rank,
            pt.team_id,
            tn.team_name
        FROM game_results gr
        JOIN player_teams pt ON gr.player_id = pt.player_id AND gr.season = pt.season
        JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        WHERE gr.season = ?
        ORDER BY gr.game_date, gr.game_number
    """
    cursor.execute(query, (selected_period,))

results = cursor.fetchall()
conn.close()

if not results:
    st.warning("選択した期間に該当するデータがありません。")
    st.stop()

# DataFrameに変換
df = pd.DataFrame(results, columns=[
    'season', 'game_date', 'game_number', 'seat_name',
    'points', 'rank', 'team_id', 'team_name'
])

st.markdown("---")
st.info(f"📊 データ件数: {len(df)}対局 / {df['team_name'].nunique()}チーム")

# ========== タブ構成 ==========
tab1, tab2, tab3 = st.tabs(["🧭 席順別", "🎮 試合番号別", "⚔️ 直対"])

# ========== タブ1: 席順別ランキング ==========
with tab1:
    st.markdown("## 🧭 席順別ランキング")

    seats = ['東', '南', '西', '北']

    tab_seat_cumulative, tab_seat_avg_rank = st.tabs(
        ["累積ポイントランキング", "平均順位ランキング"])

    with tab_seat_cumulative:
        st.markdown("### 席順別 累積ポイントランキング")

        seat_tabs = st.tabs([f"{seat}家" for seat in seats])

        for seat_idx, seat in enumerate(seats):
            with seat_tabs[seat_idx]:
                seat_df = df[df['seat_name'] == seat]

                if len(seat_df) == 0:
                    st.info(f"{seat}家のデータがありません")
                    continue

                # チームごとの統計
                team_stats = seat_df.groupby(['team_id', 'team_name']).agg({
                    'points': ['sum', 'mean', 'count'],
                    'rank': 'mean'
                }).reset_index()

                team_stats.columns = [
                    'team_id', 'team_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']

                # 順位計算
                team_stats = team_stats.sort_values(
                    'cumulative_points', ascending=False)
                team_stats.insert(0, '順位', range(1, len(team_stats) + 1))

                # 1位〜4位の回数を計算
                rank_counts = seat_df.groupby(
                    'team_id')['rank'].value_counts().unstack(fill_value=0)
                for i in range(1, 5):
                    if i not in rank_counts.columns:
                        rank_counts[i] = 0
                rank_counts = rank_counts[[1, 2, 3, 4]]
                rank_counts.columns = ['1位', '2位', '3位', '4位']

                # マージ
                team_stats = team_stats.merge(
                    rank_counts,
                    left_on='team_id',
                    right_index=True,
                    how='left'
                ).fillna(0)

                # 1位率を計算
                team_stats['1位率'] = (team_stats['1位'] /
                                     team_stats['games'] * 100).round(1)

                # 表示用に整形
                display_df = team_stats[[
                    '順位', 'team_name', 'cumulative_points', 'avg_points',
                    'games', 'avg_rank', '1位', '2位', '3位', '4位', '1位率'
                ]].copy()

                display_df.columns = [
                    '順位', 'チーム名', '累積pt', '平均pt',
                    '対局数', '平均順位', '1位', '2位', '3位', '4位', '1位率(%)'
                ]

                # フォーマット
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

    with tab_seat_avg_rank:
        st.markdown("### 席順別 平均順位ランキング")

        seat_tabs = st.tabs([f"{seat}家" for seat in seats])

        for seat_idx, seat in enumerate(seats):
            with seat_tabs[seat_idx]:
                seat_df = df[df['seat_name'] == seat]

                if len(seat_df) == 0:
                    st.info(f"{seat}家のデータがありません")
                    continue

                # チームごとの統計
                team_stats = seat_df.groupby(['team_id', 'team_name']).agg({
                    'points': ['sum', 'mean', 'count'],
                    'rank': 'mean'
                }).reset_index()

                team_stats.columns = [
                    'team_id', 'team_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']

                # 順位計算（平均順位の低い順）
                team_stats = team_stats.sort_values('avg_rank', ascending=True)
                team_stats.insert(0, '順位', range(1, len(team_stats) + 1))

                # 1位〜4位の回数を計算
                rank_counts = seat_df.groupby(
                    'team_id')['rank'].value_counts().unstack(fill_value=0)
                for i in range(1, 5):
                    if i not in rank_counts.columns:
                        rank_counts[i] = 0
                rank_counts = rank_counts[[1, 2, 3, 4]]
                rank_counts.columns = ['1位', '2位', '3位', '4位']

                # マージ
                team_stats = team_stats.merge(
                    rank_counts,
                    left_on='team_id',
                    right_index=True,
                    how='left'
                ).fillna(0)

                # 1位率を計算
                team_stats['1位率'] = (team_stats['1位'] /
                                     team_stats['games'] * 100).round(1)

                # 表示用に整形
                display_df = team_stats[[
                    '順位', 'team_name', 'avg_rank', 'games',
                    'cumulative_points', '1位', '2位', '3位', '4位', '1位率'
                ]].copy()

                display_df.columns = [
                    '順位', 'チーム名', '平均順位', '対局数',
                    '累積pt', '1位', '2位', '3位', '4位', '1位率(%)'
                ]

                # フォーマット
                display_df['平均順位'] = display_df['平均順位'].apply(
                    lambda x: f"{x:.2f}")
                display_df['累積pt'] = display_df['累積pt'].apply(
                    lambda x: f"{x:+.1f}")
                display_df['1位率(%)'] = display_df['1位率(%)'].apply(
                    lambda x: f"{x:.1f}")

                st.dataframe(display_df, width='stretch',
                             hide_index=True, height=400)

# ========== タブ2: 試合番号別ランキング ==========
with tab2:
    st.markdown("## 🎮 試合番号別ランキング")

    game_numbers = sorted(df['game_number'].unique())

    tab_game_cumulative, tab_game_avg_rank = st.tabs(
        ["累積ポイントランキング", "平均順位ランキング"])

    with tab_game_cumulative:
        st.markdown("### 試合番号別 累積ポイントランキング")

        for game_number in game_numbers:
            with st.expander(f"🎮 第{game_number}試合", expanded=False):
                game_df = df[df['game_number'] == game_number]

                # チームごとの統計
                team_stats = game_df.groupby(['team_id', 'team_name']).agg({
                    'points': ['sum', 'mean', 'count'],
                    'rank': 'mean'
                }).reset_index()

                team_stats.columns = [
                    'team_id', 'team_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']

                # 順位計算
                team_stats = team_stats.sort_values(
                    'cumulative_points', ascending=False)
                team_stats.insert(0, '順位', range(1, len(team_stats) + 1))

                # 1位〜4位の回数を計算
                rank_counts = game_df.groupby(
                    'team_id')['rank'].value_counts().unstack(fill_value=0)
                for i in range(1, 5):
                    if i not in rank_counts.columns:
                        rank_counts[i] = 0
                rank_counts = rank_counts[[1, 2, 3, 4]]
                rank_counts.columns = ['1位', '2位', '3位', '4位']

                # マージ
                team_stats = team_stats.merge(
                    rank_counts,
                    left_on='team_id',
                    right_index=True,
                    how='left'
                ).fillna(0)

                # 1位率を計算
                team_stats['1位率'] = (team_stats['1位'] /
                                     team_stats['games'] * 100).round(1)

                # 表示用に整形
                display_df = team_stats[[
                    '順位', 'team_name', 'cumulative_points', 'avg_points',
                    'games', 'avg_rank', '1位', '2位', '3位', '4位', '1位率'
                ]].copy()

                display_df.columns = [
                    '順位', 'チーム名', '累積pt', '平均pt',
                    '対局数', '平均順位', '1位', '2位', '3位', '4位', '1位率(%)'
                ]

                # フォーマット
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

    with tab_game_avg_rank:
        st.markdown("### 試合番号別 平均順位ランキング")

        for game_number in game_numbers:
            with st.expander(f"🎮 第{game_number}試合", expanded=False):
                game_df = df[df['game_number'] == game_number]

                # チームごとの統計
                team_stats = game_df.groupby(['team_id', 'team_name']).agg({
                    'points': ['sum', 'mean', 'count'],
                    'rank': 'mean'
                }).reset_index()

                team_stats.columns = [
                    'team_id', 'team_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']

                # 順位計算（平均順位の低い順）
                team_stats = team_stats.sort_values('avg_rank', ascending=True)
                team_stats.insert(0, '順位', range(1, len(team_stats) + 1))

                # 1位〜4位の回数を計算
                rank_counts = game_df.groupby(
                    'team_id')['rank'].value_counts().unstack(fill_value=0)
                for i in range(1, 5):
                    if i not in rank_counts.columns:
                        rank_counts[i] = 0
                rank_counts = rank_counts[[1, 2, 3, 4]]
                rank_counts.columns = ['1位', '2位', '3位', '4位']

                # マージ
                team_stats = team_stats.merge(
                    rank_counts,
                    left_on='team_id',
                    right_index=True,
                    how='left'
                ).fillna(0)

                # 1位率を計算
                team_stats['1位率'] = (team_stats['1位'] /
                                     team_stats['games'] * 100).round(1)

                # 表示用に整形
                display_df = team_stats[[
                    '順位', 'team_name', 'avg_rank', 'games',
                    'cumulative_points', '1位', '2位', '3位', '4位', '1位率'
                ]].copy()

                display_df.columns = [
                    '順位', 'チーム名', '平均順位', '対局数',
                    '累積pt', '1位', '2位', '3位', '4位', '1位率(%)'
                ]

                # フォーマット
                display_df['平均順位'] = display_df['平均順位'].apply(
                    lambda x: f"{x:.2f}")
                display_df['累積pt'] = display_df['累積pt'].apply(
                    lambda x: f"{x:+.1f}")
                display_df['1位率(%)'] = display_df['1位率(%)'].apply(
                    lambda x: f"{x:.1f}")

                st.dataframe(display_df, width='stretch',
                             hide_index=True, height=400)

# ========== タブ3: 直対ランキング ==========
with tab3:
    st.markdown("## ⚔️ 直対ランキング")

    st.info("""
    💡 **直対（直接対決）について**
    
    各半荘で、自チームの選手ポイント - 対戦相手チームの選手ポイントを計算し、
    チーム間の相性や優劣を分析します。
    
    - プラスが大きいほど、その相手に強い
    - マイナスが大きいほど、その相手に弱い
    """)

    # 直対成績を計算
    conn = get_connection()
    cursor = conn.cursor()

    if selected_period == "全期間":
        query = """
            SELECT 
                gr.season,
                gr.game_date,
                gr.game_number,
                gr.player_id,
                gr.points,
                pt.team_id,
                tn.team_name
            FROM game_results gr
            JOIN player_teams pt ON gr.player_id = pt.player_id AND gr.season = pt.season
            JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
            ORDER BY gr.season, gr.game_date, gr.game_number
        """
        cursor.execute(query)
    else:
        query = """
            SELECT 
                gr.season,
                gr.game_date,
                gr.game_number,
                gr.player_id,
                gr.points,
                pt.team_id,
                tn.team_name
            FROM game_results gr
            JOIN player_teams pt ON gr.player_id = pt.player_id AND gr.season = pt.season
            JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
            WHERE gr.season = ?
            ORDER BY gr.game_date, gr.game_number
        """
        cursor.execute(query, (selected_period,))

    game_data = cursor.fetchall()
    conn.close()

    game_df = pd.DataFrame(game_data, columns=[
        'season', 'game_date', 'game_number', 'player_id', 'points', 'team_id', 'team_name'
    ])

    # 直対成績を計算
    head_to_head = []

    for (season, date, number), group in game_df.groupby(['season', 'game_date', 'game_number']):
        teams_in_game = group[['team_id', 'team_name', 'points']].groupby(
            ['team_id', 'team_name']).sum().reset_index()

        for i, team1 in teams_in_game.iterrows():
            for j, team2 in teams_in_game.iterrows():
                if team1['team_id'] != team2['team_id']:
                    head_to_head.append({
                        'team_id': team1['team_id'],
                        'team_name': team1['team_name'],
                        'opponent_id': team2['team_id'],
                        'opponent_name': team2['team_name'],
                        'point_diff': team1['points'] - team2['points']
                    })

    h2h_df = pd.DataFrame(head_to_head)

    if not h2h_df.empty:
        # チーム別の直対成績を集計
        h2h_summary = h2h_df.groupby(['team_id', 'team_name', 'opponent_id', 'opponent_name']).agg({
            'point_diff': ['sum', 'mean', 'count']
        }).reset_index()

        h2h_summary.columns = ['team_id', 'team_name', 'opponent_id', 'opponent_name',
                               'total_diff', 'avg_diff', 'games']

        # チーム選択
        teams_list = sorted(h2h_summary['team_name'].unique())

        selected_team = st.selectbox("チームを選択", teams_list)

        if selected_team:
            st.markdown(f"### {selected_team} の直対成績")

            team_h2h = h2h_summary[h2h_summary['team_name']
                                   == selected_team].copy()
            team_h2h = team_h2h.sort_values('total_diff', ascending=False)
            team_h2h.insert(0, '順位', range(1, len(team_h2h) + 1))

            # 表示用に整形
            display_df = team_h2h[[
                '順位', 'opponent_name', 'games', 'total_diff', 'avg_diff'
            ]].copy()

            display_df.columns = ['順位', '対戦相手', '対局数', '累積pt差', '平均pt差']

            display_df['累積pt差'] = display_df['累積pt差'].apply(
                lambda x: f"{x:+.1f}")
            display_df['平均pt差'] = display_df['平均pt差'].apply(
                lambda x: f"{x:+.1f}")

            st.dataframe(display_df, width='stretch',
                         hide_index=True, height=400)

            # 統計情報
            col1, col2, col3 = st.columns(3)

            with col1:
                best_opponent = team_h2h.iloc[0]
                st.metric(
                    "最も有利な相手",
                    best_opponent['opponent_name'],
                    f"{best_opponent['total_diff']:+.1f}pt"
                )

            with col2:
                worst_opponent = team_h2h.iloc[-1]
                st.metric(
                    "最も不利な相手",
                    worst_opponent['opponent_name'],
                    f"{worst_opponent['total_diff']:+.1f}pt"
                )

            with col3:
                total_games = team_h2h['games'].sum()
                st.metric("総対局数", f"{total_games}局")

        # 全チーム直対マトリックス
        st.markdown("---")
        st.markdown("### 📊 全チーム直対マトリックス")

        st.markdown("各セルは「行チームから見た列チームとの累積pt差」を表示")

        # ピボットテーブルを作成
        pivot_data = h2h_summary.pivot_table(
            index='team_name',
            columns='opponent_name',
            values='total_diff',
            aggfunc='sum'
        )

        # フォーマット
        pivot_display = pivot_data.map(
            lambda x: f"{x:+.1f}" if pd.notna(x) else "-")

        st.dataframe(pivot_display, width='stretch')

    else:
        st.info("直対成績データがありません。")

# ========== 曜日別チームパフォーマンス分析 ==========
st.markdown("---")
st.subheader("📅 曜日別チームパフォーマンス分析")

st.markdown("対局の曜日によるチーム成績の傾向を分析します。")

# 曜日を追加（pandas dayofweek: 0=月曜, 6=日曜）
df_dow = df.copy()
df_dow['dow'] = pd.to_datetime(df_dow['game_date']).dt.dayofweek
dow_names = {0: '月', 1: '火', 2: '水', 3: '木', 4: '金', 5: '土', 6: '日'}
dow_order = [k for k in range(7) if k in df_dow['dow'].values]
dow_label = [dow_names[d] for d in dow_order]
df_dow['dow_name'] = df_dow['dow'].map(dow_names)

# チーム名一覧と色定義
teams_list = sorted(df_dow['team_name'].unique().tolist())
palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#17becf', '#bcbd22', '#7f7f7f']
team_color_map = {t: palette[i % len(palette)] for i, t in enumerate(teams_list)}

dtab1, dtab2, dtab3, dtab4 = st.tabs(["対局数", "平均ポイント", "平均順位", "順位割合"])

with dtab1:
    st.markdown("#### チーム別 曜日別 対局数")
    fig_dt1 = go.Figure()
    for team in teams_list:
        t_df = df_dow[df_dow['team_name'] == team]
        counts = t_df.groupby('dow')['points'].count().reindex(dow_order, fill_value=0)
        fig_dt1.add_trace(go.Bar(
            name=team,
            x=dow_label,
            y=counts.values,
            marker_color=team_color_map[team],
            text=counts.values,
            textposition='outside',
        ))
    fig_dt1.update_layout(
        barmode='group', xaxis_title="曜日", yaxis_title="対局数", height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_dt1, use_container_width=True)

with dtab2:
    st.markdown("#### チーム別 曜日別 平均ポイント")
    fig_dt2 = go.Figure()
    fig_dt2.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
    for team in teams_list:
        t_df = df_dow[df_dow['team_name'] == team]
        avg_pts = t_df.groupby('dow')['points'].mean().reindex(dow_order)
        fig_dt2.add_trace(go.Bar(
            name=team,
            x=dow_label,
            y=avg_pts.values,
            marker_color=team_color_map[team],
            text=[f"{v:+.2f}" if pd.notna(v) else "" for v in avg_pts.values],
            textposition='outside',
        ))
    fig_dt2.update_layout(
        barmode='group', xaxis_title="曜日", yaxis_title="平均ポイント", height=420,
        yaxis=dict(zeroline=True, zerolinecolor="gray"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_dt2, use_container_width=True)

with dtab3:
    st.markdown("#### チーム別 曜日別 平均順位")
    fig_dt3 = go.Figure()
    for team in teams_list:
        t_df = df_dow[df_dow['team_name'] == team]
        avg_rank = t_df.groupby('dow')['rank'].mean().reindex(dow_order)
        fig_dt3.add_trace(go.Bar(
            name=team,
            x=dow_label,
            y=avg_rank.values,
            marker_color=team_color_map[team],
            text=[f"{v:.3f}" if pd.notna(v) else "" for v in avg_rank.values],
            textposition='outside',
        ))
    fig_dt3.update_layout(
        barmode='group', xaxis_title="曜日", yaxis_title="平均順位", height=420,
        yaxis=dict(range=[1, 4.5], autorange=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_dt3, use_container_width=True)

with dtab4:
    st.markdown("#### 曜日別 順位割合（100%積み上げ）")
    selected_team_dow = st.selectbox("チームを選択", teams_list, key="dow_team_select")
    t_filtered = df_dow[df_dow['team_name'] == selected_team_dow]
    dow_stats = t_filtered.groupby('dow').agg(
        games=('points', 'count'),
        rank_1st=('rank', lambda x: (x == 1).sum()),
        rank_2nd=('rank', lambda x: (x == 2).sum()),
        rank_3rd=('rank', lambda x: (x == 3).sum()),
        rank_4th=('rank', lambda x: (x == 4).sum()),
    ).reindex(dow_order).reset_index()
    dow_stats['dow_name'] = dow_stats['dow'].map(dow_names)
    dow_stats = dow_stats.dropna(subset=['games'])
    dow_stats['rate_1st'] = (dow_stats['rank_1st'] / dow_stats['games'] * 100).round(1)
    dow_stats['rate_2nd'] = (dow_stats['rank_2nd'] / dow_stats['games'] * 100).round(1)
    dow_stats['rate_3rd'] = (dow_stats['rank_3rd'] / dow_stats['games'] * 100).round(1)
    dow_stats['rate_4th'] = (dow_stats['rank_4th'] / dow_stats['games'] * 100).round(1)

    fig_dt4 = go.Figure()
    for col, label, color in [
        ('rate_1st', '1位', '#FFD700'),
        ('rate_2nd', '2位', '#C0C0C0'),
        ('rate_3rd', '3位', '#CD7F32'),
        ('rate_4th', '4位', '#808080'),
    ]:
        fig_dt4.add_trace(go.Bar(
            x=dow_stats['dow_name'],
            y=dow_stats[col],
            name=label,
            marker_color=color,
            text=dow_stats[col].apply(lambda x: f"{x:.0f}%" if pd.notna(x) else ""),
            textposition='inside'
        ))
    fig_dt4.update_layout(
        barmode='stack',
        title=f"{selected_team_dow} — 曜日別 順位割合",
        xaxis_title="曜日", yaxis_title="割合（%）", height=480,
        yaxis=dict(range=[0, 100], dtick=25),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_dt4, use_container_width=True)

st.markdown("---")
st.caption("※ データは半荘記録から集計されています。曜日は対局日の曜日です。")
