import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- 설정 및 데이터 ---
# 더 많은 도시 추가 (다구간 여행 테스트용)
COUNTRY_MAP = {
    "🇯🇵 일본 (도쿄)": {"code": "JP", "city_name": "Tokyo", "coords": "35.6895,139.6917"},
    "🇯🇵 일본 (오사카)": {"code": "JP", "city_name": "Osaka", "coords": "34.6937,135.5023"},
    "🇻🇳 베트남 (하노이)": {"code": "VN", "city_name": "Hanoi", "coords": "21.0285,105.8542"},
    "🇻🇳 베트남 (다낭)": {"code": "VN", "city_name": "Da Nang", "coords": "16.0544,108.2022"},
    "🇹🇭 태국 (방콕)": {"code": "TH", "city_name": "Bangkok", "coords": "13.7563,100.5018"},
    "🇹🇼 대만 (타이베이)": {"code": "TW", "city_name": "Taipei", "coords": "25.0330,121.5654"},
    "🇰🇷 한국 (서울)": {"code": "KR", "city_name": "Seoul", "coords": "37.5665,126.9780"}
}

THEME_OSM_MAP = {
    "미식 🍜": '"amenity"="restaurant"',
    "쇼핑 🛍️": '"shop"="mall"',
    "문화/유적 🏯": '"tourism"="attraction"',
    "휴양/공원 🌳": '"leisure"="park"'
}

# 추천 가중치
WEIGHTS = {
    "가장 저렴하고 한적하게": [ 1, -1, 10,  1, -5],
    "연차 아껴서 알차게":   [ 1, -1, -5, 10,  1],
    "테마와 날씨가 완벽하게": [10, -5,  1,  1, 10]
}

# --- API 키 로드 ---
CALENDARIFIC_KEY = st.secrets.get("calendarific_key")

def check_api_keys():
    if not CALENDARIFIC_KEY:
        st.sidebar.error("⚠️ Calendarific API 키가 설정되지 않았습니다.")
        st.stop()

# --- 공통 API 함수 ---

@st.cache_data(ttl=3600)
def get_holidays_for_period(api_key, country_code, start_date, end_date):
    """Calendarific API: 선택한 기간의 공휴일"""
    all_holidays = set()
    # 날짜 범위가 길 수 있으므로 월별로 순회
    for month_start in pd.date_range(start_date, end_date, freq='MS'):
        try:
            url = "https://calendarific.com/api/v2/holidays"
            params = {
                "api_key": api_key, "country": country_code, 
                "year": month_start.year, "month": month_start.month
            }
            res = requests.get(url, params=params)
            if res.status_code == 200:
                holidays = res.json().get("response", {}).get("holidays", [])
                for h in holidays:
                    iso = h.get("date", {}).get("iso", "")
                    if iso: all_holidays.add(iso.split("T")[0])
        except: pass
    return all_holidays

@st.cache_data(ttl=3600)
def get_historical_weather(latitude, longitude, start_date, end_date):
    """Open-Meteo API: 과거 날씨 데이터"""
    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": latitude, "longitude": longitude,
            "start_date": start_date, "end_date": end_date,
            "daily": "temperature_2m_max,precipitation_sum",
            "timezone": "auto"
        }
        res = requests.get(url, params=params)
        res.raise_for_status()
        return res.json()
    except: return None

@st.cache_data(ttl=3600)
def get_places_osm(lat, lon, osm_tag):
    """OpenStreetMap: 주변 장소 검색"""
    try:
        overpass_url = "http://overpass-api.de/api/interpreter"
        query = f"""
        [out:json];
        (node[{osm_tag}](around:3000, {lat}, {lon});
         way[{osm_tag}](around:3000, {lat}, {lon}););
        out center 5; 
        """
        res = requests.get(overpass_url, params={'data': query})
        res.raise_for_status()
        data = res.json()
        
        places = []
        for el in data.get('elements', []):
            name = el.get('tags', {}).get('name')
            if name:
                lat = el.get('lat') or el.get('center', {}).get('lat')
                lon = el.get('lon') or el.get('center', {}).get('lon')
                places.append({"이름": name, "위치": f"{lat}, {lon}"})
        return pd.DataFrame(places)
    except: return pd.DataFrame()

# --- 데이터 처리 엔진 ---

def create_base_dataframe(weather_json, start_date, end_date):
    if not weather_json or 'daily' not in weather_json: return pd.DataFrame()
    df = pd.DataFrame(weather_json['daily'])
    df['date'] = pd.to_datetime(df['time'])
    df = df.set_index('date').drop(columns='time')
    return df

