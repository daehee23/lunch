import calendar
import datetime
import re
import requests
import streamlit as st

st.set_page_config(
    page_title="월간 학교 급식 달력", page_icon="📅", layout="wide"
)
st.title("📅 우리 학교 월간 급식 달력")
st.caption("선택한 월의 급식 메뉴를 주간 달력 형태로 한눈에 확인합니다.")

ALLERGY_MAP = {
    1: "난류",
    2: "우유",
    3: "메밀",
    4: "땅콩",
    5: "대두",
    6: "밀",
    7: "고등어",
    8: "게",
    9: "새우",
    10: "돼지고기",
    11: "복숭아",
    12: "토마토",
    13: "아황산류",
    14: "호두",
    15: "닭고기",
    16: "쇠고기",
    17: "오징어",
    18: "조개류(굴/전복/홍합 포함)",
    19: "잣",
}

# 1. 고기류 정규식 (빨간색 하이라이트)
MEAT_PATTERN = re.compile(
    r"(돼지|돈육|소고기|쇠고기|우육|닭|계육|오리|양고기|함박|떡갈비|너겟|탕수육|돈까스|돈가스|불고기|제육|장조림|갈비|보쌈|수육|소시지|소세지|햄|베이컨|\b10\b|\b15\b|\b16\b)"
)

# 2. 자율 메뉴 정규식 (초록색 하이라이트)
SELF_PATTERN = re.compile(r"자율")

# 3. 면류 정규식 (날짜 옆 🍜 이모지)
NOODLE_PATTERN = re.compile(
    r"(국수|우동|라면|짬뽕|짜장|자장|스파게티|파스타|소바|쫄면|비빔면|칼국수|수제비|당면|마라탕|쌀국수)"
)

# 4. 밥류 정규식 (날짜 옆 🍚 이모지)
RICE_PATTERN = re.compile(r"(밥|라이스|리조또|덮밥|볶음밥|비빔밥|조밥|현미밥|흑미밥)")


def highlight_dishes(dish_text):
    """고기는 빨간색, '자율' 메뉴는 초록색으로 하이라이트합니다."""
    is_meat = bool(MEAT_PATTERN.search(dish_text))
    is_self = bool(SELF_PATTERN.search(dish_text))

    if is_meat:
        return f" :red-background[**{dish_text}**] 🥩"
    elif is_self:
        return f" :green-background[**{dish_text}**] 🌿"

    return dish_text


def get_staple_emoji(day_meals):
    """해당 날짜의 식단 전체를 분석하여 면류(🍜) 또는 밥류(🍚) 이모지를 반환합니다."""
    all_text = ""
    for dishes in day_meals.values():
        all_text += " ".join(dishes) + " "

    if NOODLE_PATTERN.search(all_text):
        return " 🍜"
    elif RICE_PATTERN.search(all_text):
        return " 🍚"
    return ""


def replace_allergy_codes(dish_text, convert_to_text=True):
    """메뉴명 뒤의 알레르기 번호를 감지하여 한글 식재료명으로 치환합니다."""
    if not convert_to_text or not dish_text:
        return dish_text

    def convert_match(match):
        raw = match.group(0)
        nums = re.findall(r"\d+", raw)
        allergens = [
            ALLERGY_MAP[int(n)] for n in nums if int(n) in ALLERGY_MAP
        ]
        if allergens:
            return f" :orange[[{', '.join(allergens)}]]"
        return raw

    pattern = r"\(?(\d+\.)+\)?"
    return re.sub(pattern, convert_match, dish_text)


st.sidebar.header("⚙️ 학교 정보 설정")
office_code = st.sidebar.text_input(
    "시도교육청코드", value="T10", help="기본값: 제주특별자치도교육청(T10)"
)
school_code = st.sidebar.text_input(
    "표준학교코드",
    value="9290088",
    help="기본값: 제주중앙고등학교(9290088)",
)

st.sidebar.markdown("---")
st.sidebar.subheader("🍽️ 알레르기 표시 설정")
show_allergen_names = st.sidebar.toggle(
    "알레르기 식품명으로 변환",
    value=True,
    help="체크 시 숫자(예: 1. 5.) 대신 [난류, 대두] 형태로 변환하여 표시합니다.",
)

with st.sidebar.expander("📖 나이스 알레르기 번호 안내표"):
    table_md = "\n".join([f"- **{k}번**: {v}" for k, v in ALLERGY_MAP.items()])
    st.markdown(table_md)

today = datetime.date.today()
col_y, col_m, col_filter = st.columns([1, 1, 2])
with col_y:
    year = st.selectbox(
        "연도 선택",
        options=list(range(today.year - 1, today.year + 2)),
        index=1,
    )
with col_m:
    month = st.selectbox(
        "월 선택", options=list(range(1, 13)), index=today.month - 1
    )
with col_filter:
    meal_filter = st.radio(
        "급식 종류 선택",
        options=["전체 보기", "중식만 보기", "석식만 보기"],
        index=0,
        horizontal=True,
    )


