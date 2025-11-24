import streamlit as st
import pandas as pd
import sys
sys.path.append("..")
from db import (get_connection, get_teams, get_season_points, get_seasons, 
                get_teams_for_display, get_all_team_names, get_current_team_name)

st.set_page_config(
    page_title="データ管理 | Mリーグダッシュボード",
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

st.title("⚙️ データ管理")

tab1, tab2, tab3, tab4 = st.tabs(["📝 シーズンポイント入力", "🏷️ チーム名管理", "🏢 チーム管理", "📋 データ確認"])

# チーム情報を取得
teams_df = get_teams()
teams_display = get_teams_for_display()
team_options = {row["team_name"]: row["team_id"] for _, row in teams_display.iterrows()}

# ========== タブ1: シーズンポイント入力 ==========
with tab1:
    st.subheader("シーズンポイント入力")
    
    col1, col2 = st.columns(2)
    
    with col1:
        input_season = st.number_input("シーズン（年）", min_value=2018, max_value=2030, value=2024)
        input_team_name = st.selectbox("チーム", list(team_options.keys()))
        input_team_id = team_options[input_team_name]
    
    with col2:
        input_points = st.number_input("ポイント", min_value=-1000.0, max_value=1000.0, value=0.0, step=0.1)
        input_rank = st.number_input("順位", min_value=1, max_value=10, value=1)
    
    if st.button("登録", key="add_season_point"):
        conn = get_connection()
        cursor = conn.cursor()
        
        # 既存データチェック
        cursor.execute(
            "SELECT id FROM team_season_points WHERE season = ? AND team_id = ?",
            (input_season, input_team_id)
        )
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute(
                "UPDATE team_season_points SET points = ?, rank = ? WHERE season = ? AND team_id = ?",
                (input_points, input_rank, input_season, input_team_id)
            )
            st.success(f"{input_season}シーズン {input_team_name} のデータを更新しました")
        else:
            cursor.execute(
                "INSERT INTO team_season_points (season, team_id, points, rank) VALUES (?, ?, ?, ?)",
                (input_season, input_team_id, input_points, input_rank)
            )
            st.success(f"{input_season}シーズン {input_team_name} のデータを登録しました")
        
        conn.commit()
        conn.close()
    
    st.markdown("---")
    
    # 一括入力フォーム
    st.subheader("シーズン一括入力")
    
    bulk_season = st.number_input("一括入力するシーズン（年）", min_value=2018, max_value=2030, value=2024, key="bulk_season")
    
    st.markdown("各チームのポイントと順位を入力してください：")
    
    bulk_data = []
    cols = st.columns(2)
    
    for idx, (team_name, team_id) in enumerate(team_options.items()):
        with cols[idx % 2]:
            with st.expander(team_name):
                pts = st.number_input(f"ポイント", min_value=-1000.0, max_value=1000.0, value=0.0, step=0.1, key=f"bulk_pts_{team_id}")
                rnk = st.number_input(f"順位", min_value=1, max_value=10, value=idx+1, key=f"bulk_rnk_{team_id}")
                bulk_data.append({"team_id": team_id, "team_name": team_name, "points": pts, "rank": rnk})
    
    if st.button("一括登録", key="bulk_add"):
        conn = get_connection()
        cursor = conn.cursor()
        
        for data in bulk_data:
            cursor.execute(
                "SELECT id FROM team_season_points WHERE season = ? AND team_id = ?",
                (bulk_season, data["team_id"])
            )
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute(
                    "UPDATE team_season_points SET points = ?, rank = ? WHERE season = ? AND team_id = ?",
                    (data["points"], data["rank"], bulk_season, data["team_id"])
                )
            else:
                cursor.execute(
                    "INSERT INTO team_season_points (season, team_id, points, rank) VALUES (?, ?, ?, ?)",
                    (bulk_season, data["team_id"], data["points"], data["rank"])
                )
        
        conn.commit()
        conn.close()
        st.success(f"{bulk_season}シーズンのデータを一括登録しました")

# ========== タブ2: チーム名管理 ==========
with tab2:
    st.subheader("シーズン別チーム名設定")
    st.markdown("チーム名が変更された場合、ここで各シーズンのチーム名を設定できます。")
    
    col1, col2 = st.columns(2)
    
    with col1:
        name_team_name = st.selectbox("チーム", list(team_options.keys()), key="name_team")
        name_team_id = team_options[name_team_name]
    
    with col2:
        name_season = st.number_input("シーズン（年）", min_value=2018, max_value=2030, value=2024, key="name_season")
    
    new_team_name = st.text_input("このシーズンのチーム名", value=name_team_name)
    
    if st.button("チーム名を登録", key="add_team_name"):
        if new_team_name:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id FROM team_names WHERE team_id = ? AND season = ?",
                (name_team_id, name_season)
            )
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute(
                    "UPDATE team_names SET team_name = ? WHERE team_id = ? AND season = ?",
                    (new_team_name, name_team_id, name_season)
                )
                st.success(f"{name_season}シーズンのチーム名を更新しました")
            else:
                cursor.execute(
                    "INSERT INTO team_names (team_id, season, team_name) VALUES (?, ?, ?)",
                    (name_team_id, name_season, new_team_name)
                )
                st.success(f"{name_season}シーズンのチーム名を登録しました")
            
            conn.commit()
            conn.close()
        else:
            st.warning("チーム名を入力してください")
    
    st.markdown("---")
    st.subheader("チーム名履歴")
    
    all_names = get_all_team_names()
    if not all_names.empty:
        # チームごとにグループ化して表示
        for team_id in all_names["team_id"].unique():
            team_data = all_names[all_names["team_id"] == team_id]
            current_name = get_current_team_name(team_id)
            
            with st.expander(f"{current_name} (ID: {team_id})"):
                display = team_data[["season", "team_name"]].copy()
                display.columns = ["シーズン", "チーム名"]
                st.dataframe(display, use_container_width=True, hide_index=True)

