import streamlit as st
import requests
import pandas as pd
import math
from datetime import datetime, timedelta
import io
import pydeck as pdk
import time
import google.generativeai as genai # [신규] AI 채팅용 라이브러리

# --- 설정: 테마 매핑 ---
THEME_OSM_MAP = {
    "미식 🍜": '"amenity"="restaurant"',
    "쇼핑 🛍️": '"shop"="mall"',
    "문화/유적 🏯": '"tourism"="attraction"',
    "휴양/공원 🌳": '"leisure"="park"'
}

# --- 1. API 키 확인 및 설정 ---
CALENDARIFIC_KEY = st.secrets.get("calendarific_key")
GEMINI_KEY = st.secrets.get("gemini_key")

def check_api_keys():
    if not CALENDARIFIC_KEY:
        st.sidebar.error("⚠️ Calendarific API 키가 설정되지 않았습니다.")
        st.stop()

# [신규] Gemini AI 설정
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

# --- 2. 핵심 유틸리티 함수 ---

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

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# --- 3. 날씨 및 정보 API ---

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

# --- 4. 시각화 및 계산 ---

def draw_route_map(route_cities_data):
    map_data = []
    for i in range(len(route_cities_data)):
        city = route_cities_data[i]
        map_data.append({
            "coordinates": [city['lon'], city['lat']],
            "name": f"{i+1}. {city['name'].split(',')[0]}",
            "size": 50000, "color": [0, 200, 100, 200]
        })

    scatter_layer = pdk.Layer(
        "ScatterplotLayer", data=map_data, get_position="coordinates",
        get_fill_color="color", get_radius="size", pickable=True,
        radius_scale=1, radius_min_pixels=10, radius_max_pixels=30,
    )
    text_layer = pdk.Layer(
        "TextLayer", data=map_data, get_position="coordinates",
        get_text="name", get_size=18, get_color=[0, 0, 0],
        get_angle=0, get_text_anchor="middle", get_alignment_baseline="bottom",
        pixel_offset=[0, -15]
    )
    line_data = [{"start": [route_cities_data[i]['lon'], route_cities_data[i]['lat']], "end": [route_cities_data[i+1]['lon'], route_cities_data[i+1]['lat']]} for i in range(len(route_cities_data)-1)]
    line_layer = pdk.Layer(
        "LineLayer", data=line_data, get_source_position="start",
        get_target_position="end", get_color=[100, 100, 100, 100], get_width=3
    )

    view_state = pdk.ViewState(latitude=route_cities_data[0]['lat'], longitude=route_cities_data[0]['lon'], zoom=3)
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
    return "\n".join([f"- {t}" for t in tips])

def generate_download_content(title, details_text):
    return f"=== 여행 비서 리포트 ===\n{title}\n\n{details_text}"

# --- 모드 1: 개인 맞춤형 ---
def run_mode_single_trip():
    st.header("🎯 모드 1: 개인 맞춤형 여행 추천")
    city_query = st.text_input("어디로 떠나시나요? (예: 도쿄, 뉴욕)", "")
    
    search_data = None
    if city_query:
        with st.spinner("위치 확인 중..."):
            search_data = search_city_coordinates(city_query)
            if search_data: st.success(f"📍 {search_data['name']}")
            else: st.error("도시를 찾을 수 없습니다."); st.stop()

    c1, c2 = st.columns(2)
    with c1: theme_name = st.selectbox("여행 테마", options=THEME_OSM_MAP.keys())
    with c2: daily_budget = st.number_input("1일 예산 (원)", value=200000, step=10000)

    priority_mode = st.radio("우선순위", ["연차 효율 (휴일 포함)", "비용 절감 (휴일 제외)"], horizontal=True)

    today = datetime.now().date()
    date_range = st.date_input("기간 선택", value=(today+timedelta(30), today+timedelta(90)), min_value=today, max_value=today+timedelta(365))
    trip_duration = st.slider("여행 기간 (박)", 3, 14, 5)

    if st.button("분석 시작", type="primary", disabled=(search_data is None)):
        if len(date_range) < 2: st.error("기간을 선택하세요."); st.stop()
        start_date, end_date = date_range
        country_code = search_data.get('country_code', 'KR').upper()
        hist_start = start_date - pd.DateOffset(years=1)
        hist_end = end_date - pd.DateOffset(years=1)
        
        with st.spinner("분석 중..."):
            weather = get_historical_weather(search_data['lat'], search_data['lon'], hist_start.strftime('%Y-%m-%d'), hist_end.strftime('%Y-%m-%d'))
            local_h = get_holidays_for_period(CALENDARIFIC_KEY, country_code, start_date, end_date)
            kr_h = get_holidays_for_period(CALENDARIFIC_KEY, "KR", start_date, end_date)
            places_df = get_places_osm(search_data['lat'], search_data['lon'], THEME_OSM_MAP[theme_name])
            
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
            st.subheader(f"🗺️ '{theme_name}' 추천 장소")
            if not places_df.empty: st.dataframe(places_df, column_config={"지도 보기": st.column_config.LinkColumn("구글 지도", display_text="📍 지도")}, hide_index=True, use_container_width=True)
            else: st.info("주변 장소 데이터 없음")

            st.write("---")
            st.subheader("🏆 Best 3 일정")
            download_text = f"목적지: {search_data['name']}\n"

            for i, period in enumerate(top_3):
                p_s = period['start'].strftime('%Y-%m-%d')
                p_e = period['end'].strftime('%Y-%m-%d')
                temp = period['window']['temperature_2m_max'].mean()
                rain = period['window']['precipitation_sum'].sum()
                free = period['window']['is_free_day'].sum()
                cost = daily_budget * trip_duration
                tips = get_packing_tips(temp, rain)
                
                download_text += f"[{i+1}위] {p_s}~{p_e} / {temp:.1f}도 / {cost:,}원\n"
                
                with st.expander(f"{['🥇','🥈','🥉'][i] if i<3 else ''} {i+1}위: {p_s}~{p_e} ({period['score']:.0f}점)", expanded=(i==0)):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("기온", f"{temp:.1f}°C")
                    c2.metric("강수", f"{rain:.1f}mm")
                    c3.metric("휴일", f"{free}일")
                    c4.metric("경비", f"{cost//10000}만 원")
                    st.info(f"🧳 **팁:** {tips}")
                    flight_q = search_data['name'].split(',')[0]
                    st.link_button("✈️ 항공권 검색", f"https://www.google.com/travel/flights?q=Flights+to+{flight_q}")

            st.download_button("📥 결과 저장 (TXT)", generate_download_content("여행 분석", download_text), f"Trip_{today}.txt")

