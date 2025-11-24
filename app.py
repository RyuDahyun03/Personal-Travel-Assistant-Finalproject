import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- 상수 정의 ---
COUNTRY_MAP = {
    "일본": {"code": "JP", "city_name": "Tokyo", "coords": "35.6895,139.6917"},
    "베트남": {"code": "VN", "city_name": "Hanoi", "coords": "21.0285,105.8542"}
}

# (변경) OSM 태그 매핑: OpenStreetMap은 'Key=Value' 형태로 검색합니다.
THEME_OSM_MAP = {
    "미식": '"amenity"="restaurant"',      # 식당
    "쇼핑": '"shop"="mall"',              # 쇼핑몰/상점
    "문화/유적": '"tourism"="attraction"'   # 관광 명소
}

# 추천 모드별 가중치 설정
WEIGHTS = {
    "가장 저렴하고 한적하게": [ 1, -1, 10,  1, -5],
    "연차 아껴서 알차게":   [ 1, -1, -5, 10,  1],
    "테마와 날씨가 완벽하게": [10, -5,  1,  1, 10]
}

# --- API 키 로드 ---
# Foursquare 키는 더 이상 필요하지 않습니다.
CALENDARIFIC_KEY = st.secrets.get("calendarific_key")

def check_api_keys():
    st.sidebar.title("🔑 API 키 상태")
    st.sidebar.info("`.streamlit/secrets.toml` 파일을 확인하세요.")
    
    # Calendarific 키만 확인
    st.sidebar.markdown(f"Calendarific: {'✅' if CALENDARIFIC_KEY else '❌'}")
    
    # 무료 API 안내
    st.sidebar.success("날씨(Open-Meteo) & 관광지(OSM)는 API 키가 필요 없습니다! 🎉")
    
    if not CALENDARIFIC_KEY:
        st.error("Calendarific API 키가 설정되지 않았습니다.")
        st.stop()

# --- API 호출 함수 ---

@st.cache_data(ttl=3600)
def get_holidays_for_period(api_key, country_code, start_date, end_date):
    """Calendarific API: 선택한 기간의 공휴일"""
    all_holidays = set()
    for month_start in pd.date_range(start_date, end_date, freq='MS'):
        year = month_start.year
        month = month_start.month
        try:
            url = "https://calendarific.com/api/v2/holidays"
            params = {"api_key": api_key, "country": country_code, "year": year, "month": month}
            response = requests.get(url, params=params)
            if response.status_code == 200:
                holidays = response.json().get("response", {}).get("holidays", [])
                for holiday in holidays:
                    iso_date = holiday.get("date", {}).get("iso", "")
                    if iso_date:
                        all_holidays.add(iso_date.split("T")[0])
        except:
            pass
    return all_holidays

@st.cache_data(ttl=3600)
def get_historical_weather(latitude, longitude, start_date, end_date):
    """Open-Meteo API: 과거 날씨 데이터"""
    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_max,precipitation_sum",
            "timezone": "auto"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

@st.cache_data(ttl=3600)
def get_places_osm(lat, lon, osm_tag):
    """(신규) OpenStreetMap(Overpass API)으로 주변 장소 검색"""
    try:
        # Overpass QL 쿼리 작성 (반경 3km 내 검색)
        overpass_url = "http://overpass-api.de/api/interpreter"
        query = f"""
        [out:json];
        (
          node[{osm_tag}](around:3000, {lat}, {lon});
          way[{osm_tag}](around:3000, {lat}, {lon});
        );
        out center 5; 
        """
        # 'out center 5;' -> 중심점 좌표 포함하여 상위 5개만 출력
        
        response = requests.get(overpass_url, params={'data': query})
        response.raise_for_status()
        data = response.json()
        
        place_list = []
        for element in data.get('elements', []):
            name = element.get('tags', {}).get('name')
            # 이름이 있는 장소만 가져오기
            if name:
                # 위도/경도 정보 추출 (Node는 lat/lon, Way는 center 사용)
                p_lat = element.get('lat') or element.get('center', {}).get('lat')
                p_lon = element.get('lon') or element.get('center', {}).get('lon')
                
                place_list.append({
                    "이름": name,
                    "위치(좌표)": f"{p_lat}, {p_lon}",
                    "유형": element.get('tags', {}).get('amenity') or element.get('tags', {}).get('tourism') or "장소"
                })
        
        return pd.DataFrame(place_list)
        
    except Exception as e:
        st.sidebar.error(f"OSM API 오류: {e}")
        return pd.DataFrame()

# --- 스코어링 엔진 ---

