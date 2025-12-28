#!/usr/bin/env python3
"""
サイドバーナビゲーション一括更新スクリプト（連続記録追加版）

全ページのサイドバーナビゲーションに16_streak_records.pyへのリンクを追加します。
"""

import os
import re

# 新しいサイドバーナビゲーション
NEW_SIDEBAR = '''# サイドバーナビゲーション
st.sidebar.title("🀄 メニュー")
st.sidebar.page_link("app.py", label="🏠 トップページ")
st.sidebar.markdown("### 📊 チーム成績")
st.sidebar.page_link("pages/1_season_ranking.py", label="📊 年度別ランキング")
st.sidebar.page_link("pages/2_cumulative_ranking.py", label="🏆 累積ランキング")
st.sidebar.page_link("pages/10_team_game_analysis.py", label="📈 半荘別分析")
st.sidebar.markdown("### 👤 選手成績")
st.sidebar.page_link("pages/7_player_season_ranking.py", label="📊 年度別ランキング")
st.sidebar.page_link("pages/8_player_cumulative_ranking.py", label="🏆 累積ランキング")
st.sidebar.page_link("pages/13_player_game_analysis.py", label="📈 半荘別分析")
st.sidebar.markdown("---")
st.sidebar.page_link("pages/14_statistical_analysis.py", label="📈 統計分析")
st.sidebar.page_link("pages/16_streak_records.py", label="🔥 連続記録")
st.sidebar.page_link("pages/15_game_records.py", label="📜 対局記録")
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
    "pages/14_statistical_analysis.py",
    "pages/15_game_records.py",
]

def find_sidebar_section(content):
    """サイドバーナビゲーションセクションを検出"""
    # "# サイドバーナビゲーション" から次のセクションまで
    pattern = r'# サイドバーナビゲーション\n.*?(?=\n(?:st\.title|st\.markdown\("#|st\.header|st\.subheader|#[^#\s]|$))'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return (match.start(), match.end())
    return None

def update_file(filepath):
    """ファイルのサイドバーナビゲーションを更新"""
    if not os.path.exists(filepath):
        print(f"⚠️  ファイルが存在しません: {filepath}")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    section = find_sidebar_section(content)
    if section is None:
        print(f"⚠️  サイドバーセクションが見つかりません: {filepath}")
        return False
    
    start, end = section
    new_content = content[:start] + NEW_SIDEBAR + '\n' + content[end:]
    
    if new_content == content:
        print(f"✓  変更なし: {filepath}")
        return True
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ 更新完了: {filepath}")
    return True

def main():
    print("=" * 70)
    print("サイドバーナビゲーション一括更新（連続記録追加版）")
    print("=" * 70)
    print()
    
    success_count = 0
    fail_count = 0
    
    for filepath in TARGET_FILES:
        try:
            if update_file(filepath):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"❌ エラー: {filepath} - {e}")
            fail_count += 1
        print()
    
    print("=" * 70)
    print("更新結果")
    print("=" * 70)
    print(f"✅ 成功: {success_count}ファイル")
    print(f"❌ 失敗: {fail_count}ファイル")
    print()
    
    if success_count > 0:
        print("✅ 更新が完了しました。")
    
    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())