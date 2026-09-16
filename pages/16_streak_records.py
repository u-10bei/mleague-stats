import streamlit as st
import pandas as pd
from db import get_connection, get_team_colors, get_current_team_names, show_sidebar_navigation

st.set_page_config(
    page_title="連続記録 | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide"
)

# 共通サイドバーナビゲーションを表示
show_sidebar_navigation()

st.title("🔥 連続記録")

st.markdown("""
選手・チームの連続記録を分析します。
""")

# ========== データ取得 ==========
conn = get_connection()
cursor = conn.cursor()

# 利用可能なシーズンを取得
cursor.execute("""
    SELECT DISTINCT season 
    FROM game_results 
    ORDER BY season DESC
""")
seasons = [row[0] for row in cursor.fetchall()]

if not seasons:
    st.warning("半荘記録データがありません。先に「🎮 半荘記録入力」でデータを登録してください。")
    conn.close()
    st.stop()

# ========== フィルター設定 ==========
st.markdown("---")
st.subheader("🔍 分析条件")

col1, col2 = st.columns(2)

with col1:
    period_options = ["全期間"] + seasons
    selected_period = st.selectbox("期間", period_options, key="period_select")

with col2:
    st.info(f"選択中: **{selected_period}**")

# ========== データ取得 ==========
if selected_period == "全期間":
    query = """
        SELECT 
            gr.player_id,
            p.player_name,
            gr.season,
            gr.game_date,
            gr.game_number,
            gr.rank,
            pt.team_id,
            tn.team_name
        FROM game_results gr
        JOIN players p ON gr.player_id = p.player_id
        JOIN player_teams pt ON gr.player_id = pt.player_id AND gr.season = pt.season
        JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        ORDER BY gr.season, gr.game_date, gr.game_number, gr.player_id
    """
    cursor.execute(query)
else:
    query = """
        SELECT 
            gr.player_id,
            p.player_name,
            gr.season,
            gr.game_date,
            gr.game_number,
            gr.rank,
            pt.team_id,
            tn.team_name
        FROM game_results gr
        JOIN players p ON gr.player_id = p.player_id
        JOIN player_teams pt ON gr.player_id = pt.player_id AND gr.season = pt.season
        JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
        WHERE gr.season = ?
        ORDER BY gr.game_date, gr.game_number, gr.player_id
    """
    cursor.execute(query, (selected_period,))

results = cursor.fetchall()
conn.close()

if not results:
    st.warning("選択した期間に該当するデータがありません。")
    st.stop()

# DataFrameに変換
df = pd.DataFrame(results, columns=[
    'player_id', 'player_name', 'season', 'game_date', 'game_number', 'rank', 'team_id', 'team_name'
])
# 全期間ではシーズンごとのチーム名で束ねると同一チームが分裂するため、
# 表示名を最新シーズンの名前に寄せる（例: BEAST Japanext と BEAST X）。
if selected_period == "全期間":
    _current_names = get_current_team_names()
    df["team_name"] = df["team_id"].map(_current_names).fillna(
        df["team_id"].map(lambda i: f"Team {i}"))

st.markdown("---")
st.info(
    f"📊 データ件数: {len(df)}対局 / {df['player_name'].nunique()}選手 / {df['team_name'].nunique()}チーム")


