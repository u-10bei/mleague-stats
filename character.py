#!/usr/bin/env python3
"""キャラクターシートの四層を計算する。

    ジョブ      通算の 7 軸から組み立てる名前            変わらない
    パラメータ  7 軸のレーダーとランク                   シーズン / 通算
    とくせい    7 軸とは別の指標から拾う、その年の特徴   シーズンごと
    称号        シーズン個人賞 8 種の 3 位まで ＋ 役満    シーズンごと

元になる素カウントは aggregates.py が選手×シーズン×ステージで持っている。
率はここで「分子の和 / 分母の和」として出す。率を出場数で加重平均すると
局数の違いを吸収できないため、合算の前に率にしない。

    python character.py            計算結果の要約を表示する
    python character.py 園田賢     1 人分のシートを表示する
    python character.py --check    不変条件を検査する (CI 用)
"""

import json
import os
import sys

import numpy as np
import pandas as pd

VOCAB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "character_vocab.json")

AXES = ["しかけ", "だてん", "まもり", "ねばり", "てづくり", "みきわめ", "りーち"]

# 軸 -> (実測値の列, 表示名, 単位, 実測値と軸の向きが逆か)
AXIS_SOURCE = {
    "しかけ":   ("furo_rate_percent",   "副露率",       "%", False),
    "だてん":   ("avg_win_points",      "平均和了点",   "点", False),
    "まもり":   ("dealin_rate_percent", "放銃率",       "%", True),
    "ねばり":   ("tenpai_rate_percent", "流局聴牌率",   "%", False),
    "てづくり": ("tezukuri_percent",    "手を作る打牌", "%", False),
    "みきわめ": ("avg_wait",            "平均待ち枚数", "枚", False),
    "りーち":   ("reach_rate_percent",  "立直率",       "%", False),
}

# 偏差値 -> ランク。7 軸は強さではなく個性なので、S も G も「特徴あり」。
RANK_STEPS = [(70, "S"), (65, "A"), (60, "B"), (55, "C"),
              (45, "D"), (40, "E"), (35, "F")]

# 称号にするシーズン個人賞。(表示名, 列, 小さいほど上位か, 表示の書式)
AWARDS = [
    ("個人スコア",   "total_points",  False, "{:+.1f}"),
    ("最多登板",     "games",         False, "{:.0f}戦"),
    ("最高スコア",   "best_score",    False, "{:,.0f}"),
    ("トップ率",     "top_rate",      False, "{:.1f}%"),
    ("ラス回避率",   "last_rate",     True,  "{:.1f}%"),
    ("和了率",       "win_rate",      False, "{:.1f}%"),
    ("放銃率の低さ", "dealin_rate",   True,  "{:.1f}%"),
    ("平均和了巡目", "avg_turn",      True,  "{:.2f}巡"),
]
AWARD_PLACES = 3

# 素カウントの合算規則。best_score だけは MAX。
_MAX_COLS = {"best_score"}

# シーズン単位で扱う最小出場数。
#
# 開幕直後のシーズンは 1 試合しか消化していない選手が並び、率が 0% や 100% に
# 振れる。これを母集団に入れると σ が最大 1.72 倍に膨らみ、他の全員のとくせいが
# 閾値に届かなくなる (平均 1.36 個 → 0.91 個)。
#
# 10 戦にすると 2018〜2025 は 1 行も落ちない (各シーズンの最少出場は
# 22/10/13/12/12/14/16/20 戦)。過去の結果を一切動かさずに、消化途中の
# シーズンだけを待たせられる。通算の合算にはこの足切りをかけない。
MIN_SEASON_GAMES = 10


