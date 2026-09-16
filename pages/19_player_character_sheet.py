import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import character as ch
from db import get_connection, show_sidebar_navigation

sys.path.append("..")

st.set_page_config(
    page_title="キャラクターシート | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide",
)

show_sidebar_navigation()

# ランクの色。7 軸は強さではなく個性なので、S 側も G 側も「特徴あり」として
# 色を付け、真ん中を灰にする。
RANK_HIGH = "#1f6f5c"
RANK_LOW = "#a8402f"
RANK_MID = "#7c857f"
GOLD = "#8a6a1f"

PLACE_MARK = {1: "🥇", 2: "🥈", 3: "🥉"}


def rank_color(rank):
    if rank in ("S", "A", "B"):
        return RANK_HIGH
    if rank in ("F", "G"):
        return RANK_LOW
    return RANK_MID


@st.cache_data(show_spinner="キャラクターシートを計算中...")
def load():
    """全選手ぶんの計算結果と、表示に使う名簿をまとめて返す。"""
    con = get_connection(readonly_local=True)
    try:
        data = ch.build(con)
        players = pd.read_sql_query(
            "SELECT player_id, player_name FROM players", con)
        teams = pd.read_sql_query(
            "SELECT start_season_year AS season, player_id, team_name"
            " FROM player_season_stage_base GROUP BY 1, 2, 3", con)
        ratings = pd.read_sql_query(
            "SELECT player_id, rating FROM ratings.player_ratings", con)
    finally:
        con.close()
    return data, players, teams, ratings


data, players, teams, ratings = load()

name_of = players.set_index("player_id").player_name.to_dict()
games_of = data["career_raw"].set_index("player_id").total_game_count.to_dict()
# 通算の出場数が多い順に並べる
options = [int(p) for p in
           data["career_raw"].sort_values("total_game_count", ascending=False).player_id
           if p in name_of]

st.title("🎴 キャラクターシート")
st.caption(
    "7 軸のレーダーを土台に、ジョブ・とくせい・称号を重ねた選手カードです。"
    "7 軸は強さではなく個性を表すので、ランクは S も G も「特徴あり」を意味します。"
)

selected = st.selectbox(
    "選手を選択", options,
    format_func=lambda p: f"{name_of[p]}（{int(games_of[p])}戦）",
)
sheet = ch.sheet(data, selected)
player_name = name_of[selected]

team_rows = teams[teams.player_id == selected].sort_values("season")
team_label = team_rows.iloc[-1].team_name if len(team_rows) else ""
team_of_season = dict(zip(team_rows.season, team_rows.team_name))
rating = ratings[ratings.player_id == selected]
rating_value = f"{rating.iloc[0].rating:.0f}" if len(rating) else "—"

st.markdown("---")

# ========== ジョブ ==========
head_left, head_right = st.columns([3, 2])

with head_left:
    stars = "★" * len(sheet["stars"])
    st.markdown(
        f"<div style='font-size:12px;letter-spacing:.14em;color:{RANK_HIGH};"
        f"font-weight:700'>{team_label}</div>"
        f"<div style='font-size:26px;font-weight:600;letter-spacing:.04em'>"
        f"{player_name}"
        f"<span style='color:{GOLD};font-size:15px;margin-left:.6em'>{stars}</span>"
        f"</div>"
        f"<div style='font-size:11px;letter-spacing:.2em;color:{RANK_MID};"
        f"margin-top:16px'>ジョブ ｜ 通算</div>"
        f"<div style='font-size:42px;font-weight:600;line-height:1.2;"
        f"color:{RANK_HIGH}'>{sheet['job']}</div>",
        unsafe_allow_html=True,
    )
    if sheet["job_parts"]:
        st.dataframe(
            pd.DataFrame([
                {"役割": p["role"], "語": p["word"],
                 "由来": f"{p['axis']}{p['dir']}（{p['z']:+.2f}）",
                 "意味": p["desc"]}
                for p in sheet["job_parts"]
            ]),
            hide_index=True, width="stretch",
            column_config={
                "役割": st.column_config.TextColumn(width="small"),
                "語": st.column_config.TextColumn(width="small"),
                "由来": st.column_config.TextColumn(width="small"),
                "意味": st.column_config.TextColumn(width="large"),
            },
        )
    else:
        st.info(
            "1.0σ を超える軸がありません。どの軸にも寄っていないので"
            f"万能クラス（{data['vocab']['balanced']}）です。")

