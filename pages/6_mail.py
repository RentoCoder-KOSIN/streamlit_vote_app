import streamlit as st
import pandas as pd
import lib
from login import *
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_mail(to_addr, subject, body):
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587

    FROM_ADDR = os.environ.get("MAIL_ADDRESS")
    PASSWORD = os.environ.get("MAIL_PASSWORD")

    msg = MIMEMultipart()
    msg['From'] = FROM_ADDR
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(FROM_ADDR, PASSWORD)
        server.send_message(msg)

lib.init_files()

if 'admin_authenticated' not in st.session_state:
    st.session_state['admin_authenticated'] = False

st.title("メール送信管理")

login()

if st.session_state['admin_authenticated']:
    st.subheader('メール送信テスト')

    with st.form("mail_form"):
        to_addr = st.text_input('宛先メールアドレス')
        subject = st.text_input('件名')
        body = st.text_area('本文', height=200)
        submit = st.form_submit_button('送信')

    if submit:
        try:
            send_mail(to_addr, subject, body)
            st.success('メールを送信しました')
        except Exception as e:
            st.error(f"送信に失敗しました:{e}")
