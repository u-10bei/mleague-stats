# Mリーグダッシュボード 🀄

Mリーグの対戦結果を可視化するStreamlitダッシュボードです。

## 機能

### 閲覧機能
- **トップページ**: Mリーグの概要とチーム一覧、最新シーズンのハイライト
- **年度別ランキング**: 各シーズンのチーム別成績と順位推移グラフ
- **累積ランキング**: 全シーズン通算の成績と累積ポイント推移グラフ

### 管理機能（開発環境用）
- **データ管理**: チーム情報・シーズンポイントの入力・編集・削除
- **選手管理**: 選手情報・所属履歴・シーズン成績の入力・編集・削除

## セットアップ

### ローカル環境

```bash
# リポジトリをクローン
git clone https://github.com/your-username/mleague-dashboard.git
cd mleague-dashboard

# 依存関係をインストール
pip install -r requirements.txt

# データベース初期化（初回のみ）
python init_db.py

# アプリを起動
streamlit run app.py
```

### GitHub Codespaces

1. GitHubリポジトリで「Code」→「Codespaces」→「Create codespace on main」
2. 自動的に環境がセットアップされます
3. ターミナルで `pip install -r requirements.txt` を実行
4. `streamlit run app.py` を実行

## プロジェクト構成

```
mleague-dashboard/
├── .devcontainer/
│   └── devcontainer.json          # Codespaces設定
├── data/
│   └── mleague.db                 # SQLiteデータベース
├── pages/
│   ├── 1_season_ranking.py        # 年度別ランキング
│   ├── 2_cumulative_ranking.py    # 累積ランキング
│   ├── 3_admin.py                 # データ管理（チーム・ポイント）
│   └── 4_player_admin.py          # 選手管理
├── app.py                         # メインアプリ（トップページ）
├── db.py                          # データベース接続ユーティリティ
├── init_db.py                     # データベース初期化スクリプト
├── migrate_add_players.py         # 選手テーブル追加マイグレーション
├── requirements.txt
└── README.md
```

## データベース

データはSQLiteデータベース (`data/mleague.db`) に保存されています。

### 初期化

```bash
# 新規作成（既存データは削除されます）
python init_db.py
```

### マイグレーション

```bash
# 既存データを保持したまま選手テーブルを追加
python migrate_add_players.py
```

### テーブル構造

#### チーム関連
| テーブル | 説明 |
|---------|------|
| `teams` | チームマスター（team_id, short_name, color, established） |
| `team_names` | チーム名履歴（team_id, season, team_name）※年度別のチーム名変更に対応 |
| `team_season_points` | シーズン別ポイント（season, team_id, points, rank） |

#### 選手関連
| テーブル | 説明 |
|---------|------|
| `players` | 選手マスター（player_id, player_name, birth_date, pro_org） |
| `player_teams` | 選手所属履歴（player_id, team_id, season） |
| `player_season_stats` | 選手シーズン成績（player_id, season, games, points, rank_1st〜4th） |

## 管理画面の使い方

### データ管理（⚙️）

| タブ | 機能 |
|-----|------|
| 📝 シーズンポイント入力 | チームのシーズンポイントを個別または一括で入力 |
| 🏷️ チーム名管理 | シーズンごとのチーム名を設定（名称変更対応） |
| 🏢 チーム管理 | チームの追加・編集・削除 |
| 📋 データ確認 | 登録データの確認・削除 |

### 選手管理（👤）

| タブ | 機能 |
|-----|------|
| 📝 選手登録 | 新規選手の登録（初期所属チーム設定） |
| ✏️ 選手編集 | 選手情報の編集、所属チーム履歴管理、削除 |
| 📊 成績入力 | シーズン成績の入力・更新（試合数、ポイント、着順回数） |
| 📋 選手一覧 | 登録選手の一覧表示 |

## デプロイ

### Streamlit Community Cloud

1. GitHubにリポジトリをプッシュ
2. [share.streamlit.io](https://share.streamlit.io) にアクセス
3. 「New app」からリポジトリを選択
4. メインファイルに `app.py` を指定
5. 「Deploy」をクリック

## 今後の拡張予定

- [ ] 選手別成績ページ（閲覧用）
- [ ] 対戦詳細データ
- [ ] 和了率・放銃率などの詳細指標
- [ ] データのインポート/エクスポート機能

## ライセンス

MIT License