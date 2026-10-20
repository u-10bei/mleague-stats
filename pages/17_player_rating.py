import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db import (FORM_GAMES, RATING_K, get_connection, get_player_form, get_player_rating_history,
                get_player_ratings, show_sidebar_navigation)
from ui import fit_chart, metric_row

sys.path.append("..")

st.set_page_config(
    page_title="レーティング | Mリーグダッシュボード",
    page_icon="🀄",
    layout="wide"
)

# サイドバーナビゲーション
show_sidebar_navigation()

st.title("📊 選手レーティング")

st.markdown(f"""
4人麻雀用のElo風レーティングシステムです。
対局結果に基づいて、選手の相対的な実力をレーティングで可視化します。
**レート**は通算の積み重ねを映す実力の目安、**調子**は直近 {FORM_GAMES} 戦の上振れ・下振れです。

**システム仕様**
- 初期レート: 1500pt
- K値: {RATING_K}
- 着順スコア: 1位 +4.5、2位 +0.5、3位 -1.5、4位 -3.5（合計 0）
- 期待値: Plackett-Luce（Elo の多人数拡張）で着順の確率分布を求め、
  着順スコアの期待値を取る。ΔR = K ×（実際の着順スコア − 期待値）
- 調子: 直近 {FORM_GAMES} 戦の（実際の着順スコア − 期待値）の平均。対戦相手の強さを加味した上振れ・下振れ
""")


def form_label(v):
    """調子の値に、向きがひと目でわかる記号を添える。"""
    if pd.isna(v):
        return "—"
    mark = "↑" if v >= 0.5 else "↓" if v <= -0.5 else "→"
    return f"{mark} {v:+.2f}"


form_df = get_player_form()

# タブ構成
tab1, tab2, tab3 = st.tabs(["📈 レーティングランキング", "📊 個別詳細", "ℹ️ 説明"])

