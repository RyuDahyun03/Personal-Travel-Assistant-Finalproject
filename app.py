import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- 상수 정의 ---
COUNTRY_MAP = {
    "일본": {"code": "JP", "city_name": "Tokyo", "coords": "35.6895,139.6917"},
    "베트남": {"code": "VN", "city_name": "Hanoi", "coords": "21.0285,105.8542"}
}
THEME_MAP = {
    "미식": "13065",
    "쇼핑": "17064",
    "문화/유적": "16032"
}

# 2단계: 추천 모드별 가중치 설정
# [날씨(기온), 날씨(강수), 가격(저렴), 효율(연차), 테마(축제)]
WEIGHTS = {
    "가장 저렴하고 한적하게": [ 1, -1, 10,  1, -5],
    "연차 아껴서 알차게":   [ 1, -1, -5, 10,  1],
    "테마와 날씨가 완벽하게": [10, -5,  1,  1, 10]
}

# --- API 키 로드 ---
CALENDARIFIC_KEY = st.secrets.get("calendarific_key")
FOURSQUARE_KEY = st.secrets.get("foursquare_key")

def check_api_keys():
    st.sidebar.title("🔑 API 키 상태")
    st.sidebar.info("`.streamlit/secrets.toml` 파일에 2개의 API 키를 설정해야 합니다.")
    
    key_statuses = {
        "Calendarific": bool(CALENDARIFIC_KEY),
        "Foursquare": bool(FOURSQUARE_KEY)
    }
    all_keys_loaded = all(key_statuses.values())

    for key_name, is_loaded in key_statuses.items():
        st.sidebar.markdown(f"{key_name}: {'✅' if is_loaded else '❌'}")
    st.sidebar.success("날씨 API (Open-Meteo)는 API 키가 필요 없습니다! 🎉")
    
    if not all_keys_loaded:
        st.error("API 키가 설정되지 않았습니다. `secrets.toml` 파일을 확인하세요.")
        st.stop()

# --- API 호출 함수 ---

@st.cache_data(ttl=3600) # 1시간 캐시
def get_holidays_for_period(api_key, country_code, start_date, end_date):
    """(업그레이드) 선택한 기간(여러 달)의 모든 공휴일을 가져옵니다."""
    all_holidays = set()
    # pd.date_range로 시작월부터 종료월까지 월별로 순회
    for month_start in pd.date_range(start_date, end_date, freq='MS'):
        year = month_start.year
        month = month_start.month
        try:
            url = "https://calendarific.com/api/v2/holidays"
            params = {"api_key": api_key, "country": country_code, "year": year, "month": month}
            response = requests.get(url, params=params)
            response.raise_for_status()
            holidays = response.json().get("response", {}).get("holidays", [])
            for holiday in holidays:
                all_holidays.add(holiday.get("date", {}).get("iso", "").split("T")[0])
        except requests.exceptions.RequestException:
            pass # 한 달 실패해도 계속 진행
            
    # 'YYYY-MM-DD' 형식의 날짜 문자열 세트(set) 반환
    return all_holidays

@st.cache_data(ttl=3600) # 1시간 캐시
def get_historical_weather(latitude, longitude, start_date, end_date):
    """(업그레이드) Open-Meteo의 '과거' 날씨 API를 호출합니다."""
    try:
        url = "https://archive-api.open-meteo.com/v1/archive" # 'archive' API
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_max,precipitation_sum", # 최고기온, 총 강수량
            "timezone": "auto"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Open-Meteo 과거 날씨 API 오류: {e}")
        return None

# --- (★수정★) 'get_places' 함수를 디버그 모드로 변경 ---

@st.cache_data(ttl=3600) # 1시간 캐시
def get_places(api_key, coords, category_id):
    """Foursquare API로 테마별 장소 5곳 호출 (★디버그 모드★)"""
    try:
        url = "https://api.foursquare.com/v3/places/search"
        headers = {"Authorization": api_key, "accept": "application/json"}
        params = {"ll": coords, "categories": category_id, "limit": 5, "fields": "name,location"}
        
        # --- 디버깅을 위해 요청 URL과 파라미터를 사이드바에 출력 ---
        st.sidebar.subheader("Foursquare Debug Info")
        st.sidebar.text(url)
        st.sidebar.json(params)
        # ---
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status() # 4xx, 5xx 오류가 있으면 여기서 except로 이동
        
        results = response.json().get("results", [])
        
        place_list = []
        for place in results:
            place_list.append({
                "이름": place.get("name"),
                "주소": place.get("location", {}).get("formatted_address", "주소 정보 없음")
            })
        
        st.sidebar.success("Foursquare 호출 성공") # 성공 시 메시지
        return pd.DataFrame(place_list)
    
    except requests.exceptions.RequestException as e:
        # --- (★중요★) 숨겨진 오류를 화면에 강제로 표시 ---
        st.error(f"Foursquare API 호출 실패! (디버그 정보): {e}")
        
        # 서버가 보낸 구체적인 오류 응답(JSON)을 st.json()으로 출력
        if e.response is not None:
            try:
                st.json(e.response.json())
            except:
                st.text(e.response.text) # JSON이 아닐 경우 텍스트로 표시
        # ---
        return pd.DataFrame() # 빈 DataFrame 반환

