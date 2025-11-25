import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 전 세계 주요 도시 데이터 (50개 도시 확장) ---
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
    """일별 점수 계산"""
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

# --- 모드 1: 개인 맞춤형 (Top 3 추천) ---
def run_mode_single_trip():
    st.header("🎯 모드 1: 개인 맞춤형 여행 추천")
    st.caption("가고 싶은 도시를 하나 골라, 최적의 여행 시기를 찾아보세요.")

    # UI 개선: 도시 선택을 국가별로 그룹화하지 않고 검색 가능하게 유지
    # (선택지가 많으므로 selectbox 검색 기능 활용)
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
    st.write("📅 **언제쯤 여행을 떠나시나요?**")
    date_range = st.date_input(
        "달력에서 기간 선택",
        value=(today + timedelta(days=30), today + timedelta(days=90)),
        min_value=today,
        max_value=today + timedelta(days=365),
        format="YYYY-MM-DD"
    )
    
    trip_duration = st.slider("여행 기간 (박)", 3, 14, 5)

    if st.button("최적 일정 Top 3 찾기", type="primary"):
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

# --- 모드 2: 다구간/장기 여행 (국가별 추천 기능 추가) ---
def run_mode_multi_trip():
    st.header("🌏 모드 2: 다구간 효율적 일정 짜기")
    st.caption("가고 싶은 나라를 고르면, 그 나라의 추천 도시들을 자동으로 불러옵니다.")

    # 1. 나라 선택 (중복 제거)
    unique_countries = sorted(list(set([v['country'] for v in CITY_DATA.values()])))
    selected_nations = st.multiselect("어느 나라로 가시나요? (여러 개 선택 가능)", unique_countries)

    # 2. 선택된 나라의 도시 자동 필터링
    available_cities = []
    if selected_nations:
        available_cities = [k for k, v in CITY_DATA.items() if v['country'] in selected_nations]
    
    # 3. 도시 최종 선택
    selected_cities = st.multiselect(
        "방문할 도시를 확인해주세요 (자동 선택됨)",
        options=available_cities,
        default=available_cities
    )

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("여행 시작 가능일", value=datetime.now().date() + timedelta(days=30), min_value=datetime.now().date())
    with col2:
        total_months = st.slider("전체 여행 가능 기간 (개월)", 1, 6, 3)

    end_date = start_date + pd.DateOffset(months=total_months)
    
    if st.button("도시별 최적 시기 비교하기", type="primary"):
        if len(selected_cities) < 1:
            st.warning("분석할 도시가 없습니다. 나라를 먼저 선택해주세요."); st.stop()
            
        comparison_data = []
        progress_bar = st.progress(0)
        
        hist_start = start_date - pd.DateOffset(years=1)
        hist_end = end_date - pd.DateOffset(years=1)
        
        for idx, city_key in enumerate(selected_cities):
            data = CITY_DATA[city_key]
            lat, lon = data["coords"].split(',')
            weather = get_historical_weather(lat, lon, hist_start.strftime('%Y-%m-%d'), hist_end.strftime('%Y-%m-%d'))
            df = create_base_dataframe(weather, hist_start, hist_end)
            
            if not df.empty:
                df['score'] = (10 - abs(df['temperature_2m_max'] - 23)) - (df['precipitation_sum'] * 0.5)
                df['smooth_score'] = df['score'].rolling(window=7).mean()
                
                for date, row in df.iterrows():
                    current_date = date + pd.DateOffset(years=1)
                    if not pd.isna(row['smooth_score']):
                        # 그래프에 도시 이름만 깔끔하게 표시 (괄호 안 내용 추출)
                        simple_name = data['city']
                        comparison_data.append({
                            "날짜": current_date,
                            "도시": f"{simple_name} ({data['country']})",
                            "여행 적합도": row['smooth_score']
                        })
            progress_bar.progress((idx + 1) / len(selected_cities))

        if comparison_data:
            st.divider()
            chart_df = pd.DataFrame(comparison_data)
            st.line_chart(chart_df, x="날짜", y="여행 적합도", color="도시", height=400)
            
            st.subheader("💡 AI의 이동 순서 조언")
            best_days = chart_df.loc[chart_df.groupby("도시")["여행 적합도"].idxmax()].sort_values("날짜")
            
            st.write("날씨 데이터를 분석한 결과, 다음 순서로 이동하는 것을 추천합니다:")
            for _, row in best_days.iterrows():
                date_str = row['날짜'].strftime('%Y년 %m월')
                st.markdown(f"- **{row['도시']}**: {date_str} 경에 방문 추천")
        else:
            st.error("데이터 부족")

# --- 메인 앱 실행 ---
def main():
    st.set_page_config(page_title="Travel Planner AI", page_icon="✈️", layout="wide")
    check_api_keys()
    
    with st.sidebar:
        st.title("✈️ 여행 비서 AI")
        app_mode = st.radio("선택 메뉴", ["개인 맞춤형 (Single)", "다구간 효율 (Multi)"])
        st.write("---")
        st.caption("Made with Streamlit")

    if app_mode == "개인 맞춤형 (Single)":
        run_mode_single_trip()
    elif app_mode == "다구간 효율 (Multi)":
        run_mode_multi_trip()

if __name__ == "__main__":
    main()
