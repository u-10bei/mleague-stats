#!/usr/bin/env python3
"""
レーティングを初期化して遡及計算するスクリプト
すべての対局データから時系列でレーティングを再計算します
"""

import sqlite3
from db import DB_PATH, initialize_ratings_from_games

def recalculate_ratings():
    """レーティングを初期化して遡及計算"""
    print("=" * 60)
    print("🔄 レーティング遡及計算を開始します")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 現在の状態を確認
    cursor.execute("SELECT COUNT(*) FROM game_results")
    game_results_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT season, game_date, table_type, game_number 
            FROM game_results
        )
    """)
    unique_games = cursor.fetchone()[0]
    
    print(f"\n📊 現在のデータ:")
    print(f"  ├─ game_results レコード数: {game_results_count}")
    print(f"  └─ 一意な対局数: {unique_games}対局")
    
    # レーティング計算を実行
    print(f"\n⏳ レーティングを計算中...")
    initialize_ratings_from_games()
    
    # 計算結果を確認
    cursor.execute("SELECT SUM(games) FROM player_ratings")
    games_sum_result = cursor.fetchone()
    games_sum = games_sum_result[0] if games_sum_result[0] is not None else 0
    
    cursor.execute("SELECT COUNT(*) FROM player_ratings WHERE games > 0")
    players_with_rating = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT season, game_date, table_type, game_number 
            FROM game_results 
            WHERE rating_calculated = 1
        )
    """)
    calculated_games = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n✅ レーティング計算完了!")
    print(f"\n📊 計算結果:")
    print(f"  ├─ レーティング対象選手数: {players_with_rating}人")
    print(f"  ├─ player_ratings.games 合計: {games_sum}")
    print(f"  ├─ rating_calculated = 1 の対局数: {calculated_games}対局")
    print(f"  └─ 計算対象外の対局: {unique_games - calculated_games}対局")
    
    if games_sum == unique_games * 4:
        print(f"\n🎉 すべての対局がレーティング計算されました！")
    else:
        print(f"\n⚠️  注意: 一部の対局がレーティング計算されていません")
        print(f"   {unique_games}対局 × 4人 = {unique_games * 4} vs {games_sum}")

if __name__ == "__main__":
    recalculate_ratings()
