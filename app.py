import streamlit as st
import requests
import pandas as pd
import math
from datetime import datetime, timedelta
import io
import pydeck as pdk
import time

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

    # [유럽 - 서유럽]
    "🇬🇧 영국 (런던)": {"code": "GB", "city": "London", "coords": "51.5074,-0.1278", "country": "영국", "cost": 280000, "visa": "무비자 (6개월)"},
    "🇬🇧 영국 (에든버러)": {"code": "GB", "city": "Edinburgh", "coords": "55.9533,-3.1883", "country": "영국", "cost": 260000, "visa": "무비자 (6개월)"},
    "🇮🇪 아일랜드 (더블린)": {"code": "IE", "city": "Dublin", "coords": "53.3498,-6.2603", "country": "아일랜드", "cost": 250000, "visa": "무비자 (90일)"},
    "🇫🇷 프랑스 (파리)": {"code": "FR", "city": "Paris", "coords": "48.8566,2.3522", "country": "프랑스", "cost": 250000, "visa": "무비자 (90일)"},
    "🇫🇷 프랑스 (니스)": {"code": "FR", "city": "Nice", "coords": "43.7102,7.2620", "country": "프랑스", "cost": 260000, "visa": "무비자 (90일)"},
    "🇫🇷 프랑스 (리옹)": {"code": "FR", "city": "Lyon", "coords": "45.7640,4.8357", "country": "프랑스", "cost": 200000, "visa": "무비자 (90일)"},
    "🇫🇷 프랑스 (마르세유)": {"code": "FR", "city": "Marseille", "coords": "43.2965,5.3698", "country": "프랑스", "cost": 190000, "visa": "무비자 (90일)"},
    "🇫🇷 프랑스 (보르도)": {"code": "FR", "city": "Bordeaux", "coords": "44.8378,-0.5792", "country": "프랑스", "cost": 190000, "visa": "무비자 (90일)"},
    "🇫🇷 프랑스 (스트라스부르)": {"code": "FR", "city": "Strasbourg", "coords": "48.5734,7.7521", "country": "프랑스", "cost": 180000, "visa": "무비자 (90일)"},
    "🇫🇷 프랑스 (몽생미셸)": {"code": "FR", "city": "Mont Saint-Michel", "coords": "48.6360,-1.5115", "country": "프랑스", "cost": 210000, "visa": "무비자 (90일)"},
    "🇫🇷 프랑스 (아비뇽)": {"code": "FR", "city": "Avignon", "coords": "43.9493,4.8055", "country": "프랑스", "cost": 180000, "visa": "무비자 (90일)"},
    "🇫🇷 프랑스 (콜마르)": {"code": "FR", "city": "Colmar", "coords": "48.0794,7.3585", "country": "프랑스", "cost": 170000, "visa": "무비자 (90일)"},
    "🇧🇪 벨기에 (브뤼셀)": {"code": "BE", "city": "Brussels", "coords": "50.8503,4.3517", "country": "벨기에", "cost": 210000, "visa": "무비자 (90일)"},
    "🇳🇱 네덜란드 (암스테르담)": {"code": "NL", "city": "Amsterdam", "coords": "52.3676,4.9041", "country": "네덜란드", "cost": 230000, "visa": "무비자 (90일)"},

    # [유럽 - 남유럽]
    "🇮🇹 이탈리아 (로마)": {"code": "IT", "city": "Rome", "coords": "41.9028,12.4964", "country": "이탈리아", "cost": 220000, "visa": "무비자 (90일)"},
    "🇮🇹 이탈리아 (피렌체)": {"code": "IT", "city": "Florence", "coords": "43.7696,11.2558", "country": "이탈리아", "cost": 230000, "visa": "무비자 (90일)"},
    "🇮🇹 이탈리아 (베네치아)": {"code": "IT", "city": "Venice", "coords": "45.4408,12.3155", "country": "이탈리아", "cost": 240000, "visa": "무비자 (90일)"},
    "🇪🇸 스페인 (바르셀로나)": {"code": "ES", "city": "Barcelona", "coords": "41.3851,2.1734", "country": "스페인", "cost": 180000, "visa": "무비자 (90일)"},
    "🇪🇸 스페인 (마드리드)": {"code": "ES", "city": "Madrid", "coords": "40.4168,-3.7038", "country": "스페인", "cost": 170000, "visa": "무비자 (90일)"},
    "🇪🇸 스페인 (세비야)": {"code": "ES", "city": "Seville", "coords": "37.3891,-5.9845", "country": "스페인", "cost": 160000, "visa": "무비자 (90일)"},
    "🇵🇹 포르투갈 (리스본)": {"code": "PT", "city": "Lisbon", "coords": "38.7223,-9.1393", "country": "포르투갈", "cost": 160000, "visa": "무비자 (90일)"},
    "🇵🇹 포르투갈 (포르투)": {"code": "PT", "city": "Porto", "coords": "41.1579,-8.6291", "country": "포르투갈", "cost": 150000, "visa": "무비자 (90일)"},
    "🇬🇷 그리스 (아테네)": {"code": "GR", "city": "Athens", "coords": "37.9838,23.7275", "country": "그리스", "cost": 170000, "visa": "무비자 (90일)"},
    "🇬🇷 그리스 (산토리니)": {"code": "GR", "city": "Santorini", "coords": "36.3932,25.4615", "country": "그리스", "cost": 250000, "visa": "무비자 (90일)"},
    "🇹🇷 튀르키예 (이스탄불)": {"code": "TR", "city": "Istanbul", "coords": "41.0082,28.9784", "country": "튀르키예", "cost": 130000, "visa": "무비자 (90일)"},

    # [유럽 - 중부/동부]
    "🇨🇭 스위스 (취리히)": {"code": "CH", "city": "Zurich", "coords": "47.3769,8.5417", "country": "스위스", "cost": 350000, "visa": "무비자 (90일)"},
    "🇨🇭 스위스 (인터라켄)": {"code": "CH", "city": "Interlaken", "coords": "46.6863,7.8632", "country": "스위스", "cost": 330000, "visa": "무비자 (90일)"},
    "🇩🇪 독일 (베를린)": {"code": "DE", "city": "Berlin", "coords": "52.5200,13.4050", "country": "독일", "cost": 190000, "visa": "무비자 (90일)"},
    "🇩🇪 독일 (뮌헨)": {"code": "DE", "city": "Munich", "coords": "48.1351,11.5820", "country": "독일", "cost": 200000, "visa": "무비자 (90일)"},
    "🇩🇪 독일 (프랑크푸르트)": {"code": "DE", "city": "Frankfurt", "coords": "50.1109,8.6821", "country": "독일", "cost": 190000, "visa": "무비자 (90일)"},
    "🇦🇹 오스트리아 (빈)": {"code": "AT", "city": "Vienna", "coords": "48.2082,16.3738", "country": "오스트리아", "cost": 200000, "visa": "무비자 (90일)"},
    "🇨🇿 체코 (프라하)": {"code": "CZ", "city": "Prague", "coords": "50.0755,14.4378", "country": "체코", "cost": 120000, "visa": "무비자 (90일)"},
    "🇭🇺 헝가리 (부다페스트)": {"code": "HU", "city": "Budapest", "coords": "47.4979,19.0402", "country": "헝가리", "cost": 110000, "visa": "무비자 (90일)"},
    "🇭🇷 크로아티아 (두브로브니크)": {"code": "HR", "city": "Dubrovnik", "coords": "42.6507,18.0944", "country": "크로아티아", "cost": 180000, "visa": "무비자 (90일)"},
    "🇭🇷 크로아티아 (자그레브)": {"code": "HR", "city": "Zagreb", "coords": "45.8150,15.9819", "country": "크로아티아", "cost": 130000, "visa": "무비자 (90일)"},

    # [유럽 - 북유럽]
    "🇩🇰 덴마크 (코펜하겐)": {"code": "DK", "city": "Copenhagen", "coords": "55.6761,12.5683", "country": "덴마크", "cost": 260000, "visa": "무비자 (90일)"},
    "🇸🇪 스웨덴 (스톡홀름)": {"code": "SE", "city": "Stockholm", "coords": "59.3293,18.0686", "country": "스웨덴", "cost": 240000, "visa": "무비자 (90일)"},
    "🇳🇴 노르웨이 (오슬로)": {"code": "NO", "city": "Oslo", "coords": "59.9139,10.7522", "country": "노르웨이", "cost": 270000, "visa": "무비자 (90일)"},

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

