import streamlit as st
import pandas as pd
from datetime import datetime, date
from db import get_connection, hide_default_sidebar_navigation

st.set_page_config(
    page_title="半荘記録入力 | Mリーグダッシュボード",
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
st.sidebar.page_link("pages/9_team_master_admin.py", label="🏢 チーム管理")
st.sidebar.page_link("pages/5_season_update.py", label="🔄 シーズン更新")
st.sidebar.page_link("pages/6_player_stats_input.py", label="📊 選手成績入力")
st.sidebar.page_link("pages/11_game_results_input.py", label="🎮 半荘記録入力")

st.title("🎮 半荘記録入力")

st.markdown("""
半荘ごとの詳細な対局結果を記録します。
- シーズン、日付、卓区分、対局番号を指定
- 4名の選手の席、獲得ポイント、順位を入力
- データ整合性を自動チェック
""")

# ========== シーズン選択 ==========
st.markdown("---")
st.subheader("📅 対局情報")

conn = get_connection()
cursor = conn.cursor()

# 利用可能なシーズンを取得
cursor.execute("SELECT DISTINCT season FROM player_teams ORDER BY season DESC")
seasons = [row[0] for row in cursor.fetchall()]

if not seasons:
    st.warning("シーズンデータがありません。先に「シーズン更新」でシーズンを作成してください。")
    conn.close()
    st.stop()

col1, col2, col3, col4 = st.columns(4)

with col1:
    selected_season = st.selectbox("シーズン", seasons, key="season_select")

with col2:
    game_date = st.date_input(
        "対局日",
        value=date.today(),
        key="game_date"
    )

with col3:
    table_types = ["レギュラー", "セミファイナル", "ファイナル", "その他"]
    table_type = st.selectbox("卓区分", table_types, key="table_type")

with col4:
    game_number = st.number_input(
        "対局番号",
        min_value=1,
        max_value=100,
        value=1,
        help="同じ日に複数対局がある場合の識別番号",
        key="game_number"
    )

# ========== 選手選択肢の取得 ==========
# そのシーズンに所属している選手のリストを取得
cursor.execute("""
    SELECT DISTINCT p.player_id, p.player_name, tn.team_name
    FROM players p
    JOIN player_teams pt ON p.player_id = pt.player_id
    JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
    WHERE pt.season = ?
    ORDER BY tn.team_name, p.player_name
""", (selected_season,))

players_data = cursor.fetchall()
conn.close()

if not players_data:
    st.warning(f"{selected_season}シーズンに所属している選手がいません。")
    st.stop()

# 選手リストを作成（チーム名付き）
player_options = {
    f"{row[1]} ({row[2]})": row[0]
    for row in players_data
}
player_display_names = list(player_options.keys())

# ========== 対局結果入力 ==========
st.markdown("---")
st.subheader("🎯 対局結果")

st.info("""
💡 **入力のポイント**
- 4名全員のデータを入力してください
- 席は東・南・西・北から選択
- 獲得ポイントの合計は0になるように入力
- 順位は1〜4で重複なし
""")

# 席の選択肢
seat_options = ["東", "南", "西", "北"]

# 4名分の入力フォーム
with st.form(f"game_results_form_{selected_season}_{game_date}_{game_number}"):
    st.markdown("### 対局者")
    
    # ヘッダー行
    header_cols = st.columns([1.5, 2.5, 1.5, 1.5])
    header_cols[0].markdown("**席**")
    header_cols[1].markdown("**選手名**")
    header_cols[2].markdown("**獲得pt**")
    header_cols[3].markdown("**順位**")
    
    # 4名分の入力行
    game_data = []
    
    for i in range(4):
        cols = st.columns([1.5, 2.5, 1.5, 1.5])
        
        with cols[0]:
            seat = st.selectbox(
                f"席{i+1}",
                seat_options,
                index=i,
                key=f"seat_{selected_season}_{game_date}_{game_number}_{i}",
                label_visibility="collapsed"
            )
        
        with cols[1]:
            player = st.selectbox(
                f"選手{i+1}",
                player_display_names,
                key=f"player_{selected_season}_{game_date}_{game_number}_{i}",
                label_visibility="collapsed"
            )
        
        with cols[2]:
            points = st.number_input(
                f"ポイント{i+1}",
                min_value=-100.0,
                max_value=100.0,
                value=0.0,
                step=0.1,
                format="%.1f",
                key=f"points_{selected_season}_{game_date}_{game_number}_{i}",
                label_visibility="collapsed"
            )
        
        with cols[3]:
            rank = st.number_input(
                f"順位{i+1}",
                min_value=1,
                max_value=4,
                value=i+1,
                key=f"rank_{selected_season}_{game_date}_{game_number}_{i}",
                label_visibility="collapsed"
            )
        
        game_data.append({
            'seat': seat,
            'player_name': player,
            'player_id': player_options[player],
            'points': points,
            'rank': rank
        })
    
    # データ検証
    st.markdown("---")
    st.markdown("### データチェック")
    
    col1, col2, col3 = st.columns(3)
    
    # ポイント合計のチェック
    total_points = sum(d['points'] for d in game_data)
    with col1:
        if abs(total_points) < 0.1:
            st.success(f"✅ ポイント合計: {total_points:.1f}")
        else:
            st.error(f"❌ ポイント合計: {total_points:.1f} (0でありません)")
    
    # 順位の重複チェック
    ranks = [d['rank'] for d in game_data]
    with col2:
        if len(ranks) == len(set(ranks)) and set(ranks) == {1, 2, 3, 4}:
            st.success("✅ 順位: 正常")
        else:
            st.error("❌ 順位: 重複または欠落があります")
    
    # 席の重複チェック
    seats = [d['seat'] for d in game_data]
    with col3:
        if len(seats) == len(set(seats)):
            st.success("✅ 席: 重複なし")
        else:
            st.error("❌ 席: 重複があります")
    
    # 選手の重複チェック
    player_ids = [d['player_id'] for d in game_data]
    if len(player_ids) != len(set(player_ids)):
        st.warning("⚠️ 同じ選手が複数回選択されています")
    
    # 保存ボタン
    st.markdown("---")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        submitted = st.form_submit_button("💾 保存", type="primary")
    
    with col2:
        st.caption("保存前にデータチェックの結果を確認してください")
    
    if submitted:
        # データ検証
        errors = []
        
        if abs(total_points) >= 0.1:
            errors.append("ポイント合計が0ではありません")
        
        if len(ranks) != len(set(ranks)) or set(ranks) != {1, 2, 3, 4}:
            errors.append("順位に重複または欠落があります")
        
        if len(seats) != len(set(seats)):
            errors.append("席に重複があります")
        
        if len(player_ids) != len(set(player_ids)):
            errors.append("同じ選手が複数回選択されています")
        
        if errors:
            st.error("❌ 以下のエラーがあります:")
            for error in errors:
                st.error(f"  • {error}")
        else:
            # データベースに保存
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # 同じ対局の既存データを削除（上書き保存）
                cursor.execute("""
                    DELETE FROM game_results
                    WHERE season = ? AND game_date = ? AND game_number = ?
                """, (selected_season, game_date.strftime("%Y-%m-%d"), game_number))
                
                # 新しいデータを挿入
                for data in game_data:
                    cursor.execute("""
                        INSERT INTO game_results 
                        (season, game_date, table_type, game_number, seat_name, player_id, points, rank)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        selected_season,
                        game_date.strftime("%Y-%m-%d"),
                        table_type,
                        game_number,
                        data['seat'],
                        data['player_id'],
                        data['points'],
                        data['rank']
                    ))
                
                conn.commit()
                conn.close()
                
                st.success("✅ 対局結果を保存しました")
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ 保存中にエラーが発生しました: {e}")

# ========== 登録済みデータの表示 ==========
st.markdown("---")
st.subheader("📋 登録済みデータ")

conn = get_connection()

# 最近の登録データを取得
recent_games_query = """
SELECT 
    gr.season,
    gr.game_date,
    gr.table_type,
    gr.game_number,
    COUNT(*) as player_count,
    GROUP_CONCAT(p.player_name || '(' || gr.rank || '位)') as players
FROM game_results gr
JOIN players p ON gr.player_id = p.player_id
WHERE gr.season = ?
GROUP BY gr.season, gr.game_date, gr.table_type, gr.game_number
ORDER BY gr.game_date DESC, gr.game_number DESC
LIMIT 20
"""

recent_df = pd.read_sql_query(recent_games_query, conn, params=(selected_season,))
conn.close()

if not recent_df.empty:
    st.dataframe(
        recent_df,
        column_config={
            "season": "シーズン",
            "game_date": "対局日",
            "table_type": "卓区分",
            "game_number": "対局番号",
            "player_count": "人数",
            "players": "対局者"
        },
        hide_index=True,
        use_container_width=True
    )
    
    # 統計情報
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(DISTINCT game_date, game_number) 
        FROM game_results 
        WHERE season = ?
    """, (selected_season,))
    total_games = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM game_results 
        WHERE season = ?
    """, (selected_season,))
    total_records = cursor.fetchone()[0]
    
    conn.close()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("登録済み対局数", f"{total_games}局")
    with col2:
        st.metric("総レコード数", f"{total_records}件")
else:
    st.info(f"ℹ️ {selected_season}シーズンの半荘記録はまだ登録されていません。")

# ========== データ削除 ==========
st.markdown("---")
with st.expander("⚠️ データ削除"):
    st.warning("指定した対局のデータを削除します。この操作は取り消せません。")
    
    del_col1, del_col2, del_col3, del_col4 = st.columns(4)
    
    with del_col1:
        del_date = st.date_input("削除する対局日", value=date.today(), key="del_date")
    
    with del_col2:
        del_number = st.number_input("削除する対局番号", min_value=1, value=1, key="del_number")
    
    with del_col3:
        st.write("")  # スペース
        st.write("")  # スペース
        
        if st.button("🗑️ 削除", type="secondary"):
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM game_results
                    WHERE season = ? AND game_date = ? AND game_number = ?
                """, (selected_season, del_date.strftime("%Y-%m-%d"), del_number))
                
                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()
                
                if deleted_count > 0:
                    st.success(f"✅ {deleted_count}件のレコードを削除しました")
                    st.rerun()
                else:
                    st.info("削除するデータがありませんでした")
                    
            except Exception as e:
                st.error(f"❌ 削除中にエラーが発生しました: {e}")
