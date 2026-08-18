import streamlit as st
import requests
import json
import os


# ============================================================
# 기본 설정
# ============================================================

QUICK_STOCKS = 10
ACCOUNT_STOCKS = 5

ACCOUNTS = [
    "퇴직연금DC형",
    "IRP",
    "ISA",
    "연금저축"
]


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

SAVE_FILE = os.path.join(
    BASE_DIR,
    "portfolio_mobile.json"
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
        font-size: 17px;
        font-weight: 700;
    }

    .stock-price {
        font-size: 18px;
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

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 네이버 요청 Header
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
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

    if float(value).is_integer():
        return f"{int(value):,}"

    return f"{value:,.2f}"


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


    if not stock_name or close_price is None:
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


    # 네이버 내부 Reuters 코드 후보
    reuters_codes = [
        f"{ticker}.O",
        f"{ticker}.N",
        f"{ticker}.A"
    ]


    for reuters_code in reuters_codes:

        url = (
            f"https://api.stock.naver.com/"
            f"stock/{reuters_code}/basic"
        )

        data = request_json(url)


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


        if not stock_name or price_value is None:
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


    # --------------------------------------------------------
    # 국내 6자리 종목 우선
    # --------------------------------------------------------

    if len(code) == 6:

        result = get_domestic_stock(
            code
        )

        if result:
            return result


    # --------------------------------------------------------
    # 영문 포함 → 미국종목 조회
    # --------------------------------------------------------

    if any(
        c.isalpha()
        for c in code
    ):

        result = get_overseas_stock(
            code
        )

        if result:
            return result


    # --------------------------------------------------------
    # 마지막 국내 재시도
    # --------------------------------------------------------

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
        }
    }


# ============================================================
# 데이터 불러오기
# ============================================================

def load_data():

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


        default = make_default_data()


        # ----------------------------------------------------
        # 관심종목
        # ----------------------------------------------------

        quick = data.get(
            "quick_stocks",
            []
        )


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


        # ----------------------------------------------------
        # 계좌
        # ----------------------------------------------------

        saved_accounts = data.get(
            "accounts",
            {}
        )


        for account in ACCOUNTS:

            rows = saved_accounts.get(
                account,
                []
            )


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
            ][account] = (
                rows[
                    :ACCOUNT_STOCKS
                ]
            )


        return default


    except:

        return make_default_data()


# ============================================================
# 저장
# ============================================================

def save_data():

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

    except Exception as e:

        st.error(
            f"데이터 저장 오류: {e}"
        )


# ============================================================
# Session 초기화
# ============================================================

if "portfolio" not in st.session_state:

    st.session_state.portfolio = (
        load_data()
    )


# ============================================================
# 관심종목 전체 조회
# ============================================================

def refresh_quick_stocks():

    success = 0


    for stock in (
        st.session_state
        .portfolio[
            "quick_stocks"
        ]
    ):

        code = (
            stock.get(
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

            stock["code"] = code

            stock["name"] = (
                result["name"]
            )

            stock["price"] = (
                result["price"]
            )

            success += 1


    save_data()

    return success


# ============================================================
# 계좌 현재가 조회
# ============================================================

def refresh_account(
    account
):

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
            ] = result["price"]

            success += 1


    save_data()

    return success


# ============================================================
# 전체 현재가 조회
# ============================================================

def refresh_all():

    success = 0


    success += (
        refresh_quick_stocks()
    )


    for account in ACCOUNTS:

        success += (
            refresh_account(
                account
            )
        )


    return success


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

        for stock in quick_stocks

        if stock.get(
            "selected",
            False
        )
    ]


    if not selected:

        st.warning(
            "왼쪽 관심종목에서 추가할 종목을 선택해 주세요."
        )

        return


    for stock in selected:


        code = (
            stock.get(
                "code",
                ""
            )
        )


        if not code:
            continue


        # ----------------------------------------------------
        # 중복 체크
        # ----------------------------------------------------

        exists = any(

            row.get("code")
            == code

            for row
            in account_rows
        )


        if exists:
            continue


        # ----------------------------------------------------
        # 빈 행 찾기
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
                f"{account}은 최대 "
                f"{ACCOUNT_STOCKS}개 종목까지 가능합니다."
            )

            break


        # ----------------------------------------------------
        # 추가
        # ----------------------------------------------------

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


    save_data()


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


    save_data()


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
# 전체 시세 조회
# ============================================================

