(function () {
  const state = {
    questionnaires: [],
    rosters: [],
    members: [],
    templates: [],
    submissions: [],
    sqlViews: [],
    sqlResults: [],
    summary: {},
    server: {},
    exportsDir: "",
    liveRuleSuffix: "",
    runtimeKernel: "web",
    runtimeKernelNext: "tkinter",
    memberColumns: [],
    selectedListName: "",
    selectedRuleIndex: -1,
    logicTarget: null,
    selected: {
      questionnaireId: "",
      rosterId: "",
      memberId: "",
      submissionId: "",
    },
    draft: null,
  };

  const tabButtons = Array.from(document.querySelectorAll(".as-tab"));
  const tabPanels = Array.from(document.querySelectorAll(".as-tab-panel"));
  const authCard = document.getElementById("authCard");
  const mainSection = document.getElementById("mainSection");
  const authTitle = document.getElementById("authTitle");
  const authStatus = document.getElementById("authStatus");
  const passwordInput = document.getElementById("passwordInput");
  const initBtn = document.getElementById("initBtn");
  const unlockBtn = document.getElementById("unlockBtn");
  const toastEl = document.getElementById("toast");

  const topRefreshBtn = document.getElementById("topRefreshBtn");

  const guideStatus = document.getElementById("guideStatus");
  const guideRefreshBtn = document.getElementById("guideRefreshBtn");
  const quickRosterBtn = document.getElementById("quickRosterBtn");
  const quickTplSatBtn = document.getElementById("quickTplSatBtn");
  const quickTplEvalBtn = document.getElementById("quickTplEvalBtn");
  const dashboardText = document.getElementById("dashboardText");
  const statQuestionnaires = document.getElementById("statQuestionnaires");
  const statSubmissions = document.getElementById("statSubmissions");
  const statRosters = document.getElementById("statRosters");
  const statServer = document.getElementById("statServer");

  const questionnaireRows = document.getElementById("questionnaireRows");
  const selectedQuestionnaire = document.getElementById("selectedQuestionnaire");
  const qOpenBtn = document.getElementById("qOpenBtn");
  const qActiveBtn = document.getElementById("qActiveBtn");
  const qPauseBtn = document.getElementById("qPauseBtn");
  const qRefreshBtn = document.getElementById("qRefreshBtn");
  const qRenameBtn = document.getElementById("qRenameBtn");
  const qCopyBtn = document.getElementById("qCopyBtn");
  const qDeleteBtn = document.getElementById("qDeleteBtn");
  const qDesignerBtn = document.getElementById("qDesignerBtn");
  const qOpenListModalBtn = document.getElementById("qOpenListModalBtn");
  const qOpenEditorModalBtn = document.getElementById("qOpenEditorModalBtn");
  const qManageListPanel = document.getElementById("qManageListPanel");
  const qManageEditorPanel = document.getElementById("qManageEditorPanel");
  const qListAreaCloseBtn = document.getElementById("qListAreaCloseBtn");
  const qEditorAreaCloseBtn = document.getElementById("qEditorAreaCloseBtn");
  const qDraftTitle = document.getElementById("qDraftTitle");
  const qDraftPasscode = document.getElementById("qDraftPasscode");
  const qDraftAuthMode = document.getElementById("qDraftAuthMode");
  const qDraftRoster = document.getElementById("qDraftRoster");
  const qDraftDesc = document.getElementById("qDraftDesc");
  const qDraftIntro = document.getElementById("qDraftIntro");
  const qDraftCollectFields = document.getElementById("qDraftCollectFields");
  const qCollectConfigBtn = document.getElementById("qCollectConfigBtn");
  const qCollectFromRosterBtn = document.getElementById("qCollectFromRosterBtn");
  const qCollectClearBtn = document.getElementById("qCollectClearBtn");
  const qDraftAllowRepeat = document.getElementById("qDraftAllowRepeat");
  const qDraftAllowSameDevice = document.getElementById("qDraftAllowSameDevice");
  const qTemplateSelect = document.getElementById("qTemplateSelect");
  const qTemplateApplyBtn = document.getElementById("qTemplateApplyBtn");
  const qTemplateCreateBtn = document.getElementById("qTemplateCreateBtn");
  const qListManageBtn = document.getElementById("qListManageBtn");
  const qRuleManageBtn = document.getElementById("qRuleManageBtn");
  const qLogicManageBtn = document.getElementById("qLogicManageBtn");
  const qCheckPanelBtn = document.getElementById("qCheckPanelBtn");
  const qCheckDraftBtn = document.getElementById("qCheckDraftBtn");
  const qRefreshBoardBtn = document.getElementById("qRefreshBoardBtn");
  const qNewDraftBtn = document.getElementById("qNewDraftBtn");
  const qLoadDraftBtn = document.getElementById("qLoadDraftBtn");
  const qAddQuestionBtn = document.getElementById("qAddQuestionBtn");
  const qAddLoopBtn = document.getElementById("qAddLoopBtn");
  const qSaveDraftBtn = document.getElementById("qSaveDraftBtn");
  const qBoardCanvas = document.getElementById("qBoardCanvas");
  const qLogicTarget = document.getElementById("qLogicTarget");
  const qLogicSourceQid = document.getElementById("qLogicSourceQid");
  const qLogicOp = document.getElementById("qLogicOp");
  const qLogicValue = document.getElementById("qLogicValue");
  const qLogicRepeatFilter = document.getElementById("qLogicRepeatFilter");
  const qLogicWriteVisibleBtn = document.getElementById("qLogicWriteVisibleBtn");
  const qLogicWriteRequiredBtn = document.getElementById("qLogicWriteRequiredBtn");
  const qLogicSaveBtn = document.getElementById("qLogicSaveBtn");
  const qLogicClearBtn = document.getElementById("qLogicClearBtn");
  const qLogicVisiblePreview = document.getElementById("qLogicVisiblePreview");
  const qLogicRequiredPreview = document.getElementById("qLogicRequiredPreview");
  const qCheckOutput = document.getElementById("qCheckOutput");
  const qListPanel = document.getElementById("qListPanel");
  const qLogicPanel = document.getElementById("qLogicPanel");
  const qCheckPanel = document.getElementById("qCheckPanel");
  const qListRows = document.getElementById("qListRows");
  const qListName = document.getElementById("qListName");
  const qListType = document.getElementById("qListType");
  const qListItems = document.getElementById("qListItems");
  const qListNewBtn = document.getElementById("qListNewBtn");
  const qListSaveBtn = document.getElementById("qListSaveBtn");
  const qListDeleteBtn = document.getElementById("qListDeleteBtn");
  const qListImportRosterBtn = document.getElementById("qListImportRosterBtn");
  const qListCloseBtn = document.getElementById("qListCloseBtn");
  const qListCloseTopBtn = document.getElementById("qListCloseTopBtn");
  const qRulePanel = document.getElementById("qRulePanel");
  const qRuleSchemaText = document.getElementById("qRuleSchemaText");
  const qModalBackdrop = document.getElementById("qModalBackdrop");
  const qRuleSuffix = document.getElementById("qRuleSuffix");
  const qRuleRows = document.getElementById("qRuleRows");
  const qRuleName = document.getElementById("qRuleName");
  const qRuleSql = document.getElementById("qRuleSql");
  const qRuleOp = document.getElementById("qRuleOp");
  const qRuleValue = document.getElementById("qRuleValue");
  const qRuleMessage = document.getElementById("qRuleMessage");
  const qRuleNewBtn = document.getElementById("qRuleNewBtn");
  const qRuleSaveBtn = document.getElementById("qRuleSaveBtn");
  const qRuleDeleteBtn = document.getElementById("qRuleDeleteBtn");
  const qRuleUpBtn = document.getElementById("qRuleUpBtn");
  const qRuleDownBtn = document.getElementById("qRuleDownBtn");
  const qRuleCloseBtn = document.getElementById("qRuleCloseBtn");
  const qRuleCloseTopBtn = document.getElementById("qRuleCloseTopBtn");
  const qRuleSampleAvgBtn = document.getElementById("qRuleSampleAvgBtn");
  const qRuleSampleCountBtn = document.getElementById("qRuleSampleCountBtn");
  const qRuleSampleJoinBtn = document.getElementById("qRuleSampleJoinBtn");
  const qRuleSampleRangeBtn = document.getElementById("qRuleSampleRangeBtn");
  const qLogicCloseBtn = document.getElementById("qLogicCloseBtn");
  const qCheckCloseBtn = document.getElementById("qCheckCloseBtn");
  const qDraftStatus = document.getElementById("qDraftStatus");
  const qErrorPanel = document.getElementById("qErrorPanel");
  const qErrorTitle = document.getElementById("qErrorTitle");
  const qErrorText = document.getElementById("qErrorText");
  const qErrorCloseBtn = document.getElementById("qErrorCloseBtn");

  const rosterRows = document.getElementById("rosterRows");
  const selectedRoster = document.getElementById("selectedRoster");
  const memberRows = document.getElementById("memberRows");
  const memberHeadRow = document.getElementById("memberHeadRow");
  const rCreateBtn = document.getElementById("rCreateBtn");
  const rRefreshBtn = document.getElementById("rRefreshBtn");
  const rColumnsBtn = document.getElementById("rColumnsBtn");
  const rRenameBtn = document.getElementById("rRenameBtn");
  const rCopyBtn = document.getElementById("rCopyBtn");
  const rDeleteBtn = document.getElementById("rDeleteBtn");
  const mAddBtn = document.getElementById("mAddBtn");
  const mRemoveBtn = document.getElementById("mRemoveBtn");
  const mRefreshBtn = document.getElementById("mRefreshBtn");
  const rImportBtn = document.getElementById("rImportBtn");
  const rosterImportFile = document.getElementById("rosterImportFile");
  const rosterReplaceAll = document.getElementById("rosterReplaceAll");

  const serverHost = document.getElementById("serverHost");
  const serverPort = document.getElementById("serverPort");
  const serverQ = document.getElementById("serverQ");
  const serverStartBtn = document.getElementById("serverStartBtn");
  const serverStopBtn = document.getElementById("serverStopBtn");
  const serverOpenHomeBtn = document.getElementById("serverOpenHomeBtn");
  const serverOpenQBtn = document.getElementById("serverOpenQBtn");
  const serverRefreshBtn = document.getElementById("serverRefreshBtn");
  const serverCopyLinkBtn = document.getElementById("serverCopyLinkBtn");
  const serverInfo = document.getElementById("serverInfo");
  const serverQr = document.getElementById("serverQr");

  const offlineQ = document.getElementById("offlineQ");
  const offlinePath = document.getElementById("offlinePath");
  const offlineChoosePathBtn = document.getElementById("offlineChoosePathBtn");
  const offlineExportBtn = document.getElementById("offlineExportBtn");
  const offlineOpenDirBtn = document.getElementById("offlineOpenDirBtn");
  const offlineLog = document.getElementById("offlineLog");

  const votesQ = document.getElementById("votesQ");
  const submissionRows = document.getElementById("submissionRows");
  const subRefreshBtn = document.getElementById("subRefreshBtn");
  const subRejectBtn = document.getElementById("subRejectBtn");
  const voteImportFile = document.getElementById("voteImportFile");
  const voteImportBtn = document.getElementById("voteImportBtn");
  const sqlSchemaBtn = document.getElementById("sqlSchemaBtn");
  const sqlSchemaText = document.getElementById("sqlSchemaText");
  const sqlViewSelect = document.getElementById("sqlViewSelect");
  const sqlLoadViewBtn = document.getElementById("sqlLoadViewBtn");
  const sqlDeleteViewBtn = document.getElementById("sqlDeleteViewBtn");
  const sqlEditor = document.getElementById("sqlEditor");
  const sqlRunBtn = document.getElementById("sqlRunBtn");
  const sqlSaveViewBtn = document.getElementById("sqlSaveViewBtn");
  const payloadPreviewBtn = document.getElementById("payloadPreviewBtn");
  const sqlExportPath = document.getElementById("sqlExportPath");
  const sqlExportBtn = document.getElementById("sqlExportBtn");
  const sqlConsole = document.getElementById("sqlConsole");

  const oldPwd = document.getElementById("oldPwd");
  const newPwd = document.getElementById("newPwd");
  const newPwd2 = document.getElementById("newPwd2");
  const changePwdBtn = document.getElementById("changePwdBtn");
  const backupPath = document.getElementById("backupPath");
  const backupBtn = document.getElementById("backupBtn");
  const darkModeToggle = document.getElementById("darkModeToggle");
  const runtimeKernelText = document.getElementById("runtimeKernelText");
  const switchKernelBtn = document.getElementById("switchKernelBtn");
  const darkModeStorageKey = "votefree_dark_mode";

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function parseRosterColumnsText(raw) {
    const tokens = String(raw || "")
      .replace(/，/g, ",")
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
    const labels = tokens.length ? tokens : ["姓名", "编号"];
    const seen = new Set();
    const cols = [];
    labels.forEach((label, idx) => {
      let key = String(label).replace(/\s+/g, "_").replace(/-/g, "_");
      if (key === "姓名" || key.toLowerCase() === "name") key = "member_name";
      if (["编号", "工号", "学号", "code"].includes(key) || key.toLowerCase() === "code") key = "member_code";
      if (seen.has(key)) key = `${key}_${idx + 1}`;
      seen.add(key);
      cols.push({ key, label, is_key: false });
    });
    const codeIdx = cols.findIndex((c) => c.key === "member_code");
    const target = codeIdx >= 0 ? codeIdx : 0;
    if (cols[target]) cols[target].is_key = true;
    return cols;
  }

  function prettyAuthMode(mode) {
    const m = String(mode || "").trim();
    if (m === "open") return "开放";
    if (m === "roster_code") return "名单编号";
    if (m === "roster_name_code") return "姓名+编号";
    if (m === "roster_fields") return "自定义字段";
    return m || "-";
  }

  function newId(prefix) {
    return `${prefix}_${Math.random().toString(16).slice(2, 10)}`;
  }

  function defaultQuestion(inLoop = false) {
    const q = {
      id: newId("q"),
      title: "请填写题目",
      type: "single",
      required: true,
      options: ["选项1", "选项2"],
      min_select: 1,
      max_select: 2,
      min: 1,
      max: 5,
      step: 1,
      min_length: 0,
      max_length: 0,
      min_words: 0,
      max_words: 0,
      max_lines: 0,
      visible_if: null,
      required_if: null,
      repeat_filter: "all",
      repeat_from: "",
    };
    if (!inLoop) delete q.repeat_filter;
    return q;
  }

  function defaultLoopBlock() {
    return {
      kind: "loop",
      block_id: newId("b"),
      title: "循环块",
      repeat_from: "",
      visible_if: null,
      inner_questions: [defaultQuestion(true)],
    };
  }

  function defaultDraft() {
    return {
      questionnaire_id: "",
      title: "",
      description: "",
      intro: "",
      passcode: "",
      auth_mode: "open",
      auth_roster_id: "",
      allow_repeat: false,
      allow_same_device_repeat: false,
      collect_fields: [],
      list_objects: [],
      validation_rules: [],
      template_meta: {},
      items: [
        {
          kind: "question",
          block_id: newId("b"),
          question: defaultQuestion(false),
          visible_if: null,
        },
      ],
      meta_extra: {},
    };
  }

  function cloneObj(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function safeObj(value) {
    return value && typeof value === "object" ? value : {};
  }

  function simpleRuleFromInputs() {
    const source = String(qLogicSourceQid.value || "").trim();
    if (!source) return null;
    const op = String(qLogicOp.value || "equals").trim() || "equals";
    const vRaw = String(qLogicValue.value || "");
    let value = vRaw;
    if (["gt", "gte", "lt", "lte"].includes(op)) {
      const n = Number(vRaw);
      value = Number.isFinite(n) ? n : vRaw;
    }
    if (op === "empty" || op === "not_empty") value = "";
    return { question_id: source, op, value };
  }

  function stringifyRule(rule) {
    if (!rule || typeof rule !== "object") return "";
    return JSON.stringify(rule, null, 2);
  }

  function parseRuleFromText(text) {
    const t = String(text || "").trim();
    if (!t) return null;
    try {
      const obj = JSON.parse(t);
      if (!obj || typeof obj !== "object") return null;
      return obj;
    } catch (_) {
      return null;
    }
  }

  function andRules(left, right) {
    const l = left && typeof left === "object" ? left : null;
    const r = right && typeof right === "object" ? right : null;
    if (l && r) return { all: [l, r] };
    return l || r;
  }

  function collectFieldsToText(fields) {
    if (!Array.isArray(fields)) return "";
    return fields.map((x) => String((x && x.label) || (x && x.key) || "").trim()).filter(Boolean).join(",");
  }

  function textToCollectFields(text) {
    return parseRosterColumnsText(text).map((x) => ({ key: x.key, label: x.label }));
  }

  function fillDraftForm() {
    const d = state.draft || defaultDraft();
    qDraftTitle.value = d.title || "";
    qDraftDesc.value = d.description || "";
    qDraftIntro.value = d.intro || "";
    qDraftPasscode.value = d.passcode || "";
    qDraftAuthMode.value = d.auth_mode || "open";
    qDraftRoster.value = d.auth_roster_id || "";
    qDraftAllowRepeat.checked = !!d.allow_repeat;
    qDraftAllowSameDevice.checked = !!d.allow_same_device_repeat;
    qDraftCollectFields.value = collectFieldsToText(d.collect_fields || []);
    const itemCount = asArray(d.items).length;
    const listCount = asArray(d.list_objects).length;
    const ruleCount = asArray(d.validation_rules).length;
    qDraftStatus.textContent = `${d.questionnaire_id ? `当前编辑：${d.questionnaire_id}` : "当前编辑：新建问卷"}\n题目块：${itemCount}，列表：${listCount}，联合规则：${ruleCount}`;
  }

  function pullDraftForm() {
    if (!state.draft) state.draft = defaultDraft();
    const d = state.draft;
    d.title = String(qDraftTitle.value || "").trim();
    d.description = String(qDraftDesc.value || "").trim();
    d.intro = String(qDraftIntro.value || "").trim();
    d.passcode = String(qDraftPasscode.value || "").trim();
    d.auth_mode = String(qDraftAuthMode.value || "open").trim() || "open";
    d.auth_roster_id = String(qDraftRoster.value || "").trim();
    d.allow_repeat = !!qDraftAllowRepeat.checked;
    d.allow_same_device_repeat = !!qDraftAllowSameDevice.checked;
    d.collect_fields = textToCollectFields(qDraftCollectFields.value || "");
  }

  function ensureDraftShape() {
    if (!state.draft || typeof state.draft !== "object") state.draft = defaultDraft();
    const d = state.draft;
    if (!Array.isArray(d.items)) d.items = defaultDraft().items;
    if (!Array.isArray(d.collect_fields)) d.collect_fields = [];
    if (!Array.isArray(d.list_objects)) d.list_objects = [];
    if (!Array.isArray(d.validation_rules)) d.validation_rules = [];
    if (!d.template_meta || typeof d.template_meta !== "object") d.template_meta = {};
    if (!d.meta_extra || typeof d.meta_extra !== "object") d.meta_extra = {};
  }

  function convertSchemaToItems(schema) {
    const meta = (schema && schema.meta) || {};
    const boardV2 = (meta && meta.board_v2) || {};
    if (Array.isArray(boardV2.items) && boardV2.items.length) {
      return cloneObj(boardV2.items);
    }
    const out = [];
    const loopMap = {};
    const questions = Array.isArray(schema.questions) ? schema.questions : [];
    questions.forEach((q) => {
      const repeatFrom = String(q.repeat_from || "").trim();
      if (repeatFrom) {
        if (!loopMap[repeatFrom]) {
          loopMap[repeatFrom] = {
            kind: "loop",
            block_id: newId("b"),
            title: "循环块",
            repeat_from: repeatFrom,
            visible_if: null,
            inner_questions: [],
          };
          out.push(loopMap[repeatFrom]);
        }
        loopMap[repeatFrom].inner_questions.push(cloneObj(q));
      } else {
        out.push({
          kind: "question",
          block_id: newId("b"),
          question: cloneObj(q),
          visible_if: null,
        });
      }
    });
    if (!out.length) {
      out.push({ kind: "question", block_id: newId("b"), question: defaultQuestion(false), visible_if: null });
    }
    return out;
  }

  function extractTemplateMeta(meta) {
    const m = safeObj(meta);
    const out = {};
    Object.keys(m).forEach((k) => {
      if (String(k).startsWith("template_")) out[k] = cloneObj(m[k]);
    });
    return out;
  }

  function normalizeListObjects(raw) {
    const out = [];
    asArray(raw).forEach((obj) => {
      if (!obj || typeof obj !== "object") return;
      const name = String(obj.name || "").trim();
      if (!name) return;
      const type = String(obj.type || "text").trim() || "text";
      const source = String(obj.source || "manual").trim() || "manual";
      const readonly = !!obj.readonly;
      const items = [];
      asArray(obj.items).forEach((it) => {
        if (it && typeof it === "object") {
          const key = String(it.key || it.value || "").trim();
          const label = String(it.label || key).trim() || key;
          if (key) items.push({ key, label });
          return;
        }
        const key2 = String(it || "").trim();
        if (key2) items.push({ key: key2, label: key2 });
      });
      out.push({ name, type, source, readonly, items });
    });
    return out;
  }

  function normalizeValidationRules(raw) {
    const out = [];
    asArray(raw).forEach((rule, idx) => {
      if (!rule || typeof rule !== "object") return;
      const name = String(rule.name || `联合规则#${idx + 1}`).trim() || `联合规则#${idx + 1}`;
      const sql = String(rule.sql || "").trim();
      if (!sql) return;
      const op = String(rule.op || "lte").trim() || "lte";
      const value = String(rule.value ?? "").trim();
      const value2 = String(rule.value2 ?? "").trim();
      const message = String(rule.message || `${name} 未通过。`).trim() || `${name} 未通过。`;
      out.push({ type: "sql_aggregate", name, sql, op, value, value2, message });
    });
    return out;
  }

  function loadQuestionnaireToDraft(q) {
    const draft = defaultDraft();
    draft.questionnaire_id = String(q.id || "").trim();
    draft.title = String(q.title || "").trim();
    draft.description = String(q.description || "").trim();
    const schema = (q.schema && typeof q.schema === "object") ? q.schema : {};
    draft.intro = String(schema.intro || "").trim();
    draft.auth_mode = String(q.auth_mode || "open").trim() || "open";
    draft.auth_roster_id = String(q.auth_roster_id || "").trim();
    draft.allow_repeat = !!q.allow_repeat;
    const fields = (q.identity_fields && typeof q.identity_fields === "object") ? q.identity_fields : {};
    draft.allow_same_device_repeat = !!fields.allow_same_device_repeat;
    draft.collect_fields = Array.isArray(fields.collect_fields) ? cloneObj(fields.collect_fields) : [];
    draft.items = convertSchemaToItems(schema);
    draft.template_meta = extractTemplateMeta(schema.meta || {});
    draft.list_objects = normalizeListObjects((schema.meta && schema.meta.list_objects) || []);
    draft.validation_rules = normalizeValidationRules((schema.meta && schema.meta.validation_rules) || []);
    draft.meta_extra = (schema.meta && typeof schema.meta === "object") ? cloneObj(schema.meta) : {};
    state.draft = draft;
    state.logicTarget = null;
    state.selectedListName = "";
    state.selectedRuleIndex = -1;
    fillDraftForm();
    renderDraftBoard();
    renderListRows();
    renderRuleRows();
    renderLogicPanel();
  }

  function boardRepeatSourceChoices() {
    const d = state.draft || defaultDraft();
    const seen = new Set();
    const choices = [];
    const pushChoice = (label, value) => {
      const v = String(value || "").trim();
      if (!v || seen.has(v)) return;
      seen.add(v);
      choices.push({ label: String(label || v).trim() || v, value: v });
    };
    normalizeListObjects(d.list_objects || []).forEach((obj) => {
      const name = String(obj.name || "").trim();
      if (!name) return;
      pushChoice(`列表：${name}`, `__list__:${name}`);
    });
    const pushMultiQuestion = (q) => {
      if (!q || typeof q !== "object") return;
      if (String(q.type || "").trim() !== "multi") return;
      const qid = String(q.id || "").trim();
      if (!qid) return;
      pushChoice(`题目：${qid}（多选结果）`, qid);
    };
    asArray(d.items).forEach((item) => {
      if (item && item.kind === "question") pushMultiQuestion(item.question || {});
      if (item && item.kind === "loop") asArray(item.inner_questions).forEach((q) => pushMultiQuestion(q));
    });
    return choices;
  }

  function questionCardHtml(prefix, q, inLoop) {
    const optionsText = Array.isArray(q.options) ? q.options.join(",") : "";
    const qType = String(q.type || "single").trim() || "single";
    const repeatField = inLoop
      ? `
        <div>
          <label class="as-label">循环筛选</label>
          <select class="as-input" data-k="${prefix}:repeat_filter">
            <option value="all" ${q.repeat_filter === "all" ? "selected" : ""}>全部</option>
            <option value="self" ${q.repeat_filter === "self" ? "selected" : ""}>仅本人</option>
            <option value="peer" ${q.repeat_filter === "peer" ? "selected" : ""}>仅他人</option>
          </select>
        </div>`
      : `
        <div>
          <label class="as-label">所属块</label>
          <input class="as-input" value="普通题（不循环）" disabled />
        </div>`;

    let detailFields = "";
    if (qType === "single") {
      detailFields = `
        <div>
          <label class="as-label">选项（逗号分隔）</label>
          <input class="as-input" data-k="${prefix}:options" value="${esc(optionsText)}" />
        </div>`;
    } else if (qType === "multi") {
      detailFields = `
        <div>
          <label class="as-label">选项（逗号分隔）</label>
          <input class="as-input" data-k="${prefix}:options" value="${esc(optionsText)}" />
        </div>
        <div>
          <label class="as-label">最少选择数</label>
          <input class="as-input" data-k="${prefix}:min_select" value="${esc(q.min_select ?? 1)}" />
        </div>
        <div>
          <label class="as-label">最多选择数</label>
          <input class="as-input" data-k="${prefix}:max_select" value="${esc(q.max_select ?? 2)}" />
        </div>`;
    } else if (qType === "rating" || qType === "slider") {
      detailFields = `
        <div>
          <label class="as-label">最小值</label>
          <input class="as-input" data-k="${prefix}:min" value="${esc(q.min ?? 1)}" />
        </div>
        <div>
          <label class="as-label">最大值</label>
          <input class="as-input" data-k="${prefix}:max" value="${esc(q.max ?? 5)}" />
        </div>
        <div>
          <label class="as-label">步进值</label>
          <input class="as-input" data-k="${prefix}:step" value="${esc(q.step ?? 1)}" />
        </div>`;
    } else if (qType === "text") {
      detailFields = `
        <div>
          <label class="as-label">最少字数</label>
          <input class="as-input" data-k="${prefix}:min_length" value="${esc(q.min_length ?? 0)}" />
        </div>
        <div>
          <label class="as-label">最多字数</label>
          <input class="as-input" data-k="${prefix}:max_length" value="${esc(q.max_length ?? 0)}" />
        </div>`;
    } else if (qType === "textarea") {
      detailFields = `
        <div>
          <label class="as-label">最少字数</label>
          <input class="as-input" data-k="${prefix}:min_words" value="${esc(q.min_words ?? 0)}" />
        </div>
        <div>
          <label class="as-label">最多字数</label>
          <input class="as-input" data-k="${prefix}:max_words" value="${esc(q.max_words ?? 0)}" />
        </div>
        <div>
          <label class="as-label">最多行数</label>
          <input class="as-input" data-k="${prefix}:max_lines" value="${esc(q.max_lines ?? 0)}" />
        </div>`;
    }
    return `
<div class="as-question-card">
  <div class="as-grid-4">
    <div>
      <label class="as-label">题目ID</label>
      <input class="as-input" data-k="${prefix}:id" value="${esc(q.id || "")}" />
    </div>
    <div>
      <label class="as-label">题目标题</label>
      <input class="as-input" data-k="${prefix}:title" value="${esc(q.title || "")}" />
    </div>
    <div>
      <label class="as-label">题型</label>
      <select class="as-input" data-k="${prefix}:type">
        <option value="single" ${q.type === "single" ? "selected" : ""}>单选</option>
        <option value="multi" ${q.type === "multi" ? "selected" : ""}>多选</option>
        <option value="rating" ${q.type === "rating" ? "selected" : ""}>评分</option>
        <option value="slider" ${q.type === "slider" ? "selected" : ""}>滑杆</option>
        <option value="text" ${q.type === "text" ? "selected" : ""}>单行文本</option>
        <option value="textarea" ${q.type === "textarea" ? "selected" : ""}>多行文本</option>
      </select>
    </div>
    <div class="as-actions as-end">
      <label class="as-inline">
        <input type="checkbox" data-k="${prefix}:required" ${q.required ? "checked" : ""}/> 必填
      </label>
    </div>
  </div>
  <div class="as-grid-4 as-mt8">
    ${repeatField}
    ${detailFields}
  </div>
</div>`;
  }

  function renderDraftBoard() {
    if (!qBoardCanvas) return;
    if (!state.draft) state.draft = defaultDraft();
    const d = state.draft;
    const html = [];
    const repeatSourceChoices = boardRepeatSourceChoices();
    (d.items || []).forEach((item, i) => {
      if (item.kind === "loop") {
        let currentRepeatFrom = String(item.repeat_from || "").trim();
        if ((!currentRepeatFrom || currentRepeatFrom === "__roster_members__") && repeatSourceChoices.length) {
          currentRepeatFrom = String(repeatSourceChoices[0].value || "").trim();
          item.repeat_from = currentRepeatFrom;
        }
        let repeatOptions = repeatSourceChoices.map((opt) => {
          const selected = opt.value === currentRepeatFrom ? "selected" : "";
          return `<option value="${esc(opt.value)}" ${selected}>${esc(opt.label)}</option>`;
        });
        if (!repeatOptions.length || !repeatSourceChoices.some((opt) => opt.value === currentRepeatFrom)) {
          repeatOptions.push(`<option value="${esc(currentRepeatFrom)}" selected>自定义：${esc(currentRepeatFrom)}</option>`);
        }
        html.push(`<div class="as-block"><div class="as-block-head"><p class="as-block-title">${i + 1}. 循环块</p><div class="as-actions"><button class="as-btn" data-op="b-logic" data-i="${i}">逻辑</button><button class="as-btn" data-op="b-up" data-i="${i}">上移</button><button class="as-btn" data-op="b-down" data-i="${i}">下移</button><button class="as-btn" data-op="b-copy" data-i="${i}">复制</button><button class="as-btn" data-op="b-del" data-i="${i}">删除</button></div></div><div class="as-grid-2"><div><label class="as-label">块标题</label><input class="as-input" data-k="b:${i}:title" value="${esc(item.title || "循环块")}" /></div><div><label class="as-label">循环依据</label><select class="as-input" data-k="b:${i}:repeat_from">${repeatOptions.join("")}</select></div></div><div class="as-inner-list as-mt8">`);
        const inner = Array.isArray(item.inner_questions) ? item.inner_questions : [];
        inner.forEach((q, qi) => {
          html.push(`<div><div class="as-actions"><button class="as-btn" data-op="q-logic" data-i="${i}" data-qi="${qi}">逻辑</button><button class="as-btn" data-op="q-up" data-i="${i}" data-qi="${qi}">上移</button><button class="as-btn" data-op="q-down" data-i="${i}" data-qi="${qi}">下移</button><button class="as-btn" data-op="q-copy" data-i="${i}" data-qi="${qi}">复制</button><button class="as-btn" data-op="q-del" data-i="${i}" data-qi="${qi}">删除</button></div>${questionCardHtml(`l:${i}:${qi}`, q, true)}</div>`);
        });
        html.push(`<div class="as-actions"><button class="as-btn" data-op="q-add-in" data-i="${i}">添加块内题</button></div></div></div>`);
      } else {
        const q = item.question || defaultQuestion(false);
        html.push(`<div class="as-block"><div class="as-block-head"><p class="as-block-title">${i + 1}. 普通题</p><div class="as-actions"><button class="as-btn" data-op="q-top-logic" data-i="${i}">逻辑</button><button class="as-btn" data-op="b-up" data-i="${i}">上移</button><button class="as-btn" data-op="b-down" data-i="${i}">下移</button><button class="as-btn" data-op="b-copy" data-i="${i}">复制</button><button class="as-btn" data-op="b-del" data-i="${i}">删除</button></div></div>${questionCardHtml(`q:${i}`, q, false)}</div>`);
      }
    });
    qBoardCanvas.innerHTML = html.join("");
    qBoardCanvas.querySelectorAll("[data-op]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const op = btn.getAttribute("data-op");
        const i = Number(btn.getAttribute("data-i") || -1);
        const qi = Number(btn.getAttribute("data-qi") || -1);
        const items = d.items || [];
        if (i < 0 || i >= items.length) return;
        if (op === "b-up" && i > 0) [items[i - 1], items[i]] = [items[i], items[i - 1]];
        if (op === "b-down" && i < items.length - 1) [items[i + 1], items[i]] = [items[i], items[i + 1]];
        if (op === "b-copy") items.splice(i + 1, 0, cloneObj(items[i]));
        if (op === "b-del") items.splice(i, 1);
        if (op === "b-logic") {
          state.logicTarget = { kind: "block", i };
          renderLogicPanel();
          openDesignerModal(qLogicPanel);
          return;
        }
        if (op === "q-top-logic") {
          state.logicTarget = { kind: "top_question", i };
          renderLogicPanel();
          openDesignerModal(qLogicPanel);
          return;
        }
        if (op === "q-add-in" && items[i].kind === "loop") {
          if (!Array.isArray(items[i].inner_questions)) items[i].inner_questions = [];
          items[i].inner_questions.push(defaultQuestion(true));
          renderDraftBoard();
          return;
        }
        if (op && op.startsWith("q-") && items[i].kind === "loop") {
          if (op === "q-logic") {
            state.logicTarget = { kind: "loop_question", i, qi };
            renderLogicPanel();
            openDesignerModal(qLogicPanel);
            return;
          }
          const inner = Array.isArray(items[i].inner_questions) ? items[i].inner_questions : [];
          if (qi < 0 || qi >= inner.length) return;
          if (op === "q-up" && qi > 0) [inner[qi - 1], inner[qi]] = [inner[qi], inner[qi - 1]];
          if (op === "q-down" && qi < inner.length - 1) [inner[qi + 1], inner[qi]] = [inner[qi], inner[qi + 1]];
          if (op === "q-copy") inner.splice(qi + 1, 0, cloneObj(inner[qi]));
          if (op === "q-del") inner.splice(qi, 1);
        }
        if (!items.length) items.push({ kind: "question", block_id: newId("b"), question: defaultQuestion(false), visible_if: null });
        renderDraftBoard();
      });
    });
    qBoardCanvas.querySelectorAll("[data-k]").forEach((el) => {
      const key = String(el.getAttribute("data-k") || "");
      const assign = (allowReRender = false) => {
        const val = (el.type === "checkbox") ? !!el.checked : String(el.value || "");
        const parts = key.split(":");
        let needReRender = false;
        if (parts[0] === "q") {
          const i = Number(parts[1] || -1); const f = parts[2];
          const q = (((d.items || [])[i] || {}).question || null);
          if (!q) return;
          if (f === "required") q.required = !!val;
          else if (f === "options") q.options = String(val).replace(/，/g, ",").split(",").map((x) => x.trim()).filter(Boolean);
          else if (["min", "max", "step", "min_select", "max_select", "min_length", "max_length", "min_words", "max_words", "max_lines"].includes(f)) {
            const defaults = { min: 1, max: 5, step: 1, min_select: 1, max_select: 2, min_length: 0, max_length: 0, min_words: 0, max_words: 0, max_lines: 0 };
            const n = Number(val);
            q[f] = Number.isFinite(n) ? n : (defaults[f] ?? 0);
          }
          else q[f] = val;
          if (f === "id" || f === "type") needReRender = true;
        } else if (parts[0] === "l") {
          const i = Number(parts[1] || -1); const qi = Number(parts[2] || -1); const f = parts[3];
          const q = ((((d.items || [])[i] || {}).inner_questions || [])[qi] || null);
          if (!q) return;
          if (f === "required") q.required = !!val;
          else if (f === "options") q.options = String(val).replace(/，/g, ",").split(",").map((x) => x.trim()).filter(Boolean);
          else if (["min", "max", "step", "min_select", "max_select", "min_length", "max_length", "min_words", "max_words", "max_lines"].includes(f)) {
            const defaults = { min: 1, max: 5, step: 1, min_select: 1, max_select: 2, min_length: 0, max_length: 0, min_words: 0, max_words: 0, max_lines: 0 };
            const n = Number(val);
            q[f] = Number.isFinite(n) ? n : (defaults[f] ?? 0);
          }
          else q[f] = val;
          if (f === "id" || f === "type") needReRender = true;
        } else if (parts[0] === "b") {
          const i = Number(parts[1] || -1); const f = parts[2];
          const b = ((d.items || [])[i] || null);
          if (!b) return;
          b[f] = val;
        }
        if (allowReRender && needReRender) renderDraftBoard();
      };
      el.addEventListener("change", () => assign(true));
      el.addEventListener("input", () => assign(false));
    });
    renderLogicPanel();
  }

  function buildSchemaFromDraft() {
    pullDraftForm();
    const d = state.draft || defaultDraft();
    const questions = [];
    (d.items || []).forEach((item) => {
      if (item.kind === "loop") {
        const repeatFrom = String(item.repeat_from || "").trim();
        const blockVisible = item.visible_if && typeof item.visible_if === "object" ? item.visible_if : null;
        const inner = Array.isArray(item.inner_questions) ? item.inner_questions : [];
        inner.forEach((raw) => {
          const q = cloneObj(raw || {});
          q.id = String(q.id || newId("q")).trim();
          q.title = String(q.title || "请填写题目").trim();
          q.type = String(q.type || "single").trim();
          q.required = !!q.required;
          q.options = Array.isArray(q.options) ? q.options : [];
          q.min = Number(q.min || 1);
          q.max = Number(q.max || 5);
          q.step = Number(q.step || 1);
          q.min_select = Number(q.min_select || 1);
          q.max_select = Number(q.max_select || 2);
          q.min_length = Number(q.min_length || 0);
          q.max_length = Number(q.max_length || 0);
          q.min_words = Number(q.min_words || 0);
          q.max_words = Number(q.max_words || 0);
          q.max_lines = Number(q.max_lines || 0);
          q.repeat_from = repeatFrom;
          q.repeat_filter = String(q.repeat_filter || "all").trim() || "all";
          q.visible_if = andRules(blockVisible, q.visible_if && typeof q.visible_if === "object" ? q.visible_if : null);
          if (!(q.required_if && typeof q.required_if === "object")) q.required_if = null;
          questions.push(q);
        });
      } else {
        const q = cloneObj((item && item.question) || {});
        const blockVisible = item.visible_if && typeof item.visible_if === "object" ? item.visible_if : null;
        q.id = String(q.id || newId("q")).trim();
        q.title = String(q.title || "请填写题目").trim();
        q.type = String(q.type || "single").trim();
        q.required = !!q.required;
        q.options = Array.isArray(q.options) ? q.options : [];
        q.min = Number(q.min || 1);
        q.max = Number(q.max || 5);
        q.step = Number(q.step || 1);
        q.min_select = Number(q.min_select || 1);
        q.max_select = Number(q.max_select || 2);
        q.min_length = Number(q.min_length || 0);
        q.max_length = Number(q.max_length || 0);
        q.min_words = Number(q.min_words || 0);
        q.max_words = Number(q.max_words || 0);
        q.max_lines = Number(q.max_lines || 0);
        q.repeat_from = "";
        q.visible_if = andRules(blockVisible, q.visible_if && typeof q.visible_if === "object" ? q.visible_if : null);
        if (!(q.required_if && typeof q.required_if === "object")) q.required_if = null;
        questions.push(q);
      }
    });
    const metaExtra = (d.meta_extra && typeof d.meta_extra === "object") ? cloneObj(d.meta_extra) : {};
    const listObjects = normalizeListObjects(d.list_objects || []);
    const validationRules = normalizeValidationRules(d.validation_rules || []);
    const templateMeta = safeObj(d.template_meta);
    Object.keys(templateMeta).forEach((k) => {
      if (String(k).startsWith("template_")) metaExtra[k] = cloneObj(templateMeta[k]);
    });
    metaExtra.board_v2 = { items: cloneObj(d.items || []) };
    metaExtra.designer = "board_v2";
    metaExtra.capability_flags = ["board", "loop_block", "list_objects", "validation_rules"];
    metaExtra.list_objects = listObjects;
    metaExtra.validation_rules = validationRules;
    return {
      version: 2,
      intro: d.intro || "",
      meta: metaExtra,
      questions,
    };
  }

  function showToast(text, ok = true) {
    if (!toastEl) return;
    if (!ok) {
      showErrorModal(text || "操作失败。");
    }
    toastEl.textContent = text || "";
    toastEl.style.background = ok ? "#111" : "#333";
    toastEl.classList.remove("as-hidden");
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(() => {
      toastEl.classList.add("as-hidden");
    }, 2200);
  }

  function readDarkModeSetting() {
    try {
      return String(window.localStorage.getItem(darkModeStorageKey) || "") === "1";
    } catch (_err) {
      return false;
    }
  }

  function writeDarkModeSetting(enabled) {
    try {
      window.localStorage.setItem(darkModeStorageKey, enabled ? "1" : "0");
    } catch (_err) {
      // ignore storage errors
    }
  }

  function applyDarkMode(enabled) {
    const on = !!enabled;
    document.documentElement.classList.toggle("as-dark-mode", on);
    if (darkModeToggle) darkModeToggle.checked = on;
  }

  async function api(url, options = {}) {
    const res = await fetch(url, options);
    let data = {};
    try {
      data = await res.json();
    } catch (_) {
      throw new Error(`请求失败：${res.status}`);
    }
    if (!res.ok || !data.ok) {
      throw new Error(data.error || `请求失败：${res.status}`);
    }
    return data;
  }

  const apiGet = (url) => api(url);
  const apiPost = (url, body) => api(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const apiForm = (url, formData) => api(url, { method: "POST", body: formData });

  function switchTab(tab) {
    closeAllDesignerModals();
    tabButtons.forEach((btn) => btn.classList.toggle("is-active", btn.dataset.tab === tab));
    tabPanels.forEach((panel) => panel.classList.toggle("is-active", panel.id === `tab-${tab}`));
  }

  function showAuth(bootstrapped) {
    authCard.classList.remove("as-hidden");
    mainSection.classList.add("as-hidden");
    authTitle.textContent = bootstrapped ? "管理员解锁" : "初始化管理员密码";
    initBtn.classList.toggle("as-hidden", !!bootstrapped);
    unlockBtn.classList.toggle("as-hidden", !bootstrapped);
  }

  function showMain() {
    authCard.classList.add("as-hidden");
    mainSection.classList.remove("as-hidden");
  }

  function ensureQuestionnaireSelected() {
    if (!state.selected.questionnaireId && state.questionnaires.length) {
      state.selected.questionnaireId = String(state.questionnaires[0].id || "");
    }
    selectedQuestionnaire.textContent = state.selected.questionnaireId || "未选择";
  }

  function ensureRosterSelected() {
    if (!state.selected.rosterId && state.rosters.length) {
      state.selected.rosterId = String(state.rosters[0].id || "");
    }
    selectedRoster.textContent = state.selected.rosterId || "未选择";
  }

  function selectedRosterObject() {
    const rid = String(state.selected.rosterId || "").trim();
    if (!rid) return null;
    return state.rosters.find((r) => String(r.id || "").trim() === rid) || null;
  }

  function renderQuestionnaireRows() {
    ensureQuestionnaireSelected();
    if (!questionnaireRows) return;
    if (!state.questionnaires.length) {
      questionnaireRows.innerHTML = "<tr><td colspan='4'>暂无问卷</td></tr>";
      return;
    }
    questionnaireRows.innerHTML = state.questionnaires.map((q) => {
      const qid = String(q.id || "");
      const cls = qid === state.selected.questionnaireId ? "is-selected" : "";
      return `<tr class="${cls}" data-qid="${esc(qid)}"><td>${esc(qid)}</td><td>${esc(q.title || "")}</td><td>${esc(prettyAuthMode(q.auth_mode || ""))}</td><td>${esc(q.status || "")}</td></tr>`;
    }).join("");
    questionnaireRows.querySelectorAll("tr[data-qid]").forEach((row) => {
      row.addEventListener("click", () => {
        state.selected.questionnaireId = String(row.getAttribute("data-qid") || "");
        renderQuestionnaireRows();
        refreshQuestionnaireMenus();
      });
    });
  }

  function renderRosterRows() {
    ensureRosterSelected();
    if (!rosterRows) return;
    if (!state.rosters.length) {
      rosterRows.innerHTML = "<tr><td colspan='3'>暂无名单</td></tr>";
      return;
    }
    rosterRows.innerHTML = state.rosters.map((r) => {
      const rid = String(r.id || "");
      const cls = rid === state.selected.rosterId ? "is-selected" : "";
      return `<tr class="${cls}" data-rid="${esc(rid)}"><td>${esc(rid)}</td><td>${esc(r.name || "")}</td><td>${Number(r.member_count || 0)}</td></tr>`;
    }).join("");
    rosterRows.querySelectorAll("tr[data-rid]").forEach((row) => {
      row.addEventListener("click", () => {
        state.selected.rosterId = String(row.getAttribute("data-rid") || "");
        state.selected.memberId = "";
        renderRosterRows();
        refreshMembers();
      });
    });
  }

  function renderMemberRows() {
    ensureRosterSelected();
    if (!memberRows) return;
    const roster = selectedRosterObject();
    const columns = Array.isArray(state.memberColumns) && state.memberColumns.length
      ? state.memberColumns
      : (Array.isArray(roster && roster.columns) ? roster.columns : []);
    if (memberHeadRow) {
      const th = ['<th>行ID</th>', '<th>唯一键</th>'];
      columns.forEach((c) => {
        const label = String((c && (c.label || c.key)) || "").trim();
        th.push(`<th>${esc(label || "字段")}</th>`);
      });
      memberHeadRow.innerHTML = th.join("");
    }
    if (!state.members.length) {
      memberRows.innerHTML = `<tr><td colspan="${2 + columns.length}">暂无成员</td></tr>`;
      return;
    }
    memberRows.innerHTML = state.members.map((m) => {
      const mid = String(m.id || "");
      const cls = mid === state.selected.memberId ? "is-selected" : "";
      const values = (m && typeof m.values === "object" && m.values) ? m.values : {};
      const tds = [
        `<td>${esc(mid)}</td>`,
        `<td>${esc(m.member_key || "")}</td>`,
      ];
      columns.forEach((c) => {
        const key = String((c && c.key) || "").trim();
        const v = key ? (values[key] ?? "") : "";
        tds.push(`<td>${esc(v)}</td>`);
      });
      return `<tr class="${cls}" data-mid="${esc(mid)}">${tds.join("")}</tr>`;
    }).join("");
    memberRows.querySelectorAll("tr[data-mid]").forEach((row) => {
      row.addEventListener("click", () => {
        state.selected.memberId = String(row.getAttribute("data-mid") || "");
        renderMemberRows();
      });
    });
  }

  function renderSubmissionRows() {
    if (!submissionRows) return;
    if (!state.submissions.length) {
      submissionRows.innerHTML = "<tr><td colspan='4'>暂无票据</td></tr>";
      return;
    }
    submissionRows.innerHTML = state.submissions.map((s) => {
      const sid = String(s.id || "");
      const cls = sid === state.selected.submissionId ? "is-selected" : "";
      return `<tr class="${cls}" data-sid="${esc(sid)}"><td>${esc(sid)}</td><td>${esc(s.submitted_at || "")}</td><td>${esc(s.source || "")}</td><td>${esc(s.respondent_name || "")}</td></tr>`;
    }).join("");
    submissionRows.querySelectorAll("tr[data-sid]").forEach((row) => {
      row.addEventListener("click", () => {
        state.selected.submissionId = String(row.getAttribute("data-sid") || "");
        renderSubmissionRows();
      });
    });
  }

  function refreshQuestionnaireMenus() {
    const options = state.questionnaires.map((q) => `<option value="${esc(q.id)}">${esc(q.id)} | ${esc(q.title || "")}</option>`).join("");
    [serverQ, offlineQ, votesQ].forEach((el) => {
      if (!el) return;
      const current = el.value;
      el.innerHTML = options || "<option value=''>暂无问卷</option>";
      const target = current || state.selected.questionnaireId;
      if (target) el.value = target;
    });
    if (qDraftRoster) {
      const rosterOptions = state.rosters.map((r) => `<option value="${esc(r.id)}">${esc(r.id)} | ${esc(r.name || "")}</option>`).join("");
      qDraftRoster.innerHTML = `<option value="">不绑定</option>${rosterOptions}`;
      if (state.draft && state.draft.auth_roster_id) qDraftRoster.value = state.draft.auth_roster_id;
    }
  }

  function renderDashboard() {
    const summary = state.summary || {};
    statQuestionnaires.textContent = String(summary.questionnaires || 0);
    statSubmissions.textContent = String(summary.submissions || 0);
    statRosters.textContent = String(summary.rosters || 0);
    statServer.textContent = (state.server && state.server.running) ? "运行中" : "未启动";
    dashboardText.textContent = [
      `问卷总数：${summary.questionnaires || 0}`,
      `名单总数：${summary.rosters || 0}`,
      `票据总数：${summary.submissions || 0}`,
      `票据目录：${summary.votes_dir || ""}`,
    ].join("\n");
  }

  function kernelNameText(kernel) {
    return String(kernel || "").trim().toLowerCase() === "tkinter" ? "tkinter 内核" : "网页内核";
  }

  function renderRuntimeKernel() {
    if (runtimeKernelText) {
      runtimeKernelText.textContent = `当前：${kernelNameText(state.runtimeKernel)}`;
    }
    if (switchKernelBtn) {
      switchKernelBtn.textContent = `切换到 ${kernelNameText(state.runtimeKernelNext)}`;
    }
  }

  function renderGuide() {
    if (!guideStatus) return;
    guideStatus.textContent = (state.guideLines || []).join("\n");
  }

  function renderServer() {
    const s = state.server || {};
    serverInfo.textContent = [
      `运行状态：${s.running ? "运行中" : "未启动"}`,
      `监听地址：${s.host || "-"}:${s.port || "-"}`,
      `局域网地址：${s.base_url || "-"}`,
      `首页：${s.home_url || "-"}`,
      `默认问卷：${s.default_url || "-"}`,
    ].join("\n");
    serverQr.src = s.qr_data_uri || "";
    if (s.default_questionnaire_id) serverQ.value = s.default_questionnaire_id;
  }

  function renderSqlViews() {
    if (!sqlViewSelect) return;
    if (!state.sqlViews.length) {
      sqlViewSelect.innerHTML = "<option value=''>暂无模板</option>";
      return;
    }
    sqlViewSelect.innerHTML = state.sqlViews
      .map((v) => `<option value="${Number(v.id || 0)}">${esc(v.name || "")}</option>`)
      .join("");
  }

  function renderTemplateMenu() {
    if (!qTemplateSelect) return;
    const list = asArray(state.templates);
    if (!list.length) {
      qTemplateSelect.innerHTML = "<option value=''>暂无模板</option>";
      return;
    }
    qTemplateSelect.innerHTML = `<option value="">请选择模板</option>${list.map((t) => {
      const name = String(t.name || "").trim();
      return `<option value="${esc(name)}">${esc(name)}</option>`;
    }).join("")}`;
  }

  function renderListRows() {
    if (!qListRows) return;
    const d = state.draft || defaultDraft();
    const list = normalizeListObjects(d.list_objects || []);
    d.list_objects = list;
    if (!list.length) {
      qListRows.innerHTML = "<tr><td colspan='4'>暂无列表</td></tr>";
      return;
    }
    qListRows.innerHTML = list.map((obj) => {
      const name = String(obj.name || "");
      const cls = name === state.selectedListName ? "is-selected" : "";
      const readonly = !!obj.readonly || String(obj.source || "").startsWith("roster_auto:");
      const sourceText = `${String(obj.source || "manual")}${readonly ? "（只读）" : ""}`;
      return `<tr class="${cls}" data-list="${esc(name)}"><td>${esc(name)}</td><td>${esc(obj.type || "")}</td><td>${esc(sourceText)}</td><td>${Number(asArray(obj.items).length)}</td></tr>`;
    }).join("");
    qListRows.querySelectorAll("tr[data-list]").forEach((row) => {
      row.addEventListener("click", () => {
        state.selectedListName = String(row.getAttribute("data-list") || "");
        fillListFormFromSelected();
        renderListRows();
      });
    });
  }

  function fillListFormFromSelected() {
    const d = state.draft || defaultDraft();
    const list = normalizeListObjects(d.list_objects || []);
    const target = list.find((x) => String(x.name || "") === String(state.selectedListName || "")) || null;
    if (!target) {
      qListName.value = "";
      qListType.value = "text";
      qListItems.value = "";
      qListName.disabled = false;
      qListType.disabled = false;
      qListItems.disabled = false;
      if (qListSaveBtn) qListSaveBtn.disabled = false;
      if (qListDeleteBtn) qListDeleteBtn.disabled = true;
      return;
    }
    qListName.value = String(target.name || "");
    qListType.value = String(target.type || "text");
    qListItems.value = asArray(target.items).map((it) => {
      const key = String((it && (it.key || it.value)) || "").trim();
      const label = String((it && it.label) || key).trim();
      if (!key) return "";
      return key === label ? key : `${key}|${label}`;
    }).filter(Boolean).join("\n");
    const readonly = !!target.readonly || String(target.source || "").startsWith("roster_auto:");
    qListName.disabled = readonly;
    qListType.disabled = readonly;
    qListItems.disabled = readonly;
    if (qListSaveBtn) qListSaveBtn.disabled = readonly;
    if (qListDeleteBtn) qListDeleteBtn.disabled = readonly;
  }

  function parseListItemsText(text) {
    const out = [];
    String(text || "").split(/\r?\n/).forEach((line) => {
      const raw = String(line || "").trim();
      if (!raw) return;
      const parts = raw.split("|");
      const key = String(parts[0] || "").trim();
      const label = String(parts[1] || parts[0] || "").trim();
      if (!key) return;
      out.push({ key, label: label || key });
    });
    return out;
  }

  function renderRuleRows() {
    if (!qRuleRows) return;
    const d = state.draft || defaultDraft();
    const rules = normalizeValidationRules(d.validation_rules || []);
    d.validation_rules = rules;
    if (!rules.length) {
      qRuleRows.innerHTML = "<tr><td colspan='4'>暂无规则</td></tr>";
      return;
    }
    qRuleRows.innerHTML = rules.map((rule, idx) => {
      const cls = idx === state.selectedRuleIndex ? "is-selected" : "";
      const v = String(rule.op || "").includes("between")
        ? `${rule.value ?? ""},${rule.value2 ?? ""}`
        : `${rule.value ?? ""}`;
      return `<tr class="${cls}" data-rule-idx="${idx}"><td>${esc(rule.name || "")}</td><td>${esc(rule.op || "")}</td><td>${esc(v)}</td><td>${esc(rule.message || "")}</td></tr>`;
    }).join("");
    qRuleRows.querySelectorAll("tr[data-rule-idx]").forEach((row) => {
      row.addEventListener("click", () => {
        state.selectedRuleIndex = Number(row.getAttribute("data-rule-idx") || -1);
        fillRuleFormFromSelected();
        renderRuleRows();
      });
    });
  }

  function fillRuleFormFromSelected() {
    const d = state.draft || defaultDraft();
    const rules = normalizeValidationRules(d.validation_rules || []);
    const idx = Number(state.selectedRuleIndex || -1);
    const rule = idx >= 0 && idx < rules.length ? rules[idx] : null;
    if (!rule) {
      qRuleName.value = "";
      qRuleSql.value = "";
      qRuleOp.value = "lte";
      qRuleValue.value = "";
      qRuleMessage.value = "";
      return;
    }
    qRuleName.value = String(rule.name || "");
    qRuleSql.value = String(rule.sql || "");
    qRuleOp.value = String(rule.op || "lte");
    const v = String(rule.op || "").includes("between")
      ? `${rule.value ?? ""},${rule.value2 ?? ""}`
      : `${rule.value ?? ""}`;
    qRuleValue.value = v;
    qRuleMessage.value = String(rule.message || "");
  }

  function buildRuleFromForm() {
    const name = String(qRuleName.value || "").trim() || "联合规则";
    const sql = String(qRuleSql.value || "").trim();
    const op = String(qRuleOp.value || "lte").trim() || "lte";
    const rawV = String(qRuleValue.value || "").trim().replace(/，/g, ",");
    let value = "";
    let value2 = "";
    if (op === "between" || op === "not_between") {
      const parts = rawV.split(",");
      value = String(parts[0] || "").trim();
      value2 = String(parts[1] || "").trim();
    } else {
      value = rawV;
    }
    const message = String(qRuleMessage.value || "").trim() || `${name} 未通过。`;
    return { type: "sql_aggregate", name, sql, op, value, value2, message };
  }

  function getLogicTargetRef() {
    const d = state.draft || defaultDraft();
    const t = state.logicTarget;
    if (!t || typeof t !== "object") return null;
    const items = asArray(d.items);
    const i = Number(t.i || -1);
    if (i < 0 || i >= items.length) return null;
    const item = items[i];
    if (t.kind === "block" && item.kind === "loop") return { target: item, label: `循环块 #${i + 1}` };
    if (t.kind === "top_question" && item.kind !== "loop") return { target: item.question, label: `普通题 #${i + 1}` };
    if (t.kind === "loop_question" && item.kind === "loop") {
      const qi = Number(t.qi || -1);
      const inner = asArray(item.inner_questions);
      if (qi >= 0 && qi < inner.length) return { target: inner[qi], label: `循环块 #${i + 1} 内题 #${qi + 1}`, inLoop: true };
    }
    return null;
  }

  function renderLogicPanel() {
    if (!qLogicTarget) return;
    const ref = getLogicTargetRef();
    if (!ref) {
      qLogicTarget.textContent = "未选择";
      qLogicVisiblePreview.textContent = "";
      qLogicRequiredPreview.textContent = "";
      qLogicRepeatFilter.value = "all";
      return;
    }
    qLogicTarget.textContent = ref.label || "已选择";
    const t = ref.target || {};
    qLogicVisiblePreview.textContent = stringifyRule(t.visible_if || null);
    qLogicRequiredPreview.textContent = stringifyRule(t.required_if || null);
    if (ref.inLoop) qLogicRepeatFilter.value = String(t.repeat_filter || "all");
    else qLogicRepeatFilter.value = "all";
  }

  function getRosterColumns(rosterId) {
    const rid = String(rosterId || "").trim();
    if (!rid) return [];
    const roster = state.rosters.find((r) => String(r.id || "").trim() === rid) || null;
    if (!roster) return [];
    return asArray(roster.columns);
  }

  async function syncAutoRosterLists(reRender = true) {
    ensureDraftShape();
    const d = state.draft || defaultDraft();
    const rid = String((d && d.auth_roster_id) || qDraftRoster.value || "").trim();
    const keep = normalizeListObjects(d.list_objects || []).filter((obj) => {
      const source = String(obj.source || "").trim();
      return !source.startsWith("roster_auto:");
    });
    if (rid) {
      const data = await apiGet(`/api/admin/roster/list-objects?roster_id=${encodeURIComponent(rid)}`);
      const incoming = normalizeListObjects(data.list_objects || []);
      incoming.forEach((obj) => {
        const name = String(obj.name || "").trim();
        if (!name) return;
        const idx = keep.findIndex((x) => String(x.name || "").trim() === name);
        if (idx >= 0) keep[idx] = obj;
        else keep.push(obj);
      });
    }
    d.list_objects = keep;
    if (reRender) {
      renderListRows();
      fillListFormFromSelected();
      renderDraftBoard();
    }
  }

  function setCollectFieldsFromLabels(labels) {
    const text = asArray(labels).map((x) => String(x || "").trim()).filter(Boolean).join(",");
    qDraftCollectFields.value = text;
    pullDraftForm();
  }

  async function checkDraftConfiguration(showSuccess = true) {
    pullDraftForm();
    ensureDraftShape();
    const d = state.draft || defaultDraft();
    const errors = [];
    const warnings = [];
    if (!String(d.title || "").trim()) errors.push("问卷标题不能为空。");
    const items = asArray(d.items);
    if (!items.length) errors.push("至少需要 1 个题目块。");
    if (String(d.auth_mode || "open") !== "open" && !String(d.auth_roster_id || "").trim()) {
      errors.push("名单校验模式下必须绑定名单。");
    }
    if (String(d.auth_mode || "open") !== "open" && !asArray(d.collect_fields).length) {
      errors.push("名单校验模式下必须至少配置 1 个进入前采集字段。");
    }
    const qids = new Set();
    const multiRequiredQids = new Set();
    const listNames = new Set();
    normalizeListObjects(d.list_objects || []).forEach((obj) => {
      const n = String(obj.name || "").trim();
      if (!n) errors.push("存在未命名列表。");
      else if (listNames.has(n)) errors.push(`列表名称重复：${n}`);
      else listNames.add(n);
      if (String(obj.type || "").trim() === "number") {
        asArray(obj.items).forEach((it) => {
          const key = String((it && (it.key || it.value)) || "").trim();
          if (!key) return;
          if (!Number.isFinite(Number(key))) errors.push(`数字列表 ${n} 包含非数字项：${key}`);
        });
      }
    });
    items.forEach((item) => {
      if (item && item.kind === "loop") {
        const repeatFrom = String(item.repeat_from || "").trim();
        if (!repeatFrom) errors.push(`循环块“${String(item.title || "循环块")}”未设置循环依据。`);
        if (repeatFrom.startsWith("__list__:")) {
          const ln = repeatFrom.slice("__list__:".length).trim();
          if (!listNames.has(ln)) errors.push(`循环块“${String(item.title || "循环块")}”引用不存在列表：${ln}`);
        }
        const inner = asArray(item.inner_questions);
        if (!inner.length) errors.push(`循环块“${String(item.title || "循环块")}”内至少需要 1 道题。`);
        inner.forEach((q) => {
          const qid = String((q && q.id) || "").trim();
          const title = String((q && q.title) || "").trim();
          if (!qid) errors.push("存在题目未设置 ID。");
          if (qid && qids.has(qid)) errors.push(`题目ID重复：${qid}`);
          if (qid) qids.add(qid);
          if (qid && !title) errors.push(`${qid}：题目标题不能为空。`);
          const qType = String((q && q.type) || "").trim();
          if ((qType === "single" || qType === "multi") && !asArray(q.options).length) errors.push(`${qid || "题目"}：单选/多选题必须设置选项。`);
          if (qType === "multi" && q.required) multiRequiredQids.add(qid);
        });
      } else {
        const q = safeObj(item && item.question);
        const qid = String(q.id || "").trim();
        const title = String(q.title || "").trim();
        if (!qid) errors.push("存在题目未设置 ID。");
        if (qid && qids.has(qid)) errors.push(`题目ID重复：${qid}`);
        if (qid) qids.add(qid);
        if (qid && !title) errors.push(`${qid}：题目标题不能为空。`);
        const qType = String(q.type || "").trim();
        if ((qType === "single" || qType === "multi") && !asArray(q.options).length) errors.push(`${qid || "题目"}：单选/多选题必须设置选项。`);
      }
    });
    items.forEach((item) => {
      if (!(item && item.kind === "loop")) return;
      const repeatFrom = String(item.repeat_from || "").trim();
      if (repeatFrom && repeatFrom !== "__roster_members__" && !repeatFrom.startsWith("__list__:")) {
        if (!qids.has(repeatFrom)) errors.push(`循环块“${String(item.title || "循环块")}”引用题目ID不存在：${repeatFrom}`);
        else if (!multiRequiredQids.has(repeatFrom)) warnings.push(`循环块“${String(item.title || "循环块")}”依据题目 ${repeatFrom} 不是必填多选题，循环项可能为空。`);
      }
    });
    const rules = normalizeValidationRules(d.validation_rules || []);
    for (let i = 0; i < rules.length; i += 1) {
      const rule = rules[i];
      const idx = i + 1;
      const op = String(rule.op || "").trim();
      if (!["equals", "not_equals", "gt", "gte", "lt", "lte", "between", "not_between"].includes(op)) {
        errors.push(`联合规则 #${idx} 比较方式无效。`);
      }
      if (!String(rule.sql || "").trim()) errors.push(`联合规则 #${idx} 缺少 SQL。`);
      if (!Number.isFinite(Number(rule.value))) errors.push(`联合规则 #${idx} 目标值必须是数字。`);
      if ((op === "between" || op === "not_between") && !Number.isFinite(Number(rule.value2))) {
        errors.push(`联合规则 #${idx} 区间上限必须是数字。`);
      }
      if (String(rule.sql || "").trim()) {
        try {
          await apiPost("/api/admin/rule/validate-sql", { sql_text: String(rule.sql || "") });
        } catch (err) {
          errors.push(`联合规则 #${idx} SQL 无效：${String(err.message || err)}`);
        }
      }
    }
    const lines = [];
    if (errors.length) {
      lines.push("发现问题：");
      errors.forEach((e) => lines.push(`- ${e}`));
    }
    if (warnings.length) {
      if (lines.length) lines.push("");
      lines.push("提示项：");
      warnings.forEach((w) => lines.push(`- ${w}`));
    }
    if (!lines.length) lines.push("配置体检通过。");
    qCheckOutput.textContent = lines.join("\n");
    if (errors.length) return false;
    if (showSuccess) showToast("配置体检通过");
    return true;
  }

  function formatTable(columns, rows) {
    if (!Array.isArray(columns) || !columns.length) return "(空结果)";
    const viewRows = Array.isArray(rows) ? rows : [];
    const maxScan = Math.min(viewRows.length, 200);
    const widths = columns.map((c, idx) => {
      let w = String(c).length;
      for (let i = 0; i < maxScan; i += 1) {
        const cell = String((viewRows[i] || [])[idx] ?? "");
        w = Math.max(w, cell.length);
      }
      return Math.min(Math.max(w, 4), 36);
    });
    const line = `+${widths.map((w) => "-".repeat(w + 2)).join("+")}+`;
    const renderRow = (arr) => `|${arr.map((v, i) => {
      const text = String(v ?? "").slice(0, widths[i]);
      return ` ${text.padEnd(widths[i], " ")} `;
    }).join("|")}|`;
    const out = [line, renderRow(columns), line];
    viewRows.forEach((r) => out.push(renderRow(columns.map((_, i) => (r || [])[i]))));
    out.push(line);
    return out.join("\n");
  }

  function renderSqlResults(result) {
    const sets = (result && Array.isArray(result.results)) ? result.results : [];
    state.sqlResults = sets;
    if (!sets.length) {
      sqlConsole.textContent = "SQL> 无结果集";
      return;
    }
    const lines = ["SQL> 执行成功", ""];
    sets.forEach((rs) => {
      lines.push(`-- 结果集 #${rs.index}（${rs.row_count} 行${rs.truncated ? "，已截断" : ""}）`);
      lines.push(formatTable(rs.columns || [], rs.rows || []));
      lines.push("");
    });
    sqlConsole.textContent = lines.join("\n");
  }

  async function refreshMembers() {
    ensureRosterSelected();
    if (!state.selected.rosterId) {
      state.members = [];
      state.memberColumns = [];
      renderMemberRows();
      return;
    }
    const data = await apiGet(`/api/admin/roster/${encodeURIComponent(state.selected.rosterId)}/members?limit=5000`);
    state.members = data.members || [];
    state.memberColumns = Array.isArray(data.columns) ? data.columns : [];
    renderMemberRows();
    selectedRoster.textContent = state.selected.rosterId;
  }

  async function refreshSubmissions() {
    const qid = votesQ.value || state.selected.questionnaireId;
    if (!qid) {
      state.submissions = [];
      renderSubmissionRows();
      return;
    }
    const data = await apiGet(`/api/admin/submissions?questionnaire_id=${encodeURIComponent(qid)}`);
    state.submissions = data.submissions || [];
    renderSubmissionRows();
  }

  async function refreshSqlSchema() {
    const qid = votesQ.value || state.selected.questionnaireId;
    if (!qid) {
      sqlSchemaText.textContent = "请先选择问卷。";
      if (qRuleSchemaText) qRuleSchemaText.textContent = "请先选择问卷。";
      return;
    }
    const data = await apiGet(`/api/admin/sql/schema?questionnaire_id=${encodeURIComponent(qid)}`);
    const schema = data.schema || {};
    const text = formatSchemaText(schema);
    sqlSchemaText.textContent = text || "暂无模型";
    if (qRuleSchemaText) qRuleSchemaText.textContent = text || "暂无模型";
  }

  function formatSchemaText(schema) {
    const lines = [];
    const appendTableDefs = (title, defs) => {
      if (!Array.isArray(defs) || !defs.length) return;
      if (title) lines.push(title);
      defs.forEach((t) => {
        lines.push(`[${t.name}] ${t.desc || ""}`);
        (t.columns || []).forEach((col) => {
          const c0 = col[0] || "";
          const c1 = col[1] || "";
          const c2 = col[2] || "";
          lines.push(`  - ${c0} ${c1} ${c2}`);
        });
        lines.push("");
      });
    };
    appendTableDefs("可查询表结构：", schema.table_defs || []);
    const dynamicCols = Array.isArray(schema.identity_dynamic_columns) ? schema.identity_dynamic_columns : [];
    if (dynamicCols.length) {
      lines.push("自动身份列（可直接在 SQL 中使用）：");
      dynamicCols.forEach((item) => {
        const col = String(item.column_name || "").trim();
        const label = String(item.field_label || item.field_key || "").trim();
        if (!col) return;
        lines.push(`  - ${col}  # 来自字段 ${label}`);
      });
      lines.push("");
    }
    if (Array.isArray(schema.examples) && schema.examples.length) {
      lines.push("示例查询：");
      schema.examples.forEach((s, i) => lines.push(`${i + 1}. ${s}`));
      lines.push("");
    }
    appendTableDefs("联合规则可用项目（字段级）：", schema.live_rule_table_defs || []);
    if (schema.live_rule_suffix) {
      lines.push(`联合规则自动限制：${schema.live_rule_suffix}`);
      lines.push("");
    }
    if (Array.isArray(schema.live_rule_examples) && schema.live_rule_examples.length) {
      lines.push("联合规则示例 SQL（仅 1 条 SELECT，建议返回单值数字）：");
      schema.live_rule_examples.forEach((s, i) => lines.push(`${i + 1}. ${s}`));
    }
    return lines.join("\n");
  }

  async function refreshSqlViews() {
    const qid = votesQ.value || state.selected.questionnaireId;
    if (!qid) {
      state.sqlViews = [];
      renderSqlViews();
      return;
    }
    const data = await apiGet(`/api/admin/sql/views?questionnaire_id=${encodeURIComponent(qid)}`);
    state.sqlViews = data.views || [];
    renderSqlViews();
  }

  async function refreshServerInfo() {
    const data = await apiGet("/api/admin/server/info");
    state.server = data.server || {};
    renderServer();
  }

  function modalPanels() {
    return [
      qManageListPanel,
      qManageEditorPanel,
      qListPanel,
      qRulePanel,
      qLogicPanel,
      qCheckPanel,
      qErrorPanel,
    ].filter(Boolean);
  }

  function syncModalBackdrop() {
    if (!qModalBackdrop) return;
    const panels = modalPanels();
    const show = panels.some((p) => !p.classList.contains("as-hidden"));
    qModalBackdrop.classList.toggle("as-hidden", !show);
  }

  function openDesignerModal(panel) {
    if (!panel) return;
    const childPanels = new Set([qListPanel, qRulePanel, qLogicPanel, qCheckPanel, qErrorPanel]);
    const keepEditorOpen = childPanels.has(panel) && qManageEditorPanel && !qManageEditorPanel.classList.contains("as-hidden");
    modalPanels().forEach((p) => {
      if (p === panel) return;
      if (keepEditorOpen && p === qManageEditorPanel) return;
      p.classList.add("as-hidden");
    });
    panel.classList.remove("as-hidden");
    syncModalBackdrop();
  }

  function closeDesignerModal(panel) {
    if (!panel) return;
    panel.classList.add("as-hidden");
    syncModalBackdrop();
  }

  function closeAllDesignerModals() {
    modalPanels().forEach((p) => closeDesignerModal(p));
  }

  function showErrorModal(message, title = "错误提示") {
    if (!qErrorPanel || !qErrorText || !qErrorTitle) return;
    qErrorTitle.textContent = String(title || "错误提示");
    qErrorText.textContent = String(message || "发生未知错误。");
    openDesignerModal(qErrorPanel);
  }

  async function refreshAll() {
    const data = await apiGet("/api/admin/bootstrap");
    state.summary = data.summary || {};
    state.questionnaires = data.questionnaires || [];
    state.rosters = data.rosters || [];
    state.templates = data.templates || state.templates || [];
    state.guideLines = data.guide_lines || [];
    state.server = data.server || {};
    state.exportsDir = data.exports_dir || "";
    state.liveRuleSuffix = String(data.live_rule_suffix || "").trim();
    state.runtimeKernel = String(data.runtime_kernel || "web").trim().toLowerCase() || "web";
    state.runtimeKernelNext = String(data.runtime_kernel_next || "").trim().toLowerCase()
      || (state.runtimeKernel === "web" ? "tkinter" : "web");

    if (!serverHost.value) serverHost.value = data.default_host || "0.0.0.0";
    if (!serverPort.value) serverPort.value = String(data.default_port || 5050);
    if (!offlinePath.value) offlinePath.value = `${state.exportsDir}${state.exportsDir.endsWith("/") || state.exportsDir.endsWith("\\") ? "" : "\\"}offline_form.html`;
    if (!backupPath.value) backupPath.value = `${state.exportsDir}${state.exportsDir.endsWith("/") || state.exportsDir.endsWith("\\") ? "" : "\\"}votefree_backup.zip`;
    if (!sqlExportPath.value) sqlExportPath.value = `${state.exportsDir}${state.exportsDir.endsWith("/") || state.exportsDir.endsWith("\\") ? "" : "\\"}sql_result.csv`;

    renderGuide();
    renderDashboard();
    renderRuntimeKernel();
    renderQuestionnaireRows();
    renderRosterRows();
    refreshQuestionnaireMenus();
    renderTemplateMenu();
    renderServer();
    if (qRuleSuffix) qRuleSuffix.textContent = state.liveRuleSuffix || "(自动附加)";

    ensureDraftShape();
    fillDraftForm();
    await syncAutoRosterLists(false);
    renderDraftBoard();
    renderLogicPanel();
    renderListRows();
    renderRuleRows();
    fillListFormFromSelected();
    fillRuleFormFromSelected();

    await Promise.all([refreshMembers(), refreshSubmissions(), refreshSqlSchema(), refreshSqlViews()]);
  }

  async function refreshAuthStatus() {
    const st = await apiGet("/api/admin/status");
    if (!st.bootstrapped || !st.unlocked) {
      showAuth(!!st.bootstrapped);
      return;
    }
    showMain();
    await refreshAll();
  }

  async function changeQuestionnaireStatus(status) {
    const qid = state.selected.questionnaireId;
    if (!qid) throw new Error("请先选择问卷。");
    const data = await apiPost("/api/admin/questionnaire/status", { questionnaire_id: qid, status });
    state.questionnaires = data.questionnaires || [];
    renderQuestionnaireRows();
  }

  async function bindActions() {
    tabButtons.forEach((btn) => btn.addEventListener("click", () => switchTab(btn.dataset.tab || "dashboard")));
    document.querySelectorAll("[data-jump-tab]").forEach((el) => {
      el.addEventListener("click", () => switchTab(el.getAttribute("data-jump-tab") || "dashboard"));
    });
    if (guideRefreshBtn) {
      guideRefreshBtn.addEventListener("click", async () => {
        try { await refreshAll(); showToast("引导状态已刷新"); } catch (err) { showToast(String(err.message || err), false); }
      });
    }
    if (quickRosterBtn) {
      quickRosterBtn.addEventListener("click", async () => {
        try {
          const data = await apiPost("/api/admin/guide/quick-demo-roster", {});
          state.rosters = data.rosters || [];
          state.selected.rosterId = data.roster_id || state.selected.rosterId;
          renderRosterRows();
          await refreshMembers();
          showToast("示例名单已创建");
        } catch (err) {
          showToast(String(err.message || err), false);
        }
      });
    }
    if (quickTplSatBtn) {
      quickTplSatBtn.addEventListener("click", async () => {
        try {
          const data = await apiPost("/api/admin/guide/quick-template-questionnaire", { template_name: "普通满意度调查" });
          state.questionnaires = data.questionnaires || [];
          state.rosters = data.rosters || state.rosters;
          state.selected.questionnaireId = data.questionnaire_id || state.selected.questionnaireId;
          renderQuestionnaireRows();
          renderRosterRows();
          refreshQuestionnaireMenus();
          showToast("示例满意度问卷已创建并启用");
        } catch (err) {
          showToast(String(err.message || err), false);
        }
      });
    }
    if (quickTplEvalBtn) {
      quickTplEvalBtn.addEventListener("click", async () => {
        try {
          const data = await apiPost("/api/admin/guide/quick-template-questionnaire", { template_name: "指定对象评分" });
          state.questionnaires = data.questionnaires || [];
          state.rosters = data.rosters || state.rosters;
          state.selected.questionnaireId = data.questionnaire_id || state.selected.questionnaireId;
          renderQuestionnaireRows();
          renderRosterRows();
          refreshQuestionnaireMenus();
          showToast("示例评分问卷已创建并启用");
        } catch (err) {
          showToast(String(err.message || err), false);
        }
      });
    }

    initBtn.addEventListener("click", async () => {
      try {
        await apiPost("/api/admin/init", { password: String(passwordInput.value || "").trim() });
        showToast("初始化并解锁成功");
        await refreshAuthStatus();
      } catch (err) {
        const msg = String(err.message || err);
        authStatus.textContent = msg;
        showToast(msg, false);
      }
    });

    unlockBtn.addEventListener("click", async () => {
      try {
        await apiPost("/api/admin/unlock", { password: String(passwordInput.value || "").trim() });
        showToast("解锁成功");
        await refreshAuthStatus();
      } catch (err) {
        const msg = String(err.message || err);
        authStatus.textContent = msg;
        showToast(msg, false);
      }
    });

    topRefreshBtn.addEventListener("click", async () => {
      try { await refreshAll(); showToast("已刷新"); } catch (err) { showToast(String(err.message || err), false); }
    });

    if (qOpenListModalBtn) {
      qOpenListModalBtn.addEventListener("click", () => {
        openDesignerModal(qManageListPanel);
      });
    }
    if (qOpenEditorModalBtn) {
      qOpenEditorModalBtn.addEventListener("click", () => {
        openDesignerModal(qManageEditorPanel);
      });
    }
    if (qListAreaCloseBtn) qListAreaCloseBtn.addEventListener("click", () => closeDesignerModal(qManageListPanel));
    if (qEditorAreaCloseBtn) qEditorAreaCloseBtn.addEventListener("click", () => closeDesignerModal(qManageEditorPanel));
    if (qErrorCloseBtn) qErrorCloseBtn.addEventListener("click", () => closeDesignerModal(qErrorPanel));

    qOpenBtn.addEventListener("click", async () => {
      try {
        const qid = state.selected.questionnaireId;
        if (!qid) throw new Error("请先选择问卷。");
        const data = await apiGet(`/api/admin/questionnaire/detail?questionnaire_id=${encodeURIComponent(qid)}`);
        loadQuestionnaireToDraft(data.questionnaire || {});
        switchTab("questionnaire");
        openDesignerModal(qManageEditorPanel);
        showToast("已载入问卷到网页编辑器");
      } catch (err) { showToast(String(err.message || err), false); }
    });
    qDesignerBtn.addEventListener("click", async () => {
      try {
        const ok = await checkDraftConfiguration(true);
        if (!ok) showToast("配置体检发现问题，请先修复。", false);
      } catch (err) { showToast(String(err.message || err), false); }
    });
    qActiveBtn.addEventListener("click", async () => { try { await changeQuestionnaireStatus("active"); showToast("已启用"); } catch (err) { showToast(String(err.message || err), false); } });
    qPauseBtn.addEventListener("click", async () => { try { await changeQuestionnaireStatus("paused"); showToast("已暂停"); } catch (err) { showToast(String(err.message || err), false); } });
    qRefreshBtn.addEventListener("click", async () => { try { await refreshAll(); showToast("已刷新问卷列表"); } catch (err) { showToast(String(err.message || err), false); } });

    qRenameBtn.addEventListener("click", async () => {
      try {
        const qid = state.selected.questionnaireId;
        if (!qid) throw new Error("请先选择问卷。");
        const value = prompt("请输入新的问卷标题：", "");
        if (value === null) return;
        const data = await apiPost("/api/admin/questionnaire/rename", { questionnaire_id: qid, new_title: value.trim() });
        state.questionnaires = data.questionnaires || [];
        renderQuestionnaireRows();
        showToast("问卷已重命名");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    qCopyBtn.addEventListener("click", async () => {
      try {
        const qid = state.selected.questionnaireId;
        if (!qid) throw new Error("请先选择问卷。");
        const value = prompt("请输入副本标题（可留空）：", "");
        if (value === null) return;
        const data = await apiPost("/api/admin/questionnaire/copy", { questionnaire_id: qid, new_title: value.trim() });
        state.questionnaires = data.questionnaires || [];
        state.selected.questionnaireId = data.new_questionnaire_id || state.selected.questionnaireId;
        renderQuestionnaireRows();
        refreshQuestionnaireMenus();
        showToast("问卷已复制");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    qDeleteBtn.addEventListener("click", async () => {
      try {
        const qid = state.selected.questionnaireId;
        if (!qid) throw new Error("请先选择问卷。");
        if (!confirm(`确定删除问卷 ${qid} 吗？`)) return;
        const data = await apiPost("/api/admin/questionnaire/delete", { questionnaire_id: qid });
        state.questionnaires = data.questionnaires || [];
        state.selected.questionnaireId = "";
        renderQuestionnaireRows();
        refreshQuestionnaireMenus();
        showToast("问卷已删除");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    qNewDraftBtn.addEventListener("click", () => {
      state.draft = defaultDraft();
      state.logicTarget = null;
      state.selectedListName = "";
      state.selectedRuleIndex = -1;
      fillDraftForm();
      renderDraftBoard();
      renderLogicPanel();
      renderListRows();
      renderRuleRows();
      fillListFormFromSelected();
      fillRuleFormFromSelected();
      showToast("已新建空白编辑草稿");
    });

    qLoadDraftBtn.addEventListener("click", async () => {
      try {
        const qid = state.selected.questionnaireId;
        if (!qid) throw new Error("请先选择问卷。");
        const data = await apiGet(`/api/admin/questionnaire/detail?questionnaire_id=${encodeURIComponent(qid)}`);
        loadQuestionnaireToDraft(data.questionnaire || {});
        await syncAutoRosterLists(true);
        showToast("已载入问卷到网页编辑器");
      } catch (err) {
        showToast(String(err.message || err), false);
      }
    });

    qAddQuestionBtn.addEventListener("click", () => {
      pullDraftForm();
      ensureDraftShape();
      state.draft.items.push({ kind: "question", block_id: newId("b"), question: defaultQuestion(false), visible_if: null });
      renderDraftBoard();
      renderLogicPanel();
      showToast("已添加普通题");
    });

    qAddLoopBtn.addEventListener("click", () => {
      pullDraftForm();
      ensureDraftShape();
      state.draft.items.push(defaultLoopBlock());
      renderDraftBoard();
      renderLogicPanel();
      showToast("已添加循环块");
    });

    qCollectConfigBtn.addEventListener("click", () => {
      const current = String(qDraftCollectFields.value || "");
      const raw = prompt("请输入采集字段（逗号分隔）：", current || "姓名,编号");
      if (raw === null) return;
      qDraftCollectFields.value = raw;
      pullDraftForm();
      showToast("采集字段已更新");
    });

    qCollectFromRosterBtn.addEventListener("click", () => {
      const rid = String(qDraftRoster.value || "").trim();
      if (!rid) {
        showToast("请先绑定名单。", false);
        return;
      }
      const cols = getRosterColumns(rid);
      const labels = cols.map((c) => String((c && (c.label || c.key)) || "").trim()).filter(Boolean);
      if (!labels.length) {
        showToast("该名单没有可用字段。", false);
        return;
      }
      setCollectFieldsFromLabels(labels);
      showToast("已从名单字段填入采集字段");
    });

    qCollectClearBtn.addEventListener("click", () => {
      qDraftCollectFields.value = "";
      pullDraftForm();
      showToast("采集字段已清空");
    });

    qDraftRoster.addEventListener("change", async () => {
      try {
        pullDraftForm();
        ensureDraftShape();
        state.draft.auth_roster_id = String(qDraftRoster.value || "").trim();
        await syncAutoRosterLists(true);
        showToast("已同步名单关联列表");
      } catch (err) {
        showToast(String(err.message || err), false);
      }
    });

    qTemplateApplyBtn.addEventListener("click", async () => {
      try {
        const name = String(qTemplateSelect.value || "").trim();
        if (!name) throw new Error("请先选择模板。");
        const data = await apiPost("/api/admin/template/build", {
          template_name: name,
          roster_id: String(qDraftRoster.value || "").trim(),
        });
        const payload = data.payload || {};
        const schema = payload.schema && typeof payload.schema === "object" ? payload.schema : {};
        if (!state.draft) state.draft = defaultDraft();
        state.draft.title = String(payload.title || "").trim();
        state.draft.description = String(payload.description || "").trim();
        state.draft.passcode = String(payload.passcode || "").trim();
        state.draft.allow_repeat = !!payload.allow_repeat;
        state.draft.auth_mode = String(payload.auth_mode || "open").trim() || "open";
        state.draft.auth_roster_id = String(data.roster_id || payload.auth_roster_id || "").trim();
        const identityFields = safeObj(payload.identity_fields);
        state.draft.allow_same_device_repeat = !!identityFields.allow_same_device_repeat;
        state.draft.collect_fields = asArray(identityFields.collect_fields).map((x) => {
          if (x && typeof x === "object") return { key: String(x.key || "").trim(), label: String(x.label || x.key || "").trim() };
          const t = String(x || "").trim();
          return { key: t, label: t };
        }).filter((x) => x.key);
        state.draft.intro = String(schema.intro || "").trim();
        state.draft.items = convertSchemaToItems(schema);
        state.draft.template_meta = extractTemplateMeta(schema.meta || {});
        state.draft.list_objects = normalizeListObjects((schema.meta && schema.meta.list_objects) || []);
        state.draft.validation_rules = normalizeValidationRules((schema.meta && schema.meta.validation_rules) || []);
        state.draft.meta_extra = safeObj(schema.meta);
        state.logicTarget = null;
        state.selectedListName = "";
        state.selectedRuleIndex = -1;
        fillDraftForm();
        await syncAutoRosterLists(true);
        renderLogicPanel();
        renderRuleRows();
        fillListFormFromSelected();
        fillRuleFormFromSelected();
        showToast("模板已加载到编辑器，可继续修改");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    qTemplateCreateBtn.addEventListener("click", async () => {
      try {
        const name = String(qTemplateSelect.value || "").trim();
        if (!name) throw new Error("请先选择模板。");
        const data = await apiPost("/api/admin/guide/quick-template-questionnaire", { template_name: name });
        state.questionnaires = data.questionnaires || [];
        state.rosters = data.rosters || state.rosters;
        state.selected.questionnaireId = data.questionnaire_id || state.selected.questionnaireId;
        renderQuestionnaireRows();
        renderRosterRows();
        refreshQuestionnaireMenus();
        showToast("模板问卷已直接创建并启用");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    qListManageBtn.addEventListener("click", () => {
      openDesignerModal(qListPanel);
      renderListRows();
      fillListFormFromSelected();
    });
    qRuleManageBtn.addEventListener("click", async () => {
      openDesignerModal(qRulePanel);
      renderRuleRows();
      fillRuleFormFromSelected();
      try { await refreshSqlSchema(); } catch (_err) {}
    });
    qLogicManageBtn.addEventListener("click", () => {
      openDesignerModal(qLogicPanel);
      renderLogicPanel();
    });
    qCheckPanelBtn.addEventListener("click", () => {
      openDesignerModal(qCheckPanel);
    });
    qListCloseBtn.addEventListener("click", () => closeDesignerModal(qListPanel));
    if (qListCloseTopBtn) qListCloseTopBtn.addEventListener("click", () => closeDesignerModal(qListPanel));
    qRuleCloseBtn.addEventListener("click", () => closeDesignerModal(qRulePanel));
    if (qRuleCloseTopBtn) qRuleCloseTopBtn.addEventListener("click", () => closeDesignerModal(qRulePanel));
    if (qLogicCloseBtn) qLogicCloseBtn.addEventListener("click", () => closeDesignerModal(qLogicPanel));
    if (qCheckCloseBtn) qCheckCloseBtn.addEventListener("click", () => closeDesignerModal(qCheckPanel));
    if (qModalBackdrop) {
      qModalBackdrop.addEventListener("click", () => {
        closeAllDesignerModals();
      });
    }
    window.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") closeAllDesignerModals();
    });
    qRefreshBoardBtn.addEventListener("click", () => {
      ensureDraftShape();
      renderDraftBoard();
      renderLogicPanel();
      renderListRows();
      renderRuleRows();
      showToast("展板已刷新");
    });
    qCheckDraftBtn.addEventListener("click", async () => {
      try {
        const ok = await checkDraftConfiguration(true);
        openDesignerModal(qCheckPanel);
        if (!ok) showToast("配置体检发现问题，请按提示修复。", false);
      } catch (err) { showToast(String(err.message || err), false); }
    });

    qLogicWriteVisibleBtn.addEventListener("click", () => {
      const rule = simpleRuleFromInputs();
      qLogicVisiblePreview.textContent = stringifyRule(rule);
    });
    qLogicWriteRequiredBtn.addEventListener("click", () => {
      const rule = simpleRuleFromInputs();
      qLogicRequiredPreview.textContent = stringifyRule(rule);
    });
    qLogicSaveBtn.addEventListener("click", () => {
      const ref = getLogicTargetRef();
      if (!ref) {
        showToast("请先在题目卡片中选择“逻辑”。", false);
        return;
      }
      const target = ref.target || {};
      target.visible_if = parseRuleFromText(qLogicVisiblePreview.textContent) || null;
      target.required_if = parseRuleFromText(qLogicRequiredPreview.textContent) || null;
      if (ref.inLoop) target.repeat_filter = String(qLogicRepeatFilter.value || "all").trim() || "all";
      renderLogicPanel();
      showToast("逻辑已保存到当前目标");
    });
    qLogicClearBtn.addEventListener("click", () => {
      const ref = getLogicTargetRef();
      if (!ref) {
        showToast("请先在题目卡片中选择“逻辑”。", false);
        return;
      }
      const target = ref.target || {};
      target.visible_if = null;
      target.required_if = null;
      if (ref.inLoop) target.repeat_filter = "all";
      renderLogicPanel();
      showToast("逻辑已清空");
    });

    qListNewBtn.addEventListener("click", () => {
      state.selectedListName = "";
      fillListFormFromSelected();
    });
    qListSaveBtn.addEventListener("click", () => {
      ensureDraftShape();
      const name = String(qListName.value || "").trim();
      if (!name) {
        showToast("列表名称不能为空。", false);
        return;
      }
      const type = String(qListType.value || "text").trim() || "text";
      const items = parseListItemsText(qListItems.value || "");
      const list = normalizeListObjects(state.draft.list_objects || []);
      const idx = list.findIndex((x) => String(x.name || "") === String(state.selectedListName || ""));
      if (idx >= 0) {
        const current = list[idx] || {};
        if (!!current.readonly || String(current.source || "").startsWith("roster_auto:")) {
          showToast("该列表由名单自动生成，不能手工修改。", false);
          return;
        }
      }
      const obj = {
        name,
        type,
        source: "manual",
        readonly: false,
        items,
      };
      if (idx >= 0) list[idx] = obj;
      else list.push(obj);
      state.draft.list_objects = list;
      state.selectedListName = name;
      renderListRows();
      renderDraftBoard();
      showToast("列表已保存");
    });
    qListDeleteBtn.addEventListener("click", () => {
      ensureDraftShape();
      const name = String(state.selectedListName || "").trim();
      if (!name) {
        showToast("请先选择列表。", false);
        return;
      }
      const current = normalizeListObjects(state.draft.list_objects || []);
      const target = current.find((x) => String(x.name || "") === name) || {};
      if (!!target.readonly || String(target.source || "").startsWith("roster_auto:")) {
        showToast("该列表由名单自动生成，不能删除。", false);
        return;
      }
      state.draft.list_objects = current.filter((x) => String(x.name || "") !== name);
      state.selectedListName = "";
      renderListRows();
      fillListFormFromSelected();
      renderDraftBoard();
      showToast("列表已删除");
    });
    qListImportRosterBtn.addEventListener("click", async () => {
      try {
        pullDraftForm();
        ensureDraftShape();
        state.draft.auth_roster_id = String(qDraftRoster.value || "").trim();
        if (!state.draft.auth_roster_id) throw new Error("请先绑定名单。");
        await syncAutoRosterLists(true);
        showToast("已按名单字段填入列表");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    qRuleNewBtn.addEventListener("click", () => {
      state.selectedRuleIndex = -1;
      fillRuleFormFromSelected();
    });
    qRuleSaveBtn.addEventListener("click", async () => {
      try {
        ensureDraftShape();
        const rule = buildRuleFromForm();
        if (!String(rule.sql || "").trim()) throw new Error("SQL 不能为空。");
        await apiPost("/api/admin/rule/validate-sql", { sql_text: String(rule.sql || "") });
        const rules = normalizeValidationRules(state.draft.validation_rules || []);
        const idx = Number(state.selectedRuleIndex || -1);
        if (idx >= 0 && idx < rules.length) rules[idx] = rule;
        else {
          rules.push(rule);
          state.selectedRuleIndex = rules.length - 1;
        }
        state.draft.validation_rules = rules;
        renderRuleRows();
        showToast("联合规则已保存");
      } catch (err) { showToast(String(err.message || err), false); }
    });
    qRuleDeleteBtn.addEventListener("click", () => {
      ensureDraftShape();
      const idx = Number(state.selectedRuleIndex || -1);
      const rules = normalizeValidationRules(state.draft.validation_rules || []);
      if (idx < 0 || idx >= rules.length) {
        showToast("请先选择规则。", false);
        return;
      }
      rules.splice(idx, 1);
      state.draft.validation_rules = rules;
      state.selectedRuleIndex = -1;
      renderRuleRows();
      fillRuleFormFromSelected();
      showToast("联合规则已删除");
    });
    qRuleUpBtn.addEventListener("click", () => {
      ensureDraftShape();
      const idx = Number(state.selectedRuleIndex || -1);
      const rules = normalizeValidationRules(state.draft.validation_rules || []);
      if (idx <= 0 || idx >= rules.length) return;
      [rules[idx - 1], rules[idx]] = [rules[idx], rules[idx - 1]];
      state.draft.validation_rules = rules;
      state.selectedRuleIndex = idx - 1;
      renderRuleRows();
    });
    qRuleDownBtn.addEventListener("click", () => {
      ensureDraftShape();
      const idx = Number(state.selectedRuleIndex || -1);
      const rules = normalizeValidationRules(state.draft.validation_rules || []);
      if (idx < 0 || idx >= rules.length - 1) return;
      [rules[idx + 1], rules[idx]] = [rules[idx], rules[idx + 1]];
      state.draft.validation_rules = rules;
      state.selectedRuleIndex = idx + 1;
      renderRuleRows();
    });
    qRuleSampleAvgBtn.addEventListener("click", () => {
      qRuleName.value = "示例：平均分上限";
      qRuleOp.value = "lte";
      qRuleValue.value = "3";
      qRuleSql.value = "SELECT AVG(value_num) FROM answers WHERE question_id = 'q_score'";
      qRuleMessage.value = "当前平均分超过限制。";
    });
    qRuleSampleCountBtn.addEventListener("click", () => {
      qRuleName.value = "示例：高分人数上限";
      qRuleOp.value = "lte";
      qRuleValue.value = "2";
      qRuleSql.value = "SELECT COUNT(*) FROM answers WHERE question_id = 'q_score' AND value_num = 4";
      qRuleMessage.value = "4分人数超出上限。";
    });
    qRuleSampleJoinBtn.addEventListener("click", () => {
      qRuleName.value = "示例：互评高分人数上限";
      qRuleOp.value = "lte";
      qRuleValue.value = "2";
      qRuleSql.value = "SELECT COUNT(*) FROM answers a JOIN submissions s ON a.submission_id = s.submission_id WHERE a.question_id = 'q_score' AND a.value_num >= 4 AND a.repeat_at <> s.verified_member_key_xing_ming";
      qRuleMessage.value = "互评中4分人数超出上限。";
    });
    qRuleSampleRangeBtn.addEventListener("click", () => {
      qRuleName.value = "示例：总分区间";
      qRuleOp.value = "between";
      qRuleValue.value = "10,30";
      qRuleSql.value = "SELECT SUM(value_num) FROM answers WHERE question_id = 'q_score'";
      qRuleMessage.value = "总分不在允许区间内。";
    });

    qSaveDraftBtn.addEventListener("click", async () => {
      try {
        pullDraftForm();
        ensureDraftShape();
        const checkOk = await checkDraftConfiguration(false);
        if (!checkOk) {
          openDesignerModal(qCheckPanel);
          throw new Error("配置体检未通过，请在弹窗里按提示修复后再保存。");
        }
        if (!String(state.draft.title || "").trim()) throw new Error("问卷标题不能为空。");
        const schema = buildSchemaFromDraft();
        const data = await apiPost("/api/admin/questionnaire/save", {
          questionnaire_id: state.draft.questionnaire_id || "",
          title: state.draft.title || "",
          description: state.draft.description || "",
          intro: state.draft.intro || "",
          passcode: state.draft.passcode || "",
          allow_repeat: !!state.draft.allow_repeat,
          allow_same_device_repeat: !!state.draft.allow_same_device_repeat,
          auth_mode: state.draft.auth_mode || "open",
          auth_roster_id: state.draft.auth_roster_id || "",
          collect_fields: state.draft.collect_fields || [],
          schema,
        });
        state.questionnaires = data.questionnaires || state.questionnaires;
        state.selected.questionnaireId = data.questionnaire_id || state.selected.questionnaireId;
        state.draft.questionnaire_id = data.questionnaire_id || state.draft.questionnaire_id;
        renderQuestionnaireRows();
        refreshQuestionnaireMenus();
        fillDraftForm();
        renderListRows();
        renderRuleRows();
        showToast("问卷保存成功");
      } catch (err) {
        showToast(String(err.message || err), false);
      }
    });

    rRefreshBtn.addEventListener("click", async () => { try { await refreshAll(); showToast("已刷新名单"); } catch (err) { showToast(String(err.message || err), false); } });
    rColumnsBtn.addEventListener("click", async () => {
      try {
        const rid = state.selected.rosterId;
        if (!rid) throw new Error("请先选择名单。");
        const roster = state.rosters.find((r) => String(r.id) === rid) || {};
        const current = Array.isArray(roster.columns) ? roster.columns : [];
        const defaultText = current.map((c) => String(c.label || c.key || "").trim()).filter(Boolean).join(",");
        const raw = prompt("请输入字段名称（逗号分隔）：", defaultText || "姓名,编号");
        if (raw === null) return;
        const columns = parseRosterColumnsText(raw);
        const data = await apiPost("/api/admin/roster/columns", { roster_id: rid, columns });
        state.rosters = data.rosters || state.rosters;
        state.members = data.members || state.members;
        renderRosterRows();
        renderMemberRows();
        showToast("名单字段已更新");
      } catch (err) { showToast(String(err.message || err), false); }
    });
    rCreateBtn.addEventListener("click", async () => {
      try {
        const name = prompt("请输入名单名称：", "");
        if (name === null) return;
        const data = await apiPost("/api/admin/roster/create", { name: name.trim() });
        state.rosters = data.rosters || [];
        state.selected.rosterId = data.roster_id || "";
        renderRosterRows();
        await refreshMembers();
        showToast("名单已创建");
      } catch (err) { showToast(String(err.message || err), false); }
    });
    rRenameBtn.addEventListener("click", async () => {
      try {
        const rid = state.selected.rosterId;
        if (!rid) throw new Error("请先选择名单。");
        const name = prompt("请输入新的名单名称：", "");
        if (name === null) return;
        const data = await apiPost("/api/admin/roster/rename", { roster_id: rid, new_name: name.trim() });
        state.rosters = data.rosters || [];
        renderRosterRows();
        showToast("名单已重命名");
      } catch (err) { showToast(String(err.message || err), false); }
    });
    rCopyBtn.addEventListener("click", async () => {
      try {
        const rid = state.selected.rosterId;
        if (!rid) throw new Error("请先选择名单。");
        const name = prompt("请输入副本名称（可留空）：", "");
        if (name === null) return;
        const data = await apiPost("/api/admin/roster/copy", { roster_id: rid, new_name: name.trim() });
        state.rosters = data.rosters || [];
        state.selected.rosterId = data.new_roster_id || state.selected.rosterId;
        renderRosterRows();
        await refreshMembers();
        showToast("名单已复制");
      } catch (err) { showToast(String(err.message || err), false); }
    });
    rDeleteBtn.addEventListener("click", async () => {
      try {
        const rid = state.selected.rosterId;
        if (!rid) throw new Error("请先选择名单。");
        if (!confirm(`确定删除名单 ${rid} 吗？`)) return;
        const data = await apiPost("/api/admin/roster/delete", { roster_id: rid });
        state.rosters = data.rosters || [];
        state.selected.rosterId = "";
        state.members = [];
        state.memberColumns = [];
        renderRosterRows();
        renderMemberRows();
        showToast("名单已删除");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    mRefreshBtn.addEventListener("click", async () => { try { await refreshMembers(); showToast("已刷新成员"); } catch (err) { showToast(String(err.message || err), false); } });
    mAddBtn.addEventListener("click", async () => {
      try {
        const rid = state.selected.rosterId;
        if (!rid) throw new Error("请先选择名单。");
        const roster = state.rosters.find((r) => String(r.id) === rid) || {};
        const columns = Array.isArray(roster.columns) ? roster.columns : [];
        const values = {};
        if (!columns.length) {
          const name = prompt("姓名（可留空）：", "");
          if (name === null) return;
          const code = prompt("编号（可留空）：", "");
          if (code === null) return;
          values.member_name = String(name || "").trim();
          values.member_code = String(code || "").trim();
        } else {
          for (const col of columns) {
            const label = String(col.label || col.key || "字段");
            const key = String(col.key || "");
            if (!key) continue;
            const val = prompt(`请输入 ${label}：`, "");
            if (val === null) return;
            values[key] = String(val || "").trim();
          }
        }
        const data = await apiPost("/api/admin/roster/member/add", { roster_id: rid, values });
        state.members = data.members || [];
        renderMemberRows();
        showToast("成员已新增");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    mRemoveBtn.addEventListener("click", async () => {
      try {
        const rid = state.selected.rosterId;
        const mid = state.selected.memberId;
        if (!rid || !mid) throw new Error("请先选择成员。");
        if (!confirm(`确定删除成员行 ${mid} 吗？`)) return;
        const data = await apiPost("/api/admin/roster/member/remove", { roster_id: rid, member_id: Number(mid) });
        state.members = data.members || [];
        state.selected.memberId = "";
        renderMemberRows();
        showToast("成员已删除");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    rImportBtn.addEventListener("click", async () => {
      try {
        const rid = state.selected.rosterId;
        if (!rid) throw new Error("请先选择名单。");
        const file = rosterImportFile.files && rosterImportFile.files[0];
        if (!file) throw new Error("请先选择导入文件。");
        const fd = new FormData();
        fd.append("roster_id", rid);
        fd.append("replace_all", rosterReplaceAll.checked ? "1" : "0");
        fd.append("file", file);
        const data = await apiForm("/api/admin/roster/import", fd);
        state.members = data.members || [];
        renderMemberRows();
        await refreshAll();
        showToast("名单导入成功");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    serverStartBtn.addEventListener("click", async () => {
      try {
        const data = await apiPost("/api/admin/server/start", {
          host: serverHost.value.trim(),
          port: Number(serverPort.value || 0),
          default_questionnaire_id: serverQ.value,
        });
        state.server = data.server || {};
        renderServer();
        showToast("服务已启动");
      } catch (err) { showToast(String(err.message || err), false); }
    });
    serverStopBtn.addEventListener("click", async () => { try { const d = await apiPost("/api/admin/server/stop", {}); state.server = d.server || {}; renderServer(); showToast("服务已停止"); } catch (err) { showToast(String(err.message || err), false); } });
    serverRefreshBtn.addEventListener("click", async () => { try { await refreshServerInfo(); showToast("服务状态已刷新"); } catch (err) { showToast(String(err.message || err), false); } });
    serverOpenHomeBtn.addEventListener("click", async () => { try { await apiPost("/api/admin/server/open-home", {}); showToast("已在浏览器打开首页"); } catch (err) { showToast(String(err.message || err), false); } });
    serverOpenQBtn.addEventListener("click", async () => { try { await apiPost("/api/admin/server/open-default", {}); showToast("已在浏览器打开问卷"); } catch (err) { showToast(String(err.message || err), false); } });
    serverCopyLinkBtn.addEventListener("click", async () => {
      try {
        const link = (state.server && state.server.default_url) || (state.server && state.server.home_url) || "";
        if (!link) throw new Error("暂无可复制链接。");
        await navigator.clipboard.writeText(link);
        showToast("链接已复制");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    offlineExportBtn.addEventListener("click", async () => {
      try {
        const qid = offlineQ.value || state.selected.questionnaireId;
        if (!qid) throw new Error("请先选择问卷。");
        const data = await apiPost("/api/admin/offline/export", { questionnaire_id: qid, output_path: offlinePath.value.trim() });
        offlineLog.textContent = `导出完成：${data.output_path}`;
        showToast("离线问卷已导出");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    offlineChoosePathBtn.addEventListener("click", () => {
      const raw = prompt("请输入离线导出路径：", offlinePath.value || "");
      if (raw === null) return;
      offlinePath.value = String(raw || "").trim();
    });

    offlineOpenDirBtn.addEventListener("click", async () => {
      try { await apiPost("/api/admin/offline/open-export-dir", { output_path: offlinePath.value.trim() }); showToast("已打开导出目录"); }
      catch (err) { showToast(String(err.message || err), false); }
    });

    votesQ.addEventListener("change", async () => {
      try { await Promise.all([refreshSubmissions(), refreshSqlSchema(), refreshSqlViews()]); }
      catch (err) { showToast(String(err.message || err), false); }
    });

    subRefreshBtn.addEventListener("click", async () => { try { await refreshSubmissions(); showToast("票据已刷新"); } catch (err) { showToast(String(err.message || err), false); } });
    subRejectBtn.addEventListener("click", async () => {
      try {
        const sid = state.selected.submissionId;
        if (!sid) throw new Error("请先选择票据。");
        if (!confirm(`确定驳回票据 ${sid} 吗？`)) return;
        await apiPost("/api/admin/submission/reject", { submission_id: sid });
        await refreshSubmissions();
        showToast("票据已驳回");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    voteImportBtn.addEventListener("click", async () => {
      try {
        const file = voteImportFile.files && voteImportFile.files[0];
        if (!file) throw new Error("请先选择 .vote 文件。");
        const fd = new FormData();
        fd.append("file", file);
        const data = await apiForm("/api/admin/vote/import", fd);
        showToast(data.message || "票据导入成功");
        await refreshSubmissions();
      } catch (err) { showToast(String(err.message || err), false); }
    });

    sqlSchemaBtn.addEventListener("click", async () => { try { await refreshSqlSchema(); showToast("查询模型已刷新"); } catch (err) { showToast(String(err.message || err), false); } });
    sqlLoadViewBtn.addEventListener("click", () => {
      const vid = Number(sqlViewSelect.value || 0);
      const item = state.sqlViews.find((v) => Number(v.id || 0) === vid);
      if (!item) return;
      sqlEditor.value = String(item.sql_text || "");
      showToast("已加载模板");
    });
    sqlSaveViewBtn.addEventListener("click", async () => {
      try {
        const qid = votesQ.value || state.selected.questionnaireId;
        if (!qid) throw new Error("请先选择问卷。");
        const name = prompt("请输入模板名称：", "");
        if (name === null) return;
        const data = await apiPost("/api/admin/sql/view/save", { questionnaire_id: qid, name: name.trim(), sql_text: sqlEditor.value });
        state.sqlViews = data.views || [];
        renderSqlViews();
        showToast("模板已保存");
      } catch (err) { showToast(String(err.message || err), false); }
    });
    payloadPreviewBtn.addEventListener("click", async () => {
      try {
        const qid = votesQ.value || state.selected.questionnaireId;
        if (!qid) throw new Error("请先选择问卷。");
        const data = await apiGet(`/api/admin/submissions/payload-preview?questionnaire_id=${encodeURIComponent(qid)}&limit=3`);
        sqlConsole.textContent = JSON.stringify(data.preview || [], null, 2);
        showToast(`已显示原始票据预览（共 ${Number(data.total || 0)} 条，展示前3条）`);
      } catch (err) { showToast(String(err.message || err), false); }
    });
    sqlDeleteViewBtn.addEventListener("click", async () => {
      try {
        const qid = votesQ.value || state.selected.questionnaireId;
        const vid = Number(sqlViewSelect.value || 0);
        if (!vid) throw new Error("请先选择模板。");
        const data = await apiPost("/api/admin/sql/view/delete", { questionnaire_id: qid, view_id: vid });
        state.sqlViews = data.views || [];
        renderSqlViews();
        showToast("模板已删除");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    sqlRunBtn.addEventListener("click", async () => {
      try {
        const qid = votesQ.value || state.selected.questionnaireId;
        if (!qid) throw new Error("请先选择问卷。");
        const data = await apiPost("/api/admin/sql/run", { questionnaire_id: qid, sql_text: sqlEditor.value, row_limit: 5000 });
        renderSqlResults(data.result || {});
        showToast("查询执行成功");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    sqlExportBtn.addEventListener("click", async () => {
      try {
        if (!state.sqlResults.length) throw new Error("请先执行查询。");
        const n = prompt("导出第几个结果集？", "1");
        if (n === null) return;
        const idx = Math.max(1, Number(n || 1)) - 1;
        const rs = state.sqlResults[idx];
        if (!rs) throw new Error("结果集不存在。");
        const data = await apiPost("/api/admin/sql/export-csv", {
          columns: rs.columns || [],
          rows: rs.rows || [],
          output_path: sqlExportPath.value.trim(),
        });
        showToast(`导出成功：${data.output_path}`);
      } catch (err) { showToast(String(err.message || err), false); }
    });

    changePwdBtn.addEventListener("click", async () => {
      try {
        await apiPost("/api/admin/password/change", {
          old_password: oldPwd.value,
          new_password: newPwd.value,
          confirm_password: newPwd2.value,
        });
        oldPwd.value = "";
        newPwd.value = "";
        newPwd2.value = "";
        showToast("管理员密码已更新");
      } catch (err) { showToast(String(err.message || err), false); }
    });

    backupBtn.addEventListener("click", async () => {
      try {
        const data = await apiPost("/api/admin/backup/create", { output_path: backupPath.value.trim() });
        showToast(`备份完成：${data.output_path}`);
      } catch (err) { showToast(String(err.message || err), false); }
    });

    if (switchKernelBtn) {
      switchKernelBtn.addEventListener("click", async () => {
        try {
          const target = String(state.runtimeKernelNext || "").trim().toLowerCase()
            || (state.runtimeKernel === "web" ? "tkinter" : "web");
          const data = await apiPost("/api/admin/settings/runtime-kernel", { kernel: target });
          state.runtimeKernel = String(data.kernel || state.runtimeKernel).trim().toLowerCase() || "web";
          state.runtimeKernelNext = String(data.next_kernel || "").trim().toLowerCase()
            || (state.runtimeKernel === "web" ? "tkinter" : "web");
          renderRuntimeKernel();
          showToast(String(data.message || "已保存。重启程序后生效。"));
        } catch (err) {
          showToast(String(err.message || err), false);
        }
      });
    }

    if (darkModeToggle) {
      darkModeToggle.addEventListener("change", () => {
        const on = !!darkModeToggle.checked;
        applyDarkMode(on);
        writeDarkModeSetting(on);
        showToast(on ? "已开启深色反转模式" : "已关闭深色反转模式");
      });
    }
  }

  async function init() {
    sqlEditor.value = "SELECT * FROM submissions ORDER BY submitted_at DESC LIMIT 100";
    sqlConsole.textContent = "SQL> 等待执行查询...";
    offlineLog.textContent = "离线导出日志将显示在这里。";
    applyDarkMode(readDarkModeSetting());

    await bindActions();
    try {
      await refreshAuthStatus();
    } catch (err) {
      authStatus.textContent = String(err.message || err);
      showAuth(true);
    }
  }

  init();
})();
