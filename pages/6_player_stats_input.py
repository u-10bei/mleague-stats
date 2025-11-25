import streamlit as st
import pandas as pd
from db import get_connection, hide_default_sidebar_navigation

st.set_page_config(page_title="選手成績入力", page_icon="📊", layout="wide")

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
st.sidebar.page_link("pages/5_season_update.py", label="🔄 シーズン更新")
st.sidebar.page_link("pages/6_player_stats_input.py", label="📊 選手成績入力")



st.title("📊 選手成績入力")

st.markdown("""
シーズンごとの選手成績を一括で入力できます。
- 試合数、ポイント、順位回数を入力
- チームごとにグループ化表示
- 既存データは自動的に表示されます
""")

# ========== シーズン選択 ==========
st.markdown("---")
st.subheader("📅 シーズン選択")

col1, col2 = st.columns([1, 3])
with col1:
    # 利用可能なシーズンを取得
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT season FROM player_teams ORDER BY season DESC")
    seasons = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not seasons:
        st.warning("選手の所属データがありません。先に「シーズン更新」または「選手管理」で選手を登録してください。")
        st.stop()
    
    selected_season = st.selectbox("成績を入力するシーズンを選択", seasons)

with col2:
    st.info(f"💡 {selected_season}シーズンに所属している選手の成績を入力できます")

# ========== 選手一覧と成績入力 ==========
st.markdown("---")
st.subheader(f"🎯 {selected_season}シーズン 選手成績")

# 選手データを取得（チームごと）
conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT 
        p.player_id,
        p.player_name,
        pt.team_id,
        tn.team_name,
        COALESCE(pss.games, 0) as games,
        COALESCE(pss.points, 0) as points,
        COALESCE(pss.rank_1st, 0) as rank_1st,
        COALESCE(pss.rank_2nd, 0) as rank_2nd,
        COALESCE(pss.rank_3rd, 0) as rank_3rd,
        COALESCE(pss.rank_4th, 0) as rank_4th
    FROM player_teams pt
    JOIN players p ON pt.player_id = p.player_id
    JOIN team_names tn ON pt.team_id = tn.team_id AND pt.season = tn.season
    LEFT JOIN player_season_stats pss ON p.player_id = pss.player_id AND pss.season = ?
    WHERE pt.season = ?
    ORDER BY tn.team_name, p.player_name
