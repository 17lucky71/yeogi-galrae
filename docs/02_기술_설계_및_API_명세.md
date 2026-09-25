# 02. 기술 설계 및 API 명세

## 1. HTML / CSS / JavaScript 역할 분담

| 파일 | 역할 | 비유 |
|---|---|---|
| `index.html` | 화면의 **뼈대**: 메뉴, 4개 섹션, 입력 폼, 결과 영역 | 집의 골조 |
| `css/style.css` | 화면의 **디자인**: 색상, 배치, 반응형(모바일/태블릿), 다크 모드 | 인테리어 |
| `js/main.js` | 화면의 **동작**: 메뉴 열고 닫기, 입력 검사, 서버 호출(fetch), 결과 그리기 | 전기·수도 |
| `api/recommend.py` | **백엔드**: 입력 재검증, AI API 호출, 결과 정리 후 응답 | 주방(손님은 못 들어감) |

## 2. 전체 동작 흐름

```
① 사용자가 폼에 조건 입력 후 버튼 클릭
② main.js: 필수값 검사 (비어 있으면 여기서 멈추고 안내)
③ main.js: fetch('/api/recommend', { method: 'POST', body: JSON })
④ Vercel: /api/recommend 요청을 api/recommend.py 의 handler 로 전달
⑤ recommend.py: 입력 재검증 → Gemini API 호출(POST) → 응답 JSON 구조 검증
⑥ recommend.py: {"ok": true, "requestId": "...", "course": {...}} 또는 {"ok": false, "requestId": "...", "error": "..."} 반환
⑦ main.js: 성공이면 타임라인으로 그리고, 실패면 오류 안내 + 다시 시도 버튼 표시
```

## 3. Vercel Serverless Functions 란?

- 서버 컴퓨터를 24시간 켜두지 않고, **요청이 올 때만 잠깐 실행되는 함수**입니다.
- `api/` 폴더에 파이썬 파일을 넣으면 Vercel이 자동으로 `/api/파일이름` 주소를 만들어 줍니다.
  - `api/recommend.py` → `https://배포주소/api/recommend`
- 프론트(브라우저)는 같은 도메인의 `/api/recommend`만 부르면 되므로 주소 설정이나 CORS 문제가 없습니다.
- 필요한 파이썬 패키지는 `requirements.txt`에 적으면 Vercel이 배포할 때 설치합니다.

## 4. 왜 브라우저에서 AI API를 직접 부르지 않나요?

브라우저 코드(`main.js`)는 누구나 개발자 도구로 볼 수 있습니다. 여기에 API 키를 넣으면 키가 그대로 노출됩니다.
그래서 **키는 서버(Vercel 환경 변수)에만 두고**, 브라우저는 우리 서버에만 요청하는 구조로 만들었습니다.

## 5. API 명세 — `POST /api/recommend`

### 요청

```json
{
  "region": "강릉",
  "duration": "1박 2일",
  "companion": "친구",
  "styles": ["맛집", "자연"],
  "request": "바다가 보이는 카페는 꼭 넣어주세요"
}
```

| 필드 | 타입 | 필수 | 규칙 |
|---|---|---|---|
| region | string | ✔ | 1~30자 |
| duration | string | ✔ | `당일치기` / `1박 2일` / `2박 3일` |
| companion | string | ✔ | `혼자` / `친구` / `연인` / `가족` |
| styles | string[] | | 허용 목록 중 최대 5개 |
| request | string | | 200자 이내 |

### 응답

성공 (200):
```json
{
  "ok": true,
  "requestId": "a1b2c3d4",
  "cached": false,
  "course": {
    "title": "강릉 바다 따라 1박 2일",
    "summary": "친구와 함께 바다와 맛집을 즐기는 코스",
    "days": [
      { "day": 1, "theme": "바다와 카페",
        "items": [ { "time": "10:00", "place": "안목해변 카페거리", "description": "바다를 보며 커피 한 잔" } ] }
    ],
    "tips": ["KTX 강릉역에서 버스로 이동하기 편해요"]
  }
}
```

실패:
```json
{ "ok": false, "requestId": "f6b7fb69", "error": "여행 지역을 입력해주세요." }
```

- `requestId`: 요청마다 붙는 8자리 ID. 오류 안내 문구 끝에 "(요청 ID: …)"로 표시되고, Vercel 로그에도 같은 ID로 남아서 문제를 바로 찾을 수 있습니다.
- `cached`: 같은 조건의 최근 결과를 재사용했으면 `true` (응답 지연 개선, [05번 문서](05_성능_확장_및_운영_계획.md) 참고).

| 상태 코드 | 의미 |
|---|---|
| 400 | 필수값 누락 / 형식 오류 / 길이 초과 |
| 405 | GET 등 POST가 아닌 요청 |
| 429 | AI 사용량(쿼터) 초과 — 모든 모델이 초과일 때 |
| 500 | 서버 설정 오류 (API 키 없음, 인증 실패) |
| 502 | AI 서버 오류 / AI 응답 형식 오류 |
| 504 | AI 응답 지연 (모델당 20초 초과) |

### 응답 JSON Schema (v1)

화면(`main.js`)과 서버(`validate_course()`)가 같은 규칙을 따르도록 응답 구조를 정의했습니다. 구조를 바꿀 때는 버전을 올리고 이 표를 먼저 수정합니다.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RecommendResponse v1",
  "type": "object",
  "required": ["ok", "requestId"],
  "properties": {
    "ok": { "type": "boolean" },
    "requestId": { "type": "string" },
    "cached": { "type": "boolean" },
    "error": { "type": "string" },
    "course": {
      "type": "object",
      "required": ["title", "summary", "days"],
      "properties": {
        "title": { "type": "string" },
        "summary": { "type": "string" },
        "days": {
          "type": "array", "minItems": 1,
          "items": {
            "type": "object", "required": ["items"],
            "properties": {
              "day": { "type": "integer" },
              "theme": { "type": "string" },
              "items": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "time": { "type": "string" },
                    "place": { "type": "string" },
                    "description": { "type": "string" }
                  }
                }
              }
            }
          }
        },
        "tips": { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

## 6. AI 응답 품질을 지키는 장치

1. **JSON 응답 강제**: Gemini 호출 시 `responseMimeType: "application/json"`을 지정해 화면에 바로 그릴 수 있는 구조로 받습니다.
2. **구조 검증**: `title`, `summary`, `days[].items` 등이 올바른 타입인지 `validate_course()`에서 검사합니다.
3. **1회 재시도**: 형식이 깨지면 더 짧고 엄격한 프롬프트로 딱 한 번만 다시 요청합니다(무한 재시도 방지).
4. **모델 자동 전환**: 무료 할당량은 모델별로 따로 계산되므로, 429가 나면 `GEMINI_MODELS` 목록의 다음 모델로 넘어갑니다.
5. **결과 캐시**: 같은 조건 요청은 1시간 동안 최근 결과를 재사용해 AI를 다시 부르지 않습니다.
6. **안전한 출력**: AI가 준 텍스트는 `textContent`로만 화면에 넣어, 혹시 HTML/스크립트가 섞여 와도 실행되지 않습니다.

## 7. 반응형 기준

| 화면 폭 | 레이아웃 |
|---|---|
| 900px 초과 (데스크톱) | 히어로 2단, 폼/결과 좌우 2단, 소개 카드 3열 |
| 900px 이하 (태블릿) | 히어로·폼/결과를 위아래 1단으로 |
| 680px 이하 (모바일) | 햄버거 메뉴, 소개 카드 1열, 입력칸 1열 |
