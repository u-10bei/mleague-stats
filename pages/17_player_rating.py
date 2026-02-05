import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db import get_connection, get_player_ratings, get_player_rating_history, show_sidebar_navigation

sys.path.append("..")

st.set_page_config(
    page_title="レーティング | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide"
)

# サイドバーナビゲーション
show_sidebar_navigation()

st.title("📊 選手レーティング")

st.markdown("""
4人麻雀用のElo風レーティングシステムです。
対局結果に基づいて、選手の相対的な実力をレーティングで可視化します。

**システム仕様**
- 初期レート: 1500pt
- K値: 8
- 期待順位: 線形補間（対戦相手のレート差から計算）
- 順位スコア: 1位 +4.5、2位 +0.5、3位 -1.5、4位 -3.5
""")

# タブ構成
tab1, tab2, tab3 = st.tabs(["📈 レーティングランキング", "📊 個別詳細", "ℹ️ 説明"])

with tab1:
    st.subheader("📈 全選手レーティングランキング")
    
    # レーティングデータを取得
    rating_df = get_player_ratings()
    
    if not rating_df.empty:
        # ランキング表示用に順位を追加
        rating_df.insert(0, '順位', range(1, len(rating_df) + 1))
        
        # 表示用に整形
        display_df = rating_df[[
            '順位', 'player_name', 'rating', 'games', 'last_updated'
        ]].copy()
        
        display_df.columns = [
            '順位', '選手名', 'レート', '対局数', '最終更新'
        ]
        
        # フォーマット
        display_df['レート'] = display_df['レート'].apply(lambda x: f"{x:.1f}")
        display_df['対局数'] = display_df['対局数'].astype(int)
        
        # 指標表示
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 登録選手数", len(rating_df))
        with col2:
            st.metric("🏆 トップレート", f"{rating_df['rating'].max():.1f}pt")
        with col3:
            st.metric("📉 平均レート", f"{rating_df['rating'].mean():.1f}pt")
        with col4:
            st.metric("📈 総対局数", int(rating_df['games'].sum()))
        
        st.dataframe(display_df, hide_index=True)
        
        # グラフ表示
        st.markdown("---")
        st.subheader("📊 トップ10レーティング推移")
        
        top_10 = rating_df.nlargest(10, 'rating')
        
        fig = go.Figure()
        
        for idx, row in top_10.iterrows():
            history_df = get_player_rating_history(row['player_id'], limit=50)
            
            if not history_df.empty:
                history_df = history_df.sort_values('game_date')
                fig.add_trace(go.Scatter(
                    x=history_df['game_date'],
                    y=history_df['new_rating'],
                    mode='lines+markers',
                    name=row['player_name'],
                    line=dict(width=2)
                ))
        
        fig.update_layout(
            title="レーティング推移（上位10名）",
            xaxis_title="対局日",
            yaxis_title="レート",
            hovermode='x unified',
            height=500
        )
        
        st.plotly_chart(fig)
    else:
        st.info("📊 レーティングデータがまだ計算されていません。")
        st.info("データ管理ページで「レーティングを初期化して遡及計算」をクリックしてください。")

with tab2:
    st.subheader("📊 選手別レーティング詳細")
    
    rating_df = get_player_ratings()
    
    if not rating_df.empty:
        # 選手選択
        selected_player_id = st.selectbox(
            "選手を選択",
            options=rating_df['player_id'].tolist(),
            format_func=lambda x: f"{rating_df[rating_df['player_id'] == x]['player_name'].values[0]} ({rating_df[rating_df['player_id'] == x]['rating'].values[0]:.1f})"
        )
        
        # 選択した選手の情報
        player_info = rating_df[rating_df['player_id'] == selected_player_id].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("選手名", player_info['player_name'])
        with col2:
            st.metric("現在のレート", f"{player_info['rating']:.1f}pt")
        with col3:
            st.metric("対局数", int(player_info['games']))
        with col4:
            st.metric("最終更新", player_info['last_updated'])
        
        st.markdown("---")
        
        # レーティング履歴
        history_df = get_player_rating_history(selected_player_id, limit=100)
        
        if not history_df.empty:
            st.subheader("📈 レーティング履歴（直近100対局）")
            
            history_df = history_df.sort_values('game_date')
            
            # グラフ
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=history_df['game_date'],
                y=history_df['new_rating'],
                mode='lines+markers',
                name='新レート',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6)
            ))
            
            fig.update_layout(
                title=f"{player_info['player_name']} のレーティング推移",
                xaxis_title="対局日",
                yaxis_title="レート",
                hovermode='x',
                height=400
            )
            
            st.plotly_chart(fig)
            
            # テーブル表示
            st.markdown("---")
            st.subheader("📊 対局ごとのレート変動")
            
            display_history = history_df[[
                'game_date', 'old_rating', 'delta', 'new_rating'
            ]].copy()
            
            display_history.columns = ['対局日', '対局前', '変動Δ', '対局後']
            display_history = display_history.sort_values('対局日', ascending=False)
            display_history.insert(0, '順位', range(1, len(display_history) + 1))
            
            display_history['対局前'] = display_history['対局前'].apply(lambda x: f"{x:.1f}")
            display_history['変動Δ'] = display_history['変動Δ'].apply(lambda x: f"{x:+.1f}")
            display_history['対局後'] = display_history['対局後'].apply(lambda x: f"{x:.1f}")
            
            st.dataframe(display_history, hide_index=True)
        else:
            st.info("📊 この選手のレーティング履歴がまだありません。")
    else:
        st.info("📊 レーティングデータがまだ計算されていません。")

with tab3:
    st.subheader("ℹ️ Elo風レーティングについて")
    
    st.markdown("""
    ### システムの特徴
    
    **4人麻雀対応**
    - 各対局で4人の相対的な序列（1位 > 2位 > 3位 > 4位）を評価
    - 対戦相手のレート差から期待順位を計算
    - 実績順位との乖離でレート変動を決定
    
    **期待順位スコア（線形補間）**
    - 4人のレート差から、対象選手の期待順位スコアを計算
    - スコア範囲: -3.5（4位想定）〜 +4.5（1位想定）
    
    **レート計算式**
    ```
    ΔR = K × (実績スコア - 期待スコア)
    新レート = 現在のレート + ΔR
    ```
    
    ここで：
    - K = 8（緩やかなレート変動で収束を重視）
    - 実績スコア：1位 +4.5、2位 +0.5、3位 -1.5、4位 -3.5
    
    ### パラメータ
    
    | 項目 | 値 |
    |------|-----|
    | 初期レート | 1500pt |
    | K値 | 8 |
    | レート上限 | なし |
    | レート下限 | なし |
    
    ### レーティング更新のタイミング
    
    **自動更新**
    - 半荘記録入力時に自動的に計算
    - ゲーム保存と同時にレート更新
    
    **遡及計算**
    - データ管理ページで手動実行可能
    - 既存の全対局を時系列で再処理
    
    ### 活用方法
    
    - **選手の実力比較**: 絶対的な実力を数値化
    - **成長の追跡**: 時間経過による成長・衰退を可視化
    - **期待値との比較**: 実績との乖離から相性を分析
    """)