# ========== 選手連続記録計算関数 ==========
def calculate_player_streaks(df, condition_func, streak_name):
    """
    選手の連続記録を計算する汎用関数
    """
    all_streaks = []

    # 選手別データ（チーム情報は不要）
    player_df = df[['player_id', 'player_name', 'season',
                    'game_date', 'game_number', 'rank']].copy()

    for player_id, player_group in player_df.groupby('player_id'):
        player_name = player_group.iloc[0]['player_name']
        player_group = player_group.sort_values(
            ['season', 'game_date', 'game_number'])

        current_streak = 0
        streak_start_date = None
        streak_start_season = None

        for idx, row in player_group.iterrows():
            if condition_func(row['rank']):
                if current_streak == 0:
                    streak_start_date = row['game_date']
                    streak_start_season = row['season']
                current_streak += 1
            else:
                if current_streak > 0:
                    prev_idx = player_group.index.get_loc(idx) - 1
                    streak_end_date = player_group.iloc[prev_idx]['game_date']
                    streak_end_season = player_group.iloc[prev_idx]['season']

                    all_streaks.append({
                        'player_id': player_id,
                        'player_name': player_name,
                        'streak': current_streak,
                        'start_date': streak_start_date,
                        'end_date': streak_end_date,
                        'season_start': streak_start_season,
                        'season_end': streak_end_season,
                        'is_active': False,
                        'current_streak': 0
                    })

                    current_streak = 0
                    streak_start_date = None

        if current_streak > 0:
            all_streaks.append({
                'player_id': player_id,
                'player_name': player_name,
                'streak': current_streak,
                'start_date': streak_start_date,
                'end_date': player_group.iloc[-1]['game_date'],
                'season_start': streak_start_season,
                'season_end': player_group.iloc[-1]['season'],
                'is_active': True,
                'current_streak': current_streak
            })

    streaks_df = pd.DataFrame(all_streaks)

    if streaks_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    current_streaks = streaks_df[streaks_df['is_active']].copy()

    if not current_streaks.empty:
        current_streaks = current_streaks.sort_values(
            ['current_streak', 'start_date'],
            ascending=[False, False]
        ).reset_index(drop=True)
        current_streaks['rank'] = range(1, len(current_streaks) + 1)

    all_time_streaks = streaks_df.sort_values(
        ['streak', 'start_date'],
        ascending=[False, False]
    ).reset_index(drop=True)
    all_time_streaks['rank'] = range(1, len(all_time_streaks) + 1)

    return current_streaks, all_time_streaks


# ========== チーム連続記録計算関数 ==========
def calculate_team_streaks(df, condition_func, streak_name):
    """
    チームの連続記録を計算する汎用関数

    各対局でチームから1名のみ参加するため、そのチームの代表選手の順位を基に判定
    """
    all_streaks = []

    # チームごとに連続記録を計算
    for team_id in df['team_id'].unique():
        team_df = df[df['team_id'] == team_id].copy()
        team_name = team_df.iloc[0]['team_name']

        # 時系列順にソート
        team_df = team_df.sort_values(['season', 'game_date', 'game_number'])

        current_streak = 0
        streak_start_date = None
        streak_start_season = None

        for idx, row in team_df.iterrows():
            # このチームの選手の順位が条件を満たすか判定
            if condition_func(row['rank']):
                if current_streak == 0:
                    streak_start_date = row['game_date']
                    streak_start_season = row['season']
                current_streak += 1
            else:
                # 連続記録が途切れた
                if current_streak > 0:
                    # 直前の行を取得
                    prev_idx = team_df.index.get_loc(idx) - 1
                    prev_row = team_df.iloc[prev_idx]

                    all_streaks.append({
                        'team_id': team_id,
                        'team_name': team_name,
                        'streak': current_streak,
                        'start_date': streak_start_date,
                        'end_date': prev_row['game_date'],
                        'season_start': streak_start_season,
                        'season_end': prev_row['season'],
                        'is_active': False,
                        'current_streak': 0
                    })

                    current_streak = 0
                    streak_start_date = None

        # 最後まで連続していた場合（進行中の記録）
        if current_streak > 0:
            last_row = team_df.iloc[-1]
            all_streaks.append({
                'team_id': team_id,
                'team_name': team_name,
                'streak': current_streak,
                'start_date': streak_start_date,
                'end_date': last_row['game_date'],
                'season_start': streak_start_season,
                'season_end': last_row['season'],
                'is_active': True,
                'current_streak': current_streak
            })

    streaks_df = pd.DataFrame(all_streaks)

    if streaks_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    current_streaks = streaks_df[streaks_df['is_active']].copy()

    if not current_streaks.empty:
        current_streaks = current_streaks.sort_values(
            ['current_streak', 'start_date'],
            ascending=[False, False]
        ).reset_index(drop=True)
        current_streaks['rank'] = range(1, len(current_streaks) + 1)

    all_time_streaks = streaks_df.sort_values(
        ['streak', 'start_date'],
        ascending=[False, False]
    ).reset_index(drop=True)
    all_time_streaks['rank'] = range(1, len(all_time_streaks) + 1)

    return current_streaks, all_time_streaks


# ========== メインタブ: 選手別 / チーム別 ==========
main_tab1, main_tab2 = st.tabs(["👤 選手別", "🏢 チーム別"])

