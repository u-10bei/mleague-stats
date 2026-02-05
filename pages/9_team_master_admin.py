import sys
import sqlite3
import streamlit as st
from db import get_connection, get_teams, show_sidebar_navigation
sys.path.append("..")

st.set_page_config(
    page_title="チームマスター管理 | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide"
)

# サイドバーナビゲーション
show_sidebar_navigation()

st.title("🏢 チームマスター管理")

st.markdown("""
チーム基本情報（マスターデータ）を管理します。
- チームの新規追加
- チーム情報の編集（略称、カラー、設立年）
- チームの削除
""")

# タブで機能を分ける
tab1, tab2, tab3 = st.tabs(["📋 チーム一覧", "➕ 新規登録", "✏️ 編集・削除"])

# タブ1: チーム一覧
with tab1:
    st.subheader("登録済みチーム一覧")

    teams_df = get_teams()

    if not teams_df.empty:
        # 表示用のDataFrameを作成
        display_df = teams_df.copy()

        # カラーをプレビュー表示
        def color_preview(color_value):
            return f'<div style="width: 50px; height: 20px; background-color: {color_value}; border: 1px solid #ccc;"></div>'

        # チーム数の統計
        col1, col2 = st.columns(2)
        with col1:
            st.metric("登録チーム数", f"{len(teams_df)}チーム")
        with col2:
            avg_year = int(teams_df['established'].mean())
            st.metric("平均設立年", f"{avg_year}年")

        st.markdown("---")

        # テーブル表示
        for _, row in display_df.iterrows():
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

            with col1:
                st.markdown(f"### {row['short_name']}")

            with col2:
                st.markdown(color_preview(
                    row['color']), unsafe_allow_html=True)
                st.caption(f"カラー: {row['color']}")

            with col3:
                st.metric("設立年", f"{row['established']}年")

            with col4:
                st.metric("チームID", row['team_id'])

            st.markdown("---")

    else:
        st.info("まだチームが登録されていません。")

# タブ2: 新規登録
with tab2:
    st.subheader("新しいチームを登録")

    st.info("💡 チームIDは自動採番されます。略称は短い名前（例: ドリブンズ）を入力してください。")

    with st.form("add_team_form"):
        short_name = st.text_input(
            "チーム略称",
            placeholder="例: ドリブンズ",
            help="チームの短い名前を入力してください"
        )

        col1, col2 = st.columns(2)

        with col1:
            color = st.color_picker(
                "チームカラー",
                value="#888888",
                help="チームを識別する色を選択してください"
            )

        with col2:
            established = st.number_input(
                "設立年",
                min_value=2018,
                max_value=2030,
                value=2025,
                step=1,
                help="チームが設立された年を入力してください"
            )

        # プレビュー
        st.markdown("---")
        st.markdown("### プレビュー")

        preview_col1, preview_col2 = st.columns([1, 3])
        with preview_col1:
            st.markdown(
                f'<div style="width: 100px; height: 50px; background-color: {color}; border: 1px solid #ccc; border-radius: 4px;"></div>', unsafe_allow_html=True)
        with preview_col2:
            st.markdown(f"**{short_name}**")
            st.caption(f"設立: {established}年")

        st.markdown("---")

        submit = st.form_submit_button("➕ 登録", type="primary")

        if submit:
            if not short_name.strip():
                st.error("❌ チーム略称を入力してください")
            else:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()

                    # 重複チェック
                    cursor.execute(
                        "SELECT team_id FROM teams WHERE short_name = ?",
                        (short_name.strip(),)
                    )
                    if cursor.fetchone():
                        st.error(f"❌ 略称 '{short_name}' は既に登録されています")
                    else:
                        # チームを登録
                        cursor.execute("""
                            INSERT INTO teams (short_name, color, established)
                            VALUES (?, ?, ?)
                        """, (short_name.strip(), color, established))

                        conn.commit()
                        st.success(f"✅ {short_name} を登録しました")

                        st.info("""
                        ### 📝 次のステップ
                        
                        チームマスターを登録した後は：
                        1. **シーズン更新ページ** で各シーズンのチーム名を登録
                        2. **選手管理ページ** で所属選手を登録
                        3. **データ管理ページ** でシーズンポイントを入力
                        """)

                        st.rerun()

                    conn.close()
                except (sqlite3.IntegrityError, sqlite3.OperationalError, ValueError) as e:
                    st.error(f"❌ エラーが発生しました: {e}")

