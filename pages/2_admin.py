import streamlit as st
import pandas as pd
import lib
from login import *

lib.init_files()

if 'admin_authenticated' not in st.session_state:
    st.session_state['admin_authenticated'] = False

st.title('管理者ダッシュボード')

# 認証
login()

if st.session_state['admin_authenticated']:
    st.subheader('集計結果')
    df = lib.load_votes()
    if len(df) == 0:
        st.write('まだ投票がありません')
    else:
        total_votes = len(df)
        result = df['candidate'].value_counts()
        percent = (result / total_votes * 100).round(1)
        result_df = pd.DataFrame({'votes': result, 'percent': percent.astype(str) + '%'})
        st.table(result_df)
        st.bar_chart(result)

    st.markdown('---')
    st.subheader('管理用操作')
    if st.button('生データ CSV ダウンロード'):
        csv = lib.load_votes().to_csv(index=False).encode('utf-8')
        st.download_button('ダウンロード', data=csv, file_name='votes.csv', mime='text/csv')

    if st.button('全投票リセット'):
        df = pd.DataFrame(columns=['method', 'voter_id', 'candidate', 'timestamp'])
        lib.save_votes(df)
        st.success('投票データをリセットしました')

    if st.checkbox('生データ表示'):
        st.dataframe(lib.load_votes())

    if st.button('ログアウト'):
        st.session_state['admin_authenticated'] = False
        st.success('ログアウトしました')