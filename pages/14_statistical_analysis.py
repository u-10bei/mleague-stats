import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import get_connection, show_sidebar_navigation
from ui import fit_chart, metric_row

st.set_page_config(
    page_title="統計分析 | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide",
)

show_sidebar_navigation()

# 単色の系列と、濃淡・正負の配色。
# 正負 (平均からのずれ) は青↔赤の 2 色に灰の中点、大きさ (割合) は青の濃淡。
# 濃い側を中くらいの青で止めるのは、セルの上の黒い数字を読めるようにするため。
BLUE = "#2a78d6"
SEQUENTIAL = [[0, "#f3f7fd"], [1, "#6fa6ea"]]
DIVERGING = [[0, "#e98a89"], [0.5, "#f0efec"], [1, "#7fb0ee"]]

SEATS = ["東", "南", "西", "北"]
RANKS = [1, 2, 3, 4]

# 自由度 9 (席 4 × 着順 4) のカイ二乗分布の上側 5% 点
CHI2_CRIT_DF9 = 16.92


@st.cache_data(show_spinner="集計中...")
def load():
    """半荘単位と局単位のデータをまとめて読む。期間の絞り込みは画面側で行う。"""
    con = get_connection(readonly_local=True)
    try:
        results = pd.read_sql_query(
            "SELECT game_id, season, stage, table_type, seat_name, player_id,"
            "       points, rank, score"
            "  FROM game_results", con)
        # 局ごとの終了時点の順位。kyoku_player_result の score/rank は
        # その局を精算したあとの値 (最終局の値は半荘の最終結果と一致する)。
        kyoku = pd.read_sql_query(
            "SELECT k.id AS kyoku_id, k.game_id, k.round, k.honba_count"
            "  FROM src.kyoku k", con)
        kyoku_rank = pd.read_sql_query(
            "SELECT kyoku_id, player_id, rank FROM src.kyoku_player_result", con)
    finally:
        con.close()
    return results, kyoku, kyoku_rank


results, kyoku, kyoku_rank = load()
# データ上の最新シーズンは進行中。推移グラフでは「暫定」と添える
current_season = results.season.max()


def season_label(s):
    return f"{s}（暫定）" if s == current_season else str(s)

st.title("📈 統計分析")
st.markdown(
    "チームや選手に関係なく、**リーグ全体の傾向**を見るページです。"
    "席順による有利・不利、半荘の長さ、着順ごとの素点、途中経過からの逆転を、"
    "すべての対局をまとめて集計します。")

# ========== 絞り込み ==========
seasons = sorted(results.season.unique(), reverse=True)
stage_names = {"全ステージ": None, "レギュラー": "regular",
               "セミファイナル": "semifinal", "ファイナル": "final"}

col1, col2 = st.columns(2)
with col1:
    period = st.selectbox("期間", ["全期間"] + seasons,
                          format_func=lambda s: s if s == "全期間" else f"{s} シーズン")
with col2:
    stage_label = st.selectbox("ステージ", list(stage_names))

r = results
if period != "全期間":
    r = r[r.season == period]
if stage_names[stage_label]:
    r = r[r.stage == stage_names[stage_label]]

if r.empty:
    st.warning("選択した条件に該当する対局がありません。")
    st.stop()

game_ids = set(r.game_id)
n_games = len(game_ids)
k = kyoku[kyoku.game_id.isin(game_ids)]
st.caption(f"対象: {n_games:,} 半荘 / {len(k):,} 局")

tab_seat, tab_len, tab_score, tab_turn = st.tabs(
    ["🧭 席順", "⏱️ 半荘の長さ", "💯 素点と着順", "🔄 逆転"])


def pct(x):
    return f"{x:.1f}%"


