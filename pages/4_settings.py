import streamlit as st
import lib
import datetime
from login import *

lib.init_files()

if 'admin_authenticated' not in st.session_state:
    st.session_state['admin_authenticated'] = False

st.title('設定')

# 認証
login()

if st.session_state['admin_authenticated']:
    st.subheader('投票期間設定')
    s = lib.get_settings()
    start_str = s.get('start')
    end_str = s.get('end')

    if start_str:
        start_dt = datetime.datetime.fromisoformat(start_str)
    else:
        start_dt = None
    if end_str:
        end_dt = datetime.datetime.fromisoformat(end_str)
    else:
        end_dt = None

    new_start = st.date_input('開始日', value=start_dt.date() if start_dt else datetime.date.today())
    new_start_time = st.time_input('開始時刻', value=start_dt.time() if start_dt else datetime.time(hour=0, minute=0))
    new_end = st.date_input('終了日', value=end_dt.date() if end_dt else datetime.date.today())
    new_end_time = st.time_input('終了時刻', value=end_dt.time() if end_dt else datetime.time(hour=23, minute=59))

    if st.button('投票期間を保存'):
        start_iso = datetime.datetime.combine(new_start, new_start_time).isoformat()
        end_iso = datetime.datetime.combine(new_end, new_end_time).isoformat()
        lib.save_settings({'start': start_iso, 'end': end_iso})
        st.success('投票期間を保存しました')

    st.markdown('---')
    st.subheader('管理者パスワードの変更')
    new_pw = st.text_input('新しいパスワード', type='password')
    new_pw2 = st.text_input('新しいパスワード (確認)', type='password')
    if st.button('パスワードを変更'):
        if not new_pw:
            st.error('パスワードを入力してください')
        elif new_pw != new_pw2:
            st.error('確認用パスワードが一致しません')
        else:
            lib.set_password(new_pw)
            st.success('パスワードを更新しました')

    if st.button('ログアウト'):
        st.session_state['admin_authenticated'] = False
        st.success('ログアウトしました')