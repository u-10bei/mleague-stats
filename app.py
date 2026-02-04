import streamlit as st
from db import get_teams_for_display, get_season_points, hide_default_sidebar_navigation

st.set_page_config(
    page_title="Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

st.title("🀄 Mリーグダッシュボード")

st.markdown("""
## Mリーグとは

Mリーグは、2018年に発足した日本初のプロ麻雀リーグです。
各チームがドラフトで選手を獲得し、レギュラーシーズン・セミファイナル・ファイナルを戦います。

---

## このサイトについて

Mリーグの対戦結果を可視化し、チームや選手の成績を分析できるダッシュボードです。

### 📊 コンテンツ

**チーム成績**
- **年度別ランキング**: 各シーズンのチーム別成績
- **累積ランキング**: 全シーズン通算の成績
- **半荘別分析**: チームの対戦結果を詳細分析

**選手成績**
- **年度別ランキング**: 各シーズンの選手別成績
- **累積ランキング**: 全シーズン通算の選手成績
- **半荘別分析**: 選手の対戦成績を詳細分析

**その他の分析**
- **統計分析**: リーグ全体の統計情報
- **連続記録**: 連勝や連敗などの連続記録
- **対局記録**: 全試合の詳細記録

---

## チーム一覧
""")

# チーム情報を読み込み
teams_df = get_teams_for_display()

# チームをカード形式で表示
cols = st.columns(4)
for idx, row in teams_df.iterrows():
    with cols[idx % 4]:
        st.markdown(f"""
        <div style="
            background-color: {row['color']}20;
            border-left: 4px solid {row['color']};
            padding: 10px;
            margin: 5px 0;
            border-radius: 4px;
        ">
            <strong>{row['team_name']}</strong><br>
            <small>設立: {row['established']}年</small>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# 最新シーズンのハイライト
season_df = get_season_points()
if not season_df.empty:
    latest_season = season_df["season"].max()
    latest = season_df[season_df["season"] == latest_season].sort_values("rank")

    st.subheader(f"📈 最新シーズン ({latest_season}) ハイライト")

    col1, col2, col3 = st.columns(3)

    with col1:
        winner = latest.iloc[0]
        st.metric(
            label="🥇 レギュラー１位",
            value=winner["team_name"],
            delta=f"{winner['points']:+.1f} pt"
        )

    with col2:
        second = latest.iloc[1]
        st.metric(
            label="🥈 レギュラー２位",
            value=second["team_name"],
            delta=f"{second['points']:+.1f} pt"
        )

    with col3:
        third = latest.iloc[2]
        st.metric(
            label="🥉 レギュラー３位",
            value=third["team_name"],
            delta=f"{third['points']:+.1f} pt"
        )
else:
    st.info("シーズンデータがありません")

st.markdown("---")
st.caption("※ データはサンプルです。実際のMリーグ公式記録とは異なる場合があります。")
