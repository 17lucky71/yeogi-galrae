/* =========================================
   여기갈래? - 화면 동작 스크립트
   1) 메뉴 이동/햄버거  2) 다크 모드  3) AI 코스 추천(fetch)
   ========================================= */

const REQUEST_TIMEOUT_MS = 30000; // 30초가 지나면 요청을 취소한다.
const SLOW_NOTICE_MS = 8000;      // 8초가 넘으면 "조금 오래 걸려요" 안내로 바꾼다.

/* ---------- 1) 메뉴 ---------- */
const nav = document.getElementById("nav");
const menuToggle = document.getElementById("menuToggle");

menuToggle.addEventListener("click", () => {
  const isOpen = nav.classList.toggle("open");
  menuToggle.setAttribute("aria-expanded", String(isOpen));
  menuToggle.setAttribute("aria-label", isOpen ? "메뉴 닫기" : "메뉴 열기");
});

// 모바일에서 메뉴 항목을 누르면 메뉴를 닫는다.
nav.querySelectorAll(".nav-link").forEach((link) => {
  link.addEventListener("click", () => {
    nav.classList.remove("open");
    menuToggle.setAttribute("aria-expanded", "false");
  });
});

// 스크롤 위치에 맞춰 현재 섹션 메뉴를 강조한다.
const sections = document.querySelectorAll("main section[id]");
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      document.querySelectorAll(".nav-link").forEach((link) => {
        link.classList.toggle("active", link.getAttribute("href") === `#${entry.target.id}`);
      });
    });
  },
  { rootMargin: "-45% 0px -50% 0px" }
);
sections.forEach((section) => observer.observe(section));

/* ---------- 2) 다크 모드 (보너스) ---------- */
document.getElementById("themeToggle").addEventListener("click", () => {
  const root = document.documentElement;
  const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
  if (next === "dark") root.setAttribute("data-theme", "dark");
  else root.removeAttribute("data-theme");
  try { localStorage.setItem("theme", next); } catch (e) { /* 저장이 막힌 브라우저면 무시 */ }
});

/* ---------- 3) AI 코스 추천 ---------- */
const form = document.getElementById("plannerForm");
const submitBtn = document.getElementById("submitBtn");
const formMessage = document.getElementById("formMessage");
const requestInput = document.getElementById("request");
const requestCounter = document.getElementById("requestCounter");

const views = {
  empty: document.getElementById("resultEmpty"),
  loading: document.getElementById("resultLoading"),
  error: document.getElementById("resultError"),
  content: document.getElementById("resultContent"),
};
const loadingText = document.getElementById("loadingText");
const errorText = document.getElementById("errorText");

let lastPayload = null;

requestInput.addEventListener("input", () => {
  requestCounter.textContent = `${requestInput.value.length} / 200`;
});

function showView(name) {
  Object.entries(views).forEach(([key, el]) => { el.hidden = key !== name; });
}

// 입력값을 읽어서 서버로 보낼 형태(payload)로 만든다.
function readForm() {
  return {
    region: form.region.value.trim(),
    duration: form.duration.value,
    companion: form.companion.value,
    styles: [...form.querySelectorAll('input[name="styles"]:checked')].map((el) => el.value),
    request: requestInput.value.trim(),
  };
}

// [실패 처리 1] 빈 입력(필수값 누락) 검사
function validate(payload) {
  const missing = [];
  [["region", "여행 지역"], ["duration", "여행 기간"], ["companion", "누구와"]].forEach(([key, label]) => {
    const empty = !payload[key];
    form[key].classList.toggle("is-invalid", empty);
    if (empty) missing.push({ key, label });
  });
  if (missing.length) {
    formMessage.textContent = `필수값을 입력해주세요: ${missing.map((m) => m.label).join(", ")}`;
    form[missing[0].key].focus();
    return false;
  }
  formMessage.textContent = "";
  return true;
}

// 필수값을 채우면 빨간 테두리를 바로 없앤다.
["region", "duration", "companion"].forEach((key) => {
  const clear = () => {
    form[key].classList.remove("is-invalid");
    if (!form.querySelector(".is-invalid")) formMessage.textContent = "";
  };
  form[key].addEventListener("input", clear);
  form[key].addEventListener("change", clear);
});

