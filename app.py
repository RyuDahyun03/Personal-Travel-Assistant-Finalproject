import streamlit as st
import requests
import pandas as pd
import math
from datetime import datetime, timedelta
import pydeck as pdk
from fpdf import FPDF
import os

# --- 설정: 테마 매핑 ---
THEME_OSM_MAP = {
    "미식 🍜": '"amenity"="restaurant"',
    "쇼핑 🛍️": '"shop"="mall"',
    "문화/유적 🏯": '"tourism"="attraction"',
    "휴양/공원 🌳": '"leisure"="park"'
}

# --- 1. API 키 확인 ---
CALENDARIFIC_KEY = st.secrets.get("calendarific_key")
GEMINI_KEY = st.secrets.get("gemini_key")

def check_api_keys():
    if not CALENDARIFIC_KEY:
        st.sidebar.error("⚠️ Calendarific API 키가 설정되지 않았습니다.")
        st.stop()

# --- 2. 유틸리티 함수 (검색, 거리, 환율, PDF) ---

@st.cache_data(ttl=3600)
def get_exchange_rates(base="KRW"):
    """실시간 환율 정보 가져오기 (무료 API)"""
    try:
        url = f"https://open.er-api.com/v6/latest/{base}"
        response = requests.get(url)
        data = response.json()
        return data['rates']
    except:
        return None

def download_korean_font():
    """PDF 생성을 위한 한글 폰트 다운로드 (나눔고딕)"""
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        r = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(r.content)
    return font_path

def create_pdf_report(title, content_list):
    """PDF 리포트 생성 함수"""
    pdf = FPDF()
    pdf.add_page()
    
    # 한글 폰트 등록
    font_path = download_korean_font()
    pdf.add_font('Nanum', '', font_path)
    pdf.set_font('Nanum', '', 12)
    
    # 제목
    pdf.set_font('Nanum', '', 16)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(10)
    
    # 내용
    pdf.set_font('Nanum', '', 10)
    for line in content_list:
        # FPDF는 한글 처리가 까다로워 줄바꿈 처리
        pdf.multi_cell(0, 8, line)
        pdf.ln(2)
        
    return pdf.output(dest='S').encode('latin-1')

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@st.cache_data(ttl=3600)
def search_city_coordinates(city_name):
    """Nominatim API: 전 세계 도시 검색"""
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

# --- 3. 여행 데이터 API ---

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

# --- 4. 시각화 및 점수 계산 ---

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
        pixel_offset=[0, -15]
    )
    
    # 경로 선 그리기
    line_data = []
    for i in range(len(route_cities) - 1):
        line_data.append({
            "start": [route_cities[i]['lon'], route_cities[i]['lat']],
            "end": [route_cities[i+1]['lon'], route_cities[i+1]['lat']]
        })
        
    line_layer = pdk.Layer(
        "LineLayer", data=line_data, get_source_position="start",
        get_target_position="end", get_color=[200, 30, 0, 160], get_width=3
    )

    view_state = pdk.ViewState(latitude=route_cities[0]['lat'], longitude=route_cities[0]['lon'], zoom=3)
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
    if avg_temp < 5: tips.append("🧥 두꺼운 패딩, 목도리, 장갑 (추움)")
    elif 5 <= avg_temp < 15: tips.append("🧥 경량 패딩, 자켓, 히트텍 (쌀쌀)")
    elif 15 <= avg_temp < 22: tips.append("👕 긴팔 티셔츠, 가디건 (쾌적)")
    elif avg_temp >= 22: tips.append("👕 반팔, 반바지, 선글라스 (더움)")
    if rain_sum > 30: tips.append("☂️ 우산 또는 우비 (비 예보)")
    if avg_temp > 25: tips.append("🧴 자외선 차단제, 모자")
    return ", ".join(tips)

def calculate_travel_cost(daily_budget, days, style):
    if style == "배낭여행 (절약)": multiplier = 0.6
    elif style == "일반 (표준)": multiplier = 1.0
    else: multiplier = 2.5
    return int(daily_budget * days * multiplier)

def get_google_images_link(city_name):
    return f"https://www.google.com/search?tbm=isch&q={city_name}+travel"

