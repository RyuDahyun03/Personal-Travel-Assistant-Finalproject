import streamlit as st
import requests
import pandas as pd
import math
from datetime import datetime, timedelta
import io
import pydeck as pdk

# --- 1. 전 세계 주요 도시 데이터 ---
CITY_DATA = {
    # [동북아시아]
    "🇯🇵 일본 (도쿄)": {"code": "JP", "city": "Tokyo", "coords": "35.6895,139.6917", "country": "일본", "cost": 180000, "visa": "무비자 (90일)"},
    "🇯🇵 일본 (오사카)": {"code": "JP", "city": "Osaka", "coords": "34.6937,135.5023", "country": "일본", "cost": 160000, "visa": "무비자 (90일)"},
    "🇯🇵 일본 (후쿠오카)": {"code": "JP", "city": "Fukuoka", "coords": "33.5904,130.4017", "country": "일본", "cost": 140000, "visa": "무비자 (90일)"},
    "🇯🇵 일본 (삿포로)": {"code": "JP", "city": "Sapporo", "coords": "43.0618,141.3545", "country": "일본", "cost": 170000, "visa": "무비자 (90일)"},
    "🇯🇵 일본 (오키나와)": {"code": "JP", "city": "Naha", "coords": "26.2124,127.6809", "country": "일본", "cost": 160000, "visa": "무비자 (90일)"},
    "🇰🇷 한국 (서울)": {"code": "KR", "city": "Seoul", "coords": "37.5665,126.9780", "country": "한국", "cost": 130000, "visa": "해당 없음"},
    "🇰🇷 한국 (부산)": {"code": "KR", "city": "Busan", "coords": "35.1796,129.0756", "country": "한국", "cost": 120000, "visa": "해당 없음"},
    "🇰🇷 한국 (제주)": {"code": "KR", "city": "Jeju", "coords": "33.4996,126.5312", "country": "한국", "cost": 140000, "visa": "해당 없음"},
    "🇹🇼 대만 (타이베이)": {"code": "TW", "city": "Taipei", "coords": "25.0330,121.5654", "country": "대만", "cost": 110000, "visa": "무비자 (90일)"},
    "🇹🇼 대만 (가오슝)": {"code": "TW", "city": "Kaohsiung", "coords": "22.6273,120.3014", "country": "대만", "cost": 100000, "visa": "무비자 (90일)"},
    "🇭🇰 홍콩": {"code": "HK", "city": "Hong Kong", "coords": "22.3193,114.1694", "country": "홍콩", "cost": 190000, "visa": "무비자 (90일)"},

    # [동남아시아]
    "🇻🇳 베트남 (하노이)": {"code": "VN", "city": "Hanoi", "coords": "21.0285,105.8542", "country": "베트남", "cost": 80000, "visa": "무비자 (45일)"},
    "🇻🇳 베트남 (다낭)": {"code": "VN", "city": "Da Nang", "coords": "16.0544,108.2022", "country": "베트남", "cost": 90000, "visa": "무비자 (45일)"},
    "🇻🇳 베트남 (호치민)": {"code": "VN", "city": "Ho Chi Minh", "coords": "10.8231,106.6297", "country": "베트남", "cost": 85000, "visa": "무비자 (45일)"},
    "🇻🇳 베트남 (나트랑)": {"code": "VN", "city": "Nha Trang", "coords": "12.2388,109.1967", "country": "베트남", "cost": 85000, "visa": "무비자 (45일)"},
    "🇹🇭 태국 (방콕)": {"code": "TH", "city": "Bangkok", "coords": "13.7563,100.5018", "country": "태국", "cost": 100000, "visa": "무비자 (90일)"},
    "🇹🇭 태국 (치앙마이)": {"code": "TH", "city": "Chiang Mai", "coords": "18.7061,98.9817", "country": "태국", "cost": 70000, "visa": "무비자 (90일)"},
    "🇹🇭 태국 (푸켓)": {"code": "TH", "city": "Phuket", "coords": "7.8804,98.3923", "country": "태국", "cost": 120000, "visa": "무비자 (90일)"},
    "🇸🇬 싱가포르": {"code": "SG", "city": "Singapore", "coords": "1.3521,103.8198", "country": "싱가포르", "cost": 220000, "visa": "무비자 (90일)"},
    "🇮🇩 인도네시아 (발리)": {"code": "ID", "city": "Bali", "coords": "-8.4095,115.1889", "country": "인도네시아", "cost": 110000, "visa": "도착비자 필요 (약 4만원)"},
    "🇵🇭 필리핀 (세부)": {"code": "PH", "city": "Cebu", "coords": "10.3157,123.8854", "country": "필리핀", "cost": 90000, "visa": "무비자 (30일)"},

    # [유럽]
    "🇬🇧 영국 (런던)": {"code": "GB", "city": "London", "coords": "51.5074,-0.1278", "country": "영국", "cost": 280000, "visa": "무비자 (6개월)"},
    "🇫🇷 프랑스 (파리)": {"code": "FR", "city": "Paris", "coords": "48.8566,2.3522", "country": "프랑스", "cost": 250000, "visa": "무비자 (90일)"},
    "🇫🇷 프랑스 (니스)": {"code": "FR", "city": "Nice", "coords": "43.7102,7.2620", "country": "프랑스", "cost": 260000, "visa": "무비자 (90일)"},
    "🇮🇹 이탈리아 (로마)": {"code": "IT", "city": "Rome", "coords": "41.9028,12.4964", "country": "이탈리아", "cost": 220000, "visa": "무비자 (90일)"},
    "🇮🇹 이탈리아 (피렌체)": {"code": "IT", "city": "Florence", "coords": "43.7696,11.2558", "country": "이탈리아", "cost": 230000, "visa": "무비자 (90일)"},
    "🇮🇹 이탈리아 (베네치아)": {"code": "IT", "city": "Venice", "coords": "45.4408,12.3155", "country": "이탈리아", "cost": 240000, "visa": "무비자 (90일)"},
    "🇪🇸 스페인 (바르셀로나)": {"code": "ES", "city": "Barcelona", "coords": "41.3851,2.1734", "country": "스페인", "cost": 180000, "visa": "무비자 (90일)"},
    "🇪🇸 스페인 (마드리드)": {"code": "ES", "city": "Madrid", "coords": "40.4168,-3.7038", "country": "스페인", "cost": 170000, "visa": "무비자 (90일)"},
    "🇨🇭 스위스 (취리히)": {"code": "CH", "city": "Zurich", "coords": "47.3769,8.5417", "country": "스위스", "cost": 350000, "visa": "무비자 (90일)"},
    "🇨🇭 스위스 (인터라켄)": {"code": "CH", "city": "Interlaken", "coords": "46.6863,7.8632", "country": "스위스", "cost": 330000, "visa": "무비자 (90일)"},
    "🇨🇿 체코 (프라하)": {"code": "CZ", "city": "Prague", "coords": "50.0755,14.4378", "country": "체코", "cost": 120000, "visa": "무비자 (90일)"},
    "🇦🇹 오스트리아 (빈)": {"code": "AT", "city": "Vienna", "coords": "48.2082,16.3738", "country": "오스트리아", "cost": 200000, "visa": "무비자 (90일)"},
    "🇭🇺 헝가리 (부다페스트)": {"code": "HU", "city": "Budapest", "coords": "47.4979,19.0402", "country": "헝가리", "cost": 110000, "visa": "무비자 (90일)"},
    "🇩🇪 독일 (베를린)": {"code": "DE", "city": "Berlin", "coords": "52.5200,13.4050", "country": "독일", "cost": 190000, "visa": "무비자 (90일)"},
    "🇳🇱 네덜란드 (암스테르담)": {"code": "NL", "city": "Amsterdam", "coords": "52.3676,4.9041", "country": "네덜란드", "cost": 230000, "visa": "무비자 (90일)"},

    # [미주]
    "🇺🇸 미국 (뉴욕)": {"code": "US", "city": "New York", "coords": "40.7128,-74.0060", "country": "미국", "cost": 350000, "visa": "ESTA 필요"},
    "🇺🇸 미국 (LA)": {"code": "US", "city": "Los Angeles", "coords": "34.0522,-118.2437", "country": "미국", "cost": 300000, "visa": "ESTA 필요"},
    "🇺🇸 미국 (샌프란시스코)": {"code": "US", "city": "San Francisco", "coords": "37.7749,-122.4194", "country": "미국", "cost": 320000, "visa": "ESTA 필요"},
    "🇺🇸 미국 (라스베이거스)": {"code": "US", "city": "Las Vegas", "coords": "36.1699,-115.1398", "country": "미국", "cost": 280000, "visa": "ESTA 필요"},
    "🇺🇸 미국 (하와이 호놀룰루)": {"code": "US", "city": "Honolulu", "coords": "21.3069,-157.8583", "country": "미국", "cost": 330000, "visa": "ESTA 필요"},
    "🇨🇦 캐나다 (밴쿠버)": {"code": "CA", "city": "Vancouver", "coords": "49.2827,-123.1207", "country": "캐나다", "cost": 250000, "visa": "eTA 필요"},
    "🇨🇦 캐나다 (토론토)": {"code": "CA", "city": "Toronto", "coords": "43.6510,-79.3470", "country": "캐나다", "cost": 240000, "visa": "eTA 필요"},
    "🇲🇽 멕시코 (칸쿤)": {"code": "MX", "city": "Cancun", "coords": "21.1619,-86.8515", "country": "멕시코", "cost": 180000, "visa": "무비자 (180일)"},

    # [오세아니아/기타]
    "🇦🇺 호주 (시드니)": {"code": "AU", "city": "Sydney", "coords": "-33.8688,151.2093", "country": "호주", "cost": 230000, "visa": "ETA 필요"},
    "🇦🇺 호주 (멜버른)": {"code": "AU", "city": "Melbourne", "coords": "-37.8136,144.9631", "country": "호주", "cost": 220000, "visa": "ETA 필요"},
    "🇬🇺 괌": {"code": "GU", "city": "Guam", "coords": "13.4443,144.7937", "country": "괌", "cost": 250000, "visa": "무비자 (45일)"},
    "🇲🇵 사이판": {"code": "MP", "city": "Saipan", "coords": "15.1833,145.7500", "country": "사이판", "cost": 240000, "visa": "무비자 (45일)"}
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

def calculate_distance(coords1, coords2):
    lat1, lon1 = map(float, coords1.split(','))
    lat2, lon2 = map(float, coords2.split(','))
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# [수정된 지도 시각화] 점(Scatterplot)과 텍스트(Text)로 지역 표시
def draw_route_map(route_cities):
    """PyDeck을 사용하여 지도 위에 방문할 도시를 점과 이름으로 표시합니다."""
    map_data = []
    for i, city_key in enumerate(route_cities):
        city_data = CITY_DATA[city_key]
        # PyDeck은 [경도, 위도] 순서
        coords = list(map(float, city_data['coords'].split(',')))[::-1]
        
        map_data.append({
            "coordinates": coords,
            "name": f"{i+1}. {city_data['city']}", # 번호와 도시 이름
            "size": 50000, # 점 크기 (미터 단위, 지도 줌 레벨에 따라 조절됨)
            "color": [0, 200, 100, 200] # 초록색 점
        })

    # 1. 점 레이어 (도시 위치 표시)
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        get_position="coordinates",
        get_fill_color="color",
        get_radius="size",
        pickable=True,
        radius_scale=1,
        radius_min_pixels=10, # 최소 크기 보장
        radius_max_pixels=30,
    )

    # 2. 텍스트 레이어 (도시 이름 표시)
    text_layer = pdk.Layer(
        "TextLayer",
        data=map_data,
        get_position="coordinates",
        get_text="name",
        get_size=20,
        get_color=[0, 0, 0],
        get_angle=0,
        get_text_anchor="middle",
        get_alignment_baseline="bottom",
        pixel_offset=[0, -20] # 점 위에 글씨 표시
    )

    # 초기 뷰 설정 (첫 번째 도시 기준)
    first_city_coords = list(map(float, CITY_DATA[route_cities[0]]['coords'].split(',')))[::-1]
    view_state = pdk.ViewState(
        latitude=first_city_coords[1],
        longitude=first_city_coords[0],
        zoom=3,
        pitch=0,
    )

    st.pydeck_chart(pdk.Deck(
        layers=[scatter_layer, text_layer],
        initial_view_state=view_state,
        map_style=None,
        tooltip={"text": "{name}"}
    ))

