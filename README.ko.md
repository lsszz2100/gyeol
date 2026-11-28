<div align="center">

<img src="docs/images/logo.png" width="88" alt="결 로고">

# 결 GYEOL

**한국어 발표 자료를 만드는 AI 프레젠테이션 프로그램**
주제 한 줄이나 내 파일을 넣으면, 최신 자료를 조사해 디자인된 슬라이드와 발표 대본까지 만들어 줍니다.

[![Version](https://img.shields.io/badge/version-1.4.2-6d4aff?style=flat-square)](https://github.com/lsszz2100/gyeol-releases/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078d4?style=flat-square)](#-시작하기)
[![Python](https://img.shields.io/badge/python-3.12-3776ab?style=flat-square)](#소스로-실행)
[![Themes](https://img.shields.io/badge/themes-216-ff5d8f?style=flat-square)](#-디자인)

[English](README.md) · **한국어**

<img src="docs/images/editor.png" width="900" alt="결 편집 화면: 슬라이드 목록, 슬라이드, 오른쪽 속성 패널">

</div>

---

## ✨ 핵심 기능

| | |
|---|---|
| 🔎 **최신 자료 조사** | 오늘 기준으로 인터넷을 조사한 뒤 슬라이드를 쓰고, 참고 자료 슬라이드를 자동으로 붙입니다. |
| 📎 **내 자료로 만들기** | PDF·Word·파워포인트·한글(HWPX)·엑셀·텍스트·사진을 넣을 수 있습니다. 스캔 문서는 AI가 읽고, **파일 안의 사진도 꺼내 어울리는 슬라이드에 넣습니다.** |
| 📋 **가이드 맞춤 PPT** | 제안요청서나 과제 안내문을 넣으면 요구하는 목차·키워드·문구를 뽑아 그대로 맞춰 쓰고, ✅/⚠️ 점검표로 보여 줍니다. |
| ✍️ **클릭해서 바로 편집** | 글자와 개체를 누르면 바로 고칠 수 있습니다. 오른쪽 속성 패널에서 서체·크기·색·정렬·위치·투명도를 바꾸고, 고친 내용은 자동으로 저장됩니다. |
| 💡 **장표 추천 · AI 검수** | 지금 슬라이드에 어울리는 구성을 추천합니다. 전체 슬라이드에서 글자 넘침·겹침을 찾아 고쳐 줍니다. |
| 🎨 **테마 216종 · 스타일 22종** | 스위스 타이포·에디토리얼 명조·네오 브루탈·글래스·블루프린트·한지 전통 등. 스타일마다 서체·배경·장식이 다릅니다. |
| 🖼 **사진 · 아이콘 · 도형** | 무료 사진 검색, AI 그림, 한글로 찾는 아이콘 200여 개, 도형, 내 사진을 넣을 수 있습니다. |
| 📤 **다양한 내보내기** | 편집 가능한 파워포인트, 원본 그대로 파워포인트, PDF, HTML 한 파일, PNG 묶음, 1080p MP4 동영상, 대본(.md/.txt). |

## 🚀 시작하기

### 설치 (권장)

**[릴리스 페이지](https://github.com/lsszz2100/gyeol-releases/releases/latest)**에서 최신 설치 파일을 받으세요. 새 버전이 나오면 자동으로 업데이트됩니다.

### 소스로 실행

```bash
pip install -r requirements.txt
python -m playwright install chromium   # Edge·Chrome이 없을 때만 (내보내기용)
python app.py                           # 윈도우는 run.bat 더블클릭
```

### AI 연결

⚙️ **설정**에서 하나를 고르세요.

- **Gemini API 키**(권장): 구글 검색 조사, 스캔 문서 읽기, 사진 설명까지 됩니다.
- **OpenAI API 키**
- **구독 로그인**: ChatGPT·Claude·Gemini 공식 CLI로 로그인합니다. API 키가 필요 없습니다.

## 🧭 만드는 과정

```mermaid
flowchart LR
    A[주제 / 내 자료 / 가이드] --> B[조사<br/>인터넷 검색]
    B --> C[작성<br/>구성·도표·대본]
    C --> D[디자인<br/>테마·아이콘·사진]
    D --> E[편집<br/>클릭·속성 패널·AI 고치기]
    E --> F[발표 · 내보내기<br/>PPTX · PDF · HTML · MP4]
```

## 🎨 디자인

<div align="center">
<img src="docs/images/themes.png" width="820" alt="같은 표지를 네 가지 테마로">
<br><sub>같은 표지를 216종 중 네 가지 테마로</sub>
</div>

- 서체는 모두 상업적으로 무료입니다(Google Fonts OFL, 무료 한글 서체). 내보낼 때 서체를 함께 넣습니다.
- 한글 줄바꿈·자간·행간 안전장치가 있어서 글자가 잘리지 않습니다.

## ⌨️ 단축키

| 키 | 기능 |
|---|---|
| `←` `→` `Space` | 이전 / 다음 슬라이드 |
| `S` | 발표자 창 (대본·타이머·다음 슬라이드) |
| `O` | 전체 개요 |
| `F` | 전체화면 |
| `Ctrl` + `Z` | 되돌리기 |
| `Delete` · 화살표 | 고른 개체 삭제 / 조금씩 옮기기 |
| `Esc` | 선택 해제 / 닫기 |

## 🗂 폴더 구성

```text
app.py              로컬 서버와 API
ai_engine.py        조사·프롬프트 구성·생성
desktop.py          데스크톱 창(pywebview)과 트레이
core/               자료 읽기·사진·내보내기·가이드·장표 추천·검수·업데이트
static/             편집 화면·테마·서체·아이콘
packaging/          설치 파일과 배포 스크립트
```

## 🔒 개인정보와 보안

- 모든 작업은 내 PC에서 실행됩니다. 프로젝트와 사진은 내 컴퓨터의 데이터 폴더에만 저장됩니다.
- 로컬 API는 이 프로그램 화면에서 온, 실행할 때마다 바뀌는 토큰이 있는 요청만 받습니다.
- 파일과 인터넷에서 가져온 글은 자료로만 쓰고 지시로 따르지 않습니다. AI가 만든 HTML은 화면에 보이기 전에 안전하게 정리합니다.

## 📄 고지

외부 서체·라이브러리 목록은 [`static/THIRD_PARTY_NOTICES.txt`](static/THIRD_PARTY_NOTICES.txt)에 있습니다.
사용 환경과 연결한 AI 서비스에 따라 일부 기능이 다르게 동작할 수 있습니다.
