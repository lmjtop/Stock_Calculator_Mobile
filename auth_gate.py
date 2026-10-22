"""Password gate for the private Stock Calculator Streamlit app.

Secrets required:
AUTH_PASSWORD_HASH = "<bcrypt hash>"
AUTH_COOKIE_KEY = "<long random signing key>"

Keep both secrets in Streamlit Cloud Secrets, never in GitHub.
"""
import streamlit as st
import streamlit_authenticator as stauth


def require_login():
    try:
        password_hash = st.secrets["AUTH_PASSWORD_HASH"]
        cookie_key = st.secrets["AUTH_COOKIE_KEY"]
        if not isinstance(password_hash, str) or not password_hash.startswith("$2"):
            raise ValueError("Invalid bcrypt password hash")
        if not isinstance(cookie_key, str) or len(cookie_key) < 32:
            raise ValueError("Cookie signing key must be at least 32 characters")
    except (KeyError, ValueError, TypeError):
        st.error("로그인 설정이 없습니다. Streamlit Secrets에 AUTH_PASSWORD_HASH 및 AUTH_COOKIE_KEY를 설정해 주세요.")
        st.stop()

    credentials = {
        "usernames": {
            "owner": {
                "name": "Owner",
                "password": password_hash,
            }
        }
    }
    authenticator = stauth.Authenticate(
        credentials=credentials,
        cookie_name="stock_calculator_login",
        cookie_key=cookie_key,
        cookie_expiry_days=30,
        auto_hash=False,
    )

    authenticator.login(location="main", fields={
        "Form name": "Stock Calculator 로그인",
        "Username": "사용자 이름",
        "Password": "비밀번호",
        "Login": "로그인",
    })

    if st.session_state.get("authentication_status") is not True:
        if st.session_state.get("authentication_status") is False:
            st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
        else:
            st.info("사용자 이름은 owner입니다. 비밀번호를 입력해 주세요.")
        st.stop()

    with st.sidebar:
        authenticator.logout(button_name="로그아웃", location="sidebar")