# --- 2. API 키 확인 및 설정 ---
CALENDARIFIC_KEY = st.secrets.get("calendarific_key")
GEMINI_KEY = st.secrets.get("gemini_key")

def check_api_keys():
    if not CALENDARIFIC_KEY:
        st.sidebar.error("⚠️ Calendarific API 키가 설정되지 않았습니다.")
        st.stop()

# --- 3. 핵심 유틸리티 함수 ---

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@st.cache_data(ttl=3600)
def search_city_coordinates(city_name):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city_name, "format": "json", "limit": 1, "accept-language": "ko"}
        headers = {'User-Agent': 'MyTravelApp/1.0'}
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

# --- 4. API 함수 ---

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
    for i, city_key in enumerate(route_cities):
        city_data = CITY_DATA[city_key]
        # PyDeck은 [경도, 위도] 순서
        coords = list(map(float, city_data['coords'].split(',')))[::-1]
        map_data.append({
            "coordinates": coords,
            "name": f"{i+1}. {city_data['city']}",
            "size": 50000, "color": [0, 200, 100, 200]
        })
    
    # 1. 점 레이어
    scatter_layer = pdk.Layer(
        "ScatterplotLayer", data=map_data, get_position="coordinates",
        get_fill_color="color", get_radius="size", pickable=True,
        radius_scale=1, radius_min_pixels=10, radius_max_pixels=30
    )
    # 2. 텍스트 레이어
    text_layer = pdk.Layer(
        "TextLayer", data=map_data, get_position="coordinates",
        get_text="name", get_size=20, get_color=[0, 0, 0],
        get_angle=0, get_text_anchor="middle", get_alignment_baseline="bottom",
        pixel_offset=[0, -20]
    )
    # 초기 뷰 설정
    first_coords = list(map(float, CITY_DATA[route_cities[0]]['coords'].split(',')))[::-1]
    view_state = pdk.ViewState(latitude=first_coords[1], longitude=first_coords[0], zoom=3)
    
    st.pydeck_chart(pdk.Deck(layers=[scatter_layer, text_layer], initial_view_state=view_state, map_style=None, tooltip={"text": "{name}"}))

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
    return "\n".join([f"- {t}" for t in tips])

