# 🧳 여기갈래? 프로젝트 안내 (들어가며)

본 저장소는 **AI 코딩 도구를 활용해 직접 기획·개발·배포한 AI 국내 여행 코스 추천 웹 서비스**를 정리한 공간입니다.
여행 지역, 기간, 동행, 좋아하는 여행 스타일만 고르면 **Google Gemini AI가 시간대별 여행 코스를 1분 안에** 만들어 줍니다. 각 링크를 클릭하면 해당 문서 및 결과물로 바로 이동합니다.

> 🌐 **서비스 바로가기: https://yeogi-galrae.vercel.app**

---

## 📁 프로젝트 구조 및 주요 내용

### 1. 🌐 [배포된 웹 서비스](https://yeogi-galrae.vercel.app)

누구나 접속해서 바로 사용할 수 있는 실제 서비스입니다.

* **홈**: 서비스 한 줄 소개와 예시 코스 카드
* **서비스 소개**: 3단계 사용 방법 (조건 고르기 → AI 코스 설계 → 확인·복사)
* **AI 코스 추천**: 조건 입력 → AI가 일자별 타임라인 코스 + 여행 팁 생성
* **자주 묻는 질문**: 정확도, 해외 지역, 오류 메시지, 개인정보 저장 여부 안내

### 2. 📋 [서비스 기획 문서](docs/)

서비스를 만들기 전 설계와, 만든 뒤의 운영 기준을 정리한 문서입니다.

* [01_서비스_기획서.md](docs/01_서비스_기획서.md): 서비스 목적, 타겟 사용자, 페이지 구성, AI 기능의 입력/출력/실패 처리 기준
* [02_기술_설계_및_API_명세.md](docs/02_기술_설계_및_API_명세.md): HTML/CSS/JS 역할, 프론트→백엔드 호출 흐름, `/api/recommend` 요청·응답 명세
* [03_배포_보안_및_트러블슈팅.md](docs/03_배포_보안_및_트러블슈팅.md): Vercel 배포 과정, 로컬 vs 배포 환경 차이, API 키 보안, 오류 해결 기록

### 3. 💻 소스 코드

프레임워크 없이 순수 HTML/CSS/JavaScript와 Python 서버리스 함수로 만들었습니다.

* [index.html](index.html): 화면 뼈대 (메뉴 + 4개 섹션 + 입력 폼)
* [css/style.css](css/style.css): 디자인, 반응형(데스크톱/태블릿/모바일), 다크 모드
* [js/main.js](js/main.js): 메뉴 이동, 다크 모드, 입력 검사, `fetch('/api/recommend')` 호출, 결과 표시
* [api/recommend.py](api/recommend.py): 백엔드 — 입력 검증 → Gemini API 호출 → JSON 응답

### 4. 📸 [증빙 자료](docs/screenshots/)

* 서비스 스크린샷 (데스크톱 / 모바일 / AI 기능 동작 / 다크 모드)
* AI 코딩 도구(Claude) 사용 과정 캡처

---

## ✨ 주요 기능

| 구분 | 내용 |
|---|---|
| 🤖 AI 기능 | 조건 입력 → 일자별 타임라인 코스 + 여행 팁 표시, 코스 텍스트 복사 |
| 🛡️ 실패 처리 | 빈 입력 안내 · API 오류(4xx/5xx) 안내 · 8초 지연 안내 · 30초 타임아웃 · 다시 시도 버튼 |
| 📱 반응형 | 데스크톱 / 태블릿(≤900px) / 모바일(≤680px, 햄버거 메뉴) |
| 🌙 보너스 | 다크 모드 (시스템 설정 자동 반영 + 버튼 전환, 선택값 기억) |

## 🛠️ 기술 스택

| 영역 | 사용 기술 |
|---|---|
| 프론트엔드 | HTML, CSS, JavaScript (바닐라, 프레임워크 없음) |
| 백엔드 | Vercel Serverless Functions (Python) |
| AI | Google Gemini API |
| 배포 | GitHub + Vercel (push 시 자동 재배포) |

## 🔄 동작 흐름

```
[사용자 입력] → js/main.js 필수값 검사
  → fetch('/api/recommend', POST)
  → api/recommend.py 입력 재검증 → Gemini API 호출
  → 응답 구조 검증 (형식 오류 시 1회 재시도, 할당량 초과 시 다른 모델로 자동 전환)
  → JSON 응답 → 화면에 타임라인으로 표시
```

## 🔑 환경 변수 설정

| 이름 | 필수 | 설명 |
|---|---|---|
| `GEMINI_API_KEY` | ✔ | Google AI Studio(https://aistudio.google.com/apikey)에서 발급한 키 |
| `GEMINI_MODELS` | | 사용할 모델 순서(쉼표 구분). 비워두면 기본 순서 사용 |

**Vercel 설정 방법:** 프로젝트 → **Settings → Environment Variables** → 이름 `GEMINI_API_KEY`, 값에 키 입력 → Save → **Deployments → Redeploy**

> ⚠️ API 키는 코드·README·스크린샷 어디에도 넣지 않습니다. `.env` 파일은 `.gitignore`에 등록되어 GitHub에 올라가지 않습니다.

## 🚀 실행 및 배포 방법

**배포 (Vercel)**
1. 이 저장소를 GitHub에 push
2. [vercel.com](https://vercel.com)에 GitHub 계정으로 로그인 → **Add New → Project** → 저장소 **Import**
3. Environment Variables에 `GEMINI_API_KEY` 추가 → **Deploy**
4. 발급된 `https://...vercel.app` 주소로 접속해 확인 (이후 `git push`하면 자동 재배포)

**로컬 실행 (선택, Node.js 필요)**
```bash
npm i -g vercel
cp .env.example .env   # .env 안에 본인 키 입력
vercel dev             # http://localhost:3000
```

> `index.html`을 파일로 직접 열면 화면은 보이지만, AI 기능은 서버(`/api`)가 필요해서 동작하지 않습니다.

## 📂 폴더 구조

```
yeogi-galrae/
├── index.html
├── css/style.css
├── js/main.js
├── api/recommend.py
├── images/favicon.svg
├── docs/
│   ├── 01_서비스_기획서.md
│   ├── 02_기술_설계_및_API_명세.md
│   ├── 03_배포_보안_및_트러블슈팅.md
│   └── screenshots/
├── requirements.txt
├── vercel.json
├── .env.example
└── .gitignore
```
