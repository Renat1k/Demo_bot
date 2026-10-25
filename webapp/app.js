(() => {
  "use strict";

  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  const content = document.getElementById("content");
  const bottomNav = document.getElementById("bottom-nav");
  const adminNav = document.getElementById("admin-nav");
  const loadingOverlay = document.getElementById("loading-overlay");
  const toastElement = document.getElementById("toast");
  const salonName = document.getElementById("salon-name");
  const salonSub = document.getElementById("salon-sub");

  const state = {
    config: null,
    view: "home",
    records: [],
    booking: null,
    admin: {
      tab: "requests",
      status: "pending",
      page: 1,
      pages: 1,
      items: [],
      day: localDate(),
      dayItems: [],
    },
    holdTimer: null,
    busy: 0,
    toastTimer: null,
  };

  class ApiError extends Error {
    constructor(message, status, code) {
      super(message);
      this.status = status;
      this.code = code;
    }
  }

  function esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function localDate() {
    const now = new Date();
    const offset = now.getTimezoneOffset();
    return new Date(now.getTime() - offset * 60000).toISOString().slice(0, 10);
  }

  function applyTheme() {
    const params = (tg && tg.themeParams) || {};
    const dark = (tg && tg.colorScheme === "dark") ||
      window.matchMedia?.("(prefers-color-scheme: dark)").matches;
    document.body.classList.toggle("theme-dark", Boolean(dark));
    const root = document.documentElement;
    const map = {
      bg_color: "--bg",
      secondary_bg_color: "--surface",
      text_color: "--text",
      hint_color: "--muted",
      button_color: "--accent",
      button_text_color: "--accent-contrast",
      link_color: "--accent-strong",
      destructive_text_color: "--danger",
    };
    Object.entries(map).forEach(([key, cssVar]) => {
      if (params[key]) root.style.setProperty(cssVar, params[key]);
    });
  }

  function haptic(type = "light") {
    try {
      if (["success", "error", "warning"].includes(type)) {
        tg?.HapticFeedback?.notificationOccurred(type);
      } else {
        tg?.HapticFeedback?.impactOccurred(type);
      }
    } catch (_) {
      /* Telegram haptics are optional. */
    }
  }

  function toast(message, isError = false) {
    if (!toastElement) return;
    window.clearTimeout(state.toastTimer);
    toastElement.textContent = message;
    toastElement.hidden = false;
    toastElement.style.background = isError ? "var(--danger)" : "var(--text)";
    state.toastTimer = window.setTimeout(() => {
      toastElement.hidden = true;
    }, 3200);
  }

  function setBusy(delta) {
    state.busy = Math.max(0, state.busy + delta);
    loadingOverlay.hidden = state.busy === 0;
  }

  async function api(path, options = {}) {
    if (!tg || !tg.initData) {
      throw new ApiError("Відкрийте застосунок через Telegram.", 401, "unauthorized");
    }
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    const headers = {
      Accept: "application/json",
      "X-Telegram-Init-Data": tg.initData,
    };
    if (options.body) headers["Content-Type"] = "application/json";
    if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;
    try {
      const response = await fetch(path, {
        method: options.method || "GET",
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
        signal: controller.signal,
      });
      let payload = null;
      try {
        payload = await response.json();
      } catch (_) {
        payload = null;
      }
      if (!response.ok || !payload || payload.ok === false) {
        const error = payload && payload.error ? payload.error : {};
        throw new ApiError(
          error.message || "Не вдалося виконати запит.",
          response.status,
          error.code || "request_failed",
        );
      }
      return payload.data;
    } catch (error) {
      if (error.name === "AbortError") {
        throw new ApiError("Сервер не відповів. Спробуйте ще раз.", 0, "timeout");
      }
      throw error;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function statusClass(status) {
    return `status status-${esc(status)}`;
  }

  function statusBadge(item) {
    return `<span class="${statusClass(item.status)}">${esc(item.status_label || item.status)}</span>`;
  }

  function renderAuth(message = "Відкрийте Mini App через Telegram, щоб побачити свої записи.") {
    bottomNav.hidden = true;
    content.innerHTML = `
      <div class="hero">
        <div class="hero-kicker">DEMO · салон краси</div>
        <h1>Запис у кілька дотиків</h1>
        <p>${esc(message)}</p>
      </div>
      <div class="empty-state">
        <div class="empty-icon" aria-hidden="true">✈</div>
        <h3>Потрібен Telegram</h3>
        <p>Застосунок перевіряє підпис Telegram initData. Звичайний браузер не має доступу до записів.</p>
        <button class="btn btn-primary" type="button" data-action="retry">Спробувати знову</button>
      </div>`;
  }

  function renderError(message, code = "error") {
    content.innerHTML = `
      <div class="banner">
        <strong>Щось пішло не так</strong>
        <span>${esc(message)}</span>
      </div>
      <div class="empty-state">
        <div class="empty-icon" aria-hidden="true">↻</div>
        <h3>Не вдалося завантажити</h3>
        <p>Перевірте з'єднання та спробуйте ще раз.</p>
        <button class="btn btn-primary" type="button" data-action="retry">Оновити</button>
      </div>`;
    bottomNav.hidden = !state.config;
    setActiveNav();
    console.warn("Mini App API error", code);
  }

  function setActiveNav() {
    document.querySelectorAll(".nav-item").forEach((button) => {
      button.classList.toggle(
        "is-active",
        button.dataset.view === state.view,
      );
    });
  }

  function setSalonHeader() {
    if (!state.config) return;
    salonName.textContent = state.config.salon.name;
    salonSub.textContent = `салон краси · ${state.config.salon.city || "Київ"}`;
  }

  function navigate(view) {
    if (view === "admin" && !state.config?.is_admin) return;
    state.view = view;
    if (view === "booking" && state.booking?.step === "success") {
      state.booking = null;
    }
    if (view === "admin") {
      renderAdmin();
      if (state.admin.tab === "day") loadAdminDay();
      else loadAdminRequests();
      return;
    }
    render();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function serviceCard(service, action = "start-service") {
    return `
      <article class="service-card">
        <div class="row">
          <h3>${esc(service.name)}</h3>
          <span class="pill pill-accent">${esc(service.duration_minutes)} хв</span>
        </div>
        <p class="service-description">${esc(service.description)}</p>
        <div class="service-footer">
          <span class="price">${esc(service.price)}</span>
          <button class="btn btn-primary btn-small" type="button" data-action="${action}" data-id="${esc(service.id)}">Обрати</button>
        </div>
      </article>`;
  }

  function renderHome() {
    const records = state.records.filter((item) =>
      ["pending", "confirmed"].includes(item.status),
    );
    records.sort((a, b) => `${a.date_id} ${a.time_id}`.localeCompare(`${b.date_id} ${b.time_id}`));
    const next = records[0];
    const nextCard = next
      ? `
        <div class="card stack">
          <div class="row">
            <div>
              <div class="muted small">Наступний запис</div>
              <div class="record-title">${esc(next.service_name)}</div>
              <div class="record-meta">${esc(next.date_label)} · ${esc(next.time_label)} · ${esc(next.duration_minutes)} хв</div>
            </div>
            ${statusBadge(next)}
          </div>
          <button class="btn btn-ghost btn-small" type="button" data-action="navigate" data-view="records">Деталі</button>
        </div>`
      : "";
    content.innerHTML = `
      <section class="hero">
        <div class="hero-kicker">${esc(state.config.salon.name)} · Київ</div>
        <h1>Краса починається з турботи про себе.</h1>
        <p>Онлайн-запис із живими вільними слотами, тривалістю послуг і підтвердженням майстра.</p>
        <div class="hero-actions">
          <button class="btn btn-primary" type="button" data-action="navigate" data-view="booking">Записатися</button>
          <button class="btn btn-ghost" type="button" data-action="navigate" data-view="records">Мої записи</button>
        </div>
      </section>
      ${nextCard}
      <div class="quick-grid">
        <button class="quick-action" type="button" data-action="navigate" data-view="services">
          <span class="quick-icon" aria-hidden="true">✂</span>
          <strong>Послуги</strong>
          <span>Ціни та тривалість</span>
        </button>
        <button class="quick-action" type="button" data-action="navigate" data-view="booking">
          <span class="quick-icon" aria-hidden="true">＋</span>
          <strong>Новий запис</strong>
          <span>Вільні вікна</span>
        </button>
        <button class="quick-action" type="button" data-action="navigate" data-view="records">
          <span class="quick-icon" aria-hidden="true">◷</span>
          <strong>Мої записи</strong>
          <span>Статуси та скасування</span>
        </button>
        <button class="quick-action" type="button" data-action="navigate" data-view="info">
          <span class="quick-icon" aria-hidden="true">⌖</span>
          <strong>Контакти</strong>
          <span>Адреса та графік</span>
        </button>
      </div>
      <section class="card">
        <div class="section-heading"><h2>Графік салону</h2></div>
        <div class="working-hours muted">${esc(state.config.salon.working_hours)}</div>
        <p class="small muted" style="margin:10px 0 0">Слоти показуються з урахуванням тривалості послуги та перерви.</p>
      </section>`;
  }

  function renderServices() {
    content.innerHTML = `
      <div class="section-heading">
        <h2>Послуги та ціни</h2>
        <button type="button" data-action="navigate" data-view="booking">До запису →</button>
      </div>
      <div class="stack">${state.config.services.map((s) => serviceCard(s)).join("")}</div>
      <div class="card small muted">Ціни орієнтовні. Точну вартість підтвердить майстер.</div>`;
  }

  function bookingHeader(title, subtitle) {
    return `
      <div class="booking-head">
        <div>
          <h2>${esc(title)}</h2>
          <p>${esc(subtitle)}</p>
        </div>
      </div>
      <div class="stepper" aria-hidden="true">
        <div class="stepper-step ${state.booking?.step === "service" ? "is-done" : ""}"></div>
        <div class="stepper-step ${["date", "time", "confirm", "success"].includes(state.booking?.step) ? "is-done" : ""}"></div>
        <div class="stepper-step ${["time", "confirm", "success"].includes(state.booking?.step) ? "is-done" : ""}"></div>
        <div class="stepper-step ${["confirm", "success"].includes(state.booking?.step) ? "is-done" : ""}"></div>
      </div>`;
  }

  function renderBooking() {
    const booking = state.booking;
    if (booking && booking.step === "success" && booking.created) {
      const item = booking.created;
      content.innerHTML = `
        ${bookingHeader("Готово", "Заявку збережено в єдиній базі салону.")}
        <div class="card summary">
          <div class="row">
            <h3 class="summary-title">Заявку надіслано</h3>
            ${statusBadge(item)}
          </div>
          <div class="summary-grid">
            <div class="summary-line"><span>Номер</span><strong>#${esc(item.id)}</strong></div>
            <div class="summary-line"><span>Послуга</span><strong>${esc(item.service_name)}</strong></div>
            <div class="summary-line"><span>Дата</span><strong>${esc(item.date_label)}</strong></div>
            <div class="summary-line"><span>Час</span><strong>${esc(item.time_label)}</strong></div>
            <div class="summary-line"><span>Тривалість</span><strong>${esc(item.duration_minutes)} хв</strong></div>
          </div>
          <div class="banner"><strong>Що далі?</strong><span>Майстер підтвердить або відхилить заявку. Статус з'явиться в «Мої записи».</span></div>
          <div class="actions">
            <button class="btn btn-primary" type="button" data-action="navigate" data-view="records">Мої записи</button>
            <button class="btn btn-ghost" type="button" data-action="navigate" data-view="home">На головну</button>
          </div>
        </div>`;
      return;
    }
    if (!booking || !booking.service) {
      content.innerHTML = `
        ${bookingHeader("Запис", "Оберіть послугу, дату та зручний час.")}
        <div class="stack">${state.config.services.map((s) => serviceCard(s)).join("")}</div>`;
      return;
    }
    if (booking.step === "confirm" && booking.hold) {
      const hold = booking.hold;
      const holdMinutes = Math.max(1, Math.round((state.config.hold_ttl_seconds || 300) / 60));
      const remaining = hold.expires_at ? Math.max(0, Math.floor((new Date(hold.expires_at).getTime() - Date.now()) / 1000)) : 0;
      content.innerHTML = `
        ${bookingHeader("Перевірте заявку", `Слот утримується лише ${holdMinutes} хвилин.`)}
        <div class="card summary">
          <div class="summary-grid">
            <div class="summary-line"><span>Послуга</span><strong>${esc(hold.service_name)}</strong></div>
            <div class="summary-line"><span>Дата</span><strong>${esc(hold.date_label)}</strong></div>
            <div class="summary-line"><span>Час</span><strong>${esc(hold.time_label)}</strong></div>
            <div class="summary-line"><span>Тривалість</span><strong>${esc(hold.duration_minutes)} хв</strong></div>
            <div class="summary-line"><span>Ціна</span><strong>${esc(hold.price)}</strong></div>
          </div>
          <div class="hold-note ${remaining <= 0 ? "is-expired" : ""}" id="hold-note">
            <span aria-hidden="true">⏳</span>
            <span id="hold-text">${remaining > 0 ? "Слот утримується" : "Час утримання минув"}</span>
            <strong class="hold-clock" id="hold-clock">${formatCountdown(remaining)}</strong>
          </div>
          <div class="actions">
            <button class="btn btn-primary" type="button" data-action="confirm-hold" ${remaining <= 0 ? "disabled" : ""}>Підтвердити запис</button>
            <button class="btn btn-ghost" type="button" data-action="back-booking">Змінити час</button>
            <button class="btn btn-danger" type="button" data-action="cancel-hold">Скасувати вибір</button>
          </div>
        </div>`;
      if (remaining <= 0) {
        state.booking.expired = true;
      }
      return;
    }
    const dates = booking.dates || [];
    const slots = booking.slots || [];
    const dateStrip = dates.length
      ? `<div class="date-strip">${dates.map((date) => `
          <button class="date-chip ${date.id === booking.date?.id ? "is-selected" : ""}" type="button" data-action="choose-date" data-id="${esc(date.id)}">
            <strong>${esc(date.label.split(" ")[0])}</strong><span>${esc(date.label.split(" ").slice(1).join(" "))}</span>
          </button>`).join("")}</div>`
      : `<div class="empty-state"><div class="empty-icon" aria-hidden="true">◷</div><h3>Немає вільних дат</h3><p>Спробуйте іншу послугу або поверніться пізніше.</p></div>`;
    const times = booking.date
      ? `<div class="card stack">
          <div class="row"><strong>${esc(booking.date.label)}</strong><span class="muted small">${esc(booking.service.duration_minutes)} хв</span></div>
          ${slots.length ? `<div class="slots-grid">${slots.map((slot) => `
            <button class="slot slot-${esc(slot.status)} ${booking.selectedTime === slot.id ? "slot-selected" : ""}" type="button" data-action="choose-slot" data-id="${esc(slot.id)}" ${slot.status !== "free" ? "disabled" : ""} title="${esc(slotTitle(slot.status))}">${esc(slot.label)}</button>`).join("")}</div>` : `<div class="empty-state"><div class="empty-icon" aria-hidden="true">—</div><h3>Немає вільних годин</h3><p>Оберіть іншу дату.</p></div>`}
          <div class="legend">
            <span><i class="legend-free"></i>Вільно</span>
            <span><i class="legend-booked"></i>Зайнято</span>
            <span><i class="legend-unavailable"></i>Недоступно</span>
          </div>
        </div>`
      : "";
    content.innerHTML = `
      ${bookingHeader(booking.date ? "Оберіть час" : "Оберіть дату", booking.service.name)}
      <div class="card stack">
        <div class="row"><div><div class="muted small">Послуга</div><strong>${esc(booking.service.name)}</strong></div><div class="pill">${esc(booking.service.duration_minutes)} хв · ${esc(booking.service.price)}</div></div>
        ${dateStrip}
      </div>
      ${times}
      <div class="actions"><button class="btn btn-ghost" type="button" data-action="back-booking">← До послуг</button></div>`;
  }

  function slotTitle(status) {
    return {
      free: "Вільно",
      booked: "Уже зайнято",
      past: "Час минув",
      unavailable: "Недоступно для цієї послуги",
    }[status] || "Недоступно";
  }

  function formatCountdown(seconds) {
    const safe = Math.max(0, seconds);
    const minutes = Math.floor(safe / 60);
    const rest = safe % 60;
    return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
  }

  function updateHoldTimer() {
    if (!state.booking?.hold) return;
    const clock = document.getElementById("hold-clock");
    const note = document.getElementById("hold-note");
    const text = document.getElementById("hold-text");
    if (!clock) return;
    const remaining = Math.max(0, Math.floor((new Date(state.booking.hold.expires_at).getTime() - Date.now()) / 1000));
    clock.textContent = formatCountdown(remaining);
    if (remaining <= 0) {
      state.booking.expired = true;
      state.booking.holdKey = null;
      note?.classList.add("is-expired");
      if (text) text.textContent = "Час утримання минув";
      const button = document.querySelector('[data-action="confirm-hold"]');
      if (button) button.disabled = true;
      window.clearInterval(state.holdTimer);
      state.holdTimer = null;
      toast("Утримання минуло. Оберіть час ще раз.", true);
    }
  }

  function startHoldTimer() {
    window.clearInterval(state.holdTimer);
    state.holdTimer = window.setInterval(updateHoldTimer, 1000);
    updateHoldTimer();
  }

  function stopHoldTimer() {
    window.clearInterval(state.holdTimer);
    state.holdTimer = null;
  }

  async function startService(serviceId) {
    const service = state.config.services.find((item) => item.id === serviceId);
    if (!service) return;
    if (state.booking?.hold) {
      stopHoldTimer();
      try {
        await api(`/api/holds/${encodeURIComponent(state.booking.hold.id)}`, { method: "DELETE" });
      } catch (_) {
        /* The previous hold may already be inactive. */
      }
    }
    state.booking = { service, step: "date", dates: [], date: null, slots: [], hold: null, selectedTime: null };
    state.view = "booking";
    setActiveNav();
    render();
    await loadDates();
  }

  async function loadDates() {
    if (!state.booking?.service) return;
    setBusy(1);
    try {
      const data = await api(`/api/availability?service_id=${encodeURIComponent(state.booking.service.id)}`);
      state.booking.dates = data.dates || [];
      if (state.booking.date) {
        const stillThere = state.booking.dates.some((d) => d.id === state.booking.date.id);
        if (!stillThere) state.booking.date = null;
      }
      render();
    } catch (error) {
      toast(error.message || "Не вдалося завантажити дати.", true);
    } finally {
      setBusy(-1);
    }
  }

  async function chooseDate(dateId) {
    if (!state.booking?.service) return;
    setBusy(1);
    try {
      const data = await api(`/api/availability?service_id=${encodeURIComponent(state.booking.service.id)}&date=${encodeURIComponent(dateId)}`);
      state.booking.date = data.date;
      state.booking.slots = data.slots || [];
      state.booking.step = "time";
      state.booking.selectedTime = null;
      render();
      haptic("light");
    } catch (error) {
      toast(error.message || "Не вдалося завантажити час.", true);
    } finally {
      setBusy(-1);
    }
  }

  function bookingKey() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    return `hold-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }

  async function chooseSlot(timeId) {
    if (!state.booking?.service || !state.booking.date) return;
    if (!state.booking.holdKey) state.booking.holdKey = bookingKey();
    setBusy(1);
    try {
      const data = await api("/api/holds", {
        method: "POST",
        idempotencyKey: state.booking.holdKey,
        body: {
          service_id: state.booking.service.id,
          date: state.booking.date.id,
          time: timeId,
        },
      });
      state.booking.hold = data.booking;
      state.booking.selectedTime = timeId;
      state.booking.step = "confirm";
      state.booking.expired = false;
      startHoldTimer();
      render();
      haptic("medium");
    } catch (error) {
      if (error.code === "slot_taken" || error.code === "slot_unavailable") {
        toast("Цей час уже зайнятий. Оновлюємо слоти.", true);
        await chooseDate(state.booking.date.id);
      } else if (error.code === "hold_inactive" || error.code === "hold_expired") {
        state.booking.holdKey = null;
        toast("Утримання вже неактивне. Оберіть час ще раз.", true);
        await chooseDate(state.booking.date.id);
      } else {
        toast(error.message || "Не вдалося зарезервувати час.", true);
      }
    } finally {
      setBusy(-1);
    }
  }

  async function confirmHold() {
    const hold = state.booking?.hold;
    if (!hold || state.booking.expired) {
      toast("Утримання минуло. Оберіть час ще раз.", true);
      return;
    }
    setBusy(1);
    try {
      const data = await api(`/api/holds/${encodeURIComponent(hold.id)}/submit`, { method: "POST" });
      state.booking.created = data.booking;
      state.booking.step = "success";
      state.booking.hold = null;
      stopHoldTimer();
      await loadRecords(false);
      render();
      haptic("success");
    } catch (error) {
      if (error.code === "hold_expired") {
        toast("Час утримання минув. Оберіть час ще раз.", true);
        state.booking.expired = true;
        state.booking.holdKey = null;
        render();
      } else {
        toast(error.message || "Не вдалося надіслати заявку.", true);
      }
    } finally {
      setBusy(-1);
    }
  }

  async function cancelHold(backTo = "time") {
    const hold = state.booking?.hold;
    stopHoldTimer();
    if (hold && !state.booking.created) {
      setBusy(1);
      try {
        await api(`/api/holds/${encodeURIComponent(hold.id)}`, { method: "DELETE" });
      } catch (_) {
        /* The hold may already be expired; the UI still resets. */
      } finally {
        setBusy(-1);
      }
    }
    if (!state.booking) return;
    state.booking.hold = null;
    state.booking.expired = false;
    state.booking.holdKey = null;
    state.booking.step = backTo;
    state.booking.selectedTime = null;
    if (backTo === "service") {
      state.booking = null;
    }
    render();
  }

  async function backBooking() {
    if (!state.booking) return;
    if (state.booking.step === "confirm") {
      await cancelHold("time");
    } else if (state.booking.step === "time") {
      state.booking.date = null;
      state.booking.slots = [];
      state.booking.step = "date";
      render();
    } else if (state.booking.step === "date") {
      state.booking = null;
      render();
    }
  }

  function renderRecords() {
    const items = state.records;
    if (!items.length) {
      content.innerHTML = `
        <div class="section-heading"><h2>Мої записи</h2></div>
        <div class="empty-state">
          <div class="empty-icon" aria-hidden="true">◷</div>
          <h3>Поки що порожньо</h3>
          <p>Тут з'являться заявки та підтверджені записи.</p>
          <button class="btn btn-primary" type="button" data-action="navigate" data-view="booking">Записатися</button>
        </div>`;
      return;
    }
    content.innerHTML = `
      <div class="section-heading"><h2>Мої записи</h2><button type="button" data-action="refresh">Оновити</button></div>
      <div class="record-list">${items.map((item) => `
        <article class="record-card">
          <div class="record-top">
            <div>
              <h3 class="record-title">${esc(item.service_name)}</h3>
              <div class="record-meta">${esc(item.date_label)} · <span class="nowrap">${esc(item.time_label)} · ${esc(item.duration_minutes)} хв</span></div>
            </div>
            ${statusBadge(item)}
          </div>
          <div class="record-meta">${esc(item.price || "")}</div>
          ${item.status === "held" && item.can_submit ? `<div class="banner"><strong>Слот утримується</strong><span>Підтвердьте заявку, доки не минув час.</span></div>` : ""}
          <div class="record-actions">
            ${item.can_submit ? `<button class="btn btn-primary btn-small" type="button" data-action="resume-hold" data-id="${esc(item.id)}">Підтвердити</button>` : ""}
            ${item.can_cancel ? `<button class="btn btn-danger btn-small" type="button" data-action="cancel-record" data-id="${esc(item.id)}">Скасувати</button>` : ""}
            ${item.status === "rejected" ? `<span class="small muted">Оберіть інший час у розділі «Запис».</span>` : ""}
          </div>
        </article>`).join("")}</div>`;
  }

  function renderInfo() {
    const salon = state.config.salon;
    content.innerHTML = `
      <div class="section-heading"><h2>Про салон</h2></div>
      <div class="card stack">
        <div class="hero-kicker" style="color:var(--accent-strong)">${esc(salon.name)}</div>
        <h3 class="summary-title">Краса без поспіху</h3>
        <p class="muted" style="margin:0">Демонстраційний проєкт із єдиною системою запису для Telegram-бота та Mini App.</p>
        <div class="info-list">
          <div class="info-row"><span>Адреса</span><strong>${esc(salon.address)}</strong></div>
          <div class="info-row"><span>Телефон</span><a href="${esc(salon.phone_uri)}">${esc(salon.phone)}</a></div>
          <div class="info-row"><span>Instagram</span><a href="${esc(salon.instagram)}" target="_blank" rel="noreferrer">Відкрити</a></div>
          <div class="info-row"><span>Графік</span><strong class="working-hours">${esc(salon.working_hours)}</strong></div>
        </div>
      </div>
      <div class="card small muted">Скасувати запис онлайн можна не пізніше ніж за ${esc(Math.floor(state.config.cancellation_cutoff_minutes / 60))} год до початку. Пізніше — за телефоном.</div>`;
  }

  async function loadRecords(shouldRender = true) {
    try {
      const data = await api("/api/bookings");
      state.records = data.items || [];
      if (shouldRender && state.view === "records") render();
    } catch (error) {
      if (error.status === 401) {
        renderAuth("Сесія Telegram недійсна. Відкрийте Mini App знову.");
        throw error;
      }
      toast(error.message || "Не вдалося завантажити записи.", true);
    }
  }

  async function resumeHold(id) {
    setBusy(1);
    try {
      const data = await api(`/api/holds/${encodeURIComponent(id)}/submit`, { method: "POST" });
      await loadRecords(false);
      state.booking = { step: "success", created: data.booking, service: null, dates: [] };
      state.view = "booking";
      render();
      toast("Заявку надіслано майстру.", false);
    } catch (error) {
      toast(error.message || "Не вдалося підтвердити утримання.", true);
      await loadRecords(false);
    } finally {
      setBusy(-1);
    }
  }

  async function cancelRecord(id) {
    if (!window.confirm("Скасувати цей запис?")) return;
    setBusy(1);
    try {
      await api(`/api/bookings/${encodeURIComponent(id)}`, { method: "DELETE" });
      toast("Запис скасовано.");
      await loadRecords(false);
      render();
    } catch (error) {
      toast(error.message || "Не вдалося скасувати запис.", true);
      await loadRecords(false);
    } finally {
      setBusy(-1);
    }
  }

  async function loadAdminRequests() {
    setBusy(1);
    try {
      const data = await api(`/api/admin/bookings?status=${encodeURIComponent(state.admin.status)}&page=${encodeURIComponent(state.admin.page)}`);
      state.admin.items = data.items || [];
      state.admin.pages = data.pages || 1;
      state.admin.page = data.page || 1;
      state.admin.total = data.total || 0;
      renderAdmin();
    } catch (error) {
      toast(error.message || "Не вдалося завантажити заявки.", true);
    } finally {
      setBusy(-1);
    }
  }

  async function loadAdminDay() {
    setBusy(1);
    try {
      const data = await api(`/api/admin/day?date=${encodeURIComponent(state.admin.day)}`);
      state.admin.dayItems = data.bookings || [];
      renderAdmin();
    } catch (error) {
      toast(error.message || "Не вдалося завантажити день.", true);
    } finally {
      setBusy(-1);
    }
  }

  function adminFilters() {
    const options = [
      ["pending", "Очікують"],
      ["confirmed", "Підтверджені"],
      ["all", "Усі"],
    ];
    return `<div class="filter-row">${options.map(([value, label]) => `
      <button class="filter-button ${state.admin.status === value ? "is-active" : ""}" type="button" data-action="admin-status" data-value="${value}">${label}</button>`).join("")}</div>`;
  }

  function adminRequestCard(item) {
    return `
      <article class="admin-card">
        <div class="record-top">
          <div>
            <h3 class="record-title">${esc(item.service_name)}</h3>
              <div class="record-meta">${esc(item.client || "клієнт")} · <span class="nowrap">${esc(item.date_label)} · ${esc(item.time_label)}</span></div>
          </div>
          ${statusBadge(item)}
        </div>
        <div class="record-meta">${esc(item.duration_minutes)} хв · ${esc(item.price || "")} · #${esc(item.id)}</div>
        ${item.status === "pending" ? `<div class="record-actions">
          <button class="btn btn-primary btn-small" type="button" data-action="admin-confirm" data-id="${esc(item.id)}">Підтвердити</button>
          <button class="btn btn-danger btn-small" type="button" data-action="admin-reject" data-id="${esc(item.id)}">Відхилити</button>
        </div>` : ""}
      </article>`;
  }

  function renderAdmin() {
    const isDay = state.admin.tab === "day";
    content.innerHTML = `
      <div class="section-heading"><h2>Адмін-панель</h2><button type="button" data-action="refresh">Оновити</button></div>
      <div class="admin-tabs">
        <button type="button" class="${!isDay ? "is-active" : ""}" data-action="admin-tab" data-value="requests">Заявки</button>
        <button type="button" class="${isDay ? "is-active" : ""}" data-action="admin-tab" data-value="day">День</button>
      </div>
      ${!isDay ? `
        <div class="card stack">
          ${adminFilters()}
          ${state.admin.items.length ? state.admin.items.map(adminRequestCard).join("") : `<div class="empty-state"><div class="empty-icon" aria-hidden="true">✓</div><h3>Немає заявок</h3><p>У цьому фільтрі поки порожньо.</p></div>`}
          <div class="pager">
            <button class="btn btn-ghost btn-small" type="button" data-action="admin-page" data-value="${state.admin.page - 1}" ${state.admin.page <= 1 ? "disabled" : ""}>←</button>
            <span>${esc(state.admin.page)} / ${esc(state.admin.pages)}</span>
            <button class="btn btn-ghost btn-small" type="button" data-action="admin-page" data-value="${state.admin.page + 1}" ${state.admin.page >= state.admin.pages ? "disabled" : ""}>→</button>
          </div>
        </div>` : `
        <div class="card stack">
          <div class="day-picker">
            <input id="admin-day" type="date" value="${esc(state.admin.day)}" aria-label="Дата">
            <button class="btn btn-primary btn-small" type="button" data-action="admin-load-day">Показати</button>
          </div>
          ${state.admin.dayItems.length ? state.admin.dayItems.map(adminRequestCard).join("") : `<div class="empty-state"><div class="empty-icon" aria-hidden="true">◷</div><h3>Вільний день</h3><p>На цю дату активних записів немає.</p></div>`}
        </div>`}
      <div class="card small muted">Графік і тривалість послуг налаштовуються в <code>config.py</code>. Редагування графіка з адмінки — наступний етап; тут показані реальні записи з єдиної бази.</div>`;
  }

  async function adminAction(id, actionName) {
    if (!window.confirm(actionName === "confirm" ? "Підтвердити цю заявку?" : "Відхилити цю заявку?")) return;
    setBusy(1);
    try {
      await api(`/api/admin/bookings/${encodeURIComponent(id)}/${actionName}`, { method: "POST" });
      toast(actionName === "confirm" ? "Запис підтверджено." : "Заявку відхилено.");
      await Promise.all([loadAdminRequests(), loadAdminDay()]);
      render();
    } catch (error) {
      toast(error.message || "Не вдалося обробити заявку.", true);
    } finally {
      setBusy(-1);
    }
  }

  function render() {
    if (!state.config) return;
    setSalonHeader();
    setActiveNav();
    if (state.view === "home") renderHome();
    else if (state.view === "services") renderServices();
    else if (state.view === "booking") renderBooking();
    else if (state.view === "records") renderRecords();
    else if (state.view === "info") renderInfo();
    else if (state.view === "admin") renderAdmin();
  }

  async function refreshCurrent() {
    setBusy(1);
    try {
      if (state.view === "admin") {
        await Promise.all([loadAdminRequests(), loadAdminDay()]);
      } else {
        await loadRecords(false);
        render();
      }
    } catch (error) {
      toast(error.message || "Не вдалося оновити.", true);
    } finally {
      setBusy(-1);
    }
  }

  async function init() {
    applyTheme();
    if (!tg) {
      renderAuth("Telegram WebApp недоступний. Відкрийте застосунок через кнопку в боті.");
      return;
    }
    try {
      tg.ready();
      tg.expand();
      tg.onEvent?.("themeChanged", applyTheme);
      tg.setHeaderColor?.("secondary_bg_color");
      tg.setBackgroundColor?.("bg_color");
    } catch (_) {
      /* Older Telegram clients may not support every method. */
    }
    if (!tg.initData) {
      renderAuth("Немає підписаного initData. Відкрийте Mini App через Telegram.");
      return;
    }
    setBusy(1);
    try {
      state.config = await api("/api/config");
      await loadRecords(false);
      bottomNav.hidden = false;
      adminNav.hidden = !state.config.is_admin;
      render();
    } catch (error) {
      if (error.status === 401) renderAuth("Сесія Telegram недійсна. Відкрийте Mini App знову.");
      else renderError(error.message || "Сервер недоступний.", error.code);
    } finally {
      setBusy(-1);
    }
  }

  document.addEventListener("click", async (event) => {
    const target = event.target.closest("[data-action]");
    if (!target) return;
    const action = target.dataset.action;
    try {
      if (action === "navigate") {
        if (target.dataset.view === "admin" && state.config && !state.config.is_admin) return;
        navigate(target.dataset.view);
      } else if (action === "refresh") {
        await refreshCurrent();
      } else if (action === "retry") {
        await init();
      } else if (action === "start-service") {
        await startService(target.dataset.id);
      } else if (action === "choose-date") {
        await chooseDate(target.dataset.id);
      } else if (action === "choose-slot") {
        await chooseSlot(target.dataset.id);
      } else if (action === "confirm-hold") {
        await confirmHold();
      } else if (action === "cancel-hold") {
        await cancelHold("service");
      } else if (action === "back-booking") {
        await backBooking();
      } else if (action === "resume-hold") {
        await resumeHold(target.dataset.id);
      } else if (action === "cancel-record") {
        await cancelRecord(target.dataset.id);
      } else if (action === "admin-status") {
        state.admin.status = target.dataset.value;
        state.admin.page = 1;
        await loadAdminRequests();
      } else if (action === "admin-page") {
        const page = Number(target.dataset.value);
        if (page >= 1 && page <= state.admin.pages) {
          state.admin.page = page;
          await loadAdminRequests();
        }
      } else if (action === "admin-tab") {
        state.admin.tab = target.dataset.value;
        renderAdmin();
        if (state.admin.tab === "day") {
          await loadAdminDay();
        } else if (!state.admin.items.length) {
          await loadAdminRequests();
        }
      } else if (action === "admin-load-day") {
        const input = document.getElementById("admin-day");
        if (input && input.value) {
          state.admin.day = input.value;
          await loadAdminDay();
        }
      } else if (action === "admin-confirm") {
        await adminAction(target.dataset.id, "confirm");
      } else if (action === "admin-reject") {
        await adminAction(target.dataset.id, "reject");
      }
    } catch (error) {
      toast(error.message || "Помилка виконання дії.", true);
    }
  });

  document.addEventListener("change", (event) => {
    if (event.target && event.target.id === "admin-day") {
      state.admin.day = event.target.value;
    }
  });

  init();
})();