""", (selected_season, selected_season))

players_data = cursor.fetchall()
conn.close()

if not players_data:
    st.warning(f"{selected_season}シーズンに所属している選手がいません。")
    st.stop()

# データをDataFrameに変換
df = pd.DataFrame(players_data, columns=[
    'player_id', 'player_name', 'team_id', 'team_name', 
    'games', 'points', 'rank_1st', 'rank_2nd', 'rank_3rd', 'rank_4th'
])

# セッションステートの初期化
if 'stats_data' not in st.session_state or st.session_state.get('stats_season') != selected_season:
    st.session_state.stats_data = df.to_dict('records')
    st.session_state.stats_season = selected_season

# チームごとにグループ化して表示
teams = df['team_name'].unique()

for team_name in teams:
    team_players = [p for p in st.session_state.stats_data if p['team_name'] == team_name]
    
    with st.expander(f"🏢 {team_name} ({len(team_players)}名)", expanded=True):
        # ヘッダー行
        header_cols = st.columns([3, 1.5, 1.5, 1, 1, 1, 1])
        header_cols[0].markdown("**選手名**")
        header_cols[1].markdown("**試合数**")
        header_cols[2].markdown("**ポイント**")
        header_cols[3].markdown("**1位**")
        header_cols[4].markdown("**2位**")
        header_cols[5].markdown("**3位**")
        header_cols[6].markdown("**4位**")
        
        # 各選手の入力行
        for i, player in enumerate(team_players):
            cols = st.columns([3, 1.5, 1.5, 1, 1, 1, 1])
            
            cols[0].markdown(f"**{player['player_name']}**")
            
            # 入力フィールド
            player_idx = st.session_state.stats_data.index(player)
            
            games = cols[1].number_input(
                "試合数",
                min_value=0,
                max_value=200,
                value=int(player['games']),
                key=f"games_{player['player_id']}",
                label_visibility="collapsed"
            )
            
            points = cols[2].number_input(
                "ポイント",
                min_value=-2000.0,
                max_value=2000.0,
                value=float(player['points']),
                step=0.1,
                format="%.1f",
                key=f"points_{player['player_id']}",
                label_visibility="collapsed"
            )
            
            rank_1st = cols[3].number_input(
                "1位",
                min_value=0,
                max_value=200,
                value=int(player['rank_1st']),
                key=f"rank1_{player['player_id']}",
                label_visibility="collapsed"
            )
            
            rank_2nd = cols[4].number_input(
                "2位",
                min_value=0,
                max_value=200,
                value=int(player['rank_2nd']),
                key=f"rank2_{player['player_id']}",
                label_visibility="collapsed"
            )
            
            rank_3rd = cols[5].number_input(
                "3位",
                min_value=0,
                max_value=200,
                value=int(player['rank_3rd']),
                key=f"rank3_{player['player_id']}",
                label_visibility="collapsed"
            )
            
            rank_4th = cols[6].number_input(
                "4位",
                min_value=0,
                max_value=200,
                value=int(player['rank_4th']),
                key=f"rank4_{player['player_id']}",
                label_visibility="collapsed"
            )
            
            # セッションステートを更新
            st.session_state.stats_data[player_idx].update({
                'games': games,
                'points': points,
                'rank_1st': rank_1st,
                'rank_2nd': rank_2nd,
                'rank_3rd': rank_3rd,
                'rank_4th': rank_4th
            })

# ========== 保存ボタン ==========
st.markdown("---")

col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("💾 一括保存", type="primary"):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            success_count = 0
            for player_data in st.session_state.stats_data:
                # INSERT OR REPLACE で既存データを更新
                cursor.execute("""
                    INSERT OR REPLACE INTO player_season_stats 
                    (player_id, season, games, points, rank_1st, rank_2nd, rank_3rd, rank_4th)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    player_data['player_id'],
                    selected_season,
                    player_data['games'],
                    player_data['points'],
                    player_data['rank_1st'],
                    player_data['rank_2nd'],
                    player_data['rank_3rd'],
                    player_data['rank_4th']
                ))
                success_count += 1
            
            conn.commit()
            conn.close()
            
            st.success(f"✅ {success_count}名の成績を保存しました")
            
        except Exception as e:
            st.error(f"❌ 保存中にエラーが発生しました: {str(e)}")

with col2:
    if st.button("🔄 リセット"):
        # データベースから再読み込み
        del st.session_state.stats_data
        del st.session_state.stats_season
        st.rerun()

with col3:
    st.info("💡 入力が完了したら「一括保存」をクリックしてください")

# ========== データ確認 ==========
st.markdown("---")
st.subheader("📋 入力データ確認")

# 確認用のDataFrameを作成
confirm_data = []
for player_data in st.session_state.stats_data:
    # 順位回数の合計が試合数と一致するかチェック
    total_ranks = (player_data['rank_1st'] + player_data['rank_2nd'] + 
                   player_data['rank_3rd'] + player_data['rank_4th'])
    match_status = "✅" if total_ranks == player_data['games'] else "⚠️"
    
    confirm_data.append({
        'チーム': player_data['team_name'],
        '選手名': player_data['player_name'],
        '試合数': player_data['games'],
        'ポイント': f"{player_data['points']:.1f}",
        '1位': player_data['rank_1st'],
        '2位': player_data['rank_2nd'],
        '3位': player_data['rank_3rd'],
        '4位': player_data['rank_4th'],
        '合計': total_ranks,
        '整合性': match_status
    })

confirm_df = pd.DataFrame(confirm_data)