# --- 2단계 핵심 로직: 스코어링 엔진 ---

def create_data_frame(weather_json, local_holidays, kr_holidays, start_date, end_date):
    """
    모든 API 데이터를 취합하여 날짜별로 정리된 마스터 DataFrame을 생성합니다.
    """
    if not weather_json or 'daily' not in weather_json:
        return pd.DataFrame()
        
    df = pd.DataFrame(weather_json['daily'])
    df['date'] = pd.to_datetime(df['time'])
    df = df.set_index('date').drop(columns='time')
    
    # 날짜 인덱스를 'YYYY-MM-DD' 문자열로 변환하여 비교
    date_str_index = df.index.strftime('%Y-%m-%d')
    
    df['is_local_holiday'] = date_str_index.isin(local_holidays)
    df['is_kr_holiday'] = date_str_index.isin(kr_holidays)
    df['is_weekend'] = df.index.dayofweek >= 5 # 5: 토요일, 6: 일요일
    
    # '가격' 점수용: 주말이거나 한국/현지 공휴일이면 비싸다
    df['is_busy'] = df['is_local_holiday'] | df['is_kr_holiday'] | df['is_weekend']
    # '효율' 점수용: 주말이거나 한국 공휴일이면 연차를 아낄 수 있다
    df['is_free_day'] = df['is_kr_holiday'] | df['is_weekend']
    
    return df

def calculate_scores(window):
    """
    '슬라이딩 윈도우' (예: 5일치 DataFrame)를 받아 5가지 항목의 점수를 계산합니다.
    """
    scores = {}
    # 1. 날씨 (기온): 평균 최고 기온 (높을수록 좋음)
    scores['weather_temp'] = window['temperature_2m_max'].mean()
    # 2. 날씨 (강수): 총 강수량 (적을수록 좋음)
    scores['weather_rain'] = window['precipitation_sum'].sum()
    # 3. 가격 (저렴): '바쁜 날'이 적을수록 좋음 (0점이 최고점)
    scores['price_low'] = window['is_busy'].sum()
    # 4. 효율 (연차): '공짜 날'이 많을수록 좋음
    scores['efficiency'] = window['is_free_day'].sum()
    # 5. 테마 (축제): '현지 공휴일'이 많을수록 좋음
    scores['experience'] = window['is_local_holiday'].sum()
    
    return scores

def run_scoring_engine(df, trip_duration, weights):
    """
    마스터 DataFrame을 '슬라이딩 윈도우'로 순회하며 점수를 매기고 순위를 매깁니다.
    """
    results = []
    
    # '슬라이딩 윈도우' 실행 (예: 5일씩 묶어서)
    for i in range(len(df) - trip_duration + 1):
        window = df.iloc[i : i + trip_duration]
        
        scores = calculate_scores(window)
        
        # 가중치 적용: [기온, 강수, 가격, 효율, 테마]
        final_score = (
            (scores['weather_temp'] * weights[0]) +
            (scores['weather_rain'] * weights[1]) +
            (scores['price_low'] * -weights[2]) +  # '저렴' 가중치는 음수로 적용 (낮을수록 좋으니까)
            (scores['efficiency'] * weights[3]) +
            (scores['experience'] * weights[4])
        )
        
        # '작년' 날짜를 '올해/내년' 날짜로 다시 변환
        start_date = window.index[0] + pd.DateOffset(years=1)
        end_date = window.index[-1] + pd.DateOffset(years=1)
        
        results.append({
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "score": final_score,
            "details": scores
        })
        
    # 점수가 높은 순으로 정렬
    return sorted(results, key=lambda x: x['score'], reverse=True)

