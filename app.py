import streamlit as st
import requests
import pandas as pd
import math
from datetime import datetime, timedelta
import pydeck as pdk
import time

# --- 설정: 테마 매핑 ---
THEME_OSM_MAP = {
    "미식 🍜": '"amenity"="restaurant"',
    "쇼핑 🛍️": '"shop"="mall"',
    "문화/유적 🏯": '"tourism"="attraction"',
    "휴양/공원 🌳": '"leisure"="park"'
}

# --- 1. API 키 확인 ---
CALENDARIFIC_KEY = st.secrets.get("calendarific_key")

def check_api_keys():
    if not CALENDARIFIC_KEY:
        st.sidebar.error("⚠️ Calendarific API 키가 설정되지 않았습니다.")
        st.stop()

# --- 2. 핵심 유틸리티 함수 (검색 엔진) ---

@st.cache_data(ttl=3600)
def search_city_coordinates(city_name):
    """
    Nominatim API를 사용하여 전 세계 도시의 좌표를 검색합니다.
    """
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": city_name,
            "format": "json",
            "limit": 1,
            "accept-language": "ko" # 한국어 결과 선호
        }
        # Nominatim은 User-Agent 헤더가 필수입니다.
        headers = {'User-Agent': 'MyTravelApp/1.0'}
        
        res = requests.get(url, params=params, headers=headers)
        res.raise_for_status()
        data = res.json()
        
        if data:
            return {
                "name": data[0]['display_name'],
                "lat": float(data[0]['lat']),
                "lon": float(data[0]['lon']),
                # 국가 코드가 없는 경우도 대비
                "country_code": data[0].get('address', {}).get('country_code', 'KR').upper() 
            }
        else:
            return None
    except:
        return None

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
    # 국가 코드가 없으면 검색하지 않음
    if not country_code: return all_holidays
    
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

# --- 4. 시각화 및 계산 ---

def draw_route_map(route_cities_data):
    """route_cities_data: [{'name':..., 'lat':..., 'lon':...}, ...]"""
    map_data = []
    for i in range(len(route_cities_data)):
        city = route_cities_data[i]
        map_data.append({
            "coordinates": [city['lon'], city['lat']],
            "name": f"{i+1}. {city['name'].split(',')[0]}", # 앞부분 이름만 표시
            "size": 50000,
            "color": [0, 200, 100, 200]
        })

    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        get_position="coordinates",
        get_fill_color="color",
        get_radius="size",
        pickable=True,
        radius_scale=1,
        radius_min_pixels=10,
        radius_max_pixels=30,
    )

    text_layer = pdk.Layer(
        "TextLayer",
        data=map_data,
        get_position="coordinates",
        get_text="name",
        get_size=18,
        get_color=[0, 0, 0],
        get_angle=0,
        get_text_anchor="middle",
        get_alignment_baseline="bottom",
        pixel_offset=[0, -15]
    )

    # 경로 라인 (선택 사항)
    line_data = []
    for i in range(len(route_cities_data) - 1):
        start = route_cities_data[i]
        end = route_cities_data[i+1]
        line_data.append({
            "start": [start['lon'], start['lat']],
            "end": [end['lon'], end['lat']]
        })
    
    line_layer = pdk.Layer(
        "LineLayer",
        data=line_data,
        get_source_position="start",
        get_target_position="end",
        get_color=[100, 100, 100, 100],
        get_width=3
    )

    view_state = pdk.ViewState(
        latitude=route_cities_data[0]['lat'],
        longitude=route_cities_data[0]['lon'],
        zoom=3,
        pitch=0,
    )

    st.pydeck_chart(pdk.Deck(
        layers=[line_layer, scatter_layer, text_layer],
        initial_view_state=view_state,
        map_style=None,
        tooltip={"text": "{name}"}
    ))

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
    if avg_temp < 5: tips.append("🧥 두꺼운 패딩/코트, 목도리, 장갑 (추움)")
    elif 5 <= avg_temp < 15: tips.append("🧥 경량 패딩, 자켓, 히트텍 (쌀쌀)")
    elif 15 <= avg_temp < 22: tips.append("👕 긴팔 티셔츠, 가디건 (쾌적)")
    elif avg_temp >= 22: tips.append("👕 반팔, 반바지, 선글라스 (더움)")
    
    if rain_sum > 30: tips.append("☂️ 우산/우비 필수 (비)")
    if avg_temp > 25: tips.append("🧴 선크림, 모자")
    return "\n".join([f"- {t}" for t in tips])

def generate_download_content(title, details_text):
    return f"""
    ==========================================
    ✈️ 여행 비서 AI - 추천 일정 리포트
    ==========================================
    {title}
    
    {details_text}
    ------------------------------------------
    * AI 분석 결과이며 실제와 다를 수 있습니다.
    * 날씨는 작년 데이터를 기반으로 합니다.
    ==========================================
    """