def get_packing_tips(avg_temp, rain_sum):
    tips = []
    if avg_temp < 5: tips.append("🧥 두꺼운 패딩/코트, 목도리, 장갑 (매우 추움)")
    elif 5 <= avg_temp < 15: tips.append("🧥 경량 패딩, 자켓, 히트텍 (쌀쌀함)")
    elif 15 <= avg_temp < 22: tips.append("👕 긴팔 티셔츠, 가디건, 얇은 외투 (쾌적함)")
    elif avg_temp >= 22: tips.append("👕 반팔, 반바지, 샌들, 선글라스 (더움)")
    
    if rain_sum > 30: tips.append("☂️ 우산 또는 우비 (비가 자주 올 수 있음)")
    if avg_temp > 25: tips.append("🧴 자외선 차단제, 모자")
    
    if not tips: tips.append("평범한 여행 복장이면 충분합니다.")
    return "\n".join([f"- {t}" for t in tips])

def get_flight_link(destination_key):
    query_city = CITY_DATA[destination_key]['city']
    return f"https://www.google.com/travel/flights?q=Flights+to+{query_city}"

@st.cache_data(ttl=3600)
def get_holidays_for_period(api_key, country_code, start_date, end_date):
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

# --- 4. 데이터 처리 및 계산 엔진 ---

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

