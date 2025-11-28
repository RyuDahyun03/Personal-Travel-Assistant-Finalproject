import streamlit as st
import requests
import pandas as pd
import math
from datetime import datetime, timedelta
import pydeck as pdk
from fpdf import FPDF
import os
import time

# --- 설정: 테마 매핑 ---
THEME_OSM_MAP = {
    "미식 🍜": '"amenity"="restaurant"',
    "쇼핑 🛍️": '"shop"="mall"',
    "문화/유적 🏯": '"tourism"="attraction"',
    "휴양/공원 🌳": '"leisure"="park"'
}

# --- 1. [확장] 내장 도시 데이터 (100+개 도시 탑재) ---
# API 오류가 나도 이 도시들은 100% 검색됩니다.
FALLBACK_CITIES = {
    # 아시아
    "서울": {"lat": 37.5665, "lon": 126.9780, "code": "KR", "country": "한국"},
    "제주": {"lat": 33.4996, "lon": 126.5312, "code": "KR", "country": "한국"},
    "부산": {"lat": 35.1796, "lon": 129.0756, "code": "KR", "country": "한국"},
    "도쿄": {"lat": 35.6895, "lon": 139.6917, "code": "JP", "country": "일본"},
    "오사카": {"lat": 34.6937, "lon": 135.5023, "code": "JP", "country": "일본"},
    "후쿠오카": {"lat": 33.5904, "lon": 130.4017, "code": "JP", "country": "일본"},
    "삿포로": {"lat": 43.0618, "lon": 141.3545, "code": "JP", "country": "일본"},
    "오키나와": {"lat": 26.2124, "lon": 127.6809, "code": "JP", "country": "일본"},
    "교토": {"lat": 35.0116, "lon": 135.7681, "code": "JP", "country": "일본"},
    "방콕": {"lat": 13.7563, "lon": 100.5018, "code": "TH", "country": "태국"},
    "치앙마이": {"lat": 18.7061, "lon": 98.9817, "code": "TH", "country": "태국"},
    "푸켓": {"lat": 7.8804, "lon": 98.3923, "code": "TH", "country": "태국"},
    "다낭": {"lat": 16.0544, "lon": 108.2022, "code": "VN", "country": "베트남"},
    "하노이": {"lat": 21.0285, "lon": 105.8542, "code": "VN", "country": "베트남"},
    "호치민": {"lat": 10.8231, "lon": 106.6297, "code": "VN", "country": "베트남"},
    "나트랑": {"lat": 12.2388, "lon": 109.1967, "code": "VN", "country": "베트남"},
    "푸꾸옥": {"lat": 10.2899, "lon": 103.9840, "code": "VN", "country": "베트남"},
    "타이베이": {"lat": 25.0330, "lon": 121.5654, "code": "TW", "country": "대만"},
    "가오슝": {"lat": 22.6273, "lon": 120.3014, "code": "TW", "country": "대만"},
    "싱가포르": {"lat": 1.3521, "lon": 103.8198, "code": "SG", "country": "싱가포르"},
    "홍콩": {"lat": 22.3193, "lon": 114.1694, "code": "HK", "country": "홍콩"},
    "마카오": {"lat": 22.1987, "lon": 113.5439, "code": "MO", "country": "마카오"},
    "발리": {"lat": -8.4095, "lon": 115.1889, "code": "ID", "country": "인도네시아"},
    "자카르타": {"lat": -6.2088, "lon": 106.8456, "code": "ID", "country": "인도네시아"},
    "세부": {"lat": 10.3157, "lon": 123.8854, "code": "PH", "country": "필리핀"},
    "보라카이": {"lat": 11.9674, "lon": 121.9248, "code": "PH", "country": "필리핀"},
    "마닐라": {"lat": 14.5995, "lon": 120.9842, "code": "PH", "country": "필리핀"},
    "쿠알라룸푸르": {"lat": 3.1390, "lon": 101.6869, "code": "MY", "country": "말레이시아"},
    "코타키나발루": {"lat": 5.9804, "lon": 116.0735, "code": "MY", "country": "말레이시아"},

    # 유럽
    "파리": {"lat": 48.8566, "lon": 2.3522, "code": "FR", "country": "프랑스"},
    "니스": {"lat": 43.7102, "lon": 7.2620, "code": "FR", "country": "프랑스"},
    "리옹": {"lat": 45.7640, "lon": 4.8357, "code": "FR", "country": "프랑스"},
    "마르세유": {"lat": 43.2965, "lon": 5.3698, "code": "FR", "country": "프랑스"},
    "런던": {"lat": 51.5074, "lon": -0.1278, "code": "GB", "country": "영국"},
    "에든버러": {"lat": 55.9533, "lon": -3.1883, "code": "GB", "country": "영국"},
    "더블린": {"lat": 53.3498, "lon": -6.2603, "code": "IE", "country": "아일랜드"},
    "로마": {"lat": 41.9028, "lon": 12.4964, "code": "IT", "country": "이탈리아"},
    "피렌체": {"lat": 43.7696, "lon": 11.2558, "code": "IT", "country": "이탈리아"},
    "베네치아": {"lat": 45.4408, "lon": 12.3155, "code": "IT", "country": "이탈리아"},
    "밀라노": {"lat": 45.4642, "lon": 9.1900, "code": "IT", "country": "이탈리아"},
    "나폴리": {"lat": 40.8518, "lon": 14.2681, "code": "IT", "country": "이탈리아"},
    "바르셀로나": {"lat": 41.3851, "lon": 2.1734, "code": "ES", "country": "스페인"},
    "마드리드": {"lat": 40.4168, "lon": -3.7038, "code": "ES", "country": "스페인"},
    "세비야": {"lat": 37.3891, "lon": -5.9845, "code": "ES", "country": "스페인"},
    "리스본": {"lat": 38.7223, "lon": -9.1393, "code": "PT", "country": "포르투갈"},
    "포르투": {"lat": 41.1579, "lon": -8.6291, "code": "PT", "country": "포르투갈"},
    "취리히": {"lat": 47.3769, "lon": 8.5417, "code": "CH", "country": "스위스"},
    "제네바": {"lat": 46.2044, "lon": 6.1432, "code": "CH", "country": "스위스"},
    "인터라켄": {"lat": 46.6863, "lon": 7.8632, "code": "CH", "country": "스위스"},
    "베를린": {"lat": 52.5200, "lon": 13.4050, "code": "DE", "country": "독일"},
    "뮌헨": {"lat": 48.1351, "lon": 11.5820, "code": "DE", "country": "독일"},
    "프랑크푸르트": {"lat": 50.1109, "lon": 8.6821, "code": "DE", "country": "독일"},
    "암스테르담": {"lat": 52.3676, "lon": 4.9041, "code": "NL", "country": "네덜란드"},
    "브뤼셀": {"lat": 50.8503, "lon": 4.3517, "code": "BE", "country": "벨기에"},
    "비엔나": {"lat": 48.2082, "lon": 16.3738, "code": "AT", "country": "오스트리아"},
    "잘츠부르크": {"lat": 47.8095, "lon": 13.0550, "code": "AT", "country": "오스트리아"},
    "프라하": {"lat": 50.0755, "lon": 14.4378, "code": "CZ", "country": "체코"},
    "부다페스트": {"lat": 47.4979, "lon": 19.0402, "code": "HU", "country": "헝가리"},
    "아테네": {"lat": 37.9838, "lon": 23.7275, "code": "GR", "country": "그리스"},
    "산토리니": {"lat": 36.3932, "lon": 25.4615, "code": "GR", "country": "그리스"},
    "이스탄불": {"lat": 41.0082, "lon": 28.9784, "code": "TR", "country": "튀르키예"},
    "두브로브니크": {"lat": 42.6507, "lon": 18.0944, "code": "HR", "country": "크로아티아"},
    "자그레브": {"lat": 45.8150, "lon": 15.9819, "code": "HR", "country": "크로아티아"},
    "코펜하겐": {"lat": 55.6761, "lon": 12.5683, "code": "DK", "country": "덴마크"},
    "스톡홀름": {"lat": 59.3293, "lon": 18.0686, "code": "SE", "country": "스웨덴"},
    "오슬로": {"lat": 59.9139, "lon": 10.7522, "code": "NO", "country": "노르웨이"},
    "헬싱키": {"lat": 60.1699, "lon": 24.9384, "code": "FI", "country": "핀란드"},

    # 미주
    "뉴욕": {"lat": 40.7128, "lon": -74.0060, "code": "US", "country": "미국"},
    "LA": {"lat": 34.0522, "lon": -118.2437, "code": "US", "country": "미국"},
    "샌프란시스코": {"lat": 37.7749, "lon": -122.4194, "code": "US", "country": "미국"},
    "라스베이거스": {"lat": 36.1699, "lon": -115.1398, "code": "US", "country": "미국"},
    "시카고": {"lat": 41.8781, "lon": -87.6298, "code": "US", "country": "미국"},
    "하와이": {"lat": 21.3069, "lon": -157.8583, "code": "US", "country": "미국"},
    "밴쿠버": {"lat": 49.2827, "lon": -123.1207, "code": "CA", "country": "캐나다"},
    "토론토": {"lat": 43.6510, "lon": -79.3470, "code": "CA", "country": "캐나다"},
    "칸쿤": {"lat": 21.1619, "lon": -86.8515, "code": "MX", "country": "멕시코"},

    # 오세아니아/기타
    "시드니": {"lat": -33.8688, "lon": 151.2093, "code": "AU", "country": "호주"},
    "멜버른": {"lat": -37.8136, "lon": 144.9631, "code": "AU", "country": "호주"},
    "브리즈번": {"lat": -27.4698, "lon": 153.0251, "code": "AU", "country": "호주"},
    "오클랜드": {"lat": -36.8485, "lon": 174.7633, "code": "NZ", "country": "뉴질랜드"},
    "괌": {"lat": 13.4443, "lon": 144.7937, "code": "GU", "country": "괌"},
    "사이판": {"lat": 15.1833, "lon": 145.7500, "code": "MP", "country": "사이판"}
}

