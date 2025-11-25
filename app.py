import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 전 세계 주요 도시 데이터 (확장됨) ---
COUNTRY_MAP = {
    # 아시아
    "🇯🇵 일본 (도쿄)": {"code": "JP", "city_name": "Tokyo", "coords": "35.6895,139.6917"},
    "🇯🇵 일본 (오사카)": {"code": "JP", "city_name": "Osaka", "coords": "34.6937,135.5023"},
    "🇯🇵 일본 (후쿠오카)": {"code": "JP", "city_name": "Fukuoka", "coords": "33.5904,130.4017"},
    "🇯🇵 일본 (삿포로)": {"code": "JP", "city_name": "Sapporo", "coords": "43.0618,141.3545"},
    "🇻🇳 베트남 (하노이)": {"code": "VN", "city_name": "Hanoi", "coords": "21.0285,105.8542"},
    "🇻🇳 베트남 (다낭)": {"code": "VN", "city_name": "Da Nang", "coords": "16.0544,108.2022"},
    "🇻🇳 베트남 (호치민)": {"code": "VN", "city_name": "Ho Chi Minh", "coords": "10.8231,106.6297"},
    "🇹🇭 태국 (방콕)": {"code": "TH", "city_name": "Bangkok", "coords": "13.7563,100.5018"},
    "🇹🇭 태국 (치앙마이)": {"code": "TH", "city_name": "Chiang Mai", "coords": "18.7061,98.9817"},
    "🇹🇼 대만 (타이베이)": {"code": "TW", "city_name": "Taipei", "coords": "25.0330,121.5654"},
    "🇸🇬 싱가포르": {"code": "SG", "city_name": "Singapore", "coords": "1.3521,103.8198"},
    "🇭🇰 홍콩": {"code": "HK", "city_name": "Hong Kong", "coords": "22.3193,114.1694"},
    "🇮🇩 인도네시아 (발리)": {"code": "ID", "city_name": "Bali", "coords": "-8.4095,115.1889"},
    "🇰🇷 한국 (서울)": {"code": "KR", "city_name": "Seoul", "coords": "37.5665,126.9780"},
    
    # 유럽
    "🇫🇷 프랑스 (파리)": {"code": "FR", "city_name": "Paris", "coords": "48.8566,2.3522"},
    "🇬🇧 영국 (런던)": {"code": "GB", "city_name": "London", "coords": "51.5074,-0.1278"},
    "🇮🇹 이탈리아 (로마)": {"code": "IT", "city_name": "Rome", "coords": "41.9028,12.4964"},
    "🇮🇹 이탈리아 (베네치아)": {"code": "IT", "city_name": "Venice", "coords": "45.4408,12.3155"},
    "🇪🇸 스페인 (바르셀로나)": {"code": "ES", "city_name": "Barcelona", "coords": "41.3851,2.1734"},
    "🇨🇭 스위스 (취리히)": {"code": "CH", "city_name": "Zurich", "coords": "47.3769,8.5417"},
    "🇨🇿 체코 (프라하)": {"code": "CZ", "city_name": "Prague", "coords": "50.0755,14.4378"},
    
    # 미주/오세아니아
    "🇺🇸 미국 (뉴욕)": {"code": "US", "city_name": "New York", "coords": "40.7128,-74.0060"},
    "🇺🇸 미국 (LA)": {"code": "US", "city_name": "Los Angeles", "coords": "34.0522,-118.2437"},
    "🇺🇸 미국 (하와이 호놀룰루)": {"code": "US", "city_name": "Honolulu", "coords": "21.3069,-157.8583"},
    "🇨🇦 캐나다 (밴쿠버)": {"code": "CA", "city_name": "Vancouver", "coords": "49.2827,-123.1207"},
    "🇦🇺 호주 (시드니)": {"code": "AU", "city_name": "Sydney", "coords": "-33.8688,151.2093"},
    "🇬🇺 괌": {"code": "GU", "city_name": "Guam", "coords": "13.4443,144.7937"}
}

THEME_OSM_MAP = {
    "미식 🍜": '"amenity"="restaurant"',
    "쇼핑 🛍️": '"shop"="mall"',
    "문화/유적 🏯": '"tourism"="attraction"',
    "휴양/공원 🌳": '"leisure"="park"'
}

# --- 2. API 키 확인 ---
CALENDARIFIC_KEY = st.secrets.get("calendarific_key")

def check_api_keys():
    if not CALENDARIFIC_KEY:
        st.sidebar.error("⚠️ Calendarific API 키가 설정되지 않았습니다.")
        st.stop()

# --- 3. 공통 API 함수 ---

