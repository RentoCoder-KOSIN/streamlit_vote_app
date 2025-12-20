import streamlit as st
import pandas as pd
import lib
from login import *

lib.init_files()

if 'admin_authenticated' not in st.session_state:
    st.session_state['admin_authenticated'] = False

st.title("メール送信管理")

login()
