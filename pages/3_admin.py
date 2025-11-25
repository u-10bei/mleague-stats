import streamlit as st
import pandas as pd
import sys
sys.path.append("..")
from db import get_connection, get_season_data, hide_default_sidebar_navigation

st.set_page_config(
    page_title="データ管理 | Mリーグダッシュボード",
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
st.sidebar.markdown("### 👤 選手成績")
st.sidebar.page_link("pages/7_player_season_ranking.py", label="📊 年度別ランキング")
st.sidebar.page_link("pages/8_player_cumulative_ranking.py", label="🏆 累積ランキング")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/3_admin.py", label="⚙️ データ管理")
st.sidebar.page_link("pages/4_player_admin.py", label="👤 選手管理")
st.sidebar.page_link("pages/5_season_update.py", label="🔄 シーズン更新")
st.sidebar.page_link("pages/6_player_stats_input.py", label="📊 選手成績入力")

# メインページ
st.title("⚙️ データ管理")

st.markdown("""
このページでは、シーズン別のチームポイントを管理できます。
""")

# シーズン選択
# team_namesテーブルから全シーズンを取得（データ未入力のシーズンも選択可能に）
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT season FROM team_names ORDER BY season DESC")
seasons = [row[0] for row in cursor.fetchall()]
conn.close()

if not seasons:
    st.warning("シーズンデータがありません。")
    st.stop()

selected_season = st.selectbox("シーズンを選択", seasons)

st.markdown("---")

# そのシーズンに参加しているチーム情報を取得
conn = get_connection()
teams_query = f"""
SELECT t.team_id, tn.team_name
FROM teams t
JOIN team_names tn ON t.team_id = tn.team_id
WHERE tn.season = {selected_season}
ORDER BY t.team_id
"""
teams_df = pd.read_sql_query(teams_query, conn)
conn.close()

if teams_df.empty:
    st.warning(f"{selected_season}年度のチーム情報がありません。")
    st.stop()

# 既存データを取得
existing_data = get_season_data(selected_season)

# データ入力フォーム
st.subheader(f"{selected_season}年度 チームポイント入力")

with st.form("team_points_form"):
    updated_data = []
    
    for _, team in teams_df.iterrows():
        team_id = team["team_id"]
        team_name = team["team_name"]
        
        # 既存データから現在のポイントを取得
        current_point = 0
        if not existing_data.empty:
            existing_row = existing_data[existing_data["team_id"] == team_id]
            if not existing_row.empty:
                current_point = existing_row.iloc[0]["points"]
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**{team_name}**")
        with col2:
            point = st.number_input(
                f"{team_name}のポイント",
                value=float(current_point),
                step=0.1,
                format="%.1f",
                key=f"point_{team_id}",
                label_visibility="collapsed"
            )
            updated_data.append({
                "team_id": team_id,
                "team_name": team_name,
                "points": point
            })
    
    submitted = st.form_submit_button("💾 保存", type="primary")
    
    if submitted:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # ポイントでソートしてランクを計算
            sorted_data = sorted(updated_data, key=lambda x: x["points"], reverse=True)
            for rank, data in enumerate(sorted_data, start=1):
                cursor.execute("""
                    INSERT OR REPLACE INTO team_season_points (team_id, season, points, rank)
                    VALUES (?, ?, ?, ?)
                """, (data["team_id"], selected_season, data["points"], rank))
            
            conn.commit()
            conn.close()
            
            st.success("✅ データを保存しました")
            st.rerun()
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {e}")

# 現在のデータ表示
st.markdown("---")
st.subheader("現在のデータ")

if not existing_data.empty:
    # 表示用にカラムを選択
    display_data = existing_data[["team_name", "points"]].copy()
    display_data.columns = ["チーム名", "ポイント"]
    display_data = display_data.sort_values("ポイント", ascending=False).reset_index(drop=True)
    
    st.dataframe(display_data, width="stretch")
    
    # データ整合性チェック
    st.markdown("---")
    st.subheader("🔍 データ整合性チェック")
    
    total_points = display_data["ポイント"].sum()
    num_teams = len(display_data)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("参加チーム数", f"{num_teams}チーム")
    with col2:
        st.metric("合計ポイント", f"{total_points:,.1f}")
    with col3:
        # チームポイント制の合計は通常0になるはず（±が打ち消し合う）
        if abs(total_points) < 0.1:
            st.success("✅ 正常")
        elif abs(total_points) < 1.0:
            st.warning(f"⚠️ 誤差: {total_points:+.1f}")
        else:
            st.error(f"❌ 異常値: {total_points:+.1f}")
    
    # 詳細情報
    if abs(total_points) > 0.1:
        st.info("""
        **ℹ️ 注意事項**
        
        Mリーグのチームポイント制では、全チームの合計ポイントは通常0になります。
        合計がプラスまたはマイナスの場合、入力ミスの可能性があります。
        """)
else:
    st.info("このシーズンのデータはまだ入力されていません。")

# データ削除
st.markdown("---")
with st.expander("⚠️ 危険な操作（データ削除）"):
    st.warning("このシーズンのすべてのポイントデータを削除します。この操作は取り消せません。")
    
    if st.button("🗑️ このシーズンのデータをすべて削除", type="secondary"):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM team_season_points WHERE season = ?", (selected_season,))
            conn.commit()
            conn.close()
            
            st.success("✅ データを削除しました")
            st.rerun()
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {e}")