# --- 모드 1: 개인 맞춤형 (Single) ---
def run_mode_single_trip():
    st.header("🎯 모드 1: 개인 맞춤형 여행 추천")
    
    # 1. 도시 검색 (Nominatim)
    st.subheader("1. 여행지 검색")
    city_query = st.text_input("어디로 떠나고 싶으신가요? (예: 파리, 뉴욕, 다낭)", "")
    
    search_data = None
    if city_query:
        with st.spinner(f"'{city_query}' 찾는 중..."):
            search_data = search_city_coordinates(city_query)
            if search_data:
                st.success(f"📍 확인된 위치: {search_data['name']}")
            else:
                st.error("도시를 찾을 수 없습니다. 정확한 도시명을 입력해주세요.")
                st.stop()

    # 2. 테마 및 스타일
    col1, col2 = st.columns(2)
    with col1:
        theme_name = st.selectbox("여행 테마", options=THEME_OSM_MAP.keys())
    with col2:
        daily_budget = st.number_input("1인 1일 예산 (원)", value=200000, step=10000)

    priority_mode = st.radio("우선순위", ["연차 효율 (휴일 포함)", "비용 절감 (휴일 제외)"], horizontal=True)

    # 3. 날짜 선택
    today = datetime.now().date()
    st.subheader("2. 언제쯤 가시나요?")
    date_range = st.date_input(
        "기간 범위 선택",
        value=(today + timedelta(days=30), today + timedelta(days=90)),
        min_value=today,
        max_value=today + timedelta(days=365)
    )
    trip_duration = st.slider("여행 기간 (박)", 3, 14, 5)

    if st.button("분석 시작", type="primary", disabled=(search_data is None)):
        if len(date_range) < 2: 
            st.error("기간을 정확히 선택해주세요.")
            st.stop()
        
        start_date, end_date = date_range
        # 국가 코드 처리 (Nominatim은 'kr', 'jp' 등 소문자일 수 있음 -> 대문자로 변환)
        country_code = search_data.get('country_code', 'KR').upper()
        
        # 작년 날씨
        hist_start = start_date - pd.DateOffset(years=1)
        hist_end = end_date - pd.DateOffset(years=1)
        
        with st.spinner("데이터 분석 중..."):
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
            if not places_df.empty:
                st.dataframe(places_df, column_config={"지도 보기": st.column_config.LinkColumn("구글 지도", display_text="📍 지도")}, hide_index=True, use_container_width=True)
            else:
                st.info("주변 장소 데이터 없음")

            st.write("---")
            st.subheader("🏆 최적의 여행 시기 Best 3")
            
            download_text = f"목적지: {search_data['name']}\n"

            for i, period in enumerate(top_3):
                p_start = period['start'].strftime('%Y-%m-%d')
                p_end = period['end'].strftime('%Y-%m-%d')
                score = period['score']
                temp_avg = period['window']['temperature_2m_max'].mean()
                rain_sum = period['window']['precipitation_sum'].sum()
                free_days = period['window']['is_free_day'].sum()
                
                est_cost = daily_budget * trip_duration
                packing_tips = get_packing_tips(temp_avg, rain_sum)
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else ""
                
                download_text += f"[{i+1}순위] {p_start}~{p_end} / {temp_avg:.1f}도 / 예상경비 {est_cost:,}원\n"

                with st.expander(f"{medal} {i+1}순위: {p_start} ~ {p_end} (점수: {score:.0f})", expanded=(i==0)):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("기온", f"{temp_avg:.1f}°C")
                    c2.metric("강수", f"{rain_sum:.1f}mm")
                    c3.metric("휴일", f"{free_days}일")
                    c4.metric("예상 경비", f"{est_cost // 10000}만 원")
                    
                    st.info(f"🧳 **팁:** {packing_tips}")
                    
                    # 항공권 링크 (도시명 영문/현지어 혼합일 수 있어 단순 검색)
                    flight_query = search_data['name'].split(',')[0]
                    st.link_button("✈️ 항공권 검색", f"https://www.google.com/travel/flights?q=Flights+to+{flight_query}")

            st.download_button("📥 결과 저장 (TXT)", generate_download_content(f"{city_query} 여행 분석", download_text), f"Trip_{today}.txt")