def load_vocab(path=VOCAB_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------
# 素カウントの読み込みと合算
# ---------------------------------------------------------------------

def load_stage_rows(con):
    """選手×シーズン×ステージの素カウントを 1 枚にまとめて返す。"""
    key = ["start_season_year", "stage", "player_id"]
    base = pd.read_sql_query("SELECT * FROM player_season_stage_base", con)
    base = base.drop(columns=["player_name", "team_name"])
    for name in ("player_season_stage_discard", "player_season_stage_tenpai",
                 "player_season_stage_agari"):
        base = base.merge(pd.read_sql_query(f"SELECT * FROM {name}", con),
                          on=key, how="left")
    count_cols = [c for c in base.columns if c not in key]
    base[count_cols] = base[count_cols].fillna(0)
    return base.rename(columns={"start_season_year": "season"})


def combine(rows, by):
    """素カウントを by の粒度に合算する。best_score だけ MAX。"""
    cols = [c for c in rows.columns if c not in by + ["stage"]]
    how = {c: ("max" if c in _MAX_COLS else "sum") for c in cols}
    return rows.groupby(by, as_index=False).agg(how)


def _ratio(num, den, scale=1.0):
    den = den.replace(0, np.nan)
    return num / den * scale


def derive(df):
    """素カウントから率・平均を作る。konoui の統計ビューと同じ定義。"""
    d = df.copy()
    kyoku, games = d.total_kyoku_count, d.total_game_count
    wins, reach_agari = d.win_count, d.reach_agari_count

    d["win_rate_percent"] = _ratio(wins, kyoku, 100)
    d["dealin_rate_percent"] = _ratio(d.dealin_count, kyoku, 100)
    d["hitsumo_rate_percent"] = _ratio(d.hitsumo_count, kyoku, 100)
    d["furo_rate_percent"] = _ratio(d.furo_count, kyoku, 100)
    d["reach_rate_percent"] = _ratio(d.reach_count, kyoku, 100)
    d["ryukyoku_rate_percent"] = _ratio(d.ryukyoku_count, kyoku, 100)
    d["tenpai_rate_percent"] = _ratio(d.tenpai_count, d.ryukyoku_count, 100)
    d["yokomove_rate_percent"] = _ratio(
        kyoku - wins - d.dealin_count - d.hitsumo_count - d.ryukyoku_count,
        kyoku, 100)

    d["tsumo_win_rate_percent"] = _ratio(d.tsumo_win_count, wins, 100)
    d["dama_agari_in_win_rate_percent"] = _ratio(
        wins - reach_agari - d.furo_agari_count, wins, 100)
    d["avg_win_points"] = _ratio(d.win_point_total, wins)
    d["avg_dealin_points"] = _ratio(d.dealin_point_total, d.dealin_count)

    d["avg_dora_num"] = _ratio(d.dora_total, wins)
    d["avg_aka_dora_num"] = _ratio(d.aka_dora_total, wins)
    d["ura_dora_nori_rate_percent"] = _ratio(d.ura_dora_win_count, reach_agari, 100)

    d["oya_kaburi_rate_percent"] = _ratio(d.oya_kaburi_count, d.oya_kyoku_count, 100)
    d["itai_oya_kaburi_rate_percent"] = _ratio(
        d.itai_oya_kaburi_count, d.oya_kaburi_count, 100)
    d["renchan_rate_percent"] = _ratio(d.renchan_count, d.oya_kyoku_count, 100)

    d["top_rate"] = _ratio(d.rank1_count, games, 100)
    d["last_rate"] = _ratio(d.rank4_count, games, 100)
    d["win_rate"] = d["win_rate_percent"]
    d["dealin_rate"] = d["dealin_rate_percent"]
    d["games"] = games

    # 事前集計から来る 3 つ
    d["tezukuri_percent"] = _ratio(d.forward + d.hold, d.discards, 100)
    d["avg_wait"] = _ratio(d.wait_tiles_total, d.tenpai_states)
    d["avg_turn"] = _ratio(d.turn_total, d.agari_count)
    waits = ["ryanmen", "kanchan", "shanpon", "tanki", "fukugo",
             "penchan", "nobetan", "aryanmen"]
    for w in waits:
        d[f"wait_{w}_pct"] = _ratio(d[f"wait_{w}"], d.tenpai_states, 100)
    return d


# ---------------------------------------------------------------------
# 7 軸
# ---------------------------------------------------------------------

def axis_values(df):
    """実測値を軸の向きに揃える。放銃率だけ符号を反転する。"""
    out = df[["season", "player_id"]].copy() if "season" in df.columns \
        else df[["player_id"]].copy()
    for axis, (col, _, _, invert) in AXIS_SOURCE.items():
        out[axis] = -df[col] if invert else df[col]
    return out


def zscore(df, cols):
    z = df.copy()
    for c in cols:
        sd = df[c].std(ddof=0)
        z[c] = 0.0 if not sd else (df[c] - df[c].mean()) / sd
    return z


def rank_of(z):
    t = 50 + 10 * z
    for lim, r in RANK_STEPS:
        if t >= lim:
            return r
    return "G"


def season_axes(rows, min_games=MIN_SEASON_GAMES):
    """シーズンごとの 7 軸。母集団は最小出場数を満たす全選手シーズン。"""
    per = derive(combine(rows, ["season", "player_id"]))
    per = per[per.total_game_count >= min_games].reset_index(drop=True)
    return zscore(axis_values(per), AXES), per


def career_axes(rows):
    """通算の 7 軸。

    素カウントを全シーズン合算してから率にし、そのうえで選手間で標準化する。
    シーズン z の平均を取ると分散が縮み (σ 0.56〜0.83)、閾値 1.0 で発火する軸が
    ねばり・だてんに偏る。合算してから測れば軸ごとの散らばりが揃う。
    """
    per = derive(combine(rows, ["player_id"]))
    return zscore(axis_values(per), AXES), per


# ---------------------------------------------------------------------
# ジョブ
# ---------------------------------------------------------------------

def job_of(zrow, vocab):
    """通算の 7 軸からジョブ名を組み立てる。

    閾値を超えた軸を強い順に並べ、1 番目からクラス名、2 番目から形容詞、
    3 番目から修飾を取る。1 つも超えなければ万能クラス (遊撃手)。
    """
    th = vocab["job_threshold"]
    hits = sorted(((abs(zrow[a]), a, "高" if zrow[a] > 0 else "低")
                   for a in AXES if abs(zrow[a]) >= th), reverse=True)
    parts = []
    for i, (mag, axis, direction) in enumerate(hits):
        v = vocab["axes"][axis + direction]
        parts.append({"axis": axis, "dir": direction, "z": round(zrow[axis], 2),
                      "role": ["クラス名", "形容詞", "修飾"][i] if i < 3 else "—",
                      "word": v["class"] if i == 0 else
                              v["adjective"] if i == 1 else
                              v["mark"] if i == 2 else v["class"],
                      "desc": v["desc"]})
    if not parts:
        return vocab["balanced"], []
    name = parts[0]["word"]
    if len(parts) >= 2:
        name = parts[1]["word"] + name
    if len(parts) >= 3:
        name = name + "（" + parts[2]["word"] + "）"
    return name, parts


# ---------------------------------------------------------------------
# とくせい
# ---------------------------------------------------------------------

def traits_table(per_season, vocab):
    """シーズンごとのとくせい。7 軸とは別の指標を全選手シーズンで標準化する。"""
    th = vocab["trait_threshold"]
    cols = sorted({t["col"] for t in vocab["traits"]})
    z = zscore(per_season[cols], cols)
    means = per_season[cols].mean()
    out = []
    for i, row in per_season.iterrows():
        got = []
        for t in vocab["traits"]:
            zv = z.at[i, t["col"]] * t["sign"]
            if pd.notna(zv) and zv >= th:
                got.append({"name": t["name"], "group": t["group"],
                            "z": round(float(zv), 2), "desc": t["desc"],
                            "val": round(float(row[t["col"]]), 2),
                            "avg": round(float(means[t["col"]]), 2)})
        got.sort(key=lambda x: -x["z"])
        out.append({"season": int(row.season), "player_id": int(row.player_id),
                    "traits": got})
    return pd.DataFrame(out)


# ---------------------------------------------------------------------
# 称号
# ---------------------------------------------------------------------

def awards_table(per_season):
    """シーズン個人賞。全ステージ合算、3 位まで、規定打数は設けない。"""
    rows = []
    for label, col, ascending, fmt in AWARDS:
        d = per_season.dropna(subset=[col])
        top = d.sort_values(["season", col], ascending=[True, ascending]) \
               .groupby("season").head(AWARD_PLACES).copy()
        top["place"] = top.groupby("season").cumcount() + 1
        for r in top.itertuples():
            rows.append({"season": int(r.season), "player_id": int(r.player_id),
                         "award": label, "place": int(r.place),
                         "value": fmt.format(getattr(r, col))})
    return pd.DataFrame(rows).sort_values(["player_id", "season", "place", "award"])


def yakuman_table(con):
    """役満の 1 件ずつ。名前の横に ★ を回数分置くための材料。"""
    return pd.read_sql_query(
        "SELECT start_season_year AS season, player_id, game_date, points, yaku"
        " FROM yakuman_event ORDER BY player_id, game_date", con)


# ---------------------------------------------------------------------
# 1 人分のシート
# ---------------------------------------------------------------------

def build(con, vocab=None):
    """全選手ぶんの計算結果をまとめて返す。ページ側でキャッシュする前提。"""
    vocab = vocab or load_vocab()
    rows = load_stage_rows(con)
    s_z, s_per = season_axes(rows)
    c_z, c_per = career_axes(rows)
    return {
        "vocab": vocab,
        "season_z": s_z, "season_raw": s_per,
        "career_z": c_z, "career_raw": c_per,
        "traits": traits_table(s_per, vocab),
        "awards": awards_table(s_per),
        "yakuman": yakuman_table(con),
    }


def sheet(data, player_id):
    """1 人分のシートを組み立てる。"""
    vocab = data["vocab"]
    cz = data["career_z"].set_index("player_id").loc[player_id]
    craw = data["career_raw"].set_index("player_id").loc[player_id]
    job, parts = job_of(cz, vocab)

    seasons = []
    sz = data["season_z"].set_index("player_id")
    sraw = data["season_raw"].set_index("player_id")
    tr = data["traits"].set_index("player_id")
    for season in sorted(sraw.loc[[player_id]].season):
        zrow = sz.loc[[player_id]].query("season == @season").iloc[0]
        rrow = sraw.loc[[player_id]].query("season == @season").iloc[0]
        t = tr.loc[[player_id]].query("season == @season")
        seasons.append({
            "season": int(season),
            "games": int(rrow.total_game_count),
            "points": float(rrow.total_points),
            "z": {a: round(float(zrow[a]), 2) for a in AXES},
            "rank": {a: rank_of(float(zrow[a])) for a in AXES},
            "traits": t.iloc[0]["traits"] if len(t) else [],
        })

    aw = data["awards"]
    titles = [{"season": int(r.season), "award": r.award,
               "place": int(r.place), "value": r.value}
              for r in aw[aw.player_id == player_id].itertuples()]
    yk = data["yakuman"]
    stars = [{"season": int(r.season), "yaku": r.yaku, "date": r.game_date}
             for r in yk[yk.player_id == player_id].itertuples()]

    return {
        "player_id": int(player_id),
        "job": job, "job_parts": parts,
        "seasons_n": len(seasons),
        "games": int(craw.total_game_count),
        "win_rate": round(float(craw.win_rate_percent), 2),
        "career_z": {a: round(float(cz[a]), 2) for a in AXES},
        "career_rank": {a: rank_of(float(cz[a])) for a in AXES},
        "career_raw": {a: round(float(craw[AXIS_SOURCE[a][0]]), 2) for a in AXES},
        "seasons": seasons, "titles": titles, "stars": stars,
    }


# ---------------------------------------------------------------------

def _check(con, data):
    """不変条件を検査する。1 つでも破れていれば False。"""
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  {'OK ' if passed else 'NG '} {label}{detail}")

    # 1. derive() が konoui 自身の率と一致するか (ステージ単位で突き合わせる)。
    #    konoui の率ビューは配布DB にしかないので、軽量DB のときは飛ばす。
    #    定義のずれは同期ワークフロー (配布DB を持っている) で捕まえる。
    try:
        theirs = pd.read_sql_query(
            "SELECT s.* FROM src.player_season_stage_stats s", con)
    except Exception:
        theirs = None
    if theirs is None or "win_rate_percent" not in theirs.columns:
        print("  --  derive() と konoui の率の突合は配布DB のときだけ行う")
    else:
        names = pd.read_sql_query(
            "SELECT player_id, player_name FROM players", con)
        theirs = theirs.merge(names, on="player_name").rename(
            columns={"start_season_year": "season"})
        mine = derive(load_stage_rows(con))
        m = mine.merge(theirs, on=["season", "stage", "player_id"],
                       suffixes=("_mine", "_theirs"))
        # konoui の率ビューは列ごとに桁を決めて丸めている。その丸め幅までは
        # 一致とみなす (例: avg_win_points は ROUND(...,0) なので 0.5)。
        digits = {"avg_win_points": 0, "avg_dealin_points": 0,
                  "avg_dora_num": 3, "avg_aka_dora_num": 3}
        worst, worst_col, bad = 0.0, "", []
        for col in ["win_rate_percent", "dealin_rate_percent", "furo_rate_percent",
                    "reach_rate_percent", "tenpai_rate_percent",
                    "tsumo_win_rate_percent", "dama_agari_in_win_rate_percent",
                    "avg_win_points", "avg_dealin_points", "avg_dora_num",
                    "avg_aka_dora_num", "ura_dora_nori_rate_percent",
                    "hitsumo_rate_percent", "oya_kaburi_rate_percent",
                    "itai_oya_kaburi_rate_percent", "renchan_rate_percent",
                    "yokomove_rate_percent"]:
            a, b = m[col + "_mine"], m[col + "_theirs"]
            both = a.notna() & b.notna()
            tol = 0.5 * 10 ** -digits.get(col, 2) + 1e-9
            diff = (a[both] - b[both]).abs()
            over = float(diff.max() / tol) if len(diff) else 0.0
            if over > worst:
                worst, worst_col = over, col
            if len(diff) and diff.max() > tol:
                bad.append(f"{col} {diff.max():.5f} > {tol:.5f}")
        report(f"derive() が konoui の率と一致 ({len(m)} 行)", not bad,
               (" / ".join(bad) if bad else
                f" 丸め幅に対する最大差 {worst:.2f} 倍 ({worst_col})"))

    # 2. 標準化の結果
    for label, z in (("シーズン", data["season_z"]), ("通算", data["career_z"])):
        mean = z[AXES].mean().abs().max()
        sd = (z[AXES].std(ddof=0) - 1).abs().max()
        report(f"{label}の z 値が平均0・標準偏差1", mean < 1e-9 and sd < 1e-9,
               f" 平均のずれ {mean:.2e} / σ のずれ {sd:.2e}")

    # 3. ジョブ名が全員に付く
    jobs = [job_of(r, data["vocab"])[0] for _, r in data["career_z"].iterrows()]
    report(f"全 {len(jobs)} 名にジョブ名が付く", all(jobs),
           f" / {len(set(jobs))} 種")

    # 4. ランクが S〜G に収まる
    letters = {r for _, r in RANK_STEPS} | {"G"}
    got = {rank_of(v) for _, r in data["season_z"].iterrows() for v in r[AXES]}
    report("ランクが S〜G のいずれか", got <= letters, f" {sorted(got)}")

    # 5. とくせいが閾値を満たす
    th = data["vocab"]["trait_threshold"]
    zs = [t["z"] for row in data["traits"].traits for t in row]
    report(f"とくせいがすべて z>={th}", all(z >= th for z in zs),
           f" 最小 {min(zs):.2f} / 計 {len(zs)} 個" if zs else "")

    # 6. 称号は 1 賞につき 1 シーズン 3 件
    per = data["awards"].groupby(["season", "award"]).size()
    report("称号が 1 賞 1 シーズンあたり 3 件", bool((per == AWARD_PLACES).all()),
           f" 計 {len(data['awards'])} 件")

    # 7. 出場数の合計が素データと合う
    total = int(data["career_raw"].total_game_count.sum())
    expect = pd.read_sql_query("SELECT COUNT(*) n FROM game_results", con).n[0]
    report("延べ出場数が game_results と一致", total == expect,
           f" {total} / {expect}")
    return ok


def _main(argv):
    from db import get_connection
    con = get_connection(readonly_local=True)
    data = build(con)
    if len(argv) > 1 and argv[1] == "--check":
        print("character.py 自己検査")
        ok = _check(con, data)
        con.close()
        return 0 if ok else 1
    names = pd.read_sql_query("SELECT player_id, player_name FROM players", con)
    con.close()
    name_of = names.set_index("player_id").player_name.to_dict()
    id_of = {v: k for k, v in name_of.items()}

    if len(argv) > 1:
        pid = id_of.get(argv[1])
        if pid is None:
            print(f"選手が見つかりません: {argv[1]}", file=sys.stderr)
            return 1
        s = sheet(data, pid)
        print(f"{argv[1]}  {s['job']}  Lv.{s['seasons_n']} / {s['games']}戦 "
              f"/ 和了率 {s['win_rate']}%  {'★' * len(s['stars'])}")
        for p in s["job_parts"]:
            print(f"  {p['role']:6} {p['word']:8} {p['axis']}{p['dir']} "
                  f"({p['z']:+.2f})  {p['desc']}")
        print("  " + " ".join(f"{a}{s['career_rank'][a]}" for a in AXES))
        for r in s["seasons"]:
            names_ = "・".join(t["name"] for t in r["traits"]) or "なし"
            print(f"  {r['season']} {r['games']:>3}戦 {r['points']:+8.1f}  "
                  + " ".join(r["rank"][a] for a in AXES) + f"  {names_}")
        for t in s["titles"]:
            print(f"  称号 {t['season']} {t['place']}位 {t['award']} {t['value']}")
        for st in s["stars"]:
            print(f"  ★ {st['season']} {st['yaku']} ({st['date']})")
        return 0

    jobs = {}
    for pid in data["career_z"].player_id:
        jobs[name_of.get(pid, pid)] = sheet(data, pid)["job"]
    print(f"選手 {len(jobs)} 名 / 型 {len(set(jobs.values()))} 種")
    print(f"遊撃手 {sum(1 for v in jobs.values() if v == data['vocab']['balanced'])} 名")
    n = data["traits"].traits.apply(len)
    print(f"とくせい 平均 {n.mean():.2f} 個 / 0個 {int((n == 0).sum())} "
          f"/ 最多 {int(n.max())}")
    print(f"称号 {len(data['awards'])} 件 / 受賞者 "
          f"{data['awards'].player_id.nunique()} 名")
    print(f"役満 {len(data['yakuman'])} 件 / {data['yakuman'].player_id.nunique()} 名")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
