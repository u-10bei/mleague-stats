import streamlit as st
from db import get_teams_for_display, get_season_points, show_sidebar_navigation

st.set_page_config(
    page_title="Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 共通サイドバーナビゲーションを表示
show_sidebar_navigation()

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
- **レーティング**: Elo風レーティングシステムで選手の相対的な実力を可視化

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
    st.caption("順位はレギュラー／セミファイナル／ファイナルの到達ステージを加味した最終順位です。")

    col1, col2, col3 = st.columns(3)

    with col1:
        winner = latest.iloc[0]
        st.metric(
            label="🥇 １位",
            value=winner["team_name"],
            delta=f"{winner['points']:+.1f} pt"
        )

    with col2:
        second = latest.iloc[1]
        st.metric(
            label="🥈 ２位",
            value=second["team_name"],
            delta=f"{second['points']:+.1f} pt"
        )

    with col3:
        third = latest.iloc[2]
        st.metric(
            label="🥉 ３位",
            value=third["team_name"],
            delta=f"{third['points']:+.1f} pt"
        )
else:
    st.info("シーズンデータがありません")

st.markdown("---")
st.caption(
    "※ 対局データは [konoui/m-league-game-db](https://github.com/konoui/m-league-game-db) "
    "を正データとしています。対局時間のみ公式ビューアからの OCR による補完データです。"
)
