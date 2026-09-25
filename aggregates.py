#!/usr/bin/env python3
"""キャラクターシートが使う事前集計の定義。

局・イベント単位のテーブル (discard_event 1.18M行 / player_state 1.28M行 /
player_tenpai_state 189K行) からしか出せない指標を、選手×シーズン×ステージ
の粒度でまとめる。元テーブルは合わせて 150MB 超あるが、集計後は数百KB。

同じ SELECT を 2 か所から使う。

    build_slim_db.py  CREATE TABLE ... AS で軽量DB に焼き込む
    db_konoui.py      配布DB を使っているときは TEMP ビューとして都度計算する

こうしておくと、軽量DB でもフル配布DB でも同じテーブル名で引けて、
アプリ側は どちらを使っているかを気にしなくてよい。
"""

# konoui が提供する統計の「素カウント」ビュー (39列)。
# 上に乗っている player_season_stage_stats (43列) は、すべてこの素カウントの
# 単純な比で作られている。率ではなく素カウントを持っておけば、シーズン合算でも
# 通算でも「分子の和 / 分母の和」で正確に出せる。率を出場数で加重平均すると
# 局数の違いを吸収できず、わずかにずれる。
#
# 合算は best_score だけ MAX、他は SUM。
PLAYER_BASE = """
SELECT p.id AS player_id, b.*
FROM src.player_season_stage_stats_base b
JOIN src.player p ON p.name = b.player_name
"""

# 和了の巡目と役満。称号の「平均和了巡目」と、名前の横に付ける ★ の材料。
#
#   巡目は、その局で自分が何回ツモったかを和了時点まで数えたもの。
#   agari_event に player_state が付かないので draw_event から復元する。
AGARI = """
WITH ag AS (
    SELECT a.event_id          AS event_id,
           e.kyoku_id          AS kyoku_id,
           e.event_order       AS event_order,
           a.actor_player_id   AS player_id,
           a.is_yakuman        AS is_yakuman
    FROM src.agari_event a
    JOIN src.event e ON e.id = a.event_id
),
turns AS (
    SELECT ag.event_id, ag.kyoku_id, ag.player_id, ag.is_yakuman,
           COUNT(dw.event_id) AS turn
    FROM ag
    LEFT JOIN src.event de
           ON de.kyoku_id = ag.kyoku_id
          AND de.event_order < ag.event_order
          AND de.type = 'draw'
    LEFT JOIN src.draw_event dw
           ON dw.event_id = de.id AND dw.actor_player_id = ag.player_id
    GROUP BY ag.event_id
)
SELECT ls.start_year AS season_start_year,
       ss.stage      AS stage,
       t.player_id   AS player_id,
       COUNT(*)           AS turn_agari_count,
       SUM(t.turn)        AS turn_total,
       SUM(t.is_yakuman)  AS yakuman_count
FROM turns t
JOIN src.kyoku k ON k.id = t.kyoku_id
JOIN src.game  g ON g.id = k.game_id
JOIN src.season_stage  ss ON ss.id = g.season_stage_id
JOIN src.league_season ls ON ls.id = ss.league_season_id
GROUP BY 1, 2, 3
"""

# 役満の 1 件ずつ。★ のホバーに年と役名を出すため。31 行しかない。
YAKUMAN = """
SELECT ls.start_year      AS season_start_year,
       a.actor_player_id  AS player_id,
       g.date             AS game_date,
       a.revenue_points   AS points,
       GROUP_CONCAT(y.name, '・') AS yaku
FROM src.agari_event a
JOIN src.event e ON e.id = a.event_id
JOIN src.kyoku k ON k.id = e.kyoku_id
JOIN src.game  g ON g.id = k.game_id
JOIN src.season_stage  ss ON ss.id = g.season_stage_id
JOIN src.league_season ls ON ls.id = ss.league_season_id
LEFT JOIN src.agari_yaku ay ON ay.agari_event_id = a.event_id
LEFT JOIN src.yaku_name y ON y.id = ay.yaku_name_id
WHERE a.is_yakuman = 1
GROUP BY a.event_id
"""

