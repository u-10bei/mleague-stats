import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
sys.path.append("..")
from db import get_connection, hide_default_sidebar_navigation

st.set_page_config(
    page_title="統計分析 | Mリーグダッシュボード",
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

st.title("📈 統計分析")

st.markdown("""
半荘記録から集計した統計データを分析します。
- **席順別統計**: 東・南・西・北の各席のパフォーマンスを比較
- 期間を指定して分析可能
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

conn.close()

# ========== フィルター設定 ==========
st.markdown("---")
st.subheader("🔍 分析期間")

col1, col2 = st.columns([1, 3])

with col1:
    period_options = ["全期間"] + seasons
    selected_period = st.selectbox("期間", period_options, key="period_select")

with col2:
    if selected_period == "全期間":
        st.info(f"📊 全期間のデータを分析します（{len(seasons)}シーズン）")
    else:
        st.info(f"📊 {selected_period}シーズンのデータを分析します")

# ========== 席順別統計分析 ==========
st.markdown("---")
st.subheader("🧭 席順別パフォーマンス分析")

st.markdown("""
各席（東・南・西・北）での全選手の成績を集計し、席による有利・不利を分析します。
""")


# データ取得
conn = get_connection()

if selected_period == "全期間":
    query = """
        SELECT 
            seat_name,
            COUNT(*) as games,
            AVG(points) as avg_points,
            AVG(rank) as avg_rank,
            SUM(CASE WHEN rank = 1 THEN 1 ELSE 0 END) as rank_1st,
            SUM(CASE WHEN rank = 2 THEN 1 ELSE 0 END) as rank_2nd,
            SUM(CASE WHEN rank = 3 THEN 1 ELSE 0 END) as rank_3rd,
            SUM(CASE WHEN rank = 4 THEN 1 ELSE 0 END) as rank_4th
        FROM game_results
        GROUP BY seat_name
        ORDER BY 
            CASE seat_name
                WHEN '東' THEN 1
                WHEN '南' THEN 2
                WHEN '西' THEN 3
                WHEN '北' THEN 4
            END
    """
    cursor = conn.cursor()
    cursor.execute(query)
else:
    query = """
        SELECT 
            seat_name,
            COUNT(*) as games,
            AVG(points) as avg_points,
            AVG(rank) as avg_rank,
            SUM(CASE WHEN rank = 1 THEN 1 ELSE 0 END) as rank_1st,
            SUM(CASE WHEN rank = 2 THEN 1 ELSE 0 END) as rank_2nd,
            SUM(CASE WHEN rank = 3 THEN 1 ELSE 0 END) as rank_3rd,
            SUM(CASE WHEN rank = 4 THEN 1 ELSE 0 END) as rank_4th
        FROM game_results
        WHERE season = ?
        GROUP BY seat_name
        ORDER BY 
            CASE seat_name
                WHEN '東' THEN 1
                WHEN '南' THEN 2
                WHEN '西' THEN 3
                WHEN '北' THEN 4
            END
    """
    cursor = conn.cursor()
    cursor.execute(query, (selected_period,))

results = cursor.fetchall()
conn.close()

if not results:
    st.warning("選択した期間に該当するデータがありません。")
    st.stop()

# DataFrameに変換
df = pd.DataFrame(results, columns=[
    'seat_name', 'games', 'avg_points', 'avg_rank',
    'rank_1st', 'rank_2nd', 'rank_3rd', 'rank_4th'
])

# 1位率などを計算
df['rate_1st'] = (df['rank_1st'] / df['games'] * 100).round(2)
df['rate_2nd'] = (df['rank_2nd'] / df['games'] * 100).round(2)
df['rate_3rd'] = (df['rank_3rd'] / df['games'] * 100).round(2)
df['rate_4th'] = (df['rank_4th'] / df['games'] * 100).round(2)
    

# ========== サマリーテーブル ==========
st.markdown("### 📊 席順別統計サマリー")

# 表示用テーブル
display_df = df[['seat_name', 'games', 'avg_points', 'avg_rank', 
                 'rank_1st', 'rank_2nd', 'rank_3rd', 'rank_4th',
                 'rate_1st']].copy()

display_df.columns = ['席', '対局数', '平均pt', '平均順位', 
                      '1位', '2位', '3位', '4位', '1位率(%)']

# フォーマット
display_df['平均pt'] = display_df['平均pt'].apply(lambda x: f"{x:+.2f}")
display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.3f}")
display_df['1位率(%)'] = display_df['1位率(%)'].apply(lambda x: f"{x:.2f}")

st.dataframe(
    display_df,
    hide_index=True,
    width='stretch',
    column_config={
        '席': st.column_config.TextColumn(width="small"),
        '対局数': st.column_config.NumberColumn(width="small"),
        '平均pt': st.column_config.TextColumn(width="small"),
        '平均順位': st.column_config.TextColumn(width="small"),
        '1位': st.column_config.NumberColumn(width="small"),
        '2位': st.column_config.NumberColumn(width="small"),
        '3位': st.column_config.NumberColumn(width="small"),
        '4位': st.column_config.NumberColumn(width="small"),
        '1位率(%)': st.column_config.TextColumn(width="small"),
    }
)
    

# ========== グラフ表示 ==========
st.markdown("---")
st.markdown("### 📈 視覚的比較")

tab1, tab2, tab3, tab4 = st.tabs(["平均ポイント", "平均順位", "順位分布", "1位率"])

with tab1:
    st.markdown("#### 席別 平均ポイント")
    
    fig1 = go.Figure()
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
    
    fig1.add_trace(go.Bar(
        x=df['seat_name'],
        y=df['avg_points'],
        marker_color=colors,
        text=df['avg_points'].apply(lambda x: f"{x:+.2f}"),
        textposition='outside',
        showlegend=False
    ))
    
    fig1.update_layout(
        xaxis_title="席",
        yaxis_title="平均ポイント",
        height=400,
        yaxis=dict(zeroline=True, zerolinecolor="gray", zerolinewidth=2)
    )
    
    st.plotly_chart(fig1)
    
    # 最高値と最低値の差を表示
    max_seat = df.loc[df['avg_points'].idxmax()]
    min_seat = df.loc[df['avg_points'].idxmin()]
    diff = max_seat['avg_points'] - min_seat['avg_points']
    
    st.info(f"💡 **{max_seat['seat_name']}家**が最も高く（平均{max_seat['avg_points']:+.2f}pt）、**{min_seat['seat_name']}家**が最も低い（平均{min_seat['avg_points']:+.2f}pt）。差は**{diff:.2f}pt**です。")

with tab2:
    st.markdown("#### 席別 平均順位")
    
    fig2 = go.Figure()
    
    fig2.add_trace(go.Bar(
        x=df['seat_name'],
        y=df['avg_rank'],
        marker_color=colors,
        text=df['avg_rank'].apply(lambda x: f"{x:.3f}"),
        textposition='outside',
        showlegend=False
    ))
    
    fig2.update_layout(
        xaxis_title="席",
        yaxis_title="平均順位",
        height=400,
        yaxis=dict(range=[1, 4])
    )
    
    st.plotly_chart(fig2)
    
    # 最良と最悪の順位
    best_seat = df.loc[df['avg_rank'].idxmin()]
    worst_seat = df.loc[df['avg_rank'].idxmax()]
    diff_rank = worst_seat['avg_rank'] - best_seat['avg_rank']
    
    st.info(f"💡 **{best_seat['seat_name']}家**が最も良い平均順位（{best_seat['avg_rank']:.3f}位）、**{worst_seat['seat_name']}家**が最も悪い（{worst_seat['avg_rank']:.3f}位）。差は**{diff_rank:.3f}**です。")

with tab3:
    st.markdown("#### 席別 順位分布")
    
    fig3 = go.Figure()
    
    fig3.add_trace(go.Bar(
        name='1位',
        x=df['seat_name'],
        y=df['rate_1st'],
        marker_color='#FFD700',
        text=df['rate_1st'].apply(lambda x: f"{x:.1f}%"),
        textposition='inside'
    ))
    
    fig3.add_trace(go.Bar(
        name='2位',
        x=df['seat_name'],
        y=df['rate_2nd'],
        marker_color='#C0C0C0',
        text=df['rate_2nd'].apply(lambda x: f"{x:.1f}%"),
        textposition='inside'
    ))
    
    fig3.add_trace(go.Bar(
        name='3位',
        x=df['seat_name'],
        y=df['rate_3rd'],
        marker_color='#CD7F32',
        text=df['rate_3rd'].apply(lambda x: f"{x:.1f}%"),
        textposition='inside'
    ))
    
    fig3.add_trace(go.Bar(
        name='4位',
        x=df['seat_name'],
        y=df['rate_4th'],
        marker_color='#808080',
        text=df['rate_4th'].apply(lambda x: f"{x:.1f}%"),
        textposition='inside'
    ))
    
    fig3.update_layout(
        barmode='stack',
        xaxis_title="席",
        yaxis_title="順位分布（%）",
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    st.plotly_chart(fig3)
    
    st.info("💡 各席での1位〜4位の出現率を積み上げ棒グラフで表示。理想的には各順位が25%ずつになります。")

with tab4:
    st.markdown("#### 席別 1位率")
    
    fig4 = go.Figure()
    
    # 基準線（25%）
    fig4.add_trace(go.Scatter(
        x=['東', '南', '西', '北'],
        y=[25, 25, 25, 25],
        mode='lines',
        name='理論値（25%）',
        line=dict(color='red', dash='dash', width=2)
    ))
    
    fig4.add_trace(go.Bar(
        x=df['seat_name'],
        y=df['rate_1st'],
        marker_color=colors,
        text=df['rate_1st'].apply(lambda x: f"{x:.2f}%"),
        textposition='outside',
        name='実測値',
        showlegend=True
    ))
    
    fig4.update_layout(
        xaxis_title="席",
        yaxis_title="1位率（%）",
        height=400,
        yaxis=dict(range=[0, max(df['rate_1st'].max() + 2, 30)])
    )
    
    st.plotly_chart(fig4)
    
    # 25%との差を計算
    st.markdown("#### 理論値（25%）からの乖離")
    
    for _, row in df.iterrows():
        diff_from_25 = row['rate_1st'] - 25
        if diff_from_25 > 0:
            st.success(f"**{row['seat_name']}家**: {row['rate_1st']:.2f}% （理論値より**+{diff_from_25:.2f}%**高い）")
        elif diff_from_25 < 0:
            st.error(f"**{row['seat_name']}家**: {row['rate_1st']:.2f}% （理論値より**{diff_from_25:.2f}%**低い）")
        else:
            st.info(f"**{row['seat_name']}家**: {row['rate_1st']:.2f}% （理論値と一致）")
    

# ========== 統計的考察 ==========
st.markdown("---")
st.subheader("📝 統計的考察")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 🎯 主要な知見")
    
    # 最も有利な席
    best_points_seat = df.loc[df['avg_points'].idxmax()]
    best_rank_seat = df.loc[df['avg_rank'].idxmin()]
    best_rate_seat = df.loc[df['rate_1st'].idxmax()]
    
    st.markdown(f"""
    - **平均ポイントが最も高い**: {best_points_seat['seat_name']}家（{best_points_seat['avg_points']:+.2f}pt）
    - **平均順位が最も良い**: {best_rank_seat['seat_name']}家（{best_rank_seat['avg_rank']:.3f}位）
    - **1位率が最も高い**: {best_rate_seat['seat_name']}家（{best_rate_seat['rate_1st']:.2f}%）
    """)
    
    # データ規模
    total_games = df['games'].sum()
    st.markdown(f"""
    ---
    **分析データ規模**
    - 総対局数: {total_games:,}局
    - 席あたり平均: {total_games // 4:,}局
    """)

with col2:
    st.markdown("#### 📊 順位分布の均等性")
    
    # 各順位の分散を計算
    for rank_col, rank_name in [('rate_1st', '1位'), ('rate_2nd', '2位'), 
                                  ('rate_3rd', '3位'), ('rate_4th', '4位')]:
        mean_rate = df[rank_col].mean()
        std_rate = df[rank_col].std()
        st.markdown(f"**{rank_name}率**: 平均 {mean_rate:.2f}%、標準偏差 {std_rate:.2f}%")
    
    st.markdown("---")
    st.info("""
    💡 **解釈のヒント**
    - 標準偏差が小さいほど、席による差が少ない
    - 理論値（25%）から大きく外れる席は、構造的な有利/不利がある可能性
    - ただし、Mリーグ特有の戦略やルールの影響も考慮が必要
    """)

# ========== 将来の拡張機能 ==========
st.markdown("---")
st.subheader("🚀 今後実装予定の分析")

st.info("""
以下の統計分析を今後追加予定です：

**⏰ 時間帯別分析**
- 開始時間帯による成績の違い
- 午前/午後/夜間での傾向分析

**📅 曜日別分析**
- 曜日による成績の変動
- 週末と平日の比較

**🎮 卓区分別分析**
- レギュラー vs セミファイナル vs ファイナル
- 重要な局面での成績傾向

**📆 月別・シーズン内推移**
- シーズン序盤・中盤・終盤での傾向
- 月ごとの成績変動

**👥 対戦相手との相性分析**
- 特定の選手同士での成績
- チーム対抗での傾向

データが蓄積されるにつれて、より詳細な分析が可能になります。
""")

st.markdown("---")
st.caption("※ データは半荘記録から集計されています。")

