#!/usr/bin/env python3
"""
konoui DB の整合性検証 ＋ 対局時間(OCR結果)の取り込み。

既存アプリの整合性チェックは M リーグ公式ルールに合っておらず、
正しいデータを誤判定していた。ここでは実データ全件で成立するルールだけを使う。

  - 着順 = 1 + 自分より素点が多い人数   (同点は同着 = 1224 方式、次の順位は欠番)
  - 同着の選手は素点もポイントも一致する (順位点は折半される)
  - 素点合計 = 100000 − 未回収供託×1000 (オーラス流局で未回収の供託は没収。
                                          不足は 1000 の倍数、最大 4 本)
  - ポイント合計 = 0                     (浮動小数のため許容誤差 0.05)

使い方:
    python validate_games.py                     # 全試合を検証
    python validate_games.py --import-times ocr.csv  # 対局時間を取り込む
    python validate_games.py --check-times       # 対局時間の異常検出のみ
"""

import argparse
import csv
import os
import statistics
import sys

from db_konoui import get_connection

# ポイント合計の許容誤差
POINTS_EPSILON = 0.05
# 供託は最大 4 本 (1000点棒)
MAX_KYOTAKU = 4
# 対局時間の妥当範囲 (分)
DURATION_MIN = 30
DURATION_MAX = 180
# 局数あたり所要分の外れ値判定 (中央値比)
PER_KYOKU_LOW = 0.6
PER_KYOKU_HIGH = 1.6


# =====================================================================
# 整合性検証
# =====================================================================

def check_one_game(con, game_id):
    """1 試合の整合性を検証し、エラーメッセージのリストを返す。

    空リストなら正常。入力画面のチェックにそのまま使える。
    """
    rows = con.execute(
        "SELECT player_id, score, league_points, penalty_league_points, rank"
        "  FROM src.game_player_result WHERE game_id = ?"
        " ORDER BY rank, player_id",
        (game_id,),
    ).fetchall()

    errors = []

    if len(rows) != 4:
        errors.append(f"参加人数が {len(rows)} 人 (4 人であるべき)")
        return errors

    scores = [r[1] for r in rows]
    points = [r[2] for r in rows]
    ranks = [r[4] for r in rows]

    # --- 着順 = 1 + 自分より素点が多い人数 (1224 方式) ---
    for pid, score, _pt, _pen, rank in rows:
        expected = 1 + sum(1 for s in scores if s > score)
        if rank != expected:
            errors.append(
                f"player {pid}: 着順 {rank} だが素点順では {expected} 位"
            )

    # --- 同着の選手は素点もポイントも一致する ---
    by_rank = {}
    for pid, score, pt, _pen, rank in rows:
        by_rank.setdefault(rank, []).append((pid, score, pt))
    for rank, members in by_rank.items():
        if len(members) > 1:
            if len({m[1] for m in members}) != 1:
                errors.append(f"{rank} 位が同着だが素点が一致しない")
            if len({round(m[2], 2) for m in members}) != 1:
                errors.append(f"{rank} 位が同着だがポイントが一致しない")

    # --- 素点合計 = 100000 − 未回収供託×1000 ---
    total_score = sum(scores)
    shortage = 100000 - total_score
    if shortage < 0:
        errors.append(f"素点合計が {total_score} (100000 を超えている)")
    elif shortage % 1000 != 0:
        errors.append(f"素点合計が {total_score} (不足 {shortage} が 1000 の倍数でない)")
    elif shortage // 1000 > MAX_KYOTAKU:
        errors.append(
            f"素点合計が {total_score} (未回収供託 {shortage // 1000} 本は最大 {MAX_KYOTAKU} 本を超える)"
        )

    # --- ポイント合計 = 0 (許容誤差 0.05) ---
    total_points = sum(points)
    if abs(total_points) > POINTS_EPSILON:
        errors.append(f"ポイント合計が {total_points:+.2f} (0 であるべき)")

    # --- 着順の重複・欠番が 1224 方式に沿うか ---
    for rank in ranks:
        if not 1 <= rank <= 4:
            errors.append(f"着順 {rank} が 1〜4 の範囲外")

    return errors


