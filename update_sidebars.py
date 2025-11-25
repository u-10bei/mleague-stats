#!/usr/bin/env python3
"""
サイドバー自動更新スクリプト

既存の6つのページファイルのサイドバーを、
選手成績メニューを含む新しいサイドバーに更新します。

使い方:
    python update_sidebars.py
"""

import os
import sys
import re
from pathlib import Path

# 新しいサイドバーコード
NEW_SIDEBAR = '''# サイドバーナビゲーション
st.sidebar.title("🀄 メニュー")
st.sidebar.page_link("app.py", label="🏠 トップページ")
st.sidebar.markdown("### 📊 チーム成績")
st.sidebar.page_link("pages/1_season_ranking.py", label="📊 年度別ランキング")
st.sidebar.page_link("pages/2_cumulative_ranking.py", label="🏆 累積ランキング")
st.sidebar.markdown("### 👤 選手成績")
st.sidebar.page_link("pages/7_player_season_ranking.py", label="📊 年度別ランキング")
st.sidebar.page_link("pages/8_player_cumulative_ranking.py", label="🏆 累積ランキング")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/3_admin.py", label="⚙️ データ管理")
st.sidebar.page_link("pages/4_player_admin.py", label="👤 選手管理")
st.sidebar.page_link("pages/5_season_update.py", label="🔄 シーズン更新")
st.sidebar.page_link("pages/6_player_stats_input.py", label="📊 選手成績入力")'''

# 更新対象のファイル
FILES = [
    "pages/1_season_ranking.py",
    "pages/2_cumulative_ranking.py",
    "pages/3_admin.py",
    "pages/4_player_admin.py",
    "pages/5_season_update.py",
    "pages/6_player_stats_input.py",
]

def find_sidebar_section(content):
    """
    サイドバー部分を検索して、開始位置と終了位置を返す
    
    Returns:
        tuple: (start_index, end_index) or (None, None) if not found
    """
    # パターン1: # サイドバー から始まるコメントを探す
    patterns = [
        # コメント付き
        (r'# サイドバーナビゲーション\n', r'\n\nst\.title|st\.markdown\("#'),
        (r'# サイドバー\n', r'\n\nst\.title|st\.markdown\("#'),
        # コメントなし
        (r'st\.sidebar\.title\("🀄', r'\n\nst\.title|st\.markdown\("#'),
    ]
    
    for start_pattern, end_pattern in patterns:
        start_match = re.search(start_pattern, content)
        if start_match:
            start_pos = start_match.start()
            
            # 終了位置を探す（次のセクションの開始）
            end_match = re.search(end_pattern, content[start_pos:])
            if end_match:
                end_pos = start_pos + end_match.start()
                return start_pos, end_pos
    
    return None, None

def update_sidebar(filepath):
    """
    ファイルのサイドバーを更新
    
    Args:
        filepath: 更新対象のファイルパス
        
    Returns:
        bool: 成功した場合True
    """
    if not os.path.exists(filepath):
        print(f"❌ {filepath} が見つかりません")
        return False
    
    print(f"\n📝 処理中: {filepath}")
    
    # ファイルを読み込む
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ ファイル読み込みエラー: {e}")
        return False
    
    # サイドバー部分を検索
    start_pos, end_pos = find_sidebar_section(content)
    
    if start_pos is None:
        print(f"⚠️  サイドバー部分が見つかりませんでした")
        print(f"   {filepath} を手動で更新してください")
        return False
    
    # バックアップを作成
    backup_path = filepath + '.bak'
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"💾 バックアップ作成: {backup_path}")
    except Exception as e:
        print(f"⚠️  バックアップ作成失敗: {e}")
    
    # サイドバーを置き換え
    old_sidebar = content[start_pos:end_pos]
    new_content = content[:start_pos] + NEW_SIDEBAR + '\n\n' + content[end_pos:]
    
    # ファイルに書き込む
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ 更新完了")
        return True
    except Exception as e:
        print(f"❌ ファイル書き込みエラー: {e}")
        # バックアップから復元を試みる
        if os.path.exists(backup_path):
            with open(backup_path, 'r', encoding='utf-8') as f:
                with open(filepath, 'w', encoding='utf-8') as f2:
                    f2.write(f.read())
            print(f"🔄 バックアップから復元しました")
        return False

def verify_files():
    """
    更新対象のファイルが存在するか確認
    """
    missing = []
    for filepath in FILES:
        if not os.path.exists(filepath):
            missing.append(filepath)
    
    if missing:
        print("\n⚠️  以下のファイルが見つかりません:")
        for f in missing:
            print(f"   - {f}")
        print("\n   ファイルが存在するディレクトリで実行してください")
        return False
    
    return True

def main():
    """
    メイン処理
    """
    print("=" * 70)
    print("サイドバー自動更新スクリプト")
    print("=" * 70)
    print("\n選手成績メニューを含む新しいサイドバーに更新します")
    
    # ファイルの存在確認
    if not verify_files():
        return 1
    
    # 確認
    print(f"\n更新対象: {len(FILES)}ファイル")
    for f in FILES:
        print(f"  - {f}")
    
    response = input("\n更新を開始しますか？ [y/N]: ")
    if response.lower() not in ['y', 'yes']:
        print("\n中止しました")
        return 0
    
    # 更新実行
    print("\n" + "=" * 70)
    print("更新開始")
    print("=" * 70)
    
    updated = 0
    failed = 0
    
    for filepath in FILES:
        if update_sidebar(filepath):
            updated += 1
        else:
            failed += 1
    
    # 結果表示
    print("\n" + "=" * 70)
    print("完了")
    print("=" * 70)
    print(f"\n✅ 更新成功: {updated}件")
    if failed > 0:
        print(f"❌ 更新失敗: {failed}件")
    
    print("\n📌 次のステップ:")
    print("   1. streamlit run app.py でアプリを起動")
    print("   2. 各ページでサイドバーが正しく表示されるか確認")
    print("   3. 問題がある場合は .bak ファイルから復元してください")
    print("      例: cp pages/1_season_ranking.py.bak pages/1_season_ranking.py")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        sys.exit(1)
