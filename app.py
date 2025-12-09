import streamlit as st
import requests
import pandas as pd
import math
from datetime import datetime, timedelta
import pydeck as pdk
from fpdf import FPDF
import os
import time
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO

# --- 설정: 테마 매핑 ---
THEME_OSM_MAP = {
    "미식 🍜": '"amenity"="restaurant"',
    "쇼핑 🛍️": '"shop"="mall"',
    "문화/유적 🏯": '"tourism"="attraction"',
    "휴양/공원 🌳": '"leisure"="park"'
}

# --- 1. 내장 도시 데이터 (1차 방어선 - API 오류 방지용) ---
FALLBACK_CITIES = {
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
    if not GEMINI_KEY:
        st.sidebar.error("⚠️ Gemini API 키가 설정되지 않았습니다.")
        st.stop()

# --- 3. 유틸리티 함수 ---

@st.cache_data(ttl=3600)
def get_exchange_rates(base="KRW"):
    try:
        url = f"https://open.er-api.com/v6/latest/{base}"
        response = requests.get(url)
        data = response.json()
        return data['rates']
    except: return None

def download_korean_font():
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

@st.cache_data(ttl=3600)
def search_city_coordinates(city_name):
    clean_name = city_name.strip().replace(" ", "")
    if clean_name in FALLBACK_CITIES:
        data = FALLBACK_CITIES[clean_name]
        return {"name": city_name, "lat": data['lat'], "lon": data['lon'], "country_code": data['code']}
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city_name, "format": "json", "limit": 1, "accept-language": "ko"}
        headers = {'User-Agent': 'TravelApp_Student_Project/1.0 (contact@example.com)'}
        res = requests.get(url, params=params, headers=headers)
        res.raise_for_status()
        data = res.json()
        if data:
            return {"name": data[0]['display_name'], "lat": float(data[0]['lat']), "lon": float(data[0]['lon']), "country_code": data[0].get('address', {}).get('country_code', 'KR').upper()}
        return None
    except: return None

# [핵심] 다중 이미지 통합 및 색상 추출 (입력값을 파일 리스트로 받아서 처리)
def extract_colors_from_multiple(uploaded_files, num_colors=4):
    if not uploaded_files: return []
    
    resized_images = []
    for uploaded_file in uploaded_files:
        # 파일 포인터를 처음으로 되돌리기 (중요!)
        uploaded_file.seek(0)
        img = Image.open(uploaded_file).convert('RGB')
        img.thumbnail((150, 150))
        resized_images.append(img)
    
    if not resized_images: return []

    total_width = sum(img.width for img in resized_images)
    max_height = max(img.height for img in resized_images)
    combined_image = Image.new('RGB', (total_width, max_height))
    
    x_offset = 0
    for img in resized_images:
        combined_image.paste(img, (x_offset, 0))
        x_offset += img.width
        
    result = combined_image.convert('P', palette=Image.ADAPTIVE, colors=num_colors)
    result = result.convert('RGB')
    main_colors = result.getcolors(total_width * max_height)
    if main_colors:
        main_colors.sort(key=lambda x: x[0], reverse=True)
        return [color[1] for color in main_colors]
    return []

def display_color_palette(colors):
    html_code = '<div style="display: flex; gap: 10px;">'
    for color in colors:
        hex_color = '#{:02x}{:02x}{:02x}'.format(*color)
        html_code += f'<div style="width: 50px; height: 50px; background-color: {hex_color}; border-radius: 50%; border: 2px solid #ddd;" title="{hex_color}"></div>'
    html_code += '</div>'
    st.markdown(html_code, unsafe_allow_html=True)

# [신규] 여행 기록 카드 생성 함수
def create_memory_card(image_file, city_name, date_str, colors):
    # 1. 캔버스 준비 (흰색 배경 폴라로이드 스타일)
    card_width, card_height = 600, 800
    card = Image.new('RGB', (card_width, card_height), 'white')
    draw = ImageDraw.Draw(card)
    
    # 2. 사용자 이미지 로드
    user_img = Image.open(image_file).convert('RGB')
    
    # 이미지 비율 유지하며 맞추기 (여백 40px)
    target_width = card_width - 80
    ratio = target_width / user_img.width
    target_height = int(user_img.height * ratio)
    
    # 세로로 너무 길면 자르기
    if target_height > 550: 
        target_height = 550
        user_img = user_img.resize((target_width, target_height)) # 단순 리사이즈 (크롭X)
    else:
        user_img = user_img.resize((target_width, target_height))

    # 이미지 붙이기
    card.paste(user_img, (40, 40))
    
    # 3. 텍스트 추가 (폰트 로드 시도)
    font_path = download_korean_font()
    try:
        title_font = ImageFont.truetype(font_path, 50)
        date_font = ImageFont.truetype(font_path, 30)
    except:
        title_font = ImageFont.load_default()
        date_font = ImageFont.load_default()
    
    # 도시 이름
    draw.text((40, target_height + 60), city_name, font=title_font, fill='black')
    # 날짜
    draw.text((40, target_height + 120), date_str, font=date_font, fill='gray')
    
    # 4. 팔레트 그리기 (원형)
    start_x = 40
    start_y = target_height + 170
    for color in colors:
        draw.ellipse((start_x, start_y, start_x+50, start_y+50), fill=color, outline='gray')
        start_x += 60
        
    return card

# --- API 함수들 ---
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
                for h in res.json().get("response", {}).get("holidays", []):
                    if h.get("date", {}).get("iso"): all_holidays.add(h["date"]["iso"].split("T")[0])
        except: pass
    return all_holidays

@st.cache_data(ttl=3600)
def get_historical_weather(lat, lon, start, end):
    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {"latitude": lat, "longitude": lon, "start_date": start, "end_date": end, "daily": "temperature_2m_max,precipitation_sum", "timezone": "auto"}
        res = requests.get(url, params=params)
        res.raise_for_status()
        return res.json()
    except: return None

@st.cache_data(ttl=3600)
def get_places_osm(lat, lon, osm_tag):
    try:
        query = f"""[out:json];(node[{osm_tag}](around:3000, {lat}, {lon});way[{osm_tag}](around:3000, {lat}, {lon}););out center 10;"""
        res = requests.get("http://overpass-api.de/api/interpreter", params={'data': query})
        res.raise_for_status()
        data = res.json()
        places = []
        for el in data.get('elements', []):
            name = el.get('tags', {}).get('name')
            if name:
                plat = el.get('lat') or el.get('center', {}).get('lat')
                plon = el.get('lon') or el.get('center', {}).get('lon')
                places.append({"장소명": name, "지도 보기": f"https://www.google.com/maps/search/?api=1&query={plat},{plon}"})
        return pd.DataFrame(places)
    except: return pd.DataFrame()

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
        df['


