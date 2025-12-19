import streamlit as st
import pandas as pd
import lib

lib.init_files()

if 'admin_authenticated' not in st.session_state:
    st.session_state['admin_authenticated'] = False

st.title('有権者リスト管理')

# 認証
if not st.session_state['admin_authenticated']:
    pw = st.text_input('管理者パスワード', type='password')
    if st.button('ログイン'):
        if lib.verify_password(pw, lib.get_password_hash()):
            st.session_state['admin_authenticated'] = True
            st.success('認証成功')
        else:
            st.error('パスワードが違います')

if st.session_state['admin_authenticated']:
    st.subheader('CSVからの一括インポート')
    uploaded = st.file_uploader('学生ID一覧ファイル（1列に生ID）', type=['csv','txt'])
    if uploaded is not None:
        content = uploaded.read().decode('utf-8')
        raw_ids = [l for l in content.splitlines() if l.strip()]
        added = lib.import_eligible_from_list(raw_ids)
        st.success(f'{added} 件追加しました')

    st.markdown('---')
    st.subheader('手動追加')
    sid = st.text_input('学生ID (生のIDを入力)')
    note = st.text_input('メモ（任意）')
    if st.button('追加'):
        ok = lib.add_eligible_raw(sid, note)
        if ok:
            st.success('追加しました')
        else:
            st.warning('既に存在します')

    st.markdown('---')
    st.subheader('一覧・削除')
    df = lib.load_eligible_df()
    st.dataframe(df)
    sel = st.text_input('削除する student_id_hash を入力')
    if st.button('削除'):
        lib.remove_eligible_hash(sel)
        st.success('削除しました')

    # ダウンロード
    st.markdown('---')
    if st.button('一覧をCSVでダウンロード'):
        csv = lib.load_eligible_df().to_csv(index=False).encode('utf-8')
        st.download_button('ダウンロード', data=csv, file_name='eligible_ids.csv', mime='text/csv')

    if st.button('ログアウト'):
        st.session_state['admin_authenticated'] = False
        st.success('ログアウトしました')