with head_right:
    c1, c2 = st.columns(2)
    c1.metric("Lv.", sheet["seasons_n"])
    c2.metric("出場", f"{sheet['games']}戦")
    c3, c4 = st.columns(2)
    c3.metric("レート", rating_value)
    c4.metric("和了率", f"{sheet['win_rate']:.1f}%")

st.markdown("---")

# ========== パラメータ ==========
st.subheader("📊 パラメータ")

latest = sheet["seasons"][-1] if sheet["seasons"] else None
radar_col, table_col = st.columns([1, 1])

with radar_col:
    labels = [f"{a} {sheet['career_rank'][a]}" for a in ch.AXES]
    loop = ch.AXES + [ch.AXES[0]]

    fig = go.Figure()
    if latest:
        fig.add_trace(go.Scatterpolar(
            r=[50 + 10 * latest["z"][a] for a in loop],
            theta=labels + [labels[0]],
            mode="lines", name=str(latest["season"]),
            line=dict(color=RANK_LOW, width=2, dash="dash"),
            hovertemplate="%{theta}<br>偏差値 %{r:.1f}<extra></extra>",
        ))
    fig.add_trace(go.Scatterpolar(
        r=[50 + 10 * sheet["career_z"][a] for a in loop],
        theta=labels + [labels[0]],
        fill="toself", name="通算",
        line=dict(color=RANK_HIGH, width=2.5),
        fillcolor="rgba(31,111,92,0.16)",
        hovertemplate="%{theta}<br>偏差値 %{r:.1f}<extra></extra>",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[25, 75], showticklabels=False, ticks="")),
        legend=dict(orientation="h", yanchor="bottom", y=-0.12,
                    xanchor="center", x=0.5),
        height=460, margin=dict(l=80, r=80, t=30, b=70),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("実線が通算、破線が最新シーズン。目盛りは偏差値（25〜75）。")

