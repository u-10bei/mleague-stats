import streamlit as st

st.set_page_config(
    page_title="Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# メインページ（トップページ）
st.title("🀄 Mリーグダッシュボード")

st.markdown("""
## Mリーグとは

Mリーグは、2018年に発足した日本初のプロ麻雀リーグです。
各チームがドラフトで選手を獲得し、レギュラーシーズン・セミファイナル・ファイナルを戦います。

---

## このサイトについて

Mリーグの対戦結果を可視化し、チームや選手の成績を分析できるダッシュボードです。

### 📊 コンテンツ

- **年度別ポイントランキング**: 各シーズンのチーム別成績
- **累積ポイントランキング**: 全シーズン通算の成績

---

## チーム一覧
""")

import pandas as pd

# チーム情報を読み込み
teams_df = pd.read_csv("data/teams.csv")

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
st.subheader("📈 最新シーズン (2023) ハイライト")

season_df = pd.read_csv("data/team_season_points.csv")
latest = season_df[season_df["season"] == 2023].sort_values("rank")

col1, col2, col3 = st.columns(3)

with col1:
    winner = latest.iloc[0]
    st.metric(
        label="🥇 優勝",
        value=winner["team"],
        delta=f"{winner['points']:+.1f} pt"
    )

with col2:
    second = latest.iloc[1]
    st.metric(
        label="🥈 準優勝",
        value=second["team"],
        delta=f"{second['points']:+.1f} pt"
    )

with col3:
    third = latest.iloc[2]
    st.metric(
        label="🥉 3位",
        value=third["team"],
        delta=f"{third['points']:+.1f} pt"
    )

st.markdown("---")
st.caption("※ データはサンプルです。実際のMリーグ公式記録とは異なる場合があります。")