def calculate_travel_cost(city_key, days, style):
    """경비 계산 함수"""
    base_cost = CITY_DATA[city_key]['cost']
    
    if style == "배낭여행 (절약)":
        multiplier = 0.6
    elif style == "일반 (표준)":
        multiplier = 1.0
    else: # 럭셔리
        multiplier = 2.5
        
    total_cost = base_cost * days * multiplier
    return int(total_cost)

def generate_download_content(title, details_text):
    return f"""
    ==========================================
    ✈️ 여행 비서 AI - 추천 일정 리포트
    ==========================================
    
    {title}
    
    {details_text}
    
    ------------------------------------------
    * 본 정보는 AI 분석 결과이며 실제와 다를 수 있습니다.
    * 날씨는 작년 데이터를 기반으로 예측되었습니다.
    * 경비는 항공권을 제외한 현지 체류비 추정치입니다.
    ==========================================
    """

# --- 모드 1: 개인 맞춤형 (Single) ---
def run_mode_single_trip():
    st.header("🎯 모드 1: 개인 맞춤형 여행 추천")
    
    col1, col2 = st.columns(2)
    with col1:
        country_key = st.selectbox("어디로 떠날까요? (도시 검색)", options=CITY_DATA.keys())
    with col2:
        theme_name = st.selectbox("여행 테마는?", options=THEME_OSM_MAP.keys())

    travel_style = st.radio(
        "여행 스타일 선택 (경비 계산용)",
        options=["배낭여행 (절약)", "일반 (표준)", "럭셔리 (여유)"],
        index=1,
        horizontal=True
    )

    priority_mode = st.radio(
        "여행 우선순위 선택", 
        ["연차 효율 (휴일 포함)", "비용 절감 (휴일 제외)"], 
        horizontal=True
    )

    today = datetime.now().date()
    st.write("📅 **언제쯤 여행을 떠나시나요?**")
    date_range = st.date_input(
        "달력에서 기간 선택",
        value=(today + timedelta(days=30), today + timedelta(days=90)),
        min_value=today,
        max_value=today + timedelta(days=365),
        format="YYYY-MM-DD"
    )
    
    trip_duration = st.slider("여행 기간 (박)", 3, 14, 5)

    if st.button("최적 일정 찾기 & 경비 계산", type="primary"):
        if len(date_range) < 2: 
            st.error("달력에서 시작일과 종료일을 모두 선택해주세요.")
            st.stop()
        
        country_data = CITY_DATA[country_key]
        lat, lon = country_data["coords"].split(',')
        start_date, end_date = date_range
        
        hist_start = start_date - pd.DateOffset(years=1)
        hist_end = end_date - pd.DateOffset(years=1)
        
        with st.spinner(f"{country_key} 분석 중..."):
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

            # --- 결과 출력 ---
            st.divider()
            
            st.info(f"🛂 **비자 정보 ({country_data['country']}):** {country_data['visa']}")

            st.subheader(f"🗺️ '{theme_name}' 추천 장소 ({country_key})")
            if not places_df.empty:
                st.dataframe(places_df, column_config={"지도 보기": st.column_config.LinkColumn("구글 지도", display_text="📍 지도 열기")}, hide_index=True, use_container_width=True)
            else:
                st.info("주변 장소 데이터 없음")

            st.write("---")
            st.subheader(f"🏆 추천 여행 기간 Best 3")
            
            download_text = ""

            for i, period in enumerate(top_3):
                p_start = period['start'].strftime('%Y-%m-%d')
                p_end = period['end'].strftime('%Y-%m-%d')
                score = period['score']
                temp_avg = period['window']['temperature_2m_max'].mean()
                rain_sum = period['window']['precipitation_sum'].sum()
                free_days = period['window']['is_free_day'].sum()
                
                est_cost = calculate_travel_cost(country_key, trip_duration, travel_style)
                
                packing_tips = get_packing_tips(temp_avg, rain_sum)
                
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else ""
                
                download_text += f"[{i+1}순위] {p_start} ~ {p_end}\n"
                download_text += f" - 예상 기온: {temp_avg:.1f}도 / 강수량: {rain_sum:.1f}mm\n"
                download_text += f" - 준비물: {packing_tips.replace(chr(10), ', ')}\n"
                download_text += f" - 예상 경비: 약 {est_cost:,}원 ({travel_style})\n\n"

                with st.expander(f"{medal} {i+1}순위: {p_start} ~ {p_end} (종합 점수: {score:.0f}점)", expanded=(i==0)):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("예상 기온", f"{temp_avg:.1f}°C")
                    c2.metric("예상 강수", f"{rain_sum:.1f}mm")
                    c3.metric("휴일 포함", f"{free_days}일")
                    c4.metric("예상 경비", f"{est_cost // 10000}만 원")
                    
                    st.caption(f"💰 {trip_duration}박 체류비 ({travel_style})")
                    st.info(f"🧳 **챙겨야 할 것들:**\n{packing_tips}")
                    
                    flight_url = get_flight_link(country_key)
                    st.link_button("✈️ 실시간 항공권 가격 확인하기 (Google Flights)", flight_url)

            st.download_button(
                label="📥 추천 일정 저장하기 (TXT)",
                data=generate_download_content(f"{country_key} 여행 추천 ({trip_duration}박)", download_text),
                file_name=f"MyTrip_{country_key}_{today}.txt",
                mime="text/plain"
            )