# ========== タブ3: チーム管理 ==========
with tab3:
    st.subheader("チーム追加")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_short_name = st.text_input("略称")
    
    with col2:
        new_color = st.color_picker("チームカラー", "#000000")
        new_established = st.number_input("設立年", min_value=2018, max_value=2030, value=2024)
    
    new_initial_name = st.text_input("初期チーム名（正式名称）")
    
    if st.button("チーム追加", key="add_team"):
        if new_short_name and new_initial_name:
            conn = get_connection()
            cursor = conn.cursor()
            
            # 新しいteam_idを取得
            cursor.execute("SELECT MAX(team_id) FROM teams")
            max_id = cursor.fetchone()[0] or 0
            new_team_id = max_id + 1
            
            # チームマスター追加
            cursor.execute(
                "INSERT INTO teams (team_id, short_name, color, established) VALUES (?, ?, ?, ?)",
                (new_team_id, new_short_name, new_color, new_established)
            )
            
            # 初期チーム名を登録
            cursor.execute(
                "INSERT INTO team_names (team_id, season, team_name) VALUES (?, ?, ?)",
                (new_team_id, new_established, new_initial_name)
            )
            
            conn.commit()
            conn.close()
            st.success(f"チーム「{new_initial_name}」を追加しました")
            st.rerun()
        else:
            st.warning("略称と初期チーム名を入力してください")
    
    st.markdown("---")
    
    # チーム一覧
    st.subheader("登録チーム一覧")
    
    teams_display = get_teams_for_display()
    st.dataframe(teams_display, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    st.subheader("チーム削除")
    delete_team_name = st.selectbox("削除するチーム", list(team_options.keys()), key="delete_team")
    delete_team_id = team_options[delete_team_name]
    
    st.warning("⚠️ チームを削除すると、関連するすべてのデータ（チーム名履歴、シーズンポイント）も削除されます。")
    
    if st.button("削除", key="del_team", type="secondary"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM teams WHERE team_id = ?", (delete_team_id,))
        cursor.execute("DELETE FROM team_names WHERE team_id = ?", (delete_team_id,))
        cursor.execute("DELETE FROM team_season_points WHERE team_id = ?", (delete_team_id,))
        conn.commit()
        conn.close()
        st.success(f"チーム「{delete_team_name}」を削除しました")
        st.rerun()

# ========== タブ4: データ確認 ==========
with tab4:
    st.subheader("シーズンポイントデータ")
    
    season_df = get_season_points()
    seasons = get_seasons()
    
    if seasons:
        filter_season = st.selectbox("シーズンで絞り込み", ["すべて"] + seasons, key="filter_season")
        
        if filter_season != "すべて":
            display_df = season_df[season_df["season"] == filter_season]
        else:
            display_df = season_df
        
        display_df = display_df.sort_values(["season", "rank"], ascending=[False, True])
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # データ削除
        st.subheader("データ削除")
        
        col1, col2 = st.columns(2)
        
        with col1:
            del_season = st.selectbox("シーズン", seasons, key="del_season")
        
        with col2:
            del_team_name = st.selectbox("チーム", list(team_options.keys()), key="del_team_data")
            del_team_id = team_options[del_team_name]
        
        if st.button("このデータを削除", key="del_data", type="secondary"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM team_season_points WHERE season = ? AND team_id = ?",
                (del_season, del_team_id)
            )
            conn.commit()
            conn.close()
            st.success(f"{del_season}シーズン {del_team_name} のデータを削除しました")
            st.rerun()
    else:
        st.info("シーズンデータがありません")
