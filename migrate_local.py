#!/usr/bin/env python3
"""
旧 data/mleague.db の補完データを data/mleague_local.db へ移し替える。

konoui DB を正データにすると player_id / team_id は konoui 側の ID が正になる。
旧 mleague.db の ID とは一致しないので、**選手名・チーム名で突き合わせる**。
ここを間違えると静かにデータがずれるため、突き合わせ結果は必ず表示し、
1 件でも解決できなければ中断する。

移行対象 (konoui DB に無い情報だけ):
    対局時間            game_results.start_time / end_time  → game_time
    チーム略称/カラー   teams.short_name / color            → team_meta
    チーム名履歴        team_names                          → team_name_history
    選手プロフィール    players.birth_date / pro_org        → player_profile
    レーティング        player_ratings / rating_history     → ratings.sqlite3

使い方:
    python migrate_local.py             # 移行実行
    python migrate_local.py --dry-run   # 突き合わせ結果の確認のみ
"""

import argparse
import os
import sqlite3
import sys

from db_konoui import get_connection

OLD_DB_PATH = os.environ.get("OLD_DB_PATH", "data/mleague.db")

# 旧DBの名称が konoui 側と綴りで一致しないチームの対応表。
# 空白の有無は正規化で吸収するので、ここに書くのは表記自体が異なるものだけ。
TEAM_NAME_ALIASES = {
    "EARTHJETS": "アースジェッツ",
}


def normalize(name):
    """突き合わせ用の正規化。空白 (半角/全角) を除去する。"""
    return (name or "").replace(" ", "").replace("　", "")


def build_player_map(old, con):
    """旧 player_id → konoui player_id を選手名で突き合わせる。"""
    new_by_name = {}
    for pid, name in con.execute("SELECT id, name FROM src.player"):
        new_by_name[normalize(name)] = pid

    mapping, unresolved = {}, []
    for old_id, name in old.execute("SELECT player_id, player_name FROM players"):
        new_id = new_by_name.get(normalize(name))
        if new_id is None:
            unresolved.append((old_id, name))
        else:
            mapping[old_id] = new_id
    return mapping, unresolved


def build_team_map(old, con):
    """旧 team_id → konoui team_id をチーム名で突き合わせる。

    konoui 側は現行名しか持たないため、旧DBの「最新シーズンのチーム名」で照合する。
    """
    new_by_name = {}
    for tid, name in con.execute("SELECT id, name FROM src.team"):
        new_by_name[normalize(name)] = tid

    mapping, unresolved = {}, []
    for (old_id,) in old.execute("SELECT team_id FROM teams ORDER BY team_id"):
        row = old.execute(
            "SELECT team_name FROM team_names WHERE team_id = ?"
            " ORDER BY season DESC LIMIT 1", (old_id,)
        ).fetchone()
        if not row:
            unresolved.append((old_id, "(チーム名履歴なし)"))
            continue
        latest = row[0]
        key = normalize(latest)
        key = TEAM_NAME_ALIASES.get(key, key)
        new_id = new_by_name.get(normalize(key))
        if new_id is None:
            unresolved.append((old_id, latest))
        else:
            mapping[old_id] = new_id
    return mapping, unresolved


def migrate_game_times(old, con):
    """旧 game_results の start_time / end_time を game_time へ移す。

    旧データは全て A 卓なので venue='A' で解決する。
    """
    rows = old.execute(
        "SELECT season, game_date, game_number, start_time, end_time"
        "  FROM game_results"
        " WHERE start_time IS NOT NULL OR end_time IS NOT NULL"
        " GROUP BY season, game_date, game_number"
    ).fetchall()

    moved, skipped = 0, []
    for season, date, gnum, start, end in rows:
        row = con.execute(
            "SELECT id FROM src.game"
            " WHERE date = ? AND day_game_number = ?"
            "   AND substr(m_league_game_id, -1) = 'A'",
            (date, gnum),
        ).fetchone()
        if row is None:
            skipped.append((season, date, gnum))
            continue
        con.execute(
            "INSERT INTO main.game_time (game_id, start_time, end_time, updated_at)"
            " VALUES (?, ?, ?, CURRENT_TIMESTAMP)"
            " ON CONFLICT(game_id) DO UPDATE SET"
            "   start_time = excluded.start_time,"
            "   end_time   = excluded.end_time,"
            "   updated_at = CURRENT_TIMESTAMP",
            (row[0], start, end),
        )
        moved += 1
    return moved, skipped


def migrate_team_meta(old, con, team_map):
    moved = 0
    for old_id, short_name, color in old.execute(
            "SELECT team_id, short_name, color FROM teams"):
        new_id = team_map.get(old_id)
        if new_id is None:
            continue
        con.execute(
            "INSERT INTO main.team_meta (team_id, short_name, color)"
            " VALUES (?, ?, ?)"
            " ON CONFLICT(team_id) DO UPDATE SET"
            "   short_name = excluded.short_name, color = excluded.color",
            (new_id, short_name, color),
        )
        moved += 1
    return moved


def migrate_team_names(old, con, team_map):
    moved = 0
    for old_id, season, name in old.execute(
            "SELECT team_id, season, team_name FROM team_names"):
        new_id = team_map.get(old_id)
        if new_id is None:
            continue
        con.execute(
            "INSERT INTO main.team_name_history (team_id, season, team_name)"
            " VALUES (?, ?, ?)"
            " ON CONFLICT(team_id, season) DO UPDATE SET"
            "   team_name = excluded.team_name",
            (new_id, season, name),
        )
        moved += 1
    return moved