def fetch_monthly_meals(key, ofcdc_code, schul_code, yr, mo):
    """선택한 월의 1일부터 말일까지의 급식을 조회합니다."""
    _, last_day = calendar.monthrange(yr, mo)
    from_ymd = f"{yr}{mo:02d}01"
    to_ymd = f"{yr}{mo:02d}{last_day:02d}"

    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": ofcdc_code,
        "SD_SCHUL_CODE": schul_code,
        "MLSV_FROM_YMD": from_ymd,
        "MLSV_TO_YMD": to_ymd,
    }
    response = requests.get(url, params=params, timeout=7)
    return response.json()


if "NEIS_KEY" not in st.secrets:
    st.error("⚠️ Streamlit Secrets에 `NEIS_KEY`가 설정되어 있지 않습니다.")
    st.stop()

neis_key = st.secrets["NEIS_KEY"]

try:
    with st.spinner(f"{year}년 {month}월 급식 정보를 불러오는 중..."):
        res_data = fetch_monthly_meals(
            neis_key, office_code, school_code, year, month
        )

    meal_dict = {}
    if "mealServiceDietInfo" in res_data:
        rows = res_data["mealServiceDietInfo"][1]["row"]
        for row in rows:
            ymd = row.get("MLSV_YMD")
            meal_type = row.get("MMEAL_SC_NM", "급식")
            dish = row.get("DDISH_NM", "")

            # 1. 알레르기 코드 치환
            formatted_dish = replace_allergy_codes(
                dish, convert_to_text=show_allergen_names
            )

            # 2. 메뉴 단위로 분리 후 하이라이트 적용
            raw_lines = [
                d.strip()
                for d in formatted_dish.replace("<br/>", "\n").split("\n")
                if d.strip()
            ]
            dish_lines = [highlight_dishes(d) for d in raw_lines]

            meal_dict.setdefault(ymd, {})[meal_type] = dish_lines

    month_cal = calendar.monthcalendar(year, month)
    weekdays_kr = ["월", "화", "수", "목", "금"]

    st.markdown("---")

    for week in month_cal:
        cols = st.columns(5)
        has_school_day = False

        for i in range(5):
            day = week[i]
            with cols[i]:
                if day == 0:
                    st.empty()
                else:
                    has_school_day = True
                    ymd_str = f"{year}{month:02d}{day:02d}"
                    day_meals = meal_dict.get(ymd_str, {})
                    is_today = (
                        year == today.year
                        and month == today.month
                        and day == today.day
                    )

                    # 밥/면 이모지 계산
                    staple_icon = get_staple_emoji(day_meals)

                    with st.container(border=True):
                        if is_today:
                            st.markdown(
                                f"**{month}월 {day}일 ({weekdays_kr[i]})**{staple_icon} :orange-background[**TODAY**]"
                            )
                        else:
                            st.markdown(
                                f"**{month}월 {day}일 ({weekdays_kr[i]})**{staple_icon}"
                            )

                        st.divider()

                        if not day_meals:
                            st.caption("급식 없음 (휴업/방학)")
                        else:
                            displayed_count = 0

                            if (
                                meal_filter in ["전체 보기", "중식만 보기"]
                                and "중식" in day_meals
                            ):
                                displayed_count += 1
                                st.markdown(":blue[**🥣 중식**]")
                                for dish in day_meals["중식"]:
                                    st.markdown(
                                        f"<span style='font-size:0.85rem;'>• {dish}</span>",
                                        unsafe_allow_html=True,
                                    )

                            if (
                                meal_filter in ["전체 보기", "석식만 보기"]
                                and "석식" in day_meals
                            ):
                                displayed_count += 1
                                if (
                                    meal_filter == "전체 보기"
                                    and "중식" in day_meals
                                ):
                                    st.write("")
                                st.markdown(":red[**🌙 석식**]")
                                for dish in day_meals["석식"]:
                                    st.markdown(
                                        f"<span style='font-size:0.85rem;'>• {dish}</span>",
                                        unsafe_allow_html=True,
                                    )

                            if meal_filter == "전체 보기":
                                for m_type, dishes in day_meals.items():
                                    if m_type not in ["중식", "석식"]:
                                        displayed_count += 1
                                        st.markdown(
                                            f":green[**🍴 {m_type}**]"
                                        )
                                        for dish in dishes:
                                            st.markdown(
                                                f"<span style='font-size:0.85rem;'>• {dish}</span>",
                                                unsafe_allow_html=True,
                                            )

                            if displayed_count == 0:
                                st.caption("해당 식단 없음")

        if has_school_day:
            st.write("")

except requests.exceptions.RequestException as e:
    st.error(
        f"⚠️ 나이스 API 통신 오류: 네트워크 상태를 확인해 주세요. ({e})"
    )
except Exception as e:
    st.error(f"⚠️ 화면 구성 중 오류가 발생했습니다: {e}")