# --- 사이드바: 환율 계산기 ---
def sidebar_currency_converter():
    with st.sidebar:
        st.markdown("---")
        st.subheader("💸 실시간 환율 계산기")
        rates = get_exchange_rates("KRW") # 원화 기준 가져오기
        
        if rates:
            amount = st.number_input("원화(KRW) 입력", value=10000, step=1000)
            target_currency = st.selectbox("바꿀 통화", ["USD", "JPY", "EUR", "CNY", "VND", "THB", "GBP"])
            
            # API가 KRW 기준이므로, target_currency의 비율을 곱하면 됨 (API 제공값에 따라 역수 계산 필요할 수 있음)
            # Open ER API: Base가 KRW면 -> 1 KRW = X USD
            rate = rates.get(target_currency)
            if rate:
                converted = amount * rate
                st.metric(f"{target_currency} 환산 금액", f"{converted:,.2f} {target_currency}")
                st.caption(f"적용 환율: 1 KRW = {rate} {target_currency}")
        else:
            st.error("환율 정보를 가져올 수 없습니다.")
        st.markdown("---")
        st.caption("Made with Streamlit")

# --- 모드 1: 개인 맞춤형 ---
def run_mode_single_trip():
    st.header("🎯 개인 맞춤형 여행 추천")
    st.info("원하는 도시를 검색하면 최적의 시기를 알려드립니다.")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        city_query = st.text_input("✈️ 어디로 떠나시나요? (도시명 검색)", placeholder="예: 파리, 도쿄, 뉴욕")
    with col2:
        st.write("") # 여백
        st.write("")
        search_btn = st.button("도시 검색 🔍")

    if "search_result" not in st.session_state:
        st.session_state.search_result = None

    if search_btn and city_query:
        with st.spinner("위치 확인 중..."):
            st.session_state.search_result = search_city_coordinates(city_query)

    if st.session_state.search_result:
        city_data = st.session_state.search_result
        st.success(f"📍 선택된 도시: **{city_data['name'].split(',')[0]}**")
        
        # 도시 이미지 보기 버튼
        st.link_button("📸 도시 사진 보기 (Google Images)", get_google_images_link(city_data['name']))

        with st.form("single_trip_form"):
            c1, c2 = st.columns(2)
            with c1: theme_name = st.selectbox("여행 테마", options=THEME_OSM_MAP.keys())
            with c2: daily_budget = st.number_input("1인 1일 평균 예산 (원)", value=200000, step=10000)

            # 스타일 & 우선순위 (가로형)
            travel_style = st.radio("여행 스타일", ["배낭여행 (절약)", "일반 (표준)", "럭셔리 (여유)"], index=1, horizontal=True)
            priority_mode = st.radio("우선순위", ["연차 효율 (휴일 포함)", "비용 절감 (휴일 제외)"], horizontal=True)

            today = datetime.now().date()
            st.write("📅 **여행 가능 기간 (이 범위 내에서 추천)**")
            date_range = st.date_input(
                "달력 선택",
                value=(today+timedelta(30), today+timedelta(90)),
                min_value=today, max_value=today+timedelta(365)
            )
            trip_duration = st.slider("여행 기간 (박)", 3, 14, 5)
            
            submit = st.form_submit_button("🚀 최적 일정 분석 시작")

        if submit:
            if len(date_range) < 2: st.error("기간을 정확히 선택해주세요."); st.stop()
            
            start_date, end_date = date_range
            hist_start = start_date - pd.DateOffset(years=1)
            hist_end = end_date - pd.DateOffset(years=1)
            
            with st.spinner("날씨, 공휴일, 관광지를 분석하고 있습니다..."):
                weather = get_historical_weather(city_data['lat'], city_data['lon'], hist_start.strftime('%Y-%m-%d'), hist_end.strftime('%Y-%m-%d'))
                local_h = get_holidays_for_period(CALENDARIFIC_KEY, city_data['country_code'], start_date, end_date)
                kr_h = get_holidays_for_period(CALENDARIFIC_KEY, "KR", start_date, end_date)
                places_df = get_places_osm(city_data['lat'], city_data['lon'], THEME_OSM_MAP[theme_name])
                
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

                # --- 결과 출력 (UI 개선) ---
                st.divider()
                st.subheader(f"🗺️ '{theme_name}' 추천 장소")
                if not places_df.empty:
                    st.dataframe(
                        places_df, 
                        column_config={"지도 보기": st.column_config.LinkColumn("구글 지도", display_text="📍 지도")}, 
                        hide_index=True, 
                        use_container_width=True
                    )
                else:
                    st.info("주변 장소 데이터 없음")

                st.write("---")
                st.subheader("🏆 최적의 여행 시기 Top 3")
                
                pdf_content = [f"여행지: {city_data['name']}", f"테마: {theme_name}", f"스타일: {travel_style}", ""]

                for i, period in enumerate(top_3):
                    p_s = period['start'].strftime('%Y-%m-%d')
                    p_e = period['end'].strftime('%Y-%m-%d')
                    temp = period['window']['temperature_2m_max'].mean()
                    rain = period['window']['precipitation_sum'].sum()
                    free = period['window']['is_free_day'].sum()
                    cost = calculate_travel_cost(daily_budget, trip_duration, travel_style)
                    tips = get_packing_tips(temp, rain)
                    
                    # PDF 내용 추가
                    pdf_content.append(f"[{i+1}순위] {p_s} ~ {p_e}")
                    pdf_content.append(f" - 기온: {temp:.1f}도 / 강수: {rain:.1f}mm")
                    pdf_content.append(f" - 예상 경비: 약 {cost:,}원")
                    pdf_content.append(f" - 팁: {tips}")
                    pdf_content.append("")
                    
                    # 카드 UI
                    with st.container(border=True):
                        cols = st.columns([1, 3])
                        with cols[0]:
                            st.metric(f"{['🥇','🥈','🥉'][i]} {i+1}위", f"{period['score']:.0f}점")
                        with cols[1]:
                            st.markdown(f"### {p_s} ~ {p_e}")
                            c1, c2, c3 = st.columns(3)
                            c1.write(f"🌡️ **{temp:.1f}°C**")
                            c2.write(f"☔ **{rain:.1f}mm**")
                            c3.write(f"💰 **약 {cost//10000}만원**")
                            st.caption(f"🧳 {tips}")
                            
                            flight_q = city_data['name'].split(',')[0]
                            st.link_button("✈️ 항공권 가격 보기", f"https://www.google.com/travel/flights?q=Flights+to+{flight_q}")

                # PDF 다운로드
                pdf_bytes = create_pdf_report(f"Travel Plan: {city_data['name'].split(',')[0]}", pdf_content)
                st.download_button("📄 결과 리포트 다운로드 (PDF)", data=pdf_bytes, file_name="MyTrip.pdf", mime="application/pdf")

