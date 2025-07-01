# streamlit_app.py - HTML 렌더링 문제 수정 버전

import streamlit as st
import requests
import json
import datetime
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
import pytz

# 페이지 설정 - 모바일 최적화
st.set_page_config(
    page_title="🌤️ 스마트 출퇴근 도우미",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 모바일 친화적 CSS 스타일
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    
    .stMetric {
        background-color: #f0f2f6;
        border: 1px solid #e1e5e9;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    
    .weather-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 1rem;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    
    .recommendation-card {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    
    .time-info {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        text-align: center;
        color: white;
    }
    
    .stButton > button {
        width: 100%;
        height: 3rem;
        font-size: 1.1rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@dataclass
class WeatherData:
    """날씨 데이터 클래스"""
    temperature: float
    feels_like: float
    humidity: int
    pressure: float
    weather_condition: str
    weather_description: str
    wind_speed: float
    visibility: float
    sunrise: datetime.datetime = None
    sunset: datetime.datetime = None
    timezone_offset: int = 0  # UTC 기준 오프셋 (초)
    timestamp: datetime.datetime = None
    source: str = "데모 데이터"

class WeatherApp:
    """스마트 출퇴근 도우미 메인 클래스"""
    
    def __init__(self):
        self.api_key = self.get_api_key()
        self.backup_data = {
            "temp": 22,
            "feels_like": 24,
            "humidity": 65,
            "weather": "Clear",
            "description": "맑음 (데모 데이터)",
            "wind_speed": 3.2
        }
        
        # 주요 도시별 시간대 매핑
        self.city_timezones = {
            'Seoul': 'Asia/Seoul',
            'Busan': 'Asia/Seoul',
            'Incheon': 'Asia/Seoul',
            'Daegu': 'Asia/Seoul',
            'Daejeon': 'Asia/Seoul',
            'Gwangju': 'Asia/Seoul',
            'Tokyo': 'Asia/Tokyo',
            'Osaka': 'Asia/Tokyo',
            'Beijing': 'Asia/Shanghai',
            'Shanghai': 'Asia/Shanghai',
            'New York': 'America/New_York',
            'London': 'Europe/London',
            'Paris': 'Europe/Paris',
            'Sydney': 'Australia/Sydney',
            'Los Angeles': 'America/Los_Angeles',
            'Bangkok': 'Asia/Bangkok',
            'Singapore': 'Asia/Singapore',
            'Hong Kong': 'Asia/Hong_Kong',
            'Mumbai': 'Asia/Kolkata',
            'Dubai': 'Asia/Dubai'
        }

    def get_api_key(self) -> str:
        """API 키 가져오기"""
        try:
            return st.secrets.get("OPENWEATHER_API_KEY", "")
        except:
            return st.session_state.get("api_key", "")

    def get_weather_icon(self, condition: str) -> str:
        """날씨 조건에 따른 이모지 아이콘 반환"""
        icons = {
            'clear': '☀️',
            'clouds': '☁️',
            'rain': '🌧️',
            'drizzle': '🌦️',
            'thunderstorm': '⛈️',
            'snow': '❄️',
            'mist': '🌫️',
            'fog': '🌫️',
            'haze': '🌫️'
        }
        condition_lower = condition.lower()
        for key, icon in icons.items():
            if key in condition_lower:
                return icon
        return '🌤️'

    def get_city_local_time(self, city: str, timezone_offset: int = None) -> tuple:
        """도시의 현지 시간 반환"""
        try:
            # 시간대 매핑에서 찾기
            timezone_name = self.city_timezones.get(city)
            
            if timezone_name:
                # pytz를 사용한 정확한 시간대
                tz = pytz.timezone(timezone_name)
                local_time = datetime.datetime.now(tz)
            elif timezone_offset:
                # API에서 받은 오프셋 사용
                offset_hours = timezone_offset / 3600
                tz = pytz.FixedOffset(int(offset_hours * 60))
                local_time = datetime.datetime.now(tz)
            else:
                # 기본값: UTC
                local_time = datetime.datetime.utcnow()
                timezone_name = "UTC"
            
            return local_time, timezone_name
            
        except Exception as e:
            # 오류 시 서울 시간 반환
            seoul_tz = pytz.timezone('Asia/Seoul')
            return datetime.datetime.now(seoul_tz), 'Asia/Seoul'

    @st.cache_data(ttl=300)  # 5분 캐시
    def fetch_weather_data(_self, city: str) -> Optional[WeatherData]:
        """날씨 데이터 가져오기"""
        if not _self.api_key:
            return _self._get_backup_weather_data(city)
            
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': city,
                'appid': _self.api_key,
                'units': 'metric',
                'lang': 'kr'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 일출/일몰 시간 변환 (Unix timestamp → datetime)
            sunrise = datetime.datetime.fromtimestamp(data['sys']['sunrise'])
            sunset = datetime.datetime.fromtimestamp(data['sys']['sunset'])
            
            return WeatherData(
                temperature=data['main']['temp'],
                feels_like=data['main']['feels_like'],
                humidity=data['main']['humidity'],
                pressure=data['main']['pressure'],
                weather_condition=data['weather'][0]['main'],
                weather_description=data['weather'][0]['description'],
                wind_speed=data['wind']['speed'],
                visibility=data.get('visibility', 10000) / 1000,
                sunrise=sunrise,
                sunset=sunset,
                timezone_offset=data['timezone'],  # UTC 기준 오프셋 (초)
                timestamp=datetime.datetime.now(),
                source="OpenWeatherMap API"
            )
            
        except Exception as e:
            st.warning(f"⚠️ API 호출 실패: 데모 데이터를 사용합니다")
            return _self._get_backup_weather_data(city)

    def _get_backup_weather_data(self, city: str) -> WeatherData:
        """백업 날씨 데이터 반환"""
        now = datetime.datetime.now()
        return WeatherData(
            temperature=self.backup_data['temp'],
            feels_like=self.backup_data['feels_like'],
            humidity=self.backup_data['humidity'],
            pressure=1013,
            weather_condition=self.backup_data['weather'],
            weather_description=self.backup_data['description'],
            wind_speed=self.backup_data['wind_speed'],
            visibility=10.0,
            sunrise=now.replace(hour=6, minute=30),
            sunset=now.replace(hour=19, minute=30),
            timezone_offset=32400,  # KST (+9)
            timestamp=now,
            source="데모 데이터"
        )

    def display_weather_info(self, weather: WeatherData, city: str):
        """날씨 정보 표시 - 단순화된 버전"""
        # 도시 현지 시간 계산
        local_time, timezone_name = self.get_city_local_time(city, weather.timezone_offset)
        
        # 현지 시간 정보
        st.markdown(f"### 📍 {city} 현지 시간")
        st.write(f"📅 **{local_time.strftime('%Y년 %m월 %d일 (%A)')}**")
        st.write(f"🕐 **{local_time.strftime('%H:%M:%S')}**")
        st.write(f"🌐 시간대: {timezone_name}")
        st.write(f"📊 데이터 출처: {weather.source}")
        
        # 날씨 정보 카드
        icon = self.get_weather_icon(weather.weather_condition)
        
        # 메인 날씨 정보
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"""
            <div class="weather-card">
                <div style="font-size: 4rem; margin-bottom: 1rem;">{icon}</div>
                <div style="font-size: 3rem; font-weight: bold; margin-bottom: 1rem;">{weather.temperature:.1f}°C</div>
                <div style="font-size: 1.5rem; margin-bottom: 1rem;">{weather.weather_description}</div>
                <div style="font-size: 1.2rem;">체감온도 {weather.feels_like:.1f}°C</div>
            </div>
            """, unsafe_allow_html=True)
        
        # 일출/일몰 정보
        if weather.sunrise and weather.sunset:
            st.markdown("### 🌅 일출/일몰 시간")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🌅 일출", weather.sunrise.strftime('%H:%M'))
            with col2:
                st.metric("🌇 일몰", weather.sunset.strftime('%H:%M'))
        
        # 업데이트 시간
        st.caption(f"🔄 마지막 업데이트: {weather.timestamp.strftime('%H:%M:%S')}")
        st.caption("💡 다른 날씨 앱과 1-3°C 차이는 정상입니다")

    def get_outfit_recommendation(self, weather: WeatherData) -> List[str]:
        """옷차림 추천"""
        recommendations = []
        temp = weather.temperature
        condition = weather.weather_condition.lower()
        
        if temp < 0:
            recommendations.extend([
                "🧥 패딩이나 두꺼운 코트 필수",
                "🧤 장갑과 목도리 착용",
                "👢 따뜻한 신발 선택",
                "🔥 핫팩 준비하세요"
            ])
        elif temp < 10:
            recommendations.extend([
                "🧥 두꺼운 외투 착용",
                "👖 긴바지와 긴팔 필수",
                "🧣 목도리 준비"
            ])
        elif temp < 20:
            recommendations.extend([
                "👔 가디건이나 얇은 자켓",
                "👖 긴바지 추천",
                "👕 긴팔 셔츠"
            ])
        elif temp < 25:
            recommendations.extend([
                "👕 가벼운 긴팔이나 반팔",
                "👖 긴바지 또는 7부바지",
                "🧥 얇은 겉옷 준비"
            ])
        else:
            recommendations.extend([
                "👕 반팔과 반바지",
                "🕶️ 선글라스 준비",
                "🧴 선크림 필수"
            ])
            
        if 'rain' in condition:
            recommendations.append("☔ 우산이나 우비 필수")
        if 'snow' in condition:
            recommendations.append("❄️ 미끄럼 방지 신발 착용")
            
        return recommendations

    def get_transport_recommendation(self, weather: WeatherData) -> List[str]:
        """교통수단 추천"""
        recommendations = []
        condition = weather.weather_condition.lower()
        wind_speed = weather.wind_speed
        
        if 'rain' in condition or 'snow' in condition:
            recommendations.extend([
                "🚇 지하철 이용 강력 추천 (정시성)",
                "🚌 버스보다는 지하철 우선",
                "🚗 자차 이용시 안전운전 필수",
                "🚴‍♂️ 자전거/킥보드 피하기"
            ])
        elif wind_speed > 15:
            recommendations.extend([
                "🚇 지하철 이용 추천",
                "🚴‍♂️ 자전거/킥보드 이용 주의",
                "🚗 고속도로 이용시 바람 주의"
            ])
        else:
            recommendations.extend([
                "🚶‍♂️ 도보나 자전거 이용하기 좋은 날",
                "🚇 지하철, 🚌 버스 모두 쾌적",
                "🚗 드라이브하기 좋은 날씨"
            ])
            
        return recommendations

    def get_departure_time_recommendation(self, weather: WeatherData, city: str) -> List[str]:
        """출발시간 추천 (현지 시간 기준)"""
        recommendations = []
        condition = weather.weather_condition.lower()
        
        # 현지 시간 기준으로 출퇴근 시간 판단
        local_time, _ = self.get_city_local_time(city, weather.timezone_offset)
        current_hour = local_time.hour
        
        if 'rain' in condition or 'snow' in condition:
            recommendations.extend([
                "⏰ 평소보다 15-20분 일찍 출발",
                "🚇 대중교통 지연 가능성 고려",
                "📱 실시간 교통정보 확인 필수",
                "🏠 재택근무 고려해보기"
            ])
        elif weather.wind_speed > 10:
            recommendations.extend([
                "💨 강풍으로 인한 지연 가능, 10분 일찍 출발",
                "🚌 버스 배차 간격 늘어날 수 있음"
            ])
        else:
            recommendations.extend([
                "✅ 평소 시간에 출발해도 충분",
                "🌤️ 좋은 날씨로 쾌적한 이동 가능"
            ])
            
        # 현지 시간 기준 시간대별 조언
        if 7 <= current_hour <= 9:
            recommendations.append(f"🌅 현지 출근시간 ({current_hour}시): 교통량 많으니 여유시간 확보")
        elif 17 <= current_hour <= 19:
            recommendations.append(f"🌆 현지 퇴근시간 ({current_hour}시): 혼잡 시간대 피하거나 대안 경로 고려")
        elif 22 <= current_hour or current_hour <= 5:
            recommendations.append(f"🌙 현지 심야시간 ({current_hour}시): 대중교통 운행 상황 확인 필요")
            
        return recommendations

    def get_health_advice(self, weather: WeatherData) -> List[str]:
        """건강 조언"""
        advice = []
        temp = weather.temperature
        humidity = weather.humidity
        
        if temp < 0:
            advice.extend([
                "🥶 체온 유지 중요, 따뜻한 음료 섭취",
                "🏠 실내외 온도차 주의",
                "💊 감기 예방에 신경쓰기"
            ])
        elif temp > 30:
            advice.extend([
                "💧 충분한 수분 섭취 필수",
                "😎 직사광선 피하고 그늘 이용",
                "🏠 에어컨 사용으로 시원하게"
            ])
            
        if humidity > 80:
            advice.append("💨 높은 습도, 통풍 잘 되는 옷 선택")
        elif humidity < 30:
            advice.append("💧 건조함, 보습제 사용 및 수분 섭취")
            
        advice.extend([
            "😷 마스크 착용으로 미세먼지 차단",
            "🏃‍♂️ 적절한 운동으로 건강 유지",
            "🥗 계절에 맞는 음식 섭취"
        ])
        
        return advice

def main():
    """메인 앱 함수"""
    app = WeatherApp()
    
    # 헤더
    st.title("🌤️ 스마트 출퇴근 도우미")
    st.markdown("**전 세계 도시별 현지 시간 & 날씨 기반 맞춤 가이드**")
    st.divider()
    
    # API 키 설정 (사이드바)
    with st.sidebar:
        st.header("⚙️ 설정")
        
        if app.api_key:
            st.success("✅ API 키 설정됨")
        else:
            st.warning("🔑 API 키가 설정되지 않았습니다")
            api_key_input = st.text_input(
                "OpenWeatherMap API 키",
                type="password",
                help="https://openweathermap.org/api 에서 무료 발급"
            )
            
            if api_key_input:
                st.session_state.api_key = api_key_input
                app.api_key = api_key_input
                st.success("✅ API 키가 설정되었습니다!")
                st.rerun()
        
        st.subheader("🕐 시간대 정보")
        st.info("""
        **지원 도시별 현지 시간:**
        • 🇰🇷 한국: Seoul, Busan, Incheon 등
        • 🇯🇵 일본: Tokyo, Osaka 
        • 🇨🇳 중국: Beijing, Shanghai
        • 🇺🇸 미국: New York, Los Angeles
        • 🇬🇧 영국: London
        • 🇫🇷 프랑스: Paris
        • 기타 전 세계 주요 도시
        """)

    # 메인 컨텐츠
    col1, col2 = st.columns([3, 1])
    
    with col1:
        cities = [
            "Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju",
            "Tokyo", "Osaka", "Beijing", "Shanghai", "Hong Kong", "Singapore",
            "New York", "Los Angeles", "London", "Paris", "Sydney", "Dubai"
        ]
        
        selected_city = st.selectbox(
            "🏙️ 도시를 선택하세요",
            cities,
            index=0,
            help="선택한 도시의 현지 시간과 날씨를 표시합니다"
        )
    
    with col2:
        if st.button("🔄 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # 날씨 정보 가져오기
    with st.spinner(f"🌤️ {selected_city}의 날씨 정보를 가져오는 중..."):
        weather_data = app.fetch_weather_data(selected_city)
    
    if weather_data:
        # 날씨 정보 표시 (현지 시간 포함)
        app.display_weather_info(weather_data, selected_city)
        
        st.divider()
        
        # 상세 날씨 정보
        st.subheader("📊 상세 날씨 정보")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💧 습도", f"{weather_data.humidity}%")
        with col2:
            st.metric("💨 바람", f"{weather_data.wind_speed:.1f}m/s")
        with col3:
            st.metric("👁️ 가시거리", f"{weather_data.visibility:.1f}km")
        with col4:
            st.metric("🌡️ 기압", f"{weather_data.pressure}hPa")
        
        st.divider()
        
        # 추천사항 탭
        st.subheader("💡 스마트 추천")
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "👔 복장",
            "🚇 교통",
            "⏰ 시간",
            "💊 건강"
        ])
        
        with tab1:
            st.markdown("**👔 오늘의 복장 추천**")
            outfit_recs = app.get_outfit_recommendation(weather_data)
            for i, rec in enumerate(outfit_recs, 1):
                st.write(f"{i}. {rec}")
        
        with tab2:
            st.markdown("**🚇 교통수단 추천**")
            transport_recs = app.get_transport_recommendation(weather_data)
            for i, rec in enumerate(transport_recs, 1):
                st.write(f"{i}. {rec}")
        
        with tab3:
            st.markdown("**⏰ 출발시간 가이드**")
            time_recs = app.get_departure_time_recommendation(weather_data, selected_city)
            for i, rec in enumerate(time_recs, 1):
                st.write(f"{i}. {rec}")
        
        with tab4:
            st.markdown("**💊 건강 관리 조언**")
            health_recs = app.get_health_advice(weather_data)
            for i, rec in enumerate(health_recs, 1):
                st.write(f"{i}. {rec}")

if __name__ == "__main__":
    main()