@st.cache_data(ttl=3600)
def get_holidays_for_period(api_key, country_code, start_date, end_date):
    """Calendarific API: 선택한 기간의 공휴일"""
    all_holidays = set()
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
    """(수정됨) OpenStreetMap: 구글 지도 링크 생성"""
    try:
        overpass_url = "http://overpass-api.de/api/interpreter"
        query = f"""
        [out:json];
        (node[{osm_tag}](around:3000, {lat}, {lon});
         way[{osm_tag}](around:3000, {lat}, {lon}););
        out center 10; 
        """
        res = requests.get(overpass_url, params={'data': query})
        res.raise_for_status()
        data = res.json()
        
        places = []
        for el in data.get('elements', []):
            name = el.get('tags', {}).get('name')
            if name:
                p_lat = el.get('lat') or el.get('center', {}).get('lat')
                p_lon = el.get('lon') or el.get('center', {}).get('lon')
                
                # 좌표 대신 구글 맵 링크 생성
                map_link = f"https://www.google.com/maps/search/?api=1&query={p_lat},{p_lon}"
                
                places.append({
                    "장소명": name,
                    "지도 보기": map_link # LinkColumn으로 표시할 데이터
                })
        return pd.DataFrame(places)
    except: return pd.DataFrame()

# --- 4. 데이터 처리 엔진 ---

def create_base_dataframe(weather_json, start_date, end_date):
    if not weather_json or 'daily' not in weather_json: return pd.DataFrame()
    df = pd.DataFrame(weather_json['daily'])
    df['date'] = pd.to_datetime(df['time'])
    df = df.set_index('date').drop(columns='time')
    return df

def calculate_daily_score(df, local_holidays, kr_holidays):
    """일별 점수 계산"""
    date_str = df.index.strftime('%Y-%m-%d')
    df['is_local_holiday'] = date_str.isin(local_holidays)
    df['is_kr_holiday'] = date_str.isin(kr_holidays)
    df['is_weekend'] = df.index.dayofweek >= 5
    
    # 점수: 23도 근처면 고득점, 비오면 감점
    df['score_weather'] = 10 - abs(df['temperature_2m_max'] - 23)
    df['score_rain'] = -df['precipitation_sum'] * 2
    
    # 붐빔/효율 점수
    df['score_busy'] = (df['is_local_holiday'] | df['is_weekend']).astype(int) * -5
    df['score_free'] = (df['is_kr_holiday'] | df['is_weekend']).astype(int) * 5
    
    df['total_score'] = df['score_weather'] + df['score_rain'] + df['score_busy'] + df['score_free']
    return df

# --- 모드 1: 개인 맞춤형 (Top 3 추천) ---
def run_mode_single_trip():
    st.header("🎯 모드 1: 개인 맞춤형 여행 추천")
    st.caption("전 세계 주요 도시 중 한 곳을 골라 최적의 여행 시기 3개를 추천해드립니다.")

    col1, col2 = st.columns(2)
    with col1:
        country_key = st.selectbox("어디로 떠날까요?", options=COUNTRY_MAP.keys())
    with col2:
        theme_name = st.selectbox("여행 테마는?", options=THEME_OSM_MAP.keys())

    today = datetime.now().date()
    date_range = st.date_input(
        "여행 희망 범위 (최대 1년 이내)",
        value=(today + timedelta(days=30), today + timedelta(days=90))
    )
    trip_duration = st.slider("여행 기간 (박)", 3, 14, 5)

    if st.button("최적 일정 Top 3 찾기", type="primary"):
        if len(date_range) < 2: st.error("기간을 정확히 선택해주세요."); st.stop()
        
        country_data = COUNTRY_MAP[country_key]
        lat, lon = country_data["coords"].split(',')
        start_date, end_date = date_range
        
        # 작년 날씨 분석
        hist_start = start_date - pd.DateOffset(years=1)
        hist_end = end_date - pd.DateOffset(years=1)
        
        with st.spinner(f"{country_key}의 데이터를 분석 중입니다..."):
            weather = get_historical_weather(lat, lon, hist_start.strftime('%Y-%m-%d'), hist_end.strftime('%Y-%m-%d'))
            local_h = get_holidays_for_period(CALENDARIFIC_KEY, country_data["code"], start_date, end_date)
            kr_h = get_holidays_for_period(CALENDARIFIC_KEY, "KR", start_date, end_date)
            
            # (수정) OSM 장소 데이터 (지도 링크 포함)
            places_df = get_places_osm(lat, lon, THEME_OSM_MAP[theme_name])
            
            df = create_base_dataframe(weather, hist_start, hist_end)
            if df.empty: st.error("날씨 데이터가 없습니다."); st.stop()
            
            df = calculate_daily_score(df, local_h, kr_h)
            
            # 슬라이딩 윈도우로 점수 매기기
            best_periods = []
            for i in range(len(df) - trip_duration + 1):
                window = df.iloc[i : i + trip_duration]
                score = window['total_score'].mean()
                start = window.index[0] + pd.DateOffset(years=1)
                end = window.index[-1] + pd.DateOffset(years=1)
                best_periods.append({"start": start, "end": end, "score": score, "window": window})
            
            # 점수순 정렬 후 상위 3개 추출
            best_periods.sort(key=lambda x: x['score'], reverse=True)
            top_3 = best_periods[:3]
            
            if not top_3:
                st.warning("추천할 만한 기간을 찾지 못했습니다.")
                st.stop()

            st.divider()
            st.subheader(f"🏆 {country_key} 추천 일정 Best 3")
            
            # (수정) Top 3 반복 출력
            for i, period in enumerate(top_3):
                p_start = period['start'].strftime('%Y-%m-%d')
                p_end = period['end'].strftime('%Y-%m-%d')
                score = period['score']
                temp_avg = period['window']['temperature_2m_max'].mean()
                rain_sum = period['window']['precipitation_sum'].sum()
                
                # 이모지 선정
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else ""
                
                with st.expander(f"{medal} {i+1}순위: {p_start} ~ {p_end} (종합 점수: {score:.0f}점)", expanded=(i==0)):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("예상 평균 기온", f"{temp_avg:.1f}°C")
                    c2.metric("예상 총 강수량", f"{rain_sum:.1f}mm")
                    
                    # 주말/공휴일 개수 세기
                    free_days = period['window']['is_free_day'].sum()
                    c3.metric("연휴/주말 포함", f"{free_days}일")
                    
                    st.write("---")
                    st.markdown(f"**🗺️ '{theme_name}' 테마 추천 장소** (클릭하여 위치 확인)")
                    
                    if not places_df.empty:
                        # (수정) 데이터프레임에 링크 기능 적용
                        st.dataframe(
                            places_df,
                            column_config={
                                "지도 보기": st.column_config.LinkColumn(
                                    "구글 지도", display_text="📍 지도 열기"
                                )
                            },
                            hide_index=True
                        )
                    else:
                        st.info("주변 장소 데이터를 찾지 못했습니다.")

