import streamlit as st
import pandas as pd
import sys
sys.path.append("..")
from db import (get_connection, get_players, get_player, get_teams, 
                get_teams_for_display, get_current_team_name,
                get_player_teams, get_player_season_stats, get_seasons)

st.set_page_config(
    page_title="選手管理 | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide"
)

# サイドバーナビゲーション
st.sidebar.title("🀄 メニュー")
st.sidebar.page_link("app.py", label="🏠 トップページ")
st.sidebar.page_link("pages/1_season_ranking.py", label="📊 年度別ランキング")
st.sidebar.page_link("pages/2_cumulative_ranking.py", label="🏆 累積ランキング")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/3_admin.py", label="⚙️ データ管理")
st.sidebar.page_link("pages/4_player_admin.py", label="👤 選手管理")
st.sidebar.page_link("pages/5_season_update.py", label="🔄 シーズン更新")
st.sidebar.page_link("pages/6_player_stats_input.py", label="📊 選手成績入力")

st.title("👤 選手管理")

# チーム情報を取得
teams_df = get_teams()
teams_display = get_teams_for_display()
team_options = {row["team_name"]: row["team_id"] for _, row in teams_display.iterrows()}

tab1, tab2, tab3 = st.tabs(["📝 選手登録", "✏️ 選手編集", "📋 選手一覧"])

# ========== タブ1: 選手登録 ==========
with tab1:
    st.subheader("新規選手登録")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_player_name = st.text_input("選手名", key="new_player_name")
        new_birth_date = st.text_input(
            "生年月日 (YYYY-MM-DD)", 
            key="new_birth_date",
            placeholder="例: 1990-01-15",
            help="公表されていない場合は空欄でOKです"
        )
    
    with col2:
        new_pro_org = st.text_area(
            "所属プロ団体", 
            key="new_pro_org",
            height=100,
            placeholder="例: 日本プロ麻雀協会→最高位戦日本プロ麻雀協会(2020-)",
            help="移籍がある場合は「日本プロ麻雀協会→最高位戦日本プロ麻雀協会(2020-)」のように記入できます"
        )
        new_initial_season = st.number_input("初参加シーズン", min_value=2018, max_value=2030, value=2024, key="new_initial_season")
    
    new_initial_team = st.selectbox("初参加時の所属チーム", list(team_options.keys()), key="new_initial_team")
    new_initial_team_id = team_options[new_initial_team]
    
    if st.button("選手を登録", key="add_player"):
        if new_player_name:
            conn = get_connection()
            cursor = conn.cursor()
            
            # 選手マスター登録
            cursor.execute(
                "INSERT INTO players (player_name, birth_date, pro_org) VALUES (?, ?, ?)",
                (new_player_name, new_birth_date or None, new_pro_org or None)
            )
            player_id = cursor.lastrowid
            
            # 初期所属チーム登録
            cursor.execute(
                "INSERT INTO player_teams (player_id, team_id, season) VALUES (?, ?, ?)",
                (player_id, new_initial_team_id, new_initial_season)
            )
            
            # 初期成績レコード作成
            cursor.execute(
                "INSERT INTO player_season_stats (player_id, season) VALUES (?, ?)",
                (player_id, new_initial_season)
            )
            
            conn.commit()
            conn.close()
            st.success(f"選手「{new_player_name}」を登録しました")
        else:
            st.warning("選手名を入力してください")

