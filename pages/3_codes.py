import streamlit as st
import pandas as pd
import lib
from login import *

lib.init_files()

if 'admin_authenticated' not in st.session_state:
    st.session_state['admin_authenticated'] = False

st.title('投票コード管理')

# 認証
login()

if st.session_state['admin_authenticated']:
    st.subheader('コード生成')
    n = st.number_input('生成数', min_value=1, max_value=1000, value=10)
    if st.button('コード生成'):
        new_df = lib.generate_codes(n)
        st.success(f'{len(new_df)} 個のコードを生成しました')
        codes_text = '\n'.join(new_df['code'].tolist())
        st.text_area('生成コード', value=codes_text, height=150)
        st.download_button('生成コードをダウンロード', data=codes_text, file_name='codes.txt', mime='text/plain')

    st.markdown('---')
    st.subheader('コード一覧')
    codes = lib.load_codes()
    st.dataframe(codes)

    # QR生成表示
    st.markdown('---')
    st.subheader('QR 表示')
    sample = st.text_input('QRにしたいコードを入力')
    if sample:
        img_bytes = lib.make_qr_image_bytes(sample)
        st.image(img_bytes)
        st.download_button('QRをダウンロード (PNG)', data=img_bytes, file_name=f'{sample}.png', mime='image/png')

    if st.button('ログアウト'):
        st.session_state['admin_authenticated'] = False
        st.success('ログアウトしました')