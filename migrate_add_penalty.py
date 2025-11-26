"""
ペナルティカラム追加マイグレーション

このスクリプトは以下を実行します：
1. team_season_points テーブルに penalty カラムを追加
2. player_season_stats テーブルに penalty カラムを追加

ペナルティは獲得ポイントから減算されるもので、現行の points は
ペナルティ適用後の最終ポイントを表します。

計算式: points = 獲得ポイント - penalty
または: 獲得ポイント = points + penalty

使い方:
  python migrate_add_penalty.py
"""

import sqlite3
import os
import sys

DB_PATH = "data/mleague.db"

def check_database():
    """データベースファイルの存在確認"""
    if not os.path.exists(DB_PATH):
        print(f"❌ データベースファイルが見つかりません: {DB_PATH}")
        print()
        print("先に init_db.py を実行してデータベースを作成してください。")
        return False
    return True

def check_column_exists(cursor, table_name, column_name):
    """カラムが既に存在するかチェック"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col[1] == column_name for col in columns)

def migrate_add_penalty():
    """ペナルティカラムを追加するマイグレーション"""
    
    print("=" * 70)
    print("ペナルティカラム追加マイグレーション")
    print("=" * 70)
    print()
    
    if not check_database():
        return 1
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. team_season_points テーブルにpenaltyカラムを追加
        print("【1】team_season_points テーブルの更新")
        print("-" * 70)
        
        if check_column_exists(cursor, "team_season_points", "penalty"):
            print("✓ penalty カラムは既に存在します")
        else:
            cursor.execute("""
                ALTER TABLE team_season_points
                ADD COLUMN penalty REAL DEFAULT 0
            """)
            print("✓ penalty カラムを追加しました")
        
        print()
        
        # 2. player_season_stats テーブルにpenaltyカラムを追加
        print("【2】player_season_stats テーブルの更新")
        print("-" * 70)
        
        if check_column_exists(cursor, "player_season_stats", "penalty"):
            print("✓ penalty カラムは既に存在します")
        else:
            cursor.execute("""
                ALTER TABLE player_season_stats
                ADD COLUMN penalty REAL DEFAULT 0
            """)
            print("✓ penalty カラムを追加しました")
        
        print()
        
        # コミット
        conn.commit()
        
        # 3. テーブル構造の確認
        print("【3】更新後のテーブル構造確認")
        print("-" * 70)
        
        print("\n◆ team_season_points テーブル:")
        cursor.execute("PRAGMA table_info(team_season_points)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        print("\n◆ player_season_stats テーブル:")
        cursor.execute("PRAGMA table_info(player_season_stats)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        print()
        
        # 4. データの確認
        print("【4】既存データの確認")
        print("-" * 70)
        
        cursor.execute("SELECT COUNT(*) FROM team_season_points")
        team_count = cursor.fetchone()[0]
        print(f"チームシーズンポイント: {team_count}件")
        
        cursor.execute("SELECT COUNT(*) FROM player_season_stats")
        player_count = cursor.fetchone()[0]
        print(f"選手シーズン成績: {player_count}件")
        
        if team_count > 0 or player_count > 0:
            print()
            print("💡 既存データのpenaltyはすべて0として初期化されました。")
            print("   必要に応じて、管理画面から修正してください。")
        
        print()
        print("=" * 70)
        print("✅ マイグレーション完了")
        print("=" * 70)
        print()
        
        print("【追加されたカラム】")
        print("  • team_season_points.penalty (REAL, DEFAULT 0)")
        print("  • player_season_stats.penalty (REAL, DEFAULT 0)")
        print()
        
        print("【ペナルティの扱い】")
        print("  • penalty: ペナルティポイント（マイナス値、例: -10.0）")
        print("  • points: 最終ポイント（ペナルティ適用後）")
        print("  • 獲得ポイント = points + |penalty|")
        print()
        
        print("【次のステップ】")
        print("  1. アプリを再起動してください")
        print("  2. データ管理ページでチームペナルティを入力できます")
        print("  3. 選手成績入力ページで選手ペナルティを入力できます")
        print("  4. 表示ページでペナルティ内訳が確認できます")
        print()
        
        return 0
        
    except Exception as e:
        conn.rollback()
        print()
        print(f"❌ エラーが発生しました: {e}")
        print()
        print("マイグレーションは失敗しました。データベースは変更されていません。")
        return 1
        
    finally:
        conn.close()

def verify_migration():
    """マイグレーション結果の検証"""
    
    print()
    print("=" * 70)
    print("マイグレーション検証")
    print("=" * 70)
    print()
    
    if not check_database():
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    success = True
    
    # team_season_points の検証
    if not check_column_exists(cursor, "team_season_points", "penalty"):
        print("❌ team_season_points.penalty カラムが見つかりません")
        success = False
    else:
        print("✓ team_season_points.penalty カラムが存在します")
    
    # player_season_stats の検証
    if not check_column_exists(cursor, "player_season_stats", "penalty"):
        print("❌ player_season_stats.penalty カラムが見つかりません")
        success = False
    else:
        print("✓ player_season_stats.penalty カラムが存在します")
    
    conn.close()
    
    print()
    if success:
        print("✅ 検証成功: すべてのカラムが正しく追加されています")
    else:
        print("❌ 検証失敗: 一部のカラムが見つかりません")
    
    return success

def main():
    """メイン処理"""
    
    # ヘルプ
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print(__doc__)
        return 0
    
    # 検証モード
    if len(sys.argv) > 1 and sys.argv[1] == '--verify':
        return 0 if verify_migration() else 1
    
    # 確認
    print("このスクリプトはデータベースに以下の変更を加えます:")
    print()
    print("  1. team_season_points テーブルに penalty カラムを追加")
    print("  2. player_season_stats テーブルに penalty カラムを追加")
    print()
    print("既存のデータは保持されます。")
    print()
    
    response = input("続行しますか？ [y/N]: ")
    if response.lower() not in ['y', 'yes']:
        print("\n中止しました")
        return 0
    
    print()
    
    # マイグレーション実行
    result = migrate_add_penalty()
    
    # 検証
    if result == 0:
        verify_migration()
    
    return result

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