# ========== 選手別タブ ==========
with main_tab1:
    st.markdown("## 👤 選手別連続記録")

    tab1, tab2, tab3, tab4 = st.tabs(["🔥 連勝記録", "💔 連敗記録", "🏆 連続連対", "😓 連続逆連対"])

    # 連勝記録
    with tab1:
        st.markdown("### 🔥 連勝記録（連続1位）")

        current_wins, alltime_wins = calculate_player_streaks(
            df, lambda rank: rank == 1, "連勝")

        if not current_wins.empty or not alltime_wins.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📈 現在進行中の連勝")

                if not current_wins.empty:
                    display_current = current_wins.head(
                        10)[['rank', 'player_name', 'current_streak', 'start_date']].copy()
                    display_current.columns = ['順位', '選手名', '連勝数', '開始日']
                    st.dataframe(display_current,
                                 hide_index=True, width='stretch')
                else:
                    st.info("現在進行中の連勝記録はありません。")

            with col2:
                st.markdown("#### 🏆 歴代最長連勝記録")

                if not alltime_wins.empty:
                    display_alltime = alltime_wins.head(
                        10)[['rank', 'player_name', 'streak', 'start_date', 'end_date', 'is_active']].copy()
                    display_alltime.columns = [
                        '順位', '選手名', '連勝数', '開始日', '終了日', '進行中']
                    display_alltime['進行中'] = display_alltime['進行中'].apply(
                        lambda x: '✅' if x else '')
                    st.dataframe(display_alltime,
                                 hide_index=True, width='stretch')
                else:
                    st.info("連勝記録がありません。")
        else:
            st.info("連勝記録データがありません。")

    # 連敗記録
    with tab2:
        st.markdown("### 💔 連敗記録（連続4位）")

        current_losses, alltime_losses = calculate_player_streaks(
            df, lambda rank: rank == 4, "連敗")

        if not current_losses.empty or not alltime_losses.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📉 現在進行中の連敗")

                if not current_losses.empty:
                    display_current = current_losses.head(
                        10)[['rank', 'player_name', 'current_streak', 'start_date']].copy()
                    display_current.columns = ['順位', '選手名', '連敗数', '開始日']
                    st.dataframe(display_current,
                                 hide_index=True, width='stretch')
                else:
                    st.info("現在進行中の連敗記録はありません。")

            with col2:
                st.markdown("#### 💀 歴代最長連敗記録")

                if not alltime_losses.empty:
                    display_alltime = alltime_losses.head(
                        10)[['rank', 'player_name', 'streak', 'start_date', 'end_date', 'is_active']].copy()
                    display_alltime.columns = [
                        '順位', '選手名', '連敗数', '開始日', '終了日', '進行中']
                    display_alltime['進行中'] = display_alltime['進行中'].apply(
                        lambda x: '✅' if x else '')
                    st.dataframe(display_alltime,
                                 hide_index=True, width='stretch')
                else:
                    st.info("連敗記録がありません。")
        else:
            st.info("連敗記録データがありません。")

    # 連続連対記録
    with tab3:
        st.markdown("### 🏆 連続連対記録（連続2位以内）")

        current_top2, alltime_top2 = calculate_player_streaks(
            df, lambda rank: rank <= 2, "連続連対")

        if not current_top2.empty or not alltime_top2.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📈 現在進行中の連続連対")

                if not current_top2.empty:
                    display_current = current_top2.head(
                        10)[['rank', 'player_name', 'current_streak', 'start_date']].copy()
                    display_current.columns = ['順位', '選手名', '連続数', '開始日']
                    st.dataframe(display_current,
                                 hide_index=True, width='stretch')
                else:
                    st.info("現在進行中の連続連対記録はありません。")

            with col2:
                st.markdown("#### 🏆 歴代最長連続連対記録")

                if not alltime_top2.empty:
                    display_alltime = alltime_top2.head(
                        10)[['rank', 'player_name', 'streak', 'start_date', 'end_date', 'is_active']].copy()
                    display_alltime.columns = [
                        '順位', '選手名', '連続数', '開始日', '終了日', '進行中']
                    display_alltime['進行中'] = display_alltime['進行中'].apply(
                        lambda x: '✅' if x else '')
                    st.dataframe(display_alltime,
                                 hide_index=True, width='stretch')
                else:
                    st.info("連続連対記録がありません。")
        else:
            st.info("連続連対記録データがありません。")

    # 連続逆連対記録
    with tab4:
        st.markdown("### 😓 連続逆連対記録（連続3位以下）")

        current_bottom2, alltime_bottom2 = calculate_player_streaks(
            df, lambda rank: rank >= 3, "連続逆連対")

        if not current_bottom2.empty or not alltime_bottom2.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📉 現在進行中の連続逆連対")

                if not current_bottom2.empty:
                    display_current = current_bottom2.head(
                        10)[['rank', 'player_name', 'current_streak', 'start_date']].copy()
                    display_current.columns = ['順位', '選手名', '連続数', '開始日']
                    st.dataframe(display_current,
                                 hide_index=True, width='stretch')
                else:
                    st.info("現在進行中の連続逆連対記録はありません。")

            with col2:
                st.markdown("#### 💀 歴代最長連続逆連対記録")

                if not alltime_bottom2.empty:
                    display_alltime = alltime_bottom2.head(
                        10)[['rank', 'player_name', 'streak', 'start_date', 'end_date', 'is_active']].copy()
                    display_alltime.columns = [
                        '順位', '選手名', '連続数', '開始日', '終了日', '進行中']
                    display_alltime['進行中'] = display_alltime['進行中'].apply(
                        lambda x: '✅' if x else '')
                    st.dataframe(display_alltime,
                                 hide_index=True, width='stretch')
                else:
                    st.info("連続逆連対記録がありません。")
        else:
            st.info("連続逆連対記録データがありません。")