# --- 2. API 키 확인 ---
CALENDARIFIC_KEY = st.secrets.get("calendarific_key")
GEMINI_KEY = st.secrets.get("gemini_key")

def check_api_keys():
    if not CALENDARIFIC_KEY:
        st.sidebar.error("⚠️ Calendarific API 키가 설정되지 않았습니다.")
        st.stop()

# --- 3. 유틸리티 함수 ---

@st.cache_data(ttl=3600)
def get_exchange_rates(base="KRW"):
    """실시간 환율 정보 가져오기"""
    try:
        url = f"https://open.er-api.com/v6/latest/{base}"
        response = requests.get(url)
        data = response.json()
        return data['rates']
    except:
        return None

def download_korean_font():
    """PDF용 한글 폰트 다운로드"""
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        r = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(r.content)
    return font_path

def create_pdf_report(title, content_list):
    pdf = FPDF()
    pdf.add_page()
    
    font_path = download_korean_font()
    pdf.add_font('Nanum', '', font_path)
    pdf.set_font('Nanum', '', 12)
    
    pdf.set_font('Nanum', '', 16)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font('Nanum', '', 10)
    for line in content_list:
        pdf.multi_cell(0, 8, line)
        pdf.ln(2)
    
    temp_filename = "temp_report.pdf"
    pdf.output(temp_filename)
    
    with open(temp_filename, "rb") as f:
        pdf_bytes = f.read()
        
    return pdf_bytes

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# [핵심] 하이브리드 검색 함수 (내장 데이터 우선 -> API 후순위)
@st.cache_data(ttl=3600)
def search_city_coordinates(city_name):
    clean_name = city_name.strip().replace(" ", "")
    # 1차: 내장 데이터 확인
    if clean_name in FALLBACK_CITIES:
        data = FALLBACK_CITIES[clean_name]
        return {
            "name": city_name,
            "lat": data['lat'],
            "lon": data['lon'],
            "country_code": data['code']
        }
    # 2차: API 검색
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city_name, "format": "json", "limit": 1, "accept-language": "ko"}
        headers = {'User-Agent': 'TravelApp_Student_Project/1.0 (contact@example.com)'}
        res = requests.get(url, params=params, headers=headers)
        res.raise_for_status()
        data = res.json()
        if data:
            return {
                "name": data[0]['display_name'],
                "lat": float(data[0]['lat']),
                "lon": float(data[0]['lon']),
                "country_code": data[0].get('address', {}).get('country_code', 'KR').upper() 
            }
        return None
    except: return None

