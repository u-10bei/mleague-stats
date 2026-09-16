# mleague-stats 🀄

Mリーグの対戦結果を可視化するStreamlitダッシュボードです。

## 機能

### 閲覧機能

**チーム成績**
- **トップページ**: Mリーグの概要とチーム一覧、最新シーズンのハイライト
- **年度別チームランキング**: 各シーズンのチーム別成績と順位推移グラフ（月別ランキング・席順別統計・対局時間ランキング含む）
- **累積チームランキング**: 全シーズン通算のチーム成績と累積ポイント推移グラフ
- **チーム半荘別分析**: 半荘記録からチーム成績を分析（席順別・試合番号別・直対ランキング・曜日別分析）

**選手成績**
- **年度別選手ランキング**: 各シーズンの選手別成績とランキング、順位推移グラフ
- **累積選手ランキング**: 全シーズン通算の選手成績と累積ポイント推移グラフ、選手別詳細履歴（月別・席順別統計・対局時間ランキング含む）
- **選手半荘別分析**: 半荘記録から選手成績を分析（席順別・試合番号別・直対・曜日別分析）

**詳細分析**
- **統計分析**: 選手の席別パフォーマンス、ポジション分析
- **連続記録**: 連勝・連敗・連続連対・連続逆連対の記録分析（選手別・チーム別）
- **対局記録**: 対局の時間記録（最長・最短・平均試合時間）

### 管理機能

**補完データ管理**（既定で無効 / ローカル専用）

対局結果・選手・チームのマスタは konoui DB が正データなので入力不要です。
konoui DB に無い情報だけを 1 ページで編集します。
公開環境では書き込みがコンテナ再起動で消えるため、既定で無効にしています
（有効化は「デプロイ」の節を参照）。

- **対局時間**: OCR 結果の CSV 取り込みと手入力、2 段階の異常検出
- **チーム名履歴**: 年度別のチーム名（konoui DB は現行名のみ保持）
- **チーム略称 / カラー**: グラフの凡例と色
- **選手プロフィール**: 生年月日・所属プロ団体

## セットアップ