def validate_all(con):
    """全試合を検証する。異常があった試合数を返す。"""
    games = con.execute(
        "SELECT game_id, season, game_date, game_number, venue"
        "  FROM game_results GROUP BY game_id ORDER BY game_date, game_number"
    ).fetchall()

    print(f"整合性検証: 全 {len(games):,} 試合")

    ng = 0
    for game_id, season, date, gnum, venue in games:
        errors = check_one_game(con, game_id)
        if errors:
            ng += 1
            print(f"  NG game_id={game_id} {date} 第{gnum}試合 ({venue}卓) season={season}")
            for e in errors:
                print(f"       - {e}")

    if ng == 0:
        print(f"  ✓ 全 {len(games):,} 試合が整合")
    else:
        print(f"  ✗ {ng} 試合に異常")
    return ng


def report_stats(con):
    """実データの分布を表示する (既存チェックが誤判定していた項目)。"""
    tie = con.execute(
        "SELECT COUNT(DISTINCT game_id) FROM ("
        "  SELECT game_id, rank FROM src.game_player_result"
        "   GROUP BY game_id, rank HAVING COUNT(*) > 1)"
    ).fetchone()[0]

    short = con.execute(
        "SELECT COUNT(*) FROM ("
        "  SELECT game_id, SUM(score) s FROM src.game_player_result"
        "   GROUP BY game_id HAVING s <> 100000)"
    ).fetchone()[0]

    drift = con.execute(
        "SELECT COUNT(*) FROM ("
        "  SELECT game_id, SUM(league_points) t FROM src.game_player_result"
        "   GROUP BY game_id HAVING t <> 0 AND ABS(t) <= ?)",
        (POINTS_EPSILON,),
    ).fetchone()[0]

    penalty = con.execute(
        "SELECT COUNT(*) FROM src.game_player_result WHERE penalty_league_points <> 0"
    ).fetchone()[0]

    print()
    print("既存チェックが誤判定していた実データ:")
    print(f"  同着 (1224 方式)              {tie:>6} 試合")
    print(f"  素点合計 < 100000 (供託没収)  {short:>6} 試合")
    print(f"  ポイント合計の浮動小数誤差    {drift:>6} 試合")
    print(f"  ペナルティ (チョンボ等)       {penalty:>6} 件")


# =====================================================================
# 対局時間の取り込み
# =====================================================================

def _to_minutes(hhmm):
    h, m = hhmm.strip().split(":")
    return int(h) * 60 + int(m)


def duration_minutes(start, end):
    """開始〜終了の所要分。日跨ぎ (23:50→00:30) も扱う。"""
    if not start or not end:
        return None
    try:
        s = _to_minutes(start)
        e = _to_minutes(end)
    except (ValueError, AttributeError):
        return None
    if e < s:
        e += 24 * 60
    return e - s


def resolve_game_id(con, date, match_number, venue):
    """date + match_number + venue から src.game.id を解決する。"""
    venue = (venue or "A").strip().upper() or "A"
    row = con.execute(
        "SELECT id FROM src.game"
        " WHERE date = ? AND day_game_number = ?"
        "   AND substr(m_league_game_id, -1) = ?",
        (date.strip(), int(match_number), venue),
    ).fetchone()
    return row[0] if row else None


def import_times(con, csv_path):
    """OCR 結果の CSV を game_time へ UPSERT する。

    CSV: date,match_number,venue,start_time,end_time
    該当試合が無い行はスキップして報告するので、OCR の読み違いでデータが壊れない。
    """
    if not os.path.exists(csv_path):
        print(f"CSV が見つかりません: {csv_path}", file=sys.stderr)
        return 1

    imported = 0
    skipped = []

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"date", "match_number", "start_time", "end_time"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            print(f"CSV に必要な列がありません: {sorted(missing)}", file=sys.stderr)
            return 1

        for lineno, row in enumerate(reader, start=2):
            date = (row.get("date") or "").strip()
            mnum = (row.get("match_number") or "").strip()
            venue = (row.get("venue") or "A").strip() or "A"
            start = (row.get("start_time") or "").strip()
            end = (row.get("end_time") or "").strip()

            if not date or not mnum:
                skipped.append((lineno, f"date/match_number が空", row))
                continue

            try:
                game_id = resolve_game_id(con, date, mnum, venue)
            except ValueError:
                skipped.append((lineno, f"match_number が数値でない: {mnum}", row))
                continue

            if game_id is None:
                skipped.append(
                    (lineno, f"該当試合なし: {date} 第{mnum}試合 ({venue}卓)", row))
                continue

            if duration_minutes(start, end) is None:
                skipped.append(
                    (lineno, f"時刻の書式が不正: '{start}' '{end}'", row))
                continue

            con.execute(
                "INSERT INTO main.game_time (game_id, start_time, end_time, updated_at)"
                " VALUES (?, ?, ?, CURRENT_TIMESTAMP)"
                " ON CONFLICT(game_id) DO UPDATE SET"
                "   start_time = excluded.start_time,"
                "   end_time   = excluded.end_time,"
                "   updated_at = CURRENT_TIMESTAMP",
                (game_id, start, end),
            )
            imported += 1

    con.commit()

    print(f"取り込み: {imported} 件")
    if skipped:
        print(f"スキップ: {len(skipped)} 件")
        for lineno, reason, _row in skipped:
            print(f"  行{lineno}: {reason}")
    return 0


