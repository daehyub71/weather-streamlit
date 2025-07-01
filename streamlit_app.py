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
        """API 키 가져오기 - session_state 우선"""
        # session_state 우선 확인 (사용자 입력)
        if "api_key" in st.session_state and st.session_state.api_key:
            return st.session_state.api_key
        # secrets 확인 (배포 환경)
        try:
            return st.secrets.get("OPENWEATHER_API_KEY", "")
        except:
            return ""

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
    def fetch_weather_data(_self, city: str, api_key: str = None) -> Optional[WeatherData]:
        """날씨 데이터 가져오기"""
        # API 키 우선순위: 매개변수 > 인스턴스 변수
        current_api_key = api_key or _self.api_key
        
        if not current_api_key:
            return _self._get_backup_weather_data(city)
            
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': city,
                'appid': current_api_key,
                'units': 'metric',
                'lang': 'kr'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 일출/일몰 시간 변환 (Unix timestamp → 현지 시간으로 변환)
            timezone_offset_hours = data['timezone'] / 3600
            
            sunrise_utc = datetime.datetime.fromtimestamp(data['sys']['sunrise'], tz=datetime.timezone.utc)
            sunset_utc = datetime.datetime.fromtimestamp(data['sys']['sunset'], tz=datetime.timezone.utc)
            
            # 현지 시간대로 변환
            local_tz = datetime.timezone(datetime.timedelta(hours=timezone_offset_hours))
            sunrise_local = sunrise_utc.astimezone(local_tz)
            sunset_local = sunset_utc.astimezone(local_tz)
            
            return WeatherData(
                temperature=data['main']['temp'],
                feels_like=data['main']['feels_like'],
                humidity=data['main']['humidity'],
                pressure=data['main']['pressure'],
                weather_condition=data['weather'][0]['main'],
                weather_description=data['weather'][0]['description'],
                wind_speed=data['wind']['speed'],
                visibility=data.get('visibility', 10000) / 1000,
                sunrise=sunrise_local,
                sunset=sunset_local,
                timezone_offset=data['timezone'],  # UTC 기준 오프셋 (초)
                timestamp=datetime.datetime.now(),
                source="OpenWeatherMap API"
            )
            
        except Exception as e:
            st.warning(f"⚠️ API 호출 실패: 데모 데이터를 사용합니다")
            return _self._get_backup_weather_data(city)

    def _get_backup_weather_data(self, city: str) -> WeatherData:
        """백업 날씨 데이터 반환"""
        # 현지 시간 기준으로 일출/일몰 설정
        local_time, _ = self.get_city_local_time(city)
        
        # 계절에 맞는 일출/일몰 시간 (7월 기준)
        sunrise_time = local_time.replace(hour=6, minute=0, second=0, microsecond=0)
        sunset_time = local_time.replace(hour=19, minute=30, second=0, microsecond=0)
        
        return WeatherData(
            temperature=self.backup_data['temp'],
            feels_like=self.backup_data['feels_like'],
            humidity=self.backup_data['humidity'],
            pressure=1013,
            weather_condition=self.backup_data['weather'],
            weather_description=self.backup_data['description'],
            wind_speed=self.backup_data['wind_speed'],
            visibility=10.0,
            sunrise=sunrise_time,
            sunset=sunset_time,
            timezone_offset=32400,  # KST (+9)
            timestamp=local_time,
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
        
        # 데이터 출처 강조 표시
        if weather.source == "데모 데이터":
            st.error(f"⚠️ **데이터 출처: {weather.source}** - API 키를 확인하세요!")
        else:
            st.success(f"✅ **데이터 출처: {weather.source}**")
        
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
        """개선된 옷차림 추천 - 실제 기상 데이터 기반"""
        recommendations = []
        temp = weather.temperature
        feels_like = weather.feels_like
        humidity = weather.humidity
        wind_speed = weather.wind_speed
        condition = weather.weather_condition.lower()
        
        # 체감온도 기준 기본 복장
        effective_temp = feels_like if abs(feels_like - temp) > 2 else temp
        
        if effective_temp < -10:
            recommendations.extend([
                "🧥 두꺼운 패딩 또는 겨울 코트 필수",
                "🧤 방한장갑, 목도리, 털모자 착용",
                "👢 방수 겨울부츠, 미끄럼방지 밑창",
                "🔥 핫팩 여러 개 준비 (손, 발, 몸통용)"
            ])
        elif effective_temp < 0:
            recommendations.extend([
                "🧥 패딩 재킷 또는 울코트",
                "🧤 장갑과 목도리 필수",
                "👢 따뜻한 부츠 착용"
            ])
        elif effective_temp < 10:
            recommendations.extend([
                "🧥 두꺼운 자켓 또는 코트",
                "👕 니트나 긴팔 셔츠 + 카디건",
                "👖 긴바지, 두꺼운 양말"
            ])
        elif effective_temp < 15:
            recommendations.extend([
                "👔 얇은 자켓 또는 가디건",
                "👕 긴팔 셔츠 또는 얇은 니트",
                "👖 긴바지 추천"
            ])
        elif effective_temp < 20:
            recommendations.extend([
                "👕 긴팔 또는 얇은 가디건",
                "👖 긴바지 또는 면바지",
                "🧥 얇은 겉옷 가져가기"
            ])
        elif effective_temp < 25:
            recommendations.extend([
                "👕 반팔 또는 얇은 긴팔",
                "👖 면바지 또는 7부바지",
                "🧥 가벼운 겉옷 준비"
            ])
        else:
            recommendations.extend([
                "👕 반팔, 민소매 또는 통풍 잘 되는 옷",
                "🩳 반바지 또는 치마",
                "🕶️ 선글라스, 모자 준비",
                "🧴 선크림 SPF 30+ 필수"
            ])
        
        # 날씨별 추가 권장사항
        if 'rain' in condition or 'drizzle' in condition:
            recommendations.extend([
                "☔ 우산 또는 방수 우비 필수",
                "👢 방수 신발 착용",
                "🎒 방수 가방 또는 가방 커버"
            ])
        elif 'thunderstorm' in condition:
            recommendations.extend([
                "⛈️ 완전 방수 의류 필수",
                "🏠 가능하면 실내 대기 권장"
            ])
        elif 'snow' in condition:
            recommendations.extend([
                "❄️ 미끄럼방지 신발 필수",
                "🧥 방수 외투 착용",
                "🧤 방수 장갑 권장"
            ])
        
        # 습도별 조언
        if humidity > 80:
            recommendations.append("💨 통풍 잘 되는 소재 선택 (면, 리넨)")
        elif humidity < 30:
            recommendations.append("💧 보습 로션 사용, 립밤 준비")
        
        # 바람별 조언
        if wind_speed > 10:
            recommendations.append("💨 바람막이 재킷 또는 윈드브레이커 추천")
        
        return recommendations

    def get_transport_recommendation(self, weather: WeatherData) -> List[str]:
        """개선된 교통수단 추천 - 종합적 기상 조건 분석"""
        recommendations = []
        condition = weather.weather_condition.lower()
        wind_speed = weather.wind_speed
        visibility = weather.visibility
        temp = weather.temperature
        humidity = weather.humidity
        
        # 기상 위험도 계산
        risk_score = 0
        
        if 'rain' in condition or 'drizzle' in condition:
            risk_score += 3
        elif 'thunderstorm' in condition:
            risk_score += 5
        elif 'snow' in condition:
            risk_score += 4
        elif 'fog' in condition or 'mist' in condition:
            risk_score += 2
        
        if wind_speed > 15:
            risk_score += 3
        elif wind_speed > 10:
            risk_score += 1
            
        if visibility < 5:
            risk_score += 2
        elif visibility < 10:
            risk_score += 1
            
        if temp < -5 or temp > 35:
            risk_score += 2
            
        # 위험도별 교통수단 추천
        if risk_score >= 7:
            recommendations.extend([
                "🚇 지하철 강력 추천 (가장 안전하고 정시성 우수)",
                "🏠 가능하면 재택근무 또는 일정 연기 고려",
                "🚗 자차 이용 시 극도로 주의운전",
                "🚴‍♂️ 자전거/킥보드/도보 절대 금지"
            ])
        elif risk_score >= 4:
            recommendations.extend([
                "🚇 지하철 이용 강력 추천",
                "🚌 버스 이용 시 배차간격 지연 예상",
                "🚗 자차 이용 시 안전거리 충분히 확보",
                "🚴‍♂️ 개인형 이동수단 피하기"
            ])
        elif risk_score >= 2:
            recommendations.extend([
                "🚇 지하철/🚌 버스 모두 무난",
                "🚗 자차 이용 시 주의운전",
                "🚴‍♂️ 자전거/킥보드 신중히 판단",
                "📱 실시간 교통정보 확인 권장"
            ])
        else:
            recommendations.extend([
                "🚶‍♂️ 도보나 자전거로 이동하기 좋은 날",
                "🚴‍♂️ 킥보드, 자전거 등 친환경 이동수단 추천",
                "🚇🚌 모든 대중교통 쾌적하게 이용 가능",
                "🚗 드라이브하기 좋은 날씨"
            ])
        
        # 세부 조건별 추가 권장사항
        if 'rain' in condition:
            recommendations.append("☔ 대중교통 이용 시 우산 준비, 젖은 신발 주의")
        if wind_speed > 12:
            recommendations.append("💨 고층건물 주변 돌풍 주의")
        if visibility < 5:
            recommendations.append("👁️ 낮은 가시거리, 차량 전조등 점등 필수")
        if temp < 0:
            recommendations.append("🧊 노면 결빙 가능성, 미끄럼 주의")
        if humidity > 85:
            recommendations.append("💧 높은 습도로 실내 환기 필요")
            
        return recommendations

    def get_departure_time_recommendation(self, weather: WeatherData, city: str) -> List[str]:
        """개선된 출발시간 추천 - 현지 교통패턴 & 기상조건 분석"""
        recommendations = []
        condition = weather.weather_condition.lower()
        wind_speed = weather.wind_speed
        visibility = weather.visibility
        
        # 현지 시간 기준으로 출퇴근 시간 판단
        local_time, _ = self.get_city_local_time(city, weather.timezone_offset)
        current_hour = local_time.hour
        weekday = local_time.weekday()  # 0=월요일, 6=일요일
        
        # 기상 조건에 따른 지연 시간 계산
        delay_minutes = 0
        
        if 'thunderstorm' in condition:
            delay_minutes += 30
        elif 'snow' in condition:
            delay_minutes += 25
        elif 'rain' in condition or 'drizzle' in condition:
            delay_minutes += 15
        elif 'fog' in condition or 'mist' in condition:
            delay_minutes += 10
            
        if wind_speed > 15:
            delay_minutes += 10
        elif wind_speed > 10:
            delay_minutes += 5
            
        if visibility < 5:
            delay_minutes += 15
        elif visibility < 10:
            delay_minutes += 5
        
        # 주말/평일 구분
        is_weekend = weekday >= 5
        
        if is_weekend:
            recommendations.append("🎉 주말이므로 교통량이 평일보다 적습니다")
        
        # 시간대별 교통 분석 (평일 기준)
        if not is_weekend:
            if 6 <= current_hour <= 9:
                recommendations.append(f"🌅 출근시간대 ({current_hour}시): 교통혼잡 예상")
                delay_minutes += 10
            elif 17 <= current_hour <= 20:
                recommendations.append(f"🌆 퇴근시간대 ({current_hour}시): 극심한 교통혼잡")
                delay_minutes += 15
            elif 11 <= current_hour <= 13:
                recommendations.append(f"🍽️ 점심시간대 ({current_hour}시): 약간의 혼잡")
                delay_minutes += 5
            elif 22 <= current_hour or current_hour <= 5:
                recommendations.append(f"🌙 심야시간 ({current_hour}시): 대중교통 운행 간격 확인")
                if current_hour >= 23 or current_hour <= 4:
                    delay_minutes += 20  # 심야 대중교통 대기시간
        
        # 최종 출발시간 권장사항
        if delay_minutes >= 30:
            recommendations.extend([
                f"⏰ 평소보다 {delay_minutes}분 일찍 출발 권장",
                "🏠 가능하면 재택근무 또는 일정 조정 고려",
                "📱 실시간 교통정보 필수 확인",
                "🚇 대중교통 지연 및 운행 중단 가능성 체크"
            ])
        elif delay_minutes >= 15:
            recommendations.extend([
                f"⏰ 평소보다 {delay_minutes}분 일찍 출발",
                "📱 실시간 교통정보 확인 필수",
                "🚇 대중교통 배차간격 늘어날 수 있음"
            ])
        elif delay_minutes >= 5:
            recommendations.extend([
                f"⏰ 평소보다 {delay_minutes}분 정도 일찍 출발",
                "📱 교통정보 한 번 체크해보기"
            ])
        else:
            recommendations.extend([
                "✅ 평소 시간에 출발해도 충분",
                "🌤️ 좋은 날씨로 쾌적한 이동 예상"
            ])
        
        # 도시별 특수 상황 고려
        if city in ['Seoul', 'Busan', 'Tokyo']:
            if delay_minutes > 0:
                recommendations.append("🚇 지하철망 발달 지역: 지하철 우선 이용 권장")
        elif city in ['New York', 'London']:
            if delay_minutes > 10:
                recommendations.append("🚌 대도시 교통체증: 지하철/버스 혼용 고려")
        elif city in ['Los Angeles']:
            if delay_minutes > 0:
                recommendations.append("🚗 자동차 도시: 고속도로 우회로 검토")
                
        return recommendations

    def get_health_advice(self, weather: WeatherData) -> List[str]:
        """개선된 건강 조언 - 기상의학 기반 종합 분석"""
        advice = []
        temp = weather.temperature
        feels_like = weather.feels_like
        humidity = weather.humidity
        pressure = weather.pressure
        condition = weather.weather_condition.lower()
        wind_speed = weather.wind_speed
        
        # 온도별 건강 관리
        if temp < -10:
            advice.extend([
                "🥶 체온저하 위험: 따뜻한 음료 자주 섭취",
                "🫀 심혈관 질환자 외출 시 특별 주의",
                "🏠 실내외 온도차 20도 이상 시 서서히 적응",
                "🤧 호흡기 보호: 마스크나 목도리로 찬공기 차단"
            ])
        elif temp < 0:
            advice.extend([
                "🧊 동상 위험 부위 (손가락, 발가락, 귀) 보온 철저",
                "💧 실내 건조 주의: 가습기 사용 권장",
                "🍲 따뜻한 음식으로 체온 유지"
            ])
        elif temp > 35:
            advice.extend([
                "🌡️ 열사병 주의: 그늘에서 휴식 자주 취하기",
                "💧 탈수 방지: 30분마다 물 한 컵씩 섭취",
                "🧂 전해질 보충: 이온음료나 소금 조금 섭취",
                "❄️ 에어컨 사용 시 실내외 온도차 5-7도 유지"
            ])
        elif temp > 30:
            advice.extend([
                "💦 충분한 수분 섭취 (하루 2-3L)",
                "😎 직사광선 피하고 그늘 이용",
                "🍉 수분 많은 과일 섭취 권장"
            ])
        
        # 습도별 건강 영향
        if humidity > 85:
            advice.extend([
                "💨 고습도로 인한 답답함: 통풍 자주 시키기",
                "🦠 세균 번식 주의: 개인위생 철저히",
                "👕 땀 흡수 잘 되는 면 소재 의류 착용"
            ])
        elif humidity > 70:
            advice.append("🌫️ 높은 습도: 체감온도 상승, 수분 섭취 증가")
        elif humidity < 30:
            advice.extend([
                "🏜️ 건조 주의: 피부 보습제 수시로 사용",
                "👃 코 점막 건조 방지: 식염수 스프레이 활용",
                "💧 가습기 사용 또는 젖은 수건 활용"
            ])
        elif humidity < 40:
            advice.append("🌵 약간 건조: 립밤, 핸드크림 준비")
        
        # 기압별 건강 영향
        if pressure < 1000:
            advice.extend([
                "📉 저기압: 관절염/두통 악화 가능",
                "😴 충분한 수면과 휴식 권장",
                "🧘‍♀️ 스트레칭이나 가벼운 운동으로 혈액순환 개선"
            ])
        elif pressure > 1030:
            advice.append("📈 고기압: 대체로 몸이 가벼움, 야외활동 좋은 날")
        
        # 날씨별 건강 주의사항
        if 'rain' in condition or 'thunderstorm' in condition:
            advice.extend([
                "🌧️ 우울감 주의: 실내 조명 밝게 하기",
                "☔ 젖은 옷 즉시 갈아입기 (감기 예방)",
                "🦶 발 습기 제거: 양말 여분 준비"
            ])
        
        if 'snow' in condition:
            advice.extend([
                "❄️ 미끄러짐 사고 주의: 보폭 줄이고 천천히 걷기",
                "👁️ 설맹 주의: 선글라스 착용 권장"
            ])
        
        if wind_speed > 15:
            advice.extend([
                "💨 강풍으로 인한 안구건조: 인공눈물 사용",
                "🌪️ 비산물질 주의: 마스크 착용"
            ])
        
        # 계절별 기본 건강관리
        advice.extend([
            "😷 미세먼지 차단: 보건용 마스크 착용",
            "🚶‍♂️ 날씨에 맞는 적절한 운동 지속",
            "🥗 제철 음식과 비타민 섭취로 면역력 강화",
            "💤 규칙적인 수면 패턴 유지 (7-8시간)"
        ])
        
        # 체감온도와 실제온도 차이가 클 때 추가 조언
        temp_diff = abs(feels_like - temp)
        if temp_diff > 5:
            advice.append(f"🌡️ 체감온도({feels_like:.1f}°C)와 실제온도 차이 큼: 체온조절 신경쓰기")
        
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
        
        # 실시간 API 키 상태 확인
        current_api_key = app.get_api_key()
        
        if current_api_key:
            st.success("✅ API 키 설정됨")
            st.info(f"🔑 API 키 길이: {len(current_api_key)}자")
            # API 키 삭제 버튼 추가
            if st.button("🗑️ API 키 삭제"):
                if "api_key" in st.session_state:
                    del st.session_state.api_key
                st.cache_data.clear()
                st.rerun()
        else:
            st.warning("🔑 API 키가 설정되지 않았습니다")
            api_key_input = st.text_input(
                "OpenWeatherMap API 키",
                type="password",
                help="https://openweathermap.org/api 에서 무료 발급"
            )
            
            if api_key_input:
                st.session_state.api_key = api_key_input
                # API 키 변경 시 캐시 클리어
                st.cache_data.clear()
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
        # 실시간으로 API 키 확인
        current_api_key = app.get_api_key()
        weather_data = app.fetch_weather_data(selected_city, current_api_key)
    
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