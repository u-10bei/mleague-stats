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

st.title("👤 選手管理")

# チーム情報を取得
teams_df = get_teams()
teams_display = get_teams_for_display()
team_options = {row["team_name"]: row["team_id"] for _, row in teams_display.iterrows()}

tab1, tab2, tab3, tab4 = st.tabs(["📝 選手登録", "✏️ 選手編集", "📊 成績入力", "📋 選手一覧"])

# ========== タブ1: 選手登録 ==========
with tab1:
    st.subheader("新規選手登録")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_player_name = st.text_input("選手名", key="new_player_name")
        new_birth_date = st.text_input("生年月日 (YYYY-MM-DD)", key="new_birth_date")
    
    with col2:
        new_pro_org = st.text_input("所属プロ団体", key="new_pro_org")
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
            edit_birth = st.text_input("生年月日", value=st.session_state.edit_birth_date, key=f"edit_birth_{edit_player_id}")
        
        with col2:
            edit_org = st.text_input("所属プロ団体", value=st.session_state.edit_pro_org, key=f"edit_org_{edit_player_id}")
        
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
        
        # 所属チーム管理
        st.subheader("所属チーム管理")
        
        player_teams_df = get_player_teams(edit_player_id)
        
        if not player_teams_df.empty:
            st.markdown("**所属履歴**")
            display_teams = player_teams_df[["season", "team_name"]].copy()
            display_teams.columns = ["シーズン", "チーム"]
            st.dataframe(display_teams, use_container_width=True, hide_index=True)
        
        st.markdown("**所属チーム追加/変更**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            team_season = st.number_input("シーズン", min_value=2018, max_value=2030, value=2024, key="team_season")
        
        with col2:
            team_select = st.selectbox("チーム", list(team_options.keys()), key="team_select")
            team_select_id = team_options[team_select]
        
        if st.button("所属を登録/更新", key="add_team_history"):
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id FROM player_teams WHERE player_id = ? AND season = ?",
                (edit_player_id, team_season)
            )
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute(
                    "UPDATE player_teams SET team_id = ? WHERE player_id = ? AND season = ?",
                    (team_select_id, edit_player_id, team_season)
                )
                st.success(f"{team_season}シーズンの所属チームを更新しました")
            else:
                cursor.execute(
                    "INSERT INTO player_teams (player_id, team_id, season) VALUES (?, ?, ?)",
                    (edit_player_id, team_select_id, team_season)
                )
                st.success(f"{team_season}シーズンの所属チームを登録しました")
            
            conn.commit()
            conn.close()
            st.rerun()
        
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

# ========== タブ3: 成績入力 ==========
with tab3:
    players_df = get_players()
    
    if players_df.empty:
        st.info("登録されている選手がいません")
    else:
        player_options = {row["player_name"]: row["player_id"] for _, row in players_df.iterrows()}
        
        st.subheader("選手シーズン成績入力")
        
        col1, col2 = st.columns(2)
        
        with col1:
            stats_player_name = st.selectbox("選手", list(player_options.keys()), key="stats_player")
            stats_player_id = player_options[stats_player_name]
        
        with col2:
            stats_season = st.number_input("シーズン", min_value=2018, max_value=2030, value=2024, key="stats_season")
        
        # 既存の成績を取得
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM player_season_stats WHERE player_id = ? AND season = ?",
            (stats_player_id, stats_season)
        )
        existing_stats = cursor.fetchone()
        conn.close()
        
        # デフォルト値の設定
        if existing_stats:
            default_games = existing_stats[3]
            default_points = existing_stats[4]
            default_1st = existing_stats[5]
            default_2nd = existing_stats[6]
            default_3rd = existing_stats[7]
            default_4th = existing_stats[8]
        else:
            default_games = 0
            default_points = 0.0
            default_1st = 0
            default_2nd = 0
            default_3rd = 0
            default_4th = 0
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            input_games = st.number_input("試合数", min_value=0, max_value=200, value=default_games, key="input_games")
            input_points = st.number_input("ポイント", min_value=-2000.0, max_value=2000.0, value=float(default_points), step=0.1, format="%.1f", key="input_points")
        
        with col2:
            input_1st = st.number_input("1着回数", min_value=0, max_value=200, value=default_1st, key="input_1st")
            input_2nd = st.number_input("2着回数", min_value=0, max_value=200, value=default_2nd, key="input_2nd")
        
        with col3:
            input_3rd = st.number_input("3着回数", min_value=0, max_value=200, value=default_3rd, key="input_3rd")
            input_4th = st.number_input("4着回数", min_value=0, max_value=200, value=default_4th, key="input_4th")
        
        if st.button("成績を登録/更新", key="save_stats"):
            conn = get_connection()
            cursor = conn.cursor()
            
            if existing_stats:
                cursor.execute("""
                    UPDATE player_season_stats 
                    SET games = ?, points = ?, rank_1st = ?, rank_2nd = ?, rank_3rd = ?, rank_4th = ?
                    WHERE player_id = ? AND season = ?
                """, (input_games, input_points, input_1st, input_2nd, input_3rd, input_4th, stats_player_id, stats_season))
                st.success(f"{stats_season}シーズンの成績を更新しました")
            else:
                cursor.execute("""
                    INSERT INTO player_season_stats (player_id, season, games, points, rank_1st, rank_2nd, rank_3rd, rank_4th)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (stats_player_id, stats_season, input_games, input_points, input_1st, input_2nd, input_3rd, input_4th))
                st.success(f"{stats_season}シーズンの成績を登録しました")
            
            conn.commit()
            conn.close()
        
        st.markdown("---")
        
        # 選手の成績履歴表示
        st.subheader("成績履歴")
        
        player_stats = get_player_season_stats(stats_player_id)
        
        if not player_stats.empty:
            display_stats = player_stats[["season", "team_name", "games", "points", "rank_1st", "rank_2nd", "rank_3rd", "rank_4th"]].copy()
            display_stats.columns = ["シーズン", "チーム", "試合", "ポイント", "1着", "2着", "3着", "4着"]
            display_stats["ポイント"] = display_stats["ポイント"].apply(lambda x: f"{x:+.1f}")
            st.dataframe(display_stats, use_container_width=True, hide_index=True)
        else:
            st.info("成績データがありません")

# ========== タブ4: 選手一覧 ==========
with tab4:
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
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.markdown(f"**登録選手数: {len(players_df)}名**")
