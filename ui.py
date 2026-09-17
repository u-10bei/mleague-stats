#!/usr/bin/env python3
"""画面まわりの共通設定。

Streamlit は素のままだとデスクトップ幅を前提にしたレイアウトになる。
このモジュールは、スマホ・タブレットで見たときに崩れるところを
CSS のメディアクエリでまとめて手当てする。

    db.show_sidebar_navigation()
        └ hide_default_sidebar_navigation()
            └ inject_responsive_css()     ← ここから全ページに入る

全ページが show_sidebar_navigation() を 1 回ずつ呼んでいるので、
CSS の注入もそこに相乗りさせれば各ページを触らずに済む。

Python 側からは画面幅が分からない (Streamlit はサーバ側で描画を組み立てる)
ため、幅で切り替わるものはすべて CSS 側に寄せている。Python 側で直すのは
グラフの余白やデータフレームの列順のように、CSS では届かないところだけ。
"""

import streamlit as st

# 折り返しの境目。
#
#   MOBILE  640px  Streamlit が st.columns を縦積みに切り替える幅と同じ。
#                  iPhone 16 が 393px、Pixel 9 が 412px なので一括りにできる。
#   TABLET 1024px  iPad 縦 (820px) が入る。サイドバーは開いたままだが
#                  本文が痩せるので、サイドバー幅のほうを詰める。
MOBILE = 640
TABLET = 1024

