"""補完データ管理

konoui DB (正データ) に無い情報だけを編集するページ。
対局結果・選手・チームのマスタは konoui DB が正なので、ここでは編集しない。

編集対象:
    対局時間          game_time           (OCR 取り込み / 手入力)
    チーム名履歴      team_name_history   (年度別の名称)
    チーム略称/カラー  team_meta
    選手プロフィール   player_profile      (生年月日 / 所属団体)

このページはデフォルトで無効。有効にするには次のいずれか:
    MLEAGUE_ADMIN=1 streamlit run app.py
    .streamlit/secrets.toml に enable_admin = true
"""

import sys

import pandas as pd
import streamlit as st

from db import get_connection, require_admin, show_sidebar_navigation
from validate_games import (
    DURATION_MAX,
    DURATION_MIN,
    PER_KYOKU_HIGH,
    PER_KYOKU_LOW,
    duration_minutes,
    import_times,
    resolve_game_id,
)

sys.path.append("..")

st.set_page_config(
    page_title="補完データ管理 | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide",
)
show_sidebar_navigation()

# 公開環境では無効。サイドバーから外すだけでは URL 直打ちで到達できるため、
# ページ側でも明示的に止める。
require_admin()

st.title("🛠️ 補完データ管理")
st.caption(
    "konoui DB を正データとしているため、対局結果・選手・チームのマスタは編集できません。"
    "ここでは konoui DB に無い情報だけを編集します。"
)

conn = get_connection()

tab_time, tab_team_name, tab_team_meta, tab_player = st.tabs(
    ["⏱️ 対局時間", "🏢 チーム名履歴", "🎨 チーム略称/カラー", "👤 選手プロフィール"]
)