// [실패 처리 2, 3] API 오류(4xx/5xx), 지연/타임아웃을 구분해서 안내 문구로 바꾼다.
function messageForStatus(status, serverMessage) {
  if (serverMessage) return serverMessage;
  if (status === 400) return "입력값을 다시 확인해주세요.";
  if (status === 429) return "요청이 많아요. 1~2분 뒤에 다시 시도해주세요.";
  if (status === 504) return "AI 응답이 너무 늦어요. 잠시 후 다시 시도해주세요.";
  if (status >= 500) return "서버에 문제가 생겼어요. 잠시 후 다시 시도해주세요.";
  return `요청을 처리하지 못했어요. (오류 코드 ${status})`;
}

async function requestCourse(payload) {
  lastPayload = payload;
  submitBtn.disabled = true;
  submitBtn.classList.add("loading");
  loadingText.textContent = "AI가 코스를 짜고 있어요...";
  showView("loading");

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const slowId = setTimeout(() => {
    loadingText.textContent = "생각보다 오래 걸리고 있어요. 조금만 더 기다려주세요...";
  }, SLOW_NOTICE_MS);

  try {
    const res = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    let data = null;
    try { data = await res.json(); } catch (e) { /* JSON이 아닌 응답(예: 배포 오류 페이지) */ }

    if (!res.ok || !data || !data.ok) {
      throw new Error(messageForStatus(res.status, data && data.error));
    }
    renderCourse(data.course, payload);
    showView("content");
  } catch (err) {
    errorText.textContent =
      err.name === "AbortError"
        ? "응답 시간이 30초를 넘었어요. 네트워크 상태를 확인하고 다시 시도해주세요."
        : err.message || "알 수 없는 오류가 발생했어요.";
    showView("error");
  } finally {
    clearTimeout(timeoutId);
    clearTimeout(slowId);
    submitBtn.disabled = false;
    submitBtn.classList.remove("loading");
  }
}

// 결과 그리기: AI가 준 텍스트는 innerHTML이 아니라 textContent로 넣어서
// 혹시 HTML/스크립트가 섞여 와도 실행되지 않게 한다.
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderCourse(course, payload) {
  const box = views.content;
  box.replaceChildren();

  const head = el("div", "course-head");
  const titleWrap = el("div");
  titleWrap.append(el("h3", "course-title", course.title || `${payload.region} 여행 코스`));
  const copyBtn = el("button", "btn btn-ghost", "📋 코스 복사");
  copyBtn.type = "button";
  copyBtn.addEventListener("click", () => copyCourse(course, copyBtn));
  head.append(titleWrap, copyBtn);
  box.append(head, el("p", "course-summary", course.summary || ""));

  (course.days || []).forEach((day, i) => {
    const block = el("div", "day-block");
    block.style.animationDelay = `${i * 0.08}s`;
    const title = el("h4", "day-title");
    title.append(el("span", "day-badge", `DAY ${day.day || i + 1}`), document.createTextNode(day.theme || ""));
    const list = el("ol", "timeline");
    (day.items || []).forEach((item) => {
      const li = el("li");
      const line = el("div");
      line.append(el("span", "tl-time", item.time || ""), el("span", "tl-place", item.place || ""));
      li.append(line, el("p", "tl-desc", item.description || ""));
      list.append(li);
    });
    block.append(title, list);
    box.append(block);
  });

  if (course.tips && course.tips.length) {
    const tips = el("div", "tips");
    tips.append(el("h4", null, "💡 여행 팁"));
    const ul = el("ul");
    course.tips.forEach((tip) => ul.append(el("li", null, tip)));
    tips.append(ul);
    box.append(tips);
  }
}

function copyCourse(course, button) {
  const lines = [course.title, course.summary, ""];
  (course.days || []).forEach((day, i) => {
    lines.push(`[DAY ${day.day || i + 1}] ${day.theme || ""}`);
    (day.items || []).forEach((it) => lines.push(`- ${it.time} ${it.place}: ${it.description}`));
    lines.push("");
  });
  if (course.tips && course.tips.length) lines.push("팁: " + course.tips.join(" / "));

  navigator.clipboard.writeText(lines.join("\n")).then(
    () => { button.textContent = "✅ 복사됨"; setTimeout(() => (button.textContent = "📋 코스 복사"), 1500); },
    () => { button.textContent = "복사 실패"; }
  );
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const payload = readForm();
  if (!validate(payload)) return;
  requestCourse(payload);
});

document.getElementById("retryBtn").addEventListener("click", () => {
  if (lastPayload) requestCourse(lastPayload);
});