RESPONSIVE_CSS = f"""
<style>
/* metric_row() が置く目印。場所を示すだけなので描画はしない */
.metric-row-marker {{ display: none; }}
div[data-testid="stElementContainer"]:has(> div[data-testid="stMarkdown"] .metric-row-marker) {{
    display: none !important;
}}

/* ------------------------------------------------------------------ *
 * タブレット (〜{TABLET}px)
 * ------------------------------------------------------------------ */
@media (max-width: {TABLET}px) {{
    /* 既定の 336px は iPad 縦 (820px) だと本文を 480px まで削る。
       メニューの文字は 15px 級なので 232px あれば折り返さない。 */
    section[data-testid="stSidebar"] {{
        width: 232px !important;
        min-width: 232px !important;
    }}
    section[data-testid="stSidebar"] > div {{
        width: 232px !important;
        min-width: 232px !important;
    }}

    /* 本文の左右余白。既定の 5rem は、この幅では効きすぎる */
    section[data-testid="stMain"] .block-container {{
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        padding-top: 3.5rem;
    }}
}}

/* ------------------------------------------------------------------ *
 * スマホ (〜{MOBILE}px)
 * ------------------------------------------------------------------ */
@media (max-width: {MOBILE}px) {{

    /* --- 見出し ---------------------------------------------------- *
     * 既定の h1 は 2.75rem。390px 幅では「年度別ポイントランキング」が
     * 3 行に折り返して 1 画面の 1/3 を食う。日本語の見出しは字数が多いので
     * デスクトップ比 6 割まで落とす。 */
    section[data-testid="stMain"] h1 {{
        font-size: 1.65rem !important;
        line-height: 1.3 !important;
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        word-break: auto-phrase;      /* 文節で折り返す (対応外なら無視される) */
    }}
    section[data-testid="stMain"] h2 {{
        font-size: 1.35rem !important;
        line-height: 1.35 !important;
        padding-top: 0.75rem !important;
        padding-bottom: 0.25rem !important;
        word-break: auto-phrase;
    }}
    section[data-testid="stMain"] h3 {{
        font-size: 1.15rem !important;
        line-height: 1.4 !important;
        padding-top: 0.5rem !important;
        padding-bottom: 0.25rem !important;
        word-break: auto-phrase;
    }}

    /* --- 余白 ------------------------------------------------------ *
     * 縦に積み上がるぶん、1 要素あたりの余白が効いてくる。
     * 上下 6rem / 10rem の既定は、スクロール 1 画面ぶんの空白になる。 */
    section[data-testid="stMain"] .block-container {{
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
        padding-top: 2.75rem !important;
        padding-bottom: 3rem !important;
    }}

    /* --- メトリクスを 2 列に ---------------------------------------- *
     * Streamlit は {MOBILE}px 未満で st.columns を全部縦積みにする。
     * 4 つ並べたメトリクスが 4 画面ぶんの縦スクロールになるので、
     * メトリクスだけの行は 2 列に折り返したい。
     *
     * ただし「メトリクスだけの行」は CSS からは見分けられない。
     * :has() は子孫まで拾うので「グラフ｜ランキング表」の 2 分割でも
     * 右列の奥に統計サマリーが 1 つあれば一致してしまうし、子結合子で
     * 階層を固定しても、表とメトリクスが同じ列に同居している形
     * (7_player_season_ranking の右列) までは区別できない。
     *
     * そこで Python 側の metric_row() に目印を置いてもらい、その直後の
     * 行だけを対象にする。st.columns() は stLayoutWrapper に包まれて
     * 出てくることがあるので、目印の次の要素そのものと、その中の行の
     * 両方を見る。 */
    div[data-testid="stElementContainer"]:has(> div[data-testid="stMarkdown"] .metric-row-marker)
        + div[data-testid="stHorizontalBlock"],
    div[data-testid="stElementContainer"]:has(> div[data-testid="stMarkdown"] .metric-row-marker)
        + div[data-testid="stLayoutWrapper"] > div[data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap !important;
        gap: 0.5rem !important;
    }}
    div[data-testid="stElementContainer"]:has(> div[data-testid="stMarkdown"] .metric-row-marker)
        + div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
    div[data-testid="stElementContainer"]:has(> div[data-testid="stMarkdown"] .metric-row-marker)
        + div[data-testid="stLayoutWrapper"] > div[data-testid="stHorizontalBlock"]
        > div[data-testid="stColumn"] {{
        flex: 1 1 calc(50% - 0.5rem) !important;
        width: calc(50% - 0.5rem) !important;
        min-width: calc(50% - 0.5rem) !important;
    }}
    /* 値は 2rem 級。チーム名が入ると省略記号で切れるので縮めて折り返す。
       折り返しを止めているのは内側の stMarkdownContainer と p なので、
       そこまで降りて上書きする。 */
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] div[data-testid="stMarkdownContainer"],
    div[data-testid="stMetricValue"] p {{
        font-size: 1.15rem !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        overflow-wrap: anywhere;
        line-height: 1.3 !important;
    }}
    div[data-testid="stMetricLabel"] p {{
        font-size: 0.78rem !important;
    }}
    div[data-testid="stMetricDelta"] {{
        font-size: 0.8rem !important;
    }}

    /* --- 要素ツールバー -------------------------------------------- *
     * st.dataframe / st.plotly_chart の右上ツールバーは既定で
     * top: -2.4rem。狭い画面では直前の selectbox や見出しに重なる。
     * 要素の内側に入れ、背景を敷いて下の文字と混ざらないようにする。 */
    div[data-testid="stElementToolbar"] {{
        top: 0.15rem !important;
        right: 0.15rem !important;
        background: rgba(255, 255, 255, 0.92) !important;
        border-radius: 0.4rem;
    }}

    /* --- グラフ ---------------------------------------------------- *
     * Plotly のモードバー (ズーム・保存など) はタッチでは押しにくく、
     * グラフタイトルに重なる。スマホでは畳む。 */
    div[data-testid="stPlotlyChart"] .modebar {{
        display: none !important;
    }}

    /* --- タブ ------------------------------------------------------ *
     * 「席順別 / 試合番号別 / 直対」のように 3 つ以上並ぶと折り返して
     * 下線がずれる。横スクロールにして 1 行に保つ。 */
    div[data-testid="stTabs"] div[role="tablist"] {{
        overflow-x: auto;
        flex-wrap: nowrap !important;
        scrollbar-width: none;
    }}
    div[data-testid="stTabs"] div[role="tablist"]::-webkit-scrollbar {{
        display: none;
    }}
    div[data-testid="stTabs"] button[role="tab"] {{
        flex: 0 0 auto;
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
    }}
    div[data-testid="stTabs"] button[role="tab"] p {{
        font-size: 0.88rem !important;
    }}

    /* --- 表 -------------------------------------------------------- *
     * 列は落とさず横スクロールで見せる方針 (どの列を大事にするかは
     * ページ側の列順と column_config で決めている)。指で掴んだときに
     * 慣性が効くようにしておく。 */
    div[data-testid="stDataFrame"] {{
        -webkit-overflow-scrolling: touch;
    }}

    /* --- 入力部品 --------------------------------------------------- *
     * iOS は入力欄のフォントが 16px 未満だと勝手に拡大する。
     * selectbox / text_input は 16px を下回らせない。 */
    div[data-testid="stSelectbox"] input,
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {{
        font-size: 16px !important;
    }}

    /* --- サイドバー ------------------------------------------------- *
     * 開いたときは画面を覆う形になる。既定の 336px だと 390px 幅の
     * 端末で本文が 54px しか残らず、閉じる操作の的が小さい。 */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div {{
        width: 17rem !important;
        min-width: 17rem !important;
    }}
}}
</style>
"""


