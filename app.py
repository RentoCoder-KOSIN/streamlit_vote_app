import streamlit as st
import pandas as pd
import hashlib
import os
import datetime
import secrets

# shared helper
import lib

# 初期化
lib.init_files()

DATA_FILE = 'votes.csv'

# 初期CSVにタイムスタンプ列を追加
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=['method', 'voter_id', 'candidate', 'timestamp'])
    df.to_csv(DATA_FILE, index=False)

st.title("生徒会選挙　投票システム　(仮)")

# モード選択：投票 or 管理者
mode = st.radio("モードを選択", ["投票", "管理者"]) 

# セッション初期化（管理者認証保持用）
if 'admin_authenticated' not in st.session_state:
    st.session_state['admin_authenticated'] = False

# --- 投票画面 ---
if mode == "投票":
    if not lib.voting_open():
        st.error("現在は投票期間外です。管理者にお問い合わせください。")
    else:
        candidate = st.selectbox("候補者を選択", ["候補A", "候補B", "候補C"])
        method = st.radio("投票方法を選択", ["投票コード方式", "IDハッシュ方式"]) 

        if method == "投票コード方式":
            code = st.text_input("投票コードを入力")
            voter_id = code
        else:
            student_id = st.text_input("学生ID(test)")
            if student_id:
                # 事前登録済みかチェック
                if lib.is_eligible(student_id):
                    voter_id = hashlib.sha256(student_id.encode()).hexdigest()
                else:
                    voter_id = ""
                    st.error("この学生IDは投票権がありません。管理者にお問い合わせください。")
            else:
                voter_id = ""

        if st.button("投票"):
            if not voter_id:
                st.error("有効なIDまたはコードを入力してください")
            else:
                df = lib.load_votes()
                # 互換性: もし timestamp カラムが無ければ追加
                if 'timestamp' not in df.columns:
                    df['timestamp'] = ""

                if voter_id in df["voter_id"].values:
                    st.error("すでに投票済み")
                else:
                    # 投票コード方式ならコード検証と使用済みマーキング
                    if method == "投票コード方式":
                        ok, msg = lib.verify_code(voter_id)
                        if not ok:
                            st.error(msg)
                        else:
                            timestamp = datetime.datetime.now().isoformat()
                            new_vote = pd.DataFrame([[method, voter_id, candidate, timestamp]], columns=["method", "voter_id", "candidate", "timestamp"])
                            df = pd.concat([df, new_vote], ignore_index=True)
                            lib.save_votes(df)
                            lib.mark_code_used(voter_id, voter_id)
                            st.success("投票完了（コードを使用しました）")
                            st.write(f"あなたの投票時刻: {timestamp}")
                    else:
                        timestamp = datetime.datetime.now().isoformat()
                        new_vote = pd.DataFrame([[method, voter_id, candidate, timestamp]], columns=["method", "voter_id", "candidate", "timestamp"])
                        df = pd.concat([df, new_vote], ignore_index=True)
                        lib.save_votes(df)
                        st.success("投票完了")
                        st.write(f"あなたの投票時刻: {timestamp}")

# --- 管理者画面（パスワード保護 + セッション） ---
else:
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

    if not ADMIN_PASSWORD:
        st.error("管理者パスワードが設定されていません")
        st.stop()

    if not st.session_state['admin_authenticated']:
        admin_password = st.text_input("管理者パスワードを入力", type="password")
        if st.button("認証"):
            if admin_password == ADMIN_PASSWORD and admin_password != "":
                st.session_state['admin_authenticated'] = True
                st.success("認証成功")
            else:
                st.error("パスワードが違います")

    if st.session_state['admin_authenticated']:
        st.divider()
        st.header("集計結果（管理者用）")
        df = pd.read_csv(DATA_FILE)
        if 'timestamp' not in df.columns:
            df['timestamp'] = ""

        if len(df) == 0:
            st.write("まだ投票がありません")
        else:
            total_votes = len(df)
            result = df["candidate"].value_counts()
            percent = (result / total_votes * 100).round(1)
            result_df = pd.DataFrame({"votes": result, "percent": percent.astype(str) + "%"})

            st.subheader("票数（候補別）")
            st.table(result_df)
            st.bar_chart(result)

            # CSVダウンロード
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("生データをCSVでダウンロード", data=csv, file_name="votes.csv", mime="text/csv")

            # 表示・リセット
            if st.checkbox("生データを表示 (管理者のみ)"):
                st.dataframe(df)

            if st.button("全ての投票をリセット"):
                df = pd.DataFrame(columns=['method', 'voter_id', 'candidate', 'timestamp'])
                df.to_csv(DATA_FILE, index=False)
                st.success("投票データをリセットしました")

            # 投票コード生成
            st.markdown("---")
            st.subheader("投票コードを生成 (管理者)")
            code_count = st.number_input("生成するコード数", min_value=1, max_value=1000, value=10)
            if st.button("コードを生成"):
                codes = [secrets.token_urlsafe(6) for _ in range(code_count)]
                codes_text = "\n".join(codes)
                st.text_area("生成コード", value=codes_text, height=150)
                st.download_button("生成コードをダウンロード (txt)", data=codes_text, file_name="codes.txt", mime="text/plain")

            # ログアウト
            if st.button("管理者ログアウト"):
                st.session_state['admin_authenticated'] = False
                st.success("ログアウトしました")
    else:
        st.warning("管理者認証が必要です（パスワードを入力してください）")