対局データは [konoui/m-league-game-db](https://github.com/konoui/m-league-game-db) の
配布DB を**正データ**として利用します。アプリが実際に参照する 11 テーブルだけを
抜き出した**軽量DB** (`data/mleague_konoui_slim.sqlite3` / 約5MB) をリポジトリに
同梱しているため、**クローンしただけで動きます**。

局・イベント単位の分析をする場合だけ、562MB の配布DB を取得してください
（置いておくと自動的にそちらが使われます）。

### ローカル環境

```bash
# リポジトリをクローン
git clone https://github.com/your-username/mleague-stats.git
cd mleague-stats

# 依存関係をインストール
pip install -r requirements.txt

# 動作確認
python db_konoui.py          # 互換ビューの行数を表示
python validate_games.py     # 全試合の整合性検証

# 起動（補完データ管理も使う場合は MLEAGUE_ADMIN=1 を付ける）
streamlit run app.py
```

### 配布DB を使う場合（任意）

```bash
curl -L -O https://github.com/konoui/m-league-game-db/releases/latest/download/database.zip
unzip database.zip -d data/
rm database.zip
```

### GitHub Codespaces

1. GitHubリポジトリで「Code」→「Codespaces」→「Create codespace on main」
2. 自動的に環境がセットアップされます（`pip install` まで実行されます）
3. ターミナルで `streamlit run app.py`

## プロジェクト構成

```
mleague-stats/
├── .devcontainer/
│   └── devcontainer.json          # Codespaces設定
├── .github/workflows/
│   ├── ci.yml                     # push/PR ごとの検証
│   └── update-konoui-db.yml       # konoui 新リリースの取り込みPR（週次）
├── .streamlit/
│   ├── config.toml                # Streamlit 設定
│   └── secrets.toml.example       # 補完データ管理を有効にする雛形
├── data/
│   ├── mleague_konoui_slim.sqlite3 # 軽量DB（5MB／Git管理／Cloud はこれを使う）
│   ├── mleague_local.db           # 補完テーブルのみ（数十KB／Git管理）
│   ├── konoui_release.txt         # 取り込み済みの konoui リリースタグ
│   ├── database.sqlite3           # konoui 配布DB（562MB／任意／.gitignore）
│   └── mleague.db                 # 移行前の旧DB（参照用に保持）
├── pages/
│   ├── 1_season_ranking.py        # 年度別チームランキング
│   ├── 2_cumulative_ranking.py    # 累積チームランキング
│   ├── 7_player_season_ranking.py # 年度別選手ランキング
│   ├── 8_player_cumulative_ranking.py # 累積選手ランキング
│   ├── 10_team_game_analysis.py   # チーム半荘別分析
│   ├── 13_player_game_analysis.py # 選手半荘別分析
│   ├── 14_statistical_analysis.py # 統計分析（席別パフォーマンス）
│   ├── 15_game_records.py         # 対局記録（試合時間）
│   ├── 16_streak_records.py       # 連続記録（連勝・連敗・連対）
│   ├── 17_player_rating.py        # レーティング（Elo風）
│   └── 18_local_data_admin.py     # 補完データ管理（既定で無効）
├── app.py                         # メインアプリ（トップページ）
├── db.py                          # データ取得ユーティリティ／管理機能の有効判定
├── db_konoui.py                   # ATTACH と互換ビュー構築（DB の自動選択）
├── build_slim_db.py               # 配布DB → 軽量DB の生成
├── setup_views.sql                # 補完テーブル定義 ＋ 互換ビュー定義
├── validate_games.py              # 整合性検証 ＋ 対局時間の取り込み
├── migrate_local.py               # 旧DBの補完データ移行（初回のみ）
├── recalculate_ratings.py         # レーティングの遡及計算
├── init_db.py                     # 旧DB用の初期化スクリプト（移行後は未使用）
├── requirements.txt
└── README.md
```

## データについて

### 正データ: konoui/m-league-game-db

対局結果・選手・チームのマスタは
[konoui/m-league-game-db](https://github.com/konoui/m-league-game-db) の配布 DB が正データです。
2018-10-01 以降の全試合を、局・イベント単位まで含めて収録しています。

配布 DB は読み取り専用で扱い、毎シーズン最新のリリースに差し替えます。

### 補完データ: data/mleague_local.db

konoui DB に無い情報だけを自前で持ちます。数十 KB なので Git 管理します。

| テーブル | 内容 |
|---|---|
| `game_time` | 対局時間（開始・終了時刻）。konoui DB に無い唯一の実データ |
| `team_name_history` | 年度別のチーム名（konoui DB は現行名のみ保持） |
| `team_meta` | チーム略称・チームカラー |
| `player_profile` | 選手の生年月日・所属プロ団体 |
| `player_ratings` / `rating_history` | Elo 風レーティング（アプリ独自の計算結果） |
| `rating_state` | レーティング計算済みフラグ |

### 対局時間の取り込み

1 試合あたり開始時刻と終了時刻の 2 つだけを、公式ビューアからの OCR で埋めます。

```csv
date,match_number,venue,start_time,end_time
2025-09-25,1,A,19:00,20:35
2025-09-25,1,B,19:00,20:20
```

`venue` は 2025 シーズン以降の A卓/B卓。2024 以前は全て `A`（省略可）。

```bash
python validate_games.py --import-times ocr.csv
```

`date + match_number + venue` から試合を解決して UPSERT します。
該当試合が無い行はスキップして報告するので、OCR の読み違いでデータが壊れません。

取り込み後は 2 段階で異常を検出します。

| 検出 | 条件 |
|---|---|
| 要確認 | 対局時間が 30〜180 分の範囲外 |
| 外れ値 | 局数あたりの所要分が中央値の 0.6 倍未満 / 1.6 倍超 |

OCR の読み違いは「局数の割に極端に長い/短い」形で出るため、konoui DB の局数と
突き合わせると単純な範囲チェックより精度よく拾えます。日跨ぎ（23:50→00:30）も自動で扱います。

### 旧DBからの移行（初回のみ）

移行前の `data/mleague.db` から補完データを移し替えます。
`player_id` / `team_id` は konoui 側の ID が正になるため、**選手名・チーム名で突き合わせます**。

```bash
python migrate_local.py --dry-run   # 突き合わせ結果の確認
python migrate_local.py             # 移行実行
python recalculate_ratings.py       # 全対局でレーティングを再計算
```

## データベース

konoui 配布 DB を `src` として ATTACH し、既存アプリが参照しているテーブル名を
**互換ビュー**で再現しています。既存ページの SQL はほぼそのまま動きます。

```
data/database.sqlite3   konoui 配布DB（正データ／読み取り専用）
data/mleague_local.db   補完テーブルのみ
```

### なぜ TEMP ビューなのか

SQLite はビューから別の ATTACH 先を参照できません。したがって互換ビューは永続化できず、
接続のたびに TEMP で作ります（`db_konoui.py` が自動で行います）。
副作用として、konoui DB を差し替えてもビュー定義が古いまま残る事故が起きません。

### 提供される互換ビュー

| ビュー | 説明 |
|---|---|
| `game_results` | 半荘記録。`game_id` `venue` `score` を追加。`start_time`/`end_time` は補完テーブル由来 |
| `players` | 選手マスター。`player_name_kana` を追加。`birth_date`/`pro_org` は補完テーブル由来 |
| `teams` | チームマスター。`short_name`/`color` は補完テーブル由来 |
| `team_names` | 年度別チーム名。自前履歴があれば優先、無ければ現行名 |
| `player_teams` | 選手所属履歴。joined〜left を年度に展開 |
| `player_season_stats` | 選手シーズン成績。ステージ合算 |
| `team_season_points` | チームシーズン成績。`penalty` を分離し `total_points`/`regular_points`/`semifinal_points`/`final_points` を追加 |
| `foul_plays` | 反則・チョンボの記録（新規） |

`team_season_points` の `points` は全ステージ合算（ペナルティ除く）、`rank` は到達ステージを
加味した M リーグ公式の最終順位です。ファイナルは繰越込みで決まるため、
合算ポイントの降順と `rank` は一致しない年があります。

### 整合性検証

```bash
python validate_games.py
```

M リーグ公式ルールに沿った検証を行います。`check_one_game(con, game_id)` は
入力画面のチェックにそのまま使えます。

| ルール | 内容 |
|---|---|
| 着順 | 1 + 自分より素点が多い人数（同点は同着＝1224 方式、次の順位は欠番） |
| 同着 | 同着の選手は素点もポイントも一致する（順位点は折半） |
| 素点合計 | 100000 − 未回収供託×1000（オーラス流局で未回収の供託は没収。最大 4 本） |
| ポイント合計 | 0（浮動小数のため許容誤差 0.05） |

### ペナルティ（チョンボ）の扱い

konoui の `game_player_result.points` にペナルティは含まれず、`penalty_points` が別カラムです。
一方 `team_season_stage_result.base_points` には含まれています。
互換ビュー `team_season_points` はこれを分離し、`points`（ペナルティ除く）と `penalty` を
別々に返します。`total_points` が合計です。

### 2025シーズンの2会場制

1 日 2 会場（A卓/B卓）制です。ビュー側で B卓の `game_number` を +2 しています
（A卓 1,2 / B卓 3,4）。`venue` カラムで元の会場を参照できます。2024 以前は全て A卓です。

### さらに踏み込んだ分析

互換ビューを経由せず `src.*` を直接叩けば、局・イベント単位の分析ができます。

| テーブル | 使い道 |
|---|---|
| `src.player_state` | 各巡目の手牌・シャンテン数・フリテン |
| `src.discard_event` | 手出し/ツモ切りフラグ |
| `src.player_tenpai_state` | 待ち牌・待ちの種類・神目線の残り枚数 |
| `src.agari_yaku_event` | 役別の集計 |
| `src.tenpai_agari_matrix` | 待ち牌ごとのあがり可能性と役 |
| `src.player_season_stage_stats` | 和了率・放銃率・副露率などの完成済み統計ビュー |

## 画面の使い方

### 閲覧画面

#### チーム成績

**年度別チームランキング（📊）**
- シーズンを選択して、そのシーズンのチーム成績を表示
- 横棒グラフと順位表で可視化
- 全シーズンの順位推移グラフ
- 月別ランキング（累積ポイント推移・平均順位推移）
- 席順別統計（東・南・西・北家での成績）
- 対局時間ランキング（最長・最短・平均試合時間）

**累積チームランキング（🏆）**
- 全シーズン通算のチーム成績を表示
- 累積ポイント、参加シーズン数、平均ポイント
- 累積ポイント推移グラフ
- チーム別の詳細履歴

**チーム半荘別分析（📈）**
- 半荘記録からチーム成績を分析
- 席順別ランキング（東・南・西・北家での成績）
- 試合番号別ランキング（第1〜4試合での成績）
- 直対ランキング（チーム間の対戦成績）
- 曜日別分析（チーム別の曜日ごとの対局数・平均ポイント・平均順位・順位割合）
- 全期間またはシーズン別で集計可能

#### 選手成績

**年度別選手ランキング（📊）**
- シーズンを選択して、そのシーズンの選手成績を表示
- 上位20名の横棒グラフと上位10名のランキング表
- 全選手の詳細ランキング（試合数、ポイント、順位回数、平均順位）
- 選手名検索、最低試合数フィルター
- 全シーズン順位推移グラフ（現シーズン上位10名）
- 月別ランキング（累積ポイント・平均順位）
- 席順別統計（東・南・西・北家での成績）
- 対局時間ランキング（最長・最短・平均試合時間）

**累積選手ランキング（🏆）**
- 全シーズン通算の選手成績を表示
- 上位20名の累積ポイント棒グラフ
- 累積ポイント推移グラフ（上位10名）
- 全選手の詳細ランキング（試合数、累積ポイント、順位回数、参加シーズン数、平均順位）
- 選手名検索、最低参加シーズン数・試合数フィルター
- 選手別のシーズン成績履歴
- 月別ランキング（全期間通算）
- 席順別統計（全期間）
- 対局時間ランキング（全期間）

**選手半荘別分析（📈）**
- 半荘記録から選手成績を分析
- 席順別ランキング（東・南・西・北家での成績）
- 試合番号別ランキング（第1〜4試合での成績）
- 直対ランキング（選手間の対戦成績・累積pt差）
- 曜日別分析（選手別の曜日ごとの対局数・平均ポイント・平均順位・順位割合）
- 全期間またはシーズンを選択可能

#### 詳細分析

**統計分析（📈）**
- 選手の席別パフォーマンス分析
- 各席（東・南・西・北）での成績を可視化
- トップ率・平均順位・平均ポイントを比較
- レーダーチャートで得意席を一目で把握

**連続記録（🔥）**
- 選手別・チーム別の連続記録を分析
- **連勝**: 連続1位
- **連敗**: 連続4位
- **連続連対**: 連続2位以内
- **連続逆連対**: 連続3位以下

**表示内容**
- 現在進行中の連続記録（TOP10）
  - 順位、選手名、連続数、開始日
- 歴代最長記録（TOP10）
  - 順位、選手名、連続数、開始日、終了日
  - 進行中の記録には✅マークを表示

**フィルター**
- 全期間またはシーズン別で集計
- 選択した期間内での連続記録を計算

**特徴**
- 現在の調子（連勝中・連敗中）が一目でわかる
- 歴代記録との比較が可能
- 期間を絞って分析できる

**対局記録（📜）**
- 対局の時間記録を分析
- 最長・最短・平均試合時間
- シーズン別・月別の傾向
- 時間帯別の分布

### 管理画面

#### 補完データ管理（🛠️）

konoui DB に無い情報だけを編集します。対局結果・選手・チームのマスタは
konoui DB が正データなので、このページでは編集しません。
入力量は移行前の数十分の一です。

**⏱️ 対局時間**

- 登録済み / 未登録の件数を表示
- OCR 結果の CSV を取り込み（該当試合が無い行はスキップして報告）
- シーズンと試合を選んで手入力（所要時間をその場で表示）
- 2 段階の異常検出（範囲外・局数あたり所要分の外れ値）

**🏢 チーム名履歴**

- 年度別のチーム名を編集
- 自前履歴を削除すると konoui の現行名に戻ります

**🎨 チーム略称 / カラー**

- グラフの凡例に使う略称と、チームカラーを編集

**👤 選手プロフィール**

- 生年月日と所属プロ団体を編集
- 氏名・かな・所属チームは konoui DB が正データのため編集できません

## 📈 半荘記録の活用

互換ビュー `game_results` は全 7,600 行超の半荘記録を保持しており、
以下の SQL がそのまま使えます。

### 詳細分析の例

**選手ごとの席別成績**
```sql
SELECT 
    seat_name,
    COUNT(*) as games,
    AVG(points) as avg_points,
    AVG(rank) as avg_rank,
    SUM(CASE WHEN rank = 1 THEN 1 ELSE 0 END) as first_count
FROM game_results
WHERE player_id = ? AND season = ?
GROUP BY seat_name;
```
→ 各席（東・南・西・北）での成績を分析し、得意な席を把握

**対戦相手との勝率**
```sql
SELECT 
    p2.player_name as opponent,
    COUNT(*) as games,
    AVG(CASE WHEN gr1.rank < gr2.rank THEN 1 ELSE 0 END) as win_rate
FROM game_results gr1
JOIN game_results gr2 ON gr1.game_date = gr2.game_date 
    AND gr1.game_number = gr2.game_number
JOIN players p2 ON gr2.player_id = p2.player_id
WHERE gr1.player_id = ? AND gr2.player_id != ?
GROUP BY p2.player_name;
```
→ 特定の選手との対戦成績を分析

**日付ごとの成績推移**
```sql
SELECT 
    game_date,
    COUNT(*) as games,
    AVG(points) as avg_points,
    AVG(rank) as avg_rank
FROM game_results
WHERE player_id = ? AND season = ?
GROUP BY game_date
ORDER BY game_date;
```
→ シーズン中の調子の波を可視化

**卓区分別の成績**
```sql
SELECT 
    table_type,
    COUNT(*) as games,
    AVG(points) as avg_points,
    AVG(rank) as avg_rank
FROM game_results
WHERE player_id = ? AND season = ?
GROUP BY table_type;
```
→ レギュラー、セミファイナル、ファイナルでの成績を比較

### 活用シーン

**選手の強み・弱みの分析**
- 席別成績から得意な席を特定
- 時期別成績から調子の波を把握
- 重要な対局での成績を分析

**チーム戦略の立案**
- 選手配置の最適化
- 対戦相手との相性分析
- セミファイナル・ファイナル対策

**ファンの楽しみ方**
- 推し選手の詳細な成績追跡
- 選手同士の対戦履歴確認
- 印象的な対局の記録

### 将来の機能拡張

半荘記録を基盤として、以下の機能を実装予定：
- 📊 移動平均の表示
- 🔄 対戦相手との勝率分析
- 🔥 席×対戦相手のヒートマップ

## デプロイ

### Streamlit Community Cloud

konoui 配布DB (562MB) はリポジトリに含められないため、アプリが実際に参照する
11 テーブルだけを抜き出した**軽量DB** (`data/mleague_konoui_slim.sqlite3` / 約5MB) を
同梱しています。クローンしただけで動くので、追加の準備なしにデプロイできます。

1. [share.streamlit.io](https://share.streamlit.io) にアクセス
2. 「New app」からこのリポジトリを選択
3. メインファイルに `app.py` を指定
4. 「Deploy」をクリック

Secrets の設定は不要です。**補完データ管理ページは既定で無効**なので、
そのままデプロイしても管理機能は露出しません。

以降は `main` への push で自動的に再デプロイされます。

### 補完データ管理の有効化

補完データ管理は既定で無効です。公開環境ではコンテナ再起動で書き込みが消えるため、
そもそも出す意味がありません。ローカルで使うときだけ有効にします。

```bash
# 環境変数で有効化
MLEAGUE_ADMIN=1 streamlit run app.py
```

または `.streamlit/secrets.toml`（`.gitignore` 済み）に書きます。

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

サイドバーからリンクを外すだけでなく、URL を直接開いた場合もページ側で止めています。

### 使用する DB の自動選択

`db_konoui.py` は次の順で使う DB を決めます。

| 優先 | DB | 用途 |
|---|---|---|
| 1 | 環境変数 `KONOUI_DB_PATH` | 明示指定（CI など） |
| 2 | `data/database.sqlite3` (562MB) | ローカル開発。局・イベント単位の分析もできる |
| 3 | `data/mleague_konoui_slim.sqlite3` (5MB) | Community Cloud。Git 管理されている |

軽量DB でも互換ビューの内容は配布DB と完全に一致します（全1,918試合、8ビュー）。
`src.player_state` などの局・イベント単位テーブルを直接叩く分析をする場合だけ、
配布DB が必要です。

### 軽量DB の更新

konoui の新しいリリースが出たら作り直します。

```bash
curl -L -O https://github.com/konoui/m-league-game-db/releases/latest/download/database.zip
unzip database.zip -d data/
python build_slim_db.py     # data/mleague_konoui_slim.sqlite3 を再生成
python validate_games.py    # 検証
```

GitHub Actions が毎週月曜にこれを自動実行し、差分があれば PR を作成します
（`.github/workflows/update-konoui-db.yml`）。手動実行も可能です。
取り込み済みのリリースは `data/konoui_release.txt` に記録されます。

### CI

`.github/workflows/ci.yml` が push / PR ごとに次を検証します。

- 軽量DB で互換ビューが構築できること
- 全1,918試合の整合性
- 全ページがエラーなく読み込めること
- 補完データ管理が既定で無効であること

## 今後の拡張予定

### 実装済み ✅

**データ基盤**
- [x] konoui/m-league-game-db を正データ化（互換ビューで既存ページのSQLを維持）
- [x] 補完テーブルの分離（対局時間・チーム名履歴・略称/カラー・選手プロフィール）
- [x] Mリーグ公式ルールに沿った整合性検証（同着1224方式・供託没収・浮動小数誤差）
- [x] 対局時間のOCR取り込みと2段階の異常検出

**基本機能**

> 下記の入力系機能は konoui DB の正データ化により不要となり、
> 「補完データ管理」ページに統合されました。
- [x] 基本的なチーム成績表示（年度別・累積ランキング）
- [x] データ管理機能（チーム・シーズンポイント、ペナルティ入力）
- [x] 選手管理機能（登録・編集・削除、生年月日・所属団体管理）
- [x] チーム管理機能（チームマスター情報の管理）
- [x] シーズン更新処理（チーム名変更・選手移籍の一括処理）
- [x] 選手成績入力（一覧表示・一括入力、ペナルティ入力）
- [x] データ整合性チェック（チームスコア、選手スコア）
- [x] 選手別成績ページ（年度別ランキング・累積ランキング）
- [x] 半荘記録入力（対局結果の詳細記録、開始・終了時間、データ編集・削除）

**選手詳細関連**
- [x] 選手個別詳細ページ（プロフィール・シーズン別成績推移）
- [x] 選手間の成績比較機能（直対の累積pt差・直対マトリックス） — 実装（部分）

**分析機能**
- [x] 半荘別成績分析
  - [x] チーム分析（席順別・試合番号別・直対ランキング・曜日別）
  - [x] 選手分析（席順別・試合番号別・直対ランキング・曜日別）
- [x] 統計分析（選手の席別パフォーマンス）
- [x] 対局記録（試合時間の記録と分析）
- [x] 月別・席順別・対局時間ランキング（年度別チーム/選手ランキング、累積選手ランキングに実装）
- [x] 連続記録分析（連勝・連敗・連続連対・連続逆連対、選手別・チーム別対応）
- [x] Elo風レーティングシステム（4人麻雀用、期待順位の線形補間、自動更新と遡及計算）

**技術的改善**
- [x] Streamlit 1.44.0+ 非推奨警告の修正（use_container_width → width）
- [x] Pandas 2.1.0+ 非推奨警告の修正（applymap → map）

### 今後の実装予定 🚀

**選手詳細機能**

- [ ] 選手間の成績比較機能 — 部分実装: （直対の累積pt差・直対マトリックスを実装。勝率(%表示)は今後の実装予定）

**半荘記録の活用**
- [ ] 移動平均の表示
- [ ] 対戦相手との勝率分析 — 部分実装: 直対の累積pt差は実装済み。勝率(WinRate)表示は未実装。
- [ ] 席×対戦相手のヒートマップ

**連続記録の拡張**
- [ ] 対戦相手別の連続記録
- [ ] 席別の連続記録
- [ ] 連続ラス回避（4位以外）
- [ ] 連続プラス/マイナス収支
- [ ] 連続記録の推移グラフ（時系列）
- [ ] 連続期間中の詳細統計

**詳細統計**
- [ ] 高度な統計指標
  - [ ] 和了率・放銃率・副露率
  - [ ] 平均着順・トップ率・ラス回避率
  - [ ] 平均持ち点・リーチ率

**統計分析の拡張（14_statistical_analysis.pyより）**
- [ ] 卓区分別分析（レギュラー/セミファイナル/ファイナルの成績傾向）
- [ ] 月別・シーズン内推移（シーズン序盤・中盤・終盤での傾向）
- [ ] クラスタリングによるプレイスタイル分類
- [ ] Elo風レーティングの推定と推移
- [ ] 重要局面（オーラス等）の頻度・成功率分析

**対局記録の拡張（15_game_records.pyより）**
- [ ] 得点記録
  - [ ] 最高得点対局（単独トップ得点）
  - [ ] 最大点差対局（1位と4位の点差）
  - [ ] 箱割れ記録（マイナス得点の記録）
- [ ] 順位記録
  - [ ] 連続プラス収支記録（連続してプラスで終わった対局）
  - [ ] 連続同順位記録
- [ ] 珍しい記録
  - [ ] オーラス逆転記録
  - [ ] 同点記録
  - [ ] 全員プラス/全員マイナス対局

**データ管理**
- [ ] データのインポート/エクスポート機能
  - [ ] CSV形式でのエクスポート
  - [ ] バックアップ/リストア機能

**UI/UX改善**
- [ ] 検索・フィルター機能の強化
  - [ ] 複合条件検索
  - [ ] 期間指定フィルター
- [ ] データ可視化の強化
  - [ ] レーダーチャート（選手の強み・弱み）
  - [ ] ヒートマップ（対戦成績）
  - [ ] インタラクティブなグラフ

**パフォーマンス**
- [ ] 大量データ対応
- [ ] キャッシング機能
- [ ] ページネーション

## 技術スタック

- **フロントエンド**: Streamlit
- **データベース**: SQLite
- **可視化**: Plotly
- **データ処理**: Pandas

## ライセンス

MIT License