def metric_row(n, **kwargs):
    """メトリクスを横に並べるための st.columns()。

    Streamlit は画面幅が 640px を切ると st.columns を 1 列に積む。
    4 つのメトリクスが 4 画面ぶんの縦スクロールになってしまうので、
    この関数で作った行だけはスマホでも 2 列を保つ。

    CSS からは「メトリクスだけの行」を見分けられないため、
    目印を 1 つ置いてから st.columns() を返している。
    目印そのものは表示されない。

        c1, c2, c3 = metric_row(3)
        with c1:
            st.metric("累積ポイント", "+1580.9")
    """
    st.markdown('<span class="metric-row-marker"></span>', unsafe_allow_html=True)
    return st.columns(n, **kwargs)


def inject_responsive_css():
    """スマホ・タブレット向けの CSS を流し込む。

    show_sidebar_navigation() 経由で全ページから 1 回ずつ呼ばれる。
    """
    st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------- #
# グラフ
# ---------------------------------------------------------------------- #
#
# Plotly の余白 (margin) は px 固定なので、デスクトップ幅で決めた値を
# そのままスマホへ持っていくと比率が変わる。
#
#   margin=dict(l=20, r=100) は
#     1200px の図では 左2% / 右8%   … 余裕のある余白
#      350px の図では 左6% / 右29%  … 棒を描く場所が残らない
#
# 横棒グラフではこれが効いて、390px 幅だとプロット領域が 100px 程度しか
# 残らず、棒の長短が読めなくなる。余白は最小限にし、軸ラベルのぶんは
# automargin に任せる。
#
# 画面幅は Python 側からは分からないので、「どの幅でも成り立つ値」を
# 選んでいる。デスクトップでは余白がやや締まるが、破綻はしない。

#: グラフ上下の余白。タイトルと軸名が入るぶんだけ。
_MARGIN = dict(l=10, r=14, t=44, b=44)


def fit_chart(fig, *, horizontal=False):
    """画面幅が変わっても潰れない余白・文字サイズに整える。

    horizontal : 横棒グラフのとき True。
        Y 軸にチーム名や選手名が並ぶので、目盛りの文字を一段小さくして
        automargin が確保する左余白を詰める。棒の脇に出す値は
        textposition="auto" にして、外側に入らなければ棒の中へ回す
        (既定の "outside" だと画面端で切れて "+82.9" が "3" になる)。
    """
    # タイトルを持たない図に title=dict(...) を渡すと、plotly.js が
    # 本文なしのタイトルを描こうとして "undefined" と出る。
    # 文字の大きさを触るのは、実際にタイトルがある図だけにする。
    if fig.layout.title.text:
        fig.update_layout(title=dict(font=dict(size=15)))

    # レーダー (Scatterpolar) は直交軸を持たず automargin も効かない。
    # 軸ラベルを置く余白を自前で確保しているので、そこは触らない。
    if any(t.type == "scatterpolar" for t in fig.data):
        fig.update_layout(font=dict(size=12))
        return fig

    # グラフの下に置いた横並びの凡例は、yanchor="bottom" のままだと
    # 指定位置から上へ伸びる。10 チームぶんがスマホ幅で 10 段に折り返すと、
    # そのぶんがグラフ本体に食い込んで線が読めなくなる。
    # yanchor="top" にすると下へ伸びるので、plotly が下余白を広げてくれる。
    legend = fig.layout.legend
    if legend.orientation == "h" and legend.y is not None and legend.y < 0:
        fig.update_layout(legend=dict(yanchor="top", font=dict(size=11)))

    # タイトルのない図に上余白 44px は空白になるだけ。
    margin = dict(_MARGIN, t=44 if fig.layout.title.text else 12)
    fig.update_layout(
        margin=margin,
        font=dict(size=12),
        xaxis=dict(automargin=True),
        yaxis=dict(automargin=True),
    )
    if horizontal:
        fig.update_yaxes(tickfont=dict(size=11))
        fig.update_traces(
            selector=dict(type="bar"),
            textposition="auto",
            textfont=dict(size=11),
            cliponaxis=False,
        )
    return fig