# ========== タブ2: 選手編集 ==========
with tab2:
    players_df = get_players()
    
    if players_df.empty:
        st.info("登録されている選手がいません")
    else:
        player_options = {row["player_name"]: row["player_id"] for _, row in players_df.iterrows()}
        
        st.subheader("選手情報編集")
        
        edit_player_name = st.selectbox("編集する選手", list(player_options.keys()), key="edit_player")
        edit_player_id = player_options[edit_player_name]
        
        # 現在の選手情報を取得
        current_player = get_player(edit_player_id)
        
        # セッション状態の初期化
        if "last_edit_player_id" not in st.session_state:
            st.session_state.last_edit_player_id = None
        
        if st.session_state.last_edit_player_id != edit_player_id:
            st.session_state.last_edit_player_id = edit_player_id
            st.session_state.edit_player_name_val = current_player["player_name"]
            st.session_state.edit_birth_date = current_player["birth_date"] or ""
            st.session_state.edit_pro_org = current_player["pro_org"] or ""
        
        col1, col2 = st.columns(2)
        
        with col1:
            edit_name = st.text_input("選手名", value=st.session_state.edit_player_name_val, key=f"edit_name_{edit_player_id}")
            edit_birth = st.text_input(
                "生年月日 (YYYY-MM-DD)", 
                value=st.session_state.edit_birth_date, 
                key=f"edit_birth_{edit_player_id}",
                placeholder="例: 1990-01-15",
                help="公表されていない場合は空欄でOKです"
            )
        
        with col2:
            edit_org = st.text_area(
                "所属プロ団体", 
                value=st.session_state.edit_pro_org, 
                key=f"edit_org_{edit_player_id}",
                height=100,
                placeholder="例: 日本プロ麻雀協会→最高位戦日本プロ麻雀協会(2020-)",
                help="移籍がある場合は「日本プロ麻雀協会→最高位戦日本プロ麻雀協会(2020-)」のように記入できます"
            )
        
        if st.button("選手情報を更新", key="update_player"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE players SET player_name = ?, birth_date = ?, pro_org = ? WHERE player_id = ?",
                (edit_name, edit_birth or None, edit_org or None, edit_player_id)
            )
            conn.commit()
            conn.close()
            st.session_state.edit_player_name_val = edit_name
            st.session_state.edit_birth_date = edit_birth
            st.session_state.edit_pro_org = edit_org
            st.success("選手情報を更新しました")
            st.rerun()
        
        st.markdown("---")
        
        # 所属チーム履歴表示
        st.subheader("所属チーム履歴")
        
        player_teams_df = get_player_teams(edit_player_id)
        
        if not player_teams_df.empty:
            # 移籍履歴を分かりやすく表示
            display_history = []
            sorted_teams = player_teams_df.sort_values("season")
            
            for idx, row in sorted_teams.iterrows():
                if idx == 0:
                    # 初年度
                    display_history.append({
                        "シーズン": row["season"],
                        "移籍": "加入 (IN)",
                        "チーム": row["team_name"]
                    })
                else:
                    prev_row = sorted_teams.iloc[sorted_teams.index.get_loc(idx) - 1]
                    if prev_row["team_id"] != row["team_id"]:
                        # 移籍あり
                        display_history.append({
                            "シーズン": row["season"],
                            "移籍": f"OUT: {prev_row['team_name']} → IN: {row['team_name']}",
                            "チーム": row["team_name"]
                        })
                    else:
                        # 継続
                        display_history.append({
                            "シーズン": row["season"],
                            "移籍": "継続",
                            "チーム": row["team_name"]
                        })
            
            history_df = pd.DataFrame(display_history)
            st.dataframe(history_df, hide_index=True)
        else:
            st.info("所属履歴がありません")
        
        st.markdown("---")
        
        # 移籍入力
        st.subheader("移籍入力")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            transfer_season = st.number_input("移籍先シーズン", min_value=2018, max_value=2030, value=2024, key="transfer_season")
        
        with col2:
            # 前年度の所属チームを取得
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pt.team_id, tn.team_name 
                FROM player_teams pt
                JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
                WHERE pt.player_id = ? AND pt.season = ?
            """, (edit_player_id, transfer_season - 1))
            prev_team = cursor.fetchone()
            conn.close()
            
            if prev_team:
                out_team_display = f"OUT: {prev_team[1]}"
                st.text_input("離脱元チーム", value=prev_team[1], disabled=True, key="out_team_display")
            else:
                out_team_display = "新規加入"
                st.info("新規加入（前年度の所属なし）")
        
        with col3:
            in_team_name = st.selectbox("IN: 加入先チーム", list(team_options.keys()), key="in_team")
            in_team_id = team_options[in_team_name]
        
        if st.button("移籍を登録", key="add_transfer"):
            conn = get_connection()
            cursor = conn.cursor()
            
            # 既存データチェック
            cursor.execute(
                "SELECT id, team_id FROM player_teams WHERE player_id = ? AND season = ?",
                (edit_player_id, transfer_season)
            )
            existing = cursor.fetchone()
            
            if existing:
                if existing[1] == in_team_id:
                    st.warning(f"{transfer_season}シーズンは既に{in_team_name}に所属しています")
                else:
                    cursor.execute(
                        "UPDATE player_teams SET team_id = ? WHERE player_id = ? AND season = ?",
                        (in_team_id, edit_player_id, transfer_season)
                    )
                    conn.commit()
                    if prev_team:
                        st.success(f"{transfer_season}シーズン: {prev_team[1]} → {in_team_name} の移籍を登録しました")
                    else:
                        st.success(f"{transfer_season}シーズン: {in_team_name} への加入を登録しました")
                    st.rerun()
            else:
                cursor.execute(
                    "INSERT INTO player_teams (player_id, team_id, season) VALUES (?, ?, ?)",
                    (edit_player_id, in_team_id, transfer_season)
                )
                conn.commit()
                if prev_team:
                    st.success(f"{transfer_season}シーズン: {prev_team[1]} → {in_team_name} の移籍を登録しました")
                else:
                    st.success(f"{transfer_season}シーズン: {in_team_name} への加入を登録しました")
                st.rerun()
            
            conn.close()
        
        st.markdown("---")
        
        # 選手成績入力へのリンク
        st.info("💡 選手の成績を入力する場合は、[📊 選手成績入力](/6_player_stats_input)ページで一覧形式で入力できます。")
        
        st.markdown("---")
        
        # 選手削除
        st.subheader("選手削除")
        st.warning("⚠️ 選手を削除すると、関連するすべてのデータ（所属履歴、成績）も削除されます。")
        
        if st.button("この選手を削除", key="delete_player", type="secondary"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM players WHERE player_id = ?", (edit_player_id,))
            cursor.execute("DELETE FROM player_teams WHERE player_id = ?", (edit_player_id,))
            cursor.execute("DELETE FROM player_season_stats WHERE player_id = ?", (edit_player_id,))
            conn.commit()
            conn.close()
            st.success(f"選手「{edit_player_name}」を削除しました")
            st.rerun()

# ========== タブ3: 選手一覧 ==========
with tab3:
    st.subheader("登録選手一覧")
    
    players_df = get_players()
    
    if players_df.empty:
        st.info("登録されている選手がいません")
    else:
        # 選手一覧に最新所属チームを追加
        from db import get_player_current_team
        
        display_list = []
        for _, row in players_df.iterrows():
            team_id, team_name = get_player_current_team(row["player_id"])
            display_list.append({
                "選手名": row["player_name"],
                "所属チーム": team_name or "-",
                "プロ団体": row["pro_org"] or "-",
                "生年月日": row["birth_date"] or "-"
            })
        
        display_df = pd.DataFrame(display_list)
        st.dataframe(display_df, hide_index=True)
        
        st.markdown(f"**登録選手数: {len(players_df)}名**")
