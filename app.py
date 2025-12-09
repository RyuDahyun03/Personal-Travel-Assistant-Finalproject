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
import json

# --- 설정: 테마 매핑 ---
THEME_OSM_MAP = {
    "미식 🍜": '"amenity"="restaurant"',
    "쇼핑 🛍️": '"shop"="mall"',
    "문화/유적 🏯": '"tourism"="attraction"',
    "휴양/공원 🌳": '"leisure"="park"'
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

# --- 1. 내장 도시 데이터 (JSON 파일 로드) ---
@st.cache_data
def load_fallback_cities():
    file_path = "city_coordinates.json"
    if not os.path.exists(file_path):
        return {} 
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

FALLBACK_CITIES = load_fallback_cities()

@st.cache_data(ttl=3600)
def search_city_coordinates(city_name):
    clean_name = city_name.strip().replace(" ", "")
    # JSON 파일에서 먼저 검색
    if clean_name in FALLBACK_CITIES:
        data = FALLBACK_CITIES[clean_name]
        return {"name": city_name, "lat": data['lat'], "lon": data['lon'], "country_code": data['code']}
    # 없으면 OSM API 검색
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
        df['score_free'] = df['is_free_day'].astype(int) * 5
    df['total_score'] = df['score_weather'] + df['score_rain'] + df['score_busy'] + df['score_free']
    return df

def get_packing_tips(avg_temp, rain_sum):
    tips = []
    if avg_temp < 5: tips.append("🧥 패딩, 장갑 (추움)")
    elif 5 <= avg_temp < 15: tips.append("🧥 경량 패딩, 자켓 (쌀쌀)")
    elif 15 <= avg_temp < 22: tips.append("👕 긴팔, 가디건 (쾌적)")
    elif avg_temp >= 22: tips.append("👕 반팔, 선글라스 (더움)")
    if rain_sum > 30: tips.append("☂️ 우산/우비 필수")
    if avg_temp > 25: tips.append("🧴 선크림")
    return ", ".join(tips)

def calculate_travel_cost(daily_budget, days, style):
    multiplier = 0.6 if style == "배낭여행 (절약)" else (1.0 if style == "일반 (표준)" else 2.5)
    return int(daily_budget * days * multiplier)

def get_google_images_link(city_name):
    return f"https://www.google.com/search?tbm=isch&q={city_name}+travel"

def get_flight_link(destination_name):
    return f"https://www.google.com/travel/flights?q=Flights+to+{destination_name.split(',')[0]}"

def draw_route_map(route_cities):
    map_data = []
    for i, city in enumerate(route_cities):
        map_data.append({"coordinates": [city['lon'], city['lat']], "name": f"{i+1}. {city['name'].split(',')[0]}", "size": 50000, "color": [0, 200, 100, 200]})
    scatter_layer = pdk.Layer("ScatterplotLayer", data=map_data, get_position="coordinates", get_fill_color="color", get_radius="size", pickable=True, radius_scale=1, radius_min_pixels=10, radius_max_pixels=30)
    text_layer = pdk.Layer("TextLayer", data=map_data, get_position="coordinates", get_text="name", get_size=18, get_color=[0, 0, 0], get_angle=0, get_text_anchor="middle", get_alignment_baseline="bottom", pixel_offset=[0, -20])
    line_data = [{"start_coords": [route_cities[i]['lon'], route_cities[i]['lat']], "end_coords": [route_cities[i+1]['lon'], route_cities[i+1]['lat']]} for i in range(len(route_cities)-1)]
    line_layer = pdk.Layer("LineLayer", data=line_data, get_source_position="start_coords", get_target_position="end_coords", get_color=[80, 80, 80, 200], get_width=3)
    view_state = pdk.ViewState(latitude=route_cities[0]['lat'], longitude=route_cities[0]['lon'], zoom=3)
    st.pydeck_chart(pdk.Deck(layers=[line_layer, scatter_layer, text_layer], initial_view_state=view_state, map_style=None, tooltip={"text": "{name}"}))

# --- 실행 함수들 ---

# 단기 여행: 엔터 검색 및 입력창 초기화 적용
def run_mode_single_trip():
    st.header("🧳 개인 맞춤형 여행 추천")

    # 콜백 함수: 검색 실행 및 입력창 초기화
    def handle_search():
        query = st.session_state.single_city_input
        if query:
            with st.spinner("위치 확인 중..."):
                st.session_state.search_result = search_city_coordinates(query)
            st.session_state.single_city_input = ""  # 입력창 초기화

    if "search_result" not in st.session_state: st.session_state.search_result = None

    c1, c2 = st.columns([3, 1], vertical_alignment="bottom") 
    with c1: 
        # on_change로 엔터 입력 시 검색 실행
        st.text_input("✈️ 어디로 떠나시나요?", placeholder="도시명 (예: 파리, 도쿄)", key="single_city_input", on_change=handle_search)
    with c2: 
        # 버튼 클릭 시에도 동일한 로직 실행
        st.button("도시 검색 🔍", on_click=handle_search, use_container_width=True)

    if st.session_state.search_result:
        city_data = st.session_state.search_result
        st.success(f"📍 **{city_data['name'].split(',')[0]}**")
        st.link_button("📸 사진 보기", get_google_images_link(city_data['name']))

        with st.form("single"):
            c1, c2 = st.columns(2)
            with c1: theme = st.selectbox("테마", options=THEME_OSM_MAP.keys())
            with c2: budget = st.number_input("1일 예산 (원)", 200000, step=10000)
            style = st.radio("스타일", ["절약", "일반", "럭셔리"], index=1, horizontal=True)
            mode = st.radio("우선순위", ["연차 효율 (휴일 포함)", "비용 절감 (휴일 제외)"], horizontal=True)
            today = datetime.now().date()
            dates = st.date_input("기간", value=(today+timedelta(30), today+timedelta(90)), min_value=today, max_value=today+timedelta(365))
            dur = st.slider("여행 기간 (박)", 3, 14, 5)
            submit = st.form_submit_button("🚀 분석 시작")

        if submit:
            if len(dates) < 2: st.error("기간을 선택하세요."); st.stop()
            s, e = dates
            hs, he = s - pd.DateOffset(years=1), e - pd.DateOffset(years=1)
            with st.spinner("분석 중..."):
                w = get_historical_weather(city_data['lat'], city_data['lon'], hs.strftime('%Y-%m-%d'), he.strftime('%Y-%m-%d'))
                lh = get_holidays_for_period(CALENDARIFIC_KEY, city_data['country_code'], s, e)
                kh = get_holidays_for_period(CALENDARIFIC_KEY, "KR", s, e)
                places = get_places_osm(city_data['lat'], city_data['lon'], THEME_OSM_MAP[theme])
                df = create_base_dataframe(w, hs, he)
                if df.empty: st.error("데이터 부족"); st.stop()
                df = calculate_daily_score(df, lh, kh, mode)
                best = []
                for i in range(len(df) - dur + 1):
                    win = df.iloc[i : i + dur]
                    best.append({"s": win.index[0]+pd.DateOffset(years=1), "e": win.index[-1]+pd.DateOffset(years=1), "scr": win['total_score'].mean(), "win": win})
                best.sort(key=lambda x: x['scr'], reverse=True)
                top3 = best[:3]

                st.divider()
                st.subheader(f"🗺️ '{theme}' 추천 장소")
                if not places.empty: st.dataframe(places, column_config={"지도 보기": st.column_config.LinkColumn("구글 지도", display_text="📍 지도")}, hide_index=True)
                else: st.info("장소 데이터 없음")
                
                st.write("---")
                st.subheader("🏆 Top 3 일정")
                pdf_list = [f"도시: {city_data['name']}", f"테마: {theme}", ""]
                for i, p in enumerate(top3):
                    ps, pe = p['s'].strftime('%Y-%m-%d'), p['e'].strftime('%Y-%m-%d')
                    tm, rn = p['win']['temperature_2m_max'].mean(), p['win']['precipitation_sum'].sum()
                    fr = p['win']['is_free_day'].sum()
                    co = calculate_travel_cost(budget, dur, style)
                    tp = get_packing_tips(tm, rn)
                    pdf_list.append(f"[{i+1}위] {ps}~{pe} / {tm:.1f}도 / {co:,}원")
                    with st.expander(f"{['🥇','🥈','🥉'][i] if i<3 else ''} {i+1}위: {ps}~{pe}", expanded=(i==0)):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("기온", f"{tm:.1f}°C")
                        c2.metric("강수", f"{rn:.1f}mm")
                        c3.metric("휴일", f"{fr}일")
                        c4.metric("경비", f"{co//10000}만 원")
                        st.info(f"🧳 {tp}")
                        st.link_button("✈️ 항공권 검색", get_flight_link(city_data['name']))
                
                p_bytes = create_pdf_report(f"Travel Plan: {city_data['name'].split(',')[0]}", pdf_list)
                st.download_button("📄 PDF 다운로드", p_bytes, "Trip.pdf", "application/pdf")

# 장기 여행: 엔터 추가, 입력창 초기화 + 거리 효율성 리포트 추가
def run_mode_long_trip():
    st.header("🌏 장기 여행 (루트 최적화)")
    if 'selected_cities_data' not in st.session_state: st.session_state['selected_cities_data'] = []

    # 콜백 함수: 도시 추가 및 입력창 초기화
    def handle_add_city():
        new_city = st.session_state.multi_input_key
        if new_city:
            with st.spinner("찾는 중..."):
                found = search_city_coordinates(new_city)
                if found:
                    if any(c['name'] == found['name'] for c in st.session_state['selected_cities_data']):
                        st.toast("⚠️ 이미 추가된 도시입니다.")
                    else:
                        st.session_state['selected_cities_data'].append(found)
                        st.toast(f"✅ {found['name'].split(',')[0]} 추가 완료!")
                else:
                    st.toast("❌ 도시를 찾을 수 없습니다.")
            st.session_state.multi_input_key = "" 

    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    with c1: 
        st.text_input("도시 검색 (예: 런던, 파리)", key="multi_input_key", on_change=handle_add_city)
    with c2: 
        st.button("추가 ➕", on_click=handle_add_city, use_container_width=True)
    
    if st.session_state['selected_cities_data']:
        st.write("### 📋 선택 목록 (입력 순서)")
        for i, c in enumerate(st.session_state['selected_cities_data']): 
            st.text(f"{i+1}. {c['name']}")
        if st.button("초기화 🗑️"): st.session_state['selected_cities_data'] = []; st.rerun()
    else: st.info("도시를 추가해주세요."); return

    st.write("---")
    if len(st.session_state['selected_cities_data']) > 0:
        start_city_name = st.selectbox("출발 도시", [c['name'] for c in st.session_state['selected_cities_data']])
        start_city = next(c for c in st.session_state['selected_cities_data'] if c['name'] == start_city_name)
    
    col1, col2 = st.columns(2)
    with col1: start_date = st.date_input("시작일", value=datetime.now().date()+timedelta(30))
    with col2: total_weeks = st.slider("기간 (주)", 1, 24, 4)
    daily_budget = st.number_input("1일 예산 (원)", 150000)
    travel_style = st.radio("스타일", ["절약", "일반", "럭셔리"], horizontal=True)

    if st.button("🚀 루트 최적화", type="primary"):
        cities = st.session_state['selected_cities_data']
        if len(cities) < 2: st.warning("2개 이상 필요"); st.stop()

        # 1. 원래 순서 (사용자가 입력한 순서 + 출발지 고려)
        original_route = [start_city] + [c for c in cities if c['name'] != start_city['name']]
        
        # 원래 거리 계산
        dist_original = 0
        for i in range(len(original_route)-1):
            dist_original += calculate_distance(original_route[i]['lat'], original_route[i]['lon'], original_route[i+1]['lat'], original_route[i+1]['lon'])

        # 2. 최적화 알고리즘 (Nearest Neighbor)
        route = [start_city]
        unvisited = [c for c in cities if c['name'] != start_city['name']]
        curr = start_city
        
        while unvisited:
            nearest = min(unvisited, key=lambda x: calculate_distance(curr['lat'], curr['lon'], x['lat'], x['lon']))
            route.append(nearest)
            unvisited.remove(nearest)
            curr = nearest
        
        # 최적 거리 계산
        dist_optimized = 0
        for i in range(len(route)-1):
            dist_optimized += calculate_distance(route[i]['lat'], route[i]['lon'], route[i+1]['lat'], route[i+1]['lon'])

        # 절감 거리 및 비율
        saved_km = dist_original - dist_optimized
        saved_percent = (saved_km / dist_original * 100) if dist_original > 0 else 0

        # --- 결과 화면 ---
        st.divider()
        st.subheader("📊 루트 효율성 분석")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("기존 총 거리", f"{int(dist_original):,} km")
        m2.metric("최적화된 거리", f"{int(dist_optimized):,} km", delta=f"-{int(saved_km):,} km (절약)", delta_color="inverse")
        m3.metric("예상 항공 비용 절감", "효율적 이동", f"약 {int(saved_percent)}% 단축")

        st.subheader(f"🗺️ 추천 루트 ({len(route)}도시)")
        draw_route_map(route)
        
        total_cost = calculate_travel_cost(daily_budget, total_weeks*7, travel_style)
        st.metric("총 예상 체류 경비 (항공권 제외)", f"약 {total_cost//10000}만 원")

        st.write("---")
        st.subheader("📅 상세 일정")
        curr_date = start_date
        pdf_lines = ["=== 세계일주 루트 ===", "", f"총 거리: {int(dist_optimized):,} km (기존 대비 {int(saved_km):,} km 단축)"]
        
        days_per = max(2, (total_weeks*7) // len(route))
        
        for idx, city in enumerate(route):
            stay = (start_date + timedelta(total_weeks*7) - curr_date).days if idx == len(route)-1 else days_per
            arr, dep = curr_date, curr_date + timedelta(stay)
            hs, he = arr - pd.DateOffset(years=1), dep - pd.DateOffset(years=1)
            with st.spinner(f"{city['name'].split(',')[0]} 분석..."):
                w = get_historical_weather(city['lat'], city['lon'], hs.strftime('%Y-%m-%d'), he.strftime('%Y-%m-%d'))
                df = create_base_dataframe(w, hs, he)
            w_desc = "데이터 없음"
            if not df.empty:
                t = df['temperature_2m_max'].mean()
                w_desc = f"{t:.1f}°C ({'쾌적' if 15<=t<=25 else '더움' if t>28 else '추움'})"
            simple_name = city['name'].split(',')[0]
            pdf_lines.append(f"{idx+1}. {simple_name}: {arr}~{dep} ({stay}박) / {w_desc}")
            with st.container(border=True):
                st.markdown(f"**{idx+1}. {simple_name}** ({stay}박)")
                c1, c2, c3 = st.columns([2,2,1])
                c1.write(f"{arr.strftime('%m/%d')}~{dep.strftime('%m/%d')}")
                c2.write(f"🌡️ {w_desc}")
                c3.link_button("📍 지도", f"https://www.google.com/maps/search/?api=1&query={city['lat']},{city['lon']}")
            curr_date = dep
        p_bytes = create_pdf_report(f"Long Trip ({total_weeks} Weeks)", pdf_lines)
        st.download_button("📥 PDF 다운로드", p_bytes, "LongTrip.pdf", "application/pdf")

def run_mode_chat():
    st.header("🤖 AI Travel Consultant")
    if not GEMINI_KEY: st.error("API 키 없음"); return
    if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! ✈️"}]
    for msg in st.session_state.messages: st.chat_message(msg["role"]).markdown(msg["content"])
    if prompt := st.chat_input("질문 입력..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("생각 중..."):
                curr_date = datetime.now().strftime("%Y-%m-%d")
                candidates = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-pro"]
                success = False
                for model in candidates:
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
                        headers = {'Content-Type': 'application/json'}
                        data = {"contents": [{"parts": [{"text": f"System: Today is {curr_date}. Use search for latest info. Do not write code.\nUser: {prompt}"}]}], "tools": [{"googleSearchRetrieval": {}}]}
                        resp = requests.post(url, headers=headers, json=data)
                        if resp.status_code == 200:
                            ai_msg = resp.json()['candidates'][0]['content']['parts'][0]['text']
                            st.markdown(ai_msg)
                            st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                            success = True; break
                        else:
                            del data['tools']
                            resp = requests.post(url, headers=headers, json=data)
                            if resp.status_code == 200:
                                ai_msg = resp.json()['candidates'][0]['content']['parts'][0]['text']
                                st.markdown(ai_msg); st.caption("ℹ️ 검색 없이 답변")
                                st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                                success = True; break
                    except: continue
                if not success: st.error("AI 연결 실패")

# --- 메인 실행 ---
def main():
    st.set_page_config(page_title="Personal AI Travel Planner", page_icon="✈️", layout="wide")
    check_api_keys()
    with st.sidebar:
        st.title("✈️ 메뉴")
        app_mode = st.radio("모드 선택", ["Short-Term", "Long-Term", "AI Travel Consultant"])
        st.write("---")
        st.subheader("💸 환율 계산기")
        rates = get_exchange_rates()
        if rates:
            amt = st.number_input("KRW 입력", 10000, step=1000)
            curr = st.selectbox("통화", ["USD", "JPY", "EUR", "CNY"])
            st.metric(f"{curr} 환산", f"{amt * rates.get(curr, 0):,.2f}")
    
    if app_mode == "Short-Term": run_mode_single_trip()
    elif app_mode == "Long-Term": run_mode_long_trip()
    elif app_mode == "AI Travel Consultant": run_mode_chat()

if __name__ == "__main__":
    main()
