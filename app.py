import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- 1단계(MVP)를 위한 단순화 매핑 ---
# Foursquare API는 '국가'가 아닌 '도시'나 '좌표' 기반으로 검색합니다.
# 따라서 1단계에서는 국가와 도시, 좌표를 미리 매핑합니다.
COUNTRY_MAP = {
    "일본": {
        "code": "JP",  # Calendarific용 국가 코드
        "city": "Tokyo",  # OpenWeatherMap용 도시명
        "coords": "35.6895,139.6917"  # Foursquare용 좌표 (위도,경도)
    },
    "베트남": {
        "code": "VN",
        "city": "Hanoi",
        "coords": "21.0285,105.8542"
    }
}

# Foursquare API는 '테마'를 '카테고리 ID'로 받습니다.
# https://developer.foursquare.com/docs/places-api/categories
THEME_MAP = {
    "미식": "13065",  # Restaurant
    "쇼핑": "17064",  # Shop & Service
    "문화/유적": "16032"  # Historic Site
}

# --- API 키 로드 및 확인 (디버깅용) ---
# st.secrets에서 키를 안전하게 불러옵니다.
CALENDARIFIC_KEY = st.secrets.get("calendarific_key")
OPENWEATHER_KEY = st.secrets.get("openweather_key")
FOURSQUARE_KEY = st.secrets.get("foursquare_key")

# 사이드바에 키 로드 상태 표시
st.sidebar.title("🔑 API 키 상태")
st.sidebar.info("""
    `.streamlit/secrets.toml` 파일에
    3개의 API 키를 설정해야 합니다.
    """)
st.sidebar.markdown(
    f"Calendarific: {'✅' if CALENDARIFIC_KEY else '❌'}"
)
st.sidebar.markdown(
    f"OpenWeatherMap: {'✅' if OPENWEATHER_KEY else '❌'}"
)
st.sidebar.markdown(
    f"Foursquare: {'✅' if FOURSQUARE_KEY else '❌'}"
)

if not all([CALENDARIFIC_KEY, OPENWEATHER_KEY, FOURSQUARE_KEY]):
    st.error("일부 API 키가 secrets.toml 파일에 설정되지 않았습니다. 사이드바를 확인하세요.")
    st.stop()


# --- API 호출 헬퍼 함수 ---

def get_holidays(api_key, country_code, year, month):
    """Calendarific API로 특정 월의 공휴일 정보 호출"""
    try:
        url = "https://calendarific.com/api/v2/holidays"
        params = {
            "api_key": api_key,
            "country": country_code,
            "year": year,
            "month": month
        }
        response = requests.get(url, params=params)
        response.raise_for_status()  # 오류 발생 시 예외 처리
        return response.json().get("response", {}).get("holidays", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Calendarific API 오류: {e}")
        return None

def get_weather(api_key, city_name):
    """OpenWeatherMap API로 현재 날씨 정보 호출"""
    # 참고: 1단계(MVP)에서는 가장 단순한 '현재 날씨'를 호출합니다.
    # 사용자가 미래의 '날짜 범위'를 선택하더라도, 무료 OWM API는
    # 해당 범위의 '평균 날씨'를 제공하지 않습니다.
    # 2단계에서 이 로직을 고도화할 필요가 있습니다.
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city_name,
            "appid": api_key,
            "units": "metric",  # 섭씨온도
            "lang": "kr"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"OpenWeatherMap API 오류: {e}")
        return None

def get_places(api_key, coords, category_id):
    """Foursquare API로 테마별 장소 5곳 호출"""
    try:
        url = "https://api.foursquare.com/v3/places/search"
        headers = {
            "Authorization": api_key,
            "accept": "application/json"
        }
        params = {
            "ll": coords,
            "categories": category_id,
            "limit": 5,
            "fields": "name,location"  # 이름과 위치(주소) 정보만 요청
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get("results", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Foursquare API 오류: {e}")
        return None

# --- Streamlit UI 구성 ---

st.title("나만의 여행 비서 앱 ✈️ (MVP 1단계)")
st.caption("API 호출 및 원시 데이터(Raw Data) 확인")

# 1단계(MVP)의 UI 구성
country_name = st.selectbox(
    "국가 선택",
    options=COUNTRY_MAP.keys() # ["일본", "베트남"]
)

# 날짜 범위 선택 (기본값: 오늘부터 30일 뒤까지)
today = datetime.now().date()
default_end = today + pd.DateOffset(days=30)
date_range = st.date_input(
    "날짜 범위 선택",
    value=(today, default_end)
)

theme_name = st.selectbox(
    "테마 선택",
    options=THEME_MAP.keys() # ["미식", "쇼핑", "문화/유적"]
)

if st.button("추천받기"):
    # 0. 입력값 매핑
    country_data = COUNTRY_MAP[country_name]
    theme_id = THEME_MAP[theme_name]
    
    # 날짜 범위 확인 (Calendarific 호출용)
    start_date = date_range[0]
    # (참고: 1단계에서는 단순화를 위해 시작 월만 사용합니다.)
    start_year = start_date.year
    start_month = start_date.month

    # 모든 API 호출 실행
    with st.spinner("API에서 데이터를 가져오는 중입니다..."):
        all_ok = True
        
        # 1. Calendarific (공휴일) 호출
        st.subheader(f"🗓️ {start_year}년 {start_month}월 {country_name} 공휴일 (Calendarific)")
        holidays = get_holidays(
            CALENDARIFIC_KEY, 
            country_data["code"], 
            start_year, 
            start_month
        )
        if holidays:
            # 원시 데이터(JSON)를 그대로 출력
            st.json(holidays)
        else:
            st.warning("공휴일 정보를 가져오지 못했습니다.")
            all_ok = False

        # 2. OpenWeatherMap (날씨) 호출
        st.subheader(f"🌦️ {country_data['city']} 현재 날씨 (OpenWeatherMap)")
        weather = get_weather(OPENWEATHER_KEY, country_data["city"])
        if weather:
            st.write(f"**현재 날씨:** {weather['weather'][0]['description']}")
            st.write(f"**현재 기온:** {weather['main']['temp']}°C")
            st.write(f"**체감 기온:** {weather['main']['feels_like']}°C")
            # 원시 데이터(JSON)도 함께 출력
            with st.expander("전체 원시 데이터 보기"):
                st.json(weather)
        else:
            st.warning("날씨 정보를 가져오지 못했습니다.")
            all_ok = False

        # 3. Foursquare (관광지) 호출
        st.subheader(f"📍 {country_data['city']} '{theme_name}' 테마 추천 장소 (Foursquare)")
        places = get_places(FOURSQUARE_KEY, country_data["coords"], theme_id)
        if places:
            # Foursquare 결과는 표로 만드는 것이 보기 좋습니다.
            place_list = []
            for place in places:
                place_list.append({
                    "이름": place.get("name"),
                    "주소": place.get("location", {}).get("formatted_address", "주소 정보 없음")
                })
            st.dataframe(pd.DataFrame(place_list))
            # 원시 데이터(JSON)도 함께 출력
            with st.expander("전체 원시 데이터 보기"):
                st.json(places)
        else:
            st.warning("추천 장소 정보를 가져오지 못했습니다.")
            all_ok = False
            
    if all_ok:
        st.success("모든 API 호출이 성공적으로 완료되었습니다!")