# --- 모드 2: 장기 여행 ---
def run_mode_long_trip():
    st.header("🌏 모드 2: 장기 여행 (전 세계 루트)")
    if 'selected_cities_data' not in st.session_state: st.session_state['selected_cities_data'] = []

    c1, c2 = st.columns([3, 1])
    with c1: new_city = st.text_input("도시 검색 (예: 런던, 파리)", key="multi_input")
    with c2: 
        st.write("")
        st.write("")
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
    c1, c2 = st.columns(2)
    with c1: start_date = st.date_input("시작일", value=datetime.now().date()+timedelta(30))
    with c2: total_weeks = st.slider("기간 (주)", 1, 12, 4)
    daily_budget = st.number_input("1일 평균 예산 (원)", value=150000)
    
    if st.button("🚀 루트 최적화", type="primary"):
        cities = st.session_state['selected_cities_data']
        if len(cities) < 2: st.warning("2개 이상 필요"); st.stop()

        route = [cities[0]]
        unvisited = cities[1:]
        curr = cities[0]
        while unvisited:
            nearest = min(unvisited, key=lambda x: calculate_distance(curr['lat'], curr['lon'], x['lat'], x['lon']))
            route.append(nearest)
            unvisited.remove(nearest)
            curr = nearest

        st.divider()
        st.subheader(f"🗺️ 추천 루트 ({len(route)}도시)")
        draw_route_map(route)
        
        days_per_city = max(2, (total_weeks*7) // len(route))
        total_cost = daily_budget * total_weeks * 7
        st.metric("총 예상 경비", f"약 {total_cost//10000}만 원")

        st.write("---")
        st.subheader("📅 상세 일정")
        curr_date = start_date
        dl_text = "[[ 장기 여행 ]]\n"
        
        for idx, city in enumerate(route):
            stay = (start_date + timedelta(total_weeks*7) - curr_date).days if idx == len(route)-1 else days_per_city
            arrival, departure = curr_date, curr_date + timedelta(stay)
            
            h_start = arrival - pd.DateOffset(years=1)
            h_end = departure - pd.DateOffset(years=1)
            with st.spinner(f"{city['name'].split(',')[0]} 분석..."):
                w = get_historical_weather(city['lat'], city['lon'], h_start.strftime('%Y-%m-%d'), h_end.strftime('%Y-%m-%d'))
                df = create_base_dataframe(w, h_start, h_end)
            
            w_desc = "데이터 없음"
            if not df.empty:
                t = df['temperature_2m_max'].mean()
                w_desc = f"{t:.1f}°C ({'쾌적' if 15<=t<=25 else '더움' if t>28 else '추움'})"

            dl_text += f"{idx+1}. {city['name'].split(',')[0]}: {arrival}~{departure} / {w_desc}\n"
            with st.container():
                st.markdown(f"**{idx+1}. {city['name'].split(',')[0]}** ({stay}박)")
                c1, c2, c3 = st.columns([2,2,1])
                c1.write(f"{arrival.strftime('%m/%d')}~{departure.strftime('%m/%d')}")
                c2.write(f"🌡️ {w_desc}")
                c3.link_button("📍 지도", f"https://www.google.com/maps/search/?api=1&query={city['lat']},{city['lon']}")
                st.divider()
            curr_date = departure

        st.download_button("📥 다운로드", generate_download_content("세계일주", dl_text), "LongTrip.txt")

# --- 모드 3: AI 챗봇 (신규) ---
def run_mode_chat():
    st.header("🤖 AI 여행 상담소")
    st.caption("여행 계획, 맛집 추천, 현지 문화 등 무엇이든 물어보세요! (Google Gemini 기반)")

    if not GEMINI_KEY:
        st.error("⚠️ `.streamlit/secrets.toml`에 `gemini_key`가 설정되지 않았습니다.")
        st.info("Google AI Studio에서 무료 API 키를 발급받으세요.")
        return

    # 채팅 기록 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "안녕하세요! 여행에 대해 무엇이든 물어보세요. ✈️"}
        ]

    # 기존 메시지 표시
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 사용자 입력 처리
    if prompt := st.chat_input("질문을 입력하세요 (예: 12월 도쿄 옷차림 알려줘)"):
        # 사용자 메시지 표시
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("AI가 생각 중입니다..."):
                try:
                    # Gemini 모델 설정
                    model = genai.GenerativeModel('gemini-pro')
                    response = model.generate_content(prompt)
                    ai_msg = response.text
                    
                    st.markdown(ai_msg)
                    st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

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
