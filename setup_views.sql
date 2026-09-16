-- =====================================================================
-- setup_views.sql
--
-- konoui/m-league-game-db を正データとするための
--   (1) 補完テーブル定義   … konoui DB に無い情報だけを持つ (main = mleague_local.db)
--   (2) 互換ビュー定義     … 既存アプリのテーブル名/カラム名を再現する (TEMP)
--
-- 前提: konoui 配布DB が `src` として ATTACH されていること。
--       SQLite はビューから別の ATTACH 先を参照できないため、互換ビューは
--       永続化できず接続のたびに TEMP で作り直す (db_konoui.py が自動実行)。
-- =====================================================================


-- ---------------------------------------------------------------------
-- (1) 補完テーブル  ※ main = data/mleague_local.db に永続化される
-- ---------------------------------------------------------------------

-- 対局時間: konoui DB に無い唯一の実データ。公式ビューアからの OCR で埋める。
CREATE TABLE IF NOT EXISTS game_time (
    game_id    INTEGER PRIMARY KEY,   -- src.game.id
    start_time TEXT,                  -- 'HH:MM'
    end_time   TEXT,                  -- 'HH:MM'
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- チーム略称 / チームカラー: 表示用のため自前で持つ。
CREATE TABLE IF NOT EXISTS team_meta (
    team_id    INTEGER PRIMARY KEY,   -- src.team.id
    short_name TEXT,
    color      TEXT
);

-- チーム名履歴: konoui DB は現行名しか持たないため、年度別の名称を自前で持つ。
CREATE TABLE IF NOT EXISTS team_name_history (
    team_id   INTEGER NOT NULL,       -- src.team.id
    season    INTEGER NOT NULL,       -- src.league_season.start_year
    team_name TEXT    NOT NULL,
    PRIMARY KEY (team_id, season)
);

-- 選手プロフィール: 生年月日・所属プロ団体。
CREATE TABLE IF NOT EXISTS player_profile (
    player_id  INTEGER PRIMARY KEY,   -- src.player.id
    birth_date TEXT,
    pro_org    TEXT
);

-- レーティング: アプリ独自の計算結果。konoui DB には存在しない。
CREATE TABLE IF NOT EXISTS player_ratings (
    player_id    INTEGER PRIMARY KEY,
    rating       REAL    DEFAULT 1500.0,
    games        INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rating_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id    INTEGER NOT NULL,
    game_date    TEXT    NOT NULL,
    old_rating   REAL    NOT NULL,
    new_rating   REAL    NOT NULL,
    delta        REAL    NOT NULL,
    opponent_ids TEXT,
    season       INTEGER,
    game_number  INTEGER
);

CREATE INDEX IF NOT EXISTS idx_rating_history_player
    ON rating_history(player_id, game_date);

-- レーティング計算済みフラグ: 旧 game_results.rating_calculated の置き換え。
-- 互換ビューは更新できないため、フラグだけを補完テーブルで持つ。
CREATE TABLE IF NOT EXISTS rating_state (
    game_id    INTEGER PRIMARY KEY,   -- src.game.id
    calculated INTEGER NOT NULL DEFAULT 0
);


-- ---------------------------------------------------------------------
-- (2) 互換ビュー  ※ すべて TEMP。接続のたびに作り直す。
-- ---------------------------------------------------------------------

DROP VIEW IF EXISTS temp._game;
DROP VIEW IF EXISTS temp._first_kyoku;
DROP VIEW IF EXISTS temp._seat;
DROP VIEW IF EXISTS temp._team_season;
DROP VIEW IF EXISTS temp._team_stage_points;
DROP VIEW IF EXISTS temp._team_penalty;
DROP VIEW IF EXISTS temp.game_results;
DROP VIEW IF EXISTS temp.players;
DROP VIEW IF EXISTS temp.teams;
DROP VIEW IF EXISTS temp.team_names;
DROP VIEW IF EXISTS temp.player_teams;
DROP VIEW IF EXISTS temp.player_season_stats;
DROP VIEW IF EXISTS temp.team_season_points;
DROP VIEW IF EXISTS temp.foul_plays;


-- 試合の基本属性。
--   venue      : m_league_game_id 末尾1文字 (A卓/B卓)
--   game_number: 2025シーズンからの2会場制に対応し、B卓は +2 して
--                A卓 1,2 / B卓 3,4 とする (同日・同試合番号の衝突回避)
--   table_type : 既存アプリの卓区分表記に合わせる
CREATE TEMP VIEW _game AS
SELECT
    g.id                              AS game_id,
    ls.start_year                     AS season,
    g.date                            AS game_date,
    ss.stage                          AS stage,
    CASE ss.stage
        WHEN 'regular'   THEN 'レギュラー'
        WHEN 'semifinal' THEN 'セミファイナル'
        WHEN 'final'     THEN 'ファイナル'
        ELSE ss.stage
    END                               AS table_type,
    substr(g.m_league_game_id, -1)    AS venue,
    g.match_number
        + CASE WHEN substr(g.m_league_game_id, -1) = 'B' THEN 2 ELSE 0 END
                                      AS game_number,
    g.match_number                    AS match_number,
    g.round_number                    AS round_number
FROM src.game g
JOIN src.season_stage  ss ON ss.id = g.season_stage_id
JOIN src.league_season  ls ON ls.id = ss.league_season_id;


-- 各試合の東1局 (= 最小 kyoku.id)。席順の判定に使う。
CREATE TEMP VIEW _first_kyoku AS
SELECT game_id, MIN(id) AS kyoku_id
FROM src.kyoku
GROUP BY game_id;


-- 席 (起家=東家 からの並び)。東1局の自風がそのまま席になる。
CREATE TEMP VIEW _seat AS
SELECT
    fk.game_id,
    kpr.player_id,
    CASE kpr.player_wind
        WHEN '1z' THEN '東'
        WHEN '2z' THEN '南'
        WHEN '3z' THEN '西'
        WHEN '4z' THEN '北'
    END AS seat_name
FROM _first_kyoku fk
JOIN src.kyoku_player_result kpr ON kpr.kyoku_id = fk.kyoku_id;


-- 既存 game_results 互換。
--   points  : ペナルティを含まない素のポイント (konoui の game_player_result.points)
--   score   : 素点 (既存スキーマには無いが分析で有用なため追加)
--   game_id / venue も追加で参照できる。
CREATE TEMP VIEW game_results AS
SELECT
    r.game_id * 100 + r.player_id      AS id,
    g.season,
    g.game_date,
    g.table_type,
    g.game_number,
    s.seat_name,
    r.player_id,
    r.points,
    r.rank,
    NULL                               AS created_at,
    t.start_time,
    t.end_time,
    COALESCE(rs.calculated, 0)         AS rating_calculated,
    -- 追加カラム
    r.game_id,
    g.venue,
    g.stage,
    g.match_number,
    r.score,
    r.penalty_points                   AS penalty
FROM src.game_player_result r
JOIN _game g          ON g.game_id  = r.game_id
LEFT JOIN _seat s     ON s.game_id  = r.game_id AND s.player_id = r.player_id
LEFT JOIN main.game_time    t  ON t.game_id  = r.game_id
LEFT JOIN main.rating_state rs ON rs.game_id = r.game_id;


-- 既存 players 互換。player_name_kana を追加。
CREATE TEMP VIEW players AS
SELECT
    p.id            AS player_id,
    p.name          AS player_name,
    pp.birth_date,
    pp.pro_org,
    p.name_furigana AS player_name_kana,
    p.joined_season_year
FROM src.player p
LEFT JOIN main.player_profile pp ON pp.player_id = p.id;


-- 既存 teams 互換。short_name / color は補完テーブル由来。
CREATE TEMP VIEW teams AS
SELECT
    t.id                                   AS team_id,
    COALESCE(tm.short_name, t.name)        AS short_name,
    COALESCE(tm.color, '#888888')          AS color,
    t.joined_season_year                   AS established,
    t.name                                 AS current_name
FROM src.team t
LEFT JOIN main.team_meta tm ON tm.team_id = t.id;


-- チームが実際に参加した (team_id, season) の組み合わせ。
CREATE TEMP VIEW _team_season AS
SELECT DISTINCT
    tsr.team_id,
    tsr.league_season_start_year AS season
FROM src.team_season_stage_result tsr;


-- 既存 team_names 互換。自前履歴があれば優先、無ければ konoui の現行名。
CREATE TEMP VIEW team_names AS
SELECT
    ts.team_id * 10000 + ts.season            AS id,
    ts.team_id,
    ts.season,
    COALESCE(tnh.team_name, t.name)           AS team_name
FROM _team_season ts
JOIN src.team t ON t.id = ts.team_id
LEFT JOIN main.team_name_history tnh
       ON tnh.team_id = ts.team_id AND tnh.season = ts.season;


-- 既存 player_teams 互換。joined〜left を年度に展開。
--
-- left_season_year は「そのチームに在籍した最後のシーズン」を指す閉区間。
-- 退団20件のうち17件はこの解釈と一致するが、konoui 側が退団を先行して
-- 記録しているケース（小林剛・渋川難波・浅井堂岐 = left 2026 / 最終出場
-- 2025）があり、そのままでは開幕したばかりのシーズンで在籍者が
-- 4名を超えてしまう。
-- そこで、区間の最終シーズンについてのみ「実際に出場したか」を条件に加える。
-- 在籍中（left = 9999）の選手は出場の有無に関わらず対象のまま。
CREATE TEMP VIEW player_teams AS
SELECT
    pt.player_id * 10000 + ls.start_year AS id,
    pt.player_id,
    pt.team_id,
    ls.start_year AS season
FROM src.player_team pt
JOIN src.league_season ls
  ON ls.start_year BETWEEN pt.joined_season_year AND pt.left_season_year
WHERE pt.left_season_year = 9999
   OR ls.start_year < pt.left_season_year
   OR EXISTS (
        SELECT 1
        FROM src.game_player_result gpr
        JOIN src.game g ON g.id = gpr.game_id
        JOIN src.season_stage ss ON ss.id = g.season_stage_id
        WHERE gpr.player_id = pt.player_id
          AND ss.league_season_id = ls.id
      );


-- 既存 player_season_stats 互換。ステージ合算。
--   points  : ペナルティを含まない
--   penalty : ペナルティのみ
CREATE TEMP VIEW player_season_stats AS
SELECT
    r.player_id * 10000 + g.season      AS id,
    r.player_id,
    g.season,
    COUNT(*)                            AS games,
    ROUND(SUM(r.points), 1)             AS points,
    SUM(CASE WHEN r.rank = 1 THEN 1 ELSE 0 END) AS rank_1st,
    SUM(CASE WHEN r.rank = 2 THEN 1 ELSE 0 END) AS rank_2nd,
    SUM(CASE WHEN r.rank = 3 THEN 1 ELSE 0 END) AS rank_3rd,
    SUM(CASE WHEN r.rank = 4 THEN 1 ELSE 0 END) AS rank_4th,
    ROUND(SUM(r.penalty_points), 1)     AS penalty
FROM src.game_player_result r
JOIN _game g ON g.game_id = r.game_id
GROUP BY r.player_id, g.season;


-- ステージ別のチーム得点 (base_points はペナルティ込み)。
CREATE TEMP VIEW _team_stage_points AS
SELECT
    tsr.team_id,
    tsr.league_season_start_year AS season,
    tsr.stage,
    tsr.base_points,
    tsr.final_points
FROM src.team_season_stage_result tsr;


-- チーム・シーズン単位のペナルティ合計。
CREATE TEMP VIEW _team_penalty AS
SELECT
    pt.team_id,
    g.season,
    SUM(r.penalty_points) AS penalty
FROM src.game_player_result r
JOIN _game g          ON g.game_id   = r.game_id
JOIN src.player_team pt
  ON pt.player_id = r.player_id
 AND g.season BETWEEN pt.joined_season_year AND pt.left_season_year
GROUP BY pt.team_id, g.season;


-- 既存 team_season_points 互換。
--   points        : ペナルティを除いた合計
--   penalty       : ペナルティのみ
--   total_points  : points + penalty (= 全ステージの base_points 合計)
--   *_points      : ステージ別の累計 (final_points は繰越込み)
--   rank          : 到達ステージ優先 → そのステージの final_points 降順
CREATE TEMP VIEW team_season_points AS
SELECT
    team_id * 10000 + season AS id,
    season,
    team_id,
    points,
    rank,
    penalty,
    total_points,
    regular_points,
    semifinal_points,
    final_points
FROM (
    SELECT
        ts.team_id,
        ts.season,
        ROUND(agg.total_points - COALESCE(tp.penalty, 0), 1) AS points,
        ROUND(COALESCE(tp.penalty, 0), 1)                    AS penalty,
        ROUND(agg.total_points, 1)                           AS total_points,
        agg.regular_points,
        agg.semifinal_points,
        agg.final_points,
        ROW_NUMBER() OVER (
            PARTITION BY ts.season
            ORDER BY agg.stage_priority DESC, agg.reached_points DESC
        ) AS rank
    FROM _team_season ts
    JOIN (
        SELECT
            team_id,
            season,
            SUM(base_points)                                           AS total_points,
            ROUND(MAX(CASE WHEN stage='regular'   THEN final_points END), 1) AS regular_points,
            ROUND(MAX(CASE WHEN stage='semifinal' THEN final_points END), 1) AS semifinal_points,
            ROUND(MAX(CASE WHEN stage='final'     THEN final_points END), 1) AS final_points,
            MAX(CASE stage WHEN 'final' THEN 3 WHEN 'semifinal' THEN 2 ELSE 1 END) AS stage_priority,
            -- 到達した最終ステージの累計ポイント
            ROUND(COALESCE(
                MAX(CASE WHEN stage='final'     THEN final_points END),
                MAX(CASE WHEN stage='semifinal' THEN final_points END),
                MAX(CASE WHEN stage='regular'   THEN final_points END)
            ), 1) AS reached_points
        FROM _team_stage_points
        GROUP BY team_id, season
    ) agg ON agg.team_id = ts.team_id AND agg.season = ts.season
    LEFT JOIN _team_penalty tp ON tp.team_id = ts.team_id AND tp.season = ts.season
);


-- 反則・チョンボの記録 (既存アプリには無い新規ビュー)。
CREATE TEMP VIEW foul_plays AS
SELECT
    f.id,
    g.season,
    g.game_date,
    g.game_number,
    g.venue,
    g.table_type,
    f.actor_player_id AS player_id,
    p.name            AS player_name,
    f.type,
    f.penalty_points,
    f.is_restarted,
    f.description,
    k.round,
    k.honba_count,
    f.kyoku_id,
    k.game_id
FROM src.foul_play f
JOIN src.kyoku  k ON k.id = f.kyoku_id
JOIN _game      g ON g.game_id = k.game_id
JOIN src.player p ON p.id = f.actor_player_id;
