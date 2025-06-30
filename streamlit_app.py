# streamlit_app.py - 스마트 출퇴근 도우미 Streamlit 모바일 버전

import streamlit as st
import requests
import json
import datetime
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

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
    /* 모바일 최적화 스타일 */
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
    
    .big-emoji {
        font-size: 3rem;
        text-align: center;
    }
    
    .temperature {
        font-size: 3rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    
    .status-good {
        color: #28a745;
        font-weight: bold;
    }
    
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
    
    .status-danger {
        color: #dc3545;
        font-weight: bold;
    }
    
    /* 모바일에서 버튼 크기 조정 */
    .stButton > button {
        width: 100%;
        height: 3rem;
        font-size: 1.1rem;
        font-weight: bold;
    }
    
    /* 선택박스 모바일 최적화 */
    .stSelectbox > div > div {
        font-size: 1.1rem;
    }
    
    /* 탭 스타일 개선 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        color: #333;
        font-weight: bold;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #667eea;
        color: white;
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
    uv_index: Optional[float] = None
    timestamp: datetime.datetime = None

class WeatherApp:
    """스마트 출퇴근 도우미 메인 클래스"""
    
    def __init__(self):
        self.api_key = self.get_api_key()
        self.backup_data = {
            "temp": 22,
            "feels_like": 24,
            "humidity": 65,
            "weather": "Clear",
            "description": "맑음",
            "wind_speed": 3.2
        }

    def get_api_key(self) -> str:
        """API 키 가져오기 (Streamlit Secrets 사용)"""
        try:
            return st.secrets["OPENWEATHER_API_KEY"]
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

    @st.cache_data(ttl=600)  # 10분 캐시
    def fetch_weather_data(_self, city: str) -> Optional[WeatherData]:
        """OpenWeatherMap API에서 날씨 데이터 가져오기 (캐시 적용)"""
        if not _self.api_key:
            return _self._get_backup_weather_data()
            
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
            
            return WeatherData(
                temperature=data['main']['temp'],
                feels_like=data['main']['feels_like'],
                humidity=data['main']['humidity'],
                pressure=data['main']['pressure'],
                weather_condition=data['weather'][0]['main'],
                weather_description=data['weather'][0]['description'],
                wind_speed=data['wind']['speed'],
                visibility=data.get('visibility', 10000) / 1000,
                timestamp=datetime.datetime.now()
            )
            
        except requests.exceptions.RequestException:
            st.warning("⚠️ API 호출 실패: 데모 데이터를 사용합니다")
            return _self._get_backup_weather_data()
        except Exception as e:
            st.error(f"❌ 오류 발생: {str(e)}")
            return _self._get_backup_weather_data()

    def _get_backup_weather_data(self) -> WeatherData:
        """백업 날씨 데이터 반환"""
        return WeatherData(
            temperature=self.backup_data['temp'],
            feels_like=self.backup_data['feels_like'],
            humidity=self.backup_data['humidity'],
            pressure=1013,
            weather_condition=self.backup_data['weather'],
            weather_description=self.backup_data['description'],
            wind_speed=self.backup_data['wind_speed'],
            visibility=10.0,
            timestamp=datetime.datetime.now()
        )

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

    def get_departure_time_recommendation(self, weather: WeatherData) -> List[str]:
        """출발시간 추천"""
        recommendations = []
        condition = weather.weather_condition.lower()
        
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
            
        # 시간대별 추가 조언
        current_hour = datetime.datetime.now().hour
        if 7 <= current_hour <= 9:
            recommendations.append("🌅 출근시간: 교통량 많으니 여유시간 확보")
        elif 17 <= current_hour <= 19:
            recommendations.append("🌆 퇴근시간: 혼잡 시간대 피하거나 대안 경로 고려")
            
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

    def create_weather_chart(self, weather: WeatherData):
        """날씨 정보 차트 생성"""
        # 온도 게이지 차트
        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = weather.temperature,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "현재 온도 (°C)"},
            delta = {'reference': weather.feels_like},
            gauge = {
                'axis': {'range': [None, 40]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 10], 'color': "lightgray"},
                    {'range': [10, 25], 'color': "yellow"},
                    {'range': [25, 40], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': weather.feels_like
                }
            }
        ))
        
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        
        return fig

def main():
    """메인 앱 함수"""
    app = WeatherApp()
    
    # 헤더
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h1>🌤️ 스마트 출퇴근 도우미</h1>
        <p style='font-size: 1.2rem; color: #666;'>날씨 기반 맞춤형 출퇴근 가이드</p>
    </div>
    """, unsafe_allow_html=True)
    
    # API 키 설정 (사이드바)
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # API 키 입력
        if not app.api_key:
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
        else:
            st.success("✅ API 키 설정됨")
            
        # 기타 설정
        st.subheader("🎨 표시 설정")
        show_chart = st.checkbox("📊 온도 차트 표시", value=True)
        auto_refresh = st.checkbox("🔄 자동 새로고침 (30초)", value=False)
        
        st.subheader("📱 앱 정보")
        st.info("""
        **버전**: 1.0.0  
        **개발**: Python + Streamlit  
        **배포**: Streamlit Cloud  
        **모바일**: 최적화 완료 ✅
        """)

    # 메인 컨텐츠
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 도시 선택
        cities = [
            "Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju",
            "Tokyo", "Osaka", "Beijing", "Shanghai", "New York", "London", "Paris"
        ]
        
        selected_city = st.selectbox(
            "🏙️ 도시를 선택하세요",
            cities,
            index=0,
            help="전 세계 주요 도시의 날씨를 확인할 수 있습니다"
        )
    
    with col2:
        # 새로고침 버튼
        if st.button("🔄 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # 날씨 정보 가져오기
    with st.spinner("🌤️ 날씨 정보를 가져오는 중..."):
        weather_data = app.fetch_weather_data(selected_city)
    
    if weather_data:
        # 현재 시간 표시
        st.markdown(f"""
        <div style='text-align: center; color: #666; margin-bottom: 1rem;'>
            📅 {datetime.datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')} 기준
        </div>
        """, unsafe_allow_html=True)
        
        # 날씨 요약 카드
        icon = app.get_weather_icon(weather_data.weather_condition)
        
        st.markdown(f"""
        <div class="weather-card">
            <div class="big-emoji">{icon}</div>
            <div class="temperature">{weather_data.temperature:.1f}°C</div>
            <div style="font-size: 1.3rem; margin-bottom: 0.5rem;">{weather_data.weather_description}</div>
            <div>체감온도 {weather_data.feels_like:.1f}°C</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 상세 날씨 정보
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💧 습도",
                value=f"{weather_data.humidity}%",
                delta=None
            )
            
        with col2:
            st.metric(
                label="💨 바람",
                value=f"{weather_data.wind_speed:.1f}m/s",
                delta=None
            )
            
        with col3:
            st.metric(
                label="👁️ 가시거리",
                value=f"{weather_data.visibility:.1f}km",
                delta=None
            )
            
        with col4:
            st.metric(
                label="🌡️ 기압",
                value=f"{weather_data.pressure}hPa",
                delta=None
            )
        
        # 온도 차트 (선택사항)
        if show_chart:
            st.subheader("📊 온도 정보")
            chart = app.create_weather_chart(weather_data)
            st.plotly_chart(chart, use_container_width=True)
        
        # 추천사항 탭
        st.subheader("💡 스마트 추천")
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "👔 복장",
            "🚇 교통",
            "⏰ 시간",
            "💊 건강"
        ])
        
        with tab1:
            st.markdown("### 👔 오늘의 복장 추천")
            outfit_recs = app.get_outfit_recommendation(weather_data)
            for i, rec in enumerate(outfit_recs, 1):
                st.markdown(f"""
                <div class="recommendation-card">
                    <strong>{i}.</strong> {rec}
                </div>
                """, unsafe_allow_html=True)
        
        with tab2:
            st.markdown("### 🚇 교통수단 추천")
            transport_recs = app.get_transport_recommendation(weather_data)
            for i, rec in enumerate(transport_recs, 1):
                st.markdown(f"""
                <div class="recommendation-card">
                    <strong>{i}.</strong> {rec}
                </div>
                """, unsafe_allow_html=True)
        
        with tab3:
            st.markdown("### ⏰ 출발시간 가이드")
            time_recs = app.get_departure_time_recommendation(weather_data)
            for i, rec in enumerate(time_recs, 1):
                st.markdown(f"""
                <div class="recommendation-card">
                    <strong>{i}.</strong> {rec}
                </div>
                """, unsafe_allow_html=True)
        
        with tab4:
            st.markdown("### 💊 건강 관리 조언")
            health_recs = app.get_health_advice(weather_data)
            for i, rec in enumerate(health_recs, 1):
                st.markdown(f"""
                <div class="recommendation-card">
                    <strong>{i}.</strong> {rec}
                </div>
                """, unsafe_allow_html=True)
        
        # 날씨 상태에 따른 전체 평가
        st.subheader("🎯 오늘의 출퇴근 평가")
        
        # 점수 계산 로직
        score = 100
        status_class = "status-good"
        status_text = "최적"
        
        if 'rain' in weather_data.weather_condition.lower():
            score -= 30
            status_class = "status-warning"
            status_text = "주의"
        elif 'snow' in weather_data.weather_condition.lower():
            score -= 40
            status_class = "status-danger"
            status_text = "위험"
        elif weather_data.wind_speed > 15:
            score -= 20
            status_class = "status-warning"
            status_text = "주의"
            
        if weather_data.temperature < 0 or weather_data.temperature > 35:
            score -= 15
            
        score = max(score, 0)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"""
            <div style='text-align: center; padding: 2rem; background: #f8f9fa; border-radius: 1rem; margin: 1rem 0;'>
                <div style='font-size: 3rem; margin-bottom: 0.5rem;'>
                    {'🟢' if score >= 80 else '🟡' if score >= 60 else '🔴'}
                </div>
                <div style='font-size: 2rem; font-weight: bold;' class='{status_class}'>
                    {score}점
                </div>
                <div style='font-size: 1.2rem; margin-top: 0.5rem;'>
                    출퇴근 난이도: <span class='{status_class}'>{status_text}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; margin-top: 2rem;'>
        <p>🌤️ 스마트 출퇴근 도우미 | Made with ❤️ by Python & Streamlit</p>
        <p>📱 모바일 최적화 완료 | 🌍 전 세계 날씨 지원</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 자동 새로고침
    if auto_refresh:
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()