with tab1:
    st.subheader("📈 全選手レーティングランキング")
    
    # レーティングデータを取得
    rating_df = get_player_ratings()
    
    if not rating_df.empty:
        # ランキング表示用に順位を追加
        rating_df.insert(0, '順位', range(1, len(rating_df) + 1))
        rating_df = rating_df.merge(form_df, on='player_id', how='left')
        
        # 表示用に整形
        display_df = rating_df[[
            '順位', 'player_name', 'rating', 'form', 'games', 'last_updated'
        ]].copy()
        
        display_df.columns = [
            '順位', '選手名', 'レート', f'調子（直近{FORM_GAMES}戦）', '対局数', '最終対局日'
        ]
        
        # フォーマット
        display_df['レート'] = display_df['レート'].apply(lambda x: f"{x:.1f}")
        display_df[f'調子（直近{FORM_GAMES}戦）'] = display_df[f'調子（直近{FORM_GAMES}戦）'].apply(form_label)
        display_df['対局数'] = display_df['対局数'].astype(int)
        
        # 指標表示
        col1, col2, col3, col4 = metric_row(4)
        with col1:
            st.metric("📊 登録選手数", len(rating_df))
        with col2:
            st.metric("🏆 トップレート", f"{rating_df['rating'].max():.1f}pt")
        with col3:
            st.metric("📉 平均レート", f"{rating_df['rating'].mean():.1f}pt")
        with col4:
            st.metric("📈 総対局数", int(rating_df['games'].sum()))
        
        st.dataframe(display_df, hide_index=True)
        st.caption(
            f"調子は直近 {FORM_GAMES} 戦で、レートから期待される着順スコアをどれだけ上回ったか（1 戦あたり）。"
            "↑ は +0.5 以上、↓ は −0.5 以下。最近の結果を表すもので、次の対局の予想には使えません。")
        
        # グラフ表示
        st.markdown("---")
        st.subheader("📊 トップ10レーティング推移")
        
        top_10 = rating_df.nlargest(10, 'rating')
        
        # 全選手の履歴を先に取得して、ユニークな対局キーに連番インデックスを振る
        histories = {}
        all_game_keys = set()
        for idx, row in top_10.iterrows():
            h = get_player_rating_history(row['player_id'], limit=50)
            if not h.empty:
                h = h.sort_values(['game_date', 'game_number'])
                histories[row['player_id']] = h
                for _, r in h.iterrows():
                    gn = int(r['game_number']) if pd.notna(r['game_number']) else 1
                    all_game_keys.add((str(r['game_date']), gn))

        sorted_keys = sorted(all_game_keys)
        key_to_idx = {k: i for i, k in enumerate(sorted_keys)}

        fig = go.Figure()

        for idx, row in top_10.iterrows():
            if row['player_id'] not in histories:
                continue
            h = histories[row['player_id']]
            x_indices = []
            x_labels = []
            for _, r in h.iterrows():
                gn = int(r['game_number']) if pd.notna(r['game_number']) else 1
                key = (str(r['game_date']), gn)
                x_indices.append(key_to_idx[key])
                x_labels.append(f"{r['game_date']} 第{gn}局")
            fig.add_trace(go.Scatter(
                x=x_indices,
                y=h['new_rating'],
                mode='lines+markers',
                name=row['player_name'],
                line=dict(width=2),
                text=x_labels,
                hovertemplate='%{text}<br>レート: %{y:.1f}<extra></extra>'
            ))

        # X軸のtickvals/ticktext設定（間引きあり）
        if sorted_keys:
            total = len(sorted_keys)
            interval = max(1, total // 12)
            tickvals = list(range(total))
            ticktext = [
                f"{k[0]} 第{k[1]}局" if i % interval == 0 else ''
                for i, k in enumerate(sorted_keys)
            ]
            fig.update_xaxes(tickvals=tickvals, ticktext=ticktext)
        
        fig.update_layout(
            title="レーティング推移（上位10名）",
            xaxis_title="対局日",
            yaxis_title="レート",
            hovermode='x unified',
            height=500
        )
        
        fit_chart(fig)
        st.plotly_chart(fig, width='stretch')
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
        form_row = form_df[form_df['player_id'] == selected_player_id]
        form_value = form_row['form'].iloc[0] if len(form_row) else float('nan')
        form_games = int(form_row['form_games'].iloc[0]) if len(form_row) else 0
        
        col1, col2, col3, col4 = metric_row(4)
        with col1:
            st.metric("選手名", player_info['player_name'])
        with col2:
            st.metric("現在のレート", f"{player_info['rating']:.1f}pt")
        with col3:
            st.metric(f"調子（直近{form_games}戦）", form_label(form_value),
                      help="レートから期待される着順スコアを、1 戦あたりどれだけ上回ったか。"
                           "最近の結果を表すもので、次の対局の予想には使えません。")
        with col4:
            st.metric("対局数", int(player_info['games']))
        
        st.markdown("---")
        
        # レーティング履歴
        history_df = get_player_rating_history(selected_player_id, limit=100)
        
        if not history_df.empty:
            st.subheader("📈 レーティング履歴（直近100対局）")

            history_df = history_df.sort_values(['game_date', 'game_number'])

            # 均等間隔X軸用に連番インデックスを生成
            x_indices = list(range(len(history_df)))
            x_labels = [
                f"{r['game_date']} 第{int(r['game_number'])}局"
                if pd.notna(r['game_number']) else str(r['game_date'])
                for _, r in history_df.iterrows()
            ]

            # X軸ラベル（間引きあり）
            total = len(x_indices)
            interval = max(1, total // 12)
            tab2_ticktext = [
                x_labels[i] if i % interval == 0 else ''
                for i in range(total)
            ]

            # グラフ
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=x_indices,
                y=history_df['new_rating'],
                mode='lines+markers',
                name='新レート',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6),
                text=x_labels,
                hovertemplate='%{text}<br>レート: %{y:.1f}<extra></extra>'
            ))

            fig.update_xaxes(tickvals=x_indices, ticktext=tab2_ticktext)

            fig.update_layout(
                title=f"{player_info['player_name']} のレーティング推移",
                xaxis_title="対局（試合順）",
                yaxis_title="レート",
                hovermode='x',
                height=400
            )
            
            fit_chart(fig)
            st.plotly_chart(fig, width='stretch')
            
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
    st.subheader("ℹ️ レーティングについて")
    
    st.markdown("""
    ### システムの特徴
    
    **4人麻雀対応**
    - 各対局で4人の相対的な序列（1位 > 2位 > 3位 > 4位）を評価
    - 4人のレートから、各選手の着順スコアの期待値を計算
    - 実際の着順スコアと期待値の差でレート変動を決定
    
    **期待値の求め方（Plackett-Luce）**
    - Elo を多人数に拡張したモデルで、各選手が 1〜4 位になる確率を求める
    - 強さは 10^(レート/400)。1 位から順に、残っている選手の強さに比例して選ばれるとみなす
    - 4 人なら 24 通りの着順を数え上げて確率を厳密に出し、着順スコアの期待値を取る
    - 期待値の範囲: -3.5（4位想定）〜 +4.5（1位想定）。全員同レートなら 0
    
    **レート計算式**
    ```
    ΔR = K × (実際の着順スコア - 期待値)
    新レート = 現在のレート + ΔR
    ```
    
    ここで：
    - K = 2（1 戦ごとの運に振られにくく、通算の積み重ねが効く大きさ）
    - 着順スコア：1位 +4.5、2位 +0.5、3位 -1.5、4位 -3.5（合計 0）
    - 同着は該当する着順のスコアを平均する（1224 方式）
    - 4 人の ΔR の合計は常に 0（ゼロサム）
    
    ### パラメータ
    
    | 項目 | 値 |
    |------|-----|
    | 初期レート | 1500pt |
    | K値 | 2 |
    | レート上限 | なし |
    | レート下限 | なし |
    | 調子を測る対局数 | 直近 30 戦 |

    ### K を 2 にしている理由

    2020 年以降の全対局で、対局前のレートから着順を予測させ、K の大きさを比べました。

    - **K=1〜2 がいちばんよく当たりました。** K=8 では「全員同じ強さ」とみなすより外れました。
      M リーグは選手間の実力差が運に比べて小さく、K が大きいと直近の運を実力として拾ってしまいます
    - 100 戦以上の選手で比べると、K=8 のレートは直近 30 戦の成績と強く連動していました（相関 0.74、
      通算の成績とは 0.50）。K=2 では通算の成績との相関が 0.72、直近 30 戦とは 0.51 で、
      通算を中心に調子も少し映る形になります

    ### 調子について

    直近 30 戦の「実際の着順スコア − 期待値」の平均です。対戦相手の強さを加味した上振れ・下振れで、
    +1.0 なら 1 戦あたり着順スコア 1 点ぶん、レートからの期待を上回っています。

    調子をレートに足すと、どの重みでも着順の予測は悪くなりました。直近の勢いには次の対局を当てる力が
    見つからなかったので、レートには混ぜず、**最近の結果**として別に表示しています。
    
    ### レーティング更新のタイミング
    
    - 毎朝の konoui DB 同期で対局が増えたとき、全対局を時系列で最初から計算し直す
    - 手元で計算し直す場合は `python recalculate_ratings.py` を実行する
    - 同じ対局データからは常に同じ結果になる
    
    ### 活用方法
    
    - **選手の実力比較**: 対戦相手の強さを加味した相対的な実力を数値化
    - **成長の追跡**: 時間経過による成長・衰退を可視化
    - **期待値との比較**: 調子と対局ごとのレート変動から、レート以上・以下の結果が続いているかを把握
    """)
