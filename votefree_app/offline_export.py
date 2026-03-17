from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .security import passcode_params
from .survey_engine import normalize_schema


OFFLINE_HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} - VoteFree 离线问卷</title>
  <style>
    :root {{
      --bg: #f3f6fb;
      --panel: #ffffff;
      --text: #1c2434;
      --muted: #5f6b84;
      --primary: #0f6de0;
      --primary-soft: #e8f1ff;
      --line: #d7e1f2;
      --danger: #dc2c5a;
      --ok: #0f9d58;
      --shadow: 0 18px 42px rgba(10, 46, 110, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 5% -10%, #d8e9ff 0, transparent 40%),
        radial-gradient(circle at 100% 0%, #d7f7f0 0, transparent 35%),
        var(--bg);
    }}
    .wrap {{
      max-width: 920px;
      margin: 36px auto 64px;
      padding: 0 20px;
    }}
    .card {{
      background: var(--panel);
      border-radius: 18px;
      box-shadow: var(--shadow);
      border: 1px solid rgba(255, 255, 255, 0.5);
      padding: 26px 28px;
      margin-bottom: 18px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      letter-spacing: .3px;
    }}
    .subtitle {{
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
      font-size: 14px;
      white-space: pre-wrap;
    }}
    .badge {{
      margin-top: 14px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--primary-soft);
      color: #12489c;
      border: 1px solid #cde0ff;
      border-radius: 999px;
      padding: 6px 12px;
      font-size: 12px;
    }}
    .q {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px 16px 14px;
      margin: 14px 0;
    }}
    .q h3 {{
      margin: 0 0 10px;
      font-size: 16px;
    }}
    .req {{ color: var(--danger); margin-left: 6px; }}
    .opt {{ display: block; margin: 8px 0; color: #273145; }}
    input[type="text"], textarea, select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 12px;
      font-size: 14px;
      outline: none;
      transition: border-color .2s ease;
      background: #fff;
    }}
    textarea {{ min-height: 92px; resize: vertical; }}
    input:focus, textarea:focus, select:focus {{ border-color: var(--primary); }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .actions {{ margin-top: 20px; display: flex; gap: 12px; flex-wrap: wrap; }}
    button {{
      border: 0;
      border-radius: 10px;
      cursor: pointer;
      padding: 10px 16px;
      font-weight: 600;
      font-size: 14px;
    }}
    .primary {{
      background: linear-gradient(135deg, #0f6de0, #12489c);
      color: #fff;
      box-shadow: 0 10px 22px rgba(15, 109, 224, 0.28);
    }}
    .ghost {{
      background: #edf3ff;
      color: #21427e;
    }}
    .status {{
      margin-top: 12px;
      font-size: 13px;
      color: var(--muted);
    }}
    .status.err {{ color: var(--danger); }}
    .status.ok {{ color: var(--ok); }}
    .hidden {{ display: none; }}
    @media (max-width: 760px) {{
      .row {{ grid-template-columns: 1fr; }}
      .card {{ padding: 18px; }}
      h1 {{ font-size: 24px; }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="card">
      <h1>{title}</h1>
      <p class="subtitle">{description}</p>
      <span class="badge">离线模式 · 生成 .vote 票据后交管理员归票</span>
    </section>

    <section id="passcodeCard" class="card hidden">
      <h2 style="margin-top:0">访问口令</h2>
      <p class="subtitle">本问卷启用了口令，请输入后继续。</p>
      <input id="passcodeInput" type="text" placeholder="请输入访问口令" />
      <div class="actions">
        <button class="primary" id="unlockBtn">进入问卷</button>
      </div>
      <div id="unlockStatus" class="status"></div>
    </section>

    <section id="verifyCard" class="card hidden">
      <h2 style="margin-top:0">身份验证</h2>
      <p class="subtitle" id="verifyHint">请先通过名单验证后再填写问卷。</p>
      <div id="verifyFields"></div>
      <div class="actions">
        <button class="primary" id="verifyBtn">验证身份</button>
      </div>
      <div id="verifyStatus" class="status"></div>
    </section>

    <section id="formCard" class="card hidden">
      <div id="identityWrap"></div>
      <form id="surveyForm"></form>
      <div class="actions">
        <button class="primary" id="submitBtn" type="button">生成 .vote 票据</button>
        <button class="ghost" id="resetBtn" type="button">清空</button>
      </div>
      <div id="statusBox" class="status"></div>
    </section>
  </main>

<script>
const SURVEY = {survey_json};
const PASSCODE = {passcode_json};
const PUBLIC_KEY_SPKI_B64 = "{public_key_spki_b64}";

const formEl = document.getElementById("surveyForm");
const formCard = document.getElementById("formCard");
const passcodeCard = document.getElementById("passcodeCard");
const verifyCard = document.getElementById("verifyCard");
const statusBox = document.getElementById("statusBox");
const identityWrap = document.getElementById("identityWrap");
const unlockStatus = document.getElementById("unlockStatus");
const verifyStatus = document.getElementById("verifyStatus");
const verifyHint = document.getElementById("verifyHint");
const verifyFields = document.getElementById("verifyFields");
let verifiedMember = null;
let verifiedIdentity = {{}};
let verifyPassed = false;
const repeatRenderSignatures = {{}};
const ROSTER_REPEAT_TOKEN = "__roster_members__";

function bytesToB64(bytes) {{
  let binary = "";
  const arr = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  for (let i = 0; i < arr.length; i++) binary += String.fromCharCode(arr[i]);
  return btoa(binary);
}}
function b64ToBytes(b64) {{
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return arr;
}}
function setStatus(msg, ok=false) {{
  statusBox.textContent = msg;
  statusBox.className = "status " + (ok ? "ok" : "err");
}}
function setUnlock(msg, ok=false) {{
  unlockStatus.textContent = msg;
  unlockStatus.className = "status " + (ok ? "ok" : "err");
}}
function setVerify(msg, ok=false) {{
  verifyStatus.textContent = msg;
  verifyStatus.className = "status " + (ok ? "ok" : "err");
}}
function normalizedRule(rule) {{
  if (!rule || typeof rule !== "object") return null;
  if (Array.isArray(rule.all)) {{
    return {{ all: rule.all.map((x) => normalizedRule(x)).filter(Boolean) }};
  }}
  if (Array.isArray(rule.any)) {{
    return {{ any: rule.any.map((x) => normalizedRule(x)).filter(Boolean) }};
  }}
  if (rule.not) {{
    const n = normalizedRule(rule.not);
    return n ? {{ not: n }} : null;
  }}
  const q = String(rule.question_id || "").trim();
  if (!q) return null;
  if (Object.prototype.hasOwnProperty.call(rule, "equals")) {{
    return {{ question_id: q, op: "equals", value: rule.equals }};
  }}
  if (Object.prototype.hasOwnProperty.call(rule, "contains")) {{
    return {{ question_id: q, op: "contains", value: rule.contains }};
  }}
  return {{ question_id: q, op: String(rule.op || "equals"), value: rule.value }};
}}
function evalRule(rule, answers) {{
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
  if (op === "contains") {{
    if (Array.isArray(actual)) return actual.includes(expected);
    return String(actual || "").includes(String(expected || ""));
  }}
  if (op === "in") return Array.isArray(expected) ? expected.includes(actual) : false;
  if (op === "gt") {{
    const a = Number(actual), b = Number(expected);
    return Number.isFinite(a) && Number.isFinite(b) && a > b;
  }}
  if (op === "gte") {{
    const a = Number(actual), b = Number(expected);
    return Number.isFinite(a) && Number.isFinite(b) && a >= b;
  }}
  if (op === "lt") {{
    const a = Number(actual), b = Number(expected);
    return Number.isFinite(a) && Number.isFinite(b) && a < b;
  }}
  if (op === "lte") {{
    const a = Number(actual), b = Number(expected);
    return Number.isFinite(a) && Number.isFinite(b) && a <= b;
  }}
  if (op === "not_empty") {{
    if (actual === null || actual === undefined) return false;
    if (Array.isArray(actual)) return actual.length > 0;
    if (typeof actual === "object") return Object.keys(actual).length > 0;
    return String(actual).trim().length > 0;
  }}
  if (op === "empty") return !evalRule({{ question_id: normalized.question_id, op: "not_empty" }}, answers);
  return true;
}}
function isVisible(question, answers) {{
  return evalRule(question.visible_if, answers);
}}
function isRequired(question, answers) {{
  if (question?.required_if) return evalRule(question.required_if, answers);
  return !!question?.required;
}}
function randomId(prefix) {{
  const part = (crypto.randomUUID ? crypto.randomUUID().replaceAll("-", "") : Math.random().toString(16).slice(2));
  return prefix + part.slice(0, 14);
}}
function createClientToken() {{
  const key = "votefree_client_token";
  let v = localStorage.getItem(key);
  if (!v) {{
    v = randomId("T");
    localStorage.setItem(key, v);
  }}
  return v;
}}
function normalizeCollectFields(rawList) {{
  if (!Array.isArray(rawList)) return [];
  const out = [];
  const seen = new Set();
  rawList.forEach((item, idx) => {{
    const key = String(item?.key || "").trim() || `field_${{idx + 1}}`;
    if (!key || seen.has(key)) return;
    seen.add(key);
    out.push({{ key, label: String(item?.label || "").trim() || key }});
  }});
  return out;
}}
function getCollectFields() {{
  const identityFields = SURVEY.identity_fields || {{}};
  let fields = normalizeCollectFields(identityFields.collect_fields || []);
  if (!fields.length) {{
    if (identityFields.collect_code) fields.push({{ key: "member_code", label: "编号" }});
    if (identityFields.collect_name) fields.push({{ key: "member_name", label: "姓名" }});
  }}
  const mode = String(SURVEY.auth_mode || "open").trim().toLowerCase();
  if (!fields.length) {{
    if (mode === "roster_name_code") fields = [{{ key: "member_code", label: "编号" }}, {{ key: "member_name", label: "姓名" }}];
    else if (mode === "roster_code") fields = [{{ key: "member_code", label: "编号" }}];
  }}
  return normalizeCollectFields(fields);
}}
function needPreVerify() {{
  return needRosterAuth() || getCollectFields().length > 0;
}}
function verifyInputId(key, index = 0) {{
  const encoded = encodeURIComponent(String(key || ""))
    .replaceAll("%", "_")
    .slice(0, 96);
  return `verify_field_${{index}}_${{encoded}}`;
}}
function repeatItemsSignature(items) {{
  if (!Array.isArray(items) || items.length === 0) return "__empty__";
  return items.map((item) => `${{item.key}}::${{item.label}}::${{item.is_self ? 1 : 0}}`).join("||");
}}
function readVerifyIdentity() {{
  const out = {{}};
  getCollectFields().forEach((field, idx) => {{
    const key = String(field.key || "").trim();
    if (!key) return;
    const id = verifyInputId(key, idx);
    out[key] = String(document.getElementById(id)?.value || "").trim();
  }});
  return out;
}}
function renderVerifyFields() {{
  if (!verifyFields) return;
  const fields = getCollectFields();
  if (!fields.length) {{
    verifyFields.innerHTML = "";
    return;
  }}
  const html = fields.map((field, idx) => {{
    const key = String(field.key || "").trim();
    const label = String(field.label || "").trim() || key;
    const id = verifyInputId(key, idx);
    const value = String(verifiedIdentity?.[key] || "").trim();
    return `
      <div>
        <label class="opt">${{label}} <span class="req">*</span></label>
        <input id="${{id}}" type="text" value="${{value}}" placeholder="请输入${{label}}" />
      </div>
    `;
  }}).join("");
  verifyFields.innerHTML = `<div class="row">${{html}}</div>`;
}}
function renderIdentity() {{
  const fields = getCollectFields();
  let summary = "";
  if (fields.length && verifyPassed) {{
    const rows = fields
      .map((field) => {{
        const key = String(field.key || "").trim();
        const label = String(field.label || "").trim() || key;
        const value = String(verifiedIdentity?.[key] || "").trim();
        if (!value) return "";
        return `<div class="opt"><strong>${{label}}：</strong>${{value}}</div>`;
      }})
      .filter(Boolean)
      .join("");
    if (rows) summary = `<div class="status">已完成进入前身份采集</div>${{rows}}`;
  }}
  identityWrap.innerHTML = `
    <div class="q">
      <h3>答卷信息</h3>
      ${{summary ? `<div style="margin-bottom:8px;">${{summary}}</div>` : ""}}
    </div>
  `;
}}
function repeatItemKey(itemKey) {{
  return encodeURIComponent(String(itemKey));
}}
function repeatItemDecode(encoded) {{
  try {{
    return decodeURIComponent(encoded);
  }} catch (_err) {{
    return encoded;
  }}
}}
function normalizeRepeatSourceItem(item) {{
  if (item && typeof item === "object") {{
    const key = String(item.key ?? item.value ?? item.member_key ?? "").trim();
    if (!key) return null;
    const label = String(item.label ?? item.member_name ?? item.member_code ?? key).trim() || key;
    return {{
      key,
      label,
      member_code: String(item.member_code ?? "").trim(),
      member_name: String(item.member_name ?? "").trim(),
      is_self: !!item.is_self,
    }};
  }}
  const text = String(item || "").trim();
  if (!text) return null;
  return {{ key: text, label: text, member_code: "", member_name: "", is_self: false }};
}}
function getCurrentMemberKey() {{
  const key = String(verifiedMember?.member_key || "").trim();
  if (key) return key;
  const rosterItems = (SURVEY.roster_repeat_items || []).map((item) => normalizeRepeatSourceItem(item)).filter(Boolean);
  const code = String(verifiedIdentity?.member_code || "").trim();
  if (code) {{
    const codeMatches = rosterItems.filter((item) => String(item.member_code || "").trim() === code);
    if (codeMatches.length === 1) return codeMatches[0].key;
  }}
  const name = String(verifiedIdentity?.member_name || "").trim();
  if (name) {{
    const nameMatches = rosterItems.filter((item) => String(item.member_name || "").trim() === name);
    if (nameMatches.length === 1) return nameMatches[0].key;
  }}
  return "";
}}
function applyRepeatFilter(question, items) {{
  const mode = String(question.repeat_filter || "all").trim().toLowerCase();
  if (mode === "all") return items;
  const currentKey = getCurrentMemberKey();
  return items.filter((item) => {{
    const isSelf = !!item.is_self || (currentKey && item.key === currentKey);
    if (mode === "self") return isSelf;
    if (mode === "peer") return !isSelf;
    return true;
  }});
}}
function getRepeatSourceItems(question, answers) {{
  if (!question?.repeat_from) return [];
  if (question.repeat_from === ROSTER_REPEAT_TOKEN) {{
    const normalized = (SURVEY.roster_repeat_items || []).map((item) => normalizeRepeatSourceItem(item)).filter(Boolean);
    return applyRepeatFilter(question, normalized);
  }}
  if (String(question.repeat_from).startsWith("__list__:")) {{
    const listName = String(question.repeat_from).slice("__list__:".length).trim();
    const listObjects = SURVEY?.schema?.meta?.list_objects || [];
    if (!Array.isArray(listObjects) || !listName) return [];
    const target = listObjects.find((x) => String(x?.name || "").trim() === listName);
    if (!target || !Array.isArray(target.items)) return [];
    const normalized = target.items.map((item) => normalizeRepeatSourceItem(item)).filter(Boolean);
    return applyRepeatFilter(question, normalized);
  }}
  const fromAnswer = answers[question.repeat_from];
  if (!Array.isArray(fromAnswer)) return [];
  const normalized = fromAnswer.map((item) => normalizeRepeatSourceItem(item)).filter(Boolean);
  return applyRepeatFilter(question, normalized);
}}
function renderQuestionBody(question, repeatEncoded) {{
  if (question.type === "text") {{
    return `<input type="text" ${{repeatEncoded ? 'data-repeat-input="text"' : `data-id="${{question.id}}"`}} />`;
  }}
  if (question.type === "textarea") {{
    return `<textarea ${{repeatEncoded ? 'data-repeat-input="text"' : `data-id="${{question.id}}"`}}></textarea>`;
  }}
  if (question.type === "single") {{
    const name = repeatEncoded ? `${{question.id}}__${{repeatEncoded}}` : question.id;
    return (question.options || [])
      .map((opt) => `<label class="opt"><input type="radio" name="${{name}}" value="${{opt}}" /> ${{opt}}</label>`)
      .join("");
  }}
  if (question.type === "multi") {{
    const name = repeatEncoded ? `${{question.id}}__${{repeatEncoded}}` : question.id;
    const opts = (question.options || [])
      .map((opt) => `<label class="opt"><input type="checkbox" name="${{name}}" value="${{opt}}" /> ${{opt}}</label>`)
      .join("");
    let tip = "";
    if (question.min_select) tip += `至少选择 ${{question.min_select}} 项`;
    if (question.max_select) tip += `${{tip ? "，" : ""}}最多选择 ${{question.max_select}} 项`;
    const tipHtml = tip ? `<div class="status">${{tip}}</div>` : "";
    return opts + tipHtml;
  }}
  if (question.type === "slider") {{
    const min = Number.isInteger(question.min) ? question.min : 0;
    const max = Number.isInteger(question.max) ? question.max : 100;
    const step = Number.isInteger(question.step) && question.step > 0 ? question.step : 1;
    const markerAttr = repeatEncoded ? `data-repeat-input="slider"` : `data-id="${{question.id}}"`;
    return `
      <div>
        <input type="range" min="${{min}}" max="${{max}}" step="${{step}}" value="${{min}}" ${{markerAttr}}
          oninput="this.nextElementSibling.textContent=this.value" />
        <span class="status" style="display:inline-block;margin-left:8px;">${{min}}</span>
      </div>
    `;
  }}
  if (question.type === "rating") {{
    const min = Number.isInteger(question.min) ? question.min : 1;
    const max = Number.isInteger(question.max) ? question.max : 5;
    const name = repeatEncoded ? `${{question.id}}__${{repeatEncoded}}` : question.id;
    let out = "";
    for (let i = min; i <= max; i++) {{
      out += `<label class="opt"><input type="radio" name="${{name}}" value="${{i}}" /> ${{i}} 分</label>`;
    }}
    return out;
  }}
  return "";
}}
function renderForm() {{
  const questions = SURVEY.schema.questions || [];
  const chunks = [];
  questions.forEach((q) => {{
    const required = q.required ? '<span class="req">*</span>' : "";
    if (q.repeat_from) {{
      chunks.push(`
        <div class="q" data-qid="${{q.id}}" data-repeat-from="${{q.repeat_from}}">
          <h3>${{q.title}}${{required}}</h3>
          <div class="repeat-body"></div>
        </div>
      `);
      return;
    }}
    chunks.push(`<div class="q" data-qid="${{q.id}}"><h3>${{q.title}}${{required}}</h3>${{renderQuestionBody(q, "")}}</div>`);
  }});
  formEl.innerHTML = chunks.join("");
  Object.keys(repeatRenderSignatures).forEach((k) => delete repeatRenderSignatures[k]);
  renderRepeatBlocks();
  applyVisibility();
}}
function getRepeatQuestionValues(question) {{
  const panel = formEl.querySelector(`.q[data-qid="${{question.id}}"]`);
  if (!panel) return {{}};
  const items = Array.from(panel.querySelectorAll(".repeat-item"));
  const map = {{}};
  items.forEach((itemNode) => {{
    const encoded = itemNode.getAttribute("data-item") || "";
    const key = repeatItemDecode(encoded);
    let value = "";
    if (question.type === "text" || question.type === "textarea") {{
      const el = itemNode.querySelector('[data-repeat-input="text"]');
      value = el ? el.value.trim() : "";
    }} else if (question.type === "slider") {{
      const el = itemNode.querySelector('[data-repeat-input="slider"]');
      value = el ? Number(el.value) : "";
    }} else if (question.type === "single" || question.type === "rating") {{
      const el = itemNode.querySelector(`input[name="${{question.id}}__${{encoded}}"]:checked`);
      value = el ? (question.type === "rating" ? Number(el.value) : el.value) : "";
    }} else if (question.type === "multi") {{
      value = Array.from(itemNode.querySelectorAll(`input[name="${{question.id}}__${{encoded}}"]:checked`)).map((n) => n.value);
    }}
    if (value !== "" && (!(Array.isArray(value)) || value.length > 0)) {{
      map[key] = value;
    }}
  }});
  return map;
}}
function setRepeatItemValue(question, itemKey, itemValue) {{
  const encoded = repeatItemKey(itemKey);
  if (question.type === "text" || question.type === "textarea") {{
    const el = formEl.querySelector(`.q[data-qid="${{question.id}}"] .repeat-item[data-item="${{encoded}}"] [data-repeat-input="text"]`);
    if (el) el.value = itemValue ?? "";
    return;
  }}
  if (question.type === "slider") {{
    const el = formEl.querySelector(`.q[data-qid="${{question.id}}"] .repeat-item[data-item="${{encoded}}"] [data-repeat-input="slider"]`);
    if (el) {{
      el.value = Number(itemValue);
      const marker = el.nextElementSibling;
      if (marker) marker.textContent = String(itemValue);
    }}
    return;
  }}
  if (question.type === "single" || question.type === "rating") {{
    const el = formEl.querySelector(`input[name="${{question.id}}__${{encoded}}"][value="${{itemValue}}"]`);
    if (el) el.checked = true;
    return;
  }}
  if (question.type === "multi" && Array.isArray(itemValue)) {{
    itemValue.forEach((opt) => {{
      const el = formEl.querySelector(`input[name="${{question.id}}__${{encoded}}"][value="${{opt}}"]`);
      if (el) el.checked = true;
    }});
  }}
}}
function renderRepeatBlocks() {{
  const questions = SURVEY.schema.questions || [];
  const answers = collectRawAnswers();
  questions.forEach((q) => {{
    if (!q.repeat_from) return;
    const panel = formEl.querySelector(`.q[data-qid="${{q.id}}"]`);
    if (!panel) return;
    const body = panel.querySelector(".repeat-body");
    if (!body) return;
    const sourceItems = getRepeatSourceItems(q, answers);
    const signature = repeatItemsSignature(sourceItems);
    if (!sourceItems.length) {{
      if (repeatRenderSignatures[q.id] === signature) return;
      body.innerHTML = "<div class='status'>暂无可填写的循环对象。</div>";
      repeatRenderSignatures[q.id] = signature;
      return;
    }}
    if (repeatRenderSignatures[q.id] === signature) return;
    const existingValues = getRepeatQuestionValues(q);
    const segments = sourceItems.map((item) => {{
      const encoded = repeatItemKey(item.key);
      return `
        <div class="q repeat-item" style="margin:8px 0;" data-item="${{encoded}}">
          <h3 style="font-size:14px;margin-bottom:8px;">对象：${{item.label}}</h3>
          ${{renderQuestionBody(q, encoded)}}
        </div>
      `;
    }});
    body.innerHTML = segments.join("");
    Object.entries(existingValues).forEach(([itemKey, itemValue]) => {{
      setRepeatItemValue(q, itemKey, itemValue);
    }});
    repeatRenderSignatures[q.id] = signature;
  }});
}}
function applyVisibility() {{
  const questions = SURVEY.schema.questions || [];
  const answers = collectRawAnswers();
  questions.forEach((q) => {{
    const panel = formEl.querySelector(`.q[data-qid="${{q.id}}"]`);
    if (!panel) return;
    if (isVisible(q, answers)) panel.classList.remove("hidden");
    else panel.classList.add("hidden");
  }});
  renderRepeatBlocks();
}}
function getQuestionValue(question) {{
  if (question.repeat_from) return getRepeatQuestionValues(question);
  if (question.type === "text" || question.type === "textarea") {{
    const el = formEl.querySelector(`[data-id="${{question.id}}"]`);
    return el ? el.value.trim() : "";
  }}
  if (question.type === "slider") {{
    const el = formEl.querySelector(`[data-id="${{question.id}}"]`);
    return el ? Number(el.value) : "";
  }}
  if (question.type === "single" || question.type === "rating") {{
    const checked = formEl.querySelector(`input[name="${{question.id}}"]:checked`);
    if (!checked) return "";
    return question.type === "rating" ? Number(checked.value) : checked.value;
  }}
  if (question.type === "multi") {{
    return Array.from(formEl.querySelectorAll(`input[name="${{question.id}}"]:checked`)).map((n) => n.value);
  }}
  return "";
}}
function collectRawAnswers() {{
  const answers = {{}};
  const questions = SURVEY.schema.questions || [];
  questions.forEach((q) => {{
    const panel = formEl.querySelector(`.q[data-qid="${{q.id}}"]`);
    if (panel && panel.classList.contains("hidden")) return;
    const value = getQuestionValue(q);
    if (value === "") return;
    if (Array.isArray(value) && value.length === 0) return;
    if (typeof value === "object" && !Array.isArray(value) && Object.keys(value).length === 0) return;
    answers[q.id] = value;
  }});
  return answers;
}}
function collectAnswers() {{
  const answers = collectRawAnswers();
  const errors = [];
  const questions = SURVEY.schema.questions || [];

  function wordCount(text) {{
    return String(text || "")
      .replaceAll("\\n", " ")
      .split(" ")
      .filter((x) => x.trim().length > 0).length;
  }}

  function validateTextLimits(question, textValue) {{
    const text = String(textValue || "").trim();
    if (!text) return;
    const minLength = Number(question.min_length || 0);
    const maxLength = Number(question.max_length || 0);
    const minWords = Number(question.min_words || 0);
    const maxWords = Number(question.max_words || 0);
    const maxLines = Number(question.max_lines || 0);
    if (minLength > 0 && text.length < minLength) errors.push(`${{question.title}} 至少需要 ${{minLength}} 个字符`);
    if (maxLength > 0 && text.length > maxLength) errors.push(`${{question.title}} 最多允许 ${{maxLength}} 个字符`);
    const wc = wordCount(text);
    if (minWords > 0 && wc < minWords) errors.push(`${{question.title}} 至少需要 ${{minWords}} 个词`);
    if (maxWords > 0 && wc > maxWords) errors.push(`${{question.title}} 最多允许 ${{maxWords}} 个词`);
    if (question.type === "textarea" && maxLines > 0) {{
      const lineCount = text.split("\\n").length;
      if (lineCount > maxLines) errors.push(`${{question.title}} 最多允许 ${{maxLines}} 行`);
    }}
  }}

  function validateNumericValue(question, rawValue, suffix = "") {{
    if (rawValue === undefined || rawValue === null || rawValue === "") return;
    const num = Number(rawValue);
    if (!Number.isFinite(num)) {{
      errors.push(`${{question.title}}${{suffix}} 必须是有效数字`);
      return;
    }}
    const min = Number.isInteger(question.min) ? question.min : 0;
    const max = Number.isInteger(question.max) ? question.max : 100;
    const step = Number.isInteger(question.step) && question.step > 0 ? question.step : 1;
    if (num < min || num > max) {{
      errors.push(`${{question.title}}${{suffix}} 必须在 ${{min}}-${{max}} 范围内`);
      return;
    }}
    if (((num - min) % step) !== 0) {{
      errors.push(`${{question.title}}${{suffix}} 的步进不符合要求`);
    }}
  }}

  questions.forEach((q) => {{
    const panel = formEl.querySelector(`.q[data-qid="${{q.id}}"]`);
    if (panel && panel.classList.contains("hidden")) return;
    const required = isRequired(q, answers);
    const value = answers[q.id];
    const empty =
      value === undefined ||
      value === "" ||
      (Array.isArray(value) && value.length === 0) ||
      (typeof value === "object" && !Array.isArray(value) && Object.keys(value).length === 0);
    if (required && empty) {{
      errors.push(`${{q.title}} 为必填项`);
      return;
    }}
    if (q.type === "multi" && Array.isArray(value) && q.max_select && value.length > q.max_select) {{
      errors.push(`${{q.title}} 最多选择 ${{q.max_select}} 项`);
    }}
    if (q.type === "multi" && Array.isArray(value) && q.min_select && value.length > 0 && value.length < q.min_select) {{
      errors.push(`${{q.title}} 至少选择 ${{q.min_select}} 项`);
    }}
    if ((q.type === "text" || q.type === "textarea") && typeof value === "string") {{
      validateTextLimits(q, value);
    }}
    if (q.type === "rating" || q.type === "slider") {{
      if (q.repeat_from && value && typeof value === "object" && !Array.isArray(value)) {{
        const src = getRepeatSourceItems(q, answers);
        if (src.length > 0) {{
          src.forEach((item) => {{
            if (!Object.prototype.hasOwnProperty.call(value, item.key)) return;
            validateNumericValue(q, value[item.key], `（${{item.label}}）`);
          }});
        }} else {{
          Object.entries(value).forEach(([itemKey, itemValue]) => {{
            validateNumericValue(q, itemValue, `（${{itemKey}}）`);
          }});
        }}
      }} else {{
        validateNumericValue(q, value);
      }}
    }}
    if (q.repeat_from && required) {{
      const src = getRepeatSourceItems(q, answers);
      if (src.length > 0) {{
        const map = value || {{}};
        src.forEach((item) => {{
          if (!Object.prototype.hasOwnProperty.call(map, item.key)) {{
            errors.push(`${{q.title}} 的循环项未完成：${{item.label}}`);
          }}
        }});
        if (q.type === "multi") {{
          src.forEach((item) => {{
            const itemValue = map[item.key];
            if (!Array.isArray(itemValue)) return;
            if (q.max_select && itemValue.length > q.max_select) errors.push(`${{q.title}}（${{item.label}}）最多选择 ${{q.max_select}} 项`);
            if (q.min_select && itemValue.length > 0 && itemValue.length < q.min_select) errors.push(`${{q.title}}（${{item.label}}）至少选择 ${{q.min_select}} 项`);
          }});
        }}
        if (q.type === "text" || q.type === "textarea") {{
          src.forEach((item) => {{
            const itemValue = map[item.key];
            if (typeof itemValue === "string") validateTextLimits(q, itemValue);
          }});
        }}
      }}
    }}
  }});
  return {{answers, errors}};
}}
async function verifyPasscode(passcode) {{
  if (!PASSCODE.enabled) return true;
  const enc = new TextEncoder();
  const keyMat = await crypto.subtle.importKey("raw", enc.encode(passcode), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({{
    name: "PBKDF2",
    hash: "SHA-256",
    salt: b64ToBytes(PASSCODE.salt_b64),
    iterations: PASSCODE.iterations
  }}, keyMat, 256);
  const digest = bytesToB64(new Uint8Array(bits));
  return digest === PASSCODE.digest_b64;
}}
function needRosterAuth() {{
  return SURVEY.auth_mode && SURVEY.auth_mode !== "open";
}}
function verifyRosterIdentity(identityData) {{
  const list = Array.isArray(SURVEY.auth_members) ? SURVEY.auth_members : [];
  const mode = String(SURVEY.auth_mode || "open").trim().toLowerCase();
  if (!list.length) return null;
  if (mode === "roster_name_code") {{
    const vCode = String(identityData.member_code || "").trim();
    const vName = String(identityData.member_name || "").trim();
    if (!vCode || !vName) return null;
    return list.find((m) => String(m.member_code || "").trim() === vCode && String(m.member_name || "").trim() === vName) || null;
  }}
  if (mode === "roster_code") {{
    const vCode = String(identityData.member_code || "").trim();
    if (!vCode) return null;
    return list.find((m) => String(m.member_code || "").trim() === vCode) || null;
  }}
  const collect = getCollectFields();
  if (!collect.length) return null;
  return list.find((member) => {{
    return collect.every((field) => {{
      const key = String(field.key || "").trim();
      if (!key) return true;
      const expected = String(identityData[key] || "").trim();
      if (!expected) return false;
      const actual = String((member.values || {{}})[key] || "").trim();
      return actual === expected;
    }});
  }}) || null;
}}
async function importPublicKey() {{
  return crypto.subtle.importKey(
    "spki",
    b64ToBytes(PUBLIC_KEY_SPKI_B64),
    {{ name: "RSA-OAEP", hash: "SHA-256" }},
    false,
    ["encrypt"]
  );
}}
async function buildEnvelope(payload) {{
  const publicKey = await importPublicKey();
  const aad = new TextEncoder().encode("VoteFree-v1");
  const aesKey = await crypto.subtle.generateKey({{name: "AES-GCM", length: 256}}, true, ["encrypt"]);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const plain = new TextEncoder().encode(JSON.stringify(payload));
  const cipherBuf = await crypto.subtle.encrypt({{name: "AES-GCM", iv, additionalData: aad}}, aesKey, plain);
  const rawAes = await crypto.subtle.exportKey("raw", aesKey);
  const encryptedKey = await crypto.subtle.encrypt({{name: "RSA-OAEP"}}, publicKey, rawAes);
  return {{
    version: 1,
    algorithm: "RSA-OAEP-3072+AES-256-GCM",
    source: "offline_html",
    created_at: new Date().toISOString(),
    aad_b64: bytesToB64(aad),
    encrypted_key_b64: bytesToB64(new Uint8Array(encryptedKey)),
    nonce_b64: bytesToB64(iv),
    ciphertext_b64: bytesToB64(new Uint8Array(cipherBuf)),
  }};
}}
function downloadVoteFile(envelope, submissionId) {{
  const blob = new Blob([JSON.stringify(envelope, null, 2)], {{type: "application/json"}});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${{submissionId}}.vote`;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {{
    URL.revokeObjectURL(a.href);
    a.remove();
  }}, 0);
}}
function resetForm() {{
  document.querySelectorAll("input[type='text'], textarea").forEach((el) => el.value = "");
  document.querySelectorAll("input[type='radio'], input[type='checkbox']").forEach((el) => el.checked = false);
  document.querySelectorAll("input[type='range']").forEach((el) => {{
    el.value = el.min || 0;
    const marker = el.nextElementSibling;
    if (marker) marker.textContent = String(el.value);
  }});
  verifiedMember = null;
  verifiedIdentity = {{}};
  verifyPassed = !needPreVerify();
  applyVisibility();
  setStatus("");
}}
document.getElementById("resetBtn").addEventListener("click", resetForm);
document.getElementById("submitBtn").addEventListener("click", async () => {{
  setStatus("正在加密票据...");
  const {{answers, errors}} = collectAnswers();
  if (errors.length) {{
    setStatus(errors.join("；"));
    return;
  }}
  if (needPreVerify() && !verifyPassed) {{
    setStatus("请先完成进入前验证");
    verifyCard.classList.remove("hidden");
    formCard.classList.add("hidden");
    return;
  }}
  if (needRosterAuth() && !verifiedMember) {{
    setStatus("请先完成身份验证");
    verifyCard.classList.remove("hidden");
    formCard.classList.add("hidden");
    return;
  }}
  let respondent = {{
    name: String(verifiedIdentity.member_name || "").trim(),
    code: String(verifiedIdentity.member_code || "").trim(),
    identity_data: verifiedIdentity || {{}},
    anonymous: false,
    client_token: createClientToken(),
  }};
  const submissionId = randomId("S");
  const payload = {{
    submission_id: submissionId,
    questionnaire_id: SURVEY.id,
    questionnaire_title: SURVEY.title,
    submitted_from: "offline_html",
    identity_mode: SURVEY.identity_mode,
    respondent,
    verified: {{
      roster_id: needRosterAuth() ? SURVEY.auth_roster_id : "",
      member_key: verifiedMember ? String(verifiedMember.member_key || "") : "",
    }},
    context: {{relation_type: "", target_label: ""}},
    answers,
  }};
  try {{
    const envelope = await buildEnvelope(payload);
    downloadVoteFile(envelope, submissionId);
    setStatus("票据已生成，请将 .vote 文件发送给管理员。", true);
  }} catch (err) {{
    setStatus("加密失败：" + err);
  }}
}});
document.getElementById("unlockBtn")?.addEventListener("click", async () => {{
  const code = (document.getElementById("passcodeInput").value || "").trim();
  if (!code) {{
    setUnlock("请输入访问口令");
    return;
  }}
  const ok = await verifyPasscode(code);
  if (!ok) {{
    setUnlock("口令错误，请重试");
    return;
  }}
  setUnlock("口令通过", true);
  passcodeCard.classList.add("hidden");
  if (needPreVerify()) {{
    verifyCard.classList.remove("hidden");
    formCard.classList.add("hidden");
  }} else {{
    verifyPassed = true;
    formCard.classList.remove("hidden");
  }}
}});
document.getElementById("verifyBtn")?.addEventListener("click", () => {{
  const identity = readVerifyIdentity();
  const collect = getCollectFields();
  for (const field of collect) {{
    const key = String(field.key || "").trim();
    const label = String(field.label || "").trim() || key;
    if (!String(identity[key] || "").trim()) {{
      setVerify(`请填写“${{label}}”`);
      return;
    }}
  }}
  let member = null;
  if (needRosterAuth()) {{
    member = verifyRosterIdentity(identity);
  }}
  if (needRosterAuth() && !member) {{
    setVerify("验证失败：不在允许名单中");
    return;
  }}
  verifiedMember = member || {{
    member_key: "",
    member_name: String(identity.member_name || "").trim(),
    member_code: String(identity.member_code || "").trim(),
  }};
  verifiedIdentity = {{ ...identity }};
  if (member && member.values && typeof member.values === "object") {{
    getCollectFields().forEach((field) => {{
      const key = String(field.key || "").trim();
      if (!key) return;
      if (!String(verifiedIdentity[key] || "").trim()) {{
        verifiedIdentity[key] = String(member.values[key] || "").trim();
      }}
    }});
  }}
  verifyPassed = true;
  setVerify("验证通过", true);
  renderIdentity();
  verifyCard.classList.add("hidden");
  formCard.classList.remove("hidden");
  renderRepeatBlocks();
}});

renderVerifyFields();
renderIdentity();
renderForm();
formEl.addEventListener("input", () => applyVisibility());
formEl.addEventListener("change", () => applyVisibility());
identityWrap.addEventListener("input", () => applyVisibility());
identityWrap.addEventListener("change", () => applyVisibility());
if (needRosterAuth()) {{
  if (SURVEY.auth_mode === "roster_name_code") {{
    verifyHint.textContent = "请填写名单中的姓名和编号进行验证。";
  }} else if (SURVEY.auth_mode === "roster_code") {{
    verifyHint.textContent = "请填写名单中的编号进行验证。";
  }} else {{
    verifyHint.textContent = "请填写名单校验字段进行验证。";
  }}
}} else if (getCollectFields().length) {{
  verifyHint.textContent = "请先填写以下信息，验证后进入问卷。";
}}
if (PASSCODE.enabled) {{
  passcodeCard.classList.remove("hidden");
}} else {{
  if (needPreVerify()) {{
    verifyCard.classList.remove("hidden");
  }} else {{
    verifyPassed = true;
    formCard.classList.remove("hidden");
  }}
}}
</script>
</body>
</html>
"""


def render_offline_html(questionnaire: Dict[str, Any], public_key_spki_b64: str) -> str:
    schema = normalize_schema(questionnaire["schema"])
    auth_members: List[Dict[str, Any]] = []
    roster_repeat_items: List[Dict[str, str]] = []
    for member in questionnaire.get("offline_auth_members", []) or []:
        key = str(member.get("member_key", ""))
        code = str(member.get("member_code", ""))
        name = str(member.get("member_name", ""))
        values = member.get("values", {})
        if not isinstance(values, dict):
            values = {}
        if not values:
            extra = member.get("extra", {})
            if isinstance(extra, dict):
                for k, v in extra.items():
                    values[str(k)] = str(v)
            values["member_key"] = key
            if code:
                values["member_code"] = code
            if name:
                values["member_name"] = name
        auth_members.append(
            {
                "member_key": key,
                "member_name": name,
                "member_code": code,
                "values": values,
            }
        )
        if key:
            if code and name:
                label = f"{code} - {name}"
            elif code:
                label = code
            elif name:
                label = name
            else:
                label = key
            roster_repeat_items.append(
                {
                    "key": key,
                    "label": label,
                    "member_code": code,
                    "member_name": name,
                }
            )
    survey = {
        "id": questionnaire["id"],
        "title": questionnaire["title"],
        "description": questionnaire.get("description", ""),
        "identity_mode": questionnaire.get("identity_mode", "realname"),
        "allow_repeat": bool(questionnaire.get("allow_repeat", False)),
        "allow_same_device_repeat": bool(
            (questionnaire.get("identity_fields", {}) or {}).get("allow_same_device_repeat", False)
        ),
        "identity_fields": questionnaire.get("identity_fields", {}),
        "auth_mode": questionnaire.get("auth_mode", "open"),
        "auth_roster_id": questionnaire.get("auth_roster_id", ""),
        "auth_members": auth_members,
        "roster_repeat_items": roster_repeat_items,
        "schema": schema,
    }
    passcode_cfg = passcode_params(questionnaire.get("passcode_hash", ""))
    return OFFLINE_HTML_TEMPLATE.format(
        title=questionnaire["title"],
        description=(questionnaire.get("description", "") or "").replace("{", "&#123;").replace("}", "&#125;"),
        survey_json=json.dumps(survey, ensure_ascii=False),
        passcode_json=json.dumps(passcode_cfg, ensure_ascii=False),
        public_key_spki_b64=public_key_spki_b64,
    )


def export_offline_html(questionnaire: Dict[str, Any], public_key_spki_b64: str, output_path: Path) -> Path:
    html = render_offline_html(questionnaire, public_key_spki_b64)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
