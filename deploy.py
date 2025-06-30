# deploy.py - Streamlit Cloud 빠른 배포 스크립트

import os
import subprocess
import sys
import webbrowser
from pathlib import Path

def print_header():
    """배포 스크립트 헤더 출력"""
    print("📱" + "="*58 + "📱")
    print("🚀 Streamlit Cloud 빠른 배포 스크립트 🚀")
    print("📱" + "="*58 + "📱")
    print()

def check_required_files():
    """필수 파일 확인"""
    print("📄 필수 파일 확인 중...")
    
    required_files = {
        'streamlit_app.py': '메인 Streamlit 앱',
        'requirements.txt': '의존성 패키지 목록',
        '.streamlit/config.toml': 'Streamlit 설정',
        '.gitignore': 'Git 무시 파일'
    }
    
    missing_files = []
    for filename, description in required_files.items():
        if os.path.exists(filename):
            print(f"   ✅ {filename} ({description})")
        else:
            print(f"   ❌ {filename} ({description}) - 누락됨")
            missing_files.append(filename)
    
    if missing_files:
        print(f"\n❌ 누락된 파일들: {', '.join(missing_files)}")
        print("📥 모든 파일을 다운로드했는지 확인해주세요.")
        return False
    
    print("✅ 모든 필수 파일 확인됨!")
    return True