def check_times(con):
    """2 段階の異常検出。

      要確認 : 対局時間が 30〜180 分の範囲外
      外れ値 : 局数あたりの所要分が中央値の 0.6 倍未満 / 1.6 倍超

    OCR の読み違いは「局数の割に極端に長い/短い」形で出るので、
    konoui DB の局数と突き合わせれば単純な範囲チェックより精度よく拾える。
    """
    rows = con.execute(
        "SELECT t.game_id, g.game_date, g.game_number, g.venue,"
        "       t.start_time, t.end_time,"
        "       (SELECT COUNT(*) FROM src.kyoku k WHERE k.game_id = t.game_id)"
        "  FROM main.game_time t"
        "  JOIN (SELECT game_id, game_date, game_number, venue"
        "          FROM game_results GROUP BY game_id) g ON g.game_id = t.game_id"
        " ORDER BY g.game_date, g.game_number"
    ).fetchall()

    if not rows:
        print("対局時間が登録されていません")
        return 0

    records = []
    for game_id, date, gnum, venue, start, end, kyoku in rows:
        dur = duration_minutes(start, end)
        if dur is None:
            continue
        per = dur / kyoku if kyoku else None
        records.append((game_id, date, gnum, venue, start, end, dur, kyoku, per))

    print(f"対局時間: {len(records):,} 件登録済み")

    # --- 要確認: 範囲外 ---
    out_of_range = [r for r in records if not (DURATION_MIN <= r[6] <= DURATION_MAX)]
    print()
    print(f"[要確認] 対局時間が {DURATION_MIN}〜{DURATION_MAX} 分の範囲外: {len(out_of_range)} 件")
    for game_id, date, gnum, venue, start, end, dur, kyoku, _per in out_of_range:
        print(f"  {date} 第{gnum}試合 ({venue}卓) {start}→{end} = {dur}分 / {kyoku}局")

    # --- 外れ値: 局数あたり所要分 ---
    pers = [r[8] for r in records if r[8] is not None]
    if not pers:
        return len(out_of_range)

    median = statistics.median(pers)
    low, high = median * PER_KYOKU_LOW, median * PER_KYOKU_HIGH
    outliers = [r for r in records if r[8] is not None and not (low <= r[8] <= high)]

    print()
    print(f"[外れ値] 局数あたり所要分の中央値 {median:.1f}分/局 "
          f"(許容 {low:.1f}〜{high:.1f}): {len(outliers)} 件")
    for game_id, date, gnum, venue, start, end, dur, kyoku, per in outliers:
        print(f"  {date} 第{gnum}試合 ({venue}卓) {start}→{end} = {dur}分 / {kyoku}局"
              f" = {per:.1f}分/局")

    return len(out_of_range) + len(outliers)


# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="konoui DB の整合性検証と対局時間の取り込み")
    parser.add_argument("--import-times", metavar="CSV",
                        help="OCR 結果の CSV を game_time へ取り込む")
    parser.add_argument("--check-times", action="store_true",
                        help="対局時間の異常検出のみ実行する")
    args = parser.parse_args()

    con = get_connection()
    try:
        if args.import_times:
            rc = import_times(con, args.import_times)
            if rc:
                return rc
            print()
            check_times(con)
            return 0

        if args.check_times:
            check_times(con)
            return 0

        ng = validate_all(con)
        report_stats(con)
        print()
        check_times(con)
        return 1 if ng else 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