if st.button(
    "🔄 전체 현재가 조회",
    use_container_width=True,
    type="primary"
):

    with st.spinner(
        "현재가를 조회하고 있습니다..."
    ):

        success = refresh_all()


    if success > 0:

        st.success(
            f"{success}개 종목의 현재가를 갱신했습니다."
        )

    else:

        st.error(
            "현재가 조회에 실패했습니다."
        )


    st.rerun()


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


    if st.button(
        "🔄 관심종목 현재가 조회",
        key="quick_refresh",
        use_container_width=True
    ):

        with st.spinner(
            "관심종목을 조회하고 있습니다..."
        ):

            success = (
                refresh_quick_stocks()
            )


        if success == 0:

            st.warning(
                "현재가 조회에 실패했습니다."
            )


        st.rerun()


    # --------------------------------------------------------
    # 관심종목 10개
    # --------------------------------------------------------

    for i in range(
        QUICK_STOCKS
    ):

        stock = (
            st.session_state
            .portfolio[
                "quick_stocks"
            ][i]
        )


        with st.container(
            border=True
        ):

            top1, top2 = (
                st.columns(
                    [0.18, 0.82]
                )
            )


            # ------------------------------------------------
            # 체크박스
            # ------------------------------------------------

            with top1:

                selected = st.checkbox(
                    "",
                    value=stock.get(
                        "selected",
                        False
                    ),
                    key=f"select_{i}"
                )


                stock[
                    "selected"
                ] = selected


            # ------------------------------------------------
            # 종목코드
            # ------------------------------------------------

            with top2:

                code = st.text_input(
                    f"{i + 1}. 종목코드",
                    value=stock.get(
                        "code",
                        ""
                    ),
                    key=f"quick_code_{i}"
                )


                stock[
                    "code"
                ] = (
                    code
                    .strip()
                    .upper()
                )


            # ------------------------------------------------
            # 종목명
            # ------------------------------------------------

            stock_name = (
                stock.get(
                    "name",
                    ""
                )
            )


            if stock_name:

                st.markdown(
                    f"**{stock_name}**"
                )

            else:

                st.caption(
                    "종목코드 입력 후 현재가 조회"
                )


            # ------------------------------------------------
            # 현재가격 - 읽기 전용 표시
            # ------------------------------------------------

            current_price = to_number(
                stock.get(
                    "price",
                    0
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


# ============================================================
# 오른쪽 계좌
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


            # =================================================
            # 버튼 영역
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

                    st.rerun()


            with button2:

                if st.button(
                    "🔄 현재가 조회",
                    key=f"refresh_{account}",
                    use_container_width=True
                ):

                    with st.spinner(
                        f"{account} 현재가 조회 중..."
                    ):

                        refresh_account(
                            account
                        )


                    st.rerun()


            # =================================================
            # 합계 변수
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
            # 계좌당 5개 종목
            # =================================================

            for i in range(
                ACCOUNT_STOCKS
            ):

                row = rows[i]


                with st.container(
                    border=True
                ):


                    # -----------------------------------------
                    # 종목명 / 삭제
                    # -----------------------------------------

                    title_col, delete_col = (
                        st.columns(
                            [0.82, 0.18]
                        )
                    )


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

                                st.rerun()


                    # -----------------------------------------
                    # 빈 종목이면 계산 영역 생략
                    # -----------------------------------------

                    if not row.get(
                        "code"
                    ):

                        continue


                    # -----------------------------------------
                    # 매수단가 / 수량
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


                    # -----------------------------------------
                    # 현재가격은 입력칸 없이 표시
                    # -----------------------------------------

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
                    # 입력값 저장
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

                    buy_price = to_number(
                        buy_price_text
                    )

                    quantity = to_number(
                        quantity_text
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


                    # -----------------------------------------
                    # 합계
                    # -----------------------------------------

                    total_buy += (
                        buy_total
                    )

                    total_evaluation += (
                        evaluation
                    )


                    # -----------------------------------------
                    # 종목 계산결과
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
            # 계좌 전체 합계
            # =================================================

            total_profit = (
                total_evaluation
                - total_buy
            )


            if total_buy > 0:

                total_rate = (
                    total_profit
                    / total_buy
                    * 100
                )

            else:

                total_rate = 0


            st.markdown(
                "## 계좌 합계"
            )


            s1, s2, s3, s4 = (
                st.columns(4)
            )


            # ------------------------------------------------
            # 매수총금액 합
            # ------------------------------------------------

            with s1:

                st.markdown(
                    '<div class="summary-title">'
                    '매수총금액 합'
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
            # 현재평가금액 합
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
                    f'{format_number(total_evaluation)}'
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
            # 현재손익 합
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
# 자동 저장
# ============================================================

save_data()