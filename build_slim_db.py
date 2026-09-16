#!/usr/bin/env python3
"""
konoui 配布DB から、このアプリが実際に参照するテーブルだけを抜き出した
軽量DBを生成する。

配布DB は 562MB あり Git 管理できないが、アプリが互換ビュー経由で使うのは
11 テーブルだけで、局・イベント単位の巨大テーブル (player_state 80MB,
event 53MB, tenpai_yaku_event 22MB など) は一切参照していない。
抜き出すと 5MB 程度まで落ち、リポジトリに同梱して
Streamlit Community Cloud にそのままデプロイできる。

    python build_slim_db.py                 # data/database.sqlite3 から生成
    python build_slim_db.py --check         # 既存の軽量DBの中身を表示するだけ

konoui/m-league-game-db は MIT ライセンスで再配布が許可されている。
"""

import argparse
import os
import sqlite3
import sys
import time

from aggregates import AGGREGATES

# 互換ビュー (setup_views.sql) と validate_games.py が参照するテーブル。
# ここを増やすときは setup_views.sql の src.* 参照と揃えること。
TABLES = [
    "league_season",
    "season_stage",
    "team",
    "player",
    "player_team",
    "game",
    "game_player_result",
    "kyoku",
    "kyoku_player_result",
    "foul_play",
]

# 配布DB 側で定義されているビュー。定義をそのまま複製する。
VIEWS = ["team_season_stage_result"]

FULL_DB_PATH = os.environ.get("KONOUI_FULL_DB_PATH", "data/database.sqlite3")
SLIM_DB_PATH = os.environ.get("KONOUI_SLIM_DB_PATH", "data/mleague_konoui_slim.sqlite3")


def build(full_path, slim_path):
    if not os.path.exists(full_path):
        print(
            f"konoui 配布DB が見つかりません: {full_path}\n"
            "以下を実行して配置してください:\n"
            "  curl -L -O https://github.com/konoui/m-league-game-db/releases/"
            "latest/download/database.zip\n"
            "  unzip database.zip -d data/",
            file=sys.stderr,
        )
        return 1

    t0 = time.time()
    tmp_path = slim_path + ".tmp"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    os.makedirs(os.path.dirname(slim_path) or ".", exist_ok=True)

    con = sqlite3.connect(tmp_path)
    con.execute("ATTACH DATABASE ? AS src", ("file:{}?mode=ro".format(full_path),))

    print(f"{'テーブル':<24} {'行数':>10}")
    for table in TABLES:
        row = con.execute(
            "SELECT sql FROM src.sqlite_master WHERE name = ? AND type = 'table'",
            (table,),
        ).fetchone()
        if row is None:
            print(f"配布DB にテーブルがありません: {table}", file=sys.stderr)
            con.close()
            os.remove(tmp_path)
            return 1
        con.execute(row[0])
        con.execute('INSERT INTO "{0}" SELECT * FROM src."{0}"'.format(table))
        n = con.execute('SELECT COUNT(*) FROM "{}"'.format(table)).fetchone()[0]
        print(f"{table:<24} {n:>10,}")

    # 対象テーブルに付いているインデックスも複製する
    for name, sql in con.execute(
        "SELECT name, sql FROM src.sqlite_master"
        " WHERE type = 'index' AND sql IS NOT NULL"
    ).fetchall():
        tbl = con.execute(
            "SELECT tbl_name FROM src.sqlite_master WHERE name = ?", (name,)
        ).fetchone()[0]
        if tbl in TABLES:
            try:
                con.execute(sql)
            except sqlite3.OperationalError:
                pass

    for view in VIEWS:
        row = con.execute(
            "SELECT sql FROM src.sqlite_master WHERE name = ? AND type = 'view'",
            (view,),
        ).fetchone()
        if row is None:
            print(f"配布DB にビューがありません: {view}", file=sys.stderr)
            con.close()
            os.remove(tmp_path)
            return 1
        con.execute(row[0])

    # 事前集計。局・イベント単位のテーブルからしか出せない指標を
    # 選手×シーズン×ステージにまとめて焼き込む (aggregates.py)。
    print()
    print(f"{'事前集計':<30} {'行数':>10}")
    for name, select, index_cols in AGGREGATES:
        con.execute('CREATE TABLE "{}" AS {}'.format(name, select))
        con.execute('CREATE INDEX "idx_{}" ON "{}"({})'.format(name, name, index_cols))
        n = con.execute('SELECT COUNT(*) FROM "{}"'.format(name)).fetchone()[0]
        print(f"{name:<30} {n:>10,}")

    con.commit()
    con.execute("DETACH src")
    con.execute("VACUUM")
    con.close()

    os.replace(tmp_path, slim_path)

    full_mb = os.path.getsize(full_path) / 1024 / 1024
    slim_mb = os.path.getsize(slim_path) / 1024 / 1024
    print()
    print(f"生成: {slim_path}")
    print(f"  {full_mb:,.1f} MB → {slim_mb:,.1f} MB "
          f"({full_mb / slim_mb:.0f} 分の1) / {time.time() - t0:.1f}秒")
    return 0


def check(slim_path):
    if not os.path.exists(slim_path):
        print(f"軽量DB がありません: {slim_path}", file=sys.stderr)
        return 1
    con = sqlite3.connect("file:{}?mode=ro".format(slim_path), uri=True)
    print(f"{slim_path}  ({os.path.getsize(slim_path) / 1024 / 1024:,.1f} MB)")
    print()
    for table in TABLES:
        n = con.execute('SELECT COUNT(*) FROM "{}"'.format(table)).fetchone()[0]
        print(f"  {table:<24} {n:>10,}")
    print()
    for name, _, _ in AGGREGATES:
        n = con.execute('SELECT COUNT(*) FROM "{}"'.format(name)).fetchone()[0]
        print(f"  {name:<30} {n:>10,}")
    cov = con.execute("SELECT MIN(date), MAX(date), COUNT(*) FROM game").fetchone()
    print()
    print(f"  カバー範囲: {cov[0]} 〜 {cov[1]} / 全{cov[2]:,}試合")
    con.close()
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="konoui 配布DB から軽量DB を生成する")
    parser.add_argument("--check", action="store_true",
                        help="既存の軽量DB の中身を表示するだけ")
    parser.add_argument("--full", default=FULL_DB_PATH, help="konoui 配布DB のパス")
    parser.add_argument("--slim", default=SLIM_DB_PATH, help="生成する軽量DB のパス")
    args = parser.parse_args()

    if args.check:
        return check(args.slim)
    return build(args.full, args.slim)


if __name__ == "__main__":
    sys.exit(main())
