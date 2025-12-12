import streamlit as st
import pandas as pd
from datetime import datetime, date, time
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

st.title("🎮 半荘記録入力")

st.markdown("""
半荘ごとの詳細な対局結果を記録します。
- シーズン、日付、時間、卓区分、対局番号を指定
- 4名の選手の席、獲得ポイント、順位を入力
- データ整合性を自動チェック
- 既存データの編集・削除が可能
""")

# ========== タブで新規入力と編集を分ける ==========
tab_new, tab_edit = st.tabs(["📝 新規入力", "✏️ データ編集"])

# ========== 新規入力タブ ==========
with tab_new:
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
        selected_season = st.selectbox("シーズン", seasons, key="new_season_select")
    
    with col2:
        game_date = st.date_input(
            "対局日",
            value=date.today(),
            key="new_game_date"
        )
    
    with col3:
        table_types = ["レギュラー", "セミファイナル", "ファイナル", "その他"]
        table_type = st.selectbox("卓区分", table_types, key="new_table_type")
    
    with col4:
        game_number = st.number_input(
            "対局番号",
            min_value=1,
            max_value=100,
            value=1,
            help="同じ日に複数対局がある場合の識別番号",
            key="new_game_number"
        )
    
    # 開始・終了時間の入力
    col_time1, col_time2 = st.columns(2)
    
    with col_time1:
        start_time = st.text_input(
            "開始時間",
            value="",
            placeholder="例: 19:00",
            key="new_start_time",
            help="対局開始時刻（任意・HH:MM形式）"
        )
    
    with col_time2:
        end_time = st.text_input(
            "終了時間",
            value="",
            placeholder="例: 20:30",
            key="new_end_time",
            help="対局終了時刻（任意・HH:MM形式）"
        )
    
    # ========== 選手選択肢の取得 ==========
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
    - 席は東・南・西・北の順で固定
    - 獲得ポイントの合計は0になるように入力
    - 順位は1〜4で重複なし
    """)
    
    # 席の固定順序
    seat_names = ["東", "南", "西", "北"]
    
    # 4名分の入力フォーム
    with st.form(f"new_game_results_form"):
        st.markdown("### 対局者")
        
        # ヘッダー行
        header_cols = st.columns([1, 3, 1.5, 1.5])
        header_cols[0].markdown("**席**")
        header_cols[1].markdown("**選手名**")
        header_cols[2].markdown("**獲得pt**")
        header_cols[3].markdown("**順位**")
        
        # 4名分の入力行（席は固定）
        game_data = []
        
        for i, seat in enumerate(seat_names):
            cols = st.columns([1, 3, 1.5, 1.5])
            
            # 席名を固定表示
            with cols[0]:
                st.markdown(f"**{seat}**")
            
            with cols[1]:
                player = st.selectbox(
                    f"選手{i+1}",
                    player_display_names,
                    key=f"new_player_{i}",
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
                    key=f"new_points_{i}",
                    label_visibility="collapsed"
                )
            
            with cols[3]:
                rank = st.number_input(
                    f"順位{i+1}",
                    min_value=1,
                    max_value=4,
                    value=i+1,
                    key=f"new_rank_{i}",
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
        
        col1, col2 = st.columns(2)
        
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
                st.success("✅ 順位: 1-4 (重複なし)")
            else:
                st.error("❌ 順位: 重複または不正な値があります")
        
        # 保存ボタン
        st.markdown("---")
        submitted = st.form_submit_button("💾 保存", use_container_width=True)
        
        if submitted:
            # バリデーション
            if abs(total_points) >= 0.1:
                st.error("❌ ポイント合計が0ではありません。修正してください。")
            elif len(ranks) != len(set(ranks)) or set(ranks) != {1, 2, 3, 4}:
                st.error("❌ 順位に重複または不正な値があります。修正してください。")
            else:
                # データベースに保存
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    # 時間をフォーマット
                    start_time_str = start_time.strip() if start_time.strip() else None
                    end_time_str = end_time.strip() if end_time.strip() else None
                    
                    # 4名分のデータを挿入
                    for data in game_data:
                        cursor.execute("""
                            INSERT INTO game_results (
                                season, game_date, table_type, game_number,
                                seat_name, player_id, points, rank,
                                start_time, end_time
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            selected_season,
                            game_date.strftime("%Y-%m-%d"),
                            table_type,
                            game_number,
                            data['seat'],
                            data['player_id'],
                            data['points'],
                            data['rank'],
                            start_time_str,
                            end_time_str
                        ))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success("✅ 対局結果を保存しました")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")
                    if 'conn' in locals():
                        conn.close()

    # ========== 最近の対局一覧 ==========
    st.markdown("---")
    st.subheader("📋 最近の対局")
    
    conn = get_connection()
    
    recent_games_query = """
        SELECT 
            season,
            game_date,
            table_type,
            game_number,
            start_time,
            end_time,
            COUNT(*) as player_count,
            GROUP_CONCAT(
                (SELECT player_name FROM players WHERE player_id = gr.player_id), 
                ', '
            ) as players
        FROM game_results gr
        WHERE season = ?
        GROUP BY season, game_date, table_type, game_number
        ORDER BY game_date DESC, game_number DESC
        LIMIT 10
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
                "start_time": "開始時間",
                "end_time": "終了時間",
                "player_count": "人数",
                "players": "対局者"
            },
            hide_index=True,
            width='stretch'
        )
        
        # 統計情報
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM (
                SELECT DISTINCT season, game_date, game_number 
                FROM game_results 
                WHERE season = ?
            )
        """, (selected_season,))
        
        total_games = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM game_results WHERE season = ?
        """, (selected_season,))
        
        total_records = cursor.fetchone()[0]
        conn.close()
        
        st.info(f"📊 {selected_season}シーズン: {total_games}対局 / {total_records}記録")
    else:
        st.info(f"{selected_season}シーズンの対局記録がまだありません。")

# ========== データ編集タブ ==========
with tab_edit:
    st.markdown("---")
    st.subheader("🔍 対局検索")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 利用可能なシーズンを取得
    cursor.execute("SELECT DISTINCT season FROM game_results ORDER BY season DESC")
    edit_seasons = [row[0] for row in cursor.fetchall()]
    
    if not edit_seasons:
        st.info("まだ対局記録がありません。「新規入力」タブから記録を追加してください。")
        conn.close()
        st.stop()
    
    col1, col2 = st.columns(2)
    
    with col1:
        edit_season = st.selectbox("シーズン", edit_seasons, key="edit_season_select")
    
    # そのシーズンの対局一覧を取得
    cursor.execute("""
        SELECT DISTINCT 
            game_date,
            table_type,
            game_number,
            start_time,
            end_time
        FROM game_results
        WHERE season = ?
        ORDER BY game_date DESC, game_number DESC
    """, (edit_season,))
    
    games_list = cursor.fetchall()
    conn.close()
    
    if not games_list:
        st.info(f"{edit_season}シーズンの対局記録がありません。")
        st.stop()
    
    # 対局選択肢を作成
    game_options = {}
    game_options_list = []  # インデックスベースの選択肢リスト
    for i, game in enumerate(games_list):
        game_date_str = game[0]
        table_type = game[1]
        game_num = game[2]
        start_time = game[3] if game[3] else "--:--"
        end_time = game[4] if game[4] else "--:--"
        
        display_text = f"{game_date_str} | {table_type} | 第{game_num}試合 | {start_time}~{end_time}"
        game_options[display_text] = (game_date_str, table_type, game_num)
        game_options_list.append(display_text)
    
    with col2:
        # インデックスベースで選択
        selected_game_index = st.selectbox(
            "対局を選択",
            range(len(game_options_list)),
            format_func=lambda x: game_options_list[x],
            key="edit_game_select"
        )
    
    # 選択された対局のデータを取得
    selected_game_display = game_options_list[selected_game_index]
    game_date_str, table_type, game_num = game_options[selected_game_display]
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            gr.id,
            gr.seat_name,
            p.player_name,
            gr.player_id,
            gr.points,
            gr.rank,
            gr.start_time,
            gr.end_time
        FROM game_results gr
        JOIN players p ON gr.player_id = p.player_id
        WHERE gr.season = ? 
            AND gr.game_date = ? 
            AND gr.table_type = ?
            AND gr.game_number = ?
        ORDER BY 
            CASE gr.seat_name
                WHEN '東' THEN 1
                WHEN '南' THEN 2
                WHEN '西' THEN 3
                WHEN '北' THEN 4
            END
    """, (edit_season, game_date_str, table_type, game_num))
    
    game_records = cursor.fetchall()
    
    # 選手リストを取得（編集用）
    cursor.execute("""
        SELECT DISTINCT p.player_id, p.player_name, tn.team_name
        FROM players p
        JOIN player_teams pt ON p.player_id = pt.player_id
        JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        WHERE pt.season = ?
        ORDER BY tn.team_name, p.player_name
    """, (edit_season,))
    
    edit_players_data = cursor.fetchall()
    conn.close()
    
    # 選手リストを作成
    edit_player_options = {
        f"{row[1]} ({row[2]})": row[0]
        for row in edit_players_data
    }
    edit_player_display_names = list(edit_player_options.keys())
    
    # 編集フォーム
    st.markdown("---")
    st.subheader("✏️ データ編集")
    
    # フォームのkeyに対局インデックスを含めることで、選択が変わるたびに確実に再生成される
    form_key = f"edit_game_form_{selected_game_index}"
    
    with st.form(form_key):
        # 対局情報
        st.markdown("### 対局情報")
        
        info_col1, info_col2, info_col3 = st.columns(3)
        
        with info_col1:
            edit_game_date = st.date_input(
                "対局日",
                value=datetime.strptime(game_date_str, "%Y-%m-%d").date(),
                key=f"edit_game_date_{selected_game_index}"
            )
        
        with info_col2:
            edit_table_type = st.selectbox(
                "卓区分",
                ["レギュラー", "セミファイナル", "ファイナル", "その他"],
                index=["レギュラー", "セミファイナル", "ファイナル", "その他"].index(table_type),
                key=f"edit_table_type_{selected_game_index}"
            )
        
        with info_col3:
            edit_game_number = st.number_input(
                "対局番号",
                min_value=1,
                max_value=100,
                value=game_num,
                key=f"edit_game_number_{selected_game_index}"
            )
        
        # 時間情報
        time_col1, time_col2 = st.columns(2)
        
        # 既存の時間を取得（最初のレコードから）
        existing_start_time = game_records[0][6] if game_records[0][6] else ""
        existing_end_time = game_records[0][7] if game_records[0][7] else ""
        
        with time_col1:
            edit_start_time = st.text_input(
                "開始時間",
                value=existing_start_time,
                placeholder="例: 19:00",
                key=f"edit_start_time_{selected_game_index}",
                help="対局開始時刻（任意・HH:MM形式）"
            )
        
        with time_col2:
            edit_end_time = st.text_input(
                "終了時間",
                value=existing_end_time,
                placeholder="例: 20:30",
                key=f"edit_end_time_{selected_game_index}",
                help="対局終了時刻（任意・HH:MM形式）"
            )
        
        # 対局結果
        st.markdown("### 対局結果")
        
        # ヘッダー行
        header_cols = st.columns([1, 3, 1.5, 1.5])
        header_cols[0].markdown("**席**")
        header_cols[1].markdown("**選手名**")
        header_cols[2].markdown("**獲得pt**")
        header_cols[3].markdown("**順位**")
        
        # 編集データ
        edit_game_data = []
        
        for i, record in enumerate(game_records):
            record_id = record[0]
            seat = record[1]
            player_name = record[2]
            player_id = record[3]
            points = record[4]
            rank = record[5]
            
            # 現在の選手の表示名を取得
            current_player_display = None
            for display_name, pid in edit_player_options.items():
                if pid == player_id:
                    current_player_display = display_name
                    break
            
            if not current_player_display:
                current_player_display = edit_player_display_names[0]
            
            cols = st.columns([1, 3, 1.5, 1.5])
            
            with cols[0]:
                st.markdown(f"**{seat}**")
            
            with cols[1]:
                edited_player = st.selectbox(
                    f"選手{i+1}",
                    edit_player_display_names,
                    index=edit_player_display_names.index(current_player_display),
                    key=f"edit_player_{i}_{selected_game_index}",
                    label_visibility="collapsed"
                )
            
            with cols[2]:
                edited_points = st.number_input(
                    f"ポイント{i+1}",
                    min_value=-100.0,
                    max_value=100.0,
                    value=float(points),
                    step=0.1,
                    format="%.1f",
                    key=f"edit_points_{i}_{selected_game_index}",
                    label_visibility="collapsed"
                )
            
            with cols[3]:
                edited_rank = st.number_input(
                    f"順位{i+1}",
                    min_value=1,
                    max_value=4,
                    value=int(rank),
                    key=f"edit_rank_{i}_{selected_game_index}",
                    label_visibility="collapsed"
                )
            
            edit_game_data.append({
                'id': record_id,
                'seat': seat,
                'player_name': edited_player,
                'player_id': edit_player_options[edited_player],
                'points': edited_points,
                'rank': edited_rank
            })
        
        # データ検証
        st.markdown("---")
        st.markdown("### データチェック")
        
        col1, col2 = st.columns(2)
        
        edit_total_points = sum(d['points'] for d in edit_game_data)
        with col1:
            if abs(edit_total_points) < 0.1:
                st.success(f"✅ ポイント合計: {edit_total_points:.1f}")
            else:
                st.error(f"❌ ポイント合計: {edit_total_points:.1f} (0でありません)")
        
        edit_ranks = [d['rank'] for d in edit_game_data]
        with col2:
            if len(edit_ranks) == len(set(edit_ranks)) and set(edit_ranks) == {1, 2, 3, 4}:
                st.success("✅ 順位: 1-4 (重複なし)")
            else:
                st.error("❌ 順位: 重複または不正な値があります")
        
        # ボタン
        st.markdown("---")
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            update_submitted = st.form_submit_button("💾 更新", use_container_width=True)
        
        with col_btn2:
            delete_submitted = st.form_submit_button("🗑️ 削除", use_container_width=True, type="secondary")
        
        if update_submitted:
            # バリデーション
            if abs(edit_total_points) >= 0.1:
                st.error("❌ ポイント合計が0ではありません。修正してください。")
            elif len(edit_ranks) != len(set(edit_ranks)) or set(edit_ranks) != {1, 2, 3, 4}:
                st.error("❌ 順位に重複または不正な値があります。修正してください。")
            else:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    # 時間をフォーマット
                    start_time_str = edit_start_time.strip() if edit_start_time.strip() else None
                    end_time_str = edit_end_time.strip() if edit_end_time.strip() else None
                    
                    # 4名分のデータを更新
                    for data in edit_game_data:
                        cursor.execute("""
                            UPDATE game_results
                            SET game_date = ?,
                                table_type = ?,
                                game_number = ?,
                                seat_name = ?,
                                player_id = ?,
                                points = ?,
                                rank = ?,
                                start_time = ?,
                                end_time = ?
                            WHERE id = ?
                        """, (
                            edit_game_date.strftime("%Y-%m-%d"),
                            edit_table_type,
                            edit_game_number,
                            data['seat'],
                            data['player_id'],
                            data['points'],
                            data['rank'],
                            start_time_str,
                            end_time_str,
                            data['id']
                        ))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success("✅ 対局結果を更新しました")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")
                    if 'conn' in locals():
                        conn.close()
        
        if delete_submitted:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # この対局の全記録を削除
                cursor.execute("""
                    DELETE FROM game_results
                    WHERE season = ? 
                        AND game_date = ?
                        AND table_type = ?
                        AND game_number = ?
                """, (edit_season, game_date_str, table_type, game_num))
                
                conn.commit()
                conn.close()
                
                st.success("✅ 対局記録を削除しました")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")
                if 'conn' in locals():
                    conn.close()
