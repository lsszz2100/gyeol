"""프로그램 버전·업데이트 배포처 (단일 기준). packaging\\release.bat 이 이 값을 읽어 빌드·배포한다."""
APP_VERSION = "1.4.3"
# 업데이트 파일을 올리는 GitHub 공개 저장소 "소유자/저장소" (소스 코드는 올리지 않음)
UPDATE_REPO = "lsszz2100/gyeol-releases"
# 기반(Python·라이브러리) 번호. requirements.txt 나 launcher.py 를 바꿨을 때만 올리고, 그때는 release_full.bat 으로 배포
REQUIRED_RUNTIME = 2   # 2: 동영상 내보내기 인코더(imageio-ffmpeg) 추가
