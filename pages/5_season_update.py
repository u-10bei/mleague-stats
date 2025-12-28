import streamlit as st
import pandas as pd
from db import get_connection, hide_default_sidebar_navigation

st.set_page_config(page_title="シーズン更新", page_icon="🔄", layout="wide")

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

st.title("🔄 シーズン更新処理")

st.markdown("""
新シーズン開始時の更新作業を一括で行います：
- **チーム名変更**: 新シーズンのチーム名を設定
- **選手移籍**: 残留・移籍・退団を一括登録
""")

# ========== 新シーズン番号入力 ==========
st.markdown("---")
st.subheader("📅 新シーズン設定")

col1, col2 = st.columns([1, 3])
with col1:
    new_season = st.number_input(
        "新シーズン", 
        min_value=2018, 
        max_value=2030, 
        value=2025,
        help="更新する新しいシーズンの年度を入力してください"
    )

with col2:
    st.info(f"💡 {new_season}シーズンの情報を登録します。前シーズン（{new_season-1}）のデータを元に更新できます。")

# 前シーズンが存在するか確認
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM team_names WHERE season = ?", (new_season - 1,))
prev_season_exists = cursor.fetchone()[0] > 0
conn.close()

if not prev_season_exists:
    st.warning(f"⚠️ {new_season-1}シーズンのデータが存在しません。先にデータを登録してください。")
    st.stop()

# ========== タブ構成 ==========
tab1, tab2, tab3 = st.tabs(["🏷️ チーム名設定", "👥 選手移籍入力", "✅ 確認と登録"])

# セッション状態の初期化
if "season_update_team_names" not in st.session_state:
    st.session_state.season_update_team_names = {}
if "season_update_player_moves" not in st.session_state:
    st.session_state.season_update_player_moves = {}
if "season_update_confirmed" not in st.session_state:
    st.session_state.season_update_confirmed = False