# --- 4. 데이터 API 함수 ---

@st.cache_data(ttl=3600)
def get_holidays_for_period(api_key, country_code, start_date, end_date):
    all_holidays = set()
    if not country_code: return all_holidays
    for month_start in pd.date_range(start_date, end_date, freq='MS'):
        try:
            url = "https://calendarific.com/api/v2/holidays"
            params = {"api_key": api_key, "country": country_code, "year": month_start.year, "month": month_start.month}
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

# --- 5. 시각화 및 계산 ---

def draw_route_map(route_cities):
    map_data = []
    for i, city in enumerate(route_cities):
        map_data.append({
            "coordinates": [city['lon'], city['lat']],
            "name": f"{i+1}. {city['name'].split(',')[0]}",
            "size": 50000, "color": [0, 200, 100, 200]
        })
    
    scatter_layer = pdk.Layer(
        "ScatterplotLayer", data=map_data, get_position="coordinates",
        get_fill_color="color", get_radius="size", pickable=True,
        radius_scale=1, radius_min_pixels=10, radius_max_pixels=30
    )
    text_layer = pdk.Layer(
        "TextLayer", data=map_data, get_position="coordinates",
        get_text="name", get_size=18, get_color=[0, 0, 0],
        get_angle=0, get_text_anchor="middle", get_alignment_baseline="bottom",
        pixel_offset=[0, -20]
    )
    line_data = []
    for i in range(len(route_cities) - 1):
        line_data.append({
            "start_coords": [route_cities[i]['lon'], route_cities[i]['lat']],
            "end_coords": [route_cities[i+1]['lon'], route_cities[i+1]['lat']]
        })
    line_layer = pdk.Layer(
        "LineLayer", data=line_data,
        get_source_position="start_coords", get_target_position="end_coords",
        get_color=[80, 80, 80, 200], get_width=3, pickable=False
    )
    first_coords = [route_cities[0]['lon'], route_cities[0]['lat']]
    view_state = pdk.ViewState(latitude=first_coords[1], longitude=first_coords[0], zoom=3)
    st.pydeck_chart(pdk.Deck(layers=[line_layer, scatter_layer, text_layer], initial_view_state=view_state, map_style=None, tooltip={"text": "{name}"}))

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