# --- 모드 2: 다구간/장기 여행 ---
def run_mode_multi_trip():
    st.header("🌏 모드 2: 다구간 효율적 일정 짜기")
    st.caption("여러 도시를 여행할 때, 최적의 이동 순서를 제안합니다.")

    selected_countries = st.multiselect(
        "방문하고 싶은 도시들을 모두 선택하세요 (2개 이상)",
        options=COUNTRY_MAP.keys(),
        default=[list(COUNTRY_MAP.keys())[0], list(COUNTRY_MAP.keys())[4]] # 도쿄, 하노이
    )

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("여행 시작 가능일", value=datetime.now().date() + timedelta(days=30))
    with col2:
        total_months = st.slider("전체 여행 가능 기간 (개월)", 1, 6, 3)

    end_date = start_date + pd.DateOffset(months=total_months)
    
    if st.button("도시별 최적 시기 비교하기", type="primary"):
        if len(selected_countries) < 2:
            st.warning("2개 이상의 도시를 선택해주세요."); st.stop()
            
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
                # 쾌적도 점수 (이동 평균)
                df['score'] = (10 - abs(df['temperature_2m_max'] - 23)) - (df['precipitation_sum'] * 0.5)
                df['smooth_score'] = df['score'].rolling(window=7).mean()
                
                for date, row in df.iterrows():
                    current_date = date + pd.DateOffset(years=1)
                    if not pd.isna(row['smooth_score']):
                        comparison_data.append({
                            "날짜": current_date,
                            "도시": data["city_name"],
                            "여행 적합도": row['smooth_score']
                        })
            progress_bar.progress((idx + 1) / len(selected_countries))

        if comparison_data:
            st.divider()
            chart_df = pd.DataFrame(comparison_data)
            st.line_chart(chart_df, x="날짜", y="여행 적합도", color="도시", height=400)
            
            st.subheader("💡 AI의 일정 조언")
            best_days = chart_df.loc[chart_df.groupby("도시")["여행 적합도"].idxmax()].sort_values("날짜")
            
            st.write("다음 순서로 이동하면 가장 쾌적한 날씨를 즐길 수 있습니다:")
            for _, row in best_days.iterrows():
                date_str = row['날짜'].strftime('%Y년 %m월')
                st.markdown(f"- **{row['도시']}**: {date_str} 추천 (날씨 쾌적도 최고)")
        else:
            st.error("데이터 부족")

# --- 메인 앱 실행 ---
def main():
    st.set_page_config(page_title="Travel Planner AI", page_icon="✈️", layout="wide")
    check_api_keys()
    
    with st.sidebar:
        st.title("✈️ 여행 비서 AI")
        app_mode = st.radio("선택 메뉴", ["개인 맞춤형 (Single)", "다구간 효율 (Multi)"])
        st.info("지원 도시: 아시아, 유럽, 미주 등 전 세계 30개 주요 도시")
        st.success("Calendarific / Open-Meteo / OpenStreetMap 연동")

    if app_mode == "개인 맞춤형 (Single)":
        run_mode_single_trip()
    elif app_mode == "다구간 효율 (Multi)":
        run_mode_multi_trip()

if __name__ == "__main__":
    main()
