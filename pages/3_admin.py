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
conn = get_connection()
existing_query = f"""
SELECT 
    sp.team_id,
    tn.team_name,
    sp.points,
    COALESCE(sp.penalty, 0) as penalty,
    sp.rank
FROM team_season_points sp
JOIN team_names tn ON sp.team_id = tn.team_id AND sp.season = tn.season
WHERE sp.season = {selected_season}
ORDER BY sp.rank
"""
existing_data = pd.read_sql_query(existing_query, conn)

# 既存データを辞書形式で保持（team_idをキーに）
existing_dict = {}
if not existing_data.empty:
    for _, row in existing_data.iterrows():
        existing_dict[row['team_id']] = {
            'points': float(row['points']),
            'penalty': float(row['penalty'])
        }

conn.close()

# データ入力フォーム
st.subheader(f"{selected_season}年度 チームポイント入力")

st.info("""
💡 **ペナルティについて**
- ペナルティは反則時に獲得ポイントから減算される値です
- マイナス値で入力してください（例: -10.0）
- 最終ポイント = 獲得ポイント - ペナルティ
""")

with st.form(f"team_points_form_{selected_season}"):
    updated_data = []
    
    for _, team in teams_df.iterrows():
        team_id = team["team_id"]
        team_name = team["team_name"]
        
        # 既存データから現在のポイントとペナルティを取得（デフォルト値として使用）
        if team_id in existing_dict:
            current_point = existing_dict[team_id]['points']
            current_penalty = existing_dict[team_id]['penalty']
        else:
            current_point = 0.0
            current_penalty = 0.0
        
        st.markdown(f"### {team_name}")
        
        # 既存データがある場合は表示
        if team_id in existing_dict:
            st.caption(f"💾 既存データ: 最終pt={current_point:+.1f}, ペナルティ={current_penalty:.1f}")
        
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            point = st.number_input(
                "最終ポイント",
                min_value=-2000.0,
                max_value=2000.0,
                value=float(current_point),
                step=0.1,
                format="%.1f",
                key=f"point_{selected_season}_{team_id}",
                help="ペナルティ適用後の最終ポイント"
            )
        
        with col2:
            penalty = st.number_input(
                "ペナルティ",
                min_value=-500.0,
                max_value=0.0,
                value=float(current_penalty),
                step=0.1,
                format="%.1f",
                key=f"penalty_{selected_season}_{team_id}",
                help="マイナス値で入力（例: -10.0）"
            )
        
        with col3:
            # 獲得ポイントを計算して表示
            earned_points = point - penalty  # penaltyは負の値なので、引くと実質加算
            st.metric(
                "獲得ポイント",
                f"{earned_points:+.1f}",
                help="最終ポイント - ペナルティ"
            )
        
        updated_data.append({
            "team_id": team_id,
            "team_name": team_name,
            "points": point,
            "penalty": penalty
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
                    INSERT OR REPLACE INTO team_season_points (team_id, season, points, penalty, rank)
                    VALUES (?, ?, ?, ?, ?)
                """, (data["team_id"], selected_season, data["points"], data["penalty"], rank))
            
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
    display_data = existing_data[["team_name", "points", "penalty"]].copy()
    
    # 獲得ポイントを計算
    display_data["earned_points"] = display_data["points"] - display_data["penalty"]
    
    # カラム名を変更
    display_data.columns = ["チーム名", "最終ポイント", "ペナルティ", "獲得ポイント"]
    
    # ソート
    display_data = display_data.sort_values("最終ポイント", ascending=False).reset_index(drop=True)
    
    # フォーマット
    display_data["最終ポイント"] = display_data["最終ポイント"].apply(lambda x: f"{x:+.1f}")
    display_data["ペナルティ"] = display_data["ペナルティ"].apply(lambda x: f"{x:.1f}" if x != 0 else "-")
    display_data["獲得ポイント"] = display_data["獲得ポイント"].apply(lambda x: f"{x:+.1f}")
    
    st.dataframe(display_data, width="stretch")
    
    # データ整合性チェック
    st.markdown("---")
    st.subheader("🔍 データ整合性チェック")
    
    # ペナルティを考慮した計算
    total_points = existing_data["points"].sum()
    total_penalty = existing_data["penalty"].sum()
    total_earned = total_points - total_penalty
    num_teams = len(existing_data)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("参加チーム数", f"{num_teams}チーム")
    with col2:
        st.metric("最終ポイント合計", f"{total_points:,.1f}")
    with col3:
        st.metric("ペナルティ合計", f"{total_penalty:,.1f}")
    with col4:
        st.metric("獲得ポイント合計", f"{total_earned:,.1f}")
    
    # 最終ポイントの合計チェック
    if abs(total_points) < 0.1:
        st.success("✅ 最終ポイント合計: 正常")
    elif abs(total_points) < 1.0:
        st.warning(f"⚠️ 最終ポイント合計に誤差: {total_points:+.1f}")
    else:
        st.error(f"❌ 最終ポイント合計が異常値: {total_points:+.1f}")
    
    # ペナルティがある場合の説明
    if total_penalty != 0:
        st.info(f"""
        **💡 ペナルティの影響**
        
        - 獲得ポイント合計: {total_earned:+.1f} pt
        - ペナルティ合計: {total_penalty:+.1f} pt
        - 最終ポイント合計: {total_points:+.1f} pt
        
        ペナルティがない場合、獲得ポイント合計は0になります。
        ペナルティがある場合、最終ポイント合計にペナルティ分が反映されます。
        """)
    else:
        st.info("""
        **ℹ️ 注意事項**
        
        Mリーグのチームポイント制では、全チームの最終ポイント合計は通常0になります。
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