with table_col:
    rows = []
    for axis in ch.AXES:
        col, label, unit, invert = ch.AXIS_SOURCE[axis]
        mine = sheet["career_raw"][axis]
        avg = sheet["league_raw"][axis]
        rows.append({
            "軸": axis,
            "ランク": sheet["career_rank"][axis],
            "実測値": label + ("（逆）" if invert else ""),
            "本人": f"{mine:,.2f}{unit}",
            "リーグ": f"{avg:,.2f}{unit}",
            "差": f"{mine - avg:+,.2f}",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 height=(len(rows) + 1) * 35 + 3)
    st.caption(
        "「（逆）」は実測値が高いほど軸が低くなるもの。"
        "まもりは放銃率の裏返しです。リーグ値は全選手の素カウントを"
        "合算してから比にしたものです。")

st.markdown("---")

# ========== とくせい ==========
st.subheader("✨ とくせい ｜ シーズンごと")

if sheet["seasons"]:
    table = []
    for row in sheet["seasons"]:
        rec = {
            "シーズン": row["season"],
            "チーム": team_of_season.get(row["season"], ""),
            "戦": row["games"],
            "pt": row["points"],
        }
        rec.update({a: row["rank"][a] for a in ch.AXES})
        rec["とくせい"] = "・".join(t["name"] for t in row["traits"]) or "—"
        table.append(rec)
    df = pd.DataFrame(table)

    def style_rank(v):
        return f"color: {rank_color(v)}; font-weight: 700"

    styled = (df.style
              .map(style_rank, subset=ch.AXES)
              .format({"pt": "{:+.1f}"})
              .map(lambda v: f"color: {RANK_HIGH if v >= 0 else RANK_LOW}",
                   subset=["pt"]))
    st.dataframe(
        styled, hide_index=True, width="stretch",
        height=(len(df) + 1) * 35 + 3,
        column_config={
            "シーズン": st.column_config.NumberColumn(width="small", format="%d"),
            "チーム": st.column_config.TextColumn(width="medium"),
            "戦": st.column_config.NumberColumn(width="small"),
            "pt": st.column_config.NumberColumn(width="small"),
            "とくせい": st.column_config.TextColumn(width="large"),
            **{a: st.column_config.TextColumn(width="small") for a in ch.AXES},
        })

    picked = st.selectbox(
        "とくせいの中身を見るシーズン",
        [r["season"] for r in sheet["seasons"]][::-1],
        key="trait_season")
    detail = next(r for r in sheet["seasons"] if r["season"] == picked)
    if detail["traits"]:
        st.dataframe(
            pd.DataFrame([
                {"とくせい": t["name"], "分類": t["group"],
                 "選ばれた理由": t["desc"],
                 "本人": t["val"], "リーグ平均": t["avg"],
                 "z": f"{t['z']:+.2f}"}
                for t in detail["traits"]
            ]),
            hide_index=True, width="stretch")
    else:
        st.info(f"{picked} シーズンは、1.5σ を超える指標がありませんでした。")
else:
    st.info(f"{ch.MIN_SEASON_GAMES} 戦以上を消化したシーズンがまだありません。")

st.markdown("---")

# ========== 称号 ==========
st.subheader("🏅 称号 ｜ シーズン個人賞・3 位まで")

if sheet["titles"]:
    st.dataframe(
        pd.DataFrame([
            {"シーズン": t["season"],
             "順位": f"{PLACE_MARK.get(t['place'], '')} {t['place']}位",
             "賞": t["award"], "記録": t["value"]}
            for t in sheet["titles"]
        ]),
        hide_index=True, width="stretch")
else:
    st.info("8 賞のいずれでも 3 位に入っていません。")

if sheet["stars"]:
    st.markdown(
        "".join(
            f"<span style='display:inline-block;background:#f0e6cd;color:{GOLD};"
            f"border-radius:3px;padding:4px 12px;margin:2px 6px 2px 0;"
            f"font-size:13px'>★ {s['season']} {s['yaku']}"
            f"<span style='color:{RANK_MID};margin-left:8px;font-size:11px'>"
            f"{s['date']}</span></span>"
            for s in sheet["stars"]),
        unsafe_allow_html=True)

st.markdown("---")

# ========== 凡例 ==========
with st.expander("ℹ️ 読み方"):
    st.markdown("#### 7 軸")
    st.dataframe(
        pd.DataFrame([
            {"軸": a, "実測値": ch.AXIS_SOURCE[a][1],
             "高い": data["vocab"]["axes"][a + "高"]["desc"],
             "低い": data["vocab"]["axes"][a + "低"]["desc"]}
            for a in ch.AXES
        ]),
        hide_index=True, width="stretch")

    st.markdown("#### ランク")
    st.markdown(
        "偏差値を 8 段階にしたものです。"
        "**7 軸は強さではなく個性**なので、S も G も「特徴あり」を意味します。"
        "緑が高い側、朱が低い側、灰が中間です。")
    st.dataframe(
        pd.DataFrame([{"ランク": r, "偏差値": f"{lim} 以上"}
                      for lim, r in ch.RANK_STEPS] + [{"ランク": "G", "偏差値": "35 未満"}]),
        hide_index=True, width="stretch")

    st.markdown("#### ジョブ")
    st.markdown(
        f"通算の 7 軸のうち **{data['vocab']['job_threshold']}σ** を超えたものを強い順に並べ、"
        "1 番目からクラス名、2 番目から形容詞、3 番目から修飾を取って組み立てます"
        "（例: ねばり高 ＋ まもり低 →「大胆な闘士」）。"
        f"1 つも超えなければ万能クラス（{data['vocab']['balanced']}）です。")

    st.markdown("#### とくせい")
    st.markdown(
        f"7 軸とは別の {len(data['vocab']['traits'])} 種の指標のうち、"
        f"**{data['vocab']['trait_threshold']}σ** を超えたものが付きます。"
        "重ね着でき、付かないシーズンもあります。")

    st.markdown("#### 称号")
    st.markdown(
        "シーズン個人賞 8 種の 3 位までです。全ステージを合算した通年成績で判定し、"
        f"{ch.MIN_SEASON_GAMES} 戦以上を消化したシーズンだけが対象になります。"
        "★ は役満で、賞とは別に和了った回数だけ名前の横に付きます。")
    st.dataframe(
        pd.DataFrame([{"賞": label, "指標": col} for label, col, _, _ in ch.AWARDS]),
        hide_index=True, width="stretch")
