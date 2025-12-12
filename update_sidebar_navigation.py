#!/usr/bin/env python3
"""
サイドバーナビゲーション一括更新スクリプト

全てのページファイルのサイドバーナビゲーションを統一されたものに更新します。

使い方:
    python update_sidebar_navigation.py
    
    # ドライラン（実際には書き込まない）
    python update_sidebar_navigation.py --dry-run
    
    # バックアップなし
    python update_sidebar_navigation.py --no-backup
"""

import os
import sys
import re
from datetime import datetime

# 統一されたサイドバーナビゲーション
SIDEBAR_NAVIGATION = '''# サイドバーナビゲーション
st.sidebar.title("🀄 メニュー")
st.sidebar.page_link("app.py", label="🏠 トップページ")
st.sidebar.markdown("### 📊 チーム成績")
st.sidebar.page_link("pages/1_season_ranking.py", label="📊 年度別ランキング")
st.sidebar.page_link("pages/2_cumulative_ranking.py", label="🏆 累積ランキング")
st.sidebar.page_link("pages/10_team_game_analysis.py", label="🎲 半荘別分析")
st.sidebar.markdown("### 👤 選手成績")
st.sidebar.page_link("pages/7_player_season_ranking.py", label="📊 年度別ランキング")
st.sidebar.page_link("pages/8_player_cumulative_ranking.py", label="🏆 累積ランキング")
st.sidebar.page_link("pages/13_player_game_analysis.py", label="🎲 半荘別分析")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/3_admin.py", label="⚙️ データ管理")
st.sidebar.page_link("pages/4_player_admin.py", label="👤 選手管理")
st.sidebar.page_link("pages/9_team_master_admin.py", label="🏢 チーム管理")
st.sidebar.page_link("pages/5_season_update.py", label="🔄 シーズン更新")
st.sidebar.page_link("pages/6_player_stats_input.py", label="📊 選手成績入力")
st.sidebar.page_link("pages/11_game_results_input.py", label="🎮 半荘記録入力")'''

# 更新対象のファイル
TARGET_FILES = [
    "app.py",
    "pages/1_season_ranking.py",
    "pages/2_cumulative_ranking.py",
    "pages/3_admin.py",
    "pages/4_player_admin.py",
    "pages/5_season_update.py",
    "pages/6_player_stats_input.py",
    "pages/7_player_season_ranking.py",
    "pages/8_player_cumulative_ranking.py",
    "pages/9_team_master_admin.py",
    "pages/10_team_game_analysis.py",
    "pages/11_game_results_input.py",
    "pages/13_player_game_analysis.py",
]

def find_sidebar_section(content):
    """
    ファイル内のサイドバーナビゲーションセクションを検出
    
    Returns:
        (start_index, end_index) or None
    """
    # パターン1: "# サイドバーナビゲーション" から始まる
    pattern1 = r'# サイドバーナビゲーション\n.*?(?=\n(?:st\.title|st\.markdown|st\.header|st\.subheader|#[^#]|$))'
    
    # パターン2: st.sidebar で始まる連続した行
    pattern2 = r'(st\.sidebar\..*?\n)+'
    
    # パターン1でマッチを試みる
    match = re.search(pattern1, content, re.DOTALL)
    if match:
        return (match.start(), match.end())
    
    # パターン2でマッチを試みる
    matches = list(re.finditer(pattern2, content))
    if matches:
        # 最初のst.sidebarブロックを対象とする
        match = matches[0]
        # コメント行を含める
        start = match.start()
        # 直前のコメント行をチェック
        lines = content[:start].split('\n')
        if lines and lines[-1].strip().startswith('#'):
            # コメント行を含める
            start = content[:start].rfind('\n', 0, start - len(lines[-1])) + 1
        return (start, match.end())
    
    return None

def update_file(filepath, dry_run=False, no_backup=False):
    """
    ファイルのサイドバーナビゲーションを更新
    
    Args:
        filepath: 更新対象のファイルパス
        dry_run: Trueの場合、実際には書き込まない
        no_backup: Trueの場合、バックアップを作成しない
    
    Returns:
        bool: 更新が成功したかどうか
    """
    if not os.path.exists(filepath):
        print(f"⚠️  ファイルが存在しません: {filepath}")
        return False
    
    # ファイルを読み込む
    with open(filepath, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # サイドバーセクションを検出
    section = find_sidebar_section(original_content)
    
    if section is None:
        print(f"⚠️  サイドバーセクションが見つかりません: {filepath}")
        print(f"     手動で追加してください")
        return False
    
    start, end = section
    
    # 新しいコンテンツを作成
    new_content = (
        original_content[:start] +
        SIDEBAR_NAVIGATION +
        '\n' +
        original_content[end:]
    )
    
    # 変更がない場合
    if new_content == original_content:
        print(f"✓  変更なし: {filepath}")
        return True
    
    if dry_run:
        print(f"🔍 [DRY RUN] 更新予定: {filepath}")
        print(f"   削除される行数: {original_content[start:end].count(chr(10))}")
        print(f"   追加される行数: {SIDEBAR_NAVIGATION.count(chr(10))}")
        return True
    
    # バックアップを作成
    if not no_backup:
        backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        print(f"📦 バックアップ作成: {backup_path}")
    
    # ファイルを更新
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ 更新完了: {filepath}")
    return True

def main():
    """メイン処理"""
    # コマンドライン引数をパース
    dry_run = '--dry-run' in sys.argv
    no_backup = '--no-backup' in sys.argv
    show_help = '--help' in sys.argv or '-h' in sys.argv
    
    if show_help:
        print(__doc__)
        return 0
    
    print("=" * 70)
    print("サイドバーナビゲーション一括更新")
    print("=" * 70)
    print()
    
    if dry_run:
        print("🔍 ドライランモード（実際には書き込みません）")
        print()
    
    if no_backup:
        print("⚠️  バックアップなしモード")
        print()
    
    # 更新対象のファイルを確認
    print(f"更新対象: {len(TARGET_FILES)}ファイル")
    print()
    
    # 確認
    if not dry_run:
        response = input("更新を開始しますか？ [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("\n中止しました")
            return 0
        print()
    
    # 各ファイルを更新
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for filepath in TARGET_FILES:
        try:
            if update_file(filepath, dry_run=dry_run, no_backup=no_backup):
                success_count += 1
            else:
                skip_count += 1
        except Exception as e:
            print(f"❌ エラー: {filepath}")
            print(f"   {e}")
            fail_count += 1
        print()
    
    # 結果サマリー
    print("=" * 70)
    print("更新結果")
    print("=" * 70)
    print(f"✅ 成功: {success_count}ファイル")
    print(f"⚠️  スキップ: {skip_count}ファイル")
    print(f"❌ 失敗: {fail_count}ファイル")
    print()
    
    if dry_run:
        print("🔍 ドライランモードでした。実際に更新するには --dry-run を外して実行してください。")
    elif success_count > 0:
        print("✅ 更新が完了しました。アプリを再起動してください。")
        if not no_backup:
            print("💡 バックアップファイルは *.backup_* という名前で保存されています。")
    
    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
