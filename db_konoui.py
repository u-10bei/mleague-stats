#!/usr/bin/env python3
"""
konoui/m-league-game-db を正データとして扱うための接続ヘルパー。

    data/database.sqlite3   konoui 配布DB (読み取り専用 / 毎シーズン差し替え / .gitignore)
    data/mleague_local.db   補完テーブルのみ (Git 管理してよい)

konoui DB を `src` として ATTACH し、既存アプリが参照しているテーブル名を
互換ビューで再現する。SQLite はビューから別の ATTACH 先を参照できないため、
互換ビューは永続化できず接続のたびに TEMP で作り直す。
副作用として、konoui DB を差し替えてもビュー定義が古いまま残る事故が起きない。

動作確認:
    python db_konoui.py
"""

import os
import sqlite3

# konoui 配布DB (正データ / 読み取り専用 / 562MB / .gitignore)
FULL_DB_PATH = "data/database.sqlite3"
# 配布DB からアプリが使うテーブルだけを抜き出した軽量DB (5MB / Git管理)
SLIM_DB_PATH = "data/mleague_konoui_slim.sqlite3"
# 補完テーブルを置く自前DB
LOCAL_DB_PATH = os.environ.get("MLEAGUE_LOCAL_DB_PATH", "data/mleague_local.db")
# 補完テーブル定義 + 互換ビュー定義
SETUP_SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "setup_views.sql")

# 互換ビューとして提供されるテーブル名
COMPAT_VIEWS = [
    "game_results",
    "players",
    "teams",
    "team_names",
    "player_teams",
    "player_season_stats",
    "team_season_points",
    "foul_plays",
]


class KonouiDatabaseNotFound(FileNotFoundError):
    """konoui 配布DB が見つからない場合に送出する。"""


def get_konoui_db_path():
    """使用する konoui DB のパスを決める。

    1. 環境変数 KONOUI_DB_PATH が指定されていればそれ
    2. 配布DB (562MB) があればそれ … ローカル開発向け。局・イベント単位の
       分析もできる
    3. 軽量DB (5MB) … Git 管理されているのでクローンしただけで動く。
       Streamlit Community Cloud はこれを使う

    どれも無ければ None を返す。
    """
    env = os.environ.get("KONOUI_DB_PATH")
    if env:
        return env
    for path in (FULL_DB_PATH, SLIM_DB_PATH):
        if os.path.exists(path):
            return path
    return None


def is_slim_db(path=None):
    """軽量DB を使っているかどうか。"""
    path = path or get_konoui_db_path()
    return bool(path) and os.path.basename(path) == os.path.basename(SLIM_DB_PATH)


def _konoui_missing_message():
    return (
        f"konoui DB が見つかりません ({FULL_DB_PATH} / {SLIM_DB_PATH})\n"
        "軽量DB はリポジトリに含まれています。配布DB を使う場合は:\n"
        "  curl -L -O https://github.com/konoui/m-league-game-db/releases/"
        "latest/download/database.zip\n"
        "  unzip database.zip -d data/\n"
        "軽量DB を作り直す場合は: python build_slim_db.py"
    )


def get_connection(readonly_local=False):
    """補完DBに接続し、konoui DB を `src` として ATTACH した接続を返す。

    互換ビュー (game_results, players, teams, ...) は TEMP ビューとして
    この接続上に構築される。
    """
    konoui_path = get_konoui_db_path()
    if konoui_path is None or not os.path.exists(konoui_path):
        raise KonouiDatabaseNotFound(_konoui_missing_message())

    os.makedirs(os.path.dirname(LOCAL_DB_PATH) or ".", exist_ok=True)

    # uri=True にしておくと ATTACH 側でも file: URI が解釈される
    local_uri = "file:{}{}".format(
        LOCAL_DB_PATH, "?mode=ro" if readonly_local else ""
    )
    con = sqlite3.connect(local_uri, uri=True)

    # konoui DB は正データなので必ず読み取り専用で開く
    konoui_uri = "file:{}?mode=ro".format(konoui_path)
    con.execute("ATTACH DATABASE ? AS src", (konoui_uri,))

    _setup(con)
    return con


def _setup(con):
    """補完テーブルを作成し、互換ビューを TEMP で構築する。"""
    with open(SETUP_SQL_PATH, encoding="utf-8") as f:
        script = f.read()
    con.executescript(script)


def check():
    """接続と互換ビューの動作確認。各ビューの行数を表示する。"""
    con = get_connection()
    try:
        path = get_konoui_db_path()
        print("konoui DB :", path,
              "(軽量DB)" if is_slim_db(path) else "(配布DB)")
        print("補完DB    :", LOCAL_DB_PATH)
        print()

        cov = con.execute(
            "SELECT MIN(game_date), MAX(game_date),"
            "       COUNT(DISTINCT game_id), COUNT(DISTINCT season)"
            "  FROM game_results"
        ).fetchone()
        print("カバー範囲: {} 〜 {} / 全{:,}試合 / {}シーズン".format(
            cov[0], cov[1], cov[2], cov[3]))
        print()

        print("互換ビュー:")
        for name in COMPAT_VIEWS:
            n = con.execute('SELECT COUNT(*) FROM "{}"'.format(name)).fetchone()[0]
            print("  {:22} {:>8,}".format(name, n))

        print()
        print("補完テーブル:")
        for name in ("game_time", "team_meta", "team_name_history",
                     "player_profile", "player_ratings", "rating_history",
                     "rating_state"):
            n = con.execute('SELECT COUNT(*) FROM main."{}"'.format(name)).fetchone()[0]
            print("  {:22} {:>8,}".format(name, n))
    finally:
        con.close()


if __name__ == "__main__":
    check()