# ========== チーム別タブ ==========
with main_tab2:
    st.markdown("## 🏢 チーム別連続記録")

    st.info("""
    **チーム連続記録の定義:**
    
    各対局にはチームから1名のみ参加します。チーム連続記録は、そのチームの代表選手が参加した対局での成績が連続して条件を満たすことを示します。
    
    - **連勝**: そのチームの選手が1位を取った対局が連続
    - **連敗**: そのチームの選手が4位だった対局が連続
    - **連続連対**: そのチームの選手が2位以内に入った対局が連続
    - **連続逆連対**: そのチームの選手が3位以下だった対局が連続
    """)

    tab1, tab2, tab3, tab4 = st.tabs(["🔥 連勝記録", "💔 連敗記録", "🏆 連続連対", "😓 連続逆連対"])

    # チームカラーを取得
    team_colors = get_team_colors()

    # 連勝記録
    with tab1:
        st.markdown("### 🔥 チーム連勝記録")

        current_wins, alltime_wins = calculate_team_streaks(
            df,
            lambda rank: rank == 1,
            "連勝"
        )

        if not current_wins.empty or not alltime_wins.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📈 現在進行中の連勝")

                if not current_wins.empty:
                    display_current = current_wins.head(
                        10)[['rank', 'team_name', 'current_streak', 'start_date']].copy()
                    display_current.columns = ['順位', 'チーム名', '連勝数', '開始日']

                    # チームカラーを背景色として追加
                    def color_team(row):
                        team_id = current_wins[current_wins['team_name']
                                               == row['チーム名']].iloc[0]['team_id']
                        color = team_colors.get(team_id, '#FFFFFF')
                        return [f'background-color: {color}40'] * len(row)

                    st.dataframe(display_current,
                                 hide_index=True, width='stretch')
                else:
                    st.info("現在進行中の連勝記録はありません。")

            with col2:
                st.markdown("#### 🏆 歴代最長連勝記録")

                if not alltime_wins.empty:
                    display_alltime = alltime_wins.head(
                        10)[['rank', 'team_name', 'streak', 'start_date', 'end_date', 'is_active']].copy()
                    display_alltime.columns = [
                        '順位', 'チーム名', '連勝数', '開始日', '終了日', '進行中']
                    display_alltime['進行中'] = display_alltime['進行中'].apply(
                        lambda x: '✅' if x else '')
                    st.dataframe(display_alltime,
                                 hide_index=True, width='stretch')
                else:
                    st.info("連勝記録がありません。")
        else:
            st.info("連勝記録データがありません。")

    # 連敗記録
    with tab2:
        st.markdown("### 💔 チーム連敗記録")

        current_losses, alltime_losses = calculate_team_streaks(
            df,
            lambda rank: rank == 4,
            "連敗"
        )

        if not current_losses.empty or not alltime_losses.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📉 現在進行中の連敗")

                if not current_losses.empty:
                    display_current = current_losses.head(
                        10)[['rank', 'team_name', 'current_streak', 'start_date']].copy()
                    display_current.columns = ['順位', 'チーム名', '連敗数', '開始日']
                    st.dataframe(display_current,
                                 hide_index=True, width='stretch')
                else:
                    st.info("現在進行中の連敗記録はありません。")

            with col2:
                st.markdown("#### 💀 歴代最長連敗記録")

                if not alltime_losses.empty:
                    display_alltime = alltime_losses.head(
                        10)[['rank', 'team_name', 'streak', 'start_date', 'end_date', 'is_active']].copy()
                    display_alltime.columns = [
                        '順位', 'チーム名', '連敗数', '開始日', '終了日', '進行中']
                    display_alltime['進行中'] = display_alltime['進行中'].apply(
                        lambda x: '✅' if x else '')
                    st.dataframe(display_alltime,
                                 hide_index=True, width='stretch')
                else:
                    st.info("連敗記録がありません。")
        else:
            st.info("連敗記録データがありません。")

    # 連続連対記録
    with tab3:
        st.markdown("### 🏆 チーム連続連対記録")

        current_top2, alltime_top2 = calculate_team_streaks(
            df,
            lambda rank: rank <= 2,
            "連続連対"
        )

        if not current_top2.empty or not alltime_top2.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📈 現在進行中の連続連対")

                if not current_top2.empty:
                    display_current = current_top2.head(
                        10)[['rank', 'team_name', 'current_streak', 'start_date']].copy()
                    display_current.columns = ['順位', 'チーム名', '連続数', '開始日']
                    st.dataframe(display_current,
                                 hide_index=True, width='stretch')
                else:
                    st.info("現在進行中の連続連対記録はありません。")

            with col2:
                st.markdown("#### 🏆 歴代最長連続連対記録")

                if not alltime_top2.empty:
                    display_alltime = alltime_top2.head(
                        10)[['rank', 'team_name', 'streak', 'start_date', 'end_date', 'is_active']].copy()
                    display_alltime.columns = [
                        '順位', 'チーム名', '連続数', '開始日', '終了日', '進行中']
                    display_alltime['進行中'] = display_alltime['進行中'].apply(
                        lambda x: '✅' if x else '')
                    st.dataframe(display_alltime,
                                 hide_index=True, width='stretch')
                else:
                    st.info("連続連対記録がありません。")
        else:
            st.info("連続連対記録データがありません。")

    # 連続逆連対記録
    with tab4:
        st.markdown("### 😓 チーム連続逆連対記録")

        current_bottom2, alltime_bottom2 = calculate_team_streaks(
            df,
            lambda rank: rank >= 3,
            "連続逆連対"
        )

        if not current_bottom2.empty or not alltime_bottom2.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📉 現在進行中の連続逆連対")

                if not current_bottom2.empty:
                    display_current = current_bottom2.head(
                        10)[['rank', 'team_name', 'current_streak', 'start_date']].copy()
                    display_current.columns = ['順位', 'チーム名', '連続数', '開始日']
                    st.dataframe(display_current,
                                 hide_index=True, width='stretch')
                else:
                    st.info("現在進行中の連続逆連対記録はありません。")

            with col2:
                st.markdown("#### 💀 歴代最長連続逆連対記録")

                if not alltime_bottom2.empty:
                    display_alltime = alltime_bottom2.head(
                        10)[['rank', 'team_name', 'streak', 'start_date', 'end_date', 'is_active']].copy()
                    display_alltime.columns = [
                        '順位', 'チーム名', '連続数', '開始日', '終了日', '進行中']
                    display_alltime['進行中'] = display_alltime['進行中'].apply(
                        lambda x: '✅' if x else '')
                    st.dataframe(display_alltime,
                                 hide_index=True, width='stretch')
                else:
                    st.info("連続逆連対記録がありません。")
        else:
            st.info("連続逆連対記録データがありません。")
