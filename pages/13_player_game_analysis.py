import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db import get_connection, show_sidebar_navigation

st.set_page_config(
    page_title="選手半荘別分析 | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide"
)

# サイドバーナビゲーション
show_sidebar_navigation()

st.title("🎲 選手半荘別分析")

st.markdown("""
半荘記録から各選手の成績を詳細に分析します。
- 席順別ランキング（累積ポイント・平均順位）
- 試合番号別ランキング（累積ポイント・平均順位）
- 直対ランキング（対選手別の成績）
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
            gr.player_id,
            p.player_name,
            gr.season,
            gr.game_date,
            gr.game_number,
            gr.seat_name,
            gr.points,
            gr.rank
        FROM game_results gr
        JOIN players p ON gr.player_id = p.player_id
        ORDER BY gr.season, gr.game_date, gr.game_number
    """
    cursor.execute(query)
else:
    query = """
        SELECT 
            gr.player_id,
            p.player_name,
            gr.season,
            gr.game_date,
            gr.game_number,
            gr.seat_name,
            gr.points,
            gr.rank
        FROM game_results gr
        JOIN players p ON gr.player_id = p.player_id
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
    'player_id', 'player_name', 'season', 'game_date',
    'game_number', 'seat_name', 'points', 'rank'
])

# 月の情報を追加
df['month'] = pd.to_datetime(df['game_date']).dt.to_period('M').astype(str)

st.markdown("---")
st.info(f"📊 データ件数: {len(df)}対局 / {df['player_name'].nunique()}選手")

# ========== タブ構成 ==========
tab1, tab2, tab3 = st.tabs(["🧭 席順別", "🎮 試合番号別", "⚔️ 直対"])

# ========== タブ1: 席順別ランキング ==========
with tab1:
    st.markdown("## 🧭 席順別ランキング（累積ポイント）")

    seats = ['東', '南', '西', '北']
    seat_tabs = st.tabs([f"{seat}家" for seat in seats])

    for seat_idx, seat in enumerate(seats):
        with seat_tabs[seat_idx]:
            seat_df = df[df['seat_name'] == seat]

            if len(seat_df) == 0:
                st.info(f"{seat}家のデータがありません")
                continue

            # 選手ごとの統計
            player_stats = seat_df.groupby(['player_id', 'player_name']).agg({
                'points': ['sum', 'mean', 'count'],
                'rank': 'mean'
            }).reset_index()

            player_stats.columns = ['player_id', 'player_name',
                                    'cumulative_points', 'avg_points', 'games', 'avg_rank']

            # 順位計算
            player_stats = player_stats.sort_values(
                'cumulative_points', ascending=False)
            player_stats.insert(0, '順位', range(1, len(player_stats) + 1))

            # 1位〜4位の回数を計算
            rank_counts = seat_df.groupby(
                'player_id')['rank'].value_counts().unstack(fill_value=0)
            for i in range(1, 5):
                if i not in rank_counts.columns:
                    rank_counts[i] = 0
            rank_counts = rank_counts[[1, 2, 3, 4]]
            rank_counts.columns = ['1位', '2位', '3位', '4位']

            # マージ
            player_stats = player_stats.merge(
                rank_counts,
                left_on='player_id',
                right_index=True,
                how='left'
            ).fillna(0)

            # 1位率を計算
            player_stats['1位率'] = (
                player_stats['1位'] / player_stats['games'] * 100).round(1)

            # 表示用に整形
            display_df = player_stats[[
                '順位', 'player_name', 'cumulative_points', 'avg_points',
                'games', 'avg_rank', '1位', '2位', '3位', '4位', '1位率'
            ]].copy()

            display_df.columns = [
                '順位', '選手名', '累積pt', '平均pt',
                '対局数', '平均順位', '1位', '2位', '3位', '4位', '1位率(%)'
            ]

            # フォーマット
            display_df['累積pt'] = display_df['累積pt'].apply(
                lambda x: f"{x:+.1f}")
            display_df['平均pt'] = display_df['平均pt'].apply(
                lambda x: f"{x:+.1f}")
            display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
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

                # 選手ごとの統計
                player_stats = game_df.groupby(['player_id', 'player_name']).agg({
                    'points': ['sum', 'mean', 'count'],
                    'rank': 'mean'
                }).reset_index()

                player_stats.columns = [
                    'player_id',
                    'player_name',
                    'cumulative_points',
                    'avg_points',
                    'games',
                    'avg_rank'
                ]

                # 順位計算
                player_stats = player_stats.sort_values(
                    'cumulative_points', ascending=False)
                player_stats.insert(0, '順位', range(1, len(player_stats) + 1))

                # 1位〜4位の回数を計算
                rank_counts = game_df.groupby(
                    'player_id')['rank'].value_counts().unstack(fill_value=0)
                for i in range(1, 5):
                    if i not in rank_counts.columns:
                        rank_counts[i] = 0
                rank_counts = rank_counts[[1, 2, 3, 4]]
                rank_counts.columns = ['1位', '2位', '3位', '4位']

                # マージ
                player_stats = player_stats.merge(
                    rank_counts,
                    left_on='player_id',
                    right_index=True,
                    how='left'
                ).fillna(0)

                # 1位率を計算
                player_stats['1位率'] = (
                    player_stats['1位'] / player_stats['games'] * 100).round(1)

                # 表示用に整形
                display_df = player_stats[[
                    '順位', 'player_name', 'cumulative_points', 'avg_points',
                    'games', 'avg_rank', '1位', '2位', '3位', '4位', '1位率'
                ]].copy()

                display_df.columns = [
                    '順位', '選手名', '累積pt', '平均pt',
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

                # 選手ごとの統計
                player_stats = game_df.groupby(['player_id', 'player_name']).agg({
                    'points': ['sum', 'mean', 'count'],
                    'rank': 'mean'
                }).reset_index()

                player_stats.columns = [
                    'player_id',
                    'player_name',
                    'cumulative_points',
                    'avg_points',
                    'games',
                    'avg_rank'
                ]

                # 順位計算（平均順位の低い順）
                player_stats = player_stats.sort_values(
                    'avg_rank', ascending=True)
                player_stats.insert(0, '順位', range(1, len(player_stats) + 1))

                # 1位〜4位の回数を計算
                rank_counts = game_df.groupby(
                    'player_id')['rank'].value_counts().unstack(fill_value=0)
                for i in range(1, 5):
                    if i not in rank_counts.columns:
                        rank_counts[i] = 0
                rank_counts = rank_counts[[1, 2, 3, 4]]
                rank_counts.columns = ['1位', '2位', '3位', '4位']

                # マージ
                player_stats = player_stats.merge(
                    rank_counts,
                    left_on='player_id',
                    right_index=True,
                    how='left'
                ).fillna(0)

                # 1位率を計算
                player_stats['1位率'] = (
                    player_stats['1位'] / player_stats['games'] * 100).round(1)

                # 表示用に整形
                display_df = player_stats[[
                    '順位', 'player_name', 'avg_rank', 'games',
                    'cumulative_points', '1位', '2位', '3位', '4位', '1位率'
                ]].copy()

                display_df.columns = [
                    '順位', '選手名', '平均順位', '対局数',
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
    
    各半荘で、自分のポイント - 各対戦相手のポイントを計算し、
    選手間の相性や優劣を分析します。
    
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
                p.player_name,
                gr.points
            FROM game_results gr
            JOIN players p ON gr.player_id = p.player_id
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
                p.player_name,
                gr.points
            FROM game_results gr
            JOIN players p ON gr.player_id = p.player_id
            WHERE gr.season = ?
            ORDER BY gr.game_date, gr.game_number
        """
        cursor.execute(query, (selected_period,))

    game_data = cursor.fetchall()
    conn.close()

    game_df = pd.DataFrame(game_data, columns=[
        'season', 'game_date', 'game_number', 'player_id', 'player_name', 'points'
    ])

    # 直対成績を計算
    head_to_head = []

    for (season, date, number), group in game_df.groupby(['season', 'game_date', 'game_number']):
        players_in_game = group[['player_id', 'player_name', 'points']].values

        for player1 in players_in_game:
            for player2 in players_in_game:
                if player1[0] != player2[0]:
                    head_to_head.append({
                        'player_id': player1[0],
                        'player_name': player1[1],
                        'opponent_id': player2[0],
                        'opponent_name': player2[1],
                        'point_diff': player1[2] - player2[2]
                    })

    h2h_df = pd.DataFrame(head_to_head)

    if not h2h_df.empty:
        # 選手別の直対成績を集計
        h2h_summary = h2h_df.groupby(['player_id', 'player_name', 'opponent_id', 'opponent_name']).agg({
            'point_diff': ['sum', 'mean', 'count']
        }).reset_index()

        h2h_summary.columns = ['player_id', 'player_name', 'opponent_id', 'opponent_name',
                               'total_diff', 'avg_diff', 'games']

        # 選手選択
        players_list = sorted(h2h_summary['player_name'].unique())

        selected_player = st.selectbox("選手を選択", players_list)

        if selected_player:
            st.markdown(f"### {selected_player} の直対成績")

            player_h2h = h2h_summary[h2h_summary['player_name']
                                     == selected_player].copy()
            player_h2h = player_h2h.sort_values('total_diff', ascending=False)
            player_h2h.insert(0, '順位', range(1, len(player_h2h) + 1))

            # 表示用に整形
            display_df = player_h2h[[
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
                best_opponent = player_h2h.iloc[0]
                st.metric(
                    "最も有利な相手",
                    best_opponent['opponent_name'],
                    f"{best_opponent['total_diff']:+.1f}pt"
                )

            with col2:
                worst_opponent = player_h2h.iloc[-1]
                st.metric(
                    "最も不利な相手",
                    worst_opponent['opponent_name'],
                    f"{worst_opponent['total_diff']:+.1f}pt"
                )

            with col3:
                total_games = player_h2h['games'].sum()
                st.metric("総対局数", f"{total_games}局")

        # TOP5 vs TOP5 マトリックス
        st.markdown("---")
        st.markdown("### 📊 TOP20選手 直対マトリックス")

        st.markdown("各セルは「行選手から見た列選手との累積pt差」を表示")

        # 累積pt上位20名を取得
        conn = get_connection()
        if selected_period == "全期間":
            top_query = """
                SELECT p.player_id, p.player_name, SUM(gr.points) as total_points
                FROM game_results gr
                JOIN players p ON gr.player_id = p.player_id
                GROUP BY p.player_id, p.player_name
                ORDER BY total_points DESC
                LIMIT 20
            """
            top_players_df = pd.read_sql_query(top_query, conn)
        else:
            top_query = """
                SELECT p.player_id, p.player_name, SUM(gr.points) as total_points
                FROM game_results gr
                JOIN players p ON gr.player_id = p.player_id
                WHERE gr.season = ?
                GROUP BY p.player_id, p.player_name
                ORDER BY total_points DESC
                LIMIT 20
            """
            top_players_df = pd.read_sql_query(
                top_query, conn, params=(selected_period,))
        conn.close()

        top_players = top_players_df['player_name'].tolist()

        # TOP20内の直対成績のみを抽出
        top_h2h = h2h_summary[
            (h2h_summary['player_name'].isin(top_players)) &
            (h2h_summary['opponent_name'].isin(top_players))
        ]

        # ピボットテーブルを作成
        pivot_data = top_h2h.pivot_table(
            index='player_name',
            columns='opponent_name',
            values='total_diff',
            aggfunc='sum'
        )

        # 名前順でソート
        pivot_data = pivot_data.reindex(index=top_players, columns=top_players)

        # フォーマット
        pivot_display = pivot_data.map(
            lambda x: f"{x:+.1f}" if pd.notna(x) else "-")

        st.dataframe(pivot_display, width='stretch', height=600)

    else:
        st.info("直対成績データがありません。")

# ========== 曜日別選手パフォーマンス分析 ==========
st.markdown("---")
st.subheader("📅 曜日別選手パフォーマンス分析")

st.markdown("対局の曜日による選手成績の傾向を分析します。")

# 選手を選択
players_list = sorted(df['player_name'].unique().tolist())
selected_player_dow = st.selectbox("選手を選択", players_list, key="dow_player_select")

# 曜日を追加（pandas dayofweek: 0=月曜, 6=日曜）
df_dow_p = df[df['player_name'] == selected_player_dow].copy()
df_dow_p['dow'] = pd.to_datetime(df_dow_p['game_date']).dt.dayofweek
dow_names_p = {0: '月', 1: '火', 2: '水', 3: '木', 4: '金', 5: '土', 6: '日'}
dow_order_p = [k for k in range(7) if k in df_dow_p['dow'].values]
df_dow_p['dow_name'] = df_dow_p['dow'].map(dow_names_p)

if df_dow_p.empty:
    st.warning("選択した選手のデータがありません。")
else:
    # 集計
    dow_stats_p = df_dow_p.groupby('dow').agg(
        games=('points', 'count'),
        avg_points=('points', 'mean'),
        avg_rank=('rank', 'mean'),
        rank_1st=('rank', lambda x: (x == 1).sum()),
        rank_2nd=('rank', lambda x: (x == 2).sum()),
        rank_3rd=('rank', lambda x: (x == 3).sum()),
        rank_4th=('rank', lambda x: (x == 4).sum()),
    ).reindex(dow_order_p).reset_index()
    dow_stats_p['dow_name'] = dow_stats_p['dow'].map(dow_names_p)
    dow_stats_p = dow_stats_p.dropna(subset=['games'])
    dow_stats_p['rate_1st'] = (dow_stats_p['rank_1st'] / dow_stats_p['games'] * 100).round(1)
    dow_stats_p['rate_2nd'] = (dow_stats_p['rank_2nd'] / dow_stats_p['games'] * 100).round(1)
    dow_stats_p['rate_3rd'] = (dow_stats_p['rank_3rd'] / dow_stats_p['games'] * 100).round(1)
    dow_stats_p['rate_4th'] = (dow_stats_p['rank_4th'] / dow_stats_p['games'] * 100).round(1)

    dow_colors_p = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#FFB347', '#DDA0DD']
    bar_colors_p = [dow_colors_p[d % len(dow_colors_p)] for d in dow_stats_p['dow']]

    # サマリーテーブル
    st.markdown(f"### 📊 {selected_player_dow} 曜日別統計サマリー")
    display_p = dow_stats_p[['dow_name', 'games', 'avg_points', 'avg_rank',
                              'rank_1st', 'rank_2nd', 'rank_3rd', 'rank_4th', 'rate_1st']].copy()
    display_p.columns = ['曜日', '対局数', '平均pt', '平均順位', '1位', '2位', '3位', '4位', '1位率(%)']
    display_p['平均pt'] = display_p['平均pt'].apply(lambda x: f"{x:+.2f}")
    display_p['平均順位'] = display_p['平均順位'].apply(lambda x: f"{x:.3f}")
    display_p['1位率(%)'] = display_p['1位率(%)'].apply(lambda x: f"{x:.1f}")
    st.dataframe(display_p, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("### 📈 視覚的比較")

    ptab1, ptab2, ptab3, ptab4 = st.tabs(["対局数", "平均ポイント", "平均順位", "順位割合"])

    with ptab1:
        st.markdown(f"#### {selected_player_dow} 曜日別 対局数")
        fig_p1 = go.Figure()
        fig_p1.add_trace(go.Bar(
            x=dow_stats_p['dow_name'],
            y=dow_stats_p['games'],
            marker_color=bar_colors_p,
            text=dow_stats_p['games'],
            textposition='outside',
            showlegend=False
        ))
        fig_p1.update_layout(xaxis_title="曜日", yaxis_title="対局数", height=400)
        st.plotly_chart(fig_p1, use_container_width=True)

    with ptab2:
        st.markdown(f"#### {selected_player_dow} 曜日別 平均ポイント")
        fig_p2 = go.Figure()
        fig_p2.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
        fig_p2.add_trace(go.Bar(
            x=dow_stats_p['dow_name'],
            y=dow_stats_p['avg_points'],
            marker_color=bar_colors_p,
            text=dow_stats_p['avg_points'].apply(lambda x: f"{x:+.2f}"),
            textposition='outside',
            showlegend=False
        ))
        fig_p2.update_layout(
            xaxis_title="曜日", yaxis_title="平均ポイント", height=400,
            yaxis=dict(zeroline=True, zerolinecolor="gray")
        )
        st.plotly_chart(fig_p2, use_container_width=True)
        best_p = dow_stats_p.loc[dow_stats_p['avg_points'].idxmax()]
        worst_p = dow_stats_p.loc[dow_stats_p['avg_points'].idxmin()]
        st.info(f"💡 平均ポイントが最も高い曜日は **{best_p['dow_name']}曜日**（{best_p['avg_points']:+.2f}pt）、最も低いのは **{worst_p['dow_name']}曜日**（{worst_p['avg_points']:+.2f}pt）です。")

    with ptab3:
        st.markdown(f"#### {selected_player_dow} 曜日別 平均順位")
        fig_p3 = go.Figure()
        fig_p3.add_trace(go.Bar(
            x=dow_stats_p['dow_name'],
            y=dow_stats_p['avg_rank'],
            marker_color=bar_colors_p,
            text=dow_stats_p['avg_rank'].apply(lambda x: f"{x:.3f}"),
            textposition='outside',
            showlegend=False
        ))
        fig_p3.update_layout(
            xaxis_title="曜日", yaxis_title="平均順位", height=400,
            yaxis=dict(range=[1, 4.5], autorange=False)
        )
        st.plotly_chart(fig_p3, use_container_width=True)
        best_pr = dow_stats_p.loc[dow_stats_p['avg_rank'].idxmin()]
        worst_pr = dow_stats_p.loc[dow_stats_p['avg_rank'].idxmax()]
        st.info(f"💡 平均順位が最も良い曜日は **{best_pr['dow_name']}曜日**（{best_pr['avg_rank']:.3f}位）、最も悪いのは **{worst_pr['dow_name']}曜日**（{worst_pr['avg_rank']:.3f}位）です。")

    with ptab4:
        st.markdown(f"#### {selected_player_dow} 曜日別 順位割合（100%積み上げ）")
        fig_p4 = go.Figure()
        for col, label, color in [
            ('rate_1st', '1位', '#FFD700'),
            ('rate_2nd', '2位', '#C0C0C0'),
            ('rate_3rd', '3位', '#CD7F32'),
            ('rate_4th', '4位', '#808080'),
        ]:
            fig_p4.add_trace(go.Bar(
                x=dow_stats_p['dow_name'],
                y=dow_stats_p[col],
                name=label,
                marker_color=color,
                text=dow_stats_p[col].apply(lambda x: f"{x:.0f}%" if pd.notna(x) else ""),
                textposition='inside'
            ))
        fig_p4.update_layout(
            barmode='stack',
            title=f"{selected_player_dow} — 曜日別 順位割合",
            xaxis_title="曜日", yaxis_title="割合（%）", height=480,
            yaxis=dict(range=[0, 100], dtick=25),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_p4, use_container_width=True)

st.markdown("---")
st.caption("※ データは半荘記録から集計されています。曜日は対局日の曜日です。")