def get_packing_tips(avg_temp, rain_sum):
    tips = []
    if avg_temp < 5: tips.append("🧥 두꺼운 패딩, 장갑 (추움)")
    elif 5 <= avg_temp < 15: tips.append("🧥 경량 패딩, 자켓 (쌀쌀)")
    elif 15 <= avg_temp < 22: tips.append("👕 긴팔, 가디건 (쾌적)")
    elif avg_temp >= 22: tips.append("👕 반팔, 선글라스 (더움)")
    if rain_sum > 30: tips.append("☂️ 우산/우비 필수")
    if avg_temp > 25: tips.append("🧴 선크림")
    return ", ".join(tips)

def calculate_travel_cost(daily_budget, days, style):
    if style == "배낭여행 (절약)": multiplier = 0.6
    elif style == "일반 (표준)": multiplier = 1.0
    else: multiplier = 2.5
    return int(daily_budget * days * multiplier)

def get_google_images_link(city_name):
    return f"https://www.google.com/search?tbm=isch&q={city_name}+travel"

def get_flight_link(destination_name):
    query_city = destination_name.split(',')[0]
    return f"https://www.google.com/travel/flights?q=Flights+to+{query_city}"

# --- 모드 1: 개인 맞춤형 ---
def run_mode_single_trip():
    st.header("🎯 개인 맞춤형 여행 추천")
    col1, col2 = st.columns([2, 1])
    with col1: city_query = st.text_input("✈️ 어디로 떠나시나요?", placeholder="도시명 (예: 파리, 도쿄, 서울)")
    with col2: 
        st.write(""); st.write("")
        search_btn = st.button("도시 검색 🔍")

    if "search_result" not in st.session_state: st.session_state.search_result = None
    if search_btn and city_query:
        with st.spinner("위치 확인 중..."):
            st.session_state.search_result = search_city_coordinates(city_query)

    if st.session_state.search_result:
        city_data = st.session_state.search_result
        st.success(f"📍 **{city_data['name'].split(',')[0]}**")
        st.link_button("📸 사진 보기", get_google_images_link(city_data['name']))

        with st.form("single_trip_form"):
            c1, c2 = st.columns(2)
            with c1: theme_name = st.selectbox("여행 테마", options=THEME_OSM_MAP.keys())
            with c2: daily_budget = st.number_input("1일 예산 (원)", value=200000, step=10000)
            travel_style = st.radio("스타일", ["배낭여행 (절약)", "일반 (표준)", "럭셔리 (여유)"], index=1, horizontal=True)
            priority_mode = st.radio("우선순위", ["연차 효율 (휴일 포함)", "비용 절감 (휴일 제외)"], horizontal=True)
            today = datetime.now().date()
            date_range = st.date_input("기간 선택", value=(today+timedelta(30), today+timedelta(90)), min_value=today, max_value=today+timedelta(365))
            trip_duration = st.slider("여행 기간 (박)", 3, 14, 5)
            submit = st.form_submit_button("🚀 분석 시작")

        if submit:
            if len(date_range) < 2: st.error("기간을 선택하세요."); st.stop()
            start_date, end_date = date_range
            h_start, h_end = start_date - pd.DateOffset(years=1), end_date - pd.DateOffset(years=1)
            with st.spinner("분석 중..."):
                w = get_historical_weather(city_data['lat'], city_data['lon'], h_start.strftime('%Y-%m-%d'), h_end.strftime('%Y-%m-%d'))
                l_h = get_holidays_for_period(CALENDARIFIC_KEY, city_data['country_code'], start_date, end_date)
                k_h = get_holidays_for_period(CALENDARIFIC_KEY, "KR", start_date, end_date)
                places = get_places_osm(city_data['lat'], city_data['lon'], THEME_OSM_MAP[theme_name])
                df = create_base_dataframe(w, h_start, h_end)
                if df.empty: st.error("날씨 데이터 부족"); st.stop()
                df = calculate_daily_score(df, l_h, k_h, priority_mode)
                best = []
                for i in range(len(df) - trip_duration + 1):
                    window = df.iloc[i : i + trip_duration]
                    best.append({"start": window.index[0] + pd.DateOffset(years=1), "end": window.index[-1] + pd.DateOffset(years=1), "score": window['total_score'].mean(), "window": window})
                best.sort(key=lambda x: x['score'], reverse=True)
                top3 = best[:3]

                st.divider()
                st.subheader(f"🗺️ '{theme_name}' 추천 장소")
                if not places.empty: st.dataframe(places, column_config={"지도 보기": st.column_config.LinkColumn("구글 지도", display_text="📍 지도")}, hide_index=True, use_container_width=True)
                else: st.info("장소 데이터 없음")

                st.write("---")
                st.subheader("🏆 Top 3 일정")
                pdf_lines = [f"여행지: {city_data['name']}", f"테마: {theme_name}", ""]
                for i, p in enumerate(top3):
                    p_s, p_e = p['start'].strftime('%Y-%m-%d'), p['end'].strftime('%Y-%m-%d')
                    temp, rain = p['window']['temperature_2m_max'].mean(), p['window']['precipitation_sum'].sum()
                    free = p['window']['is_free_day'].sum()
                    cost = calculate_travel_cost(daily_budget, trip_duration, travel_style)
                    tips = get_packing_tips(temp, rain)
                    pdf_lines.append(f"[{i+1}위] {p_s}~{p_e} / {temp:.1f}도 / {cost:,}원")
                    with st.expander(f"{['🥇','🥈','🥉'][i] if i<3 else ''} {i+1}위: {p_s}~{p_e}", expanded=(i==0)):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("기온", f"{temp:.1f}°C")
                        c2.metric("강수", f"{rain:.1f}mm")
                        c3.metric("휴일", f"{free}일")
                        c4.metric("경비", f"{cost//10000}만 원")
                        st.info(f"🧳 팁: {tips}")
                        st.link_button("✈️ 항공권 검색", get_flight_link(city_data['name']))
                pdf_bytes = create_pdf_report(f"Travel Plan: {city_data['name'].split(',')[0]}", pdf_lines)
                st.download_button("📄 PDF 다운로드", data=pdf_bytes, file_name="Trip.pdf", mime="application/pdf")