# --- 모드 2: 장기 여행 (Long-term) ---
def run_mode_long_trip():
    st.header("🌏 모드 2: 장기 여행 (루트 최적화)")

    unique_countries = sorted(list(set([v['country'] for v in CITY_DATA.values()])))
    selected_nations = st.multiselect("방문할 나라들을 선택하세요", unique_countries)

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

    start_city = st.selectbox("어디서 여행을 시작하시나요? (출발 도시)", options=selected_cities)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("여행 시작일", value=datetime.now().date() + timedelta(days=30))
    with col2:
        total_weeks = st.slider("전체 여행 기간 (주)", 1, 12, 4)
    
    travel_style = st.radio(
        "여행 스타일 (전체 경비 계산용)",
        options=["배낭여행 (절약)", "일반 (표준)", "럭셔리 (여유)"],
        index=0,
        horizontal=True
    )

    total_days = total_weeks * 7

    if st.button("루트 최적화 & 통합 경비 계산", type="primary"):
        if len(selected_cities) < 2:
            st.warning("루트를 짜려면 2개 이상의 도시가 필요합니다."); st.stop()

        route = [start_city]
        unvisited = [c for c in selected_cities if c != start_city]
        current_city = start_city

        while unvisited:
            curr_coords = CITY_DATA[current_city]["coords"]
            nearest_city = min(unvisited, key=lambda x: calculate_distance(curr_coords, CITY_DATA[x]["coords"]))
            route.append(nearest_city)
            unvisited.remove(nearest_city)
            current_city = nearest_city

        days_per_city = max(2, total_days // len(route))
        
        st.divider()
        st.subheader(f"🗺️ 추천 여행 루트 ({len(route)}개 도시, 총 {total_weeks}주)")
        
        # [지도 시각화 수정] 선(Arc) 대신 점(Scatter)과 텍스트 표시
        draw_route_map(route)
        
        total_est_cost = 0
        visa_summary = set()
        download_text = "[[ 추천 루트 ]]\n"

        for city in route:
            if city == route[-1]:
                stay = total_days - (days_per_city * (len(route)-1))
            else:
                stay = days_per_city
            
            cost = calculate_travel_cost(city, stay, travel_style)
            total_est_cost += cost
            visa_summary.add(f"{CITY_DATA[city]['country']}: {CITY_DATA[city]['visa']}")
            download_text += f" -> {city} ({stay}박)\n"

        c1, c2 = st.columns(2)
        c1.metric("총 예상 경비", f"약 {total_est_cost // 10000}만 원", f"{travel_style}")
        c2.info("**비자 요약:**\n" + "\n".join([f"- {v}" for v in visa_summary]))

        st.write("---")
        st.subheader("📅 도시별 상세 일정")
        
        current_date = start_date
        download_text += "\n[[ 상세 일정 ]]\n"
        
        for idx, city in enumerate(route):
            city_data = CITY_DATA[city]
            lat, lon = city_data["coords"].split(',')
            
            if idx == len(route) - 1:
                stay_days = (start_date + timedelta(days=total_days) - current_date).days
            else:
                stay_days = days_per_city
            
            arrival_date = current_date
            departure_date = current_date + timedelta(days=stay_days)
            
            hist_start = arrival_date - pd.DateOffset(years=1)
            hist_end = departure_date - pd.DateOffset(years=1)
            
            with st.spinner(f"{city} 분석 중..."):
                weather = get_historical_weather(lat, lon, hist_start.strftime('%Y-%m-%d'), hist_end.strftime('%Y-%m-%d'))
                df = create_base_dataframe(weather, hist_start, hist_end)
            
            weather_desc = "데이터 없음"
            if not df.empty:
                temp = df['temperature_2m_max'].mean()
                status = "🌿 쾌적" if 15 <= temp <= 25 else ("🥵 더움" if temp > 28 else "🥶 추움")
                weather_desc = f"평균 {temp:.1f}°C ({status})"

            detail_str = f"{idx+1}. {city} ({stay_days}박): {arrival_date.strftime('%Y-%m-%d')} ~"
            download_text += f"{detail_str} | 날씨: {weather_desc}\n"

            with st.container():
                st.markdown(f"### {idx+1}. {city}")
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"🗓️ **일정:** {arrival_date.strftime('%m/%d')} ~ {departure_date.strftime('%m/%d')} ({stay_days}박)")
                c2.write(f"🌦️ **날씨:** {weather_desc}")
                map_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                c3.markdown(f"[📍 지도]({map_link})")
                st.divider()

            current_date = departure_date

        st.download_button(
            label="📥 전체 루트 저장하기 (TXT)",
            data=generate_download_content(f"장기 여행 루트 ({len(route)}개 도시)", download_text),
            file_name=f"LongTrip_Route_{start_date}.txt",
            mime="text/plain"
        )

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
    elif app_mode == "장기 여행 (Long-term)":
        run_mode_long_trip()

if __name__ == "__main__":
    main()