# ========== 席順 ==========
with tab_seat:
    st.subheader("席順による有利・不利")
    st.markdown(
        "東 = 起家（東 1 局の親）。席ごとに着順の割合と平均ポイントを比べます。"
        "どの席も着順が均等なら、各着順は 25% ずつになります。")

    seat = (r.groupby("seat_name")
            .agg(games=("rank", "size"), avg_points=("points", "mean"),
                 sd_points=("points", "std"), avg_rank=("rank", "mean"))
            .reindex(SEATS))
    counts = (pd.crosstab(r.seat_name, r["rank"])
              .reindex(index=SEATS, columns=RANKS, fill_value=0))
    rates = counts.div(seat.games, axis=0) * 100
    seat["ci"] = 1.96 * seat.sd_points / seat.games.pow(0.5)

    # 席と着順に関係があるか (独立性のカイ二乗検定)。同着があるので
    # 期待度数は各席の対局数 × 着順ごとの全体の割合で出す。
    expected = pd.DataFrame(
        [[g * counts[k_].sum() / counts.values.sum() for k_ in RANKS]
         for g in seat.games], index=SEATS, columns=RANKS)
    chi2 = float(((counts - expected) ** 2 / expected).values.sum())
    if expected.values.min() < 5:
        # 期待度数が 5 を切るとカイ二乗の近似が効かない
        st.info(f"対局数が {n_games} 半荘と少ないため、席による偏りの有無は判断できません。")
    elif chi2 >= CHI2_CRIT_DF9:
        st.warning(
            f"**席と着順には関係がありそうです**（カイ二乗値 {chi2:.1f}。"
            f"偶然でもこれ以上になる確率は 5% 未満の目安 {CHI2_CRIT_DF9} を超えています）。")
    else:
        st.success(
            f"**席による着順の偏りは、偶然の範囲に収まっています**（カイ二乗値 {chi2:.1f}。"
            f"偶然でもこの程度は起きる目安 {CHI2_CRIT_DF9} 未満）。")

    left, right = st.columns(2)
    with left:
        fig = go.Figure(go.Scatter(
            x=SEATS, y=seat.avg_points,
            error_y=dict(type="data", array=seat.ci, thickness=2, width=8,
                         color=BLUE),
            mode="markers", marker=dict(size=12, color=BLUE),
            customdata=seat[["ci", "games"]].values,
            hovertemplate="%{x}家<br>平均 %{y:+.2f}pt"
                          "<br>95%区間 ±%{customdata[0]:.2f}pt"
                          "<br>%{customdata[1]:,}半荘<extra></extra>",
        ))
        fig.add_hline(y=0, line=dict(color="#9a9a96", width=1, dash="dot"))
        fig.update_layout(
            title="席ごとの平均ポイント（縦線は 95% 区間）",
            yaxis_title="pt", height=380, showlegend=False)
        fit_chart(fig)
        st.plotly_chart(fig, width="stretch")
        st.caption("縦線が 0 をまたいでいれば、その席の有利・不利ははっきりしません。")

    with right:
        diff = rates - 25
        lim = max(3.0, float(diff.abs().values.max()))
        fig = go.Figure(go.Heatmap(
            z=diff.values, x=[f"{k_}位" for k_ in RANKS], y=SEATS,
            zmin=-lim, zmax=lim, colorscale=DIVERGING,
            text=rates.map(pct).values, texttemplate="%{text}",
            textfont=dict(size=14, color="#1a1a19"),
            customdata=counts.values,
            hovertemplate="%{y}家 %{x}<br>%{text}（%{customdata:,}回）"
                          "<br>25% との差 %{z:+.1f}pt<extra></extra>",
            colorbar=dict(title="25%との差", ticksuffix="pt", len=0.8),
        ))
        fig.update_layout(title="席 × 着順の割合", height=380,
                          yaxis=dict(autorange="reversed"))
        fit_chart(fig)
        st.plotly_chart(fig, width="stretch")
        st.caption("青は 25% より多く、赤は少ない。色が薄いほど 25% に近い。")

    table = pd.DataFrame({
        "席": SEATS,
        "半荘": seat.games.astype(int).values,
        "平均pt": [f"{v:+.2f}" for v in seat.avg_points],
        "95%区間": [f"±{v:.2f}" for v in seat.ci],
        "平均順位": [f"{v:.3f}" for v in seat.avg_rank],
        **{f"{k_}位率": [pct(v) for v in rates[k_]] for k_ in RANKS},
    })
    st.dataframe(table, hide_index=True, width="stretch")

