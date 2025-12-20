import streamlit as st
import pandas as pd
import lib

def login():

    if not st.session_state['admin_authenticated']:
        pw = st.text_input('管理者パスワード', type='password')
        if st.button('ログイン'):
            if lib.verify_password(pw, lib.get_password_hash()):
                st.session_state['admin_authenticated'] = True
                st.success('認証成功')
            else:
                st.error('パスワードが違います')