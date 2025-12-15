import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from db import get_connection, hide_default_sidebar_navigation

st.set_page_config(
    page_title="チーム半荘別分析 | Mリーグダッシュボード",
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
st.sidebar.page_link("pages/15_game_records.py", label="📜 対局記録")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/3_admin.py", label="⚙️ データ管理")
st.sidebar.page_link("pages/4_player_admin.py", label="👤 選手管理")
st.sidebar.page_link("pages/9_team_master_admin.py", label="🏢 チーム管理")
st.sidebar.page_link("pages/5_season_update.py", label="🔄 シーズン更新")
st.sidebar.page_link("pages/6_player_stats_input.py", label="📊 選手成績入力")
st.sidebar.page_link("pages/11_game_results_input.py", label="🎮 半荘記録入力")

st.title("🎲 チーム半荘別分析")

st.markdown("""
半荘記録から各チームの成績を詳細に分析します。
- 月別ランキング（累積ポイント推移・平均順位推移グラフ）
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

# 月の情報を追加
df['month'] = pd.to_datetime(df['game_date']).dt.to_period('M').astype(str)

st.markdown("---")
st.info(f"📊 データ件数: {len(df)}対局 / {df['team_name'].nunique()}チーム")

# ========== タブ構成 ==========
tab1, tab2, tab3, tab4 = st.tabs(["📅 月別", "🧭 席順別", "🎮 試合番号別", "⚔️ 直対"])

# ========== タブ1: 月別ランキング ==========
with tab1:
    st.markdown("## 📅 月別ランキング")
    
    months = sorted(df['month'].unique())
    
    if len(months) == 0:
        st.info("月別データがありません。")
    else:
        # チーム別・月別の累積データを計算
        monthly_team_data = []
        
        for month in months:
            month_df = df[df['month'] == month]
            
            # チームごとの統計
            team_stats = month_df.groupby(['team_id', 'team_name']).agg({
                'points': ['sum', 'mean', 'count'],
                'rank': 'mean'
            }).reset_index()
            
            team_stats.columns = ['team_id', 'team_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']
            
            for _, row in team_stats.iterrows():
                monthly_team_data.append({
                    'month': month,
                    'team_id': row['team_id'],
                    'team_name': row['team_name'],
                    'cumulative_points': row['cumulative_points'],
                    'avg_points': row['avg_points'],
                    'games': row['games'],
                    'avg_rank': row['avg_rank']
                })
        
        monthly_df = pd.DataFrame(monthly_team_data)
        
        # タブで累積ポイントと平均順位を分ける
        tab_cumulative, tab_avg_rank = st.tabs(["累積ポイント推移", "平均順位推移"])
        
        with tab_cumulative:
            st.markdown("### 📈 月別累積ポイント推移")
            
            # 折れ線グラフ作成
            fig1 = go.Figure()
            
            teams = monthly_df['team_name'].unique()
            
            for team_name in sorted(teams):
                team_data = monthly_df[monthly_df['team_name'] == team_name].sort_values('month')
                
                fig1.add_trace(go.Scatter(
                    x=team_data['month'],
                    y=team_data['cumulative_points'],
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
                title="チーム別 月別累積ポイント推移",
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
                yaxis=dict(zeroline=True, zerolinecolor="gray", zerolinewidth=1)
            )
            
            st.plotly_chart(fig1, use_container_width=True)
            
            # 統計サマリー
            st.markdown("#### 📊 月別統計")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("対象月数", f"{len(months)}ヶ月")
            
            with col2:
                total_games = monthly_df['games'].sum()
                st.metric("総対局数", f"{int(total_games)}対局")
            
            with col3:
                avg_games_per_month = total_games / len(months) if len(months) > 0 else 0
                st.metric("月平均対局数", f"{avg_games_per_month:.1f}対局")
        
        with tab_avg_rank:
            st.markdown("### 📈 月別平均順位推移")
            
            # 折れ線グラフ作成
            fig2 = go.Figure()
            
            teams = monthly_df['team_name'].unique()
            
            for team_name in sorted(teams):
                team_data = monthly_df[monthly_df['team_name'] == team_name].sort_values('month')
                
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
                title="チーム別 月別平均順位推移",
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
            
            st.plotly_chart(fig2, use_container_width=True)
            
            # 最新月のランキング
            st.markdown("#### 🏆 最新月のランキング")
            
            latest_month = months[-1]
            latest_month_df = monthly_df[monthly_df['month'] == latest_month].sort_values('cumulative_points', ascending=False)
            latest_month_df = latest_month_df.reset_index(drop=True)
            latest_month_df.insert(0, '順位', range(1, len(latest_month_df) + 1))
            
            display_latest = latest_month_df[['順位', 'team_name', 'cumulative_points', 'avg_rank', 'games']].copy()
            display_latest.columns = ['順位', 'チーム名', '累積pt', '平均順位', '対局数']
            display_latest['累積pt'] = display_latest['累積pt'].apply(lambda x: f"{x:+.1f}")
            display_latest['平均順位'] = display_latest['平均順位'].apply(lambda x: f"{x:.2f}")
            
            st.dataframe(display_latest, hide_index=True, use_container_width=True)

# ========== タブ2: 席順別ランキング ==========
with tab2:
    st.markdown("## 🧭 席順別ランキング")
    
    seats = ['東', '南', '西', '北']
    
    tab_seat_cumulative, tab_seat_avg_rank = st.tabs(["累積ポイントランキング", "平均順位ランキング"])
    
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
                
                team_stats.columns = ['team_id', 'team_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']
                
                # 順位計算
                team_stats = team_stats.sort_values('cumulative_points', ascending=False)
                team_stats.insert(0, '順位', range(1, len(team_stats) + 1))
                
                # 1位〜4位の回数を計算
                rank_counts = seat_df.groupby('team_id')['rank'].value_counts().unstack(fill_value=0)
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
                team_stats['1位率'] = (team_stats['1位'] / team_stats['games'] * 100).round(1)
                
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
                display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
                display_df['平均pt'] = display_df['平均pt'].apply(lambda x: f"{x:+.1f}")
                display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
                display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.1f}")
                
                st.dataframe(display_df, width='stretch', hide_index=True, height=400)
    
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
                
                team_stats.columns = ['team_id', 'team_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']
                
                # 順位計算（平均順位の低い順）
                team_stats = team_stats.sort_values('avg_rank', ascending=True)
                team_stats.insert(0, '順位', range(1, len(team_stats) + 1))
                
                # 1位〜4位の回数を計算
                rank_counts = seat_df.groupby('team_id')['rank'].value_counts().unstack(fill_value=0)
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
                team_stats['1位率'] = (team_stats['1位'] / team_stats['games'] * 100).round(1)
                
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
                display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
                display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
                display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.1f}")
                
                st.dataframe(display_df, width='stretch', hide_index=True, height=400)

# ========== タブ3: 試合番号別ランキング ==========
with tab3:
    st.markdown("## 🎮 試合番号別ランキング")
    
    game_numbers = sorted(df['game_number'].unique())
    
    tab_game_cumulative, tab_game_avg_rank = st.tabs(["累積ポイントランキング", "平均順位ランキング"])
    
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
                
                team_stats.columns = ['team_id', 'team_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']
                
                # 順位計算
                team_stats = team_stats.sort_values('cumulative_points', ascending=False)
                team_stats.insert(0, '順位', range(1, len(team_stats) + 1))
                
                # 1位〜4位の回数を計算
                rank_counts = game_df.groupby('team_id')['rank'].value_counts().unstack(fill_value=0)
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
                team_stats['1位率'] = (team_stats['1位'] / team_stats['games'] * 100).round(1)
                
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
                display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
                display_df['平均pt'] = display_df['平均pt'].apply(lambda x: f"{x:+.1f}")
                display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
                display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.1f}")
                
                st.dataframe(display_df, width='stretch', hide_index=True, height=400)
    
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
                
                team_stats.columns = ['team_id', 'team_name', 'cumulative_points', 'avg_points', 'games', 'avg_rank']
                
                # 順位計算（平均順位の低い順）
                team_stats = team_stats.sort_values('avg_rank', ascending=True)
                team_stats.insert(0, '順位', range(1, len(team_stats) + 1))
                
                # 1位〜4位の回数を計算
                rank_counts = game_df.groupby('team_id')['rank'].value_counts().unstack(fill_value=0)
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
                team_stats['1位率'] = (team_stats['1位'] / team_stats['games'] * 100).round(1)
                
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
                display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
                display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
                display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.1f}")
                
                st.dataframe(display_df, width='stretch', hide_index=True, height=400)

# ========== タブ4: 直対ランキング ==========
with tab4:
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
        teams_in_game = group[['team_id', 'team_name', 'points']].groupby(['team_id', 'team_name']).sum().reset_index()
        
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
            
            team_h2h = h2h_summary[h2h_summary['team_name'] == selected_team].copy()
            team_h2h = team_h2h.sort_values('total_diff', ascending=False)
            team_h2h.insert(0, '順位', range(1, len(team_h2h) + 1))
            
            # 表示用に整形
            display_df = team_h2h[[
                '順位', 'opponent_name', 'games', 'total_diff', 'avg_diff'
            ]].copy()
            
            display_df.columns = ['順位', '対戦相手', '対局数', '累積pt差', '平均pt差']
            
            display_df['累積pt差'] = display_df['累積pt差'].apply(lambda x: f"{x:+.1f}")
            display_df['平均pt差'] = display_df['平均pt差'].apply(lambda x: f"{x:+.1f}")
            
            st.dataframe(display_df, width='stretch', hide_index=True, height=400)
            
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
        pivot_display = pivot_data.applymap(lambda x: f"{x:+.1f}" if pd.notna(x) else "-")
        
        st.dataframe(pivot_display, width='stretch')
        
    else:
        st.info("直対成績データがありません。")