# ========== 半荘の長さ ==========
with tab_len:
    st.subheader("1 半荘の局数")
    st.markdown(
        "本場（連荘・流局）も 1 局と数えます。M リーグは飛び終了がなく、"
        "東 1 局〜南 4 局の 8 局が最短です。")

    per_game = k.groupby("game_id").size()
    c1, c2, c3, c4 = metric_row(4)
    c1.metric("平均", f"{per_game.mean():.2f} 局")
    c2.metric("中央値", f"{per_game.median():.0f} 局")
    c3.metric("最短（8 局）で終わった", pct((per_game == 8).mean() * 100))
    c4.metric("最長", f"{per_game.max()} 局")

    dist = per_game.value_counts().sort_index()
    fig = go.Figure(go.Bar(
        x=dist.index, y=dist.values / len(per_game) * 100,
        marker=dict(color=BLUE, cornerradius=4),
        customdata=dist.values,
        hovertemplate="%{x} 局<br>%{y:.1f}%（%{customdata:,} 半荘）<extra></extra>",
    ))
    fig.update_layout(title="局数の分布", xaxis_title="局数",
                      yaxis_title="半荘の割合（%）", height=360, bargap=0.15,
                      xaxis=dict(dtick=1))
    fit_chart(fig)
    st.plotly_chart(fig, width="stretch")

    if period == "全期間":
        season_of = r.drop_duplicates("game_id").set_index("game_id").season
        trend = per_game.groupby(season_of.reindex(per_game.index)).mean()
        fig = go.Figure(go.Scatter(
            x=[season_label(s) for s in trend.index], y=trend.values, mode="lines+markers",
            line=dict(color=BLUE, width=2), marker=dict(size=8),
            hovertemplate="%{x}<br>平均 %{y:.2f} 局<extra></extra>",
        ))
        fig.update_layout(title="シーズンごとの平均局数（局）", xaxis=dict(type="category"),
                          height=320, showlegend=False)
        fit_chart(fig)
        st.plotly_chart(fig, width="stretch")

    # 親の連荘の長さ。同じ round が続いた回数の最大を局ごとに取る。
    renchan = k.groupby(["game_id", "round"]).honba_count.max()
    st.caption(
        f"1 つの局で積まれた本場の最大は {int(renchan.max())} 本場、"
        f"5 本場以上まで続いたのは {int((renchan >= 5).sum()):,} 回です。")

# ========== 素点と着順 ==========
with tab_score:
    st.subheader("着順ごとの素点")
    st.markdown("持ち点 25,000 点スタート。素点は半荘終了時の持ち点です。")

    by_rank = r.groupby("rank").score
    top_scores = r[r["rank"] == 1].groupby("game_id").score.max()
    minus_games = r[r.score < 0].game_id.nunique()

    c1, c2, c3 = metric_row(3)
    c1.metric("トップの平均素点", f"{top_scores.mean():,.0f} 点")
    c2.metric("トップが 50,000 点以上", pct((top_scores >= 50000).mean() * 100))
    c3.metric("箱下（マイナス）が出た半荘", pct(minus_games / n_games * 100))

    fig = go.Figure()
    for k_ in RANKS:
        fig.add_trace(go.Box(
            y=r[r["rank"] == k_].score, name=f"{k_}位",
            marker=dict(color=BLUE, size=4), line=dict(color=BLUE, width=2),
            fillcolor="rgba(42,120,214,0.15)", boxpoints="outliers",
            hovertemplate="%{y:,} 点<extra></extra>",
        ))
    fig.add_hline(y=25000, line=dict(color="#9a9a96", width=1, dash="dot"),
                  annotation_text="25,000", annotation_position="top left")
    fig.update_layout(title="着順ごとの素点の分布（点）",
                      height=420, showlegend=False)
    fit_chart(fig)
    st.plotly_chart(fig, width="stretch")
    st.caption("箱が中央の半分、箱の中の線が中央値、点は外れ値です。")

    st.dataframe(pd.DataFrame({
        "着順": [f"{k_}位" for k_ in RANKS],
        "平均": [f"{by_rank.mean()[k_]:,.0f}" for k_ in RANKS],
        "中央値": [f"{by_rank.median()[k_]:,.0f}" for k_ in RANKS],
        "最低": [f"{by_rank.min()[k_]:,.0f}" for k_ in RANKS],
        "最高": [f"{by_rank.max()[k_]:,.0f}" for k_ in RANKS],
    }), hide_index=True, width="stretch")

    if period == "全期間":
        season_of = r.drop_duplicates("game_id").set_index("game_id").season
        trend = top_scores.groupby(season_of.reindex(top_scores.index)).mean()
        fig = go.Figure(go.Scatter(
            x=[season_label(s) for s in trend.index], y=trend.values, mode="lines+markers",
            line=dict(color=BLUE, width=2), marker=dict(size=8),
            hovertemplate="%{x}<br>平均 %{y:,.0f} 点<extra></extra>",
        ))
        fig.update_layout(title="シーズンごとのトップの平均素点（点）", xaxis=dict(type="category"),
                          height=320, showlegend=False)
        fit_chart(fig)
        st.plotly_chart(fig, width="stretch")

