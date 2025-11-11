import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- 1단계(MVP)를 위한 단순화 매핑 ---
# Foursquare, Open-Meteo 모두 좌표 기반으로 검색합니다.
COUNTRY_MAP = {
    "일본": {
        "code": "JP",  # Calendarific용 국가 코드
        "city_name": "Tokyo", # Foursquare 결과 표시용
        "coords": "35.6895,139.6917"  # Foursquare, Open-Meteo용 (위도,경도)
    },
    "베트남": {
        "code": "VN",
        "city_name": "Hanoi",
        "coords": "21.0285,105.8542"
    }
}

# Foursquare API는 '테마'를 '카테고리 ID'로 받습니다.
THEME_MAP = {
    "미식": "13065",  # Restaurant
    "쇼핑": "17064",  # Shop & Service
    "문화/유적": "16032"  # Historic Site
}

# --- API 키 로드 및 확인 ---
# st.secrets에서 키를 안전하게 불러옵니다.
CALENDARIFIC_KEY = st.secrets.get("calendarific_key")
FOURSQUARE_KEY = st.secrets.get("foursquare_key")

def check_api_keys():
    """사이드바에 API 키 로드 상태를 표시하고 유효성을 검사합니다."""
    st.sidebar.title("🔑 API 키 상태")
    st.sidebar.info("""
        이 앱을 실행하려면 `.streamlit/secrets.toml` 파일에
        2개의 API 키를 설정해야 합니다.
        (자세한 내용은 README.md 참조)
        """)
    
    key_statuses = {
        "Calendarific": bool(CALENDARIFIC_KEY),
        "Foursquare": bool(FOURSQUARE_KEY)
    }
    
    all_keys_loaded = all(key_statuses.values())

    for key_name, is_loaded in key_statuses.items():
        st.sidebar.markdown(f"{key_name}: {'✅' if is_loaded else '❌'}")

    st.sidebar.success("날씨 API (Open-Meteo)는 API 키가 필요 없습니다! 🎉")
    
    if not all_keys_loaded:
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
        response.raise_for_status() # 200 OK가 아니면 오류 발생
        return response.json().get("response", {}).get("holidays", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Calendarific API 오류: {e}")
        return None

def get_weather_forecast(latitude, longitude, start_date, end_date):
    """Open-Meteo API로 날짜 범위의 일기 예보 호출"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "auto"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Open-Meteo API 오류: {e}")
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
            "fields": "name,location" # 필요한 필드만 요청
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get("results", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Foursquare API 오류: {e}")
        return None

# --- 메인 함수 ---
def main():
    st.title("나만의 여행 비서 앱 ✈️ (MVP 1단계)")
    st.caption("API 호출 및 원시 데이터(Raw Data) 확인 (날씨: Open-Meteo)")
    
    # 1. API 키 확인 (사이드바에 표시)
    check_api_keys()

    # 2. 사용자 입력 UI
    country_name = st.selectbox(
        "국가 선택",
        options=COUNTRY_MAP.keys()
    )

    today = datetime.now().date()
    # Open-Meteo 무료 예보는 16일
    default_end = today + pd.DateOffset(days=15) 
    date_range = st.date_input(
        "날짜 범위 선택 (최대 16일)",
        value=(today, default_end)
    )

    theme_name = st.selectbox(
        "테마 선택",
        options=THEME_MAP.keys()
    )

    # 3. "추천받기" 버튼 로직
    if st.button("추천받기"):
        # 입력값 매핑
        country_data = COUNTRY_MAP[country_name]
        theme_id = THEME_MAP[theme_name]
        
        # 날짜 범위 확인 (Calendarific, Open-Meteo)
        start_date = date_range[0]
        end_date = date_range[1]
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        start_year = start_date.year
        start_month = start_date.month

        lat, lon = country_data["coords"].split(',')

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
                st.json(holidays)
            else:
                st.warning("공휴일 정보를 가져오지 못했습니다.")
                all_ok = False

            # 2. Open-Meteo (날씨) 호출
            st.subheader(f"🌦️ {country_data['city_name']} 날씨 예보 (Open-Meteo)")
            weather = get_weather_forecast(lat, lon, start_date_str, end_date_str)
            
            if weather and 'daily' in weather:
                weather_df = pd.DataFrame(weather['daily'])
                weather_df['time'] = pd.to_datetime(weather_df['time'])
                weather_df = weather_df.set_index('time')
                
                st.write(f"**평균 최고 기온:** {weather_df['temperature_2m_max'].mean():.1f}°C")
                st.write(f"**평균 최저 기온:** {weather_df['temperature_2m_min'].mean():.1f}°C")
                st.write(f"**최고 강수 확률:** {weather_df['precipitation_probability_max'].max()}%")
                
                st.line_chart(weather_df[['temperature_2m_max', 'temperature_2m_min']])
                
                with st.expander("전체 원시 데이터 보기"):
                    st.json(weather)
            else:
                st.warning("날씨 정보를 가져오지 못했습니다.")
                if weather: st.json(weather) # 오류가 있다면 원시 데이터 표시
                all_ok = False

            # 3. Foursquare (관광지) 호출
            st.subheader(f"📍 {country_data['city_name']} '{theme_name}' 테마 추천 장소 (Foursquare)")
            places = get_places(FOURSQUARE_KEY, country_data["coords"], theme_id)
            if places:
                place_list = []
                for place in places:
                    place_list.append({
                        "이름": place.get("name"),
                        "주소": place.get("location", {}).get("formatted_address", "주소 정보 없음")
                    })
                st.dataframe(pd.DataFrame(place_list))
                with st.expander("전체 원시 데이터 보기"):
                    st.json(places)
            else:
                st.warning("추천 장소 정보를 가져오지 못했습니다.")
                all_ok = False
                
        if all_ok:
            st.success("모든 API 호출이 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    main()
