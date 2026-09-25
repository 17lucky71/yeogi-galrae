"""
여기갈래? - AI 여행 코스 추천 API (Vercel Serverless Function, Python)

엔드포인트: POST /api/recommend
요청(JSON):
  {
    "region": "강릉",                 # 필수, 여행 지역
    "duration": "1박 2일",            # 필수, 당일치기 / 1박 2일 / 2박 3일
    "companion": "친구",              # 필수, 혼자 / 친구 / 연인 / 가족
    "styles": ["맛집", "자연"],        # 선택, 여행 스타일 (최대 5개)
    "request": "바다가 보이는 카페"     # 선택, 추가 요청 (최대 200자)
  }

응답(JSON, 성공 200):
  {
    "ok": true,
    "course": {
      "title": str, "summary": str,
      "days": [{"day": int, "theme": str,
                "items": [{"time": str, "place": str, "description": str}]}],
      "tips": [str]
    }
  }

응답(JSON, 실패):
  {"ok": false, "error": "사용자에게 보여줄 안내 문구"}
  - 400: 필수값 누락/형식 오류
  - 429: AI API 사용량(쿼터) 초과
  - 500: 서버 설정 오류(API 키 없음)
  - 502: AI 응답 오류 또는 형식이 잘못된 응답
  - 504: AI 응답 지연(타임아웃)

API 키는 코드에 넣지 않고, Vercel 환경 변수 GEMINI_API_KEY 에서만 읽는다.
"""

import json
import os
from http.server import BaseHTTPRequestHandler

import requests

# 무료 요금제 할당량은 "프로젝트 + 모델" 단위로 따로 계산된다.
# 그래서 앞 모델이 할당량 초과(429)면 다음 모델로 자동 전환한다. (환경 변수로 순서 변경 가능)
DEFAULT_MODELS = "gemini-3.8-flash,gemini-3.7-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite"
GEMINI_MODELS = [m.strip() for m in os.environ.get("GEMINI_MODELS", DEFAULT_MODELS).split(",") if m.strip()]
GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_TIMEOUT_SECONDS = 20

ALLOWED_DURATIONS = ["당일치기", "1박 2일", "2박 3일"]
ALLOWED_COMPANIONS = ["혼자", "친구", "연인", "가족"]
ALLOWED_STYLES = ["맛집", "자연", "역사·문화", "카페", "액티비티", "쇼핑"]
MAX_REGION_LENGTH = 30
MAX_REQUEST_LENGTH = 200


class ApiError(Exception):
    """사용자에게 보여줄 메시지와 HTTP 상태 코드를 함께 담는 예외."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def validate_input(data):
    """요청 본문을 검증하고 정리된 값을 돌려준다. 문제가 있으면 400 ApiError."""
    if not isinstance(data, dict):
        raise ApiError(400, "요청 형식이 올바르지 않습니다.")

    region = str(data.get("region", "")).strip()
    duration = str(data.get("duration", "")).strip()
    companion = str(data.get("companion", "")).strip()
    styles = data.get("styles") or []
    extra = str(data.get("request", "")).strip()

    if not region:
        raise ApiError(400, "여행 지역을 입력해주세요.")
    if len(region) > MAX_REGION_LENGTH:
        raise ApiError(400, f"여행 지역은 {MAX_REGION_LENGTH}자 이내로 입력해주세요.")
    if duration not in ALLOWED_DURATIONS:
        raise ApiError(400, "여행 기간을 선택해주세요.")
    if companion not in ALLOWED_COMPANIONS:
        raise ApiError(400, "누구와 가는지 선택해주세요.")
    if not isinstance(styles, list):
        raise ApiError(400, "여행 스타일 형식이 올바르지 않습니다.")
    styles = [s for s in styles if s in ALLOWED_STYLES][:5]
    if len(extra) > MAX_REQUEST_LENGTH:
        raise ApiError(400, f"추가 요청은 {MAX_REQUEST_LENGTH}자 이내로 입력해주세요.")

    return {
        "region": region,
        "duration": duration,
        "companion": companion,
        "styles": styles,
        "request": extra,
    }


def build_prompt(params, strict=False):
    """Gemini에게 보낼 프롬프트를 만든다. strict=True면 재시도용 더 엄격한 버전."""
    styles_text = ", ".join(params["styles"]) if params["styles"] else "특별히 없음"
    extra_text = params["request"] or "없음"

    schema = (
        '{"title": "코스 제목", "summary": "코스 한 줄 소개", '
        '"days": [{"day": 1, "theme": "그날의 테마", '
        '"items": [{"time": "09:00", "place": "장소 이름", "description": "한두 문장 설명"}]}], '
        '"tips": ["여행 팁"]}'
    )

    if strict:
        return (
            f"지역: {params['region']}, 기간: {params['duration']}, 동행: {params['companion']}, "
            f"스타일: {styles_text}, 추가 요청: {extra_text}\n"
            f"아래 구조의 JSON 하나만 출력하세요. 코드블록, 설명 문장은 절대 넣지 마세요.\n{schema}"
        )

    return f"""당신은 대한민국 국내 여행 코스를 짜주는 여행 플래너입니다.
아래 조건에 맞는 여행 코스를 추천해주세요.