# --- 메인 함수 ---
def main():
    st.title("나만의 여행 비서 앱 ✈️ (MVP 2단계)")
    st.caption("과거 날씨 기반 추천 로직 (Scoring Engine) 적용")
    
    # 1. API 키 확인
    check_api_keys()

    # 2. 사용자 입력 UI (업그레이드)
    st.subheader("1. 여행 기본 정보 입력")
    
    country_name = st.selectbox("국가 선택", options=COUNTRY_MAP.keys())
    
    today = datetime.now().date()
    # 2단계: 날짜 범위는 1년까지도 가능
    date_range = st.date_input(
        "여행 희망 기간 (이 기간의 '작년' 날씨를 분석합니다)",
        value=(today + pd.DateOffset(months=3), today + pd.DateOffset(months=6))
    )
    
    trip_duration = st.number_input(
        "여행 기간 (며칠)", min_value=3, max_value=16, value=5
    )
    
    theme_name = st.selectbox("주요 테마 선택", options=THEME_MAP.keys())
    
    # 2단계: 추천 방식(간편 모드) UI 추가
    st.subheader("2. 추천 우선순위 선택")
    mode = st.radio(
        "어떤 여행을 추천해드릴까요?",
        options=WEIGHTS.keys(),
        horizontal=True
    )

    # 3. "추천받기" 버튼 로직
    if st.button("최적의 여행 기간 추천받기"):
        # 입력값 매핑
        country_data = COUNTRY_MAP[country_name]
        theme_id = THEME_MAP[theme_name]
        weights = WEIGHTS[mode]
        lat, lon = country_data["coords"].split(',')

        # 날짜 범위 확인 (1년 전으로 설정)
        start_date, end_date = date_range
        
        # (중요) 날씨 API는 작년 데이터 기준
        hist_start = start_date - pd.DateOffset(years=1)
        hist_end = end_date - pd.DateOffset(years=1)
        
        # (중요) 공휴일 API는 올해/내년 데이터 기준
        current_start = start_date
        current_end = end_date

        with st.spinner("작년 날씨와 올해 공휴일 정보를 분석 중입니다..."):
            # 1. 모든 API 데이터 호출
            weather_data = get_historical_weather(
                lat, lon, 
                hist_start.strftime('%Y-%m-%d'), 
                hist_end.strftime('%Y-%m-%d')
            )
            local_holidays = get_holidays_for_period(
                CALENDARIFIC_KEY, country_data["code"], current_start, current_end
            )
            kr_holidays = get_holidays_for_period(
                CALENDARIFIC_KEY, "KR", current_start, current_end
            )
            places_df = get_places(
                FOURSQUARE_KEY, country_data["coords"], theme_id
            )

            if not weather_data:
                st.error("날씨 데이터를 가져오는 데 실패했습니다. 잠시 후 다시 시도해주세요.")
                st.stop()

            # 2. 데이터 가공 (마스터 DataFrame 생성)
            df = create_data_frame(
                weather_data, local_holidays, kr_holidays, 
                hist_start.strftime('%Y-%m-%d'), 
                hist_end.strftime('%Y-%m-%d')
            )
            
            if df.empty:
                st.error("데이터 분석에 실패했습니다. 날짜 범위를 확인해주세요.")
                st.stop()

            # 3. 스코어링 엔진 실행
            results = run_scoring_engine(df, trip_duration, weights)
            
            if not results:
                st.warning("추천할 만한 기간을 찾지 못했습니다. 날짜 범위를 늘려보세요.")
                st.stop()

        # 4. 최종 결과 표시
        st.subheader(f"🎉 '{mode}' 기준, 최적의 여행 기간 Top 3")
        
        top_3_results = results[:3]
        
        for i, res in enumerate(top_3_results):
            with st.expander(f"**🥇 추천 {i+1}: {res['start_date']} ~ {res['end_date']}** (종합 점수: {res['score']:.0f}점)"):
                
                # 2단계: 추천 '근거' 제시
                details = res['details']
                st.write(f"**추천 근거 (작년 날씨 기준):**")
                st.markdown(f"""
                * **날씨:** 평균 최고 {details['weather_temp']:.1f}°C, {trip_duration}일 총 강수량 {details['weather_rain']:.1f}mm
                * **휴가 효율:** {trip_duration}일 중 **{int(details['efficiency'])}일**이 주말/한국 공휴일입니다. (연차 절약!)
                * **현지 상황:** {trip_duration}일 중 **{int(details['experience'])}일**이 현지 공휴일(축제)입니다.
                * **가격:** {trip_duration}일 중 **{int(details['price_low'])}일**이 주말/공휴일과 겹칩니다. (낮을수록 한적/저렴)
                """)
                
                # Foursquare 관광지 정보 표시
                if not places_df.empty:
                    st.write(f"**'{theme_name}' 테마 추천 장소:**")
                    st.dataframe(places_df)
                else:
                    st.warning("추천 장소 정보를 가져오지 못했습니다.")

if __name__ == "__main__":
    main()