def create_data_frame(weather_json, local_holidays, kr_holidays, start_date, end_date):
    if not weather_json or 'daily' not in weather_json:
        return pd.DataFrame()
    df = pd.DataFrame(weather_json['daily'])
    df['date'] = pd.to_datetime(df['time'])
    df = df.set_index('date').drop(columns='time')
    
    date_str_index = df.index.strftime('%Y-%m-%d')
    df['is_local_holiday'] = date_str_index.isin(local_holidays)
    df['is_kr_holiday'] = date_str_index.isin(kr_holidays)
    df['is_weekend'] = df.index.dayofweek >= 5
    df['is_busy'] = df['is_local_holiday'] | df['is_kr_holiday'] | df['is_weekend']
    df['is_free_day'] = df['is_kr_holiday'] | df['is_weekend']
    return df

def run_scoring_engine(df, trip_duration, weights):
    results = []
    for i in range(len(df) - trip_duration + 1):
        window = df.iloc[i : i + trip_duration]
        
        score_temp = window['temperature_2m_max'].mean()
        score_rain = window['precipitation_sum'].sum()
        score_price = window['is_busy'].sum()
        score_eff = window['is_free_day'].sum()
        score_exp = window['is_local_holiday'].sum()
        
        final_score = (
            (score_temp * weights[0]) +
            (score_rain * weights[1]) +
            (score_price * -weights[2]) +
            (score_eff * weights[3]) +
            (score_exp * weights[4])
        )
        
        start_date = window.index[0] + pd.DateOffset(years=1)
        end_date = window.index[-1] + pd.DateOffset(years=1)
        
        results.append({
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "score": final_score,
            "details": {
                "temp": score_temp, "rain": score_rain,
                "eff": score_eff, "exp": score_exp, "price": score_price
            }
        })
    return sorted(results, key=lambda x: x['score'], reverse=True)

# --- 메인 함수 ---
def main():
    st.title("나만의 여행 비서 앱 ✈️ (OSM 버전)")
    st.caption("Foursquare 대신 완전 무료 OpenStreetMap 사용")
    
    check_api_keys()

    st.subheader("1. 여행 기본 정보 입력")
    country_name = st.selectbox("국가 선택", options=COUNTRY_MAP.keys())
    
    today = datetime.now().date()
    date_range = st.date_input(
        "여행 희망 기간 (작년 날씨 분석)",
        value=(today + pd.DateOffset(months=3), today + pd.DateOffset(months=6))
    )
    trip_duration = st.number_input("여행 기간 (일)", 3, 16, 5)
    theme_name = st.selectbox("주요 테마 선택", options=THEME_OSM_MAP.keys())
    
    st.subheader("2. 추천 우선순위 선택")
    mode = st.radio("추천 모드", options=WEIGHTS.keys(), horizontal=True)

    if st.button("최적의 여행 기간 추천받기"):
        country_data = COUNTRY_MAP[country_name]
        osm_tag = THEME_OSM_MAP[theme_name]
        weights = WEIGHTS[mode]
        lat, lon = country_data["coords"].split(',')

        if not date_range or len(date_range) < 2:
            st.error("날짜 범위를 선택해주세요.")
            st.stop()
            
        start_date, end_date = date_range
        hist_start = start_date - pd.DateOffset(years=1)
        hist_end = end_date - pd.DateOffset(years=1)

        with st.spinner("데이터 분석 및 관광지 검색 중..."):
            # API 호출
            weather_data = get_historical_weather(lat, lon, hist_start.strftime('%Y-%m-%d'), hist_end.strftime('%Y-%m-%d'))
            local_holidays = get_holidays_for_period(CALENDARIFIC_KEY, country_data["code"], start_date, end_date)
            kr_holidays = get_holidays_for_period(CALENDARIFIC_KEY, "KR", start_date, end_date)
            
            # (변경) OSM 호출
            places_df = get_places_osm(lat, lon, osm_tag)

            if not weather_data:
                st.error("날씨 데이터 오류")
                st.stop()

            df = create_data_frame(weather_data, local_holidays, kr_holidays, hist_start.strftime('%Y-%m-%d'), hist_end.strftime('%Y-%m-%d'))
            results = run_scoring_engine(df, trip_duration, weights)
            
            if not results:
                st.warning("적절한 기간을 찾지 못했습니다.")
                st.stop()

        # 결과 표시
        st.subheader(f"🎉 '{mode}' Top 3 추천")
        for i, res in enumerate(results[:3]):
            d = res['details']
            with st.expander(f"🥇 {i+1}위: {res['start_date']} ~ {res['end_date']} ({res['score']:.0f}점)"):
                st.write(f"**날씨:** {d['temp']:.1f}°C / 강수 {d['rain']:.1f}mm")
                st.write(f"**효율:** 연차 절약 {int(d['eff'])}일, 축제 {int(d['exp'])}일")
                
                if not places_df.empty:
                    st.write(f"**🗺️ 주변 '{theme_name}' 추천 장소 (OpenStreetMap):**")
                    st.dataframe(places_df)
                else:
                    st.info("주변에 해당 테마의 장소 데이터가 없습니다.")

if __name__ == "__main__":
    main()