# タブ3: 編集・削除
with tab3:
    st.subheader("チーム情報の編集・削除")

    teams_df = get_teams()

    if not teams_df.empty:
        # チーム選択
        team_options = dict(zip(teams_df["short_name"], teams_df["team_id"]))

        selected_team_name = st.selectbox(
            "編集するチームを選択",
            options=list(team_options.keys())
        )

        if selected_team_name:
            selected_team_id = team_options[selected_team_name]
            team_data = teams_df[teams_df["team_id"]
                                 == selected_team_id].iloc[0]

            st.markdown("---")

            col1, col2 = st.columns([3, 1])

            with col1:
                st.subheader("✏️ チーム情報を編集")

                with st.form("edit_team_form"):
                    new_short_name = st.text_input(
                        "チーム略称",
                        value=team_data["short_name"],
                        help="チームの短い名前"
                    )

                    edit_col1, edit_col2 = st.columns(2)

                    with edit_col1:
                        new_color = st.color_picker(
                            "チームカラー",
                            value=team_data["color"],
                            help="チームを識別する色"
                        )

                    with edit_col2:
                        new_established = st.number_input(
                            "設立年",
                            min_value=2018,
                            max_value=2030,
                            value=int(team_data["established"]),
                            step=1,
                            help="チームが設立された年"
                        )

                    # プレビュー
                    st.markdown("---")
                    st.markdown("### プレビュー")

                    preview_col1, preview_col2 = st.columns([1, 3])
                    with preview_col1:
                        st.markdown(
                            f'<div style="width: 100px; height: 50px; background-color: {new_color}; border: 1px solid #ccc; border-radius: 4px;"></div>', unsafe_allow_html=True)
                    with preview_col2:
                        st.markdown(f"**{new_short_name}**")
                        st.caption(f"設立: {new_established}年")

                    st.markdown("---")

                    update = st.form_submit_button("💾 更新", type="primary")

                    if update:
                        if not new_short_name.strip():
                            st.error("❌ チーム略称を入力してください")
                        else:
                            try:
                                conn = get_connection()
                                cursor = conn.cursor()

                                # 重複チェック（自分以外）
                                cursor.execute(
                                    "SELECT team_id FROM teams WHERE short_name = ? AND team_id != ?",
                                    (new_short_name.strip(), selected_team_id)
                                )
                                if cursor.fetchone():
                                    st.error(
                                        f"❌ 略称 '{new_short_name}' は既に使用されています")
                                else:
                                    # チーム情報を更新
                                    cursor.execute("""
                                        UPDATE teams 
                                        SET short_name = ?, color = ?, established = ?
                                        WHERE team_id = ?
                                    """, (new_short_name.strip(), new_color, new_established, selected_team_id))

                                    conn.commit()
                                    st.success(
                                        f"✅ {new_short_name} の情報を更新しました")
                                    st.rerun()

                                conn.close()
                            except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
                                st.error(f"❌ エラーが発生しました: {e}")

            with col2:
                st.subheader("🗑️ 削除")

                st.warning("⚠️ この操作は取り消せません")

                # 関連データの確認
                conn = get_connection()
                cursor = conn.cursor()

                # チーム名履歴の数
                cursor.execute(
                    "SELECT COUNT(*) FROM team_names WHERE team_id = ?",
                    (selected_team_id,)
                )
                team_names_count = cursor.fetchone()[0]

                # シーズンポイントの数
                cursor.execute(
                    "SELECT COUNT(*) FROM team_season_points WHERE team_id = ?",
                    (selected_team_id,)
                )
                points_count = cursor.fetchone()[0]

                # 選手所属の数
                cursor.execute(
                    "SELECT COUNT(*) FROM player_teams WHERE team_id = ?",
                    (selected_team_id,)
                )
                players_count = cursor.fetchone()[0]

                conn.close()

                st.markdown("### 関連データ")
                st.metric("チーム名履歴", f"{team_names_count}件")
                st.metric("シーズンポイント", f"{points_count}件")
                st.metric("選手所属", f"{players_count}件")

                total_related = team_names_count + points_count + players_count

                if total_related > 0:
                    st.error(f"⚠️ {total_related}件の関連データがあります")
                    st.markdown("削除すると、これらのデータも**すべて削除**されます（カスケード削除）")

                if st.button("🗑️ 削除", type="secondary", key="delete_team"):
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()

                        # カスケード削除（ON DELETE CASCADEにより自動的に関連データも削除される）
                        cursor.execute(
                            "DELETE FROM teams WHERE team_id = ?",
                            (selected_team_id,)
                        )

                        conn.commit()
                        conn.close()

                        st.success(f"✅ {team_data['short_name']} を削除しました")
                        st.rerun()

                    except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
                        st.error(f"❌ エラーが発生しました: {e}")
    else:
        st.info("チームが登録されていません。")

# データベース統計
st.markdown("---")
with st.expander("📊 データベース統計"):
    teams_df = get_teams()

    if not teams_df.empty:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("総チーム数", f"{len(teams_df)}チーム")

        with col2:
            oldest_year = teams_df['established'].min()
            st.metric("最古の設立", f"{oldest_year}年")

        with col3:
            newest_year = teams_df['established'].max()
            st.metric("最新の設立", f"{newest_year}年")

        # チーム一覧表
        st.markdown("### チーム一覧")
        display_df = teams_df[['team_id', 'short_name', 'established']].copy()
        display_df.columns = ['ID', 'チーム略称', '設立年']
        st.dataframe(display_df, hide_index=True)
    else:
        st.info("データがありません")