# 整合性チェックの説明
col1, col2 = st.columns(2)
with col1:
    mismatch_count = len([d for d in confirm_data if d['整合性'] == "⚠️"])
    if mismatch_count > 0:
        st.warning(f"⚠️ {mismatch_count}名の選手で順位回数の合計が試合数と一致していません")
    else:
        st.success("✅ すべての選手のデータが整合しています")

with col2:
    st.info("💡 「整合性」列: 順位回数の合計が試合数と一致しているかチェック")

# データテーブル表示
st.dataframe(
    confirm_df,
    hide_index=True,
    width="stretch",
    column_config={
        "ポイント": st.column_config.NumberColumn(format="%.1f"),
        "整合性": st.column_config.TextColumn(width="small")
    }
)

# ========== チームスコア整合性チェック ==========
st.markdown("---")
st.subheader("📊 チームスコア整合性チェック")

# チームごとの選手ポイント合計を計算
team_player_totals = {}
for player_data in st.session_state.stats_data:
    team_name = player_data['team_name']
    team_id = player_data['team_id']
    if team_name not in team_player_totals:
        team_player_totals[team_name] = {
            'team_id': team_id,
            'players_total': 0.0
        }
    team_player_totals[team_name]['players_total'] += player_data['points']

# チームの登録スコアを取得
conn = get_connection()
cursor = conn.cursor()
cursor.execute("""
    SELECT tsp.team_id, tn.team_name, tsp.points
    FROM team_season_points tsp
    JOIN team_names tn ON tsp.team_id = tn.team_id AND tsp.season = tn.season
    WHERE tsp.season = ?
    ORDER BY tn.team_name
""", (selected_season,))
team_scores = cursor.fetchall()
conn.close()

# 整合性チェック結果を作成
team_check_data = []
inconsistent_teams = []

for team_id, team_name, team_points in team_scores:
    if team_name in team_player_totals:
        players_total = team_player_totals[team_name]['players_total']
        difference = team_points - players_total
        
        # 小数点誤差を考慮（0.1pt以内は整合とみなす）
        is_consistent = abs(difference) <= 0.1
        
        team_check_data.append({
            'チーム名': team_name,
            'チームスコア': team_points,
            '選手合計': players_total,
            '差分': difference,
            '整合性': '✅' if is_consistent else '⚠️'
        })
        
        if not is_consistent:
            inconsistent_teams.append(team_name)

if team_check_data:
    # 整合性サマリー
    if inconsistent_teams:
        st.warning(f"⚠️ {len(inconsistent_teams)}チームでスコアが不整合です: {', '.join(inconsistent_teams)}")
    else:
        st.success("✅ すべてのチームでスコアが整合しています")
    
    # チームスコア比較テーブル
    team_check_df = pd.DataFrame(team_check_data)
    
    st.dataframe(
        team_check_df,
        hide_index=True,
        column_config={
            'チームスコア': st.column_config.NumberColumn(format="%.1f"),
            '選手合計': st.column_config.NumberColumn(format="%.1f"),
            '差分': st.column_config.NumberColumn(format="%+.1f"),
            '整合性': st.column_config.TextColumn(width="small")
        }
    )
    
    st.info("💡 チームスコア（team_season_pointsテーブル）と選手スコア合計が一致しているかチェックします。差分が0.1pt以内は整合とみなします。")
else:
    st.info(f"ℹ️ {selected_season}シーズンのチームスコアが未登録です。先に「データ管理」ページでチームスコアを登録してください。")

# 統計情報
st.markdown("---")
st.subheader("📈 統計情報")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_players = len(st.session_state.stats_data)
    st.metric("総選手数", f"{total_players}名")

with col2:
    players_with_data = len([p for p in st.session_state.stats_data if p['games'] > 0])
    st.metric("成績入力済み", f"{players_with_data}名")

with col3:
    total_games = sum(p['games'] for p in st.session_state.stats_data)
    st.metric("総試合数", f"{total_games}試合")

with col4:
    total_points = sum(p['points'] for p in st.session_state.stats_data)
    st.metric("総ポイント", f"{total_points:.1f}pt")