# ========== タブ1: チーム名設定 ==========
with tab1:
    st.subheader(f"🏷️ {new_season}シーズンのチーム名設定")
    st.markdown(f"前シーズン（{new_season-1}）のチーム名がデフォルトで表示されます。変更がある場合のみ編集してください。")
    
    # 前シーズンのチーム名を取得
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.team_id, t.short_name, tn.team_name
        FROM teams t
        JOIN team_names tn ON t.team_id = tn.team_id
        WHERE tn.season = ?
        ORDER BY t.team_id
    """, (new_season - 1,))
    prev_teams = cursor.fetchall()
    conn.close()
    
    st.markdown("---")
    
    # チーム名入力フォーム
    team_name_changes = {}
    
    for team_id, short_name, prev_name in prev_teams:
        col1, col2, col3 = st.columns([1, 2, 2])
        
        with col1:
            st.write(f"**{short_name}**")
        
        with col2:
            st.text_input(
                "前シーズン", 
                value=prev_name, 
                disabled=True,
                key=f"prev_name_{team_id}",
                label_visibility="collapsed"
            )
        
        with col3:
            # セッション状態に保存されている値があればそれを使用、なければ前シーズンの名前
            default_value = st.session_state.season_update_team_names.get(team_id, prev_name)
            new_name = st.text_input(
                f"{new_season}シーズン",
                value=default_value,
                key=f"new_name_{team_id}",
                placeholder=f"例: {prev_name}",
                label_visibility="collapsed"
            )
            team_name_changes[team_id] = new_name
    
    # チーム名をセッション状態に保存
    if st.button("チーム名を保存", key="save_team_names", type="primary"):
        st.session_state.season_update_team_names = team_name_changes
        st.success("✅ チーム名を保存しました。次のタブで選手移籍を入力してください。")
        st.rerun()
    
    # 保存済みの場合は表示
    if st.session_state.season_update_team_names:
        st.markdown("---")
        st.success("✅ チーム名は保存済みです")

# ========== タブ2: 選手移籍入力 ==========
with tab2:
    st.subheader(f"👥 {new_season}シーズンの選手移籍入力")
    
    if not st.session_state.season_update_team_names:
        st.warning("⚠️ 先に「チーム名設定」タブでチーム名を保存してください。")
    else:
        st.markdown(f"前シーズン（{new_season-1}）所属の選手について、残留・移籍・退団を選択してください。")
        
        # 前シーズンの選手所属情報を取得
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.player_id, p.player_name, pt.team_id, t.short_name, tn.team_name
            FROM players p
            JOIN player_teams pt ON p.player_id = pt.player_id
            JOIN teams t ON pt.team_id = t.team_id
            JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
            WHERE pt.season = ?
            ORDER BY t.team_id, p.player_name
        """, (new_season - 1,))
        prev_players = cursor.fetchall()
        
        # チーム選択肢を取得
        cursor.execute("SELECT team_id, short_name FROM teams ORDER BY team_id")
        team_options = {row[1]: row[0] for row in cursor.fetchall()}
        conn.close()
        
        if not prev_players:
            st.info(f"ℹ️ {new_season-1}シーズンに所属選手が登録されていません。")
        else:
            st.markdown("---")
            
            # チームごとにグループ化して表示
            current_team = None
            player_moves = {}
            
            for player_id, player_name, team_id, short_name, team_name in prev_players:
                # 新しいチームの場合はヘッダーを表示
                if current_team != team_id:
                    if current_team is not None:
                        st.markdown("---")
                    st.markdown(f"### 📋 {short_name} ({team_name})")
                    current_team = team_id
                
                col1, col2, col3 = st.columns([2, 2, 3])
                
                with col1:
                    st.write(f"**{player_name}**")
                
                with col2:
                    # セッション状態から前回の選択を取得
                    prev_status = st.session_state.season_update_player_moves.get(player_id, {}).get("status", "残留")
                    status = st.selectbox(
                        "状態",
                        ["残留", "移籍", "退団"],
                        index=["残留", "移籍", "退団"].index(prev_status),
                        key=f"status_{player_id}",
                        label_visibility="collapsed"
                    )
                
                with col3:
                    if status == "移籍":
                        # セッション状態から前回の選択を取得
                        prev_new_team = st.session_state.season_update_player_moves.get(player_id, {}).get("new_team_id")
                        prev_new_team_name = None
                        if prev_new_team:
                            for name, tid in team_options.items():
                                if tid == prev_new_team:
                                    prev_new_team_name = name
                                    break
                        
                        new_team_name = st.selectbox(
                            "移籍先",
                            list(team_options.keys()),
                            index=list(team_options.keys()).index(prev_new_team_name) if prev_new_team_name else 0,
                            key=f"new_team_{player_id}",
                            label_visibility="collapsed"
                        )
                        new_team_id = team_options[new_team_name]
                        player_moves[player_id] = {
                            "player_name": player_name,
                            "prev_team_id": team_id,
                            "prev_team_name": short_name,
                            "status": status,
                            "new_team_id": new_team_id,
                            "new_team_name": new_team_name
                        }
                    else:
                        if status == "残留":
                            st.text_input(
                                "継続",
                                value=f"{short_name} で継続",
                                disabled=True,
                                key=f"stay_{player_id}",
                                label_visibility="collapsed"
                            )
                            player_moves[player_id] = {
                                "player_name": player_name,
                                "prev_team_id": team_id,
                                "prev_team_name": short_name,
                                "status": status,
                                "new_team_id": team_id,
                                "new_team_name": short_name
                            }
                        else:  # 退団
                            st.text_input(
                                "退団",
                                value="Mリーグ退団",
                                disabled=True,
                                key=f"retire_{player_id}",
                                label_visibility="collapsed"
                            )
                            player_moves[player_id] = {
                                "player_name": player_name,
                                "prev_team_id": team_id,
                                "prev_team_name": short_name,
                                "status": status,
                                "new_team_id": None,
                                "new_team_name": None
                            }
            
            # 選手移籍情報をセッション状態に保存
            if st.button("選手移籍を保存", key="save_player_moves", type="primary"):
                st.session_state.season_update_player_moves = player_moves
                st.success("✅ 選手移籍情報を保存しました。「確認と登録」タブで内容を確認してください。")
                st.rerun()
            
            # 保存済みの場合は表示
            if st.session_state.season_update_player_moves:
                st.markdown("---")
                st.success("✅ 選手移籍情報は保存済みです")

