import calendar
from datetime import datetime
import requests
import streamlit as st

# ==========================================
# 1. 페이지 기본 설정 및 스타일 정의
# ==========================================
st.set_page_config(page_title="학교 급식 달력", layout="wide", page_icon="🍱")

# 카드로 날짜를 표현하기 위한 간단한 CSS 스타일
st.markdown(
    """
    <style>
    .day-card {
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 15px;
        min-height: 250px;
        background-color: #FFFFFF;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .today-card {
        border: 2px solid #FF4B4B !important;
        background-color: #FFF5F5 !important;
    }
    .day-header {
        font-weight: bold;
        font-size: 1.1em;
        margin-bottom: 8px;
        padding-bottom: 4px;
        border-bottom: 1px solid #F0F0F0;
    }
    .today-badge {
        background-color: #FF4B4B;
        color: white;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8em;
        float: right;
    }
    .meal-title {
        font-weight: bold;
        margin-top: 8px;
        margin-bottom: 2px;
        font-size: 0.9em;
    }
    .lunch { color: #1E88E5; }  /* 중식: 파란색 */
    .dinner { color: #E53935; } /* 석식: 빨간색 */
    .other-meal { color: #43A047; } /* 조식 등: 초록색 */
    .menu-text {
        font-size: 0.85em;
        color: #333333;
        line-height: 1.4;
    }
    .no-data {
        color: #9E9E9E;
        font-size: 0.85em;
        font-style: italic;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# 알레르기 번호 -> 식재료 명칭 매핑 사전 (1~19)
ALLERGY_MAP = {
    "1": "난류",
    "2": "우유",
    "3": "메밀",
    "4": "땅콩",
    "5": "대두",
    "6": "밀",
    "7": "고등어",
    "8": "게",
    "9": "새우",
    "10": "돼지고기",
    "11": "복숭아",
    "12": "토마토",
    "13": "아황산류",
    "14": "호두",
    "15": "닭고기",
    "16": "쇠고기",
    "17": "오징어",
    "18": "조개류",
    "19": "잣",
}


# ==========================================
# 2. 알레르기 변환 함수
# ==========================================
def replace_allergy_codes(menu_str, convert_flag):
    """메뉴 문자열 내의 알레르기 숫자(1~19)를 설정에 따라 이름으로 변환하거나 정리합니다."""
    if not menu_str:
        return ""

    import re

    # NEIS 메뉴는 보통 "메뉴명 (1.2.5)" 형태로 전달됨
    def replace_match(match):
        numbers = match.group(1).split(".")
        if convert_flag:
            # 숫자를 식재료 이름으로 변환
            names = [ALLERGY_MAP.get(num, num) for num in numbers if num]
            return f" <span style='color:#888; font-size:0.8em;'>({', '.join(names)})</span>"
        else:
            # 숫자 유지
            return f" <span style='color:#888; font-size:0.8em;'>({'.'.join(numbers)})</span>"

    # 괄호 안의 숫자.숫자 패턴 찾기
    cleaned_menu = re.sub(r"\(([0-9\.]+)\)", replace_match, menu_str)
    # <br/> 태그 정리
    cleaned_menu = cleaned_menu.replace("<br/>", "<br/>• ")
    return "• " + cleaned_menu


# ==========================================
# 3. 사이드바 구성
# ==========================================
st.sidebar.title("⚙️ 설정")

# NEIS API 키 확인 (st.secrets)
if "NEIS_KEY" not in st.secrets:
    st.error("⚠️ `NEIS_KEY`가 Secrets에 설정되어 있지 않습니다.")
    st.info(
        "`.streamlit/secrets.toml` 파일에 아래와 같이 API 키를 추가해 주세요:\n"
        '```toml\nNEIS_KEY = "발급받은_API_키"\n