# ---------------------------------------------------------------- 対局時間
with tab_time:
    st.subheader("対局時間")
    st.caption(
        "konoui DB に無い唯一の実データ。1 試合あたり開始時刻と終了時刻の 2 つだけ。"
    )

    total_games = conn.execute(
        "SELECT COUNT(DISTINCT game_id) FROM game_results"
    ).fetchone()[0]
    filled = conn.execute("SELECT COUNT(*) FROM main.game_time").fetchone()[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("全試合", f"{total_games:,}")
    c2.metric("登録済み", f"{filled:,}")
    c3.metric("未登録", f"{total_games - filled:,}")

    st.markdown("#### CSV 取り込み")
    st.code("date,match_number,venue,start_time,end_time\n"
            "2025-09-25,1,A,19:00,20:35\n"
            "2025-09-25,1,B,19:00,20:20", language="csv")
    st.caption("`venue` は 2025 シーズン以降の A卓/B卓。2024 以前は全て `A`（省略可）。"
               "該当試合が無い行はスキップして報告するので、OCR の読み違いでデータが壊れません。")

    uploaded = st.file_uploader("CSV を選択", type="csv", key="time_csv")
    if uploaded is not None and st.button("取り込む", key="do_import"):
        tmp_path = "/tmp/_mleague_ocr_upload.csv"
        with open(tmp_path, "wb") as f:
            f.write(uploaded.getbuffer())
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            import_times(conn, tmp_path)
        st.code(buf.getvalue() or "(出力なし)")
        st.rerun()

    st.markdown("#### 手入力")
    seasons = [r[0] for r in conn.execute(
        "SELECT DISTINCT season FROM game_results ORDER BY season DESC")]
    sel_season = st.selectbox("シーズン", seasons, key="time_season")

    games = pd.read_sql_query(
        """
        SELECT gr.game_id, gr.game_date, gr.game_number, gr.venue, gr.table_type,
               gt.start_time, gt.end_time
          FROM (SELECT game_id, game_date, game_number, venue, table_type, season
                  FROM game_results GROUP BY game_id) gr
          LEFT JOIN main.game_time gt ON gt.game_id = gr.game_id
         WHERE gr.season = ?
         ORDER BY gr.game_date, gr.game_number
        """,
        conn, params=(sel_season,),
    )

    only_missing = st.checkbox("未登録のみ表示", value=True, key="time_missing")
    view = games[games["start_time"].isna()] if only_missing else games

    if view.empty:
        st.success("このシーズンは全て登録済みです。")
    else:
        labels = {
            int(r.game_id): f"{r.game_date} 第{r.game_number}試合 ({r.venue}卓) {r.table_type}"
            for r in view.itertuples()
        }
        sel_game = st.selectbox(
            "試合", list(labels), format_func=lambda g: labels[g], key="time_game")

        cur = games[games["game_id"] == sel_game].iloc[0]
        c1, c2 = st.columns(2)
        start = c1.text_input(
            "開始時刻 (HH:MM)", value=cur["start_time"] or "", key="time_start")
        end = c2.text_input(
            "終了時刻 (HH:MM)", value=cur["end_time"] or "", key="time_end")

        if start and end:
            d = duration_minutes(start, end)
            if d is None:
                st.warning("時刻の書式が不正です (HH:MM)")
            else:
                st.info(f"所要時間: {d} 分")

        if st.button("保存", key="time_save"):
            if duration_minutes(start, end) is None:
                st.error("時刻の書式が不正です (HH:MM)")
            else:
                conn.execute(
                    "INSERT INTO main.game_time (game_id, start_time, end_time, updated_at)"
                    " VALUES (?, ?, ?, CURRENT_TIMESTAMP)"
                    " ON CONFLICT(game_id) DO UPDATE SET"
                    "   start_time = excluded.start_time,"
                    "   end_time   = excluded.end_time,"
                    "   updated_at = CURRENT_TIMESTAMP",
                    (int(sel_game), start, end),
                )
                conn.commit()
                st.success("保存しました")
                st.rerun()

    st.markdown("#### 異常検出")
    st.caption(
        f"要確認: 対局時間が {DURATION_MIN}〜{DURATION_MAX} 分の範囲外／"
        f"外れ値: 局数あたりの所要分が中央値の {PER_KYOKU_LOW} 倍未満・{PER_KYOKU_HIGH} 倍超。"
        " OCR の読み違いは「局数の割に極端に長い/短い」形で出ます。"
    )

    checked = pd.read_sql_query(
        """
        SELECT g.game_date, g.game_number, g.venue,
               t.start_time, t.end_time,
               (SELECT COUNT(*) FROM src.kyoku k WHERE k.game_id = t.game_id) AS kyoku
          FROM main.game_time t
          JOIN (SELECT game_id, game_date, game_number, venue
                  FROM game_results GROUP BY game_id) g ON g.game_id = t.game_id
         ORDER BY g.game_date, g.game_number
        """,
        conn,
    )
    if checked.empty:
        st.info("対局時間が登録されていません。")
    else:
        checked["分"] = [
            duration_minutes(s, e)
            for s, e in zip(checked["start_time"], checked["end_time"])
        ]
        checked = checked.dropna(subset=["分"])
        checked["分/局"] = checked["分"] / checked["kyoku"]
        median = checked["分/局"].median()
        low, high = median * PER_KYOKU_LOW, median * PER_KYOKU_HIGH

        out_range = checked[
            (checked["分"] < DURATION_MIN) | (checked["分"] > DURATION_MAX)]
        outlier = checked[(checked["分/局"] < low) | (checked["分/局"] > high)]

        c1, c2, c3 = st.columns(3)
        c1.metric("中央値", f"{median:.1f} 分/局")
        c2.metric("要確認", f"{len(out_range)} 件")
        c3.metric("外れ値", f"{len(outlier)} 件")

        if not out_range.empty:
            st.markdown("**要確認（範囲外）**")
            st.dataframe(out_range, width='stretch', hide_index=True)
        if not outlier.empty:
            st.markdown(f"**外れ値（許容 {low:.1f}〜{high:.1f} 分/局）**")
            st.dataframe(outlier, width='stretch', hide_index=True)
        if out_range.empty and outlier.empty:
            st.success("異常は検出されませんでした。")


# ------------------------------------------------------------ チーム名履歴
with tab_team_name:
    st.subheader("チーム名履歴")
    st.caption("konoui DB は現行名しか持たないため、年度別の名称を自前で持ちます。"
               "自前履歴があればそれを優先し、無ければ konoui の現行名を表示します。")

    df = pd.read_sql_query(
        """
        SELECT tn.season, tn.team_id, t.current_name AS 現行名,
               h.team_name AS 自前履歴, tn.team_name AS 表示名
          FROM team_names tn
          JOIN teams t ON t.team_id = tn.team_id
          LEFT JOIN main.team_name_history h
                 ON h.team_id = tn.team_id AND h.season = tn.season
         ORDER BY tn.season DESC, tn.team_id
        """,
        conn,
    )
    st.dataframe(df, width='stretch', hide_index=True)

    st.markdown("#### 編集")
    c1, c2 = st.columns(2)
    seasons_tn = sorted(df["season"].unique(), reverse=True)
    e_season = c1.selectbox("シーズン", seasons_tn, key="tn_season")
    rows = df[df["season"] == e_season]
    e_team = c2.selectbox(
        "チーム", rows["team_id"].tolist(),
        format_func=lambda t: rows[rows["team_id"] == t]["現行名"].iloc[0],
        key="tn_team")
    cur_name = rows[rows["team_id"] == e_team]["表示名"].iloc[0]
    new_name = st.text_input("そのシーズンのチーム名", value=cur_name, key="tn_name")

    c1, c2 = st.columns(2)
    if c1.button("保存", key="tn_save"):
        conn.execute(
            "INSERT INTO main.team_name_history (team_id, season, team_name)"
            " VALUES (?, ?, ?)"
            " ON CONFLICT(team_id, season) DO UPDATE SET team_name = excluded.team_name",
            (int(e_team), int(e_season), new_name),
        )
        conn.commit()
        st.success("保存しました")
        st.rerun()
    if c2.button("自前履歴を削除（現行名に戻す）", key="tn_del"):
        conn.execute(
            "DELETE FROM main.team_name_history WHERE team_id = ? AND season = ?",
            (int(e_team), int(e_season)),
        )
        conn.commit()
        st.success("削除しました")
        st.rerun()


# --------------------------------------------------------- チーム略称/カラー
with tab_team_meta:
    st.subheader("チーム略称 / カラー")
    st.caption("グラフの凡例と色に使います。未設定のチームは現行名と灰色で表示されます。")

    df = pd.read_sql_query(
        "SELECT team_id, current_name AS 現行名, short_name AS 略称,"
        "       color AS カラー, established AS 参入年"
        "  FROM teams ORDER BY team_id", conn)
    st.dataframe(df, width='stretch', hide_index=True)

    st.markdown("#### 編集")
    e_team = st.selectbox(
        "チーム", df["team_id"].tolist(),
        format_func=lambda t: df[df["team_id"] == t]["現行名"].iloc[0],
        key="tm_team")
    cur = df[df["team_id"] == e_team].iloc[0]

    c1, c2 = st.columns(2)
    short_name = c1.text_input("略称", value=cur["略称"] or "", key="tm_short")
    color = c2.color_picker("カラー", value=cur["カラー"] or "#888888", key="tm_color")

    if st.button("保存", key="tm_save"):
        conn.execute(
            "INSERT INTO main.team_meta (team_id, short_name, color)"
            " VALUES (?, ?, ?)"
            " ON CONFLICT(team_id) DO UPDATE SET"
            "   short_name = excluded.short_name, color = excluded.color",
            (int(e_team), short_name, color),
        )
        conn.commit()
        st.success("保存しました")
        st.rerun()


# ------------------------------------------------------------ 選手プロフィール
with tab_player:
    st.subheader("選手プロフィール")
    st.caption("氏名・かな・所属チームは konoui DB が正データです。"
               "ここでは生年月日と所属プロ団体だけを編集します。")

    df = pd.read_sql_query(
        "SELECT player_id, player_name AS 氏名, player_name_kana AS かな,"
        "       birth_date AS 生年月日, pro_org AS 所属団体"
        "  FROM players ORDER BY player_id", conn)

    only_missing = st.checkbox("未入力のみ表示", value=False, key="pp_missing")
    view = df[df["生年月日"].isna() | df["所属団体"].isna()] if only_missing else df
    st.dataframe(view, width='stretch', hide_index=True)

    st.markdown("#### 編集")
    e_player = st.selectbox(
        "選手", df["player_id"].tolist(),
        format_func=lambda p: df[df["player_id"] == p]["氏名"].iloc[0],
        key="pp_player")
    cur = df[df["player_id"] == e_player].iloc[0]

    c1, c2 = st.columns(2)
    birth = c1.text_input("生年月日 (YYYY-MM-DD)",
                          value=cur["生年月日"] or "", key="pp_birth")
    org = c2.text_input("所属プロ団体", value=cur["所属団体"] or "", key="pp_org")

    if st.button("保存", key="pp_save"):
        conn.execute(
            "INSERT INTO main.player_profile (player_id, birth_date, pro_org)"
            " VALUES (?, ?, ?)"
            " ON CONFLICT(player_id) DO UPDATE SET"
            "   birth_date = excluded.birth_date, pro_org = excluded.pro_org",
            (int(e_player), birth or None, org or None),
        )
        conn.commit()
        st.success("保存しました")
        st.rerun()

conn.close()