def calculate_travel_cost(city_key, days, style):
    base_cost = CITY_DATA[city_key]['cost']
    if style == "배낭여행 (절약)": multiplier = 0.6
    elif style == "일반 (표준)": multiplier = 1.0
    else: multiplier = 2.5
    return int(base_cost * days * multiplier)

def generate_download_content(title, details_text):
    return f"=== 여행 비서 리포트 ===\n{title}\n\n{details_text}"

def get_flight_link(destination_key):
    query_city = CITY_DATA[destination_key]['city']
    return f"https://www.google.com/travel/flights?q=Flights+to+{query_city}"

# --- 모드 1: 개인 맞춤형 ---
def run_mode_single_trip():
    st.header("🎯 모드 1: 개인 맞춤형 여행 추천")
    
    col1, col2 = st.columns(2)
    with col1:
        # [신규] 검색 기능 활성화된 selectbox
        country_key = st.selectbox("어디로 떠날까요? (도시 검색)", options=CITY_DATA.keys())
    with col2:
        theme_name = st.selectbox("여행 테마", options=THEME_OSM_MAP.keys())

    # [신규] 라디오 버튼 스타일
    travel_style = st.radio("여행 스타일 (경비용)", ["배낭여행 (절약)", "일반 (표준)", "럭셔리 (여유)"], index=1, horizontal=True)
    priority_mode = st.radio("우선순위", ["연차 효율 (휴일 포함)", "비용 절감 (휴일 제외)"], horizontal=True)

    today = datetime.now().date()
    st.write("📅 **언제쯤 가시나요?**")
    date_range = st.date_input(
        "기간 선택",
        value=(today+timedelta(30), today+timedelta(90)),
        min_value=today, max_value=today+timedelta(365), format="YYYY-MM-DD"
    )
    trip_duration = st.slider("여행 기간 (박)", 3, 14, 5)

    if st.button("최적 일정 찾기", type="primary"):
        if len(date_range) < 2: st.error("기간을 선택하세요."); st.stop()
        
        country_data = CITY_DATA[country_key]
        lat, lon = country_data["coords"].split(',')
        start_date, end_date = date_range
        hist_start = start_date - pd.DateOffset(years=1)
        hist_end = end_date - pd.DateOffset(years=1)
        
        with st.spinner("분석 중..."):
            weather = get_historical_weather(lat, lon, hist_start.strftime('%Y-%m-%d'), hist_end.strftime('%Y-%m-%d'))
            local_h = get_holidays_for_period(CALENDARIFIC_KEY, country_data["code"], start_date, end_date)
            kr_h = get_holidays_for_period(CALENDARIFIC_KEY, "KR", start_date, end_date)
            places_df = get_places_osm(lat, lon, THEME_OSM_MAP[theme_name])
            
            df = create_base_dataframe(weather, hist_start, hist_end)
            if df.empty: st.error("날씨 데이터 부족"); st.stop()
            
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
            
            st.divider()
            st.info(f"🛂 **비자:** {country_data['visa']}")
            st.subheader(f"🗺️ '{theme_name}' 추천 장소")
            if not places_df.empty: st.dataframe(places_df, column_config={"지도 보기": st.column_config.LinkColumn("구글 지도", display_text="📍 지도")}, hide_index=True, use_container_width=True)
            else: st.info("주변 장소 데이터 없음")

            st.write("---")
            st.subheader("🏆 Best 3 일정")
            download_text = f"목적지: {country_key}\n"

            for i, period in enumerate(top_3):
                p_s = period['start'].strftime('%Y-%m-%d')
                p_e = period['end'].strftime('%Y-%m-%d')
                temp = period['window']['temperature_2m_max'].mean()
                rain = period['window']['precipitation_sum'].sum()
                free = period['window']['is_free_day'].sum()
                cost = calculate_travel_cost(country_key, trip_duration, travel_style)
                tips = get_packing_tips(temp, rain)
                
                download_text += f"[{i+1}위] {p_s}~{p_e} / {temp:.1f}도 / {cost:,}원\n"
                
                with st.expander(f"{['🥇','🥈','🥉'][i] if i<3 else ''} {i+1}위: {p_s}~{p_e} ({period['score']:.0f}점)", expanded=(i==0)):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("기온", f"{temp:.1f}°C")
                    c2.metric("강수", f"{rain:.1f}mm")
                    c3.metric("휴일", f"{free}일")
                    c4.metric("경비", f"{cost//10000}만 원")
                    st.caption(f"💰 {trip_duration}박 ({travel_style})")
                    st.info(f"🧳 **팁:** {tips}")
                    st.link_button("✈️ 항공권 검색", get_flight_link(country_key))

            st.download_button("📥 결과 저장 (TXT)", generate_download_content(f"{country_key} 여행 분석", download_text), f"Trip_{today}.txt")