def calculate_daily_score(df, local_holidays, kr_holidays):
    """일별 점수 계산 (벡터 연산)"""
    date_str = df.index.strftime('%Y-%m-%d')
    df['is_local_holiday'] = date_str.isin(local_holidays)
    df['is_kr_holiday'] = date_str.isin(kr_holidays)
    df['is_weekend'] = df.index.dayofweek >= 5
    
    # 점수 요소 계산
    # 1. 날씨 점수 (20~25도가 최고, 비오면 감점)
    df['score_weather'] = 10 - abs(df['temperature_2m_max'] - 23) # 23도 기준
    df['score_rain'] = -df['precipitation_sum'] * 2 # 비 1mm당 2점 감점
    
    # 2. 효율/가격/테마 (단순화된 로직)
    df['score_busy'] = (df['is_local_holiday'] | df['is_weekend']).astype(int) * -5
    df['score_free'] = (df['is_kr_holiday'] | df['is_weekend']).astype(int) * 5
    
    # 종합 점수 (단순 합산)
    df['total_score'] = df['score_weather'] + df['score_rain'] + df['score_busy'] + df['score_free']
    return df

# --- 모드 1: 개인 맞춤형 (기존 로직) ---
def run_mode_single_trip():
    st.header("🎯 모드 1: 개인 맞춤형 여행 추천")
    st.caption("한 도시를 깊이 있게 여행하고 싶을 때, 최적의 날짜를 찾아드립니다.")

    col1, col2 = st.columns(2)
    with col1:
        country_key = st.selectbox("어디로 떠날까요?", options=COUNTRY_MAP.keys())
    with col2:
        theme_name = st.selectbox("여행 테마는?", options=THEME_OSM_MAP.keys())

    today = datetime.now().date()
    date_range = st.date_input(
        "언제쯤 가고 싶으신가요? (기간 설정)",
        value=(today + timedelta(days=90), today + timedelta(days=120))
    )
    trip_duration = st.slider("여행 기간 (박)", 3, 14, 5)

    if st.button("최적 날짜 찾기", type="primary"):
        if len(date_range) < 2: st.error("기간을 정확히 선택해주세요."); st.stop()
        
        country_data = COUNTRY_MAP[country_key]
        lat, lon = country_data["coords"].split(',')
        start_date, end_date = date_range
        
        # 작년 날씨 가져오기
        hist_start = start_date - pd.DateOffset(years=1)
        hist_end = end_date - pd.DateOffset(years=1)
        
        with st.spinner("데이터 분석 중..."):
            weather = get_historical_weather(lat, lon, hist_start.strftime('%Y-%m-%d'), hist_end.strftime('%Y-%m-%d'))
            local_h = get_holidays_for_period(CALENDARIFIC_KEY, country_data["code"], start_date, end_date)
            kr_h = get_holidays_for_period(CALENDARIFIC_KEY, "KR", start_date, end_date)
            places = get_places_osm(lat, lon, THEME_OSM_MAP[theme_name])
            
            df = create_base_dataframe(weather, hist_start, hist_end)
            if df.empty: st.error("날씨 데이터 없음"); st.stop()
            
            # 점수 계산 및 윈도우 합산
            df = calculate_daily_score(df, local_h, kr_h)
            
            best_periods = []
            for i in range(len(df) - trip_duration + 1):
                window = df.iloc[i : i + trip_duration]
                score = window['total_score'].mean()
                start = window.index[0] + pd.DateOffset(years=1)
                end = window.index[-1] + pd.DateOffset(years=1)
                best_periods.append({"start": start, "end": end, "score": score, "window": window})
            
            best_periods.sort(key=lambda x: x['score'], reverse=True)
            
            # 결과 출력
            top = best_periods[0]
            st.success(f"🏆 추천 일정: {top['start'].strftime('%Y-%m-%d')} ~ {top['end'].strftime('%Y-%m-%d')}")
            
            col_a, col_b = st.columns([1, 1])
            with col_a:
                st.metric("예상 평균 기온", f"{top['window']['temperature_2m_max'].mean():.1f}°C")
                st.metric("예상 강수량", f"{top['window']['precipitation_sum'].sum():.1f}mm")
            with col_b:
                st.write("**추천 장소:**")
                st.dataframe(places, hide_index=True)

