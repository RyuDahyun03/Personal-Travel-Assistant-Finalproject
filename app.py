import streamlit as st
import requests
import pandas as pd
import math
from datetime import datetime, timedelta

# --- 1. 전 세계 주요 도시 데이터 ---
CITY_DATA = {
    # [동북아시아]
    "🇯🇵 일본 (도쿄)": {"code": "JP", "city": "Tokyo", "coords": "35.6895,139.6917", "country": "일본"},
    "🇯🇵 일본 (오사카)": {"code": "JP", "city": "Osaka", "coords": "34.6937,135.5023", "country": "일본"},
    "🇯🇵 일본 (후쿠오카)": {"code": "JP", "city": "Fukuoka", "coords": "33.5904,130.4017", "country": "일본"},
    "🇯🇵 일본 (삿포로)": {"code": "JP", "city": "Sapporo", "coords": "43.0618,141.3545", "country": "일본"},
    "🇯🇵 일본 (오키나와)": {"code": "JP", "city": "Naha", "coords": "26.2124,127.6809", "country": "일본"},
    "🇰🇷 한국 (서울)": {"code": "KR", "city": "Seoul", "coords": "37.5665,126.9780", "country": "한국"},
    "🇰🇷 한국 (부산)": {"code": "KR", "city": "Busan", "coords": "35.1796,129.0756", "country": "한국"},
    "🇰🇷 한국 (제주)": {"code": "KR", "city": "Jeju", "coords": "33.4996,126.5312", "country": "한국"},
    "🇹🇼 대만 (타이베이)": {"code": "TW", "city": "Taipei", "coords": "25.0330,121.5654", "country": "대만"},
    "🇹🇼 대만 (가오슝)": {"code": "TW", "city": "Kaohsiung", "coords": "22.6273,120.3014", "country": "대만"},
    "🇭🇰 홍콩": {"code": "HK", "city": "Hong Kong", "coords": "22.3193,114.1694", "country": "홍콩"},

    # [동남아시아]
    "🇻🇳 베트남 (하노이)": {"code": "VN", "city": "Hanoi", "coords": "21.0285,105.8542", "country": "베트남"},
    "🇻🇳 베트남 (다낭)": {"code": "VN", "city": "Da Nang", "coords": "16.0544,108.2022", "country": "베트남"},
    "🇻🇳 베트남 (호치민)": {"code": "VN", "city": "Ho Chi Minh", "coords": "10.8231,106.6297", "country": "베트남"},
    "🇻🇳 베트남 (나트랑)": {"code": "VN", "city": "Nha Trang", "coords": "12.2388,109.1967", "country": "베트남"},
    "🇹🇭 태국 (방콕)": {"code": "TH", "city": "Bangkok", "coords": "13.7563,100.5018", "country": "태국"},
    "🇹🇭 태국 (치앙마이)": {"code": "TH", "city": "Chiang Mai", "coords": "18.7061,98.9817", "country": "태국"},
    "🇹🇭 태국 (푸켓)": {"code": "TH", "city": "Phuket", "coords": "7.8804,98.3923", "country": "태국"},
    "🇸🇬 싱가포르": {"code": "SG", "city": "Singapore", "coords": "1.3521,103.8198", "country": "싱가포르"},
    "🇮🇩 인도네시아 (발리)": {"code": "ID", "city": "Bali", "coords": "-8.4095,115.1889", "country": "인도네시아"},
    "🇵🇭 필리핀 (세부)": {"code": "PH", "city": "Cebu", "coords": "10.3157,123.8854", "country": "필리핀"},

    # [유럽]
    "🇬🇧 영국 (런던)": {"code": "GB", "city": "London", "coords": "51.5074,-0.1278", "country": "영국"},
    "🇫🇷 프랑스 (파리)": {"code": "FR", "city": "Paris", "coords": "48.8566,2.3522", "country": "프랑스"},
    "🇫🇷 프랑스 (니스)": {"code": "FR", "city": "Nice", "coords": "43.7102,7.2620", "country": "프랑스"},
    "🇮🇹 이탈리아 (로마)": {"code": "IT", "city": "Rome", "coords": "41.9028,12.4964", "country": "이탈리아"},
    "🇮🇹 이탈리아 (피렌체)": {"code": "IT", "city": "Florence", "coords": "43.7696,11.2558", "country": "이탈리아"},
    "🇮🇹 이탈리아 (베네치아)": {"code": "IT", "city": "Venice", "coords": "45.4408,12.3155", "country": "이탈리아"},
    "🇪🇸 스페인 (바르셀로나)": {"code": "ES", "city": "Barcelona", "coords": "41.3851,2.1734", "country": "스페인"},
    "🇪🇸 스페인 (마드리드)": {"code": "ES", "city": "Madrid", "coords": "40.4168,-3.7038", "country": "스페인"},
    "🇨🇭 스위스 (취리히)": {"code": "CH", "city": "Zurich", "coords": "47.3769,8.5417", "country": "스위스"},
    "🇨🇭 스위스 (인터라켄)": {"code": "CH", "city": "Interlaken", "coords": "46.6863,7.8632", "country": "스위스"},
    "🇨🇿 체코 (프라하)": {"code": "CZ", "city": "Prague", "coords": "50.0755,14.4378", "country": "체코"},
    "🇦🇹 오스트리아 (빈)": {"code": "AT", "city": "Vienna", "coords": "48.2082,16.3738", "country": "오스트리아"},
    "🇭🇺 헝가리 (부다페스트)": {"code": "HU", "city": "Budapest", "coords": "47.4979,19.0402", "country": "헝가리"},
    "🇩🇪 독일 (베를린)": {"code": "DE", "city": "Berlin", "coords": "52.5200,13.4050", "country": "독일"},
    "🇳🇱 네덜란드 (암스테르담)": {"code": "NL", "city": "Amsterdam", "coords": "52.3676,4.9041", "country": "네덜란드"},

    # [미주]
    "🇺🇸 미국 (뉴욕)": {"code": "US", "city": "New York", "coords": "40.7128,-74.0060", "country": "미국"},
    "🇺🇸 미국 (LA)": {"code": "US", "city": "Los Angeles", "coords": "34.0522,-118.2437", "country": "미국"},
    "🇺🇸 미국 (샌프란시스코)": {"code": "US", "city": "San Francisco", "coords": "37.7749,-122.4194", "country": "미국"},
    "🇺🇸 미국 (라스베이거스)": {"code": "US", "city": "Las Vegas", "coords": "36.1699,-115.1398", "country": "미국"},
    "🇺🇸 미국 (하와이 호놀룰루)": {"code": "US", "city": "Honolulu", "coords": "21.3069,-157.8583", "country": "미국"},
    "🇨🇦 캐나다 (밴쿠버)": {"code": "CA", "city": "Vancouver", "coords": "49.2827,-123.1207", "country": "캐나다"},
    "🇨🇦 캐나다 (토론토)": {"code": "CA", "city": "Toronto", "coords": "43.6510,-79.3470", "country": "캐나다"},
    "🇲🇽 멕시코 (칸쿤)": {"code": "MX", "city": "Cancun", "coords": "21.1619,-86.8515", "country": "멕시코"},

    # [오세아니아/기타]
    "🇦🇺 호주 (시드니)": {"code": "AU", "city": "Sydney", "coords": "-33.8688,151.2093", "country": "호주"},
    "🇦🇺 호주 (멜버른)": {"code": "AU", "city": "Melbourne", "coords": "-37.8136,144.9631", "country": "호주"},
    "🇬🇺 괌": {"code": "GU", "city": "Guam", "coords": "13.4443,144.7937", "country": "괌"},
    "🇲🇵 사이판": {"code": "MP", "city": "Saipan", "coords": "15.1833,145.7500", "country": "사이판"}
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

# --- 3. 공통 API 및 유틸리티 함수 ---

# [신규] 거리 계산 함수 (Haversine formula)
def calculate_distance(coords1, coords2):
    lat1, lon1 = map(float, coords1.split(','))
    lat2, lon2 = map(float, coords2.split(','))
    R = 6371  # 지구 반지름 (km)
    
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

import math # math 모듈 임포트

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
    """OpenStreetMap: 구글 지도 링크 생성"""
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
                map_link = f"https://www.google.com/maps/search/?api=1&query={p_lat},{p_lon}"
                places.append({"장소명": name, "지도 보기": map_link})
        return pd.DataFrame(places)
    except: return pd.DataFrame()

# --- 4. 데이터 처리 엔진 ---

def create_base_dataframe(weather_json, start_date, end_date):
    if not weather_json or 'daily' not in weather_json: return pd.DataFrame()
    df = pd.DataFrame(weather_json['daily'])
    df['date'] = pd.to_datetime(df['time'])
    df = df.set_index('date').drop(columns='time')
    return df

def calculate_daily_score(df, local_holidays, kr_holidays, priority_mode):
    date_str = df.index.strftime('%Y-%m-%d')
    df['is_local_holiday'] = date_str.isin(local_holidays)
    df['is_kr_holiday'] = date_str.isin(kr_holidays)
    df['is_weekend'] = df.index.dayofweek >= 5
    df['is_free_day'] = df['is_kr_holiday'] | df['is_weekend']
    
    df['score_weather'] = 10 - abs(df['temperature_2m_max'] - 23)
    df['score_rain'] = -df['precipitation_sum'] * 2
    
    if priority_mode == "비용 절감 (휴일 제외)":
        df['score_busy'] = (df['is_local_holiday'] | df['is_kr_holiday'] | df['is_weekend']).astype(int) * -10
        df['score_free'] = 0 
    else:
        df['score_busy'] = (df['is_local_holiday'] | df['is_weekend']).astype(int) * -5
        df['score_free'] = df['is_free_day'].astype(int) * 5
    
    df['total_score'] = df['score_weather'] + df['score_rain'] + df['score_busy'] + df['score_free']
    return df

# --- 모드 1: 개인 맞춤형 (Single) ---
def run_mode_single_trip():
    st.header("🎯 개인 맞춤형 여행 추천")
    st.caption("가고 싶은 도시를 하나 골라, 최적의 여행 시기를 찾아보세요.")

    col1, col2 = st.columns(2)
    with col1:
        country_key = st.selectbox("어디로 떠날까요? (도시 검색)", options=CITY_DATA.keys())
    with col2:
        theme_name = st.selectbox("여행 테마는?", options=THEME_OSM_MAP.keys())

    priority_mode = st.radio(
        "여행 우선순위 선택", 
        ["연차 효율 (휴일 포함)", "비용 절감 (휴일 제외)"], 
        horizontal=True
    )

    today = datetime.now().date()
    st.write("📅 **언제 여행을 떠나시나요?**")
    date_range = st.date_input(
        "달력에서 기간 선택",
        value=(today + timedelta(days=30), today + timedelta(days=90)),
        min_value=today,
        max_value=today + timedelta(days=365),
        format="YYYY-MM-DD"
    )
    
    trip_duration = st.slider("여행 기간 (박)", 3, 14, 5)

    if st.button("최적 일정 찾기", type="primary"):
        if len(date_range) < 2: 
            st.error("달력에서 시작일과 종료일을 모두 선택해주세요.")
            st.stop()
        
        country_data = CITY_DATA[country_key]
        lat, lon = country_data["coords"].split(',')
        start_date, end_date = date_range
        
        hist_start = start_date - pd.DateOffset(years=1)
        hist_end = end_date - pd.DateOffset(years=1)
        
        with st.spinner(f"{country_key} 데이터 분석 중..."):
            weather = get_historical_weather(lat, lon, hist_start.strftime('%Y-%m-%d'), hist_end.strftime('%Y-%m-%d'))
            local_h = get_holidays_for_period(CALENDARIFIC_KEY, country_data["code"], start_date, end_date)
            kr_h = get_holidays_for_period(CALENDARIFIC_KEY, "KR", start_date, end_date)
            places_df = get_places_osm(lat, lon, THEME_OSM_MAP[theme_name])
            
            df = create_base_dataframe(weather, hist_start, hist_end)
            if df.empty: st.error("날씨 데이터 없음"); st.stop()
            
            df = calculate_daily_score(df, local_h, kr_h, priority_mode)
            
            best_periods = []
            for i in range(len(df) - trip_duration + 1):
                window = df.iloc[i : i + trip_duration]
                score = window['total_score'].mean()
                start = window.index[0] + pd.DateOffset(years=1)
                end = window.index[-1] + pd.DateOffset(years=1)
                best_periods.append({"start": start, "end": end, "score": score, "window": window})
            
            best_periods.sort(key=lambda x: x['score'], reverse=True)
            top_3 = best_periods[:3]
            
            if not top_3:
                st.warning("추천 기간을 찾지 못했습니다."); st.stop()

            st.divider()
            st.subheader(f"🗺️ '{theme_name}' 추천 장소 ({country_key})")
            if not places_df.empty:
                st.dataframe(places_df, column_config={"지도 보기": st.column_config.LinkColumn("구글 지도", display_text="📍 지도 열기")}, hide_index=True, use_container_width=True)
            else:
                st.info("주변 장소 데이터 없음")

            st.write("---")
            st.subheader(f"🏆 추천 여행 기간 Best 3")
            
            for i, period in enumerate(top_3):
                p_start = period['start'].strftime('%Y-%m-%d')
                p_end = period['end'].strftime('%Y-%m-%d')
                score = period['score']
                temp_avg = period['window']['temperature_2m_max'].mean()
                rain_sum = period['window']['precipitation_sum'].sum()
                free_days = period['window']['is_free_day'].sum()
                
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else ""
                
                with st.expander(f"{medal} {i+1}순위: {p_start} ~ {p_end} (종합 점수: {score:.0f}점)", expanded=(i==0)):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("예상 기온", f"{temp_avg:.1f}°C")
                    c2.metric("예상 강수", f"{rain_sum:.1f}mm")
                    c3.metric("휴일 포함", f"{free_days}일")
                    if temp_avg > 28: st.caption("🥵 더운 날씨 대비 필요")
                    elif temp_avg < 5: st.caption("🥶 추운 날씨 대비 필요")
                    elif 15 <= temp_avg <= 25: st.caption("🌿 여행하기 최적의 날씨!")

# --- 모드 2: 장기 여행 (루트 최적화) ---
def run_mode_long_trip():
    st.header("🌏 장기 여행 (루트 최적화)")
    st.caption("여러 도시를 효율적으로 방문하는 순서(루트)를 제안합니다.")

    # 1. 나라 선택
    unique_countries = sorted(list(set([v['country'] for v in CITY_DATA.values()])))
    selected_nations = st.multiselect("방문할 나라들을 선택하세요", unique_countries)

    # 2. 도시 자동 필터링 및 선택
    available_cities = []
    if selected_nations:
        available_cities = [k for k, v in CITY_DATA.items() if v['country'] in selected_nations]
    
    selected_cities = st.multiselect(
        "방문할 도시를 확인 및 선택해주세요",
        options=available_cities,
        default=available_cities
    )

    if not selected_cities:
        st.info("나라를 먼저 선택해주세요.")
        return

    # [신규] 출발 도시 선택
    start_city = st.selectbox("어디서 여행을 시작하시나요?", options=selected_cities)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("여행 시작일", value=datetime.now().date() + timedelta(days=30))
    with col2:
        # [변경] 개월 -> 주 단위로 변경
        total_weeks = st.slider("전체 여행 기간 (주)", 1, 12, 4)
    
    total_days = total_weeks * 7

    if st.button("효율적인 여행 루트 짜기", type="primary"):
        if len(selected_cities) < 2:
            st.warning("2개 이상의 도시를 선택해주세요."); st.stop()

        # --- 루트 최적화 (Greedy: Nearest Neighbor) ---
        route = [start_city]
        unvisited = [c for c in selected_cities if c != start_city]
        current_city = start_city

        while unvisited:
            # 현재 도시에서 가장 가까운 도시 찾기
            curr_coords = CITY_DATA[current_city]["coords"]
            
            # 거리 계산 및 정렬 lambda (x: 도시명)
            nearest_city = min(unvisited, key=lambda x: calculate_distance(curr_coords, CITY_DATA[x]["coords"]))
            
            route.append(nearest_city)
            unvisited.remove(nearest_city)
            current_city = nearest_city

        # --- 일정 배분 및 날씨 체크 ---
        days_per_city = max(2, total_days // len(route)) # 도시당 최소 2일 보장 노력
        
        st.divider()
        st.subheader(f"🗺️ 추천 여행 루트 ({len(route)}개 도시, 총 {total_weeks}주)")
        st.write("지리적 거리와 효율성을 고려하여 다음 순서를 추천합니다:")

        # 루트 시각화 (간단한 화살표)
        route_str = "  ➡️  ".join([f"**{city.split('(')[0].strip()}**" for city in route])
        st.info(route_str)

        st.subheader("📅 도시별 상세 일정 및 날씨 예보")
        
        current_date = start_date
        
        for idx, city in enumerate(route):
            city_data = CITY_DATA[city]
            lat, lon = city_data["coords"].split(',')
            
            # 마지막 도시는 남은 기간 전부 소진
            if idx == len(route) - 1:
                stay_days = (start_date + timedelta(days=total_days) - current_date).days
            else:
                stay_days = days_per_city
            
            arrival_date = current_date
            departure_date = current_date + timedelta(days=stay_days)
            
            # 작년 날씨 확인
            hist_start = arrival_date - pd.DateOffset(years=1)
            hist_end = departure_date - pd.DateOffset(years=1)
            
            with st.spinner(f"{city} 날씨 확인 중..."):
                weather = get_historical_weather(lat, lon, hist_start.strftime('%Y-%m-%d'), hist_end.strftime('%Y-%m-%d'))
                df = create_base_dataframe(weather, hist_start, hist_end)
            
            weather_desc = "데이터 없음"
            temp_avg = 0
            if not df.empty:
                temp_avg = df['temperature_2m_max'].mean()
                rain_sum = df['precipitation_sum'].sum()
                
                if temp_avg > 28: weather_status = "🥵 더움"
                elif temp_avg < 5: weather_status = "🥶 추움"
                elif 15 <= temp_avg <= 25: weather_status = "🌿 쾌적"
                else: weather_status = "😐 보통"
                
                if rain_sum > 30: weather_status += ", ☔ 비 많음"
                weather_desc = f"평균 {temp_avg:.1f}°C ({weather_status})"

            # 카드 형태로 일정 출력
            with st.container():
                st.markdown(f"### {idx+1}. {city}")
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"🗓️ **일정:** {arrival_date.strftime('%Y-%m-%d')} ~ {departure_date.strftime('%m-%d')} ({stay_days}박)")
                c2.write(f"🌦️ **예상 날씨:** {weather_desc}")
                
                # 구글 맵 링크
                map_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                c3.markdown(f"[📍 지도 보기]({map_link})")
                
                st.divider()

            current_date = departure_date # 다음 도시 도착일 = 이번 도시 출발일

# --- 메인 앱 실행 ---
def main():
    st.set_page_config(page_title="Travel Planner AI", page_icon="✈️", layout="wide")
    check_api_keys()
    
    with st.sidebar:
        st.title("✈️ 여행 비서 AI")
        app_mode = st.radio("선택 메뉴", ["개인 맞춤형 (Single)", "장기 여행 (Long-term)"])
        st.write("---")
        st.caption("Made with Streamlit")

    if app_mode == "개인 맞춤형 (Single)":
        run_mode_single_trip()
    elif app_mode == "장기 여행 (Long-term)": # 이름 변경 반영
        run_mode_long_trip()

if __name__ == "__main__":
    main()