# 打牌の内訳。「てづくり」軸の材料。
#
#   立直後の打牌は手牌が固定されるので除く (ツモ切り率 79.2%)。
#   各局・各選手の第一打は直前の打牌が無く向聴の増減を取れないので除く。
#   残った手出しを、直前の自分の打牌からの向聴の動きで 3 つに分ける。
#   ツモ切りは手牌が変わらないので分類しない (鳴いた直後のツモ切りだけは
#   向聴が動くが、動かしたのは鳴きなので数えない)。
#
#     forward : 向聴が進んだ手出し
#     hold    : 向聴が変わらない手出し
#     retreat : 向聴が戻った手出し (降りの打牌)
#
#   てづくり = (forward + hold) / discards
#
#   後退を外すのは、それが「まもり」(放銃率 r=-0.37) と
#   「ねばり」(流局聴牌率 r=-0.43) で既に測られているため。
#   3 案を比べたとき、この形がいちばん他軸と独立していた
#   (てづくりの最大相関 0.11 / 合計だと 0.22 / 維持のみだと 0.20)。
DISCARD = """
WITH d AS (
    SELECT ls.start_year        AS season_start_year,
           ss.stage             AS stage,
           de.actor_player_id   AS player_id,
           e.kyoku_id           AS kyoku_id,
           e.event_order        AS event_order,
           de.is_tsumogiri      AS is_tsumogiri,
           ps.shanten_count     AS shanten
    FROM src.discard_event de
    JOIN src.event  e ON e.id = de.event_id
    JOIN src.player_state ps
         ON ps.event_id = de.event_id AND ps.player_id = de.actor_player_id
    JOIN src.kyoku  k ON k.id = e.kyoku_id
    JOIN src.game   g ON g.id = k.game_id
    JOIN src.season_stage  ss ON ss.id = g.season_stage_id
    JOIN src.league_season ls ON ls.id = ss.league_season_id
    WHERE ps.is_reached = 0
),
x AS (
    SELECT d.*,
           LAG(shanten) OVER (PARTITION BY kyoku_id, player_id
                              ORDER BY event_order) AS prev_shanten
    FROM d
)
SELECT season_start_year, stage, player_id,
       COUNT(*)                                                 AS discards,
       SUM(CASE WHEN is_tsumogiri = 0
                 AND shanten <  prev_shanten THEN 1 ELSE 0 END) AS forward,
       SUM(CASE WHEN is_tsumogiri = 0
                 AND shanten =  prev_shanten THEN 1 ELSE 0 END) AS hold,
       SUM(CASE WHEN is_tsumogiri = 0
                 AND shanten >  prev_shanten THEN 1 ELSE 0 END) AS retreat,
       SUM(is_tsumogiri)                                        AS tsumogiri
FROM x
WHERE prev_shanten IS NOT NULL
GROUP BY 1, 2, 3
"""

# 聴牌形の内訳。「みきわめ」軸 (平均待ち枚数 = wait_tiles_total / tenpai_states)
# と、とくせいの待ち 7 種の材料。
#
#   player_tenpai_state は聴牌中のイベントごとに 1 行入る。待ちが変われば
#   行が増えるので、行数は「聴牌していた延べイベント数」であって
#   「聴牌回数」ではない。平均待ち枚数にも待ちの継続時間で重みが付く。
TENPAI = """
SELECT ls.start_year AS season_start_year,
       ss.stage      AS stage,
       ts.player_id  AS player_id,
       COUNT(*)                      AS tenpai_states,
       SUM(ts.available_tile_count)  AS wait_tiles_total,
       SUM(CASE WHEN ts.waiting_type = '両面'      THEN 1 ELSE 0 END) AS wait_ryanmen,
       SUM(CASE WHEN ts.waiting_type = 'カンチャン' THEN 1 ELSE 0 END) AS wait_kanchan,
       SUM(CASE WHEN ts.waiting_type = 'シャンポン' THEN 1 ELSE 0 END) AS wait_shanpon,
       SUM(CASE WHEN ts.waiting_type = '単騎'      THEN 1 ELSE 0 END) AS wait_tanki,
       SUM(CASE WHEN ts.waiting_type = '複合形'     THEN 1 ELSE 0 END) AS wait_fukugo,
       SUM(CASE WHEN ts.waiting_type = 'ペンチャン' THEN 1 ELSE 0 END) AS wait_penchan,
       SUM(CASE WHEN ts.waiting_type = 'ノベタン'   THEN 1 ELSE 0 END) AS wait_nobetan,
       SUM(CASE WHEN ts.waiting_type = '亜両面'     THEN 1 ELSE 0 END) AS wait_aryanmen
FROM src.player_tenpai_state ts
JOIN src.event  e ON e.id = ts.event_id
JOIN src.kyoku  k ON k.id = e.kyoku_id
JOIN src.game   g ON g.id = k.game_id
JOIN src.season_stage  ss ON ss.id = g.season_stage_id
JOIN src.league_season ls ON ls.id = ss.league_season_id
GROUP BY 1, 2, 3
"""

# (テーブル名, SELECT, 索引を張る列)
AGGREGATES = [
    ("player_season_stage_base",    PLAYER_BASE, "player_id, season_start_year"),
    ("player_season_stage_discard", DISCARD,     "player_id, season_start_year"),
    ("player_season_stage_tenpai",  TENPAI,      "player_id, season_start_year"),
    ("player_season_stage_agari",   AGARI,       "player_id, season_start_year"),
    ("yakuman_event",               YAKUMAN,     "player_id, season_start_year"),
]