# --- 모드 2: 장기 여행 ---
def run_mode_long_trip():
    st.header("🌏 모드 2: 장기 여행 (루트 최적화)")
    
    # [신규] 나라 선택으로 필터링
    countries = sorted(list(set([v['country'] for v in CITY_DATA.values()])))
    selected_nations = st.multiselect("나라 선택", countries)
    
    available_cities = [k for k,v in CITY_DATA.items() if v['country'] in selected_nations] if selected_nations else []
    selected_cities = st.multiselect("도시 선택", available_cities, default=available_cities)
    
    if not selected_cities: st.info("나라를 먼저 선택해주세요."); return

    start_city = st.selectbox("출발 도시", selected_cities)
    
    col1, col2 = st.columns(2)
    with col1: start_date = st.date_input("시작일", value=datetime.now().date()+timedelta(30))
    with col2: total_weeks = st.slider("기간 (주)", 1, 12, 4)
    
    travel_style = st.radio("여행 스타일", ["배낭여행 (절약)", "일반 (표준)", "럭셔리 (여유)"], horizontal=True)
    total_days = total_weeks * 7

    if st.button("🚀 루트 최적화", type="primary"):
        if len(selected_cities) < 2: st.warning("2개 이상 필요"); st.stop()

        route = [start_city]
        unvisited = [c for c in selected_cities if c != start_city]
        curr = start_city
        while unvisited:
            curr_coords = CITY_DATA[curr]["coords"]
            nearest = min(unvisited, key=lambda x: calculate_distance(curr_coords, CITY_DATA[x]["coords"]))
            route.append(nearest)
            unvisited.remove(nearest)
            curr = nearest

        days_per_city = max(2, total_days // len(route))
        
        st.divider()
        st.subheader(f"🗺️ 추천 루트 ({len(route)}도시)")
        draw_route_map(route)
        
        total_cost = 0
        visa_list = set()
        dl_text = "[[ 장기 여행 ]]\n"
        
        # 총 비용 계산
        for i, city in enumerate(route):
            stay = (start_date + timedelta(total_days) - start_date).days if i == len(route)-1 else days_per_city # 단순화
            # 실제 날짜별 비용 계산은 복잡하므로 단순 합산
            total_cost += calculate_travel_cost(city, days_per_city, travel_style)
            visa_list.add(f"{CITY_DATA[city]['country']}: {CITY_DATA[city]['visa']}")

        c1, c2 = st.columns(2)
        c1.metric("총 예상 경비", f"약 {total_cost//10000}만 원")
        c2.info("**비자:**\n" + "\n".join([f"- {v}" for v in visa_list]))

        st.write("---")
        st.subheader("📅 상세 일정")
        curr_date = start_date
        
        for idx, city in enumerate(route):
            stay = (start_date + timedelta(total_days) - curr_date).days if idx == len(route)-1 else days_per_city
            arrival, departure = curr_date, curr_date + timedelta(stay)
            
            city_data = CITY_DATA[city]
            lat, lon = city_data["coords"].split(',')
            h_start = arrival - pd.DateOffset(years=1)
            h_end = departure - pd.DateOffset(years=1)
            
            with st.spinner(f"{city} 분석..."):
                w = get_historical_weather(lat, lon, h_start.strftime('%Y-%m-%d'), h_end.strftime('%Y-%m-%d'))
                df = create_base_dataframe(w, h_start, h_end)
            
            w_desc = "데이터 없음"
            if not df.empty:
                t = df['temperature_2m_max'].mean()
                w_desc = f"{t:.1f}°C ({'쾌적' if 15<=t<=25 else '더움' if t>28 else '추움'})"

            dl_text += f"{idx+1}. {city}: {arrival}~{departure} / {w_desc}\n"
            with st.container():
                st.markdown(f"**{idx+1}. {city}** ({stay}박)")
                c1, c2, c3 = st.columns([2,2,1])
                c1.write(f"{arrival.strftime('%m/%d')}~{departure.strftime('%m/%d')}")
                c2.write(f"🌡️ {w_desc}")
                c3.link_button("📍 지도", f"https://www.google.com/maps/search/?api=1&query={lat},{lon}")
                st.divider()
            curr_date = departure

        st.download_button("📥 다운로드", generate_download_content("세계일주", dl_text), "LongTrip.txt")

# --- 모드 3: AI 챗봇 (자동 복구 기능 탑재) ---
def run_mode_chat():
    st.header("🤖 AI 여행 상담소")
    st.caption("여행 계획, 맛집 추천, 현지 문화 등 무엇이든 물어보세요! (Google Gemini 기반)")

    if not GEMINI_KEY:
        st.error("⚠️ `.streamlit/secrets.toml`에 `gemini_key`가 설정되지 않았습니다.")
        return

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 여행에 대해 무엇이든 물어보세요. ✈️"}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("질문을 입력하세요 (예: 12월 도쿄 옷차림 알려줘)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("AI가 생각 중입니다..."):
                # [자동 복구] 사용 가능한 모델 리스트 (우선순위 순서)
                candidates = [
                    "gemini-2.0-flash", # 1순위: 사용자 목록에 있던 최신 모델
                    "gemini-1.5-flash", # 2순위: 일반적인 표준 모델
                    "gemini-pro",       # 3순위: 가장 안정적인 구형 모델
                    "gemini-1.0-pro"    # 4순위: 최후의 수단
                ]
                
                success = False
                last_error = ""
                
                for model_name in candidates:
                    try:
                        # REST API 직접 호출 (라이브러리 의존성 제거)
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
                        headers = {'Content-Type': 'application/json'}
                        data = {
                            "contents": [{"parts": [{"text": prompt}]}]
                        }
                        response = requests.post(url, headers=headers, json=data)
                        
                        if response.status_code == 200:
                            ai_msg = response.json()['candidates'][0]['content']['parts'][0]['text']
                            st.markdown(ai_msg)
                            st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                            success = True
                            break # 성공하면 루프 탈출!
                        else:
                            # 404 등 오류 발생 시 다음 모델 시도
                            last_error = f"{response.status_code} ({model_name})"
                            continue
                    except Exception as e:
                        last_error = str(e)
                        continue
                
                if not success:
                    st.error(f"모든 모델 연결 실패 😢 (마지막 오류: {last_error})")
                    st.info("잠시 후 다시 시도하거나 API 키를 확인해주세요.")

# --- 메인 실행 ---
def main():
    st.set_page_config(page_title="Travel Planner AI", page_icon="✈️", layout="wide")
    check_api_keys()
    
    with st.sidebar:
        st.title("✈️ 여행 비서 AI")
        app_mode = st.radio("메뉴 선택", ["개인 맞춤형 (Single)", "장기 여행 (Long-term)", "AI 상담소 (Chat)"])
        st.write("---")
        st.caption("Made with Streamlit")

    if app_mode == "개인 맞춤형 (Single)":
        run_mode_single_trip()
    elif app_mode == "장기 여행 (Long-term)":
        run_mode_long_trip()
    elif app_mode == "AI 상담소 (Chat)":
        run_mode_chat()

if __name__ == "__main__":
    main()