# --- 모드 2: 장기 여행 (Long-term) ---
def run_mode_long_trip():
    st.header("🌏 모드 2: 장기 여행 (전 세계 루트)")
    st.caption("가고 싶은 도시들을 검색해서 장바구니에 담으세요. 최적의 루트를 짜드립니다.")

    # Session State로 도시 목록 관리
    if 'selected_cities_data' not in st.session_state:
        st.session_state['selected_cities_data'] = []

    # 1. 도시 추가 UI
    with st.container():
        c1, c2 = st.columns([3, 1])
        with c1:
            new_city_query = st.text_input("도시 검색 (예: 런던, 파리, 로마)", key="multi_city_input")
        with c2:
            st.write("") 
            st.write("")
            add_btn = st.button("도시 추가 ➕")

    if add_btn and new_city_query:
        with st.spinner("위치 찾는 중..."):
            found = search_city_coordinates(new_city_query)
            if found:
                # 중복 체크
                if any(c['name'] == found['name'] for c in st.session_state['selected_cities_data']):
                    st.warning("이미 추가된 도시입니다.")
                else:
                    st.session_state['selected_cities_data'].append(found)
                    st.success(f"✅ {found['name'].split(',')[0]} 추가됨!")
            else:
                st.error("도시를 찾을 수 없습니다.")

    # 2. 선택된 도시 목록 표시
    if st.session_state['selected_cities_data']:
        st.write("---")
        st.write("### 📋 선택된 도시 목록")
        for i, city in enumerate(st.session_state['selected_cities_data']):
            st.text(f"{i+1}. {city['name']}")
        
        if st.button("목록 초기화 🗑️"):
            st.session_state['selected_cities_data'] = []
            st.rerun()
    else:
        st.info("도시를 검색해서 추가해주세요.")
        return # 도시 없으면 아래 실행 안함

    # 3. 설정 및 실행
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("여행 시작일", value=datetime.now().date() + timedelta(days=30))
    with col2:
        total_weeks = st.slider("전체 여행 기간 (주)", 1, 12, 4)
    
    daily_budget = st.number_input("전체 일정 1일 평균 예산 (원)", value=150000)
    total_days = total_weeks * 7

    if st.button("🚀 루트 최적화 및 분석", type="primary"):
        cities = st.session_state['selected_cities_data']
        if len(cities) < 2:
            st.warning("최소 2개 이상의 도시가 필요합니다."); st.stop()

        # 루트 최적화 (Greedy Nearest Neighbor)
        # 첫 번째 추가한 도시를 출발지로 가정
        route = [cities[0]]
        unvisited = cities[1:]
        current = cities[0]

        while unvisited:
            # 가장 가까운 도시 찾기
            nearest = min(unvisited, key=lambda x: calculate_distance(current['lat'], current['lon'], x['lat'], x['lon']))
            route.append(nearest)
            unvisited.remove(nearest)
            current = nearest

        days_per_city = max(2, total_days // len(route))
        
        st.divider()
        st.subheader(f"🗺️ 추천 루트 ({len(route)}개 도시)")
        
        # 지도 그리기
        draw_route_map(route)
        
        total_est_cost = daily_budget * total_days
        st.metric("총 예상 경비 (항공권 제외)", f"약 {total_est_cost // 10000}만 원")

        st.write("---")
        st.subheader("📅 상세 일정")
        
        current_date = start_date
        download_text = "[[ 장기 여행 루트 ]]\n"
        
        for idx, city in enumerate(route):
            if idx == len(route) - 1:
                stay_days = (start_date + timedelta(days=total_days) - current_date).days
            else:
                stay_days = days_per_city
            
            arrival_date = current_date
            departure_date = current_date + timedelta(days=stay_days)
            
            # 날씨 확인
            hist_start = arrival_date - pd.DateOffset(years=1)
            hist_end = departure_date - pd.DateOffset(years=1)
            
            with st.spinner(f"{city['name'].split(',')[0]} 분석..."):
                weather = get_historical_weather(city['lat'], city['lon'], hist_start.strftime('%Y-%m-%d'), hist_end.strftime('%Y-%m-%d'))
                df = create_base_dataframe(weather, hist_start, hist_end)
            
            weather_desc = "데이터 없음"
            if not df.empty:
                temp = df['temperature_2m_max'].mean()
                status = "쾌적" if 15 <= temp <= 25 else ("더움" if temp > 28 else "추움")
                weather_desc = f"{temp:.1f}°C ({status})"

            simple_name = city['name'].split(',')[0]
            download_text += f"{idx+1}. {simple_name}: {arrival_date} ~ {departure_date} ({weather_desc})\n"

            with st.container():
                st.markdown(f"**{idx+1}. {simple_name}** ({stay_days}박)")
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"{arrival_date.strftime('%m/%d')} ~ {departure_date.strftime('%m/%d')}")
                c2.write(f"🌡️ {weather_desc}")
                c3.link_button("📍 지도", f"https://www.google.com/maps/search/?api=1&query={city['lat']},{city['lon']}")
                st.divider()

            current_date = departure_date

        st.download_button("📥 전체 일정 다운로드", generate_download_content("세계일주 루트", download_text), "LongTrip.txt")

# --- 메인 앱 실행 ---
def main():
    st.set_page_config(page_title="Travel Planner AI", page_icon="✈️", layout="wide")
    check_api_keys()
    
    with st.sidebar:
        st.title("✈️ 여행 비서 AI")
        app_mode = st.radio("모드 선택", ["개인 맞춤형 (Single)", "장기 여행 (Long-term)"])
        st.info("🌍 전 세계 도시 검색 지원\n(OpenStreetMap 기반)")
        st.caption("Made with Streamlit")

    if app_mode == "개인 맞춤형 (Single)":
        run_mode_single_trip()
    elif app_mode == "장기 여행 (Long-term)":
        run_mode_long_trip()

if __name__ == "__main__":
    main()