# --- 모드 2: 다구간/장기 여행 (신규 로직) ---
def run_mode_multi_trip():
    st.header("🌏 모드 2: 다구간 효율적 일정 짜기")
    st.caption("여러 도시를 여행할 때, '어느 도시를 먼저 가는 게 좋을지' 날씨와 시즌을 비교해드립니다.")

    selected_countries = st.multiselect(
        "방문하고 싶은 도시들을 모두 선택하세요 (2개 이상)",
        options=COUNTRY_MAP.keys(),
        default=[list(COUNTRY_MAP.keys())[0], list(COUNTRY_MAP.keys())[2]]
    )

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("여행 시작 가능일", value=datetime.now().date() + timedelta(days=30))
    with col2:
        total_months = st.slider("전체 여행 가능 기간 (개월)", 1, 6, 3)

    end_date = start_date + pd.DateOffset(months=total_months)
    
    if st.button("도시별 최적 시기 비교하기", type="primary"):
        if len(selected_countries) < 2:
            st.warning("비교를 위해 2개 이상의 도시를 선택해주세요.")
            st.stop()
            
        # 차트용 데이터 수집
        comparison_data = []
        
        progress_bar = st.progress(0)
        
        hist_start = start_date - pd.DateOffset(years=1)
        hist_end = end_date - pd.DateOffset(years=1)
        
        for idx, country_key in enumerate(selected_countries):
            data = COUNTRY_MAP[country_key]
            lat, lon = data["coords"].split(',')
            
            weather = get_historical_weather(lat, lon, hist_start.strftime('%Y-%m-%d'), hist_end.strftime('%Y-%m-%d'))
            df = create_base_dataframe(weather, hist_start, hist_end)
            
            if not df.empty:
                # 쾌적도 점수만 계산 (이동 평균)
                # 23도에 가까울수록, 비가 안 올수록 높은 점수
                df['score'] = (10 - abs(df['temperature_2m_max'] - 23)) - (df['precipitation_sum'] * 0.5)
                # 7일 이동평균선 (부드러운 그래프를 위해)
                df['smooth_score'] = df['score'].rolling(window=7).mean()
                
                # 날짜를 올해/내년으로 변환하여 차트에 추가
                for date, row in df.iterrows():
                    current_date = date + pd.DateOffset(years=1)
                    if not pd.isna(row['smooth_score']):
                        comparison_data.append({
                            "날짜": current_date,
                            "도시": data["city_name"], # 영어 이름으로 표시 (차트 가독성)
                            "여행 적합도": row['smooth_score']
                        })
            
            progress_bar.progress((idx + 1) / len(selected_countries))

        if comparison_data:
            st.divider()
            st.subheader("📊 도시별 여행 적합도 흐름")
            st.info("그래프가 **높을수록** 여행하기 좋은 날씨(맑고 쾌적함)입니다. 그래프가 교차하는 지점을 보고 이동 순서를 정해보세요!")
            
            chart_df = pd.DataFrame(comparison_data)
            
            # 라인 차트로 시각화
            st.line_chart(
                chart_df,
                x="날짜",
                y="여행 적합도",
                color="도시",
                height=400
            )
            
            # 간단한 조언 생성
            st.subheader("💡 AI의 일정 조언")
            best_days = chart_df.loc[chart_df.groupby("도시")["여행 적합도"].idxmax()]
            best_days = best_days.sort_values("날짜")
            
            st.write("날씨 데이터를 기반으로 추천하는 방문 순서는 다음과 같습니다:")
            order_str = ""
            for _, row in best_days.iterrows():
                date_str = row['날짜'].strftime('%Y년 %m월')
                st.markdown(f"- **{row['도시']}**: {date_str} 경에 최고점 도달")
        else:
            st.error("데이터를 불러오지 못했습니다.")

# --- 메인 앱 실행 ---
def main():
    st.set_page_config(page_title="Travel Planner AI", page_icon="✈️")
    
    check_api_keys()
    
    with st.sidebar:
        st.title("✈️ 여행 비서 AI")
        st.write("원하는 모드를 선택하세요.")
        app_mode = st.radio(
            "선택 메뉴",
            ["개인 맞춤형 (Single)", "다구간 효율 (Multi)"],
            index=0
        )
        st.divider()
        st.markdown("**API Status**")
        st.success("Calendarific ✅")
        st.success("Open-Meteo ✅")
        st.success("OpenStreetMap ✅")

    if app_mode == "개인 맞춤형 (Single)":
        run_mode_single_trip()
    elif app_mode == "다구간 효율 (Multi)":
        run_mode_multi_trip()

if __name__ == "__main__":
    main()
