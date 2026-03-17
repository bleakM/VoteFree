(function () {
  const ctx = window.VF_CONTEXT || {};
  const qid = ctx.questionnaireId;
  const passcodeEnabled = !!ctx.passcodeEnabled;
  const passcodeUnlocked = !!ctx.passcodeUnlocked;

  const passcodeCard = document.getElementById("passcodeCard");
  const surveyCard = document.getElementById("surveyCard");
  const verifyCard = document.getElementById("verifyCard");
  const formEl = document.getElementById("vfForm");
  const statusBox = document.getElementById("vfStatusBox");
  const unlockStatus = document.getElementById("vfUnlockStatus");
  const verifyStatus = document.getElementById("vfVerifyStatus");
  const verifyHint = document.getElementById("vfVerifyHint");
  const verifyFieldsWrap = document.getElementById("vfVerifyFields");
  const identityWrap = document.getElementById("vfIdentityWrap");
  const unlockBtn = document.getElementById("vfUnlockBtn");
  const verifyBtn = document.getElementById("vfVerifyBtn");
  const submitBtn = document.getElementById("vfSubmitBtn");
  const resetBtn = document.getElementById("vfResetBtn");

  const state = {
    questionnaire: null,
    authToken: "",
    verifiedMember: null,
    verifiedIdentity: {},
    verifyPassed: false,
    applyingDraft: false,
    repeatRenderSignatures: {},
    lastValidAnswers: {},
    liveCheckTimer: null,
    liveCheckSeq: 0,
    liveCheckPaused: false,
  };
  const ROSTER_REPEAT_TOKEN = "__roster_members__";

  function escapeHtml(text) {
    return String(text)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function randomToken() {
    const key = "votefree_client_token";
    let token = localStorage.getItem(key);
    if (!token) {
      const raw = (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)).replaceAll("-", "");
      token = "T" + raw.slice(0, 16);
      localStorage.setItem(key, token);
    }
    return token;
  }

  function draftKey() {
    return `votefree_draft_${qid}`;
  }

  function setStatus(msg, ok = false) {
    statusBox.textContent = msg || "";
    statusBox.className = "vf-status " + (msg ? (ok ? "vf-ok" : "vf-err") : "");
  }

  function setUnlockStatus(msg, ok = false) {
    if (!unlockStatus) return;
    unlockStatus.textContent = msg || "";
    unlockStatus.className = "vf-status " + (msg ? (ok ? "vf-ok" : "vf-err") : "");
  }

  function setVerifyStatus(msg, ok = false) {
    if (!verifyStatus) return;
    verifyStatus.textContent = msg || "";
    verifyStatus.className = "vf-status " + (msg ? (ok ? "vf-ok" : "vf-err") : "");
  }

  function ensureLiveToast() {
    let el = document.getElementById("vfLiveToast");
    if (!el) {
      el = document.createElement("div");
      el.id = "vfLiveToast";
      el.className = "vf-toast";
      document.body.appendChild(el);
    }
    return el;
  }

  function showLiveToast(message, ok = false) {
    const text = String(message || "").trim();
    if (!text) return;
    const el = ensureLiveToast();
    el.textContent = text;
    el.className = "vf-toast " + (ok ? "vf-toast-ok" : "vf-toast-err");
    window.clearTimeout(Number(el.dataset.timer || 0));
    requestAnimationFrame(() => {
      el.classList.add("show");
    });
    const timer = window.setTimeout(() => {
      el.classList.remove("show");
    }, 2200);
    el.dataset.timer = String(timer);
  }

  function showCard(card, visible) {
    if (!card) return;
    if (visible) card.classList.remove("vf-hidden");
    else card.classList.add("vf-hidden");
  }

  function normalizeCollectFields(rawList) {
    if (!Array.isArray(rawList)) return [];
    const out = [];
    const seen = new Set();
    rawList.forEach((item, idx) => {
      const key = String(item?.key || "").trim() || `field_${idx + 1}`;
      if (!key || seen.has(key)) return;
      seen.add(key);
      out.push({ key, label: String(item?.label || "").trim() || key });
    });
    return out;
  }

  function getCollectFields() {
    if (!state.questionnaire) return [];
    const identityFields = state.questionnaire.identity_fields || {};
    let fields = normalizeCollectFields(identityFields.collect_fields || []);
    if (!fields.length) {
      if (identityFields.collect_code) fields.push({ key: "member_code", label: "编号" });
      if (identityFields.collect_name) fields.push({ key: "member_name", label: "姓名" });
    }
    const mode = String(state.questionnaire.auth_mode || "open").trim().toLowerCase();
    if (!fields.length) {
      if (mode === "roster_name_code") fields = [{ key: "member_code", label: "编号" }, { key: "member_name", label: "姓名" }];
      else if (mode === "roster_code") fields = [{ key: "member_code", label: "编号" }];
    }
    return normalizeCollectFields(fields);
  }

  function needVerifyStep() {
    if (!state.questionnaire) return false;
    return !!state.questionnaire.auth_required || getCollectFields().length > 0;
  }

  function verifyInputId(key, index = 0) {
    const encoded = encodeURIComponent(String(key || ""))
      .replaceAll("%", "_")
      .slice(0, 96);
    return `vfVerifyField_${index}_${encoded}`;
  }

  function normalizedRule(rule) {
    if (!rule || typeof rule !== "object") return null;
    if (Array.isArray(rule.all)) {
      return { all: rule.all.map((x) => normalizedRule(x)).filter(Boolean) };
    }
    if (Array.isArray(rule.any)) {
      return { any: rule.any.map((x) => normalizedRule(x)).filter(Boolean) };
    }
    if (rule.not) {
      const n = normalizedRule(rule.not);
      return n ? { not: n } : null;
    }
    const q = String(rule.question_id || "").trim();
    if (!q) return null;
    if (Object.prototype.hasOwnProperty.call(rule, "equals")) {
      return { question_id: q, op: "equals", value: rule.equals };
    }
    if (Object.prototype.hasOwnProperty.call(rule, "contains")) {
      return { question_id: q, op: "contains", value: rule.contains };
    }
    return { question_id: q, op: String(rule.op || "equals"), value: rule.value };
  }

  function evalRule(rule, answers) {
    const normalized = normalizedRule(rule);
    if (!normalized) return true;
    if (normalized.all) return normalized.all.every((x) => evalRule(x, answers));
    if (normalized.any) return normalized.any.some((x) => evalRule(x, answers));
    if (normalized.not) return !evalRule(normalized.not, answers);

    const actual = answers[normalized.question_id];
    const expected = normalized.value;
    const op = String(normalized.op || "equals");
    if (op === "equals") return actual === expected;
    if (op === "not_equals") return actual !== expected;
    if (op === "contains") {
      if (Array.isArray(actual)) return actual.includes(expected);
      return String(actual || "").includes(String(expected || ""));
    }
    if (op === "in") {
      return Array.isArray(expected) ? expected.includes(actual) : false;
    }
    if (op === "gt") {
      const a = Number(actual);
      const b = Number(expected);
      return Number.isFinite(a) && Number.isFinite(b) && a > b;
    }
    if (op === "gte") {
      const a = Number(actual);
      const b = Number(expected);
      return Number.isFinite(a) && Number.isFinite(b) && a >= b;
    }
    if (op === "lt") {
      const a = Number(actual);
      const b = Number(expected);
      return Number.isFinite(a) && Number.isFinite(b) && a < b;
    }
    if (op === "lte") {
      const a = Number(actual);
      const b = Number(expected);
      return Number.isFinite(a) && Number.isFinite(b) && a <= b;
    }
    if (op === "not_empty") {
      if (actual === null || actual === undefined) return false;
      if (Array.isArray(actual)) return actual.length > 0;
      if (typeof actual === "object") return Object.keys(actual).length > 0;
      return String(actual).trim().length > 0;
    }
    if (op === "empty") return !evalRule({ question_id: normalized.question_id, op: "not_empty" }, answers);
    return true;
  }

  function isVisible(question, answers) {
    return evalRule(question.visible_if, answers);
  }

  function repeatItemKey(itemKey) {
    return encodeURIComponent(String(itemKey));
  }

  function repeatItemDecode(encoded) {
    try {
      return decodeURIComponent(encoded);
    } catch (_err) {
      return encoded;
    }
  }

  function repeatItemsSignature(items) {
    if (!Array.isArray(items) || items.length === 0) return "__empty__";
    return items.map((item) => `${item.key}::${item.label}::${item.is_self ? 1 : 0}`).join("||");
  }

  function normalizeRepeatSourceItem(item) {
    if (item && typeof item === "object") {
      const rawKey = item.key ?? item.value ?? item.id ?? "";
      const key = String(rawKey).trim();
      if (!key) return null;
      const rawLabel = item.label ?? item.name ?? item.title ?? key;
      const code = String(item.member_code ?? item.code ?? "").trim();
      const name = String(item.member_name ?? item.name ?? "").trim();
      return {
        key,
        label: String(rawLabel).trim() || key,
        member_code: code,
        member_name: name,
        is_self: !!item.is_self,
      };
    }
    const text = String(item ?? "").trim();
    if (!text) return null;
    return { key: text, label: text, member_code: "", member_name: "", is_self: false };
  }

  function getCurrentMemberKey() {
    const verifiedKey = String(state.verifiedMember?.member_key || "").trim();
    if (verifiedKey) return verifiedKey;
    const rosterItems = (state.questionnaire?.roster_repeat_items || [])
      .map((item) => normalizeRepeatSourceItem(item))
      .filter(Boolean);
    if (!rosterItems.length) return "";
    const codeInput = String(state.verifiedIdentity?.member_code || "").trim();
    if (codeInput) {
      const codeMatches = rosterItems.filter((item) => String(item.member_code || "").trim() === codeInput);
      if (codeMatches.length === 1) return codeMatches[0].key;
    }
    const nameInput = String(state.verifiedIdentity?.member_name || "").trim();
    if (nameInput) {
      const nameMatches = rosterItems.filter((item) => String(item.member_name || "").trim() === nameInput);
      if (nameMatches.length === 1) return nameMatches[0].key;
    }
    return "";
  }

  function applyRepeatFilter(question, items) {
    const repeatFilter = String(question?.repeat_filter || "all").trim().toLowerCase();
    if (repeatFilter === "all") return items;
    const currentKey = getCurrentMemberKey();
    return items.filter((item) => {
      const itemIsSelf = !!item.is_self || (currentKey && item.key === currentKey);
      if (repeatFilter === "self") return itemIsSelf;
      if (repeatFilter === "peer") return !itemIsSelf;
      return true;
    });
  }

  function getRepeatSourceItems(question, answers) {
    if (!question?.repeat_from) return [];
    if (question.repeat_from === ROSTER_REPEAT_TOKEN) {
      const fromRoster = state.questionnaire?.roster_repeat_items || [];
      const normalized = fromRoster.map((item) => normalizeRepeatSourceItem(item)).filter(Boolean);
      return applyRepeatFilter(question, normalized);
    }
    if (String(question.repeat_from).startsWith("__list__:")) {
      const listName = String(question.repeat_from).slice("__list__:".length).trim();
      const listObjects = state.questionnaire?.schema?.meta?.list_objects || [];
      if (!Array.isArray(listObjects) || !listName) return [];
      const target = listObjects.find((x) => String(x?.name || "").trim() === listName);
      if (!target || !Array.isArray(target.items)) return [];
      const normalized = target.items.map((item) => normalizeRepeatSourceItem(item)).filter(Boolean);
      return applyRepeatFilter(question, normalized);
    }
    const fromAnswer = answers[question.repeat_from];
    if (!Array.isArray(fromAnswer)) return [];
    const normalized = fromAnswer.map((item) => normalizeRepeatSourceItem(item)).filter(Boolean);
    return applyRepeatFilter(question, normalized);
  }

  function isRequired(question, answers) {
    if (question?.required_if) return evalRule(question.required_if, answers);
    return !!question?.required;
  }

  function getQuestionValue(question) {
    if (question.repeat_from) {
      return getRepeatQuestionValues(question);
    }
    if (question.type === "text" || question.type === "textarea") {
      const el = formEl.querySelector(`[data-id="${question.id}"]`);
      return el ? el.value.trim() : "";
    }
    if (question.type === "slider") {
      const el = formEl.querySelector(`[data-id="${question.id}"]`);
      return el ? Number(el.value) : "";
    }
    if (question.type === "single" || question.type === "rating") {
      const el = formEl.querySelector(`input[name="${question.id}"]:checked`);
      if (!el) return "";
      return question.type === "rating" ? Number(el.value) : el.value;
    }
    if (question.type === "multi") {
      return Array.from(formEl.querySelectorAll(`input[name="${question.id}"]:checked`)).map((n) => n.value);
    }
    return "";
  }

  function getRepeatQuestionValues(question) {
    const panel = formEl.querySelector(`.vf-q[data-qid="${question.id}"]`);
    if (!panel) return {};
    // 兼容旧 class 与当前 data 属性，避免重绘时丢失已选值。
    const items = Array.from(panel.querySelectorAll(".vf-repeat-item, [data-repeat-item]"));
    const map = {};
    items.forEach((itemNode) => {
      const encoded = itemNode.getAttribute("data-item") || "";
      const item = repeatItemDecode(encoded);
      let value = "";
      if (question.type === "text" || question.type === "textarea") {
        const el = itemNode.querySelector("[data-repeat-input='text']");
        value = el ? el.value.trim() : "";
      } else if (question.type === "slider") {
        const el = itemNode.querySelector("[data-repeat-input='slider']");
        value = el ? Number(el.value) : "";
      } else if (question.type === "single" || question.type === "rating") {
        const el = itemNode.querySelector(`input[name="${question.id}__${encoded}"]:checked`);
        value = el ? (question.type === "rating" ? Number(el.value) : el.value) : "";
      } else if (question.type === "multi") {
        value = Array.from(itemNode.querySelectorAll(`input[name="${question.id}__${encoded}"]:checked`)).map(
          (n) => n.value,
        );
      }
      if (value !== "" && (!(Array.isArray(value)) || value.length > 0)) {
        map[item] = value;
      }
    });
    return map;
  }

  function setRepeatItemValue(question, itemKey, itemValue) {
    const encoded = repeatItemKey(itemKey);
    if (question.type === "text" || question.type === "textarea") {
      const el = formEl.querySelector(
        `.vf-q[data-qid="${question.id}"] .vf-repeat-item[data-item="${encoded}"] [data-repeat-input="text"]`,
      );
      if (el) el.value = itemValue ?? "";
      return;
    }
    if (question.type === "slider") {
      const el = formEl.querySelector(
        `.vf-q[data-qid="${question.id}"] .vf-repeat-item[data-item="${encoded}"] [data-repeat-input="slider"]`,
      );
      if (el) {
        el.value = Number(itemValue);
        const marker = el.nextElementSibling;
        if (marker) marker.textContent = String(itemValue);
      }
      return;
    }
    if (question.type === "single" || question.type === "rating") {
      const el = formEl.querySelector(`input[name="${question.id}__${encoded}"][value="${itemValue}"]`);
      if (el) el.checked = true;
      return;
    }
    if (question.type === "multi" && Array.isArray(itemValue)) {
      itemValue.forEach((opt) => {
        const el = formEl.querySelector(`input[name="${question.id}__${encoded}"][value="${opt}"]`);
        if (el) el.checked = true;
      });
    }
  }

  function collectRawAnswers() {
    const answers = {};
    const questions = state.questionnaire?.schema?.questions || [];
    questions.forEach((q) => {
      const panel = formEl.querySelector(`.vf-q[data-qid="${q.id}"]`);
      if (!panel || panel.classList.contains("vf-hidden")) return;
      const value = getQuestionValue(q);
      if (value === "") return;
      if (Array.isArray(value) && value.length === 0) return;
      if (typeof value === "object" && !Array.isArray(value) && Object.keys(value).length === 0) return;
      answers[q.id] = value;
    });
    return answers;
  }

  function collectAnswers(validate = true) {
    const questions = state.questionnaire?.schema?.questions || [];
    const errors = [];
    const answers = collectRawAnswers();

    if (!validate) return { answers, errors };

    function wordCount(text) {
      return String(text || "")
        .replaceAll("\n", " ")
        .split(" ")
        .filter((x) => x.trim().length > 0).length;
    }

    function validateTextLimits(question, textValue) {
      const text = String(textValue || "").trim();
      if (!text) return;
      const minLength = Number(question.min_length || 0);
      const maxLength = Number(question.max_length || 0);
      const minWords = Number(question.min_words || 0);
      const maxWords = Number(question.max_words || 0);
      const maxLines = Number(question.max_lines || 0);
      if (minLength > 0 && text.length < minLength) {
        errors.push(`${question.title} 至少需要 ${minLength} 个字符`);
      }
      if (maxLength > 0 && text.length > maxLength) {
        errors.push(`${question.title} 最多允许 ${maxLength} 个字符`);
      }
      const wc = wordCount(text);
      if (minWords > 0 && wc < minWords) {
        errors.push(`${question.title} 至少需要 ${minWords} 个词`);
      }
      if (maxWords > 0 && wc > maxWords) {
        errors.push(`${question.title} 最多允许 ${maxWords} 个词`);
      }
      if (question.type === "textarea" && maxLines > 0) {
        const lineCount = text.split("\n").length;
        if (lineCount > maxLines) {
          errors.push(`${question.title} 最多允许 ${maxLines} 行`);
        }
      }
    }

    function validateNumericValue(question, rawValue, suffix = "") {
      if (rawValue === undefined || rawValue === null || rawValue === "") return;
      const num = Number(rawValue);
      if (!Number.isFinite(num)) {
        errors.push(`${question.title}${suffix} 必须是有效数字`);
        return;
      }
      const min = Number.isInteger(question.min) ? question.min : 0;
      const max = Number.isInteger(question.max) ? question.max : 100;
      const step = Number.isInteger(question.step) && question.step > 0 ? question.step : 1;
      if (num < min || num > max) {
        errors.push(`${question.title}${suffix} 必须在 ${min}-${max} 范围内`);
        return;
      }
      if (((num - min) % step) !== 0) {
        errors.push(`${question.title}${suffix} 的步进不符合要求`);
      }
    }

    questions.forEach((q) => {
      const panel = formEl.querySelector(`.vf-q[data-qid="${q.id}"]`);
      if (!panel || panel.classList.contains("vf-hidden")) return;
      const required = isRequired(q, answers);
      const value = answers[q.id];
      const empty =
        value === undefined ||
        value === "" ||
        (Array.isArray(value) && value.length === 0) ||
        (typeof value === "object" && !Array.isArray(value) && Object.keys(value).length === 0);
      if (required && empty) {
        errors.push(`${q.title} 为必填项`);
      }
      if (q.type === "multi" && Array.isArray(value) && q.max_select && value.length > q.max_select) {
        errors.push(`${q.title} 最多可选 ${q.max_select} 项`);
      }
      if (q.type === "multi" && Array.isArray(value) && q.min_select && value.length > 0 && value.length < q.min_select) {
        errors.push(`${q.title} 至少可选 ${q.min_select} 项`);
      }
      if ((q.type === "text" || q.type === "textarea") && typeof value === "string") {
        validateTextLimits(q, value);
      }
      if (q.type === "rating" || q.type === "slider") {
        if (q.repeat_from && value && typeof value === "object" && !Array.isArray(value)) {
          const src = getRepeatSourceItems(q, answers);
          if (src.length > 0) {
            src.forEach((item) => {
              if (!Object.prototype.hasOwnProperty.call(value, item.key)) return;
              validateNumericValue(q, value[item.key], `（${item.label}）`);
            });
          } else {
            Object.entries(value).forEach(([itemKey, itemValue]) => {
              validateNumericValue(q, itemValue, `（${itemKey}）`);
            });
          }
        } else {
          validateNumericValue(q, value);
        }
      }
      if (q.repeat_from && required) {
        const src = getRepeatSourceItems(q, answers);
        if (src.length > 0) {
          const map = value || {};
          src.forEach((item) => {
            if (!Object.prototype.hasOwnProperty.call(map, item.key)) {
              errors.push(`${q.title} 的循环项未完成：${item.label}`);
            }
          });
          if (q.type === "multi") {
            src.forEach((item) => {
              const itemValue = map[item.key];
              if (!Array.isArray(itemValue)) return;
              if (q.max_select && itemValue.length > q.max_select) {
                errors.push(`${q.title}（${item.label}）最多可选 ${q.max_select} 项`);
              }
              if (q.min_select && itemValue.length > 0 && itemValue.length < q.min_select) {
                errors.push(`${q.title}（${item.label}）至少可选 ${q.min_select} 项`);
              }
            });
          }
          if (q.type === "text" || q.type === "textarea") {
            src.forEach((item) => {
              const itemValue = map[item.key];
              if (typeof itemValue === "string") validateTextLimits(q, itemValue);
            });
          }
        }
      }
    });
    return { answers, errors };
  }

  function renderIdentity() {
    if (!state.questionnaire) return;
    const fields = getCollectFields();
    let summaryHtml = "";
    if (fields.length && state.verifyPassed) {
      const rows = fields
        .map((field) => {
          const key = String(field.key || "").trim();
          const label = String(field.label || "").trim() || key;
          const value = String(state.verifiedIdentity?.[key] || "").trim();
          if (!value) return "";
          return `<div class="vf-opt"><strong>${escapeHtml(label)}：</strong>${escapeHtml(value)}</div>`;
        })
        .filter(Boolean)
        .join("");
      if (rows) summaryHtml = `<div class="vf-status" style="margin-bottom:8px;">已完成进入前身份采集</div>${rows}`;
    }

    let html = "<div class='vf-q'><h3>答卷信息</h3>";
    if (summaryHtml) html += `<div style="margin-bottom:10px;">${summaryHtml}</div>`;
    html += `
      <div class="vf-row" style="margin-top:10px;">
        <div>
          <label class="vf-opt">关系类型（可选）</label>
          <input id="vfRelationType" type="text" placeholder="例如：自评 / 互评 / 投票" />
        </div>
        <div>
          <label class="vf-opt">目标对象（可选）</label>
          <input id="vfTargetLabel" type="text" placeholder="例如：候选人A / 项目1" />
        </div>
      </div>
    `;
    html += "</div>";
    identityWrap.innerHTML = html;
  }

  function readVerifyIdentityInputs() {
    const out = {};
    getCollectFields().forEach((field, idx) => {
      const key = String(field.key || "").trim();
      if (!key) return;
      const id = verifyInputId(key, idx);
      const value = String(document.getElementById(id)?.value || "").trim();
      out[key] = value;
    });
    return out;
  }

  function renderVerifyFields() {
    if (!verifyFieldsWrap) return;
    const fields = getCollectFields();
    if (!fields.length) {
      verifyFieldsWrap.innerHTML = "";
      return;
    }
    const chunks = fields.map((field, idx) => {
      const key = String(field.key || "").trim();
      const label = String(field.label || "").trim() || key;
      const id = verifyInputId(key, idx);
      const value = String(state.verifiedIdentity?.[key] || "").trim();
      return `
        <div>
          <label class="vf-opt">${escapeHtml(label)} <span class="vf-required">*</span></label>
          <input id="${escapeHtml(id)}" type="text" value="${escapeHtml(value)}" placeholder="请输入${escapeHtml(label)}" />
        </div>
      `;
    });
    verifyFieldsWrap.innerHTML = `<div class="vf-row">${chunks.join("")}</div>`;
  }

  function renderQuestionBody(question, repeatEncoded) {
    if (question.type === "text") {
      return `<input type="text" ${repeatEncoded ? `data-repeat-input="text"` : `data-id="${question.id}"`} />`;
    }
    if (question.type === "textarea") {
      return `<textarea ${repeatEncoded ? `data-repeat-input="text"` : `data-id="${question.id}"`}></textarea>`;
    }
    if (question.type === "single") {
      const name = repeatEncoded ? `${question.id}__${repeatEncoded}` : question.id;
      return (question.options || [])
        .map((opt) => `<label class="vf-opt"><input type="radio" name="${name}" value="${escapeHtml(opt)}" /> ${escapeHtml(opt)}</label>`)
        .join("");
    }
    if (question.type === "multi") {
      const name = repeatEncoded ? `${question.id}__${repeatEncoded}` : question.id;
      const opts = (question.options || [])
        .map((opt) => `<label class="vf-opt"><input type="checkbox" name="${name}" value="${escapeHtml(opt)}" /> ${escapeHtml(opt)}</label>`)
        .join("");
      let tip = "";
      if (question.min_select) tip += `至少选择 ${question.min_select} 项`;
      if (question.max_select) tip += `${tip ? "，" : ""}最多选择 ${question.max_select} 项`;
      return opts + (tip ? `<p class="vf-status">${tip}</p>` : "");
    }
    if (question.type === "slider") {
      const min = Number.isInteger(question.min) ? question.min : 0;
      const max = Number.isInteger(question.max) ? question.max : 100;
      const step = Number.isInteger(question.step) && question.step > 0 ? question.step : 1;
      const markerAttr = repeatEncoded ? `data-repeat-input="slider"` : `data-id="${question.id}"`;
      return `
        <div class="vf-slider-wrap">
          <input type="range" min="${min}" max="${max}" step="${step}" value="${min}" ${markerAttr}
            oninput="this.nextElementSibling.textContent=this.value" />
          <span class="vf-status" style="display:inline-block;margin-left:8px;">${min}</span>
        </div>
      `;
    }
    if (question.type === "rating") {
      const min = Number.isInteger(question.min) ? question.min : 1;
      const max = Number.isInteger(question.max) ? question.max : 5;
      const name = repeatEncoded ? `${question.id}__${repeatEncoded}` : question.id;
      let out = "";
      for (let i = min; i <= max; i += 1) {
        out += `<label class="vf-opt"><input type="radio" name="${name}" value="${i}" /> ${i} 分</label>`;
      }
      return out;
    }
    return "";
  }

  function renderQuestions() {
    const questions = state.questionnaire?.schema?.questions || [];
    const chunks = [];
    questions.forEach((q) => {
      const required = q.required ? '<span class="vf-required">*</span>' : "";
      if (q.repeat_from) {
        chunks.push(`
          <div class="vf-q" data-qid="${q.id}" data-repeat-from="${q.repeat_from}">
            <h3>${escapeHtml(q.title)}${required}</h3>
            <div class="vf-repeat-body"></div>
          </div>
        `);
        return;
      }
      chunks.push(`
        <div class="vf-q" data-qid="${q.id}">
          <h3>${escapeHtml(q.title)}${required}</h3>
          ${renderQuestionBody(q, "")}
        </div>
      `);
    });
    formEl.innerHTML = chunks.join("");
    state.repeatRenderSignatures = {};
  }

  function renderRepeatBlocks() {
    const questions = state.questionnaire?.schema?.questions || [];
    const answers = collectRawAnswers();
    questions.forEach((q) => {
      if (!q.repeat_from) return;
      const panel = formEl.querySelector(`.vf-q[data-qid="${q.id}"]`);
      if (!panel) return;
      const body = panel.querySelector(".vf-repeat-body");
      if (!body) return;
      const sourceItems = getRepeatSourceItems(q, answers);
      const signature = repeatItemsSignature(sourceItems);
      if (sourceItems.length === 0) {
        if (state.repeatRenderSignatures[q.id] === signature) return;
        if (q.repeat_from === ROSTER_REPEAT_TOKEN) {
          const filterMode = String(q.repeat_filter || "all").trim().toLowerCase();
          if (filterMode === "self") {
            body.innerHTML = "<p class='vf-status'>未识别到“本人”循环项，请先完成身份验证或填写身份信息。</p>";
          } else {
            body.innerHTML = "<p class='vf-status'>未读取到循环名单，请联系管理员检查问卷绑定名单。</p>";
          }
        } else {
          body.innerHTML = "<p class='vf-status'>请先完成循环来源题目后再填写本题。</p>";
        }
        state.repeatRenderSignatures[q.id] = signature;
        return;
      }
      if (state.repeatRenderSignatures[q.id] === signature) return;
      // 重绘前保留已输入值，避免循环区每次联动时清空。
      const existingValues = getRepeatQuestionValues(q);
      const segments = sourceItems.map((item) => {
        const encoded = repeatItemKey(item.key);
        return `
          <div class="vf-q vf-repeat-item" style="margin:8px 0;" data-repeat-item data-item="${encoded}">
            <h3 style="font-size:14px;margin-bottom:8px;">对象：${escapeHtml(item.label)}</h3>
            ${renderQuestionBody(q, encoded)}
          </div>
        `;
      });
      body.innerHTML = segments.join("");
      Object.entries(existingValues).forEach(([itemKey, itemValue]) => {
        setRepeatItemValue(q, itemKey, itemValue);
      });
      state.repeatRenderSignatures[q.id] = signature;
    });
  }

  function applyVisibility() {
    const questions = state.questionnaire?.schema?.questions || [];
    const answers = collectRawAnswers();
    questions.forEach((q) => {
      const panel = formEl.querySelector(`.vf-q[data-qid="${q.id}"]`);
      if (!panel) return;
      if (isVisible(q, answers)) panel.classList.remove("vf-hidden");
      else panel.classList.add("vf-hidden");
    });
    renderRepeatBlocks();
  }

  function saveDraft() {
    if (state.applyingDraft || !state.questionnaire) return;
    const payload = {
      identity: {
        relation_type: document.getElementById("vfRelationType")?.value || "",
        target_label: document.getElementById("vfTargetLabel")?.value || "",
        verified_identity: state.verifiedIdentity || {},
      },
      answers: collectRawAnswers(),
      updated_at: Date.now(),
    };
    localStorage.setItem(draftKey(), JSON.stringify(payload));
  }

  function restoreDraft() {
    const raw = localStorage.getItem(draftKey());
    if (!raw) return;
    let draft = null;
    try {
      draft = JSON.parse(raw);
    } catch (_err) {
      return;
    }
    if (!draft || typeof draft !== "object") return;
    state.applyingDraft = true;
    const identity = draft.identity || {};
    if (identity.verified_identity && typeof identity.verified_identity === "object") {
      state.verifiedIdentity = { ...identity.verified_identity };
    }
    renderVerifyFields();
    renderIdentity();
    const relationEl = document.getElementById("vfRelationType");
    const targetEl = document.getElementById("vfTargetLabel");
    if (relationEl) relationEl.value = identity.relation_type || "";
    if (targetEl) targetEl.value = identity.target_label || "";

    const answers = draft.answers || {};
    const questions = state.questionnaire?.schema?.questions || [];
    questions.forEach((q) => {
      if (q.repeat_from) return;
      const value = answers[q.id];
      if (value === undefined) return;
      if (q.type === "text" || q.type === "textarea") {
        const el = formEl.querySelector(`[data-id="${q.id}"]`);
        if (el) el.value = value;
      } else if (q.type === "slider") {
        const el = formEl.querySelector(`[data-id="${q.id}"]`);
        if (el) {
          el.value = value;
          const marker = el.nextElementSibling;
          if (marker) marker.textContent = String(value);
        }
      } else if (q.type === "single" || q.type === "rating") {
        const el = formEl.querySelector(`input[name="${q.id}"][value="${value}"]`);
        if (el) el.checked = true;
      } else if (q.type === "multi" && Array.isArray(value)) {
        value.forEach((item) => {
          const el = formEl.querySelector(`input[name="${q.id}"][value="${item}"]`);
          if (el) el.checked = true;
        });
      }
    });

    applyVisibility();
    questions.forEach((q) => {
      if (!q.repeat_from) return;
      const map = answers[q.id];
      if (!map || typeof map !== "object") return;
      Object.entries(map).forEach(([itemKey, itemValue]) => {
        setRepeatItemValue(q, itemKey, itemValue);
      });
    });
    state.applyingDraft = false;
  }

  function applyAnswersSnapshot(rawAnswers) {
    const answers = rawAnswers && typeof rawAnswers === "object" ? rawAnswers : {};
    if (!state.questionnaire || !formEl) return;
    state.liveCheckPaused = true;
    state.applyingDraft = true;
    try {
      renderQuestions();
      applyVisibility();
      const questions = state.questionnaire?.schema?.questions || [];
      questions.forEach((q) => {
        if (q.repeat_from) return;
        const value = answers[q.id];
        if (value === undefined) return;
        if (q.type === "text" || q.type === "textarea") {
          const el = formEl.querySelector(`[data-id="${q.id}"]`);
          if (el) el.value = value;
        } else if (q.type === "slider") {
          const el = formEl.querySelector(`[data-id="${q.id}"]`);
          if (el) {
            el.value = value;
            const marker = el.nextElementSibling;
            if (marker) marker.textContent = String(value);
          }
        } else if (q.type === "single" || q.type === "rating") {
          const el = formEl.querySelector(`input[name="${q.id}"][value="${value}"]`);
          if (el) el.checked = true;
        } else if (q.type === "multi" && Array.isArray(value)) {
          value.forEach((item) => {
            const el = formEl.querySelector(`input[name="${q.id}"][value="${item}"]`);
            if (el) el.checked = true;
          });
        }
      });
      applyVisibility();
      questions.forEach((q) => {
        if (!q.repeat_from) return;
        const map = answers[q.id];
        if (!map || typeof map !== "object") return;
        Object.entries(map).forEach(([itemKey, itemValue]) => {
          setRepeatItemValue(q, itemKey, itemValue);
        });
      });
      applyVisibility();
    } finally {
      state.applyingDraft = false;
      state.liveCheckPaused = false;
    }
  }

  function buildLiveRespondent() {
    return {
      name: String(state.verifiedIdentity?.member_name || "").trim(),
      code: String(state.verifiedIdentity?.member_code || "").trim(),
      identity_data: state.verifiedIdentity || {},
    };
  }

  async function runLiveCheckNow() {
    if (!state.questionnaire || !formEl || state.liveCheckPaused) return;
    if (needVerifyStep() && !state.verifyPassed) return;
    const { answers } = collectAnswers(false);
    const requestId = ++state.liveCheckSeq;
    let data = null;
    let res = null;
    try {
      res = await fetch(`/api/q/${qid}/live-check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answers,
          respondent: buildLiveRespondent(),
        }),
      });
      data = await res.json();
    } catch (_err) {
      return;
    }
    if (requestId !== state.liveCheckSeq) return;
    if (!res || !res.ok || !data || !data.ok) {
      setStatus((data && data.error) || "实时校验失败");
      return;
    }
    const hintList = Array.isArray(data.hints) ? data.hints.filter((x) => String(x || "").trim()) : [];
    if (!data.pass) {
      const msg = Array.isArray(data.rule_errors) && data.rule_errors.length
        ? String(data.rule_errors[0] || "").trim()
        : "联合规则未通过，请调整后继续。";
      showLiveToast(msg || "联合规则未通过");
      setStatus(msg || "联合规则未通过");
      applyAnswersSnapshot(state.lastValidAnswers || {});
      saveDraft();
      return;
    }
    if (hintList.length) {
      setStatus(hintList.slice(0, 2).join("；"));
    } else {
      const currentStatus = String(statusBox?.textContent || "").trim();
      if (currentStatus && (currentStatus.includes("联合规则") || currentStatus.includes("实时校验"))) {
        setStatus("");
      }
    }
    state.lastValidAnswers = JSON.parse(JSON.stringify(answers || {}));
  }

  function scheduleLiveCheck(delay = 160) {
    if (state.liveCheckPaused) return;
    if (state.liveCheckTimer) {
      clearTimeout(state.liveCheckTimer);
      state.liveCheckTimer = null;
    }
    state.liveCheckTimer = setTimeout(() => {
      state.liveCheckTimer = null;
      runLiveCheckNow();
    }, delay);
  }

  function clearDraft() {
    localStorage.removeItem(draftKey());
  }

  function resetAll() {
    document.querySelectorAll("input[type='text'], textarea").forEach((el) => {
      el.value = "";
    });
    document.querySelectorAll("input[type='radio'], input[type='checkbox']").forEach((el) => {
      el.checked = false;
    });
    document.querySelectorAll("input[type='range']").forEach((el) => {
      const min = Number(el.min || 0);
      el.value = String(min);
      const marker = el.nextElementSibling;
      if (marker) marker.textContent = String(min);
    });
    state.authToken = "";
    state.verifiedMember = null;
    state.verifiedIdentity = {};
    state.verifyPassed = !needVerifyStep();
    setStatus("");
    setVerifyStatus("");
    clearDraft();
    applyVisibility();
    state.lastValidAnswers = {};
  }

  function updateVerifyHint() {
    if (!state.questionnaire) return;
    const mode = String(state.questionnaire.auth_mode || "open").trim().toLowerCase();
    const collectFields = getCollectFields();
    if (!verifyHint) return;
    if (mode === "open") {
      if (collectFields.length) verifyHint.textContent = "请先填写以下信息，验证后进入问卷。";
      else verifyHint.textContent = "无需身份验证，可直接填写。";
    } else if (mode === "roster_name_code") {
      verifyHint.textContent = "请填写名单中的编号和姓名进行验证。";
    } else if (mode === "roster_code") {
      verifyHint.textContent = "请填写名单中的编号进行验证。";
    } else {
      verifyHint.textContent = "请填写名单校验字段，验证通过后进入问卷。";
    }
  }

  async function loadSchema() {
    const res = await fetch(`/api/q/${qid}/schema`);
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || "无法加载问卷");
    state.questionnaire = data.questionnaire;
    state.verifyPassed = false;
    state.verifiedMember = null;
    state.verifiedIdentity = {};
    state.authToken = "";
    renderVerifyFields();
    renderIdentity();
    renderQuestions();
    applyVisibility();
    restoreDraft();
    renderIdentity();
    updateVerifyHint();
    state.lastValidAnswers = JSON.parse(JSON.stringify(collectRawAnswers() || {}));

    if (needVerifyStep()) {
      showCard(verifyCard, true);
      showCard(surveyCard, false);
    } else {
      state.verifyPassed = true;
      showCard(verifyCard, false);
      showCard(surveyCard, true);
      scheduleLiveCheck(30);
    }
  }

  async function unlock() {
    const input = document.getElementById("vfPasscodeInput");
    const passcode = input ? input.value.trim() : "";
    if (!passcode) {
      setUnlockStatus("请输入访问口令");
      return;
    }
    setUnlockStatus("验证中...");
    const res = await fetch(`/api/q/${qid}/unlock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passcode }),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      setUnlockStatus(data.error || "口令验证失败");
      return;
    }
    setUnlockStatus("口令通过", true);
    showCard(passcodeCard, false);
    await loadSchema();
  }

  async function verifyIdentity() {
    if (!state.questionnaire) return;
    if (!needVerifyStep()) {
      state.verifyPassed = true;
      showCard(verifyCard, false);
      showCard(surveyCard, true);
      return;
    }
    const identityData = readVerifyIdentityInputs();
    const collectFields = getCollectFields();
    for (const field of collectFields) {
      const key = String(field.key || "").trim();
      const label = String(field.label || "").trim() || key;
      if (!String(identityData[key] || "").trim()) {
        setVerifyStatus(`请填写“${label}”后再验证。`);
        return;
      }
    }
    const memberCode = String(identityData.member_code || "").trim();
    const memberName = String(identityData.member_name || "").trim();
    setVerifyStatus("验证中...");
    const res = await fetch(`/api/q/${qid}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ member_code: memberCode, member_name: memberName, identity_data: identityData }),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      setVerifyStatus(data.error || "身份验证失败");
      return;
    }
    state.authToken = data.auth_token || "";
    state.verifiedMember = data.member || null;
    state.verifiedIdentity = (data.member && data.member.identity_data && typeof data.member.identity_data === "object")
      ? { ...data.member.identity_data }
      : { ...identityData };
    state.verifyPassed = true;
    setVerifyStatus("验证通过", true);
    renderIdentity();
    applyVisibility();
    state.lastValidAnswers = JSON.parse(JSON.stringify(collectRawAnswers() || {}));
    scheduleLiveCheck(20);
    showCard(verifyCard, false);
    showCard(surveyCard, true);
  }

  async function submitSurvey() {
    if (!state.questionnaire) return;
    const { answers, errors } = collectAnswers(true);
    if (errors.length) {
      setStatus(errors.join("；"));
      return;
    }
    if (needVerifyStep() && !state.verifyPassed) {
      setStatus("请先完成进入前验证");
      showCard(surveyCard, false);
      showCard(verifyCard, true);
      return;
    }
    if (state.questionnaire.auth_required && !state.authToken) {
      setStatus("身份会话已失效，请重新验证。");
      state.verifyPassed = false;
      showCard(surveyCard, false);
      showCard(verifyCard, true);
      return;
    }

    const relation_type = (document.getElementById("vfRelationType")?.value || "").trim();
    const target_label = (document.getElementById("vfTargetLabel")?.value || "").trim();
    const respondent = buildLiveRespondent();

    setStatus("提交中...");
    const res = await fetch(`/api/q/${qid}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        answers,
        respondent,
        client_token: randomToken(),
        relation_type,
        target_label,
        auth_token: state.authToken,
      }),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      setStatus(data.error || "提交失败");
      if ((data.error || "").includes("身份会话")) {
        state.authToken = "";
        state.verifyPassed = false;
        showCard(surveyCard, false);
        showCard(verifyCard, true);
      }
      return;
    }
    setStatus(`提交成功，票据编号 ${data.submission_id}`, true);
    clearDraft();
    state.authToken = "";
    state.verifyPassed = false;
    state.lastValidAnswers = {};
    if (needVerifyStep()) {
      showCard(surveyCard, false);
      showCard(verifyCard, true);
      renderVerifyFields();
      updateVerifyHint();
    }
  }

  if (unlockBtn) unlockBtn.addEventListener("click", unlock);
  if (verifyBtn) verifyBtn.addEventListener("click", verifyIdentity);
  if (submitBtn) submitBtn.addEventListener("click", submitSurvey);
  if (resetBtn) resetBtn.addEventListener("click", resetAll);

  if (formEl) {
    formEl.addEventListener("input", () => {
      if (state.liveCheckPaused) return;
      applyVisibility();
      saveDraft();
      scheduleLiveCheck(260);
    });
    formEl.addEventListener("change", () => {
      if (state.liveCheckPaused) return;
      applyVisibility();
      saveDraft();
      scheduleLiveCheck(60);
    });
  }
  if (identityWrap) {
    identityWrap.addEventListener("input", () => {
      applyVisibility();
      saveDraft();
    });
    identityWrap.addEventListener("change", () => {
      applyVisibility();
      saveDraft();
    });
  }

  if (passcodeEnabled && !passcodeUnlocked) {
    showCard(passcodeCard, true);
    showCard(verifyCard, false);
    showCard(surveyCard, false);
  } else {
    showCard(passcodeCard, false);
    loadSchema().catch((err) => setStatus(err.message || String(err)));
  }
})();
