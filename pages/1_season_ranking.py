import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
sys.path.append("..")
from db import get_team_colors, get_season_points, get_seasons, get_season_data, get_connection, hide_default_sidebar_navigation

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
st.sidebar.page_link("pages/10_team_game_analysis.py", label="🎲 半荘別分析")
st.sidebar.markdown("### 👤 選手成績")
st.sidebar.page_link("pages/7_player_season_ranking.py", label="📊 年度別ランキング")
st.sidebar.page_link("pages/8_player_cumulative_ranking.py", label="🏆 累積ランキング")
st.sidebar.page_link("pages/13_player_game_analysis.py", label="🎲 半荘別分析")
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
filtered_df = get_season_data(selected_season).sort_values("points", ascending=True)

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
    
    rank_df = filtered_df.sort_values("rank")[["rank", "team_name", "points"]].copy()
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
        
        st.markdown("### 月別ランキング（累積ポイント順）")
        
        for month in months:
            with st.expander(f"📅 {month}", expanded=False):
                month_df = df[df['month'] == month].copy()
                
                # 累積ポイント順に並べる
                month_df = month_df.sort_values('total_points', ascending=False)
                month_df.insert(0, '順位', range(1, len(month_df) + 1))
                
                # 表示用に整形
                display_df = month_df[[
                    '順位', 'team_name', 'total_points', 'games', 'avg_rank'
                ]].copy()
                
                display_df.columns = [
                    '順位', 'チーム名', '累積pt', '対局数', '平均順位'
                ]
                
                display_df['累積pt'] = display_df['累積pt'].apply(lambda x: f"{x:+.1f}")
                display_df['平均順位'] = display_df['平均順位'].apply(lambda x: f"{x:.2f}")
                
                st.dataframe(display_df, width='stretch', hide_index=True, height=300)
    else:
        st.info(f"{selected_season}シーズンの半荘記録がありません。")
else:
    st.info(f"{selected_season}シーズンの半荘記録がありません。「🎮 半荘記録入力」ページで対局結果を記録してください。")
    conn.close()

st.markdown("---")
st.caption("※ データはサンプルです。実際のMリーグ公式記録とは異なる場合があります。")