# ========== 逆転 ==========
with tab_turn:
    st.subheader("途中の順位から、最終順位はどれだけ変わるか")

    point = st.radio(
        "時点", ["南入時点（東 4 局の終了時）", "オーラス開始時点"], horizontal=True)

    kk = k.sort_values("kyoku_id")
    if point.startswith("南入"):
        # 東場の最後の局 (東 4 局の本場を含む) の終了時
        at = kk[kk["round"].str.startswith("1z")].groupby("game_id").kyoku_id.max()
    else:
        # 南 4 局 (オーラス) の最初の局の、ひとつ前の局の終了時
        kk = kk.assign(prev=kk.groupby("game_id").kyoku_id.shift(1))
        at = kk[kk["round"] == "2z4"].groupby("game_id").prev.min().dropna()

    mid = kyoku_rank[kyoku_rank.kyoku_id.isin(set(at.astype(int)))]
    mid = mid.merge(kyoku[["kyoku_id", "game_id"]], on="kyoku_id")
    pair = mid.merge(r[["game_id", "player_id", "rank"]],
                     on=["game_id", "player_id"], suffixes=("_mid", "_final"))
    trans = (pd.crosstab(pair.rank_mid, pair.rank_final)
             .reindex(index=RANKS, columns=RANKS, fill_value=0))
    trans_pct = trans.div(trans.sum(axis=1), axis=0) * 100

    c1, c2, c3 = metric_row(3)
    c1.metric("トップがそのままトップ", pct(trans_pct.loc[1, 1]))
    c2.metric("ラスがそのままラス", pct(trans_pct.loc[4, 4]))
    c3.metric("ラスからトップへ", pct(trans_pct.loc[4, 1]))

    fig = go.Figure(go.Heatmap(
        z=trans_pct.values, x=[f"最終 {k_}位" for k_ in RANKS],
        y=[f"{k_}位" for k_ in RANKS], zmin=0, zmax=100,
        colorscale=SEQUENTIAL,
        text=trans_pct.map(pct).values, texttemplate="%{text}",
        textfont=dict(size=14, color="#1a1a19"),
        customdata=trans.values,
        hovertemplate="その時点 %{y} → %{x}<br>%{text}（%{customdata:,}回）"
                      "<extra></extra>",
        colorbar=dict(title="割合", ticksuffix="%", len=0.8),
    ))
    fig.update_layout(title=f"{point.split('（')[0]}の順位 → 最終順位",
                      yaxis=dict(title="その時点の順位", autorange="reversed"),
                      height=420)
    fit_chart(fig)
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "行ごとに合計 100%。対角線（左上→右下）が順位を守った割合です。"
        "同点は同順位として数えます。")

st.markdown("---")
st.caption("※ 半荘記録と、局ごとの精算後の持ち点・順位（konoui DB）から集計しています。")
