import streamlit as st
import pandas as pd
import sys
sys.path.append("..")
from db import (
    get_connection, 
    get_players, 
    get_teams, 
    get_current_team_name,
    hide_default_sidebar_navigation
)

st.set_page_config(
    page_title="選手管理 | Mリーグダッシュボード",
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

# メインページ
st.title("👤 選手管理")

st.markdown("""
このページでは、選手情報を管理できます。
""")

# タブで機能を分ける
tab1, tab2, tab3 = st.tabs(["📋 選手一覧", "➕ 新規登録", "✏️ 編集・削除"])

# タブ1: 選手一覧
with tab1:
    st.subheader("登録済み選手一覧")
    
    players_df = get_players()
    
    if not players_df.empty:
        # 最新のチーム情報を取得
        conn = get_connection()
        team_query = """
        SELECT 
            p.player_id,
            p.player_name,
            p.birth_date,
            p.pro_org,
            COALESCE(t.team_name, '未所属') as team_name,
            pt.season
        FROM players p
        LEFT JOIN (
            SELECT player_id, team_id, season,
                   ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY season DESC) as rn
            FROM player_teams
        ) pt ON p.player_id = pt.player_id AND pt.rn = 1
        LEFT JOIN team_names t ON pt.team_id = t.team_id AND pt.season = t.season
        ORDER BY p.player_name
        """
        display_df = pd.read_sql_query(team_query, conn)
        conn.close()
        
        # カラム名を変更
        display_df.columns = ["player_id", "選手名", "生年月日", "所属団体", "所属チーム", "season"]
        
        # 生年月日のフォーマット
        display_df["生年月日"] = display_df["生年月日"].fillna("-")
        display_df["所属団体"] = display_df["所属団体"].fillna("-")
        
        # 表示用に選択
        display_df = display_df[["選手名", "生年月日", "所属団体", "所属チーム"]]
        
        # フィルター
        col1, col2, col3 = st.columns(3)
        with col1:
            team_filter = st.multiselect(
                "チームでフィルター",
                options=sorted(display_df["所属チーム"].unique()),
                default=None
            )
        with col2:
            org_filter = st.multiselect(
                "所属団体でフィルター",
                options=sorted([x for x in display_df["所属団体"].unique() if x != "-"]),
                default=None
            )
        
        # フィルター適用
        filtered_df = display_df.copy()
        if team_filter:
            filtered_df = filtered_df[filtered_df["所属チーム"].isin(team_filter)]
        if org_filter:
            filtered_df = filtered_df[filtered_df["所属団体"].isin(org_filter)]
        
        st.dataframe(
            filtered_df.reset_index(drop=True),
            width="stretch",
            height=400
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("登録選手数", f"{len(players_df)}名")
        with col2:
            with_birthdate = len([x for x in players_df["birth_date"] if pd.notna(x)])
            st.metric("生年月日登録", f"{with_birthdate}名")
        with col3:
            with_org = len([x for x in players_df["pro_org"] if pd.notna(x)])
            st.metric("所属団体登録", f"{with_org}名")
    else:
        st.info("まだ選手が登録されていません。")

# タブ2: 新規登録
with tab2:
    st.subheader("新しい選手を登録")
    
    teams_df = get_teams()
    
    # 現在のシーズンを取得
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(season) FROM team_names")
    current_season = cursor.fetchone()[0]
    conn.close()
    
    if current_season is None:
        st.error("シーズンデータがありません。先にシーズンを追加してください。")
    else:
        # チームオプションを作成
        team_names_query = f"""
        SELECT team_id, team_name 
        FROM team_names 
        WHERE season = {current_season}
        ORDER BY team_name
        """
        conn = get_connection()
        team_names_df = pd.read_sql_query(team_names_query, conn)
        conn.close()
        
        team_options = dict(zip(team_names_df["team_name"], team_names_df["team_id"]))
        
        with st.form("add_player_form"):
            player_name = st.text_input("選手名（フルネーム）", placeholder="例: 多井隆晴")
            
            col1, col2 = st.columns(2)
            
            with col1:
                birth_date = st.date_input(
                    "生年月日",
                    value=None,
                    min_value=pd.Timestamp("1950-01-01"),
                    max_value=pd.Timestamp("2010-12-31"),
                    help="選手の生年月日を選択してください（オプション）",
                    format="YYYY/MM/DD"
                )
            
            with col2:
                pro_org = st.text_input(
                    "所属団体",
                    placeholder="例: 日本プロ麻雀協会",
                    help="選手の所属するプロ団体を入力してください（オプション）"
                )
                st.caption("💡 主な団体: 日本プロ麻雀協会、日本プロ麻雀連盟、最高位戦日本プロ麻雀協会、RMU、麻将連合")
            
            selected_team_name = st.selectbox("所属チーム", options=list(team_options.keys()))
            team_id = team_options[selected_team_name]
            
            season = st.number_input(
                "所属開始シーズン",
                value=current_season,
                min_value=2018,
                max_value=2030,
                step=1
            )
            
            submit = st.form_submit_button("➕ 登録", type="primary")
            
            if submit:
                if not player_name.strip():
                    st.error("❌ 選手名を入力してください")
                else:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        
                        # 重複チェック
                        cursor.execute(
                            "SELECT player_id FROM players WHERE player_name = ?",
                            (player_name.strip(),)
                        )
                        if cursor.fetchone():
                            st.error(f"❌ {player_name} は既に登録されています")
                        else:
                            # birth_dateとpro_orgの処理
                            birth_date_str = birth_date.strftime("%Y-%m-%d") if birth_date else None
                            pro_org_str = pro_org.strip() if pro_org.strip() else None
                            
                            # 選手を登録
                            cursor.execute("""
                                INSERT INTO players (player_name, birth_date, pro_org)
                                VALUES (?, ?, ?)
                            """, (player_name.strip(), birth_date_str, pro_org_str))
                            
                            player_id = cursor.lastrowid
                            
                            # チーム所属を登録
                            cursor.execute("""
                                INSERT INTO player_teams (player_id, team_id, season)
                                VALUES (?, ?, ?)
                            """, (player_id, team_id, season))
                            
                            conn.commit()
                            st.success(f"✅ {player_name} を登録しました")
                            st.rerun()
                        
                        conn.close()
                    except Exception as e:
                        st.error(f"❌ エラーが発生しました: {e}")

# タブ3: 編集・削除
with tab3:
    st.subheader("選手情報の編集・削除")
    
    players_df = get_players()
    
    if not players_df.empty:
        # 選手名と最新のチーム名を取得
        conn = get_connection()
        player_team_query = """
        SELECT 
            p.player_id,
            p.player_name,
            p.birth_date,
            p.pro_org,
            COALESCE(t.team_name, '未所属') as team_name
        FROM players p
        LEFT JOIN (
            SELECT player_id, team_id, season,
                   ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY season DESC) as rn
            FROM player_teams
        ) pt ON p.player_id = pt.player_id AND pt.rn = 1
        LEFT JOIN team_names t ON pt.team_id = t.team_id AND pt.season = t.season
        ORDER BY p.player_name
        """
        player_display_df = pd.read_sql_query(player_team_query, conn)
        conn.close()
        
        player_display_df["display_name"] = player_display_df["player_name"] + " (" + player_display_df["team_name"] + ")"
        player_options = dict(zip(player_display_df["display_name"], player_display_df["player_id"]))
        
        selected_player_display = st.selectbox(
            "編集する選手を選択",
            options=list(player_options.keys())
        )
        
        if selected_player_display:
            selected_player_id = player_options[selected_player_display]
            player_data = player_display_df[player_display_df["player_id"] == selected_player_id].iloc[0]
            
            st.markdown("---")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader("✏️ 選手情報を編集")
                
                with st.form("edit_player_info_form"):
                    st.markdown("#### 基本情報")
                    
                    new_player_name = st.text_input(
                        "選手名",
                        value=player_data["player_name"]
                    )
                    
                    edit_col1, edit_col2 = st.columns(2)
                    
                    with edit_col1:
                        # 既存の生年月日があればそれを使用
                        current_birth_date = None
                        if pd.notna(player_data["birth_date"]) and player_data["birth_date"]:
                            try:
                                current_birth_date = pd.to_datetime(player_data["birth_date"]).date()
                            except:
                                pass
                        
                        new_birth_date = st.date_input(
                            "生年月日",
                            value=current_birth_date,
                            min_value=pd.Timestamp("1950-01-01"),
                            max_value=pd.Timestamp("2010-12-31"),
                            help="選手の生年月日を選択してください（オプション）",
                            format="YYYY/MM/DD"
                        )
                    
                    with edit_col2:
                        # 既存の所属団体があればそれを使用
                        current_pro_org = ""
                        if pd.notna(player_data["pro_org"]) and player_data["pro_org"]:
                            current_pro_org = player_data["pro_org"]
                        
                        new_pro_org = st.text_input(
                            "所属団体",
                            value=current_pro_org,
                            placeholder="例: 日本プロ麻雀協会",
                            help="選手の所属するプロ団体を入力してください（オプション）"
                        )
                        st.caption("💡 主な団体: 日本プロ麻雀協会、日本プロ麻雀連盟、最高位戦日本プロ麻雀協会、RMU、麻将連合")
                    
                    update_info = st.form_submit_button("💾 基本情報を更新", type="primary")
                    
                    if update_info:
                        if not new_player_name.strip():
                            st.error("❌ 選手名を入力してください")
                        else:
                            try:
                                conn = get_connection()
                                cursor = conn.cursor()
                                
                                # 重複チェック（自分以外）
                                cursor.execute(
                                    "SELECT player_id FROM players WHERE player_name = ? AND player_id != ?",
                                    (new_player_name.strip(), selected_player_id)
                                )
                                if cursor.fetchone():
                                    st.error(f"❌ {new_player_name} は既に登録されています")
                                else:
                                    # birth_dateとpro_orgの処理
                                    new_birth_date_str = new_birth_date.strftime("%Y-%m-%d") if new_birth_date else None
                                    new_pro_org_str = new_pro_org.strip() if new_pro_org.strip() else None
                                    
                                    # 選手情報を更新
                                    cursor.execute("""
                                        UPDATE players 
                                        SET player_name = ?, birth_date = ?, pro_org = ?
                                        WHERE player_id = ?
                                    """, (new_player_name.strip(), new_birth_date_str, new_pro_org_str, selected_player_id))
                                    
                                    conn.commit()
                                    st.success(f"✅ {new_player_name} の情報を更新しました")
                                    st.rerun()
                                
                                conn.close()
                            except Exception as e:
                                st.error(f"❌ エラーが発生しました: {e}")
                
                st.markdown("---")
                st.markdown("#### チーム所属を変更")
                
                # 現在のシーズンを取得
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(season) FROM team_names")
                current_season = cursor.fetchone()[0]
                conn.close()
                
                if current_season:
                    # チームオプションを作成
                    team_names_query = f"""
                    SELECT team_id, team_name 
                    FROM team_names 
                    WHERE season = {current_season}
                    ORDER BY team_name
                    """
                    conn = get_connection()
                    team_names_df = pd.read_sql_query(team_names_query, conn)
                    conn.close()
                    
                    team_options = dict(zip(team_names_df["team_name"], team_names_df["team_id"]))
                    
                    with st.form("edit_player_team_form"):
                        new_team_name = st.selectbox(
                            "新しい所属チーム",
                            options=list(team_options.keys())
                        )
                        new_team_id = team_options[new_team_name]
                        
                        season = st.number_input(
                            "シーズン",
                            value=current_season,
                            min_value=2018,
                            max_value=2030,
                            step=1
                        )
                        
                        update_team = st.form_submit_button("💾 チーム所属を更新", type="primary")
                        
                        if update_team:
                            try:
                                conn = get_connection()
                                cursor = conn.cursor()
                                
                                # チーム所属を更新（既存レコードがあれば更新、なければ挿入）
                                cursor.execute("""
                                    INSERT OR REPLACE INTO player_teams (player_id, team_id, season)
                                    VALUES (?, ?, ?)
                                """, (selected_player_id, new_team_id, season))
                                
                                conn.commit()
                                conn.close()
                                
                                st.success(f"✅ {player_data['player_name']} のチーム所属を更新しました")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ エラーが発生しました: {e}")
            
            with col2:
                st.subheader("🗑️ 削除")
                st.warning("この操作は取り消せません")
                
                if st.button("削除", type="secondary"):
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        
                        # 選手の成績データも確認
                        cursor.execute(
                            "SELECT COUNT(*) FROM player_season_stats WHERE player_id = ?",
                            (selected_player_id,)
                        )
                        stats_count = cursor.fetchone()[0]
                        
                        if stats_count > 0:
                            st.error(f"❌ この選手には{stats_count}件の成績データがあります。先に成績データを削除してください。")
                        else:
                            # player_teamsも削除される（CASCADE）
                            cursor.execute(
                                "DELETE FROM players WHERE player_id = ?",
                                (selected_player_id,)
                            )
                            conn.commit()
                            st.success(f"✅ {player_data['player_name']} を削除しました")
                            st.rerun()
                        
                        conn.close()
                    except Exception as e:
                        st.error(f"❌ エラーが発生しました: {e}")
    else:
        st.info("選手が登録されていません。")

# データベース情報
st.markdown("---")
with st.expander("📊 データベース統計"):
    players_df = get_players()
    
    if not players_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_players = len(players_df)
            st.metric("総選手数", f"{total_players}名")
        
        with col2:
            # 現在活動中の選手数（最新シーズンに所属がある選手）
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(DISTINCT player_id) 
                FROM player_teams 
                WHERE season = (SELECT MAX(season) FROM player_teams)
            """)
            active_count = cursor.fetchone()[0]
            conn.close()
            st.metric("現役選手", f"{active_count}名")
        
        with col3:
            with_birthdate = len([x for x in players_df["birth_date"] if pd.notna(x)])
            st.metric("生年月日登録", f"{with_birthdate}名")
        
        with col4:
            with_org = len([x for x in players_df["pro_org"] if pd.notna(x)])
            st.metric("所属団体登録", f"{with_org}名")
        
        # チーム別の選手数
        st.markdown("### チーム別選手数（最新シーズン）")
        conn = get_connection()
        team_stats_query = """
        SELECT 
            t.team_name,
            COUNT(DISTINCT pt.player_id) as count
        FROM team_names t
        LEFT JOIN player_teams pt ON t.team_id = pt.team_id AND t.season = pt.season
        WHERE t.season = (SELECT MAX(season) FROM team_names)
        GROUP BY t.team_name
        ORDER BY count DESC, t.team_name
        """
        team_counts = pd.read_sql_query(team_stats_query, conn)
        conn.close()
        team_counts.columns = ["チーム名", "選手数"]
        
        st.dataframe(team_counts, width="stretch", hide_index=True)
        
        # 所属団体別の選手数
        st.markdown("### 所属団体別選手数")
        org_counts = players_df["pro_org"].value_counts().reset_index()
        org_counts.columns = ["所属団体", "選手数"]
        org_counts["所属団体"] = org_counts["所属団体"].fillna("未登録")
        
        st.dataframe(org_counts, width="stretch", hide_index=True)
    else:
        st.info("データがありません")