- 여행 지역: {params['region']}
- 여행 기간: {params['duration']}
- 동행: {params['companion']}
- 선호 스타일: {styles_text}
- 추가 요청: {extra_text}

규칙:
1. 실제로 존재할 법한 대표 장소 위주로, 하루에 4~6개 일정을 시간 순서대로 짜주세요.
2. 기간이 당일치기면 days는 1개, 1박 2일이면 2개, 2박 3일이면 3개입니다.
3. 동행과 스타일을 반영해서 description에 추천 이유를 짧게 넣어주세요.
4. tips에는 교통, 준비물, 주의사항 같은 실용 팁을 2~4개 넣어주세요.
5. 입력된 지역이 대한민국 여행지가 아니면, 가장 비슷한 국내 여행지로 대신 추천하고 summary에 그 사실을 알려주세요.

다음 JSON 형식으로만 답하세요:
{schema}
"""


def validate_course(course):
    """AI 응답이 화면에 그릴 수 있는 구조인지 검사한다. 문제가 있으면 ValueError."""
    if not isinstance(course, dict):
        raise ValueError("응답이 객체가 아닙니다.")
    if not isinstance(course.get("title"), str) or not isinstance(course.get("summary"), str):
        raise ValueError("title/summary가 문자열이 아닙니다.")
    days = course.get("days")
    if not isinstance(days, list) or not days:
        raise ValueError("days가 비어 있거나 배열이 아닙니다.")
    for day in days:
        if not isinstance(day, dict) or not isinstance(day.get("items"), list):
            raise ValueError("days 항목 형식이 잘못되었습니다.")
    if not isinstance(course.get("tips", []), list):
        raise ValueError("tips가 배열이 아닙니다.")
    course.setdefault("tips", [])
    return course


def call_gemini_once(model, prompt, api_key):
    """모델 하나에 Gemini REST API를 POST로 호출하고, 모델이 돌려준 텍스트를 반환한다."""
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.8},
    }
    try:
        response = requests.post(
            GEMINI_URL_TEMPLATE.format(model=model),
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json=body,
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        raise ApiError(504, "AI 응답이 너무 오래 걸리고 있어요. 잠시 후 다시 시도해주세요.")
    except requests.exceptions.RequestException:
        raise ApiError(502, "AI 서버에 연결하지 못했어요. 잠시 후 다시 시도해주세요.")

    if response.status_code == 429:
        raise ApiError(429, "오늘 AI 사용량이 많아 잠시 쉬어가요. 잠시 후 다시 시도해주세요.")
    if response.status_code in (401, 403):
        raise ApiError(500, "서버의 AI 인증 설정에 문제가 있어요. 관리자에게 알려주세요.")
    if response.status_code == 404:
        raise ApiError(502, "사용할 수 없는 AI 모델이에요.")
    if response.status_code >= 400:
        raise ApiError(502, f"AI 서버 오류가 발생했어요. (코드 {response.status_code})")

    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise ApiError(502, "AI가 답변을 만들지 못했어요. 입력을 바꿔서 다시 시도해주세요.")


def call_gemini(prompt, api_key):
    """GEMINI_MODELS 순서대로 시도한다.
    할당량 초과(429)나 모델 없음/서버 오류(502)면 다음 모델로 넘어가고,
    인증 오류(500)나 타임아웃(504)은 다른 모델로 바꿔도 소용없으므로 바로 실패시킨다."""
    last_error = ApiError(502, "사용 가능한 AI 모델이 없어요.")
    for model in GEMINI_MODELS:
        try:
            return call_gemini_once(model, prompt, api_key)
        except ApiError as e:
            if e.status in (429, 502):
                last_error = e
                continue
            raise
    raise last_error


def recommend_course(params, api_key):
    """코스를 추천받는다. JSON 형식이 깨지면 더 엄격한 프롬프트로 1회만 재시도한다."""
    for strict in (False, True):
        text = call_gemini(build_prompt(params, strict=strict), api_key)
        try:
            return validate_course(json.loads(text))
        except (json.JSONDecodeError, ValueError):
            continue
    raise ApiError(502, "AI 응답 형식이 올바르지 않아요. 다시 시도해주세요.")


class handler(BaseHTTPRequestHandler):
    """Vercel이 /api/recommend 요청을 이 클래스로 전달한다."""

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send_json(405, {"ok": False, "error": "POST 방식으로 요청해주세요."})

    def do_POST(self):
        try:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ApiError(500, "서버에 AI API 키가 설정되지 않았어요. 관리자에게 알려주세요.")

            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > 10_000:
                raise ApiError(400, "요청 내용이 비어 있거나 너무 깁니다.")
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                raise ApiError(400, "요청 형식이 올바르지 않습니다.")

            params = validate_input(data)
            course = recommend_course(params, api_key)
            self._send_json(200, {"ok": True, "course": course})
        except ApiError as e:
            self._send_json(e.status, {"ok": False, "error": e.message})
        except Exception:
            # 예상 못한 오류도 사용자에게는 친절한 문구로만 안내한다(내부 정보 노출 방지).
            self._send_json(500, {"ok": False, "error": "알 수 없는 오류가 발생했어요. 잠시 후 다시 시도해주세요."})