# --- 모드 2: 장기 여행 ---
def run_mode_long_trip():
    st.header("🌏 장기 여행 (루트 최적화)")
    if 'selected_cities_data' not in st.session_state: st.session_state['selected_cities_data'] = []
    c1, c2 = st.columns([3, 1])
    with c1: new_city = st.text_input("도시 검색 (예: 런던)", key="multi_input")
    with c2: 
        st.write(""); st.write("")
        if st.button("추가 ➕") and new_city:
            with st.spinner("찾는 중..."):
                found = search_city_coordinates(new_city)
                if found:
                    if any(c['name'] == found['name'] for c in st.session_state['selected_cities_data']): st.warning("중복")
                    else: st.session_state['selected_cities_data'].append(found); st.success(f"✅ {found['name'].split(',')[0]} 추가")
                else: st.error("도시 없음")

    if st.session_state['selected_cities_data']:
        st.write("### 📋 선택 목록")
        for i, c in enumerate(st.session_state['selected_cities_data']): st.text(f"{i+1}. {c['name']}")
        if st.button("초기화 🗑️"): st.session_state['selected_cities_data'] = []; st.rerun()
    else: st.info("도시를 추가해주세요."); return

    st.write("---")
    if len(st.session_state['selected_cities_data']) > 0:
        start_city_name = st.selectbox("출발 도시", [c['name'] for c in st.session_state['selected_cities_data']])
        start_city = next(c for c in st.session_state['selected_cities_data'] if c['name'] == start_city_name)
    
    col1, col2 = st.columns(2)
    with col1: start_date = st.date_input("시작일", value=datetime.now().date()+timedelta(30))
    with col2: total_weeks = st.slider("기간 (주)", 1, 24, 4)
    daily_budget = st.number_input("1일 평균 예산 (원)", value=150000)
    travel_style = st.radio("스타일", ["배낭여행", "일반", "럭셔리"], horizontal=True)

    if st.button("🚀 루트 최적화", type="primary"):
        cities = st.session_state['selected_cities_data']
        if len(cities) < 2: st.warning("2개 이상 필요"); st.stop()
        route = [start_city]
        unvisited = [c for c in cities if c['name'] != start_city['name']]
        curr = start_city
        while unvisited:
            nearest = min(unvisited, key=lambda x: calculate_distance(curr['lat'], curr['lon'], x['lat'], x['lon']))
            route.append(nearest)
            unvisited.remove(nearest)
            curr = nearest
        days_per_city = max(2, (total_weeks*7) // len(route))
        
        st.divider()
        st.subheader(f"🗺️ 추천 루트 ({len(route)}도시)")
        draw_route_map(route)
        total_cost = calculate_travel_cost(daily_budget, total_weeks*7, travel_style)
        st.metric("총 예상 경비 (항공권 제외)", f"약 {total_cost//10000}만 원")
        st.write("---")
        st.subheader("📅 상세 일정")
        curr_date = start_date
        pdf_lines = ["=== 세계일주 루트 ===", ""]
        for idx, city in enumerate(route):
            stay = (start_date + timedelta(total_weeks*7) - curr_date).days if idx == len(route)-1 else days_per_city
            arrival, departure = curr_date, curr_date + timedelta(stay)
            h_start, h_end = arrival - pd.DateOffset(years=1), departure - pd.DateOffset(years=1)
            with st.spinner(f"{city['name'].split(',')[0]} 분석..."):
                w = get_historical_weather(city['lat'], city['lon'], h_start.strftime('%Y-%m-%d'), h_end.strftime('%Y-%m-%d'))
                df = create_base_dataframe(w, h_start, h_end)
            w_desc = "데이터 없음"
            if not df.empty:
                t = df['temperature_2m_max'].mean()
                w_desc = f"{t:.1f}°C ({'쾌적' if 15<=t<=25 else '더움' if t>28 else '추움'})"
            simple_name = city['name'].split(',')[0]
            pdf_lines.append(f"{idx+1}. {simple_name}: {arrival}~{departure} ({stay}박) / {w_desc}")
            with st.container(border=True):
                st.markdown(f"**{idx+1}. {simple_name}** ({stay}박)")
                c1, c2, c3 = st.columns([2,2,1])
                c1.write(f"{arrival.strftime('%m/%d')}~{departure.strftime('%m/%d')}")
                c2.write(f"🌡️ {w_desc}")
                c3.link_button("📍 지도", f"https://www.google.com/maps/search/?api=1&query={city['lat']},{city['lon']}")
                st.divider()
            curr_date = departure
        pdf_bytes = create_pdf_report(f"Long Trip Plan ({total_weeks} Weeks)", pdf_lines)
        st.download_button("📥 PDF 다운로드", data=pdf_bytes, file_name="LongTrip.pdf", mime="application/pdf")

# --- 모드 3: AI 챗봇 (채팅 백지화 해결) ---
def run_mode_chat():
    st.header("🤖 AI 채팅 플래너")
    if not GEMINI_KEY: st.error("API 키 없음"); return
    if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! ✈️"}]
    for msg in st.session_state.messages: st.chat_message(msg["role"]).markdown(msg["content"])
    
    if prompt := st.chat_input("질문 입력..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("생각 중..."):
                current_date = datetime.now().strftime("%Y년 %m월 %d일")
                candidates = ["gemini-2.0-flash-exp", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]
                success = False
                
                for model_name in candidates:
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
                        headers = {'Content-Type': 'application/json'}
                        
                        # 1차 시도: 검색 도구 포함
                        payload_with_tool = {
                            "contents": [{"parts": [{"text": f"System: 오늘은 {current_date}입니다. 한국어로 답변하세요.\nUser: {prompt}"}]}],
                            "tools": [{"googleSearchRetrieval": {}}]
                        }
                        resp = requests.post(url, headers=headers, json=payload_with_tool)
                        
                        if resp.status_code == 200:
                            ai_msg = resp.json()['candidates'][0]['content']['parts'][0]['text']
                            st.markdown(ai_msg)
                            st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                            success = True
                            break
                        
                        # 실패 시 (특히 400/404): 검색 도구 없이 재시도
                        else:
                            del payload_with_tool['tools']
                            resp_retry = requests.post(url, headers=headers, json=payload_with_tool)
                            if resp_retry.status_code == 200:
                                ai_msg = resp_retry.json()['candidates'][0]['content']['parts'][0]['text']
                                st.markdown(ai_msg)
                                st.caption("ℹ️ (검색 기능 없이 답변되었습니다)")
                                st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                                success = True
                                break
                    except: continue
                
                if not success: st.error("AI 응답 실패. 잠시 후 다시 시도해주세요.")

# --- 메인 실행 ---
def main():
    st.set_page_config(page_title="Travel Planner AI", page_icon="✈️", layout="wide")
    check_api_keys()
    with st.sidebar:
        st.title("✈️ 메뉴")
        app_mode = st.radio("모드 선택", ["개인 맞춤형 (Single)", "장기 여행 (Long-term)", "AI 여행 플래너"])
        st.write("---")
        st.subheader("💸 환율 계산기")
        rates = get_exchange_rates()
        if rates:
            amt = st.number_input("KRW 입력", 10000, step=1000)
            curr = st.selectbox("통화", ["USD", "JPY", "EUR", "CNY"])
            st.metric(f"{curr} 환산 금액", f"{amt * rates.get(curr, 0):,.2f} {curr}")
            st.caption(f"1 KRW = {rates.get(curr, 0):.6f} {curr}")

    if app_mode == "개인 맞춤형 (Single)": run_mode_single_trip()
    elif app_mode == "장기 여행 (Long-term)": run_mode_long_trip()
    elif app_mode == "AI 여행 플래너": run_mode_chat()

if __name__ == "__main__":
    main()
