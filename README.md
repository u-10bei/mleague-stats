# Mリーグダッシュボード 🀄

Mリーグの対戦結果を可視化するStreamlitダッシュボードです。

## 機能

- **トップページ**: Mリーグの概要とチーム一覧
- **年度別ランキング**: 各シーズンのチーム別成績と順位推移
- **累積ランキング**: 全シーズン通算の成績と推移

## セットアップ

### ローカル環境

```bash
# リポジトリをクローン
git clone https://github.com/your-username/mleague-stats.git
cd mleague-stats

# 依存関係をインストール
pip install -r requirements.txt

# アプリを起動
streamlit run app.py
```

### GitHub Codespaces

1. GitHubリポジトリで「Code」→「Codespaces」→「Create codespace on main」
2. 自動的に環境がセットアップされます
3. ターミナルで `streamlit run app.py` を実行

## プロジェクト構成

```
mleague-dashboard/
├── .devcontainer/
│   └── devcontainer.json    # Codespaces設定
├── data/
│   ├── team_season_points.csv  # シーズン別チームポイント
│   └── teams.csv               # チームマスターデータ
├── pages/
│   ├── 1_season_ranking.py         # 年度別ランキング
│   └── 2_cumulative_ranking.py     # 累積ランキング
├── app.py                   # メインアプリ（トップページ）
├── requirements.txt
└── README.md
```

## データについて

現在のデータはサンプルです。実際のMリーグ公式記録を反映するには、`data/` ディレクトリ内のCSVファイルを更新してください。

## デプロイ

### Streamlit Community Cloud

1. GitHubにリポジトリをプッシュ
2. [share.streamlit.io](https://share.streamlit.io) にアクセス
3. 「New app」からリポジトリを選択
4. メインファイルに `app.py` を指定
5. 「Deploy」をクリック

## 今後の拡張予定

- [ ] 選手別成績ページ
- [ ] 対戦詳細データ
- [ ] 和了率・放銃率などの詳細指標
- [ ] データの自動更新機能

## ライセンス

MIT License
