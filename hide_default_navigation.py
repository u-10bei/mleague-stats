#!/usr/bin/env python3
"""
サイドバーデフォルトナビゲーション非表示化スクリプト

すべてのページファイルに hide_default_sidebar_navigation() を追加します。

使い方:
    python hide_default_navigation.py
"""

import os
import sys
import re
from pathlib import Path

# 更新対象のファイル
FILES = [
    "app.py",
    "pages/1_season_ranking.py",
    "pages/2_cumulative_ranking.py",
    "pages/3_admin.py",
    "pages/4_player_admin.py",
    "pages/5_season_update.py",
    "pages/6_player_stats_input.py",
    "pages/7_player_season_ranking.py",
    "pages/8_player_cumulative_ranking.py",
]

def add_hide_navigation(filepath):
    """
    ファイルに hide_default_sidebar_navigation() を追加
    
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
    
    # 既に追加済みかチェック
    if 'hide_default_sidebar_navigation()' in content:
        print(f"✅ 既に修正済みです")
        return True
    
    # バックアップを作成
    backup_path = filepath + '.bak'
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"💾 バックアップ作成: {backup_path}")
    except Exception as e:
        print(f"⚠️  バックアップ作成失敗: {e}")
    
    # 修正を行う
    modified = False
    
    # 1. importに hide_default_sidebar_navigation を追加
    # パターン1: from db import で始まる行を探す
    import_pattern = r'(from db import )([^\n]+)'
    import_match = re.search(import_pattern, content)
    
    if import_match:
        full_import = import_match.group(0)
        import_list = import_match.group(2).strip()
        
        # 既にimportに含まれているかチェック
        if 'hide_default_sidebar_navigation' not in import_list:
            # 最後にカンマがなければ追加
            if not import_list.endswith(','):
                import_list += ','
            # hide_default_sidebar_navigationを追加
            new_import = f"from db import {import_list} hide_default_sidebar_navigation"
            content = content.replace(full_import, new_import)
            print(f"✓ importに追加しました")
            modified = True
        else:
            print(f"✓ importは既に修正済みです")
    else:
        print(f"⚠️  'from db import' が見つかりませんでした")
        return False
    
    # 2. st.set_page_config() の後に関数呼び出しを追加
    # パターン: st.set_page_config(...) の後に追加
    config_pattern = r'(st\.set_page_config\([^)]+\)\n)\n'
    config_match = re.search(config_pattern, content, re.DOTALL)
    
    if config_match:
        # 関数呼び出しを追加
        insertion_text = '\n# デフォルトのサイドバーナビゲーションを非表示\nhide_default_sidebar_navigation()\n\n'
        content = content.replace(
            config_match.group(0),
            config_match.group(1) + insertion_text
        )
        print(f"✓ 関数呼び出しを追加しました")
        modified = True
    else:
        # もう少し柔軟なパターンで試す
        config_pattern2 = r'(st\.set_page_config\([^)]+\))\n'
        config_match2 = re.search(config_pattern2, content, re.DOTALL)
        
        if config_match2:
            insertion_text = '\n\n# デフォルトのサイドバーナビゲーションを非表示\nhide_default_sidebar_navigation()\n'
            content = content.replace(
                config_match2.group(0),
                config_match2.group(1) + insertion_text
            )
            print(f"✓ 関数呼び出しを追加しました")
            modified = True
        else:
            print(f"⚠️  'st.set_page_config()' が見つかりませんでした")
            return False
    
    if not modified:
        print(f"⚠️  変更が適用されませんでした")
        return False
    
    # ファイルに書き込む
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 更新完了")
        return True
    except Exception as e:
        print(f"❌ ファイル書き込みエラー: {e}")
        # バックアップから復元を試みる
        if os.path.exists(backup_path):
            try:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                print(f"🔄 バックアップから復元しました")
            except:
                pass
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
    print("サイドバーデフォルトナビゲーション非表示化スクリプト")
    print("=" * 70)
    print("\nStreamlitのサイドバーに自動表示されるページリストを非表示にします")
    
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
    skipped = 0
    failed = 0
    
    for filepath in FILES:
        result = add_hide_navigation(filepath)
        if result:
            # 既に修正済みかチェック
            with open(filepath, 'r', encoding='utf-8') as f:
                if 'hide_default_sidebar_navigation()' in f.read():
                    updated += 1
                else:
                    skipped += 1
        else:
            failed += 1
    
    # 結果表示
    print("\n" + "=" * 70)
    print("完了")
    print("=" * 70)
    print(f"\n✅ 更新成功: {updated}件")
    if skipped > 0:
        print(f"⏭️  スキップ: {skipped}件（既に修正済み）")
    if failed > 0:
        print(f"❌ 更新失敗: {failed}件")
    
    print("\n📌 次のステップ:")
    print("   1. 各ファイルの変更内容を確認してください")
    print("   2. streamlit run app.py でアプリを起動")
    print("   3. サイドバーを確認してください")
    print("   4. 問題がある場合は .bak ファイルから復元できます")
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
        import traceback
        traceback.print_exc()
        sys.exit(1)