# --- 모드 2: 장기 여행 ---
def run_mode_long_trip():
    st.header("🌏 장기 여행 (세계 일주 루트)")
    st.info("가고 싶은 도시들을 검색해서 추가하면, 최적의 동선을 짜드립니다.")

    if 'selected_cities_data' not in st.session_state:
        st.session_state['selected_cities_data'] = []

    c1, c2 = st.columns([3, 1])
    with c1: new_city = st.text_input("도시 검색 (예: 런던, 파리)", key="multi_input")
    with c2: 
        st.write("")
        st.write("")
        if st.button("추가 ➕") and new_city:
            with st.spinner("위치 확인 중..."):
                found = search_city_coordinates(new_city)
                if found:
                    if any(c['name'] == found['name'] for c in st.session_state['selected_cities_data']):
                        st.warning("이미 추가된 도시입니다.")
                    else:
                        st.session_state['selected_cities_data'].append(found)
                        st.success(f"✅ {found['name'].split(',')[0]} 추가됨")
                else: st.error("도시를 찾을 수 없습니다.")

    if st.session_state['selected_cities_data']:
        st.markdown("##### 📋 선택된 도시 목록")
        for i, c in enumerate(st.session_state['selected_cities_data']):
            st.text(f"{i+1}. {c['name']}")
        if st.button("목록 초기화 🗑️"):
            st.session_state['selected_cities_data'] = []
            st.rerun()

    st.write("---")
    
    if len(st.session_state['selected_cities_data']) > 0:
        start_city_name = st.selectbox("출발 도시 선택", [c['name'] for c in st.session_state['selected_cities_data']])
        start_city = next(c for c in st.session_state['selected_cities_data'] if c['name'] == start_city_name)
    
    col1, col2 = st.columns(2)
    with col1: start_date = st.date_input("여행 시작일", value=datetime.now().date()+timedelta(30))
    with col2: total_weeks = st.slider("전체 기간 (주)", 1, 24, 4)
    
    daily_budget = st.number_input("전체 일정 1일 평균 예산 (원)", value=150000)
    travel_style = st.radio("여행 스타일", ["배낭여행", "일반", "럭셔리"], horizontal=True)

    if st.button("🚀 루트 최적화 및 분석", type="primary"):
        cities = st.session_state['selected_cities_data']
        if len(cities) < 2: st.warning("2개 이상 필요"); st.stop()

        # 루트 최적화
        route = [start_city]
        unvisited = [c for c in cities if c['name'] != start_city['name']]
        curr = start_city
        while unvisited:
            nearest = min(unvisited, key=lambda x: calculate_distance(curr['lat'], curr['lon'], x['lat'], x['lon']))
            route.append(nearest)
            unvisited.remove(nearest)
            curr = nearest

        total_days = total_weeks * 7
        days_per_city = max(2, total_days // len(route))
        
        st.divider()
        st.subheader(f"🗺️ 추천 루트 ({len(route)}개 도시)")
        draw_route_map(route)
        
        total_cost = calculate_travel_cost(daily_budget, total_days, travel_style)
        st.metric("총 예상 경비 (항공권 제외)", f"약 {total_cost//10000}만 원")

        st.write("---")
        st.subheader("📅 상세 일정")
        
        curr_date = start_date
        pdf_lines = ["=== 장기 여행 루트 ===", ""]
        
        for idx, city in enumerate(route):
            stay = (start_date + timedelta(total_days) - curr_date).days if idx == len(route)-1 else days_per_city
            arrival, departure = curr_date, curr_date + timedelta(stay)
            
            # 날씨 분석
            h_start = arrival - pd.DateOffset(years=1)
            h_end = departure - pd.DateOffset(years=1)
            with st.spinner(f"{city['name'].split(',')[0]} 분석..."):
                w = get_historical_weather(city['lat'], city['lon'], h_start.strftime('%Y-%m-%d'), h_end.strftime('%Y-%m-%d'))
                df = create_base_dataframe(w, h_start, h_end)
            
            w_desc = "데이터 없음"
            if not df.empty:
                t = df['temperature_2m_max'].mean()
                w_desc = f"{t:.1f}°C ({'쾌적' if 15<=t<=25 else '더움' if t>28 else '추움'})"

            line_str = f"{idx+1}. {city['name'].split(',')[0]}: {arrival}~{departure} ({stay}박) / 날씨: {w_desc}"
            pdf_lines.append(line_str)

            with st.container(border=True):
                st.markdown(f"**{idx+1}. {city['name'].split(',')[0]}**")
                c1, c2, c3 = st.columns([2,2,1])
                c1.write(f"🗓️ {arrival.strftime('%m/%d')} ~ {departure.strftime('%m/%d')}")
                c2.write(f"🌡️ {w_desc}")
                c3.link_button("📍 지도", f"https://www.google.com/maps/search/?api=1&query={city['lat']},{city['lon']}")
            
            curr_date = departure

        pdf_bytes = create_pdf_report(f"World Tour Plan ({total_weeks} Weeks)", pdf_lines)
        st.download_button("📥 전체 일정 다운로드 (PDF)", data=pdf_bytes, file_name="LongTrip.pdf", mime="application/pdf")

# --- 모드 3: AI 챗봇 (업그레이드) ---
def run_mode_chat():
    st.header("🤖 AI 여행 상담소")
    st.caption("여행지 추천, 맛집, 문화 등 무엇이든 물어보세요! (Google Gemini 기반)")

    if not GEMINI_KEY:
        st.error("⚠️ 설정에서 API 키를 확인해주세요.")
        return

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 여행에 대해 궁금한 점이 있으신가요? ✈️"}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("질문을 입력하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("AI가 생각 중입니다..."):
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_KEY)
                
                # 자동 모델 선택
                candidates = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]
                response_text = "죄송합니다. 현재 AI 서버 연결이 원활하지 않습니다."
                
                for model_name in candidates:
                    try:
                        model = genai.GenerativeModel(model_name)
                        # 검색 도구 활성화
                        tools = [{"google_search_retrieval": {}}]
                        response = model.generate_content(prompt) # 라이브러리 자동 처리
                        response_text = response.text
                        break
                    except: continue
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

# --- 메인 실행 ---
def main():
    st.set_page_config(page_title="Travel Planner AI", page_icon="✈️", layout="wide")
    check_api_keys()
    
    # 사이드바에 환율 계산기 탑재
    sidebar_currency_converter()
    
    with st.sidebar:
        st.title("✈️ 메뉴")
        app_mode = st.radio("모드 선택", ["개인 맞춤형 (Single)", "장기 여행 (Long-term)", "AI 상담소 (Chat)"])

    if app_mode == "개인 맞춤형 (Single)":
        run_mode_single_trip()
    elif app_mode == "장기 여행 (Long-term)":
        run_mode_long_trip()
    elif app_mode == "AI 상담소 (Chat)":
        run_mode_chat()

if __name__ == "__main__":
    main()