def check_secrets_file():
    """secrets.toml 파일 확인"""
    print("\n🔑 API 키 설정 확인 중...")
    
    secrets_path = '.streamlit/secrets.toml'
    
    if os.path.exists(secrets_path):
        print("✅ secrets.toml 파일이 존재합니다")
        
        # 파일 내용 확인
        try:
            with open(secrets_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'OPENWEATHER_API_KEY' in content and 'your_openweathermap_api_key_here' not in content:
                print("✅ API 키가 설정되어 있습니다")
                return True
            else:
                print("⚠️ API 키가 설정되지 않았습니다")
                
        except Exception as e:
            print(f"❌ secrets.toml 파일 읽기 실패: {e}")
            
    else:
        print("❌ secrets.toml 파일이 없습니다")
    
    print("\n📝 API 키 설정 방법:")
    print("1. https://openweathermap.org/api 에서 무료 API 키 발급")
    print("2. .streamlit/secrets.toml 파일 생성")
    print("3. 다음 내용 추가:")
    print('   OPENWEATHER_API_KEY = "your_actual_api_key_here"')
    print()
    
    setup_now = input("지금 API 키를 설정하시겠습니까? (y/n): ").lower()
    if setup_now == 'y':
        return setup_api_key()
    
    return False

def setup_api_key():
    """API 키 설정"""
    print("\n🔑 API 키 설정")
    
    api_key = input("OpenWeatherMap API 키를 입력하세요: ").strip()
    
    if not api_key:
        print("❌ API 키가 입력되지 않았습니다")
        return False
    
    if len(api_key) != 32:
        print("⚠️ API 키 형식이 올바르지 않을 수 있습니다 (32자여야 함)")
        continue_anyway = input("계속 진행하시겠습니까? (y/n): ").lower()
        if continue_anyway != 'y':
            return False
    
    # .streamlit 디렉토리 생성
    os.makedirs('.streamlit', exist_ok=True)
    
    # secrets.toml 파일 생성
    secrets_content = f'''# .streamlit/secrets.toml - API 키 설정
OPENWEATHER_API_KEY = "{api_key}"
DEFAULT_CITY = "Seoul"
'''
    
    try:
        with open('.streamlit/secrets.toml', 'w', encoding='utf-8') as f:
            f.write(secrets_content)
        
        print("✅ API 키가 설정되었습니다!")
        return True
        
    except Exception as e:
        print(f"❌ secrets.toml 파일 생성 실패: {e}")
        return False

def check_git_status():
    """Git 상태 확인"""
    print("\n📝 Git 상태 확인 중...")
    
    # Git 초기화 확인
    if not os.path.exists('.git'):
        print("❌ Git 저장소가 초기화되지 않았습니다")
        
        init_git = input("Git를 초기화하시겠습니까? (y/n): ").lower()
        if init_git == 'y':
            try:
                subprocess.run(['git', 'init'], check=True, capture_output=True)
                print("✅ Git 저장소 초기화 완료")
            except subprocess.CalledProcessError as e:
                print(f"❌ Git 초기화 실패: {e}")
                return False
        else:
            return False
    
    # Git 상태 확인
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            print("📝 커밋되지 않은 변경사항이 있습니다:")
            print(result.stdout)
            
            commit_now = input("변경사항을 커밋하시겠습니까? (y/n): ").lower()
            if commit_now == 'y':
                return commit_changes()
            else:
                print("⚠️ 변경사항을 커밋하지 않으면 배포에 반영되지 않습니다")
                return True
        else:
            print("✅ 모든 변경사항이 커밋되었습니다")
            return True
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Git 상태 확인 실패: {e}")
        return False

def commit_changes():
    """변경사항 커밋"""
    try:
        # 모든 파일 추가 (secrets.toml 제외)
        subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
        
        # secrets.toml 파일 제거 (보안상 중요!)
        try:
            subprocess.run(['git', 'reset', '.streamlit/secrets.toml'], 
                         check=True, capture_output=True)
            print("🔒 secrets.toml 파일을 Git에서 제외했습니다 (보안)")
        except:
            pass  # 파일이 없을 수 있음
        
        # 커밋 메시지 입력
        commit_message = input("커밋 메시지를 입력하세요 (Enter: 기본 메시지): ").strip()
        if not commit_message:
            commit_message = "Deploy: Weather Commute Assistant to Streamlit Cloud"
        
        subprocess.run(['git', 'commit', '-m', commit_message], 
                      check=True, capture_output=True)
        
        print("✅ 변경사항 커밋 완료")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 커밋 실패: {e}")
        return False

def check_remote_repository():
    """원격 저장소 확인"""
    print("\n🌐 GitHub 저장소 확인 중...")
    
    try:
        result = subprocess.run(['git', 'remote', '-v'], 
                              capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            print("✅ GitHub 저장소가 연결되어 있습니다:")
            print(result.stdout)
            return True
        else:
            print("❌ GitHub 저장소가 연결되지 않았습니다")
            return setup_remote_repository()
            
    except subprocess.CalledProcessError:
        print("❌ Git 원격 저장소 확인 실패")
        return False

def setup_remote_repository():
    """원격 저장소 설정"""
    print("\n📦 GitHub 저장소 설정")
    print("1. https://github.com 에서 새 저장소 생성")
    print("2. 저장소 URL을 복사하세요")
    print()
    
    repo_url = input("GitHub 저장소 URL을 입력하세요: ").strip()
    
    if not repo_url:
        print("❌ 저장소 URL이 입력되지 않았습니다")
        return False
    
    try:
        subprocess.run(['git', 'remote', 'add', 'origin', repo_url], 
                      check=True, capture_output=True)
        print("✅ GitHub 저장소 연결 완료")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 저장소 연결 실패: {e}")
        return False

def push_to_github():
    """GitHub에 푸시"""
    print("\n📤 GitHub에 코드 업로드 중...")
    
    try:
        # 현재 브랜치 확인
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True, check=True)
        branch = result.stdout.strip() or 'main'
        
        # 첫 푸시인지 확인
        try:
            subprocess.run(['git', 'ls-remote', '--exit-code', 'origin'], 
                         check=True, capture_output=True)
            # 원격 저장소가 존재함
            subprocess.run(['git', 'push', 'origin', branch], 
                         check=True, capture_output=True)
        except subprocess.CalledProcessError:
            # 첫 푸시
            subprocess.run(['git', 'push', '-u', 'origin', branch], 
                         check=True, capture_output=True)
        
        print("✅ GitHub에 코드 업로드 완료!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ GitHub 푸시 실패: {e}")
        print("💡 GitHub 인증이 필요할 수 있습니다")
        print("   Personal Access Token을 설정했는지 확인하세요")
        return False

def open_streamlit_cloud():
    """Streamlit Cloud 배포 페이지 열기"""
    print("\n🚀 Streamlit Cloud 배포 안내")
    print("이제 다음 단계를 진행하세요:")
    print()
    print("1. 🌐 https://share.streamlit.io 접속")
    print("2. 📝 'New app' 클릭")
    print("3. 📁 GitHub 저장소 연결")
    print("4. 📄 Main file path: streamlit_app.py")
    print("5. ⚙️ 'Advanced settings' → 'Secrets' 탭")
    print("6. 🔑 다음 내용 입력:")
    print('   OPENWEATHER_API_KEY = "your_api_key_here"')
    print("7. 🚀 'Deploy!' 클릭")
    print()
    
    open_browser = input("Streamlit Cloud 사이트를 열까요? (y/n): ").lower()
    if open_browser == 'y':
        webbrowser.open('https://share.streamlit.io')
        print("🌐 브라우저에서 Streamlit Cloud가 열렸습니다!")

def test_local_app():
    """로컬에서 앱 테스트"""
    print("\n🧪 로컬 테스트 실행")
    
    test_now = input("로컬에서 앱을 테스트해보시겠습니까? (y/n): ").lower()
    if test_now != 'y':
        return
    
    try:
        print("🚀 Streamlit 앱 실행 중...")
        print("💡 브라우저에서 http://localhost:8501 이 열립니다")
        print("🛑 종료하려면 Ctrl+C를 누르세요")
        print()
        
        subprocess.run(['streamlit', 'run', 'streamlit_app.py'], check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 앱 실행 실패: {e}")
        print("💡 'pip install streamlit'로 Streamlit을 설치했는지 확인하세요")
    except KeyboardInterrupt:
        print("\n✅ 앱 테스트 완료!")

def show_success_message():
    """성공 메시지 출력"""
    print("\n🎉 배포 준비 완료!")
    print("📱" + "="*58 + "📱")
    print()
    print("✅ 완료된 작업:")
    print("   📄 필수 파일 확인")
    print("   🔑 API 키 설정") 
    print("   📝 Git 커밋")
    print("   📤 GitHub 업로드")
    print()
    print("🚀 다음 단계:")
    print("   1. https://share.streamlit.io 에서 앱 배포")
    print("   2. 배포 완료 후 모바일에서 테스트")
    print("   3. URL 공유하여 다른 사람들과 함께 사용")
    print()
    print("📱 모바일 최적화된 스마트 출퇴근 도우미 완성! 🌤️")

def main():
    """메인 배포 함수"""
    print_header()
    
    # 1. 필수 파일 확인
    if not check_required_files():
        return False
    
    # 2. API 키 설정 확인
    if not check_secrets_file():
        print("⚠️ API 키를 나중에 Streamlit Cloud에서 설정할 수 있습니다")
    
    # 3. Git 상태 확인
    if not check_git_status():
        return False
    
    # 4. 원격 저장소 확인
    if not check_remote_repository():
        return False
    
    # 5. GitHub에 푸시
    if not push_to_github():
        print("⚠️ 수동으로 GitHub에 업로드 후 배포를 진행하세요")
    
    # 6. 로컬 테스트 (선택사항)
    test_local_app()
    
    # 7. Streamlit Cloud 안내
    open_streamlit_cloud()
    
    # 8. 성공 메시지
    show_success_message()
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎯 배포 스크립트가 성공적으로 완료되었습니다!")
        else:
            print("\n❌ 배포 준비 중 오류가 발생했습니다.")
            print("💡 수동으로 GitHub 업로드 및 Streamlit Cloud 배포를 진행하세요.")
    except KeyboardInterrupt:
        print("\n👋 배포 스크립트가 중단되었습니다.")
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        print("💡 수동 배포 가이드를 따라 진행하세요.")