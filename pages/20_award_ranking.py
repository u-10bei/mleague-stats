import pandas as pd
import streamlit as st

import character as ch
from db import get_connection, show_sidebar_navigation

st.set_page_config(
    page_title="称号ランキング | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide",
)

show_sidebar_navigation()

PLACE_MARK = {1: "🥇", 2: "🥈", 3: "🥉"}


@st.cache_data(show_spinner="集計中...")
def load():
    """選手×シーズンの実測値と、表示に使う名簿をまとめて返す。"""
    con = get_connection(readonly_local=True)
    try:
        stats = ch.season_stats(con)
        players = pd.read_sql_query(
            "SELECT player_id, player_name FROM players", con)
        # チーム名はシーズンで変わるので、年度別の名前を持つ team_names から引く
        teams = pd.read_sql_query(
            "SELECT pt.season, pt.player_id, tn.team_name"
            " FROM player_teams pt"
            " JOIN team_names tn"
            "   ON tn.team_id = pt.team_id AND tn.season = pt.season", con)
    finally:
        con.close()
    return stats, players, teams


stats, players, teams = load()
name_of = players.set_index("player_id").player_name.to_dict()

seasons = sorted(stats.season.unique(), reverse=True)
# キャラクターシートと同じく、データ上の最新シーズンを進行中とみなす
current = seasons[0]

st.title("🏅 称号ランキング")
st.caption(
    "キャラクターシートの称号（シーズン個人賞 8 種）を、全選手の順位で並べます。"
    "全ステージを合算した通年成績で判定し、同じ記録なら同順位です。")

col1, col2 = st.columns([1, 1])
with col1:
    season = st.selectbox(
        "シーズン", seasons,
        format_func=lambda s: f"{s}（暫定）" if s == current else str(s))
with col2:
    min_games = st.number_input(
        "規定出場数（率の賞のみ）", min_value=1, max_value=100,
        value=ch.MIN_SEASON_GAMES, step=1,
        help="トップ率・ラス回避率・和了率・放銃率の低さ・平均和了巡目は、"
             "この出場数に届いた選手だけで順位を付けます。"
             f"キャラクターシートの称号は {ch.MIN_SEASON_GAMES} 戦で判定しています。")

if season == current:
    st.info(
        f"📅 {season} シーズンは進行中のため**暫定順位**です。"
        "キャラクターシートの称号には、シーズンが終わってから反映されます。")

per = stats[stats.season == season]
team_of = (teams[teams.season == season]
           .drop_duplicates("player_id").set_index("player_id").team_name.to_dict())


def ranking(col, ascending):
    d = per
    if col in ch.RATE_AWARD_COLS:
        d = d[d.total_game_count >= min_games]
    return ch.award_ranking(d, col, ascending)


rankings = {label: (ranking(col, asc), col, fmt)
            for label, col, asc, fmt in ch.AWARDS}

# ========== 各賞の上位 3 名 ==========
st.markdown("---")
st.subheader(f"🏆 各賞の上位 3 名｜{season}")

cols = st.columns(4)
for i, (label, (r, col, fmt)) in enumerate(rankings.items()):
    top = r[r.place <= ch.AWARD_PLACES]
    # 開幕直後の最多登板などは同順位が十数人並ぶので、カードは 3 行までにする
    more = len(top) - ch.AWARD_PLACES
    top = top.head(ch.AWARD_PLACES)
    lines = "".join(
        f"<div style='display:flex;justify-content:space-between;gap:8px;"
        f"padding:2px 0'><span>{PLACE_MARK.get(int(x.place), '')} "
        f"{name_of.get(x.player_id, x.player_id)}</span>"
        f"<span style='font-variant-numeric:tabular-nums'>"
        f"{fmt.format(getattr(x, col))}</span></div>"
        for x in top.itertuples())
    if more > 0:
        lines += (f"<div style='opacity:.7;font-size:13px;padding-top:2px'>"
                  f"ほか {more} 名（同順位）</div>")
    if not lines:
        lines = ("<div style='opacity:.7'>規定出場数に届いた選手がいません</div>"
                 if col in ch.RATE_AWARD_COLS else "<div>対象者なし</div>")
    with cols[i % 4]:
        st.markdown(
            f"<div style='border:1px solid rgba(128,128,128,.35);border-radius:6px;"
            f"padding:10px 12px;margin-bottom:12px'>"
            f"<div style='font-weight:700;margin-bottom:4px'>{label}</div>"
            f"{lines}</div>",
            unsafe_allow_html=True)

# ========== 賞ごとの全順位 ==========
st.markdown("---")
st.subheader("📋 賞ごとの全順位")

award = st.selectbox("賞", list(rankings))
r, col, fmt = rankings[award]
if r.empty:
    st.info(f"出場が {min_games} 戦に届いた選手がいません。"
            "上の「規定出場数」を下げると、暫定の順位を見られます。")
else:
    table = pd.DataFrame({
        "順位": [f"{PLACE_MARK.get(int(p), '')} {int(p)}位".strip() for p in r.place],
        "選手": [name_of.get(p, p) for p in r.player_id],
        "記録": [fmt.format(v) for v in r[col]],
        "出場": r.total_game_count.astype(int).values,
        "チーム": [team_of.get(p, "") for p in r.player_id],
    })
    st.dataframe(
        table, hide_index=True, width="stretch",
        height=min(len(table), 20) * 35 + 38,
        column_config={
            "順位": st.column_config.TextColumn(width="small", pinned=True),
            "選手": st.column_config.TextColumn(width="medium", pinned=True),
            "記録": st.column_config.TextColumn(width="small"),
            "出場": st.column_config.NumberColumn(width="small", format="%d戦"),
            "チーム": st.column_config.TextColumn(width="medium"),
        })

    if col in ch.RATE_AWARD_COLS:
        left_out = int((per.total_game_count < min_games).sum())
        if left_out:
            st.caption(f"出場が {min_games} 戦に届いていない {left_out} 名は、"
                       "この賞の順位に入れていません。")

with st.expander("ℹ️ 各賞の決め方"):
    st.markdown(
        "| 賞 | 記録 | 上位 |\n|---|---|---|\n"
        "| 個人スコア | 獲得ポイントの合計（ペナルティ込み） | 高い順 |\n"
        "| 最多登板 | 出場数 | 多い順 |\n"
        "| 最高スコア | 1 半荘の最高素点 | 高い順 |\n"
        "| トップ率 | 1 位の回数 ÷ 出場数 | 高い順 |\n"
        "| ラス回避率 | 4 位以外の回数 ÷ 出場数 | 高い順 |\n"
        "| 和了率 | 和了数 ÷ 参加した局数 | 高い順 |\n"
        "| 放銃率の低さ | 放銃数 ÷ 参加した局数 | 低い順 |\n"
        "| 平均和了巡目 | 和了までのツモ回数の平均 | 早い順 |\n")
    st.markdown(
        "率の賞（トップ率・ラス回避率・和了率・放銃率の低さ・平均和了巡目）は、"
        "規定出場数に届いた選手だけで順位を付けます。"
        "出場の少ない選手の率は 0% や 100% に振れやすいためです。"
        "キャラクターシートの称号は、終わったシーズンについて規定出場数 "
        f"{ch.MIN_SEASON_GAMES} 戦の 3 位までです。")