# ========== タブ3: 確認と登録 ==========
with tab3:
    st.subheader(f"✅ {new_season}シーズン更新内容の確認")
    
    if not st.session_state.season_update_team_names:
        st.warning("⚠️ チーム名設定を完了してください。")
    elif not st.session_state.season_update_player_moves:
        st.warning("⚠️ 選手移籍入力を完了してください。")
    else:
        st.success("✅ すべての情報が入力されています。内容を確認して登録してください。")
        
        # チーム名変更の確認
        st.markdown("---")
        st.markdown("### 🏷️ チーム名変更")
        
        team_name_list = []
        for team_id, new_name in st.session_state.season_update_team_names.items():
            # 前シーズンの名前を取得
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.short_name, tn.team_name
                FROM teams t
                JOIN team_names tn ON t.team_id = tn.team_id
                WHERE t.team_id = ? AND tn.season = ?
            """, (team_id, new_season - 1))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                short_name, prev_name = result
                change_status = "変更あり" if prev_name != new_name else "変更なし"
                team_name_list.append({
                    "チーム": short_name,
                    f"{new_season-1}年": prev_name,
                    f"{new_season}年": new_name,
                    "状態": change_status
                })
        
        df_teams = pd.DataFrame(team_name_list)
        st.dataframe(df_teams, hide_index=True, width="stretch")
        
        # 選手移籍の確認
        st.markdown("---")
        st.markdown("### 👥 選手移籍")
        
        player_move_list = []
        for player_id, info in st.session_state.season_update_player_moves.items():
            if info["status"] == "残留":
                move_info = "残留"
            elif info["status"] == "移籍":
                move_info = f"OUT: {info['prev_team_name']} → IN: {info['new_team_name']}"
            else:  # 退団
                move_info = f"OUT: {info['prev_team_name']} (退団)"
            
            player_move_list.append({
                "選手名": info["player_name"],
                "移籍情報": move_info,
                "状態": info["status"]
            })
        
        df_players = pd.DataFrame(player_move_list)
        
        # フィルタ
        col1, col2, col3 = st.columns(3)
        with col1:
            show_stay = st.checkbox("残留", value=True)
        with col2:
            show_transfer = st.checkbox("移籍", value=True)
        with col3:
            show_retire = st.checkbox("退団", value=True)
        
        filter_status = []
        if show_stay:
            filter_status.append("残留")
        if show_transfer:
            filter_status.append("移籍")
        if show_retire:
            filter_status.append("退団")
        
        if filter_status:
            filtered_df = df_players[df_players["状態"].isin(filter_status)]
            st.dataframe(filtered_df, hide_index=True, width="stretch")
            
            # 統計情報
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("合計", len(df_players))
            with col2:
                stay_count = len(df_players[df_players["状態"] == "残留"])
                st.metric("残留", stay_count)
            with col3:
                transfer_count = len(df_players[df_players["状態"] == "移籍"])
                st.metric("移籍", transfer_count)
            with col4:
                retire_count = len(df_players[df_players["状態"] == "退団"])
                st.metric("退団", retire_count)
        else:
            st.info("表示する状態を選択してください")
        
        # 登録ボタン
        st.markdown("---")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.warning("⚠️ 登録後は元に戻せません。内容を十分に確認してから登録してください。")
        with col2:
            if st.button("🚀 データベースに登録", type="primary"):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    # 1. チーム名を登録
                    for team_id, new_name in st.session_state.season_update_team_names.items():
                        cursor.execute("""
                            INSERT OR REPLACE INTO team_names (team_id, season, team_name)
                            VALUES (?, ?, ?)
                        """, (team_id, new_season, new_name))
                    
                    # 2. 選手所属を登録（退団者以外）
                    for player_id, info in st.session_state.season_update_player_moves.items():
                        if info["status"] != "退団":
                            cursor.execute("""
                                INSERT OR REPLACE INTO player_teams (player_id, team_id, season)
                                VALUES (?, ?, ?)
                            """, (player_id, info["new_team_id"], new_season))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success(f"✅ {new_season}シーズンのデータを登録しました！")
                    
                    # セッション状態をクリア
                    st.session_state.season_update_team_names = {}
                    st.session_state.season_update_player_moves = {}
                    st.session_state.season_update_confirmed = True
                    
                    st.balloons()
                    
                    # 完了メッセージ
                    st.markdown("---")
                    st.info("""
                    ### 🎉 シーズン更新が完了しました！
                    
                    次のステップ：
                    1. 新加入選手がいる場合は「選手管理」ページで登録してください
                    2. シーズン成績を「データ管理」ページで入力してください
                    """)
                    
                except Exception as e:
                    conn.rollback()
                    conn.close()
                    st.error(f"❌ エラーが発生しました: {e}")

# ========== サイドバー ==========
with st.sidebar:
    st.markdown("### 📖 使い方")
    st.markdown("""
    1. **新シーズン番号を入力**
       - 更新する年度を設定
    
    2. **チーム名設定タブ**
       - 各チームの新シーズン名を確認・編集
       - 変更がない場合もそのまま「保存」
    
    3. **選手移籍入力タブ**
       - 各選手の状態を選択
       - 残留/移籍/退団から選択
    
    4. **確認と登録タブ**
       - 変更内容を確認
       - 問題なければ「登録」
    """)
    
    st.markdown("---")
    st.markdown("### ⚠️ 注意事項")
    st.markdown("""
    - 一度登録すると元に戻せません
    - 新加入選手は別途「選手管理」で登録
    - バックアップを取ってから実行推奨
    """)
