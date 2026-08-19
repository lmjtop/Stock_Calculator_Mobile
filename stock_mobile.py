import streamlit as st
import requests
import json
import os

from streamlit_local_storage import LocalStorage


# ============================================================
# 기본 설정
# ============================================================

QUICK_STOCKS = 5
ACCOUNT_STOCKS = 4
CASH_SLOT_NO = 5

ACCOUNTS = [
    "퇴직연금DC형",
    "IRP",
    "ISA",
    "연금저축"
]

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

# 서버 임시 백업용
SAVE_FILE = os.path.join(
    BASE_DIR,
    "portfolio_mobile.json"
)

# 아이폰 Safari LocalStorage 저장 KEY
LOCAL_STORAGE_KEY = (
    "stock_calculator_portfolio_v1"
)


# ============================================================
# Streamlit 화면 설정
# ============================================================

st.set_page_config(
    page_title="Stock Calculator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# LocalStorage
# ============================================================

local_storage = LocalStorage()


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    h1 {
        margin-bottom: 0.1rem;
    }

    .stock-name {
        font-size: 15px;
        font-weight: 700;
    }

    .stock-price {
        font-size: 16px;
        font-weight: 700;
        text-align: right;
    }

    .summary-title {
        font-size: 13px;
        color: #666666;
    }

    .summary-value {
        font-size: 20px;
        font-weight: 800;
    }

    .profit-positive {
        color: red;
        font-size: 21px;
        font-weight: 800;
    }

    .profit-negative {
        color: blue;
        font-size: 21px;
        font-weight: 800;
    }

    .profit-zero {
        color: black;
        font-size: 21px;
        font-weight: 800;
    }

    div[data-testid="stTextInput"] {
        margin-bottom: -0.35rem;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        margin-bottom: 0.35rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 네이버 요청 Header
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Referer": "https://m.stock.naver.com/"
}


# ============================================================
# 숫자 변환
# ============================================================

def to_number(value):

    try:

        if value is None:
            return 0.0

        text = (
            str(value)
            .replace(",", "")
            .replace("원", "")
            .replace("$", "")
            .strip()
        )

        if text == "":
            return 0.0

        return float(text)

    except:
        return 0.0


# ============================================================
# 숫자 표시
# ============================================================

def format_number(value):

    if value is None:
        return ""

    try:

        value = float(value)

        if value.is_integer():
            return f"{int(value):,}"

        return f"{value:,.2f}"

    except:
        return "0"


# ============================================================
# 손익 표시
# ============================================================

def format_profit(value):

    if value > 0:
        return f"+{format_number(value)}"

    if value < 0:
        return format_number(value)

    return "0"


# ============================================================
# 수익률 표시
# ============================================================

def format_rate(value):

    if value > 0:
        return f"+{value:.2f}%"

    if value < 0:
        return f"{value:.2f}%"

    return "0.00%"


# ============================================================
# JSON 요청
# ============================================================

def request_json(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=5
        )

        response.raise_for_status()

        return response.json()

    except:
        return None


# ============================================================
# 국내주식 조회
# ============================================================

def get_domestic_stock(stock_code):

    url = (
        f"https://m.stock.naver.com/"
        f"api/stock/{stock_code}/basic"
    )

    data = request_json(url)

    if not data:
        return None

    stock_name = data.get(
        "stockName"
    )

    close_price = data.get(
        "closePrice"
    )

    if (
        not stock_name
        or close_price is None
    ):
        return None

    price = to_number(
        close_price
    )

    return {
        "code": stock_code,
        "name": stock_name,
        "price": price
    }


# ============================================================
# 미국주식 조회
# ============================================================

def get_overseas_stock(ticker):

    ticker = (
        ticker
        .strip()
        .upper()
    )

    reuters_codes = [
        f"{ticker}.O",
        f"{ticker}.N",
        f"{ticker}.A"
    ]

    for reuters_code in reuters_codes:

        url = (
            "https://api.stock.naver.com/"
            f"stock/{reuters_code}/basic"
        )

        data = request_json(
            url
        )

        if not data:
            continue

        stock_name = (
            data.get("stockName")
            or data.get("name")
            or data.get("stockNameEng")
        )

        price_value = (
            data.get("closePrice")
            or data.get("regularMarketPrice")
            or data.get("currentPrice")
        )

        if (
            not stock_name
            or price_value is None
        ):
            continue

        price = to_number(
            price_value
        )

        return {
            "code": ticker,
            "name": stock_name,
            "price": price
        }

    return None


# ============================================================
# 국내 / 해외 통합 조회
# ============================================================

def get_stock_price(stock_code):

    code = (
        stock_code
        .strip()
        .upper()
    )

    if code == "":
        return None

    # 국내주식
    if len(code) == 6:

        result = get_domestic_stock(
            code
        )

        if result:
            return result

    # 영문 포함 : 미국주식
    if any(
        c.isalpha()
        for c in code
    ):

        result = get_overseas_stock(
            code
        )

        if result:
            return result

    return get_domestic_stock(
        code
    )


# ============================================================
# 초기 데이터
# ============================================================

def make_default_data():

    return {

        "quick_stocks": [

            {
                "code": "",
                "name": "",
                "price": 0,
                "selected": False
            }

            for _ in range(
                QUICK_STOCKS
            )
        ],

        "accounts": {

            account: [

                {
                    "code": "",
                    "name": "",
                    "buy_price": "",
                    "quantity": "",
                    "current_price": 0
                }

                for _ in range(
                    ACCOUNT_STOCKS
                )
            ]

            for account in ACCOUNTS
        },

        "cash_balances": {

            account: ""

            for account in ACCOUNTS
        }
    }


# ============================================================
# 저장 데이터 구조 보정
# ============================================================

def normalize_data(data):

    default = make_default_data()

    if not isinstance(
        data,
        dict
    ):

        return default


    # --------------------------------------------------------
    # 관심종목
    # --------------------------------------------------------

    quick = data.get(
        "quick_stocks",
        []
    )

    if not isinstance(
        quick,
        list
    ):

        quick = []

    while len(quick) < QUICK_STOCKS:

        quick.append(
            {
                "code": "",
                "name": "",
                "price": 0,
                "selected": False
            }
        )

    default[
        "quick_stocks"
    ] = quick[
        :QUICK_STOCKS
    ]


    # --------------------------------------------------------
    # 계좌
    # --------------------------------------------------------

    saved_accounts = data.get(
        "accounts",
        {}
    )

    if not isinstance(
        saved_accounts,
        dict
    ):

        saved_accounts = {}

    for account in ACCOUNTS:

        rows = saved_accounts.get(
            account,
            []
        )

        if not isinstance(
            rows,
            list
        ):

            rows = []

        while len(rows) < ACCOUNT_STOCKS:

            rows.append(
                {
                    "code": "",
                    "name": "",
                    "buy_price": "",
                    "quantity": "",
                    "current_price": 0
                }
            )

        default[
            "accounts"
        ][account] = rows[
            :ACCOUNT_STOCKS
        ]


    # --------------------------------------------------------
    # 현금잔고
    # --------------------------------------------------------

    saved_cash = data.get(
        "cash_balances",
        {}
    )

    if not isinstance(
        saved_cash,
        dict
    ):

        saved_cash = {}

    for account in ACCOUNTS:

        default[
            "cash_balances"
        ][account] = str(
            saved_cash.get(
                account,
                ""
            )
        )

    return default


# ============================================================
# 서버 JSON 불러오기
# ============================================================

def load_server_data():

    if not os.path.exists(
        SAVE_FILE
    ):

        return make_default_data()

    try:

        with open(
            SAVE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        return normalize_data(
            data
        )

    except:

        return make_default_data()


# ============================================================
# 서버 JSON 저장
# ============================================================

def save_server_data():

    try:

        with open(
            SAVE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                st.session_state.portfolio,
                file,
                ensure_ascii=False,
                indent=4
            )

    except:
        pass


# ============================================================
# 저장 요청 표시
#
# 브라우저 LocalStorage는 바로 쓰지 않고
# 화면 마지막에서 딱 한 번만 저장
# ============================================================

def request_save():

    save_server_data()

    st.session_state[
        "browser_save_needed"
    ] = True


# ============================================================
# Session 기본값
# ============================================================

if "portfolio" not in st.session_state:

    st.session_state.portfolio = (
        load_server_data()
    )


if (
    "browser_save_needed"
    not in st.session_state
):

    st.session_state[
        "browser_save_needed"
    ] = False


if (
    "browser_loaded"
    not in st.session_state
):

    st.session_state[
        "browser_loaded"
    ] = False


if (
    "browser_read_count"
    not in st.session_state
):

    st.session_state[
        "browser_read_count"
    ] = 0


if (
    "last_saved_text"
    not in st.session_state
):

    st.session_state[
        "last_saved_text"
    ] = ""


# ============================================================
# Safari LocalStorage 읽기
#
# 중요:
# getItem은 이 한 곳에서만 실행
# ============================================================

browser_data = local_storage.getItem(
    LOCAL_STORAGE_KEY,
    key="portfolio_browser_load"
)


# ============================================================
# LocalStorage 최초 복원
# ============================================================

if not st.session_state[
    "browser_loaded"
]:

    st.session_state[
        "browser_read_count"
    ] += 1

    # --------------------------------------------------------
    # Safari에 기존 저장값이 있는 경우
    # --------------------------------------------------------

    if browser_data:

        try:

            if isinstance(
                browser_data,
                str
            ):

                loaded_data = json.loads(
                    browser_data
                )

            else:

                loaded_data = (
                    browser_data
                )

            st.session_state.portfolio = (
                normalize_data(
                    loaded_data
                )
            )

            st.session_state[
                "browser_loaded"
            ] = True

            current_text = json.dumps(
                st.session_state.portfolio,
                ensure_ascii=False,
                sort_keys=True
            )

            st.session_state[
                "last_saved_text"
            ] = current_text

            save_server_data()

        except:

            st.session_state[
                "browser_loaded"
            ] = True


    # --------------------------------------------------------
    # 두 번째 실행까지 값이 없으면
    # 새 브라우저로 판단
    # --------------------------------------------------------

    elif (
        st.session_state[
            "browser_read_count"
        ] >= 2
    ):

        st.session_state[
            "browser_loaded"
        ] = True

        current_text = json.dumps(
            st.session_state.portfolio,
            ensure_ascii=False,
            sort_keys=True
        )

        st.session_state[
            "last_saved_text"
        ] = current_text


# ============================================================
# 관심종목 조회
# ============================================================

def refresh_quick_stocks():

    success = 0
    failed_codes = []

    for i in range(
        QUICK_STOCKS
    ):

        widget_key = (
            f"quick_code_{i}"
        )

        if widget_key in st.session_state:

            code = (
                str(
                    st.session_state[
                        widget_key
                    ]
                )
                .strip()
                .upper()
            )

        else:

            code = (
                st.session_state
                .portfolio[
                    "quick_stocks"
                ][i]
                .get(
                    "code",
                    ""
                )
                .strip()
                .upper()
            )

        if not code:
            continue

        st.session_state.portfolio[
            "quick_stocks"
        ][i]["code"] = code

        result = get_stock_price(
            code
        )

        if result:

            st.session_state.portfolio[
                "quick_stocks"
            ][i]["name"] = (
                result["name"]
            )

            st.session_state.portfolio[
                "quick_stocks"
            ][i]["price"] = (
                result["price"]
            )

            success += 1

        else:

            failed_codes.append(
                code
            )

    request_save()

    return (
        success,
        failed_codes
    )


# ============================================================
# 계좌 현재가 조회
# ============================================================

def refresh_account(account):

    success = 0

    rows = (
        st.session_state
        .portfolio[
            "accounts"
        ][account]
    )

    for row in rows:

        code = (
            row.get(
                "code",
                ""
            )
            .strip()
            .upper()
        )

        if not code:
            continue

        result = get_stock_price(
            code
        )

        if result:

            row["name"] = (
                result["name"]
            )

            row[
                "current_price"
            ] = result[
                "price"
            ]

            success += 1

    request_save()

    return success


# ============================================================
# 전체 현재가 조회
# ============================================================

def refresh_all():

    total_success = 0
    failed_codes = []

    quick_success, quick_failed = (
        refresh_quick_stocks()
    )

    total_success += (
        quick_success
    )

    failed_codes.extend(
        quick_failed
    )

    for account in ACCOUNTS:

        account_success = (
            refresh_account(
                account
            )
        )

        total_success += (
            account_success
        )

    request_save()

    return (
        total_success,
        failed_codes
    )


# ============================================================
# 선택 종목 계좌 추가
# ============================================================

def add_selected_to_account(
    account
):

    quick_stocks = (
        st.session_state
        .portfolio[
            "quick_stocks"
        ]
    )

    account_rows = (
        st.session_state
        .portfolio[
            "accounts"
        ][account]
    )

    selected = [

        stock

        for stock
        in quick_stocks

        if stock.get(
            "selected",
            False
        )
    ]

    if not selected:

        st.warning(
            "왼쪽 관심종목에서 "
            "추가할 종목을 선택해 주세요."
        )

        return


    for stock in selected:

        code = stock.get(
            "code",
            ""
        )

        if not code:
            continue


        # ----------------------------------------------------
        # 중복 체크
        # ----------------------------------------------------

        exists = any(

            row.get(
                "code",
                ""
            ) == code

            for row
            in account_rows
        )

        if exists:
            continue


        # ----------------------------------------------------
        # 빈 행 검색
        # ----------------------------------------------------

        empty_index = None

        for i, row in enumerate(
            account_rows
        ):

            if not row.get(
                "code"
            ):

                empty_index = i
                break


        if empty_index is None:

            st.warning(
                f"{account}은 종목을 최대 "
                f"{ACCOUNT_STOCKS}개까지 "
                f"넣을 수 있습니다. "
                f"{CASH_SLOT_NO}번째 칸은 "
                f"현금잔고 전용입니다."
            )

            break


        account_rows[
            empty_index
        ] = {

            "code":
                code,

            "name":
                stock.get(
                    "name",
                    ""
                ),

            "buy_price":
                "",

            "quantity":
                "",

            "current_price":
                stock.get(
                    "price",
                    0
                )
        }


    # --------------------------------------------------------
    # 체크 해제
    # --------------------------------------------------------

    for stock in quick_stocks:

        stock[
            "selected"
        ] = False


    request_save()


# ============================================================
# 계좌 종목 삭제
# ============================================================

def delete_account_stock(
    account,
    index
):

    st.session_state.portfolio[
        "accounts"
    ][account][index] = {

        "code": "",
        "name": "",
        "buy_price": "",
        "quantity": "",
        "current_price": 0
    }

    request_save()


# ============================================================
# 전체 데이터 초기화
# ============================================================

def reset_all_data():

    st.session_state.portfolio = (
        make_default_data()
    )

    # --------------------------------------------------------
    # 입력 위젯 값 삭제
    # --------------------------------------------------------

    remove_keys = []

    for key in list(
        st.session_state.keys()
    ):

        if (
            key.startswith(
                "quick_code_"
            )
            or key.startswith(
                "select_"
            )
            or key.startswith(
                "buy_"
            )
            or key.startswith(
                "qty_"
            )
            or key.startswith(
                "cash_"
            )
        ):

            remove_keys.append(
                key
            )

    for key in remove_keys:

        try:

            del st.session_state[
                key
            ]

        except:
            pass


    request_save()


# ============================================================
# 제목
# ============================================================

st.title(
    "📊 Stock Calculator"
)

st.caption(
    "현재가격은 네이버 시세 조회값을 사용합니다."
)


# ============================================================
# 전체 현재가 조회
# ============================================================

if st.button(
    "🔄 전체 현재가 조회",
    use_container_width=True,
    type="primary"
):

    with st.spinner(
        "현재가를 조회하고 있습니다..."
    ):

        success, failed_codes = (
            refresh_all()
        )

    if success > 0:

        st.success(
            f"{success}개 종목의 "
            "현재가를 갱신했습니다."
        )

    if failed_codes:

        st.warning(
            "조회 실패 종목: "
            + ", ".join(
                failed_codes
            )
        )

    if (
        success == 0
        and not failed_codes
    ):

        st.warning(
            "조회할 종목이 없습니다."
        )


# ============================================================
# PC 좌우 배치
# ============================================================

left_col, right_col = st.columns(
    [1.05, 2.4],
    gap="large"
)


# ============================================================
# 왼쪽 관심종목
# ============================================================

with left_col:

    st.subheader(
        "관심 종목"
    )

    for i in range(
        QUICK_STOCKS
    ):

        stock = (
            st.session_state
            .portfolio[
                "quick_stocks"
            ][i]
        )


        # ----------------------------------------------------
        # 체크 + 종목코드
        # ----------------------------------------------------

        col_check, col_code = (
            st.columns(
                [0.12, 0.88],
                gap="small"
            )
        )


        with col_check:

            selected = st.checkbox(
                "",
                value=stock.get(
                    "selected",
                    False
                ),
                key=f"select_{i}",
                label_visibility="collapsed"
            )

            stock[
                "selected"
            ] = selected


        with col_code:

            code = st.text_input(
                f"{i + 1}. 종목코드",
                value=stock.get(
                    "code",
                    ""
                ),
                key=f"quick_code_{i}",
                label_visibility="collapsed",
                placeholder=f"{i + 1}. 종목코드"
            )

            stock[
                "code"
            ] = (
                code
                .strip()
                .upper()
            )


        # ----------------------------------------------------
        # 종목명 + 현재가격
        # ----------------------------------------------------

        col_name, col_price = (
            st.columns(
                [0.62, 0.38],
                gap="small"
            )
        )


        with col_name:

            stock_name = stock.get(
                "name",
                ""
            )

            if stock_name:

                st.markdown(
                    f"<div style='"
                    f"font-size:15px;"
                    f"font-weight:700;"
                    f"padding-top:1px;'>"
                    f"{stock_name}"
                    f"</div>",
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    "<div style='"
                    "font-size:12px;"
                    "color:#888888;"
                    "padding-top:2px;'>"
                    "종목코드 입력"
                    "</div>",
                    unsafe_allow_html=True
                )


        with col_price:

            current_price = (
                to_number(
                    stock.get(
                        "price",
                        0
                    )
                )
            )

            if current_price > 0:

                st.markdown(
                    f"<div style='"
                    f"text-align:right;"
                    f"font-weight:800;"
                    f"font-size:16px;"
                    f"padding-top:1px;'>"
                    f"{format_number(current_price)}"
                    f"</div>",
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    "<div style='"
                    "text-align:right;"
                    "font-size:15px;"
                    "padding-top:1px;'>"
                    "-"
                    "</div>",
                    unsafe_allow_html=True
                )


        st.markdown(
            "<hr style='"
            "margin:2px 0 7px 0;"
            "border:none;"
            "border-top:1px solid #e6e6e6;'>",
            unsafe_allow_html=True
        )


# ============================================================
# 오른쪽 계좌 포트폴리오
# ============================================================

with right_col:

    st.subheader(
        "계좌 포트폴리오"
    )

    tabs = st.tabs(
        ACCOUNTS
    )


    for tab, account in zip(
        tabs,
        ACCOUNTS
    ):

        with tab:

            st.caption(
                "1~4번은 보유종목, "
                "5번은 현금잔고입니다."
            )


            # =================================================
            # 버튼
            # =================================================

            button1, button2 = (
                st.columns(2)
            )


            with button1:

                if st.button(
                    "➕ 선택 종목 추가",
                    key=f"add_{account}",
                    use_container_width=True
                ):

                    add_selected_to_account(
                        account
                    )


            with button2:

                if st.button(
                    "🔄 현재가 조회",
                    key=f"refresh_{account}",
                    use_container_width=True
                ):

                    with st.spinner(
                        f"{account} "
                        "현재가 조회 중..."
                    ):

                        refresh_account(
                            account
                        )


            # =================================================
            # 합계
            # =================================================

            total_buy = 0
            total_evaluation = 0

            rows = (
                st.session_state
                .portfolio[
                    "accounts"
                ][account]
            )


            # =================================================
            # 1~4번 보유주식
            # =================================================

            for i in range(
                ACCOUNT_STOCKS
            ):

                row = rows[i]


                with st.container(
                    border=True
                ):

                    title_col, delete_col = (
                        st.columns(
                            [0.82, 0.18]
                        )
                    )


                    # -----------------------------------------
                    # 종목명
                    # -----------------------------------------

                    with title_col:

                        if row.get(
                            "code"
                        ):

                            st.markdown(
                                f"### {i + 1}. "
                                f"{row.get('name', '')}"
                            )

                            st.caption(
                                row.get(
                                    "code",
                                    ""
                                )
                            )

                        else:

                            st.markdown(
                                f"### {i + 1}. 빈 종목"
                            )


                    # -----------------------------------------
                    # 삭제
                    # -----------------------------------------

                    with delete_col:

                        if row.get(
                            "code"
                        ):

                            if st.button(
                                "삭제",
                                key=(
                                    f"delete_"
                                    f"{account}_"
                                    f"{i}"
                                ),
                                use_container_width=True
                            ):

                                delete_account_stock(
                                    account,
                                    i
                                )


                    if not row.get(
                        "code"
                    ):

                        continue


                    # -----------------------------------------
                    # 매수단가 / 수량 / 현재가격
                    # -----------------------------------------

                    c1, c2, c3 = (
                        st.columns(
                            [1, 1, 1]
                        )
                    )


                    with c1:

                        buy_price_text = (
                            st.text_input(
                                "매수단가",
                                value=str(
                                    row.get(
                                        "buy_price",
                                        ""
                                    )
                                ),
                                key=(
                                    f"buy_"
                                    f"{account}_"
                                    f"{i}"
                                )
                            )
                        )


                    with c2:

                        quantity_text = (
                            st.text_input(
                                "매수주식수",
                                value=str(
                                    row.get(
                                        "quantity",
                                        ""
                                    )
                                ),
                                key=(
                                    f"qty_"
                                    f"{account}_"
                                    f"{i}"
                                )
                            )
                        )


                    with c3:

                        current_price = (
                            to_number(
                                row.get(
                                    "current_price",
                                    0
                                )
                            )
                        )

                        if current_price > 0:

                            st.metric(
                                "현재가격",
                                format_number(
                                    current_price
                                )
                            )

                        else:

                            st.metric(
                                "현재가격",
                                "-"
                            )


                    # -----------------------------------------
                    # 입력값
                    # -----------------------------------------

                    row[
                        "buy_price"
                    ] = buy_price_text

                    row[
                        "quantity"
                    ] = quantity_text


                    # -----------------------------------------
                    # 계산
                    # -----------------------------------------

                    buy_price = (
                        to_number(
                            buy_price_text
                        )
                    )

                    quantity = (
                        to_number(
                            quantity_text
                        )
                    )

                    buy_total = (
                        buy_price
                        * quantity
                    )

                    evaluation = (
                        current_price
                        * quantity
                    )

                    profit = (
                        evaluation
                        - buy_total
                    )

                    total_buy += (
                        buy_total
                    )

                    total_evaluation += (
                        evaluation
                    )


                    # -----------------------------------------
                    # 종목 계산 결과
                    # -----------------------------------------

                    r1, r2, r3 = (
                        st.columns(3)
                    )

                    r1.metric(
                        "매수총금액",
                        format_number(
                            buy_total
                        )
                    )

                    r2.metric(
                        "평가금액",
                        format_number(
                            evaluation
                        )
                    )

                    r3.metric(
                        "평가손익",
                        format_profit(
                            profit
                        )
                    )


            # =================================================
            # 5번째 현금잔고
            # =================================================

            with st.container(
                border=True
            ):

                st.markdown(
                    f"### {CASH_SLOT_NO}. 현금잔고"
                )

                cash_text = st.text_input(
                    "현금잔고금액",
                    value=str(
                        st.session_state
                        .portfolio[
                            "cash_balances"
                        ].get(
                            account,
                            ""
                        )
                    ),
                    key=f"cash_{account}",
                    placeholder="예: 5,000,000"
                )

                st.session_state.portfolio[
                    "cash_balances"
                ][account] = (
                    cash_text
                )

                cash_balance = (
                    to_number(
                        cash_text
                    )
                )

                st.metric(
                    "현재 현금잔고",
                    format_number(
                        cash_balance
                    )
                    if cash_balance > 0
                    else "0"
                )


            # =================================================
            # 계좌 전체 합계
            # =================================================

            total_evaluation_with_cash = (
                total_evaluation
                + cash_balance
            )

            # 현금은 손익 0원으로 계산
            total_base = (
                total_buy
                + cash_balance
            )

            total_profit = (
                total_evaluation_with_cash
                - total_base
            )

            if total_base > 0:

                total_rate = (
                    total_profit
                    / total_base
                    * 100
                )

            else:

                total_rate = 0


            # =================================================
            # 계좌 합계 표시
            # =================================================

            st.markdown(
                "## 계좌 합계"
            )

            s1, s2, s3, s4 = (
                st.columns(4)
            )


            # ------------------------------------------------
            # 매수총금액
            # ------------------------------------------------

            with s1:

                st.markdown(
                    '<div class="summary-title">'
                    '매수총금액 합(주식)'
                    '</div>',
                    unsafe_allow_html=True
                )

                st.markdown(
                    f'<div class="summary-value">'
                    f'{format_number(total_buy)}'
                    f'</div>',
                    unsafe_allow_html=True
                )


            # ------------------------------------------------
            # 현재평가금액 + 현금
            # ------------------------------------------------

            with s2:

                st.markdown(
                    '<div class="summary-title">'
                    '현재평가금액 합'
                    '</div>',
                    unsafe_allow_html=True
                )

                st.markdown(
                    f'<div class="summary-value">'
                    f'{format_number(total_evaluation_with_cash)}'
                    f'</div>',
                    unsafe_allow_html=True
                )


            # ------------------------------------------------
            # 손익 색상
            # ------------------------------------------------

            if total_profit > 0:

                color_class = (
                    "profit-positive"
                )

            elif total_profit < 0:

                color_class = (
                    "profit-negative"
                )

            else:

                color_class = (
                    "profit-zero"
                )


            # ------------------------------------------------
            # 현재손익
            # ------------------------------------------------

            with s3:

                st.markdown(
                    '<div class="summary-title">'
                    '현재손익 합'
                    '</div>',
                    unsafe_allow_html=True
                )

                st.markdown(
                    f'<div class="{color_class}">'
                    f'{format_profit(total_profit)}'
                    f'</div>',
                    unsafe_allow_html=True
                )


            # ------------------------------------------------
            # 전체 수익률
            # ------------------------------------------------

            with s4:

                st.markdown(
                    '<div class="summary-title">'
                    '전체 수익률'
                    '</div>',
                    unsafe_allow_html=True
                )

                st.markdown(
                    f'<div class="{color_class}">'
                    f'{format_rate(total_rate)}'
                    f'</div>',
                    unsafe_allow_html=True
                )


# ============================================================
# 데이터 변경 여부 확인
# ============================================================

current_save_text = json.dumps(
    st.session_state.portfolio,
    ensure_ascii=False,
    sort_keys=True
)

previous_save_text = (
    st.session_state.get(
        "last_saved_text",
        ""
    )
)


# ============================================================
# 입력 내용이 변경되면 저장 요청
# ============================================================

if (
    st.session_state[
        "browser_loaded"
    ]
    and
    current_save_text
    != previous_save_text
):

    st.session_state[
        "browser_save_needed"
    ] = True

    save_server_data()


# ============================================================
# Safari LocalStorage 저장
#
# 중요:
# setItem은 전체 프로그램에서
# 이곳에서 단 한 번만 실행
# ============================================================

if (
    st.session_state[
        "browser_loaded"
    ]
    and
    st.session_state[
        "browser_save_needed"
    ]
):

    try:

        local_storage.setItem(
            LOCAL_STORAGE_KEY,
            current_save_text,
            key="portfolio_browser_save"
        )

        st.session_state[
            "last_saved_text"
        ] = current_save_text

        st.session_state[
            "browser_save_needed"
        ] = False

    except Exception:

        pass