def migrate_player_profiles(old, con, player_map):
    moved = 0
    for old_id, birth, org in old.execute(
            "SELECT player_id, birth_date, pro_org FROM players"):
        new_id = player_map.get(old_id)
        if new_id is None or (birth is None and org is None):
            continue
        con.execute(
            "INSERT INTO main.player_profile (player_id, birth_date, pro_org)"
            " VALUES (?, ?, ?)"
            " ON CONFLICT(player_id) DO UPDATE SET"
            "   birth_date = excluded.birth_date, pro_org = excluded.pro_org",
            (new_id, birth, org),
        )
        moved += 1
    return moved


def migrate_ratings(old, con, player_map):
    """レーティングは旧 player_id を含むため、本体も opponent_ids も変換する。"""
    ratings = 0
    for old_id, rating, games, updated in old.execute(
            "SELECT player_id, rating, games, last_updated FROM player_ratings"):
        new_id = player_map.get(old_id)
        if new_id is None:
            continue
        con.execute(
            "INSERT INTO ratings.player_ratings (player_id, rating, games, last_updated)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT(player_id) DO UPDATE SET"
            "   rating = excluded.rating, games = excluded.games,"
            "   last_updated = excluded.last_updated",
            (new_id, rating, games, updated),
        )
        ratings += 1

    con.execute("DELETE FROM ratings.rating_history")
    history = 0
    for (old_id, date, old_r, new_r, delta, opp, season, gnum) in old.execute(
            "SELECT player_id, game_date, old_rating, new_rating, delta,"
            "       opponent_ids, season, game_number FROM rating_history"
            " ORDER BY id"):
        new_id = player_map.get(old_id)
        if new_id is None:
            continue
        # opponent_ids は旧 ID のカンマ区切り。こちらも変換する。
        new_opp = opp
        if opp:
            parts = []
            for token in str(opp).split(","):
                token = token.strip()
                if not token:
                    continue
                try:
                    mapped = player_map.get(int(token))
                except ValueError:
                    mapped = None
                if mapped is not None:
                    parts.append(str(mapped))
            new_opp = ",".join(parts) if parts else None
        con.execute(
            "INSERT INTO ratings.rating_history"
            " (player_id, game_date, old_rating, new_rating, delta,"
            "  opponent_ids, season, game_number)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id, date, old_r, new_r, delta, new_opp, season, gnum),
        )
        history += 1
    return ratings, history


def main():
    parser = argparse.ArgumentParser(
        description="旧 mleague.db の補完データを mleague_local.db へ移行する")
    parser.add_argument("--dry-run", action="store_true",
                        help="突き合わせ結果の確認のみ (書き込まない)")
    args = parser.parse_args()

    if not os.path.exists(OLD_DB_PATH):
        print(f"旧DBが見つかりません: {OLD_DB_PATH}", file=sys.stderr)
        return 1

    old = sqlite3.connect("file:{}?mode=ro".format(OLD_DB_PATH), uri=True)
    con = get_connection()

    try:
        player_map, p_unresolved = build_player_map(old, con)
        team_map, t_unresolved = build_team_map(old, con)

        print("=== 名前による突き合わせ ===")
        print(f"選手: {len(player_map)} 件解決 / 未解決 {len(p_unresolved)} 件")
        for old_id, name in p_unresolved:
            print(f"  ✗ 旧player_id={old_id} '{name}'")

        print(f"チーム: {len(team_map)} 件解決 / 未解決 {len(t_unresolved)} 件")
        for old_id, name in t_unresolved:
            print(f"  ✗ 旧team_id={old_id} '{name}'")
        for old_id in sorted(team_map):
            new_name = con.execute("SELECT name FROM src.team WHERE id = ?",
                                   (team_map[old_id],)).fetchone()[0]
            old_name = old.execute(
                "SELECT team_name FROM team_names WHERE team_id = ?"
                " ORDER BY season DESC LIMIT 1", (old_id,)).fetchone()[0]
            mark = " (別表記)" if normalize(old_name) != normalize(new_name) else ""
            print(f"  ✓ {old_id:2} '{old_name}' → {team_map[old_id]:2} '{new_name}'{mark}")

        if p_unresolved or t_unresolved:
            print("\n未解決があるため中断します。"
                  "TEAM_NAME_ALIASES に対応表を追加してください。", file=sys.stderr)
            return 1

        if args.dry_run:
            print("\n--dry-run のため書き込みませんでした。")
            return 0

        print()
        print("=== 移行 ===")
        moved, skipped = migrate_game_times(old, con)
        print(f"対局時間          : {moved} 試合")
        for season, date, gnum in skipped:
            print(f"  ✗ 該当試合なし: {date} 第{gnum}試合 (season={season})")

        print(f"チーム略称/カラー  : {migrate_team_meta(old, con, team_map)} 件")
        print(f"チーム名履歴      : {migrate_team_names(old, con, team_map)} 件")
        print(f"選手プロフィール   : {migrate_player_profiles(old, con, player_map)} 件")
        r, h = migrate_ratings(old, con, player_map)
        print(f"レーティング      : {r} 人 / 履歴 {h} 件")

        con.commit()
        print("\n✓ 移行完了")
        return 0
    finally:
        old.close()
        con.close()


if __name__ == "__main__":
    sys.exit(main())
