from __future__ import annotations

import json
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Dict, List, Optional

import customtkinter as ctk
import qrcode

from .config import APP_NAME, DEFAULT_HOST, DEFAULT_PORT
from .offline_export import export_offline_html
from . import scenario_templates
from .server import SurveyServer
from .services import ServiceError, VoteFreeService
from .survey_engine import ROSTER_REPEAT_TOKEN, make_question_id


def _pretty_mode(mode: str) -> str:
    mapping = {"anonymous": "实名", "realname": "实名", "semi": "实名"}
    return mapping.get(mode, mode)


def _center(win: tk.Tk, width: int, height: int) -> None:
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    x = int((screen_w - width) / 2)
    y = int((screen_h - height) / 2)
    win.geometry(f"{width}x{height}+{x}+{y}")


MODE_LABEL_TO_VALUE = {"实名": "realname"}
MODE_VALUE_TO_LABEL = {"anonymous": "实名", "realname": "实名", "semi": "实名"}

AUTH_LABEL_TO_VALUE = {
    "开放作答": "open",
    "名单校验（编号）": "roster_code",
    "名单校验（姓名+编号）": "roster_name_code",
    "名单校验（自定义字段）": "roster_fields",
}
AUTH_VALUE_TO_LABEL = {v: k for k, v in AUTH_LABEL_TO_VALUE.items()}

QTYPE_LABEL_TO_VALUE = {
    "单选": "single",
    "多选": "multi",
    "评分": "rating",
    "滑杆数值": "slider",
    "单行文本": "text",
    "多行文本": "textarea",
}
QTYPE_VALUE_TO_LABEL = {v: k for k, v in QTYPE_LABEL_TO_VALUE.items()}

BOARD_QTYPE_LABELS = ["单选", "多选", "评分", "滑杆数值", "单行文本", "多行文本"]
BOARD_QTYPE_VALUES = {label: QTYPE_LABEL_TO_VALUE[label] for label in BOARD_QTYPE_LABELS}
BOARD_QTYPE_LABEL_BY_VALUE = {value: label for label, value in BOARD_QTYPE_VALUES.items()}

REPEAT_FILTER_LABEL_TO_VALUE = {
    "全部循环项": "all",
    "仅本人（自评）": "self",
    "仅他人（互评）": "peer",
}
REPEAT_FILTER_VALUE_TO_LABEL = {v: k for k, v in REPEAT_FILTER_LABEL_TO_VALUE.items()}

LOGIC_OP_LABEL_TO_VALUE = {
    "等于": "equals",
    "不等于": "not_equals",
    "包含": "contains",
    "大于": "gt",
    "大于等于": "gte",
    "小于": "lt",
    "小于等于": "lte",
    "不为空": "not_empty",
    "为空": "empty",
}
LOGIC_OP_VALUE_TO_LABEL = {v: k for k, v in LOGIC_OP_LABEL_TO_VALUE.items()}

RULE_TYPE_LABEL_TO_VALUE = {
    "多题总和比较": "sum_compare",
    "条件人数比较": "count_compare",
    "选项命中次数": "option_hit_compare",
    "两题结果比较": "question_compare",
}
RULE_TYPE_VALUE_TO_LABEL = {v: k for k, v in RULE_TYPE_LABEL_TO_VALUE.items()}

RULE_COMPARE_LABEL_TO_VALUE = {
    "等于": "equals",
    "不等于": "not_equals",
    "大于": "gt",
    "大于等于": "gte",
    "小于": "lt",
    "小于等于": "lte",
    "区间内": "between",
    "区间外": "not_between",
}
RULE_COMPARE_VALUE_TO_LABEL = {v: k for k, v in RULE_COMPARE_LABEL_TO_VALUE.items()}

RULE_AGG_LABEL_TO_VALUE = {
    "求和": "sum",
    "平均": "avg",
    "最大": "max",
    "最小": "min",
    "数量": "count",
}
RULE_AGG_VALUE_TO_LABEL = {v: k for k, v in RULE_AGG_LABEL_TO_VALUE.items()}

TEMPLATE_PLACEHOLDER = "请选择模板"
TEMPLATE_OPTIONS = [TEMPLATE_PLACEHOLDER] + list(scenario_templates.RECOMMENDED_TEMPLATE_NAMES)


class VoteFreeAdminApp(ctk.CTk):
    def __init__(self, service: VoteFreeService):
        super().__init__()
        self.service = service
        self.server = SurveyServer(service=service, paths=service.paths)
        self.editing_qid: Optional[str] = None
        self.editing_draft_qid: Optional[str] = None
        self.draft_questions: List[Dict[str, Any]] = []
        self.draft_schema_meta: Dict[str, Any] = {}
        self.server_qr_image: Optional[ctk.CTkImage] = None
        self.roster_cache: List[Dict[str, Any]] = []
        self.template_catalog: List[Dict[str, Any]] = scenario_templates.list_templates()
        self.last_selected_template_key: str = ""
        self.design_logic_disabled = True
        self.use_new_board_designer = True

        self.board_items: List[Dict[str, Any]] = []
        self.board_list_objects: List[Dict[str, Any]] = []
        self.board_validation_rules: List[Dict[str, Any]] = []
        self.board_collect_fields: List[Dict[str, str]] = []
        self.board_template_meta: Dict[str, Any] = {}
        self.board_logic_target: Optional[Dict[str, str]] = None
        self.board_card_widgets: List[tuple[str, ctk.CTkFrame]] = []
        self.board_inner_widgets: Dict[str, List[tuple[str, ctk.CTkFrame]]] = {}
        self.board_drag_ctx: Optional[Dict[str, str]] = None
        self.board_selected_card_id: str = ""
        self.board_left_collapsed = True
        self.board_right_collapsed = True
        self.board_left_width = 220
        self.board_right_width = 300

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME} 管理端")
        _center(self, 1320, 860)
        self.minsize(1180, 760)
        self.configure(fg_color="#edf2fb")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if not self._bootstrap_admin_auth():
            self.after(100, self.destroy)
            return

        self._build_ui()
        self._refresh_all()

    def _bootstrap_admin_auth(self) -> bool:
        self.withdraw()
        self.update()

        if not self.service.is_bootstrapped():
            while True:
                pwd1 = simpledialog.askstring(
                    "初始化管理员密码",
                    "首次使用，请设置管理员密码：",
                    parent=self,
                    show="*",
                )
                if pwd1 is None:
                    return False
                pwd2 = simpledialog.askstring(
                    "确认密码",
                    "请再次输入管理员密码：",
                    parent=self,
                    show="*",
                )
                if pwd2 is None:
                    return False
                if len(pwd1) < 8:
                    messagebox.showerror("密码过短", "管理员密码至少 8 位。", parent=self)
                    continue
                if pwd1 != pwd2:
                    messagebox.showerror("密码不一致", "两次输入的密码不一致。", parent=self)
                    continue
                try:
                    self.service.initialize_admin(pwd1)
                    self.service.unlock_admin(pwd1)
                    break
                except ServiceError as exc:
                    messagebox.showerror("初始化失败", str(exc), parent=self)
                    return False
        else:
            while True:
                pwd = simpledialog.askstring(
                    "管理员登录",
                    "请输入管理员密码以解锁历史票据：",
                    parent=self,
                    show="*",
                )
                if pwd is None:
                    return False
                try:
                    self.service.unlock_admin(pwd)
                    break
                except ServiceError as exc:
                    if not messagebox.askretrycancel("密码错误", str(exc), parent=self):
                        return False

        self.deiconify()
        return True

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="#1e2b44", corner_radius=0, height=62)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            top,
            text="VoteFree",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#f8fbff",
        ).grid(row=0, column=0, padx=(22, 12), pady=14, sticky="w")

        self.top_status = ctk.CTkLabel(
            top,
            text="",
            font=ctk.CTkFont(size=13),
            text_color="#c9d8f2",
        )
        self.top_status.grid(row=0, column=1, sticky="e", padx=18)

        tab_wrap = ctk.CTkFrame(self, fg_color="transparent")
        tab_wrap.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        tab_wrap.grid_rowconfigure(0, weight=1)
        tab_wrap.grid_columnconfigure(0, weight=1)

        self.tabs = ctk.CTkTabview(tab_wrap, segmented_button_fg_color="#dce6f7")
        self.tabs.grid(row=0, column=0, sticky="nsew")

        self.tab_guide = self.tabs.add("新手引导")
        self.tab_dashboard = self.tabs.add("概览")
        self.tab_questionnaire = self.tabs.add("问卷管理")
        self.tab_roster = self.tabs.add("名单管理")
        self.tab_server = self.tabs.add("局域网服务")
        self.tab_offline = self.tabs.add("离线模式")
        self.tab_votes = self.tabs.add("票据与SQL")
        self.tab_settings = self.tabs.add("设置")

        self._build_guide_tab()
        self._build_dashboard_tab()
        self._build_questionnaire_tab()
        self._build_roster_tab()
        self._build_server_tab()
        self._build_offline_tab()
        self._build_votes_tab()
        self._build_settings_tab()

    def _build_design_disabled_tab(self, tab: ctk.CTkFrame, title: str) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        panel = ctk.CTkFrame(tab, corner_radius=14)
        panel.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(panel, text=title, font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 8)
        )
        ctk.CTkLabel(
            panel,
            text=(
                "当前版本已按你的要求移除旧问卷设计逻辑。\n"
                "该模块暂时停用，等待你提供新的设计方案后重建。"
            ),
            justify="left",
            text_color="#51607d",
        ).grid(row=1, column=0, sticky="nw", padx=16, pady=(0, 16))

    def _notify_design_disabled(self) -> None:
        messagebox.showinfo("模块已停用", "问卷设计模块已停用，等待你提供新的设计方案。", parent=self)

    def _build_guide_tab(self) -> None:
        tab = self.tab_guide
        tab.grid_columnconfigure((0, 1), weight=1)
        tab.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(tab, corner_radius=14)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=12)
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="新手引导：按这 5 步就能完成一次问卷收集",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))
        ctk.CTkLabel(
            header,
            text=(
                "1) 建名单  2) 建问卷  3) 启用问卷  4) 启动局域网服务  5) 查看票据与SQL\n"
                "如果你想快速体验，可用下方“一键创建示例”按钮自动生成可用数据。"
            ),
            justify="left",
            text_color="#4e5f81",
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))

        left = ctk.CTkFrame(tab, corner_radius=14)
        left.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(12, 6), pady=(0, 12))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(left, text="当前完成度", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 8)
        )
        self.guide_status_text = ctk.CTkTextbox(left)
        self.guide_status_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        ctk.CTkButton(left, text="刷新引导状态", command=self._refresh_guide_status).grid(
            row=2, column=0, sticky="e", padx=12, pady=(0, 12)
        )

        right = ctk.CTkFrame(tab, corner_radius=14)
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 8))
        right.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(right, text="快速跳转", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 8)
        )
        ctk.CTkButton(right, text="去名单管理", command=lambda: self._switch_tab("名单管理")).grid(
            row=1, column=0, padx=6, pady=6, sticky="ew"
        )
        ctk.CTkButton(right, text="去问卷管理", command=lambda: self._switch_tab("问卷管理")).grid(
            row=1, column=1, padx=6, pady=6, sticky="ew"
        )
        ctk.CTkButton(right, text="去局域网服务", command=lambda: self._switch_tab("局域网服务")).grid(
            row=2, column=0, padx=6, pady=6, sticky="ew"
        )
        ctk.CTkButton(right, text="去SQL查询", command=lambda: self._switch_tab("票据与SQL")).grid(
            row=2, column=1, padx=6, pady=6, sticky="ew"
        )

        quick = ctk.CTkFrame(tab, corner_radius=14)
        quick.grid(row=2, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))
        quick.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(quick, text="一键创建示例", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 8)
        )
        ctk.CTkButton(quick, text="创建示例名单", command=self._quick_create_demo_roster).grid(
            row=1, column=0, padx=6, pady=6, sticky="ew"
        )
        ctk.CTkButton(
            quick,
            text="创建示例问卷（满意度）",
            command=lambda: self._quick_create_template_questionnaire("普通满意度调查"),
        ).grid(row=1, column=1, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(
            quick,
            text="创建示例问卷（名单逐人评分）",
            command=lambda: self._quick_create_template_questionnaire("指定对象评分"),
        ).grid(row=2, column=0, columnspan=2, padx=6, pady=(6, 10), sticky="ew")

    def _build_dashboard_tab(self) -> None:
        tab = self.tab_dashboard
        tab.grid_columnconfigure((0, 1, 2, 3), weight=1)
        tab.grid_rowconfigure(1, weight=1)

        self.card_q_count = self._metric_card(tab, 0, "问卷总数")
        self.card_s_count = self._metric_card(tab, 1, "票据总数")
        self.card_server = self._metric_card(tab, 2, "服务状态")
        self.card_rosters = self._metric_card(tab, 3, "名单总数")

        body = ctk.CTkFrame(tab, corner_radius=14)
        body.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=12, pady=12)
        body.grid_columnconfigure(0, weight=1)

        self.dashboard_text = ctk.CTkTextbox(body, height=360)
        self.dashboard_text.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)

        ctk.CTkButton(
            body,
            text="刷新概览",
            command=self._refresh_all,
            width=120,
            height=34,
        ).grid(row=1, column=0, sticky="e", padx=14, pady=(0, 12))

    def _metric_card(self, parent: ctk.CTkFrame, col: int, title: str) -> ctk.CTkLabel:
        card = ctk.CTkFrame(parent, corner_radius=14, fg_color="#ffffff")
        card.grid(row=0, column=col, sticky="nsew", padx=12, pady=12)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14), text_color="#5f6d89").pack(
            anchor="w", padx=16, pady=(14, 4)
        )
        val = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=30, weight="bold"), text_color="#1b2c4b")
        val.pack(anchor="w", padx=16, pady=(0, 14))
        return val

    def _build_questionnaire_tab(self) -> None:
        if self.use_new_board_designer:
            self._build_questionnaire_board_tab(self.tab_questionnaire)
            return
        if self.design_logic_disabled:
            self._build_design_disabled_tab(self.tab_questionnaire, "问卷设计模块已停用")
            return
        tab = self.tab_questionnaire
        tab.grid_columnconfigure(0, weight=1, minsize=380)
        tab.grid_columnconfigure(1, weight=1, minsize=580)
        tab.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(tab, corner_radius=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left, text="问卷列表", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 8)
        )

        list_wrap = ctk.CTkFrame(left, corner_radius=10, fg_color="#f8fbff")
        list_wrap.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        list_wrap.grid_rowconfigure(0, weight=1)
        list_wrap.grid_columnconfigure(0, weight=1)

        self.tree_questionnaires = ttk.Treeview(
            list_wrap,
            columns=("id", "title", "mode", "status"),
            show="headings",
            height=15,
        )
        for col, text, width in [
            ("id", "ID", 120),
            ("title", "标题", 180),
            ("mode", "模式", 80),
            ("status", "状态", 80),
        ]:
            self.tree_questionnaires.heading(col, text=text)
            self.tree_questionnaires.column(col, width=width, anchor="w")
        self.tree_questionnaires.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(list_wrap, orient="vertical", command=self.tree_questionnaires.yview).grid(
            row=0, column=1, sticky="ns"
        )

        btns = ctk.CTkFrame(left, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        btns.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkButton(btns, text="载入编辑", command=self._load_selected_questionnaire).grid(
            row=0, column=0, padx=4, sticky="ew"
        )
        ctk.CTkButton(btns, text="启用", command=lambda: self._set_selected_status("active")).grid(
            row=0, column=1, padx=4, sticky="ew"
        )
        ctk.CTkButton(btns, text="暂停", command=lambda: self._set_selected_status("paused")).grid(
            row=0, column=2, padx=4, sticky="ew"
        )
        ctk.CTkButton(btns, text="刷新", command=self._refresh_questionnaire_list).grid(
            row=0, column=3, padx=4, sticky="ew"
        )
        ctk.CTkButton(btns, text="重命名", command=self._rename_selected_questionnaire).grid(
            row=1, column=0, padx=4, pady=(6, 0), sticky="ew"
        )
        ctk.CTkButton(btns, text="复制", command=self._copy_selected_questionnaire).grid(
            row=1, column=1, padx=4, pady=(6, 0), sticky="ew"
        )
        ctk.CTkButton(btns, text="删除", command=self._delete_selected_questionnaire).grid(
            row=1, column=2, padx=4, pady=(6, 0), sticky="ew"
        )

        right = ctk.CTkScrollableFrame(tab, corner_radius=14)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="问卷编辑器", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 8)
        )

        template_bar = ctk.CTkFrame(right, fg_color="#f8fbff", corner_radius=12)
        template_bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        template_bar.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkLabel(template_bar, text="问卷模板（推荐场景）").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))
        self.template_var = ctk.StringVar(value=TEMPLATE_PLACEHOLDER)
        self.template_menu = ctk.CTkOptionMenu(template_bar, variable=self.template_var, values=TEMPLATE_OPTIONS)
        self.template_menu.grid(row=1, column=0, padx=10, pady=(6, 10), sticky="ew")
        ctk.CTkButton(template_bar, text="套用模板到编辑器", command=self._apply_selected_template).grid(
            row=1, column=1, padx=6, pady=(6, 10), sticky="ew"
        )
        ctk.CTkButton(template_bar, text="配置体检", command=self._check_draft_configuration).grid(
            row=1, column=2, padx=(6, 10), pady=(6, 10), sticky="ew"
        )

        form = ctk.CTkFrame(right, fg_color="#f8fbff", corner_radius=12)
        form.grid(row=2, column=0, sticky="ew", padx=8)
        form.grid_columnconfigure((0, 1), weight=1)

        self.entry_title = self._labeled_entry(form, "问卷标题", 0, 0)
        self.entry_passcode = self._labeled_entry(form, "访问口令（可选）", 0, 1, show="*")
        self.entry_desc = self._labeled_text(form, "问卷说明", 1, 0, 2, height=80)
        self.entry_intro = self._labeled_text(form, "引导文案（可选）", 2, 0, 2, height=64)

        mode_wrap = ctk.CTkFrame(form, fg_color="transparent")
        mode_wrap.grid(row=3, column=0, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(mode_wrap, text="身份模式").pack(anchor="w")
        self.mode_var = ctk.StringVar(value="实名")
        self.mode_menu = ctk.CTkOptionMenu(
            mode_wrap,
            variable=self.mode_var,
            values=list(MODE_LABEL_TO_VALUE.keys()),
            command=self._on_identity_mode_changed,
        )
        self.mode_menu.pack(fill="x", pady=(4, 0))

        repeat_wrap = ctk.CTkFrame(form, fg_color="transparent")
        repeat_wrap.grid(row=3, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(repeat_wrap, text="重复提交").pack(anchor="w")
        self.repeat_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(repeat_wrap, text="允许重复提交", variable=self.repeat_var).pack(anchor="w", pady=(8, 0))
        self.same_device_repeat_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(repeat_wrap, text="允许同设备重复提交", variable=self.same_device_repeat_var).pack(
            anchor="w", pady=(6, 0)
        )

        auth_wrap = ctk.CTkFrame(form, fg_color="transparent")
        auth_wrap.grid(row=4, column=0, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(auth_wrap, text="身份验证方式").pack(anchor="w")
        self.auth_mode_var = ctk.StringVar(value="开放作答")
        self.auth_mode_menu = ctk.CTkOptionMenu(
            auth_wrap,
            variable=self.auth_mode_var,
            values=list(AUTH_LABEL_TO_VALUE.keys()),
        )
        self.auth_mode_menu.pack(fill="x", pady=(4, 0))

        roster_bind_wrap = ctk.CTkFrame(form, fg_color="transparent")
        roster_bind_wrap.grid(row=4, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(roster_bind_wrap, text="绑定名单（名单校验时必选）").pack(anchor="w")
        self.auth_roster_var = ctk.StringVar(value="")
        self.auth_roster_menu = ctk.CTkOptionMenu(roster_bind_wrap, variable=self.auth_roster_var, values=[""])
        self.auth_roster_menu.pack(fill="x", pady=(4, 0))

        identity_collect = ctk.CTkFrame(form, fg_color="transparent")
        identity_collect.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(2, 10))
        identity_collect.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.collect_name_var = ctk.BooleanVar(value=False)
        self.name_required_var = ctk.BooleanVar(value=False)
        self.collect_code_var = ctk.BooleanVar(value=False)
        self.code_required_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(identity_collect, text="采集姓名", variable=self.collect_name_var).grid(
            row=0, column=0, padx=4, sticky="w"
        )
        ctk.CTkSwitch(identity_collect, text="姓名必填", variable=self.name_required_var).grid(
            row=0, column=1, padx=4, sticky="w"
        )
        ctk.CTkSwitch(identity_collect, text="采集编号", variable=self.collect_code_var).grid(
            row=0, column=2, padx=4, sticky="w"
        )
        ctk.CTkSwitch(identity_collect, text="编号必填", variable=self.code_required_var).grid(
            row=0, column=3, padx=4, sticky="w"
        )
        self._on_identity_mode_changed(self.mode_var.get())

        q_builder = ctk.CTkFrame(right, fg_color="#f8fbff", corner_radius=12)
        q_builder.grid(row=3, column=0, sticky="nsew", padx=8, pady=(10, 8))
        q_builder.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(q_builder, text="题目配置", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 6)
        )

        self.entry_q_title = self._labeled_entry(q_builder, "题目标题", 1, 0)
        self.entry_q_id = self._labeled_entry(q_builder, "题目ID（可选，留空自动生成）", 2, 0)

        kind_wrap = ctk.CTkFrame(q_builder, fg_color="transparent")
        kind_wrap.grid(row=3, column=0, sticky="ew", padx=10, pady=2)
        kind_wrap.grid_columnconfigure((0, 1), weight=1)

        left_k = ctk.CTkFrame(kind_wrap, fg_color="transparent")
        left_k.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(left_k, text="题型").pack(anchor="w")
        self.q_type = ctk.StringVar(value="单选")
        ctk.CTkOptionMenu(
            left_k,
            variable=self.q_type,
            values=list(QTYPE_LABEL_TO_VALUE.keys()),
        ).pack(fill="x", pady=(4, 0))

        right_k = ctk.CTkFrame(kind_wrap, fg_color="transparent")
        right_k.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ctk.CTkLabel(right_k, text="必填").pack(anchor="w")
        self.q_required = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(right_k, text="必填", variable=self.q_required).pack(anchor="w", pady=(8, 0))

        self.entry_q_options = self._labeled_text(q_builder, "选项（单选/多选每行一项）", 4, 0, 1, height=76)

        logic_wrap = ctk.CTkFrame(q_builder, fg_color="transparent")
        logic_wrap.grid(row=5, column=0, sticky="ew", padx=10, pady=4)
        logic_wrap.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.entry_visible_qid = self._small_labeled_entry(logic_wrap, "显示条件-题目ID", 0)
        self.entry_visible_value = self._small_labeled_entry(logic_wrap, "显示条件-值", 1)
        self.entry_repeat_from = self._small_labeled_entry(logic_wrap, "循环来源（题目ID或“名单”）", 2)
        repeat_filter_wrap = ctk.CTkFrame(logic_wrap, fg_color="transparent")
        repeat_filter_wrap.grid(row=0, column=3, sticky="ew", padx=6)
        ctk.CTkLabel(repeat_filter_wrap, text="循环项筛选").pack(anchor="w")
        self.repeat_filter_var = ctk.StringVar(value="全部循环项")
        self.repeat_filter_menu = ctk.CTkOptionMenu(
            repeat_filter_wrap,
            variable=self.repeat_filter_var,
            values=list(REPEAT_FILTER_LABEL_TO_VALUE.keys()),
        )
        self.repeat_filter_menu.pack(fill="x", pady=(4, 0))

        required_wrap = ctk.CTkFrame(q_builder, fg_color="transparent")
        required_wrap.grid(row=6, column=0, sticky="ew", padx=10, pady=(0, 4))
        required_wrap.grid_columnconfigure((0, 1, 2), weight=1)
        self.entry_required_qid = self._small_labeled_entry(required_wrap, "必填条件-题目ID", 0)
        self.entry_required_value = self._small_labeled_entry(required_wrap, "必填条件-值", 1)
        self.entry_logic_hint = self._small_labeled_entry(required_wrap, "逻辑提示（可选）", 2)
        self.entry_logic_hint.insert(0, "如：当上题=参加时必填")

        num_wrap = ctk.CTkFrame(q_builder, fg_color="transparent")
        num_wrap.grid(row=7, column=0, sticky="ew", padx=10, pady=4)
        num_wrap.grid_columnconfigure((0, 1, 2), weight=1)

        self.entry_max_select = self._small_labeled_entry(num_wrap, "最多可选", 0)
        self.entry_rating_min = self._small_labeled_entry(num_wrap, "评分最小", 1)
        self.entry_rating_max = self._small_labeled_entry(num_wrap, "评分最大", 2)
        self.entry_max_select.insert(0, "1")
        self.entry_rating_min.insert(0, "1")
        self.entry_rating_max.insert(0, "5")

        action_wrap = ctk.CTkFrame(q_builder, fg_color="transparent")
        action_wrap.grid(row=8, column=0, sticky="ew", padx=10, pady=(4, 10))
        action_wrap.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)
        self.btn_add_question = ctk.CTkButton(action_wrap, text="新增题目", command=self._add_question)
        self.btn_add_question.grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(action_wrap, text="编辑选中题目", command=self._edit_selected_question).grid(
            row=0, column=1, padx=4, sticky="ew"
        )
        ctk.CTkButton(action_wrap, text="复制选中题目", command=self._duplicate_selected_question).grid(
            row=0, column=2, padx=4, sticky="ew"
        )
        ctk.CTkButton(action_wrap, text="上移", command=self._move_question_up).grid(
            row=0, column=3, padx=4, sticky="ew"
        )
        ctk.CTkButton(action_wrap, text="下移", command=self._move_question_down).grid(
            row=0, column=4, padx=4, sticky="ew"
        )
        ctk.CTkButton(action_wrap, text="删除选中题目", command=self._remove_question).grid(
            row=0, column=5, padx=4, sticky="ew"
        )
        self.btn_cancel_edit_question = ctk.CTkButton(action_wrap, text="取消编辑", command=self._cancel_question_edit)
        self.btn_cancel_edit_question.grid(row=0, column=6, padx=4, sticky="ew")
        self.btn_cancel_edit_question.configure(state="disabled")

        self.q_edit_mode_var = ctk.StringVar(value="当前为新增模式。")
        ctk.CTkLabel(action_wrap, textvariable=self.q_edit_mode_var, text_color="#5f6d89").grid(
            row=1, column=0, columnspan=7, sticky="w", padx=4, pady=(6, 0)
        )

        self.tree_draft_questions = ttk.Treeview(
            q_builder, columns=("id", "title", "type", "required"), show="headings", height=7
        )
        for col, text, width in [
            ("id", "ID", 110),
            ("title", "题目", 280),
            ("type", "类型", 90),
            ("required", "必填", 80),
        ]:
            self.tree_draft_questions.heading(col, text=text)
            self.tree_draft_questions.column(col, width=width, anchor="w")
        self.tree_draft_questions.grid(row=9, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.tree_draft_questions.bind("<Double-1>", lambda _event: self._edit_selected_question())

        save_bar = ctk.CTkFrame(right, fg_color="transparent")
        save_bar.grid(row=4, column=0, sticky="ew", padx=8, pady=(4, 10))
        save_bar.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.btn_save_q = ctk.CTkButton(save_bar, text="保存问卷", height=36, command=self._save_questionnaire)
        self.btn_save_q.grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(save_bar, text="清空编辑器", height=36, command=self._clear_editor).grid(
            row=0, column=1, padx=4, sticky="ew"
        )
        ctk.CTkButton(save_bar, text="刷新列表", height=36, command=self._refresh_questionnaire_list).grid(
            row=0, column=2, padx=4, sticky="ew"
        )
        ctk.CTkButton(save_bar, text="快速诊断", height=36, command=self._check_draft_configuration).grid(
            row=0, column=3, padx=4, sticky="ew"
        )

    def _build_questionnaire_board_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=0, minsize=self.board_left_width)
        tab.grid_columnconfigure(1, weight=1, minsize=980)
        tab.grid_columnconfigure(2, weight=0, minsize=self.board_right_width)
        tab.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(tab, corner_radius=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        self.board_left_panel = left
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(left, text="问卷列表", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 8)
        )

        tree_wrap = ctk.CTkFrame(left, fg_color="#f8fbff", corner_radius=10)
        tree_wrap.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree_wrap.grid_columnconfigure(0, weight=1)
        self.tree_board_questionnaires = ttk.Treeview(
            tree_wrap,
            columns=("id", "title", "mode", "status"),
            show="headings",
            height=18,
        )
        for col, text, width in [
            ("id", "ID", 120),
            ("title", "标题", 165),
            ("mode", "模式", 70),
            ("status", "状态", 70),
        ]:
            self.tree_board_questionnaires.heading(col, text=text)
            self.tree_board_questionnaires.column(col, width=width, anchor="w")
        self.tree_board_questionnaires.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree_board_questionnaires.yview).grid(
            row=0, column=1, sticky="ns"
        )

        left_btns = ctk.CTkFrame(left, fg_color="transparent")
        left_btns.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        left_btns.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(left_btns, text="载入", command=self._board_load_selected_questionnaire).grid(
            row=0, column=0, padx=4, pady=4, sticky="ew"
        )
        ctk.CTkButton(left_btns, text="启用", command=lambda: self._board_set_selected_status("active")).grid(
            row=0, column=1, padx=4, pady=4, sticky="ew"
        )
        ctk.CTkButton(left_btns, text="暂停", command=lambda: self._board_set_selected_status("paused")).grid(
            row=0, column=2, padx=4, pady=4, sticky="ew"
        )
        ctk.CTkButton(left_btns, text="刷新列表", command=self._refresh_board_questionnaire_list).grid(
            row=1, column=0, columnspan=3, padx=4, pady=(0, 4), sticky="ew"
        )

        center = ctk.CTkFrame(tab, corner_radius=14)
        center.grid(row=0, column=1, sticky="nsew", padx=(6, 6), pady=12)
        self.board_center_panel = center
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(2, weight=1)

        head = ctk.CTkFrame(center, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="问卷展板设计器", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.board_toggle_left_btn = ctk.CTkButton(head, text="收起列表", width=96, command=self._board_toggle_left_panel)
        self.board_toggle_left_btn.grid(row=0, column=1, padx=4, sticky="e")
        self.board_toggle_right_btn = ctk.CTkButton(
            head, text="收起逻辑面板", width=110, command=self._board_toggle_right_panel
        )
        self.board_toggle_right_btn.grid(row=0, column=2, padx=4, sticky="e")
        self.board_focus_mode_btn = ctk.CTkButton(head, text="显示两侧", width=96, command=self._board_toggle_focus_mode)
        self.board_focus_mode_btn.grid(row=0, column=3, padx=4, sticky="e")
        ctk.CTkLabel(
            head,
            text="题目从上到下即真实作答顺序。循环仅允许在“循环块”中设置。",
            text_color="#506080",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        cfg = ctk.CTkFrame(center, fg_color="#f8fbff", corner_radius=12)
        cfg.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        cfg.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.board_entry_title = self._labeled_entry(cfg, "问卷标题", 0, 0)
        self.board_entry_passcode = self._labeled_entry(cfg, "访问口令（可选）", 0, 1, show="*")
        self.board_desc_text = self._labeled_text(cfg, "问卷说明", 1, 0, 2, height=64)
        self.board_intro_text = self._labeled_text(cfg, "引导文案（可选）", 1, 2, 2, height=64)

        mode_wrap = ctk.CTkFrame(cfg, fg_color="transparent")
        mode_wrap.grid(row=2, column=0, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(mode_wrap, text="身份模式").pack(anchor="w")
        self.board_mode_var = ctk.StringVar(value="实名")
        self.board_mode_menu = ctk.CTkOptionMenu(
            mode_wrap,
            variable=self.board_mode_var,
            values=list(MODE_LABEL_TO_VALUE.keys()),
            command=self._board_on_identity_mode_changed,
        )
        self.board_mode_menu.pack(fill="x", pady=(4, 0))

        repeat_wrap = ctk.CTkFrame(cfg, fg_color="transparent")
        repeat_wrap.grid(row=2, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(repeat_wrap, text="重复提交").pack(anchor="w")
        self.board_repeat_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(repeat_wrap, text="允许重复提交", variable=self.board_repeat_var).pack(anchor="w", pady=(8, 0))
        self.board_same_device_repeat_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(repeat_wrap, text="允许同设备重复提交", variable=self.board_same_device_repeat_var).pack(
            anchor="w", pady=(6, 0)
        )

        auth_wrap = ctk.CTkFrame(cfg, fg_color="transparent")
        auth_wrap.grid(row=2, column=2, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(auth_wrap, text="身份校验方式").pack(anchor="w")
        self.board_auth_mode_var = ctk.StringVar(value="开放作答")
        self.board_auth_mode_menu = ctk.CTkOptionMenu(
            auth_wrap,
            variable=self.board_auth_mode_var,
            values=list(AUTH_LABEL_TO_VALUE.keys()),
            command=lambda _value: self._board_sync_auto_lists(re_render=True),
        )
        self.board_auth_mode_menu.pack(fill="x", pady=(4, 0))

        roster_wrap = ctk.CTkFrame(cfg, fg_color="transparent")
        roster_wrap.grid(row=2, column=3, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(roster_wrap, text="绑定名单").pack(anchor="w")
        self.board_auth_roster_var = ctk.StringVar(value="")
        self.board_auth_roster_menu = ctk.CTkOptionMenu(
            roster_wrap,
            variable=self.board_auth_roster_var,
            values=[""],
            command=lambda _value: self._board_sync_auto_lists(re_render=True),
        )
        self.board_auth_roster_menu.pack(fill="x", pady=(4, 0))

        fields_wrap = ctk.CTkFrame(cfg, fg_color="transparent")
        fields_wrap.grid(row=3, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 8))
        fields_wrap.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.board_collect_name_var = ctk.BooleanVar(value=False)  # 兼容旧数据
        self.board_collect_code_var = ctk.BooleanVar(value=False)  # 兼容旧数据
        self.board_name_required_var = ctk.BooleanVar(value=False)  # 兼容旧数据
        self.board_code_required_var = ctk.BooleanVar(value=False)  # 兼容旧数据
        ctk.CTkLabel(fields_wrap, text="进入问卷前采集字段（全部必填）").grid(row=0, column=0, sticky="w", padx=4)
        self.board_collect_fields_summary_var = ctk.StringVar(value="未设置（不采集身份字段）")
        ctk.CTkLabel(
            fields_wrap,
            textvariable=self.board_collect_fields_summary_var,
            text_color="#506080",
            justify="left",
            wraplength=520,
        ).grid(row=1, column=0, columnspan=4, sticky="w", padx=4, pady=(2, 6))

        field_btns = ctk.CTkFrame(fields_wrap, fg_color="transparent")
        field_btns.grid(row=2, column=0, columnspan=4, sticky="ew", padx=2)
        field_btns.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(field_btns, text="配置采集字段", command=self._board_open_collect_fields_manager).grid(
            row=0, column=0, padx=4, sticky="ew"
        )
        ctk.CTkButton(field_btns, text="从名单字段填入", command=self._board_fill_collect_fields_from_roster).grid(
            row=0, column=1, padx=4, sticky="ew"
        )
        ctk.CTkButton(field_btns, text="清空采集字段", command=self._board_clear_collect_fields).grid(
            row=0, column=2, padx=4, sticky="ew"
        )

        tpl_wrap = ctk.CTkFrame(cfg, fg_color="transparent")
        tpl_wrap.grid(row=4, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 10))
        tpl_wrap.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        ctk.CTkLabel(tpl_wrap, text="模板").grid(row=0, column=0, padx=4, sticky="w")
        self.board_template_var = ctk.StringVar(value=TEMPLATE_PLACEHOLDER)
        self.board_template_menu = ctk.CTkOptionMenu(
            tpl_wrap,
            variable=self.board_template_var,
            values=TEMPLATE_OPTIONS,
        )
        self.board_template_menu.grid(row=0, column=1, columnspan=2, padx=4, sticky="ew")
        ctk.CTkButton(tpl_wrap, text="套用模板", command=self._board_apply_selected_template).grid(
            row=0, column=3, padx=4, sticky="ew"
        )
        ctk.CTkButton(tpl_wrap, text="新建空白", command=self._board_new_draft).grid(row=0, column=4, padx=4, sticky="ew")
        ctk.CTkButton(tpl_wrap, text="保存问卷", command=self._board_save_questionnaire).grid(
            row=0, column=5, padx=(4, 0), sticky="ew"
        )

        tool = ctk.CTkFrame(center, fg_color="#f8fbff", corner_radius=12)
        tool.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tool.grid_columnconfigure(0, weight=1)
        tool.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(tool, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8))
        bar.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        ctk.CTkButton(bar, text="添加普通题", command=self._board_add_top_question).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bar, text="添加循环块", command=self._board_add_loop_block).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(bar, text="列表管理", command=self._board_open_list_manager).grid(row=0, column=2, padx=4, sticky="ew")
        ctk.CTkButton(bar, text="联合规则", command=self._board_open_validation_rule_manager).grid(row=0, column=3, padx=4, sticky="ew")
        ctk.CTkButton(bar, text="配置体检", command=self._board_check_configuration).grid(row=0, column=4, padx=4, sticky="ew")
        ctk.CTkButton(bar, text="刷新展板", command=self._board_render_canvas).grid(row=0, column=5, padx=4, sticky="ew")

        self.board_canvas = ctk.CTkScrollableFrame(tool, corner_radius=10, fg_color="#ffffff")
        self.board_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.board_canvas.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(tab, corner_radius=14)
        right.grid(row=0, column=2, sticky="nsew", padx=(6, 12), pady=12)
        self.board_right_panel = right
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(5, weight=1)
        right_head = ctk.CTkFrame(right, fg_color="transparent")
        right_head.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        right_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(right_head, text="逻辑面板", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )

        def show_logic_help() -> None:
            messagebox.showinfo(
                "面板使用说明",
                (
                    "不需要写代码，按下面三步即可：\n"
                    "1. 先点题目卡片上的“逻辑”，选中目标题目。\n"
                    "2. 填“条件来源题目ID + 比较方式 + 比较值”。\n"
                    "3. 点“写入显示条件”或“写入必填条件”，再点“保存逻辑”。\n\n"
                    "联合限制（比如人数上限）请点展板上方“联合规则”，\n"
                    "用“单条聚合 SQL + 比较条件”的方式配置。"
                ),
                parent=self,
            )

        ctk.CTkButton(right_head, text="i", width=30, command=show_logic_help).grid(row=0, column=1, sticky="e")
        self.board_logic_target_var = ctk.StringVar(value="未选择题目/块")
        ctk.CTkLabel(right, textvariable=self.board_logic_target_var, text_color="#4f5f7f").grid(
            row=1, column=0, sticky="w", padx=12, pady=(0, 8)
        )

        quick = ctk.CTkFrame(right, fg_color="#f8fbff", corner_radius=10)
        quick.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        quick.grid_columnconfigure((0, 1), weight=1)
        self.board_logic_source_qid = self._labeled_entry(quick, "条件来源题目ID", 0, 0)
        op_box = ctk.CTkFrame(quick, fg_color="transparent")
        op_box.grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(op_box, text="比较方式").pack(anchor="w")
        self.board_logic_op_var = ctk.StringVar(value="等于")
        ctk.CTkOptionMenu(op_box, variable=self.board_logic_op_var, values=list(LOGIC_OP_LABEL_TO_VALUE.keys())).pack(
            fill="x", pady=(4, 0)
        )
        self.board_logic_value_entry = self._labeled_entry(quick, "比较值（可选）", 1, 0)
        quick_btn = ctk.CTkFrame(quick, fg_color="transparent")
        quick_btn.grid(row=1, column=1, sticky="ew", padx=10, pady=8)
        quick_btn.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(quick_btn, text="写入显示条件", command=lambda: self._board_fill_rule_box("visible")).grid(
            row=0, column=0, padx=4, sticky="ew"
        )
        ctk.CTkButton(quick_btn, text="写入必填条件", command=lambda: self._board_fill_rule_box("required")).grid(
            row=0, column=1, padx=4, sticky="ew"
        )

        self.board_visible_rule_text = self._labeled_text(right, "显示条件规则", 3, 0, 1, height=92)
        self.board_required_rule_text = self._labeled_text(right, "必填条件规则", 4, 0, 1, height=92)

        logic_ops = ctk.CTkFrame(right, fg_color="#f8fbff", corner_radius=10)
        logic_ops.grid(row=5, column=0, sticky="nsew", padx=12, pady=(0, 8))
        logic_ops.grid_columnconfigure((0, 1), weight=1)
        rf_box = ctk.CTkFrame(logic_ops, fg_color="transparent")
        rf_box.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(rf_box, text="循环项筛选").pack(anchor="w")
        self.board_repeat_filter_var = ctk.StringVar(value="全部循环项")
        self.board_repeat_filter_menu = ctk.CTkOptionMenu(
            rf_box,
            variable=self.board_repeat_filter_var,
            values=list(REPEAT_FILTER_LABEL_TO_VALUE.keys()),
        )
        self.board_repeat_filter_menu.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(
            logic_ops,
            text=(
                "说明：此处只负责题目显隐/必填/循环筛选逻辑。\n"
                "统计请到“票据与SQL”页使用 SQL 查询完成。"
            ),
            text_color="#586a8c",
            justify="left",
            wraplength=260,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))
        logic_btns = ctk.CTkFrame(logic_ops, fg_color="transparent")
        logic_btns.grid(row=2, column=1, sticky="ew", padx=10, pady=(0, 10))
        logic_btns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(logic_btns, text="保存逻辑", command=self._board_save_logic_panel).grid(
            row=0, column=0, padx=4, sticky="ew"
        )
        ctk.CTkButton(logic_btns, text="清空逻辑", command=self._board_clear_logic_panel).grid(
            row=0, column=1, padx=4, sticky="ew"
        )

        self._board_new_draft(show_message=False)
        self._refresh_board_questionnaire_list()
        self._board_on_identity_mode_changed(self.board_mode_var.get())
        self._board_apply_panel_layout()

    def _board_toggle_left_panel(self) -> None:
        self.board_left_collapsed = not self.board_left_collapsed
        self._board_apply_panel_layout()

    def _board_toggle_right_panel(self) -> None:
        self.board_right_collapsed = not self.board_right_collapsed
        self._board_apply_panel_layout()

    def _board_toggle_focus_mode(self) -> None:
        if self.board_left_collapsed and self.board_right_collapsed:
            self.board_left_collapsed = False
            self.board_right_collapsed = False
        else:
            self.board_left_collapsed = True
            self.board_right_collapsed = True
        self._board_apply_panel_layout()

    def _board_apply_panel_layout(self) -> None:
        if not hasattr(self, "tab_questionnaire"):
            return
        tab = self.tab_questionnaire
        if self.board_left_collapsed:
            if hasattr(self, "board_left_panel"):
                self.board_left_panel.grid_remove()
            tab.grid_columnconfigure(0, minsize=0, weight=0)
            if hasattr(self, "board_toggle_left_btn"):
                self.board_toggle_left_btn.configure(text="显示列表")
        else:
            if hasattr(self, "board_left_panel"):
                self.board_left_panel.grid()
            tab.grid_columnconfigure(0, minsize=self.board_left_width, weight=0)
            if hasattr(self, "board_toggle_left_btn"):
                self.board_toggle_left_btn.configure(text="收起列表")

        if self.board_right_collapsed:
            if hasattr(self, "board_right_panel"):
                self.board_right_panel.grid_remove()
            tab.grid_columnconfigure(2, minsize=0, weight=0)
            if hasattr(self, "board_toggle_right_btn"):
                self.board_toggle_right_btn.configure(text="显示逻辑面板")
        else:
            if hasattr(self, "board_right_panel"):
                self.board_right_panel.grid()
            tab.grid_columnconfigure(2, minsize=self.board_right_width, weight=0)
            if hasattr(self, "board_toggle_right_btn"):
                self.board_toggle_right_btn.configure(text="收起逻辑面板")

        if hasattr(self, "board_focus_mode_btn"):
            if self.board_left_collapsed and self.board_right_collapsed:
                self.board_focus_mode_btn.configure(text="显示两侧")
            else:
                self.board_focus_mode_btn.configure(text="专注设计")

    def _board_on_identity_mode_changed(self, mode_label: str) -> None:
        _ = MODE_LABEL_TO_VALUE.get(mode_label, "realname")
        self._board_refresh_collect_fields_summary()

    def _board_clone(self, value: Any) -> Any:
        return json.loads(json.dumps(value, ensure_ascii=False))

    def _board_new_block_id(self) -> str:
        return f"b_{make_question_id().split('_', 1)[1]}"

    def _board_default_question(self, in_loop: bool = False) -> Dict[str, Any]:
        question = {
            "id": make_question_id(),
            "title": "请填写题目",
            "type": "single",
            "required": True,
            "options": ["选项1", "选项2"],
            "max_select": 2,
            "min_select": 1,
            "min": 1,
            "max": 5,
            "step": 1,
            "min_length": 0,
            "max_length": 0,
            "min_words": 0,
            "max_words": 0,
            "max_lines": 0,
            "visible_if": None,
            "required_if": None,
            "repeat_filter": "all",
        }
        if not in_loop:
            question.pop("repeat_filter", None)
        return question

    def _board_default_loop_block(self) -> Dict[str, Any]:
        return {
            "kind": "loop",
            "block_id": self._board_new_block_id(),
            "title": "循环块",
            "description": "",
            "repeat_from": "",
            "visible_if": None,
            "inner_questions": [self._board_default_question(in_loop=True)],
        }

    def _board_normalize_collect_fields(self, raw_fields: Any) -> List[Dict[str, str]]:
        if not isinstance(raw_fields, list):
            return []
        result: List[Dict[str, str]] = []
        seen: set[str] = set()
        for idx, item in enumerate(raw_fields, start=1):
            if isinstance(item, dict):
                key = str(item.get("key", "")).strip() or f"field_{idx}"
                label = str(item.get("label", "")).strip() or key
            else:
                label = str(item or "").strip()
                key = label or f"field_{idx}"
            key = key.replace(" ", "_").replace("-", "_")
            if not key or key in seen:
                continue
            seen.add(key)
            result.append({"key": key, "label": label})
        return result

    def _board_refresh_collect_fields_summary(self) -> None:
        if not hasattr(self, "board_collect_fields_summary_var"):
            return
        fields = self._board_normalize_collect_fields(self.board_collect_fields)
        self.board_collect_fields = fields
        if not fields:
            self.board_collect_fields_summary_var.set("未设置（不采集身份字段）")
            return
        labels = [str(item.get("label", item.get("key", ""))).strip() for item in fields]
        self.board_collect_fields_summary_var.set(f"已设置 {len(fields)} 项：{'、'.join(labels)}（全部必填）")

    def _board_clear_collect_fields(self) -> None:
        self.board_collect_fields = []
        self._board_refresh_collect_fields_summary()

    def _board_fill_collect_fields_from_roster(self) -> None:
        roster_id = self._extract_qid(self.board_auth_roster_var.get())
        if not roster_id:
            messagebox.showwarning("提示", "请先选择绑定名单。", parent=self)
            return
        columns = self.service.get_roster_columns(roster_id)
        if not columns:
            messagebox.showwarning("提示", "该名单没有可用字段。", parent=self)
            return
        self.board_collect_fields = [
            {"key": str(col.get("key", "")).strip(), "label": str(col.get("label", "")).strip() or str(col.get("key", "")).strip()}
            for col in columns
            if str(col.get("key", "")).strip()
        ]
        self._board_refresh_collect_fields_summary()
        messagebox.showinfo("完成", "已从名单字段填入进入前采集项。", parent=self)

    def _board_open_collect_fields_manager(self) -> None:
        win = tk.Toplevel(self)
        win.title("配置进入前采集字段")
        win.geometry("700x520")
        win.transient(self)
        win.grab_set()

        local_fields = self._board_normalize_collect_fields(self.board_collect_fields)

        wrap = ctk.CTkFrame(win, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=12, pady=12)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(wrap, text="进入前采集字段（全部必填）", font=ctk.CTkFont(size=17, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        tree_wrap = ctk.CTkFrame(wrap, fg_color="#f8fbff", corner_radius=10)
        tree_wrap.grid(row=1, column=0, sticky="nsew")
        tree_wrap.grid_columnconfigure(0, weight=1)
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree = ttk.Treeview(tree_wrap, columns=("key", "label"), show="headings", height=14)
        tree.heading("key", text="字段键")
        tree.heading("label", text="显示名称")
        tree.column("key", width=240, anchor="w")
        tree.column("label", width=260, anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(tree_wrap, orient="vertical", command=tree.yview).grid(row=0, column=1, sticky="ns")

        def refresh_tree() -> None:
            for iid in tree.get_children():
                tree.delete(iid)
            for idx, field in enumerate(local_fields):
                tree.insert("", "end", iid=str(idx), values=(field.get("key", ""), field.get("label", "")))

        btns = ctk.CTkFrame(wrap, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        btns.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        def add_field() -> None:
            label = simpledialog.askstring("新增字段", "请输入字段显示名称：", parent=win) or ""
            label = label.strip()
            if not label:
                return
            key = simpledialog.askstring("字段键", "请输入字段键（建议英文/数字/下划线，可留空自动）：", parent=win) or ""
            key = key.strip() or label
            key = key.replace(" ", "_").replace("-", "_")
            if any(str(item.get("key", "")).strip() == key for item in local_fields):
                messagebox.showwarning("提示", "字段键重复。", parent=win)
                return
            local_fields.append({"key": key, "label": label})
            refresh_tree()

        def remove_selected() -> None:
            selected = tree.selection()
            if not selected:
                return
            idx = int(str(selected[0]))
            if idx < 0 or idx >= len(local_fields):
                return
            local_fields.pop(idx)
            refresh_tree()

        def edit_selected() -> None:
            selected = tree.selection()
            if not selected:
                return
            idx = int(str(selected[0]))
            if idx < 0 or idx >= len(local_fields):
                return
            field = local_fields[idx]
            new_label = simpledialog.askstring("修改字段", "显示名称：", initialvalue=str(field.get("label", "")), parent=win)
            if new_label is None:
                return
            new_label = new_label.strip()
            if not new_label:
                messagebox.showwarning("提示", "显示名称不能为空。", parent=win)
                return
            new_key = simpledialog.askstring("修改字段", "字段键：", initialvalue=str(field.get("key", "")), parent=win)
            if new_key is None:
                return
            new_key = new_key.strip().replace(" ", "_").replace("-", "_")
            if not new_key:
                messagebox.showwarning("提示", "字段键不能为空。", parent=win)
                return
            if any(i != idx and str(item.get("key", "")).strip() == new_key for i, item in enumerate(local_fields)):
                messagebox.showwarning("提示", "字段键重复。", parent=win)
                return
            local_fields[idx] = {"key": new_key, "label": new_label}
            refresh_tree()

        def import_from_roster() -> None:
            roster_id = self._extract_qid(self.board_auth_roster_var.get())
            if not roster_id:
                messagebox.showwarning("提示", "请先在主界面选择绑定名单。", parent=win)
                return
            columns = self.service.get_roster_columns(roster_id)
            if not columns:
                messagebox.showwarning("提示", "该名单没有可用字段。", parent=win)
                return
            local_fields.clear()
            for col in columns:
                key = str(col.get("key", "")).strip()
                label = str(col.get("label", "")).strip() or key
                if key:
                    local_fields.append({"key": key, "label": label})
            refresh_tree()

        def save_and_close() -> None:
            self.board_collect_fields = self._board_normalize_collect_fields(local_fields)
            self._board_refresh_collect_fields_summary()
            win.destroy()

        ctk.CTkButton(btns, text="新增字段", command=add_field).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(btns, text="修改选中", command=edit_selected).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(btns, text="删除选中", command=remove_selected).grid(row=0, column=2, padx=4, sticky="ew")
        ctk.CTkButton(btns, text="按名单字段填入", command=import_from_roster).grid(row=0, column=3, padx=4, sticky="ew")
        ctk.CTkButton(btns, text="保存并关闭", command=save_and_close).grid(row=0, column=4, padx=4, sticky="ew")
        ctk.CTkButton(btns, text="取消", command=win.destroy).grid(row=0, column=5, padx=4, sticky="ew")

        refresh_tree()

    def _board_collect_identity_fields(self) -> Dict[str, Any]:
        fields = self._board_normalize_collect_fields(self.board_collect_fields)
        self.board_collect_fields = fields
        collect_name = any(str(item.get("key", "")).strip() == "member_name" for item in fields)
        collect_code = any(str(item.get("key", "")).strip() == "member_code" for item in fields)
        self.board_collect_name_var.set(collect_name)
        self.board_collect_code_var.set(collect_code)
        self.board_name_required_var.set(collect_name)
        self.board_code_required_var.set(collect_code)
        return {
            "collect_fields": fields,
            "collect_name": collect_name,
            "collect_code": collect_code,
            "name_required": collect_name,
            "code_required": collect_code,
            "allow_same_device_repeat": bool(self.board_same_device_repeat_var.get()),
        }

    def _board_find_item_index(self, block_id: str) -> int:
        for idx, item in enumerate(self.board_items):
            if str(item.get("block_id", "")).strip() == block_id:
                return idx
        return -1

    def _board_find_inner_index(self, block_id: str, question_id: str) -> int:
        block = next((x for x in self.board_items if str(x.get("block_id", "")) == block_id), None)
        if not block or block.get("kind") != "loop":
            return -1
        inner = block.get("inner_questions", [])
        for idx, q in enumerate(inner):
            if str(q.get("id", "")).strip() == question_id:
                return idx
        return -1

    def _board_new_draft(self, show_message: bool = True) -> None:
        self.editing_qid = None
        self.board_entry_title.delete(0, "end")
        self.board_entry_passcode.delete(0, "end")
        self.board_desc_text.delete("1.0", "end")
        self.board_intro_text.delete("1.0", "end")
        self.board_mode_var.set("实名")
        self.board_repeat_var.set(False)
        self.board_same_device_repeat_var.set(False)
        self.board_auth_mode_var.set("开放作答")
        self.board_auth_roster_var.set("")
        self.board_collect_fields = []
        self.board_collect_name_var.set(False)
        self.board_collect_code_var.set(False)
        self.board_name_required_var.set(False)
        self.board_code_required_var.set(False)
        self._board_refresh_collect_fields_summary()
        self.board_template_var.set(TEMPLATE_PLACEHOLDER)
        self.board_list_objects = []
        self.board_validation_rules = []
        self.board_template_meta = {}
        self.board_items = [
            {
                "kind": "question",
                "block_id": self._board_new_block_id(),
                "question": self._board_default_question(in_loop=False),
                "visible_if": None,
            }
        ]
        self.board_logic_target = None
        self.board_selected_card_id = ""
        self._board_sync_auto_lists(re_render=False)
        self._board_clear_logic_panel(silent=True)
        self._board_render_canvas()
        if show_message:
            messagebox.showinfo("已重置", "已创建新的空白问卷草稿。", parent=self)

    def _refresh_board_questionnaire_list(self) -> None:
        if not hasattr(self, "tree_board_questionnaires"):
            return
        items = self.service.list_questionnaires(active_only=False)
        for i in self.tree_board_questionnaires.get_children():
            self.tree_board_questionnaires.delete(i)
        for q in items:
            self.tree_board_questionnaires.insert(
                "",
                "end",
                values=(q["id"], q["title"], _pretty_mode(q["identity_mode"]), q["status"]),
            )

    def _board_selected_questionnaire_id(self) -> str:
        if not hasattr(self, "tree_board_questionnaires"):
            return ""
        selected = self.tree_board_questionnaires.selection()
        if not selected:
            return ""
        values = self.tree_board_questionnaires.item(selected[0], "values")
        return str(values[0]).strip() if values else ""

    def _board_set_selected_status(self, status: str) -> None:
        qid = self._board_selected_questionnaire_id()
        if not qid:
            messagebox.showwarning("提示", "请先选择问卷。", parent=self)
            return
        self.service.db.set_questionnaire_status(qid, status)
        self._refresh_all()

    def _board_add_top_question(self) -> None:
        self.board_items.append(
            {
                "kind": "question",
                "block_id": self._board_new_block_id(),
                "question": self._board_default_question(in_loop=False),
                "visible_if": None,
            }
        )
        self._board_render_canvas()

    def _board_add_loop_block(self) -> None:
        self.board_items.append(self._board_default_loop_block())
        self._board_render_canvas()

    def _board_add_inner_question(self, block_id: str) -> None:
        idx = self._board_find_item_index(block_id)
        if idx < 0:
            return
        item = self.board_items[idx]
        if item.get("kind") != "loop":
            return
        inner = item.setdefault("inner_questions", [])
        inner.append(self._board_default_question(in_loop=True))
        self._board_render_canvas()

    def _board_move_item(self, block_id: str, offset: int) -> None:
        idx = self._board_find_item_index(block_id)
        if idx < 0:
            return
        self._board_move_item_at(idx, offset)

    def _board_move_item_at(self, item_index: int, offset: int) -> None:
        if item_index < 0 or item_index >= len(self.board_items):
            return
        target = item_index + offset
        if target < 0 or target >= len(self.board_items):
            return
        self.board_items[item_index], self.board_items[target] = self.board_items[target], self.board_items[item_index]
        self._board_render_canvas()

    def _board_duplicate_item(self, block_id: str) -> None:
        idx = self._board_find_item_index(block_id)
        if idx < 0:
            return
        clone = self._board_clone(self.board_items[idx])
        clone["block_id"] = self._board_new_block_id()
        if clone.get("kind") == "question":
            clone["question"]["id"] = make_question_id()
        elif clone.get("kind") == "loop":
            for q in clone.get("inner_questions", []):
                q["id"] = make_question_id()
        self.board_items.insert(idx + 1, clone)
        self._board_render_canvas()

    def _board_remove_item(self, block_id: str) -> None:
        idx = self._board_find_item_index(block_id)
        if idx < 0:
            return
        self.board_items.pop(idx)
        if not self.board_items:
            self._board_add_top_question()
            return
        self._board_render_canvas()

    def _board_move_inner(self, block_id: str, question_id: str, offset: int) -> None:
        idx = self._board_find_item_index(block_id)
        if idx < 0:
            return
        item = self.board_items[idx]
        if item.get("kind") != "loop":
            return
        inner = item.get("inner_questions", [])
        qidx = self._board_find_inner_index(block_id, question_id)
        if qidx < 0:
            return
        self._board_move_inner_at(block_id, qidx, offset)

    def _board_move_inner_at(self, block_id: str, inner_index: int, offset: int) -> None:
        idx = self._board_find_item_index(block_id)
        if idx < 0:
            return
        item = self.board_items[idx]
        if item.get("kind") != "loop":
            return
        inner = item.get("inner_questions", [])
        if inner_index < 0 or inner_index >= len(inner):
            return
        target = inner_index + offset
        if target < 0 or target >= len(inner):
            return
        inner[inner_index], inner[target] = inner[target], inner[inner_index]
        self._board_render_canvas()

    def _board_duplicate_inner(self, block_id: str, question_id: str) -> None:
        idx = self._board_find_item_index(block_id)
        if idx < 0:
            return
        item = self.board_items[idx]
        if item.get("kind") != "loop":
            return
        inner = item.get("inner_questions", [])
        qidx = self._board_find_inner_index(block_id, question_id)
        if qidx < 0:
            return
        clone = self._board_clone(inner[qidx])
        clone["id"] = make_question_id()
        inner.insert(qidx + 1, clone)
        self._board_render_canvas()

    def _board_remove_inner(self, block_id: str, question_id: str) -> None:
        idx = self._board_find_item_index(block_id)
        if idx < 0:
            return
        item = self.board_items[idx]
        if item.get("kind") != "loop":
            return
        inner = item.get("inner_questions", [])
        qidx = self._board_find_inner_index(block_id, question_id)
        if qidx < 0:
            return
        inner.pop(qidx)
        if not inner:
            inner.append(self._board_default_question(in_loop=True))
        self._board_render_canvas()

    def _board_sync_auto_lists(self, re_render: bool = True) -> None:
        keep: List[Dict[str, Any]] = []
        for obj in self.board_list_objects:
            if str(obj.get("source", "")).startswith("roster_auto:"):
                continue
            keep.append(obj)

        roster_id = self._extract_qid(self.board_auth_roster_var.get())
        if roster_id:
            keep.extend(self.service.build_roster_column_list_objects(roster_id))

        self.board_list_objects = keep
        if re_render:
            self._board_render_canvas()

    def _board_repeat_source_choices(self) -> Dict[str, str]:
        choices: Dict[str, str] = {}
        for obj in self.board_list_objects:
            name = str(obj.get("name", "")).strip()
            if not name:
                continue
            choices[f"列表：{name}"] = f"__list__:{name}"
        for item in self.board_items:
            if item.get("kind") == "question":
                q = item.get("question", {})
                if str(q.get("type", "")) == "multi":
                    qid = str(q.get("id", "")).strip()
                    if qid:
                        choices[f"题目：{qid}（多选结果）"] = qid
            elif item.get("kind") == "loop":
                for q in item.get("inner_questions", []):
                    if str(q.get("type", "")) == "multi":
                        qid = str(q.get("id", "")).strip()
                        if qid:
                            choices[f"题目：{qid}（多选结果）"] = qid
        return choices

    def _board_parse_rule_text(self, widget: ctk.CTkTextbox) -> Optional[Dict[str, Any]]:
        raw = widget.get("1.0", "end").strip()
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except Exception as exc:
            raise ServiceError(f"规则 JSON 解析失败：{exc}") from exc
        if not isinstance(parsed, dict):
            raise ServiceError("规则必须是 JSON 对象。")
        return parsed

    def _board_fill_rule_box(self, target: str) -> None:
        if not self.board_logic_target:
            messagebox.showwarning("提示", "请先在展板中选择题目或块。", parent=self)
            return
        source_qid = self.board_logic_source_qid.get().strip()
        if not source_qid:
            messagebox.showwarning("提示", "请填写条件来源题目ID。", parent=self)
            return
        op_label = self.board_logic_op_var.get().strip()
        op = LOGIC_OP_LABEL_TO_VALUE.get(op_label, "equals")
        value_raw = self.board_logic_value_entry.get().strip()
        rule: Dict[str, Any] = {"question_id": source_qid, "op": op}
        if op not in {"not_empty", "empty"}:
            if value_raw == "":
                messagebox.showwarning("提示", "当前比较方式需要填写比较值。", parent=self)
                return
            try:
                if value_raw.isdigit():
                    rule["value"] = int(value_raw)
                else:
                    rule["value"] = float(value_raw)
            except Exception:
                rule["value"] = value_raw

        if target == "visible":
            self.board_visible_rule_text.delete("1.0", "end")
            self.board_visible_rule_text.insert("1.0", json.dumps(rule, ensure_ascii=False, indent=2))
        else:
            self.board_required_rule_text.delete("1.0", "end")
            self.board_required_rule_text.insert("1.0", json.dumps(rule, ensure_ascii=False, indent=2))

    def _board_clear_logic_panel(self, silent: bool = False) -> None:
        self.board_logic_source_qid.delete(0, "end")
        self.board_logic_op_var.set("等于")
        self.board_logic_value_entry.delete(0, "end")
        self.board_visible_rule_text.delete("1.0", "end")
        self.board_required_rule_text.delete("1.0", "end")
        self.board_repeat_filter_var.set("全部循环项")
        if not silent:
            self.board_logic_target = None
            self.board_logic_target_var.set("未选择题目/块")
            self.board_selected_card_id = ""
            self._board_render_canvas()

    def _board_find_question_ref(self, block_id: str, question_id: str) -> Optional[Dict[str, Any]]:
        idx = self._board_find_item_index(block_id)
        if idx < 0:
            return None
        item = self.board_items[idx]
        if item.get("kind") == "question":
            q = item.get("question", {})
            if not question_id or str(q.get("id", "")) == question_id:
                return q
            return None
        for q in item.get("inner_questions", []):
            if str(q.get("id", "")) == question_id:
                return q
        return None

    def _board_set_logic_target(self, target: Dict[str, str]) -> None:
        self.board_logic_target = target
        target_kind = target.get("kind", "")
        block_id = target.get("block_id", "")
        question_id = target.get("question_id", "")

        title = "未选择题目/块"
        visible_rule = None
        required_rule = None
        repeat_filter = "all"
        self.board_selected_card_id = target.get("card_id", "")

        idx = self._board_find_item_index(block_id)
        if idx >= 0:
            item = self.board_items[idx]
            if target_kind == "block" and item.get("kind") == "loop":
                title = f"循环块：{item.get('title', '')}"
                visible_rule = item.get("visible_if")
            else:
                q = self._board_find_question_ref(block_id, question_id)
                if q:
                    title = f"题目：{q.get('title', '')}（{q.get('id', '')}）"
                    visible_rule = q.get("visible_if")
                    required_rule = q.get("required_if")
                    repeat_filter = str(q.get("repeat_filter", "all")).strip().lower() or "all"

        self.board_logic_target_var.set(title)
        self.board_visible_rule_text.delete("1.0", "end")
        self.board_required_rule_text.delete("1.0", "end")
        if isinstance(visible_rule, dict):
            self.board_visible_rule_text.insert("1.0", json.dumps(visible_rule, ensure_ascii=False, indent=2))
        if isinstance(required_rule, dict):
            self.board_required_rule_text.insert("1.0", json.dumps(required_rule, ensure_ascii=False, indent=2))
        self.board_repeat_filter_var.set(REPEAT_FILTER_VALUE_TO_LABEL.get(repeat_filter, "全部循环项"))
        self._board_render_canvas()

    def _board_save_logic_panel(self) -> None:
        if not self.board_logic_target:
            messagebox.showwarning("提示", "请先选择题目或循环块。", parent=self)
            return
        target = self.board_logic_target
        target_kind = target.get("kind", "")
        block_id = target.get("block_id", "")
        question_id = target.get("question_id", "")
        idx = self._board_find_item_index(block_id)
        if idx < 0:
            return
        try:
            visible = self._board_parse_rule_text(self.board_visible_rule_text)
            required = self._board_parse_rule_text(self.board_required_rule_text)
        except ServiceError as exc:
            messagebox.showerror("保存失败", str(exc), parent=self)
            return

        if target_kind == "block":
            item = self.board_items[idx]
            if item.get("kind") == "loop":
                item["visible_if"] = visible
        else:
            q = self._board_find_question_ref(block_id, question_id)
            if q is None:
                return
            q["visible_if"] = visible
            q["required_if"] = required
            if target.get("in_loop") == "1":
                q["repeat_filter"] = REPEAT_FILTER_LABEL_TO_VALUE.get(self.board_repeat_filter_var.get(), "all")
            else:
                q.pop("repeat_filter", None)
        self._board_render_canvas()
        messagebox.showinfo("已保存", "逻辑配置已保存到当前题目/块。", parent=self)

    def _board_apply_selected_template(self) -> None:
        template_name = self.board_template_var.get().strip()
        if template_name == TEMPLATE_PLACEHOLDER:
            messagebox.showwarning("提示", "请先选择模板。", parent=self)
            return
        payload = self._template_payload(template_name)
        if not payload:
            messagebox.showerror("失败", "模板不存在。", parent=self)
            return
        schema = payload.get("schema", {}) if isinstance(payload.get("schema"), dict) else {}
        self.board_entry_title.delete(0, "end")
        self.board_entry_title.insert(0, str(payload.get("title", "")))
        self.board_desc_text.delete("1.0", "end")
        self.board_desc_text.insert("1.0", str(payload.get("description", "")))
        self.board_intro_text.delete("1.0", "end")
        self.board_intro_text.insert("1.0", str(schema.get("intro", "")))
        self.board_mode_var.set(MODE_VALUE_TO_LABEL.get(str(payload.get("identity_mode", "realname")), "实名"))
        self.board_repeat_var.set(bool(payload.get("allow_repeat", False)))
        self.board_auth_mode_var.set(AUTH_VALUE_TO_LABEL.get(str(payload.get("auth_mode", "open")), "开放作答"))

        roster_id = self._resolve_roster_for_payload(payload, self.board_auth_roster_var.get())
        if payload.get("requires_roster") and not roster_id:
            return
        if roster_id:
            roster_match = next((f"{r['id']} | {r['name']}" for r in self.roster_cache if str(r["id"]) == roster_id), roster_id)
            self.board_auth_roster_var.set(roster_match)
        else:
            self.board_auth_roster_var.set("")

        fields = payload.get("identity_fields", {}) if isinstance(payload.get("identity_fields"), dict) else {}
        self.board_same_device_repeat_var.set(bool(fields.get("allow_same_device_repeat", False)))
        collect_fields = fields.get("collect_fields", [])
        if isinstance(collect_fields, list) and collect_fields:
            self.board_collect_fields = self._board_normalize_collect_fields(collect_fields)
        else:
            fallback: List[Dict[str, str]] = []
            if bool(fields.get("collect_code", False)):
                fallback.append({"key": "member_code", "label": "编号"})
            if bool(fields.get("collect_name", False)):
                fallback.append({"key": "member_name", "label": "姓名"})
            self.board_collect_fields = self._board_normalize_collect_fields(fallback)
        self._board_refresh_collect_fields_summary()

        self._board_load_schema_to_state(schema)
        self._board_sync_auto_lists(re_render=False)
        self._board_render_canvas()
        messagebox.showinfo("模板已套用", "模板已加载到展板，可继续逐题修改。", parent=self)

    def _board_add_list_object_dialog(self, list_type: str) -> None:
        name = simpledialog.askstring("新建列表", "请输入列表名称（不可重复）：", parent=self) or ""
        name = name.strip()
        if not name:
            return
        if any(str(obj.get("name", "")).strip() == name for obj in self.board_list_objects):
            messagebox.showwarning("提示", "列表名称重复，请换一个。", parent=self)
            return
        prompt = "每行一项；数字列表需全部可转为数字。"
        raw = simpledialog.askstring("列表内容", prompt, parent=self) or ""
        values = [line.strip() for line in raw.splitlines() if line.strip()]
        if not values:
            messagebox.showwarning("提示", "列表内容不能为空。", parent=self)
            return
        items: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for value in values:
            if list_type == "number":
                try:
                    float(value)
                except Exception:
                    messagebox.showwarning("提示", f"“{value}”不是数字。", parent=self)
                    return
            if value in seen:
                continue
            seen.add(value)
            items.append({"key": value, "label": value})
        self.board_list_objects.append(
            {"name": name, "type": "number" if list_type == "number" else "text", "items": items, "source": "manual"}
        )
        self._board_render_canvas()

    def _board_import_lists_from_roster(self) -> None:
        rid = self._extract_qid(self.board_auth_roster_var.get())
        if not rid:
            messagebox.showwarning("提示", "请先在上方绑定名单，或先选择一个问卷名单。", parent=self)
            return
        auto_lists = self.service.build_roster_column_list_objects(rid)
        inserted = 0
        for obj in auto_lists:
            name = str(obj.get("name", "")).strip()
            if not name:
                continue
            if any(str(item.get("name", "")).strip() == name for item in self.board_list_objects):
                continue
            self.board_list_objects.append(obj)
            inserted += 1
        self._board_render_canvas()
        messagebox.showinfo("完成", f"从名单生成 {inserted} 个列表对象。", parent=self)

    def _board_open_list_manager(self) -> None:
        win = tk.Toplevel(self)
        win.title("列表管理")
        win.geometry("760x500")
        win.transient(self)
        win.grab_set()
        wrap = ctk.CTkFrame(win, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=12, pady=12)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(wrap, text="循环列表对象", font=ctk.CTkFont(size=17, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        list_wrap = ctk.CTkFrame(wrap, fg_color="#f8fbff", corner_radius=10)
        list_wrap.grid(row=1, column=0, sticky="nsew")
        list_wrap.grid_rowconfigure(0, weight=1)
        list_wrap.grid_columnconfigure(0, weight=1)
        tree = ttk.Treeview(list_wrap, columns=("name", "type", "count", "source"), show="headings")
        for col, title, width in [
            ("name", "名称", 220),
            ("type", "类型", 80),
            ("count", "项数", 80),
            ("source", "来源", 220),
        ]:
            tree.heading(col, text=title)
            tree.column(col, width=width, anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(list_wrap, orient="vertical", command=tree.yview).grid(row=0, column=1, sticky="ns")

        def refresh_tree() -> None:
            for node in tree.get_children():
                tree.delete(node)
            for obj in self.board_list_objects:
                tree.insert(
                    "",
                    "end",
                    iid=str(obj.get("name", "")),
                    values=(
                        str(obj.get("name", "")),
                        str(obj.get("type", "")),
                        len(obj.get("items", []) if isinstance(obj.get("items"), list) else []),
                        str(obj.get("source", "manual")),
                    ),
                )

        bar = ctk.CTkFrame(wrap, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        bar.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        ctk.CTkButton(bar, text="新建文本列表", command=lambda: (self._board_add_list_object_dialog("text"), refresh_tree())).grid(
            row=0, column=0, padx=4, sticky="ew"
        )
        ctk.CTkButton(bar, text="新建数字列表", command=lambda: (self._board_add_list_object_dialog("number"), refresh_tree())).grid(
            row=0, column=1, padx=4, sticky="ew"
        )
        ctk.CTkButton(bar, text="从名单生成", command=lambda: (self._board_import_lists_from_roster(), refresh_tree())).grid(
            row=0, column=2, padx=4, sticky="ew"
        )

        def remove_selected() -> None:
            selected = tree.selection()
            if not selected:
                return
            name = str(selected[0])
            obj = next((x for x in self.board_list_objects if str(x.get("name", "")) == name), None)
            if not obj:
                return
            if bool(obj.get("readonly", False)):
                messagebox.showwarning("提示", "该列表为系统自动列表，不能删除。", parent=win)
                return
            self.board_list_objects = [x for x in self.board_list_objects if str(x.get("name", "")) != name]
            self._board_render_canvas()
            refresh_tree()

        ctk.CTkButton(bar, text="删除选中", command=remove_selected).grid(row=0, column=3, padx=4, sticky="ew")
        ctk.CTkButton(bar, text="关闭", command=win.destroy).grid(row=0, column=4, padx=4, sticky="ew")
        refresh_tree()

    def _board_open_validation_rule_manager(self) -> None:
        win = tk.Toplevel(self)
        win.title("联合规则（SQL）")
        win.geometry("2360x1520")
        win.transient(self)
        win.grab_set()

        raw_rules = self.board_validation_rules if isinstance(self.board_validation_rules, list) else []
        legacy_count = len(
            [
                x
                for x in raw_rules
                if isinstance(x, dict) and str(x.get("type", "")).strip().lower() not in {"", "sql_aggregate"}
            ]
        )
        local_rules: List[Dict[str, Any]] = [
            self._board_clone(x)
            for x in raw_rules
            if isinstance(x, dict) and str(x.get("type", "")).strip().lower() in {"", "sql_aggregate"}
        ]
        if legacy_count > 0:
            messagebox.showwarning(
                "提示",
                f"检测到 {legacy_count} 条旧版联合规则。\n本版本统一使用 SQL 规则，应用后将仅保留当前窗口内的规则。",
                parent=win,
            )

        wrap = ctk.CTkFrame(win, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=12, pady=12)
        wrap.grid_columnconfigure(0, weight=0, minsize=360)
        wrap.grid_columnconfigure(1, weight=1)
        wrap.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(wrap, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="联合规则（SQL）", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )

        def show_help() -> None:
            messagebox.showinfo(
                "联合规则说明",
                (
                    "1. 每条规则只能填写 1 条 SELECT 语句。\n"
                    "2. 支持常见 SQL 条件与结构：JOIN、IN、EXISTS、BETWEEN、子查询、GROUP BY、HAVING 等。\n"
                    "3. SQL 执行后会读取第 1 列结果作为规则值（应为数字）。\n"
                    "4. 当前联合规则模型仅包含“当前答卷”，无需额外追加 submission_id 过滤。\n"
                    "5. SQL 结果再与“比较条件”判断，未通过则阻止作答/提交。\n\n"
                    "可用表：submissions、identity_kv、question_defs、question_options、\n"
                    "answers、answer_options、v_scores、v_text_answers、\n"
                    "v_answers_enriched、v_answer_options_enriched、\n"
                    "v_identity_enriched、v_submissions_identity"
                ),
                parent=win,
            )

        ctk.CTkButton(header, text="i", width=32, command=show_help).grid(row=0, column=1, sticky="e")

        left = ctk.CTkFrame(wrap, corner_radius=10)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(left, text="已配置规则", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 6)
        )

        tree_wrap = ctk.CTkFrame(left, fg_color="#f8fbff", corner_radius=10)
        tree_wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
        tree_wrap.grid_columnconfigure(0, weight=1)
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree = ttk.Treeview(tree_wrap, columns=("idx", "name", "op"), show="headings", height=18)
        for col, text, width in [("idx", "#", 40), ("name", "规则名", 200), ("op", "比较方式", 100)]:
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=tree_scroll.set)

        right = ctk.CTkFrame(wrap, corner_radius=10)
        right.grid(row=1, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(3, weight=1)

        var_name = ctk.StringVar(value="")
        var_op_label = ctk.StringVar(value="小于等于")
        var_value = ctk.StringVar(value="")
        var_value2 = ctk.StringVar(value="")
        var_message = ctk.StringVar(value="")
        status_var = ctk.StringVar(value="请选择规则编辑，或点击“新建规则”。")
        current_index: Optional[int] = None

        ctk.CTkLabel(right, text="规则名称").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        ctk.CTkEntry(right, textvariable=var_name).grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))

        ctk.CTkLabel(right, text="SQL（仅 1 条 SELECT，建议返回 1 个数字）").grid(row=2, column=0, sticky="w", padx=10, pady=(0, 4))
        sql_text = ctk.CTkTextbox(right, height=200)
        sql_text.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 6))
        auto_suffix = self.service.live_rule_auto_filter_suffix()
        ctk.CTkLabel(right, text=f"系统自动追加：{auto_suffix}", text_color="#4f658c").grid(
            row=4, column=0, sticky="w", padx=10, pady=(0, 8)
        )

        compare_box = ctk.CTkFrame(right, fg_color="#f8fbff", corner_radius=10)
        compare_box.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 8))
        compare_box.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkLabel(compare_box, text="比较方式").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(compare_box, text="目标值").grid(row=0, column=1, sticky="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(compare_box, text="区间上限（仅区间）").grid(row=0, column=2, sticky="w", padx=8, pady=(8, 2))
        ctk.CTkOptionMenu(compare_box, variable=var_op_label, values=list(RULE_COMPARE_LABEL_TO_VALUE.keys())).grid(
            row=1, column=0, sticky="ew", padx=8, pady=(0, 8)
        )
        ctk.CTkEntry(compare_box, textvariable=var_value, placeholder_text="例如：30").grid(
            row=1, column=1, sticky="ew", padx=8, pady=(0, 8)
        )
        ctk.CTkEntry(compare_box, textvariable=var_value2, placeholder_text="例如：60").grid(
            row=1, column=2, sticky="ew", padx=8, pady=(0, 8)
        )

        ctk.CTkLabel(right, text="不通过提示语").grid(row=6, column=0, sticky="w", padx=10, pady=(0, 4))
        ctk.CTkEntry(right, textvariable=var_message).grid(row=7, column=0, sticky="ew", padx=10, pady=(0, 8))
        ctk.CTkLabel(right, textvariable=status_var, text_color="#506080").grid(row=8, column=0, sticky="w", padx=10, pady=(0, 8))

        def build_sql_model_hint_text() -> str:
            qid = str(self.editing_qid or self._board_selected_questionnaire_id()).strip()
            if not qid:
                return "可用项目：当前为未保存草稿。保存后可显示完整 SQL 可用表与字段。"
            try:
                model = self.service.query_model_schema(qid)
            except ServiceError as exc:
                return f"可用项目读取失败：{exc}"
            lines: List[str] = []
            lines.append("可用项目（联合规则 SQL 可直接使用）")
            rule_tables = model.get("live_rule_table_defs", [])
            source_tables = rule_tables if isinstance(rule_tables, list) and rule_tables else model.get("table_defs", [])
            for table in source_tables:
                if not isinstance(table, dict):
                    continue
                name = str(table.get("name", "")).strip()
                desc = str(table.get("desc", "")).strip()
                if not name:
                    continue
                lines.append(f"- {name}：{desc}")
                for col in table.get("columns", []):
                    if not isinstance(col, (list, tuple)) or len(col) < 3:
                        continue
                    lines.append(f"    {col[0]} ({col[1]})  # {col[2]}")
            suffix = str(model.get("live_rule_suffix", "")).strip()
            if suffix:
                lines.append("")
                lines.append(f"自动限制：{suffix}")
            identity_cols = model.get("identity_dynamic_columns", [])
            if isinstance(identity_cols, list) and identity_cols:
                lines.append("")
                lines.append("动态身份列：")
                for item in identity_cols:
                    if not isinstance(item, dict):
                        continue
                    col = str(item.get("column_name", "")).strip()
                    if not col:
                        continue
                    label = str(item.get("field_label", "")).strip() or str(item.get("field_key", "")).strip()
                    lines.append(f"  {col}  # {label}")
            return "\n".join(lines)

        info_box_wrap = ctk.CTkFrame(right, fg_color="#f8fbff", corner_radius=10)
        info_box_wrap.grid(row=10, column=0, sticky="nsew", padx=10, pady=(0, 10))
        info_box_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(info_box_wrap, text="可用项目", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 4)
        )
        info_box = ctk.CTkTextbox(info_box_wrap, height=190)
        info_box.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        info_box.insert("1.0", build_sql_model_hint_text())
        info_box.configure(state="disabled")

        def parse_number_required(raw_text: str, label: str) -> float:
            text = str(raw_text or "").strip()
            if not text:
                raise ServiceError(f"{label}不能为空。")
            try:
                return float(text)
            except Exception as exc:
                raise ServiceError(f"{label}必须是数字。") from exc

        def refresh_tree(select_idx: Optional[int] = None) -> None:
            for iid in tree.get_children():
                tree.delete(iid)
            for idx, rule in enumerate(local_rules, start=1):
                if not isinstance(rule, dict):
                    continue
                name = str(rule.get("name", "")).strip() or f"联合规则{idx}"
                op = str(rule.get("op", "lte")).strip().lower()
                op_label = RULE_COMPARE_VALUE_TO_LABEL.get(op, "小于等于")
                tree.insert("", "end", iid=str(idx - 1), values=(idx, name, op_label))
            if select_idx is not None and str(select_idx) in tree.get_children():
                tree.selection_set(str(select_idx))
                tree.focus(str(select_idx))

        def clear_form() -> None:
            var_name.set("")
            sql_text.delete("1.0", "end")
            var_op_label.set("小于等于")
            var_value.set("")
            var_value2.set("")
            var_message.set("")

        def load_rule(index: int) -> None:
            nonlocal current_index
            if index < 0 or index >= len(local_rules):
                return
            rule = local_rules[index] if isinstance(local_rules[index], dict) else {}
            current_index = index
            var_name.set(str(rule.get("name", "")).strip())
            sql_text.delete("1.0", "end")
            sql_text.insert("1.0", str(rule.get("sql", "")).strip())
            op = str(rule.get("op", "lte")).strip().lower()
            var_op_label.set(RULE_COMPARE_VALUE_TO_LABEL.get(op, "小于等于"))
            var_value.set(str(rule.get("value", "")))
            var_value2.set("" if rule.get("value2") is None else str(rule.get("value2")))
            var_message.set(str(rule.get("message", "")).strip())
            status_var.set(f"正在编辑第 {index + 1} 条规则。")

        def build_rule_from_form() -> Dict[str, Any]:
            name = var_name.get().strip()
            sql_raw = sql_text.get("1.0", "end").strip()
            if not sql_raw:
                raise ServiceError("请填写 SQL。")
            sql_normalized = self.service.validate_live_rule_sql(sql_raw)
            op = RULE_COMPARE_LABEL_TO_VALUE.get(var_op_label.get().strip(), "lte")
            value = parse_number_required(var_value.get(), "目标值")
            value2: Optional[float] = None
            if op in {"between", "not_between"}:
                value2 = parse_number_required(var_value2.get(), "区间上限")
            message = var_message.get().strip() or "联合规则未通过，请按提示调整后继续。"
            return {
                "type": "sql_aggregate",
                "name": name or "联合规则",
                "sql": sql_normalized,
                "op": op,
                "value": value,
                "value2": value2,
                "message": message,
            }

        def on_select(_event: Any = None) -> None:
            selected = tree.selection()
            if not selected:
                return
            try:
                idx = int(str(selected[0]))
            except Exception:
                return
            load_rule(idx)

        tree.bind("<<TreeviewSelect>>", on_select)

        def add_new_rule() -> None:
            nonlocal current_index
            current_index = None
            clear_form()
            status_var.set("正在新建规则。")

        def save_current_rule() -> None:
            nonlocal current_index
            try:
                rule = build_rule_from_form()
            except ServiceError as exc:
                messagebox.showwarning("规则错误", str(exc), parent=win)
                return
            if current_index is None:
                local_rules.append(rule)
                current_index = len(local_rules) - 1
                status_var.set(f"已新增第 {current_index + 1} 条规则。")
            else:
                local_rules[current_index] = rule
                status_var.set(f"已更新第 {current_index + 1} 条规则。")
            refresh_tree(select_idx=current_index)

        def remove_selected_rule() -> None:
            nonlocal current_index
            selected = tree.selection()
            if not selected:
                return
            try:
                idx = int(str(selected[0]))
            except Exception:
                return
            if idx < 0 or idx >= len(local_rules):
                return
            local_rules.pop(idx)
            current_index = None
            clear_form()
            refresh_tree(select_idx=min(idx, len(local_rules) - 1) if local_rules else None)
            status_var.set("已删除规则。")

        def move_rule(offset: int) -> None:
            selected = tree.selection()
            if not selected:
                return
            try:
                idx = int(str(selected[0]))
            except Exception:
                return
            target = idx + offset
            if target < 0 or target >= len(local_rules):
                return
            local_rules[idx], local_rules[target] = local_rules[target], local_rules[idx]
            refresh_tree(select_idx=target)

        def fill_example(kind: str) -> None:
            if kind == "avg":
                var_name.set("平均分上限")
                sql_text.delete("1.0", "end")
                sql_text.insert("1.0", "SELECT AVG(value_num) FROM v_scores WHERE question_id = 'q_score'")
                var_op_label.set("小于等于")
                var_value.set("3.5")
                var_value2.set("")
                var_message.set("当前平均分超过上限，请调整后继续。")
            elif kind == "count":
                var_name.set("高分人数上限")
                sql_text.delete("1.0", "end")
                sql_text.insert(
                    "1.0",
                    "SELECT COUNT(*) FROM v_scores WHERE question_id = 'q_score' AND value_num >= 4",
                )
                var_op_label.set("小于等于")
                var_value.set("2")
                var_value2.set("")
                var_message.set("4分人数超过上限，请调整后继续。")
            elif kind == "join":
                var_name.set("互评高分人数上限")
                sql_text.delete("1.0", "end")
                sql_text.insert(
                    "1.0",
                    (
                        "SELECT COUNT(*)\n"
                        "FROM answers a\n"
                        "JOIN submissions s ON a.submission_id = s.submission_id\n"
                        "WHERE a.question_id = 'q_score' AND a.value_num >= 4 AND a.repeat_at <> s.verified_member_key_xing_ming"
                    ),
                )
                var_op_label.set("小于等于")
                var_value.set("2")
                var_value2.set("")
                var_message.set("互评中 4 分人数超过上限，请调整后继续。")
            else:
                var_name.set("去重对象数量限制")
                sql_text.delete("1.0", "end")
                sql_text.insert(
                    "1.0",
                    "SELECT COUNT(DISTINCT repeat_at) FROM v_scores WHERE question_id = 'q_score'",
                )
                var_op_label.set("区间内")
                var_value.set("1")
                var_value2.set("20")
                var_message.set("互评对象数量不在允许范围内。")
            status_var.set("示例已填入，请按你的题目ID和条件修改后保存。")

        left_btns = ctk.CTkFrame(left, fg_color="transparent")
        left_btns.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        left_btns.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkButton(left_btns, text="新建规则", command=add_new_rule).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(left_btns, text="删除规则", command=remove_selected_rule).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(left_btns, text="上移", command=lambda: move_rule(-1)).grid(row=0, column=2, padx=4, sticky="ew")
        ctk.CTkButton(left_btns, text="下移", command=lambda: move_rule(1)).grid(row=0, column=3, padx=4, sticky="ew")

        right_btns = ctk.CTkFrame(right, fg_color="transparent")
        right_btns.grid(row=9, column=0, sticky="ew", padx=10, pady=(0, 10))
        right_btns.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)
        ctk.CTkButton(right_btns, text="示例：平均", command=lambda: fill_example("avg")).grid(
            row=0, column=0, padx=4, sticky="ew"
        )
        ctk.CTkButton(right_btns, text="示例：人数", command=lambda: fill_example("count")).grid(
            row=0, column=1, padx=4, sticky="ew"
        )
        ctk.CTkButton(right_btns, text="示例：JOIN", command=lambda: fill_example("join")).grid(
            row=0, column=2, padx=4, sticky="ew"
        )
        ctk.CTkButton(right_btns, text="示例：区间", command=lambda: fill_example("range")).grid(
            row=0, column=3, padx=4, sticky="ew"
        )
        ctk.CTkButton(right_btns, text="保存当前规则", command=save_current_rule).grid(row=0, column=4, padx=4, sticky="ew")

        def apply_and_close() -> None:
            self.board_validation_rules = local_rules
            win.destroy()
            messagebox.showinfo("已保存", f"联合规则已保存：{len(local_rules)} 条。", parent=self)

        ctk.CTkButton(right_btns, text="应用并关闭", command=apply_and_close).grid(row=0, column=5, padx=4, sticky="ew")
        ctk.CTkButton(right_btns, text="取消", command=win.destroy).grid(row=0, column=6, padx=4, sticky="ew")

        clear_form()
        refresh_tree()
    def _board_card_style(self, card_id: str) -> tuple[str, int]:
        if card_id and card_id == self.board_selected_card_id:
            return "#2e6ce5", 2
        return "#d8e1f2", 1

    def _board_begin_drag(self, level: str, block_id: str, question_id: str = "") -> None:
        self.board_drag_ctx = {
            "level": level,
            "block_id": block_id,
            "question_id": question_id,
        }

    def _board_end_drag(self, event: tk.Event) -> None:
        ctx = self.board_drag_ctx or {}
        self.board_drag_ctx = None
        level = str(ctx.get("level", ""))
        if level == "top":
            block_id = str(ctx.get("block_id", "")).strip()
            if not block_id or len(self.board_items) <= 1:
                return
            ordered = [(bid, frame) for bid, frame in self.board_card_widgets if frame.winfo_exists()]
            if len(ordered) <= 1:
                return
            target_idx = 0
            y_root = int(event.y_root)
            for idx, (_bid, frame) in enumerate(ordered):
                mid = frame.winfo_rooty() + (frame.winfo_height() / 2)
                if y_root > mid:
                    target_idx = idx + 1
            current_idx = self._board_find_item_index(block_id)
            if current_idx < 0:
                return
            if target_idx > current_idx:
                target_idx -= 1
            if target_idx == current_idx:
                return
            item = self.board_items.pop(current_idx)
            self.board_items.insert(max(0, min(target_idx, len(self.board_items))), item)
            self._board_render_canvas()
            return

        if level == "inner":
            block_id = str(ctx.get("block_id", "")).strip()
            question_id = str(ctx.get("question_id", "")).strip()
            if not block_id or not question_id:
                return
            idx = self._board_find_item_index(block_id)
            if idx < 0:
                return
            block = self.board_items[idx]
            if block.get("kind") != "loop":
                return
            inner = block.get("inner_questions", [])
            if len(inner) <= 1:
                return
            pairs = self.board_inner_widgets.get(block_id, [])
            ordered = [(qid, frame) for qid, frame in pairs if frame.winfo_exists()]
            if len(ordered) <= 1:
                return
            target_idx = 0
            y_root = int(event.y_root)
            for pos, (_qid, frame) in enumerate(ordered):
                mid = frame.winfo_rooty() + (frame.winfo_height() / 2)
                if y_root > mid:
                    target_idx = pos + 1
            current_idx = self._board_find_inner_index(block_id, question_id)
            if current_idx < 0:
                return
            if target_idx > current_idx:
                target_idx -= 1
            if target_idx == current_idx:
                return
            item = inner.pop(current_idx)
            inner.insert(max(0, min(target_idx, len(inner))), item)
            self._board_render_canvas()

    def _board_update_question_field(self, block_id: str, question_id: str, key: str, value: Any) -> None:
        q = self._board_find_question_ref(block_id, question_id)
        if q is None:
            return
        q[key] = value

    def _board_parse_csv_tokens(self, raw: str) -> List[str]:
        text = str(raw or "").replace("，", ",").replace("；", ",").strip()
        return [item.strip() for item in text.split(",") if item.strip()]

    def _board_collect_all_question_ids(self) -> List[str]:
        ids: List[str] = []
        for item in self.board_items:
            if item.get("kind") == "question":
                q = item.get("question", {})
                qid = str(q.get("id", "")).strip()
                if qid:
                    ids.append(qid)
            else:
                for q in item.get("inner_questions", []):
                    qid = str(q.get("id", "")).strip()
                    if qid:
                        ids.append(qid)
        return ids

    def _board_remap_question_references(self, old_qid: str, new_qid: str) -> None:
        if not old_qid or not new_qid or old_qid == new_qid:
            return
        mapping = {old_qid: new_qid}
        for item in self.board_items:
            if not isinstance(item, dict):
                continue
            if str(item.get("repeat_from", "")).strip() == old_qid:
                item["repeat_from"] = new_qid
            if isinstance(item.get("visible_if"), dict):
                item["visible_if"] = self._remap_rule_question_ids(item.get("visible_if"), mapping)
            if item.get("kind") == "question":
                q = item.get("question", {})
                if not isinstance(q, dict):
                    continue
                if str(q.get("repeat_from", "")).strip() == old_qid:
                    q["repeat_from"] = new_qid
                q["visible_if"] = self._remap_rule_question_ids(q.get("visible_if"), mapping)
                q["required_if"] = self._remap_rule_question_ids(q.get("required_if"), mapping)
                continue
            for q in item.get("inner_questions", []):
                if not isinstance(q, dict):
                    continue
                if str(q.get("repeat_from", "")).strip() == old_qid:
                    q["repeat_from"] = new_qid
                q["visible_if"] = self._remap_rule_question_ids(q.get("visible_if"), mapping)
                q["required_if"] = self._remap_rule_question_ids(q.get("required_if"), mapping)

        for rule in self.board_validation_rules:
            if not isinstance(rule, dict):
                continue
            if str(rule.get("type", "")).strip().lower() in {"", "sql_aggregate"}:
                sql_text = str(rule.get("sql", ""))
                if sql_text:
                    rule["sql"] = (
                        sql_text.replace(f"'{old_qid}'", f"'{new_qid}'")
                        .replace(f'"{old_qid}"', f'"{new_qid}"')
                    )
            if isinstance(rule.get("when"), dict):
                rule["when"] = self._remap_rule_question_ids(rule.get("when"), mapping)
            qids = rule.get("question_ids")
            if isinstance(qids, list):
                updated: List[str] = []
                for raw in qids:
                    text = str(raw).strip()
                    if text == old_qid:
                        text = new_qid
                    if text:
                        updated.append(text)
                rule["question_ids"] = updated
            left_q = str(rule.get("left_question", "")).strip()
            right_q = str(rule.get("right_question", "")).strip()
            if left_q == old_qid:
                rule["left_question"] = new_qid
            if right_q == old_qid:
                rule["right_question"] = new_qid

    def _board_update_question_id(self, block_id: str, old_qid: str, new_qid_raw: str) -> None:
        q = self._board_find_question_ref(block_id, old_qid)
        if q is None:
            return
        new_qid = str(new_qid_raw).strip() or old_qid
        if any(ch.isspace() for ch in new_qid):
            messagebox.showwarning("提示", "题目ID不能包含空白字符。", parent=self)
            self._board_render_canvas()
            return
        all_ids = self._board_collect_all_question_ids()
        dup_count = sum(1 for qid in all_ids if qid == new_qid)
        if new_qid != old_qid and dup_count > 0:
            messagebox.showwarning("提示", f"题目ID重复：{new_qid}", parent=self)
            self._board_render_canvas()
            return
        q["id"] = new_qid
        self._board_remap_question_references(old_qid, new_qid)
        if self.board_logic_source_qid.get().strip() == old_qid:
            self.board_logic_source_qid.delete(0, "end")
            self.board_logic_source_qid.insert(0, new_qid)
        if self.board_logic_target and self.board_logic_target.get("question_id") == old_qid:
            self.board_logic_target["question_id"] = new_qid
        self._board_render_canvas()

    def _board_update_question_numeric(
        self,
        block_id: str,
        question_id: str,
        key: str,
        raw: str,
        fallback: int,
        min_value: Optional[int] = None,
    ) -> None:
        q = self._board_find_question_ref(block_id, question_id)
        if q is None:
            return
        try:
            value = int(str(raw).strip())
        except Exception:
            value = fallback
        if min_value is not None:
            value = max(min_value, value)
        q[key] = value

    def _board_update_question_options(self, block_id: str, question_id: str, raw: str) -> None:
        q = self._board_find_question_ref(block_id, question_id)
        if q is None:
            return
        text = str(raw or "").replace("\n", "|")
        options = [item.strip() for item in text.split("|") if item.strip()]
        if not options:
            options = ["选项1", "选项2"]
        q["options"] = options

    def _board_on_question_type_change(self, block_id: str, question_id: str, label: str) -> None:
        q = self._board_find_question_ref(block_id, question_id)
        if q is None:
            return
        q_type = BOARD_QTYPE_VALUES.get(label, "single")
        q["type"] = q_type
        if q_type in {"single", "multi"} and not q.get("options"):
            q["options"] = ["选项1", "选项2"]
        self._board_render_canvas()

    def _board_render_question_card(
        self,
        parent: ctk.CTkFrame,
        block_id: str,
        question: Dict[str, Any],
        order_label: str,
        in_loop: bool = False,
        top_index: Optional[int] = None,
        top_total: Optional[int] = None,
        inner_index: Optional[int] = None,
        inner_total: Optional[int] = None,
    ) -> ctk.CTkFrame:
        qid = str(question.get("id", "")).strip()
        card_id = f"q:{block_id}:{qid}" if in_loop else f"topq:{block_id}"
        border_color, border_width = self._board_card_style(card_id)
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color="#f8fbff", border_color=border_color, border_width=border_width)
        card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=4, sticky="ew", padx=10, pady=(8, 4))
        head.grid_columnconfigure(1, weight=1)
        handle = ctk.CTkLabel(
            head,
            text="拖动排序",
            text_color="#4f6184",
            cursor="hand2",
            font=ctk.CTkFont(size=12),
        )
        handle.grid(row=0, column=0, sticky="w")
        if in_loop:
            handle.bind("<ButtonPress-1>", lambda _e, b=block_id, q=qid: self._board_begin_drag("inner", b, q))
            handle.bind("<ButtonRelease-1>", self._board_end_drag)
        else:
            handle.bind("<ButtonPress-1>", lambda _e, b=block_id: self._board_begin_drag("top", b))
            handle.bind("<ButtonRelease-1>", self._board_end_drag)

        ctk.CTkLabel(
            head,
            text=f"{order_label} {'循环题' if in_loop else '普通题'}",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=1, sticky="w", padx=(10, 0))
        ctk.CTkButton(
            head,
            text="逻辑",
            width=62,
            command=lambda b=block_id, q=qid, c=card_id: self._board_set_logic_target(
                {"kind": "question", "block_id": b, "question_id": q, "in_loop": "1" if in_loop else "0", "card_id": c}
            ),
        ).grid(row=0, column=2, padx=4, sticky="e")
        ctk.CTkButton(
            head,
            text="复制",
            width=62,
            command=(
                (lambda b=block_id, q=qid: self._board_duplicate_inner(b, q))
                if in_loop
                else (lambda b=block_id: self._board_duplicate_item(b))
            ),
        ).grid(row=0, column=3, padx=4, sticky="e")

        base = ctk.CTkFrame(card, fg_color="transparent")
        base.grid(row=1, column=0, columnspan=4, sticky="ew", padx=10, pady=2)
        base.grid_columnconfigure((0, 1, 2, 3), weight=1)

        title_box = ctk.CTkFrame(base, fg_color="transparent")
        title_box.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
        title_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(title_box, text="题目标题").grid(row=0, column=0, sticky="w")
        title_entry = ctk.CTkEntry(title_box)
        title_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        title_entry.insert(0, str(question.get("title", "")))
        title_entry.bind(
            "<FocusOut>",
            lambda _e, b=block_id, q=qid, w=title_entry: self._board_update_question_field(b, q, "title", w.get().strip()),
        )

        id_box = ctk.CTkFrame(base, fg_color="transparent")
        id_box.grid(row=0, column=2, sticky="ew", padx=4, pady=4)
        id_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(id_box, text="题目ID").grid(row=0, column=0, sticky="w")
        id_entry = ctk.CTkEntry(id_box)
        id_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        id_entry.insert(0, qid)
        id_entry.bind(
            "<FocusOut>",
            lambda _e, b=block_id, q=qid, w=id_entry: self._board_update_question_id(b, q, w.get()),
        )

        type_box = ctk.CTkFrame(base, fg_color="transparent")
        type_box.grid(row=0, column=3, sticky="ew", padx=4, pady=4)
        type_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(type_box, text="题型").grid(row=0, column=0, sticky="w")
        q_type_label = BOARD_QTYPE_LABEL_BY_VALUE.get(str(question.get("type", "single")), "单选")
        q_type_var = ctk.StringVar(value=q_type_label)
        ctk.CTkOptionMenu(
            type_box,
            variable=q_type_var,
            values=BOARD_QTYPE_LABELS,
            command=lambda label, b=block_id, q=qid: self._board_on_question_type_change(b, q, label),
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

        req_wrap = ctk.CTkFrame(base, fg_color="transparent")
        req_wrap.grid(row=1, column=0, sticky="w", padx=4, pady=(2, 4))
        req_var = ctk.BooleanVar(value=bool(question.get("required", False)))
        ctk.CTkSwitch(
            req_wrap,
            text="必填",
            variable=req_var,
            command=lambda b=block_id, q=qid, v=req_var: self._board_update_question_field(b, q, "required", bool(v.get())),
        ).pack(anchor="w")

        if in_loop:
            rf_wrap = ctk.CTkFrame(base, fg_color="transparent")
            rf_wrap.grid(row=1, column=1, sticky="ew", padx=4, pady=(2, 4))
            ctk.CTkLabel(rf_wrap, text="循环筛选").pack(anchor="w")
            rf_val = str(question.get("repeat_filter", "all")).strip().lower() or "all"
            rf_var = ctk.StringVar(value=REPEAT_FILTER_VALUE_TO_LABEL.get(rf_val, "全部循环项"))
            ctk.CTkOptionMenu(
                rf_wrap,
                variable=rf_var,
                values=list(REPEAT_FILTER_LABEL_TO_VALUE.keys()),
                command=lambda label, b=block_id, q=qid: self._board_update_question_field(
                    b, q, "repeat_filter", REPEAT_FILTER_LABEL_TO_VALUE.get(label, "all")
                ),
            ).pack(fill="x", pady=(4, 0))

        q_type = str(question.get("type", "single"))
        detail = ctk.CTkFrame(card, fg_color="#ffffff", corner_radius=8)
        detail.grid(row=2, column=0, columnspan=4, sticky="ew", padx=10, pady=(2, 6))
        detail.grid_columnconfigure((0, 1, 2), weight=1)

        if q_type in {"single", "multi"}:
            opt_box = ctk.CTkFrame(detail, fg_color="transparent")
            opt_box.grid(row=0, column=0, columnspan=3, sticky="ew", padx=6, pady=6)
            opt_box.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(opt_box, text="选项（用 | 分隔）").grid(row=0, column=0, sticky="w")
            opt_entry = ctk.CTkEntry(opt_box)
            opt_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
            opt_entry.insert(0, " | ".join([str(x) for x in question.get("options", [])]))
            opt_entry.bind(
                "<FocusOut>",
                lambda _e, b=block_id, q=qid, w=opt_entry: self._board_update_question_options(b, q, w.get()),
            )
            if q_type == "multi":
                mn_box = ctk.CTkFrame(detail, fg_color="transparent")
                mn_box.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
                mn_box.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(mn_box, text="最少选择").grid(row=0, column=0, sticky="w")
                mn_entry = ctk.CTkEntry(mn_box)
                mn_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
                mn_entry.insert(0, str(question.get("min_select", 1)))
                mn_entry.bind(
                    "<FocusOut>",
                    lambda _e, b=block_id, q=qid, w=mn_entry: self._board_update_question_numeric(
                        b, q, "min_select", w.get(), 1, min_value=0
                    ),
                )

                mx_box = ctk.CTkFrame(detail, fg_color="transparent")
                mx_box.grid(row=1, column=1, sticky="ew", padx=6, pady=(0, 6))
                mx_box.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(mx_box, text="最多选择").grid(row=0, column=0, sticky="w")
                mx_entry = ctk.CTkEntry(mx_box)
                mx_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
                mx_entry.insert(0, str(question.get("max_select", 2)))
                mx_entry.bind(
                    "<FocusOut>",
                    lambda _e, b=block_id, q=qid, w=mx_entry: self._board_update_question_numeric(
                        b, q, "max_select", w.get(), 2, min_value=1
                    ),
                )
        elif q_type in {"rating", "slider"}:
            for col, key, title, fallback in [
                (0, "min", "最小值", 1),
                (1, "max", "最大值", 5),
                (2, "step", "步进", 1),
            ]:
                box = ctk.CTkFrame(detail, fg_color="transparent")
                box.grid(row=0, column=col, sticky="ew", padx=6, pady=6)
                box.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(box, text=title).grid(row=0, column=0, sticky="w")
                entry = ctk.CTkEntry(box)
                entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
                entry.insert(0, str(question.get(key, fallback)))
                entry.bind(
                    "<FocusOut>",
                    lambda _e, b=block_id, q=qid, k=key, w=entry, d=fallback: self._board_update_question_numeric(
                        b, q, k, w.get(), d, min_value=1 if k == "step" else None
                    ),
                )
        elif q_type in {"text", "textarea"}:
            limits: List[tuple[str, str, int]] = [
                ("min_length", "最小字数", 0),
                ("max_length", "最大字数", 0),
            ]
            if q_type == "text":
                limits.extend([("min_words", "最少词数", 0), ("max_words", "最多词数", 0)])
            else:
                limits.append(("max_lines", "最多行数", 0))
            for idx, (key, title, fallback) in enumerate(limits):
                col = idx % 3
                row = idx // 3
                box = ctk.CTkFrame(detail, fg_color="transparent")
                box.grid(row=row, column=col, sticky="ew", padx=6, pady=6)
                box.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(box, text=title).grid(row=0, column=0, sticky="w")
                entry = ctk.CTkEntry(box)
                entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
                entry.insert(0, str(question.get(key, fallback)))
                entry.bind(
                    "<FocusOut>",
                    lambda _e, b=block_id, q=qid, k=key, w=entry, d=fallback: self._board_update_question_numeric(
                        b, q, k, w.get(), d, min_value=0
                    ),
                )

        bottom = ctk.CTkFrame(card, fg_color="transparent")
        bottom.grid(row=3, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 8))
        bottom.grid_columnconfigure((0, 1, 2), weight=1)

        if in_loop:
            up_cmd = (
                (lambda b=block_id, i=inner_index: self._board_move_inner_at(b, int(i), -1))
                if inner_index is not None
                else (lambda b=block_id, q=qid: self._board_move_inner(b, q, -1))
            )
            down_cmd = (
                (lambda b=block_id, i=inner_index: self._board_move_inner_at(b, int(i), 1))
                if inner_index is not None
                else (lambda b=block_id, q=qid: self._board_move_inner(b, q, 1))
            )
            up_disabled = inner_index is not None and inner_index <= 0
            down_disabled = (
                inner_index is not None and inner_total is not None and inner_index >= max(0, inner_total - 1)
            )
        else:
            up_cmd = (
                (lambda i=top_index: self._board_move_item_at(int(i), -1))
                if top_index is not None
                else (lambda b=block_id: self._board_move_item(b, -1))
            )
            down_cmd = (
                (lambda i=top_index: self._board_move_item_at(int(i), 1))
                if top_index is not None
                else (lambda b=block_id: self._board_move_item(b, 1))
            )
            up_disabled = top_index is not None and top_index <= 0
            down_disabled = top_index is not None and top_total is not None and top_index >= max(0, top_total - 1)

        up_btn = ctk.CTkButton(bottom, text="上移", command=up_cmd)
        up_btn.grid(row=0, column=0, padx=4, sticky="ew")
        if up_disabled:
            up_btn.configure(state="disabled")

        down_btn = ctk.CTkButton(bottom, text="下移", command=down_cmd)
        down_btn.grid(row=0, column=1, padx=4, sticky="ew")
        if down_disabled:
            down_btn.configure(state="disabled")

        ctk.CTkButton(
            bottom,
            text="删除",
            command=(
                (lambda b=block_id, q=qid: self._board_remove_inner(b, q))
                if in_loop
                else (lambda b=block_id: self._board_remove_item(b))
            ),
        ).grid(row=0, column=2, padx=4, sticky="ew")
        return card

    def _board_render_loop_block_card(
        self,
        parent: ctk.CTkFrame,
        item: Dict[str, Any],
        order_idx: int,
        item_index: int,
        item_total: int,
    ) -> ctk.CTkFrame:
        block_id = str(item.get("block_id", "")).strip()
        card_id = f"loop:{block_id}"
        border_color, border_width = self._board_card_style(card_id)
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color="#f3f8ff", border_color=border_color, border_width=border_width)
        card.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        head.grid_columnconfigure(1, weight=1)
        handle = ctk.CTkLabel(head, text="拖动排序", text_color="#4f6184", cursor="hand2", font=ctk.CTkFont(size=12))
        handle.grid(row=0, column=0, sticky="w")
        handle.bind("<ButtonPress-1>", lambda _e, b=block_id: self._board_begin_drag("top", b))
        handle.bind("<ButtonRelease-1>", self._board_end_drag)

        ctk.CTkLabel(head, text=f"{order_idx}. 循环块", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=1, sticky="w", padx=(10, 0)
        )
        ctk.CTkButton(
            head,
            text="逻辑",
            width=62,
            command=lambda b=block_id, c=card_id: self._board_set_logic_target(
                {"kind": "block", "block_id": b, "question_id": "", "card_id": c}
            ),
        ).grid(row=0, column=2, padx=4, sticky="e")
        ctk.CTkButton(head, text="复制", width=62, command=lambda b=block_id: self._board_duplicate_item(b)).grid(
            row=0, column=3, padx=4, sticky="e"
        )

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=1, column=0, sticky="ew", padx=10, pady=2)
        body.grid_columnconfigure((0, 1, 2), weight=1)

        title_box = ctk.CTkFrame(body, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        title_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(title_box, text="块标题").grid(row=0, column=0, sticky="w")
        title_entry = ctk.CTkEntry(title_box)
        title_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        title_entry.insert(0, str(item.get("title", "")))
        title_entry.bind("<FocusOut>", lambda _e, i=item, w=title_entry: i.__setitem__("title", w.get().strip() or "循环块"))

        source_choices = self._board_repeat_source_choices()
        current_source = str(item.get("repeat_from", "")).strip()
        if not current_source and source_choices:
            current_source = next(iter(source_choices.values()))
            item["repeat_from"] = current_source
        source_label = next(
            (k for k, v in source_choices.items() if v == current_source),
            (next(iter(source_choices.keys())) if source_choices else "（请先创建列表）"),
        )
        source_box = ctk.CTkFrame(body, fg_color="transparent")
        source_box.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        source_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(source_box, text="循环依据").grid(row=0, column=0, sticky="w")
        src_var = ctk.StringVar(value=source_label)
        ctk.CTkOptionMenu(
            source_box,
            variable=src_var,
            values=list(source_choices.keys()) if source_choices else ["（请先创建列表）"],
            command=lambda label, i=item, m=source_choices: i.__setitem__("repeat_from", m.get(label, "")),
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

        action_box = ctk.CTkFrame(body, fg_color="transparent")
        action_box.grid(row=0, column=2, sticky="ew", padx=4, pady=4)
        action_box.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(action_box, text="添加块内题", command=lambda b=block_id: self._board_add_inner_question(b)).grid(
            row=0, column=0, padx=4, pady=(20, 4), sticky="ew"
        )
        ctk.CTkButton(action_box, text="删除循环块", command=lambda b=block_id: self._board_remove_item(b)).grid(
            row=0, column=1, padx=4, pady=(20, 4), sticky="ew"
        )

        move_box = ctk.CTkFrame(action_box, fg_color="transparent")
        move_box.grid(row=1, column=0, columnspan=2, sticky="ew")
        move_box.grid_columnconfigure((0, 1), weight=1)
        up_btn = ctk.CTkButton(move_box, text="上移", command=lambda i=item_index: self._board_move_item_at(i, -1))
        up_btn.grid(row=0, column=0, padx=4, sticky="ew")
        if item_index <= 0:
            up_btn.configure(state="disabled")
        down_btn = ctk.CTkButton(move_box, text="下移", command=lambda i=item_index: self._board_move_item_at(i, 1))
        down_btn.grid(row=0, column=1, padx=4, sticky="ew")
        if item_index >= max(0, item_total - 1):
            down_btn.configure(state="disabled")

        inner_wrap = ctk.CTkFrame(card, fg_color="#ffffff", corner_radius=8)
        inner_wrap.grid(row=2, column=0, sticky="ew", padx=10, pady=(4, 8))
        inner_wrap.grid_columnconfigure(0, weight=1)
        self.board_inner_widgets[block_id] = []
        inner_questions = item.get("inner_questions", [])
        inner_total = len(inner_questions)
        for idx, question in enumerate(inner_questions, start=1):
            inner_card = self._board_render_question_card(
                inner_wrap,
                block_id=block_id,
                question=question,
                order_label=f"{order_idx}.{idx}",
                in_loop=True,
                inner_index=idx - 1,
                inner_total=inner_total,
            )
            inner_card.grid(row=idx - 1, column=0, sticky="ew", padx=8, pady=6)
            qid = str(question.get("id", "")).strip()
            if qid:
                self.board_inner_widgets[block_id].append((qid, inner_card))
        return card

    def _board_render_canvas(self) -> None:
        if not hasattr(self, "board_canvas"):
            return
        for child in self.board_canvas.winfo_children():
            child.destroy()
        self.board_card_widgets = []
        self.board_inner_widgets = {}

        if not self.board_items:
            tip = ctk.CTkLabel(self.board_canvas, text="当前没有题目，点击“添加普通题”开始。", text_color="#5f6f8f")
            tip.grid(row=0, column=0, sticky="w", padx=10, pady=10)
            return

        total_items = len(self.board_items)
        for idx, item in enumerate(self.board_items, start=1):
            kind = str(item.get("kind", "question"))
            block_id = str(item.get("block_id", "")).strip()
            if not block_id:
                block_id = self._board_new_block_id()
                item["block_id"] = block_id
            if kind == "loop":
                card = self._board_render_loop_block_card(
                    self.board_canvas,
                    item,
                    idx,
                    item_index=idx - 1,
                    item_total=total_items,
                )
            else:
                question = item.get("question") if isinstance(item.get("question"), dict) else self._board_default_question(False)
                item["question"] = question
                card = self._board_render_question_card(
                    self.board_canvas,
                    block_id=block_id,
                    question=question,
                    order_label=str(idx),
                    in_loop=False,
                    top_index=idx - 1,
                    top_total=total_items,
                )
            card.grid(row=idx - 1, column=0, sticky="ew", padx=10, pady=8)
            self.board_card_widgets.append((block_id, card))

    def _board_merge_question_defaults(self, question: Dict[str, Any], in_loop: bool) -> Dict[str, Any]:
        merged = self._board_default_question(in_loop=in_loop)
        merged.update(self._board_clone(question))
        merged["id"] = str(merged.get("id", "")).strip() or make_question_id()
        merged["title"] = str(merged.get("title", "")).strip() or "请填写题目"
        merged["type"] = str(merged.get("type", "single")).strip()
        if merged["type"] not in {"single", "multi", "rating", "slider", "text", "textarea"}:
            merged["type"] = "single"
        merged["required"] = bool(merged.get("required", False))
        if merged["type"] in {"single", "multi"}:
            options = merged.get("options", [])
            if not isinstance(options, list):
                options = []
            merged["options"] = [str(x).strip() for x in options if str(x).strip()] or ["选项1", "选项2"]
            try:
                merged["min_select"] = int(merged.get("min_select", 1))
            except Exception:
                merged["min_select"] = 1
            try:
                merged["max_select"] = int(merged.get("max_select", 2))
            except Exception:
                merged["max_select"] = 2
            merged["min_select"] = max(0, merged["min_select"])
            merged["max_select"] = max(1, merged["max_select"])
        if merged["type"] in {"rating", "slider"}:
            for key, fallback in [("min", 1), ("max", 5), ("step", 1)]:
                try:
                    merged[key] = int(merged.get(key, fallback))
                except Exception:
                    merged[key] = fallback
            merged["step"] = max(1, int(merged.get("step", 1)))
        if merged["type"] in {"text", "textarea"}:
            for key in ["min_length", "max_length", "min_words", "max_words", "max_lines"]:
                try:
                    merged[key] = int(merged.get(key, 0))
                except Exception:
                    merged[key] = 0
                merged[key] = max(0, int(merged.get(key, 0)))
        # 统计项不在问卷设计中维护，统一由 SQL 查询决定。
        for legacy_key in ("stats_methods", "stats_top_n", "stats_bottom_n", "stats_group", "exclude_from_overall"):
            merged.pop(legacy_key, None)
        if in_loop:
            merged["repeat_filter"] = str(merged.get("repeat_filter", "all")).strip().lower() or "all"
        else:
            merged.pop("repeat_filter", None)
        return merged

    def _board_load_schema_to_state(self, schema: Dict[str, Any]) -> None:
        meta = schema.get("meta", {}) if isinstance(schema.get("meta"), dict) else {}
        self.board_template_meta = {
            str(k): self._board_clone(v)
            for k, v in meta.items()
            if str(k).startswith("template_")
        }
        rules_raw = meta.get("validation_rules", [])
        if isinstance(rules_raw, list):
            self.board_validation_rules = [rule for rule in rules_raw if isinstance(rule, dict)]
        else:
            self.board_validation_rules = []
        list_objects = meta.get("list_objects", [])
        if isinstance(list_objects, list):
            cleaned_list_objects: List[Dict[str, Any]] = []
            for obj in list_objects:
                if not isinstance(obj, dict):
                    continue
                name = str(obj.get("name", "")).strip()
                if not name:
                    continue
                items_raw = obj.get("items", [])
                items: List[Dict[str, Any]] = []
                if isinstance(items_raw, list):
                    for item in items_raw:
                        if isinstance(item, dict):
                            key = str(item.get("key", "")).strip() or str(item.get("value", "")).strip()
                            label = str(item.get("label", "")).strip() or key
                        else:
                            key = str(item).strip()
                            label = key
                        if not key:
                            continue
                        items.append({"key": key, "label": label})
                cleaned_list_objects.append(
                    {
                        "name": name,
                        "type": str(obj.get("type", "text")).strip() or "text",
                        "items": items,
                        "source": str(obj.get("source", "manual")).strip() or "manual",
                        "readonly": bool(obj.get("readonly", False)),
                    }
                )
            self.board_list_objects = cleaned_list_objects
        else:
            self.board_list_objects = []

        board_v2 = meta.get("board_v2", {}) if isinstance(meta.get("board_v2"), dict) else {}
        saved_items = board_v2.get("items", []) if isinstance(board_v2.get("items"), list) else []
        loaded_items: List[Dict[str, Any]] = []
        if saved_items:
            for raw in saved_items:
                if not isinstance(raw, dict):
                    continue
                kind = str(raw.get("kind", "question")).strip()
                block_id = str(raw.get("block_id", "")).strip() or self._board_new_block_id()
                if kind == "loop":
                    inner_raw = raw.get("inner_questions", [])
                    inner_questions: List[Dict[str, Any]] = []
                    if isinstance(inner_raw, list):
                        for q in inner_raw:
                            if isinstance(q, dict):
                                inner_questions.append(self._board_merge_question_defaults(q, in_loop=True))
                    if not inner_questions:
                        inner_questions = [self._board_default_question(in_loop=True)]
                    loaded_items.append(
                        {
                            "kind": "loop",
                            "block_id": block_id,
                            "title": str(raw.get("title", "")).strip() or "循环块",
                            "description": str(raw.get("description", "")).strip(),
                            "repeat_from": str(raw.get("repeat_from", "")).strip(),
                            "visible_if": raw.get("visible_if") if isinstance(raw.get("visible_if"), dict) else None,
                            "inner_questions": inner_questions,
                        }
                    )
                else:
                    question = raw.get("question", {}) if isinstance(raw.get("question"), dict) else {}
                    loaded_items.append(
                        {
                            "kind": "question",
                            "block_id": block_id,
                            "question": self._board_merge_question_defaults(question, in_loop=False),
                            "visible_if": raw.get("visible_if") if isinstance(raw.get("visible_if"), dict) else None,
                        }
                    )
        else:
            questions = schema.get("questions", []) if isinstance(schema.get("questions"), list) else []
            last_loop: Optional[Dict[str, Any]] = None
            for raw_q in questions:
                if not isinstance(raw_q, dict):
                    continue
                q = self._board_clone(raw_q)
                repeat_from = str(q.pop("repeat_from", "")).strip()
                if repeat_from:
                    if last_loop and str(last_loop.get("repeat_from", "")).strip() == repeat_from:
                        last_loop["inner_questions"].append(self._board_merge_question_defaults(q, in_loop=True))
                    else:
                        last_loop = {
                            "kind": "loop",
                            "block_id": self._board_new_block_id(),
                            "title": "循环块",
                            "description": "",
                            "repeat_from": repeat_from,
                            "visible_if": None,
                            "inner_questions": [self._board_merge_question_defaults(q, in_loop=True)],
                        }
                        loaded_items.append(last_loop)
                else:
                    last_loop = None
                    loaded_items.append(
                        {
                            "kind": "question",
                            "block_id": self._board_new_block_id(),
                            "question": self._board_merge_question_defaults(q, in_loop=False),
                            "visible_if": None,
                        }
                    )
        # 兼容旧数据：历史“名单循环”统一迁移为“列表循环”。
        first_list_name = ""
        for obj in self.board_list_objects:
            name = str(obj.get("name", "")).strip()
            if name:
                first_list_name = name
                break
        for item in loaded_items:
            if str(item.get("kind", "")).strip() != "loop":
                continue
            repeat_from = str(item.get("repeat_from", "")).strip()
            if repeat_from == ROSTER_REPEAT_TOKEN:
                item["repeat_from"] = f"__list__:{first_list_name}" if first_list_name else ""
        self.board_items = loaded_items or [
            {
                "kind": "question",
                "block_id": self._board_new_block_id(),
                "question": self._board_default_question(in_loop=False),
                "visible_if": None,
            }
        ]

    def _board_and_rules(self, left: Optional[Dict[str, Any]], right: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if left and right:
            return {"all": [left, right]}
        return left or right

    def _board_build_schema(self) -> Dict[str, Any]:
        intro = self.board_intro_text.get("1.0", "end").strip()
        questions: List[Dict[str, Any]] = []
        for item in self.board_items:
            kind = str(item.get("kind", "question")).strip()
            if kind == "loop":
                repeat_from = str(item.get("repeat_from", "")).strip()
                block_visible = item.get("visible_if") if isinstance(item.get("visible_if"), dict) else None
                for inner in item.get("inner_questions", []):
                    q = self._board_merge_question_defaults(inner, in_loop=True)
                    q["repeat_from"] = repeat_from
                    q["visible_if"] = self._board_and_rules(block_visible, q.get("visible_if") if isinstance(q.get("visible_if"), dict) else None)
                    questions.append(q)
            else:
                q = self._board_merge_question_defaults(item.get("question", {}), in_loop=False)
                q.pop("repeat_from", None)
                q["visible_if"] = self._board_and_rules(
                    item.get("visible_if") if isinstance(item.get("visible_if"), dict) else None,
                    q.get("visible_if") if isinstance(q.get("visible_if"), dict) else None,
                )
                questions.append(q)

        list_objects: List[Dict[str, Any]] = []
        for obj in self.board_list_objects:
            if not isinstance(obj, dict):
                continue
            name = str(obj.get("name", "")).strip()
            if not name:
                continue
            items = obj.get("items", [])
            normalized_items: List[Dict[str, Any]] = []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        key = str(item.get("key", "")).strip() or str(item.get("value", "")).strip()
                        label = str(item.get("label", "")).strip() or key
                    else:
                        key = str(item).strip()
                        label = key
                    if not key:
                        continue
                    normalized_items.append({"key": key, "label": label})
            list_objects.append(
                {
                    "name": name,
                    "type": str(obj.get("type", "text")).strip() or "text",
                    "items": normalized_items,
                    "source": str(obj.get("source", "manual")).strip() or "manual",
                    "readonly": bool(obj.get("readonly", False)),
                }
            )

        meta_out: Dict[str, Any] = self._board_clone(self.board_template_meta) if isinstance(self.board_template_meta, dict) else {}
        meta_out.update(
            {
                "designer": "board_v2",
                "capability_flags": [
                    "board",
                    "loop_block",
                    "list_objects",
                    "validation_rules",
                ],
                "board_v2": {
                    "items": self._board_clone(self.board_items),
                },
                "list_objects": list_objects,
                "validation_rules": self._board_clone(self.board_validation_rules),
            }
        )
        return {
            "version": 2,
            "intro": intro,
            "meta": meta_out,
            "questions": questions,
        }

    def _board_check_configuration(self, show_success: bool = True) -> bool:
        errors: List[str] = []
        warnings: List[str] = []

        title = self.board_entry_title.get().strip()
        if not title:
            errors.append("问卷标题不能为空。")
        if not self.board_items:
            errors.append("至少需要 1 个题目块。")

        auth_mode = AUTH_LABEL_TO_VALUE.get(self.board_auth_mode_var.get().strip(), "open")
        roster_id = self._extract_qid(self.board_auth_roster_var.get())
        collect_fields = self._board_normalize_collect_fields(self.board_collect_fields)
        if auth_mode != "open" and not roster_id:
            errors.append("名单校验模式下必须绑定名单。")
        if auth_mode != "open" and not collect_fields:
            errors.append("名单校验模式下必须至少配置 1 个进入前采集字段。")

        list_name_seen: set[str] = set()
        for obj in self.board_list_objects:
            if not isinstance(obj, dict):
                continue
            name = str(obj.get("name", "")).strip()
            if not name:
                errors.append("存在未命名列表对象。")
                continue
            if name in list_name_seen:
                errors.append(f"列表名称重复：{name}")
            list_name_seen.add(name)
            list_type = str(obj.get("type", "text")).strip().lower() or "text"
            items = obj.get("items", [])
            if not isinstance(items, list):
                errors.append(f"列表 {name} 的 items 必须是数组。")
                continue
            if list_type == "number":
                for item in items:
                    if isinstance(item, dict):
                        key = str(item.get("key", "")).strip() or str(item.get("value", "")).strip()
                    else:
                        key = str(item).strip()
                    if not key:
                        continue
                    try:
                        float(key)
                    except Exception:
                        errors.append(f"数字列表 {name} 包含非数字项：{key}")
                        break

        qid_seen: set[str] = set()
        qid_duplicate: set[str] = set()
        required_multi_ids: set[str] = set()
        for item in self.board_items:
            if item.get("kind") == "loop":
                repeat_from = str(item.get("repeat_from", "")).strip()
                if not repeat_from:
                    errors.append(f"循环块“{item.get('title', '循环块')}”未设置循环依据。")
                if repeat_from.startswith("__list__:"):
                    list_name = repeat_from.split(":", 1)[1].strip()
                    if not any(str(obj.get("name", "")).strip() == list_name for obj in self.board_list_objects):
                        errors.append(f"循环块“{item.get('title', '循环块')}”引用了不存在的列表：{list_name}")
                inner = item.get("inner_questions", [])
                if not inner:
                    errors.append(f"循环块“{item.get('title', '循环块')}”内至少需要 1 道题。")
                pool = inner
            else:
                pool = [item.get("question", {})]

            for question in pool:
                qid = str(question.get("id", "")).strip()
                title_q = str(question.get("title", "")).strip()
                q_type = str(question.get("type", "")).strip()
                if not qid:
                    errors.append("存在题目未设置 ID。")
                    continue
                if any(char.isspace() for char in qid):
                    errors.append(f"{qid}：题目ID不能包含空白字符。")
                if qid in qid_seen:
                    qid_duplicate.add(qid)
                qid_seen.add(qid)
                if not title_q:
                    errors.append(f"{qid}：题目标题不能为空。")
                if q_type in {"single", "multi"}:
                    options = question.get("options", [])
                    if not isinstance(options, list) or not any(str(x).strip() for x in options):
                        errors.append(f"{qid}：单选/多选题必须设置选项。")
                if q_type == "multi" and bool(question.get("required", False)):
                    required_multi_ids.add(qid)
                    try:
                        min_select = int(question.get("min_select", 0) or 0)
                    except Exception:
                        min_select = -1
                    try:
                        max_select = int(question.get("max_select", 0) or 0)
                    except Exception:
                        max_select = -1
                    if min_select < 0:
                        errors.append(f"{qid}：最少选择不能小于 0。")
                    if max_select <= 0:
                        errors.append(f"{qid}：最多选择必须大于 0。")
                    if max_select and min_select and min_select > max_select:
                        errors.append(f"{qid}：最少选择不能大于最多选择。")
                if q_type in {"rating", "slider"}:
                    try:
                        min_v = int(question.get("min", 1))
                        max_v = int(question.get("max", 5))
                        step = int(question.get("step", 1))
                    except Exception:
                        errors.append(f"{qid}：评分/滑杆参数必须为整数。")
                        continue
                    if min_v >= max_v:
                        errors.append(f"{qid}：最小值必须小于最大值。")
                    if step <= 0:
                        errors.append(f"{qid}：步进必须大于 0。")

        if qid_duplicate:
            errors.append(f"题目ID重复：{', '.join(sorted(qid_duplicate))}")

        for item in self.board_items:
            if item.get("kind") != "loop":
                continue
            repeat_from = str(item.get("repeat_from", "")).strip()
            if repeat_from and repeat_from != ROSTER_REPEAT_TOKEN and not repeat_from.startswith("__list__:"):
                if repeat_from not in qid_seen:
                    errors.append(f"循环块“{item.get('title', '循环块')}”引用的题目ID不存在：{repeat_from}")
                elif repeat_from not in required_multi_ids:
                    warnings.append(
                        f"循环块“{item.get('title', '循环块')}”依据题目 {repeat_from} 不是“必填多选题”，循环项可能为空。"
                    )

        valid_rule_types = {"sql_aggregate"}
        valid_ops = {"equals", "not_equals", "gt", "gte", "lt", "lte", "between", "not_between"}
        for idx, rule in enumerate(self.board_validation_rules, start=1):
            if not isinstance(rule, dict):
                errors.append(f"联合规则 #{idx} 不是对象。")
                continue
            r_type = str(rule.get("type", "")).strip().lower()
            if not r_type:
                r_type = "sql_aggregate"
            if r_type not in valid_rule_types:
                errors.append(f"联合规则 #{idx} 类型无效：{r_type or '[空]'}")
                continue
            op = str(rule.get("op", "")).strip().lower()
            if op not in valid_ops:
                errors.append(f"联合规则 #{idx} 比较符无效：{op or '[空]'}")
            sql_text = str(rule.get("sql", "")).strip()
            if not sql_text:
                errors.append(f"联合规则 #{idx} 缺少 SQL。")
            else:
                try:
                    self.service.validate_live_rule_sql(sql_text)
                except ServiceError as exc:
                    errors.append(f"联合规则 #{idx} SQL 无效：{exc}")
            value_text = str(rule.get("value", "")).strip()
            try:
                float(value_text)
            except Exception:
                errors.append(f"联合规则 #{idx} 目标值必须是数字。")
            if op in {"between", "not_between"}:
                value2_text = str(rule.get("value2", "")).strip()
                try:
                    float(value2_text)
                except Exception:
                    errors.append(f"联合规则 #{idx} 使用区间比较时，区间上限必须是数字。")

        lines: List[str] = []
        if errors:
            lines.append("发现问题：")
            lines.extend([f"- {msg}" for msg in errors])
        if warnings:
            if lines:
                lines.append("")
            lines.append("提示项：")
            lines.extend([f"- {msg}" for msg in warnings])
        if not lines:
            lines.append("配置体检通过：未发现明显问题。")

        if errors:
            messagebox.showerror("配置体检", "\n".join(lines), parent=self)
            return False
        if warnings:
            messagebox.showwarning("配置体检", "\n".join(lines), parent=self)
            return True
        if show_success:
            messagebox.showinfo("配置体检", "\n".join(lines), parent=self)
        return True

    def _board_save_questionnaire(self) -> None:
        if not self._board_check_configuration(show_success=False):
            return
        title = self.board_entry_title.get().strip()
        if not title:
            messagebox.showwarning("提示", "请填写问卷标题。", parent=self)
            return
        desc = self.board_desc_text.get("1.0", "end").strip()
        passcode = self.board_entry_passcode.get().strip()
        mode = MODE_LABEL_TO_VALUE.get(self.board_mode_var.get().strip(), "realname")
        allow_repeat = bool(self.board_repeat_var.get())
        auth_mode = AUTH_LABEL_TO_VALUE.get(self.board_auth_mode_var.get().strip(), "open")
        auth_roster_id = self._extract_qid(self.board_auth_roster_var.get())
        if auth_mode != "open" and not auth_roster_id:
            messagebox.showwarning("提示", "名单校验模式下必须绑定名单。", parent=self)
            return

        self._board_sync_auto_lists(re_render=False)
        schema = self._board_build_schema()
        try:
            qid = self.service.create_questionnaire(
                title=title,
                description=desc,
                identity_mode=mode,
                allow_repeat=allow_repeat,
                passcode=passcode,
                schema=schema,
                questionnaire_id=self.editing_qid,
                auth_mode=auth_mode,
                auth_roster_id=auth_roster_id,
                identity_fields=self._board_collect_identity_fields(),
            )
            self.editing_qid = qid
            self._refresh_all()
            messagebox.showinfo("成功", f"问卷已保存：{qid}", parent=self)
        except ServiceError as exc:
            messagebox.showerror("保存失败", str(exc), parent=self)

    def _board_load_selected_questionnaire(self) -> None:
        qid = self._board_selected_questionnaire_id()
        if not qid:
            messagebox.showwarning("提示", "请先在左侧选择问卷。", parent=self)
            return
        q = self.service.get_questionnaire(qid)
        if not q:
            messagebox.showerror("失败", "问卷不存在。", parent=self)
            return
        self.editing_qid = qid
        self.board_entry_title.delete(0, "end")
        self.board_entry_title.insert(0, str(q.get("title", "")))
        self.board_entry_passcode.delete(0, "end")
        self.board_desc_text.delete("1.0", "end")
        self.board_desc_text.insert("1.0", str(q.get("description", "")))
        schema = q.get("schema", {}) if isinstance(q.get("schema"), dict) else {}
        self.board_intro_text.delete("1.0", "end")
        self.board_intro_text.insert("1.0", str(schema.get("intro", "")))

        self.board_mode_var.set(MODE_VALUE_TO_LABEL.get(str(q.get("identity_mode", "realname")), "实名"))
        self.board_repeat_var.set(bool(q.get("allow_repeat", False)))
        self.board_auth_mode_var.set(AUTH_VALUE_TO_LABEL.get(str(q.get("auth_mode", "open")), "开放作答"))
        roster_id = str(q.get("auth_roster_id", "")).strip()
        if roster_id:
            roster_match = next((f"{r['id']} | {r['name']}" for r in self.roster_cache if str(r["id"]) == roster_id), roster_id)
            self.board_auth_roster_var.set(roster_match)
        else:
            self.board_auth_roster_var.set("")

        fields = q.get("identity_fields", {}) if isinstance(q.get("identity_fields"), dict) else {}
        self.board_same_device_repeat_var.set(bool(fields.get("allow_same_device_repeat", False)))
        collect_fields = fields.get("collect_fields", [])
        if isinstance(collect_fields, list) and collect_fields:
            self.board_collect_fields = self._board_normalize_collect_fields(collect_fields)
        else:
            fallback: List[Dict[str, str]] = []
            if bool(fields.get("collect_code", False)):
                fallback.append({"key": "member_code", "label": "编号"})
            if bool(fields.get("collect_name", False)):
                fallback.append({"key": "member_name", "label": "姓名"})
            self.board_collect_fields = self._board_normalize_collect_fields(fallback)
        self._board_refresh_collect_fields_summary()

        self._board_load_schema_to_state(schema)
        self._board_sync_auto_lists(re_render=False)
        self._board_clear_logic_panel(silent=True)
        self._board_render_canvas()
        messagebox.showinfo("提示", f"已载入问卷 {qid}，修改后点击保存。", parent=self)

    def _build_template_center_tab(self) -> None:
        if self.design_logic_disabled:
            self._build_design_disabled_tab(self.tab_templates, "场景模板模块已停用")
            return
        tab = self.tab_templates
        tab.grid_columnconfigure(0, weight=1, minsize=420)
        tab.grid_columnconfigure(1, weight=1, minsize=580)
        tab.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(tab, corner_radius=14)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=12)
        top.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkLabel(top, text="场景模板中心", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 6)
        )
        ctk.CTkLabel(
            top,
            text="包含 100 个模板场景，可筛选、可手动调参、可直接建问卷。",
            text_color="#55617a",
        ).grid(row=1, column=0, columnspan=4, sticky="w", padx=12, pady=(0, 8))

        self.tpl_search_entry = ctk.CTkEntry(top, placeholder_text="搜索模板名称/标签")
        self.tpl_search_entry.grid(row=2, column=0, padx=8, pady=(0, 12), sticky="ew")
        self.tpl_search_entry.bind("<KeyRelease>", lambda _event: self._refresh_template_catalog())

        category_values = ["全部分类"] + scenario_templates.list_categories()
        self.tpl_category_var = ctk.StringVar(value=category_values[0])
        self.tpl_category_menu = ctk.CTkOptionMenu(top, variable=self.tpl_category_var, values=category_values)
        self.tpl_category_menu.grid(row=2, column=1, padx=8, pady=(0, 12), sticky="ew")
        self.tpl_category_menu.configure(command=lambda _value: self._refresh_template_catalog())

        self.tpl_support_var = ctk.StringVar(value="全部支持级别")
        self.tpl_support_menu = ctk.CTkOptionMenu(
            top,
            variable=self.tpl_support_var,
            values=["全部支持级别", "可直接使用", "可用（需调整）", "规划中"],
        )
        self.tpl_support_menu.grid(row=2, column=2, padx=8, pady=(0, 12), sticky="ew")
        self.tpl_support_menu.configure(command=lambda _value: self._refresh_template_catalog())

        ctk.CTkButton(top, text="刷新模板列表", command=self._refresh_template_catalog).grid(
            row=2, column=3, padx=(8, 12), pady=(0, 12), sticky="ew"
        )

        left = ctk.CTkFrame(tab, corner_radius=14)
        left.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(left, text="模板列表", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 8)
        )

        list_wrap = ctk.CTkFrame(left, fg_color="#f8fbff", corner_radius=10)
        list_wrap.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        list_wrap.grid_rowconfigure(0, weight=1)
        list_wrap.grid_columnconfigure(0, weight=1)
        self.tree_templates = ttk.Treeview(
            list_wrap,
            columns=("name", "category", "support"),
            show="headings",
            height=18,
        )
        for col, title, width in [
            ("name", "模板名称", 200),
            ("category", "分类", 100),
            ("support", "支持度", 90),
        ]:
            self.tree_templates.heading(col, text=title)
            self.tree_templates.column(col, width=width, anchor="w")
        self.tree_templates.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(list_wrap, orient="vertical", command=self.tree_templates.yview).grid(row=0, column=1, sticky="ns")
        self.tree_templates.bind("<<TreeviewSelect>>", self._on_template_selected)

        right = ctk.CTkScrollableFrame(tab, corner_radius=14)
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))
        right.grid_columnconfigure(0, weight=1)

        self.tpl_detail_title_var = ctk.StringVar(value="请选择左侧模板")
        ctk.CTkLabel(right, textvariable=self.tpl_detail_title_var, font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 8)
        )

        self.tpl_detail_text = ctk.CTkTextbox(right, height=140)
        self.tpl_detail_text.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 10))

        cfg = ctk.CTkFrame(right, fg_color="#f8fbff", corner_radius=12)
        cfg.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        cfg.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(cfg, text="模板参数（可手动配置）", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 4)
        )

        self.tpl_title_override = self._labeled_entry(cfg, "问卷标题（可改）", 1, 0)
        self.tpl_passcode = self._labeled_entry(cfg, "访问口令（可选）", 1, 1, show="*")

        mode_wrap = ctk.CTkFrame(cfg, fg_color="transparent")
        mode_wrap.grid(row=2, column=0, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(mode_wrap, text="身份模式").pack(anchor="w")
        self.tpl_identity_var = ctk.StringVar(value="实名")
        self.tpl_identity_menu = ctk.CTkOptionMenu(
            mode_wrap,
            variable=self.tpl_identity_var,
            values=list(MODE_LABEL_TO_VALUE.keys()),
        )
        self.tpl_identity_menu.pack(fill="x", pady=(4, 0))

        auth_wrap = ctk.CTkFrame(cfg, fg_color="transparent")
        auth_wrap.grid(row=2, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(auth_wrap, text="身份验证方式").pack(anchor="w")
        self.tpl_auth_var = ctk.StringVar(value="开放作答")
        self.tpl_auth_menu = ctk.CTkOptionMenu(
            auth_wrap,
            variable=self.tpl_auth_var,
            values=list(AUTH_LABEL_TO_VALUE.keys()),
        )
        self.tpl_auth_menu.pack(fill="x", pady=(4, 0))

        roster_wrap = ctk.CTkFrame(cfg, fg_color="transparent")
        roster_wrap.grid(row=3, column=0, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(roster_wrap, text="绑定名单（可选）").pack(anchor="w")
        self.tpl_roster_var = ctk.StringVar(value="")
        self.tpl_roster_menu = ctk.CTkOptionMenu(roster_wrap, variable=self.tpl_roster_var, values=[""])
        self.tpl_roster_menu.pack(fill="x", pady=(4, 0))

        switches = ctk.CTkFrame(cfg, fg_color="transparent")
        switches.grid(row=3, column=1, sticky="ew", padx=10, pady=8)
        switches.grid_columnconfigure((0, 1), weight=1)
        self.tpl_allow_repeat_var = ctk.BooleanVar(value=False)
        self.tpl_allow_same_device_repeat_var = ctk.BooleanVar(value=False)
        self.tpl_use_roster_loop_var = ctk.BooleanVar(value=False)
        self.tpl_waitlist_var = ctk.BooleanVar(value=False)
        self.tpl_approval_var = ctk.BooleanVar(value=False)
        self.tpl_first_come_var = ctk.BooleanVar(value=False)
        self.tpl_allow_modify_var = ctk.BooleanVar(value=False)
        self.tpl_auto_ranking_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(switches, text="允许重复提交", variable=self.tpl_allow_repeat_var).grid(
            row=0, column=0, sticky="w", padx=4, pady=2
        )
        ctk.CTkSwitch(switches, text="按名单字段列表循环评分", variable=self.tpl_use_roster_loop_var).grid(
            row=0, column=1, sticky="w", padx=4, pady=2
        )
        ctk.CTkSwitch(switches, text="允许同设备重复", variable=self.tpl_allow_same_device_repeat_var).grid(
            row=1, column=0, sticky="w", padx=4, pady=2
        )
        ctk.CTkSwitch(switches, text="启用候补", variable=self.tpl_waitlist_var).grid(
            row=1, column=1, sticky="w", padx=4, pady=2
        )
        ctk.CTkSwitch(switches, text="需审批通过", variable=self.tpl_approval_var).grid(
            row=2, column=0, sticky="w", padx=4, pady=2
        )
        ctk.CTkSwitch(switches, text="先到先得", variable=self.tpl_first_come_var).grid(
            row=2, column=1, sticky="w", padx=4, pady=2
        )
        ctk.CTkSwitch(switches, text="允许后续修改", variable=self.tpl_allow_modify_var).grid(
            row=3, column=0, sticky="w", padx=4, pady=2
        )
        ctk.CTkSwitch(switches, text="评分自动排名", variable=self.tpl_auto_ranking_var).grid(
            row=3, column=1, sticky="w", padx=4, pady=(2, 0)
        )

        numeric = ctk.CTkFrame(cfg, fg_color="transparent")
        numeric.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 8))
        numeric.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.tpl_max_select = self._small_labeled_entry(numeric, "最多可选", 0)
        self.tpl_rating_min = self._small_labeled_entry(numeric, "评分最小", 1)
        self.tpl_rating_max = self._small_labeled_entry(numeric, "评分最大", 2)
        self.tpl_submission_limit = self._small_labeled_entry(numeric, "提交上限(0不限)", 3)
        self.tpl_max_select.insert(0, "2")
        self.tpl_rating_min.insert(0, "1")
        self.tpl_rating_max.insert(0, "10")
        self.tpl_submission_limit.insert(0, "0")

        actions = ctk.CTkFrame(right, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 12))
        actions.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkButton(actions, text="加载到问卷编辑器（可再改题）", command=self._apply_template_center_to_editor).grid(
            row=0, column=0, padx=4, pady=4, sticky="ew"
        )
        ctk.CTkButton(actions, text="直接创建并启用", command=self._create_from_template_center).grid(
            row=0, column=1, padx=4, pady=4, sticky="ew"
        )
        ctk.CTkButton(actions, text="恢复默认参数", command=self._reset_template_center_options).grid(
            row=0, column=2, padx=4, pady=4, sticky="ew"
        )
        ctk.CTkButton(actions, text="跳转问卷管理", command=lambda: self._switch_tab("问卷管理")).grid(
            row=0, column=3, padx=4, pady=4, sticky="ew"
        )

        self._refresh_template_catalog()

    def _build_roster_tab(self) -> None:
        tab = self.tab_roster
        tab.grid_columnconfigure(0, weight=1, minsize=360)
        tab.grid_columnconfigure(1, weight=2, minsize=520)
        tab.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(tab, corner_radius=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left, text="名单列表", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 8)
        )
        roster_wrap = ctk.CTkFrame(left, fg_color="#f8fbff", corner_radius=10)
        roster_wrap.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        roster_wrap.grid_rowconfigure(0, weight=1)
        roster_wrap.grid_columnconfigure(0, weight=1)

        self.tree_rosters = ttk.Treeview(
            roster_wrap,
            columns=("id", "name", "count"),
            show="headings",
            height=16,
        )
        for col, title, width in [
            ("id", "名单ID", 120),
            ("name", "名单名称", 170),
            ("count", "成员数", 80),
        ]:
            self.tree_rosters.heading(col, text=title)
            self.tree_rosters.column(col, width=width, anchor="w")
        self.tree_rosters.grid(row=0, column=0, sticky="nsew")
        self.tree_rosters.bind("<<TreeviewSelect>>", self._on_roster_selected)

        roster_btns = ctk.CTkFrame(left, fg_color="transparent")
        roster_btns.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        roster_btns.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkButton(roster_btns, text="新建名单", command=self._create_roster).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(roster_btns, text="配置字段", command=self._configure_roster_columns).grid(
            row=0, column=1, padx=4, sticky="ew"
        )
        ctk.CTkButton(roster_btns, text="导入名单", command=self._import_roster).grid(row=0, column=2, padx=4, sticky="ew")
        ctk.CTkButton(roster_btns, text="刷新名单", command=self._refresh_roster_list).grid(row=0, column=3, padx=4, sticky="ew")
        ctk.CTkButton(roster_btns, text="重命名", command=self._rename_selected_roster).grid(
            row=1, column=0, padx=4, pady=(6, 0), sticky="ew"
        )
        ctk.CTkButton(roster_btns, text="复制", command=self._copy_selected_roster).grid(
            row=1, column=1, padx=4, pady=(6, 0), sticky="ew"
        )
        ctk.CTkButton(roster_btns, text="删除", command=self._delete_selected_roster).grid(
            row=1, column=2, padx=4, pady=(6, 0), sticky="ew"
        )

        right = ctk.CTkFrame(tab, corner_radius=14)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        self.roster_title = ctk.CTkLabel(right, text="成员列表", font=ctk.CTkFont(size=18, weight="bold"))
        self.roster_title.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))

        member_wrap = ctk.CTkFrame(right, fg_color="#f8fbff", corner_radius=10)
        member_wrap.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        member_wrap.grid_rowconfigure(0, weight=1)
        member_wrap.grid_columnconfigure(0, weight=1)

        self.tree_roster_members = ttk.Treeview(
            member_wrap,
            columns=("id", "key"),
            show="headings",
            height=18,
        )
        for col, title, width in [
            ("id", "行ID", 60),
            ("key", "唯一标识", 130),
        ]:
            self.tree_roster_members.heading(col, text=title)
            self.tree_roster_members.column(col, width=width, anchor="w")
        self.tree_roster_members.grid(row=0, column=0, sticky="nsew")

        member_btns = ctk.CTkFrame(right, fg_color="transparent")
        member_btns.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        member_btns.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(member_btns, text="手工新增成员", command=self._add_roster_member_manual).grid(
            row=0, column=0, padx=4, sticky="ew"
        )
        ctk.CTkButton(member_btns, text="删除选中成员", command=self._remove_selected_roster_member).grid(
            row=0, column=1, padx=4, sticky="ew"
        )
        ctk.CTkButton(member_btns, text="刷新成员", command=self._refresh_roster_members).grid(
            row=0, column=2, padx=4, sticky="ew"
        )

    def _build_server_tab(self) -> None:
        tab = self.tab_server
        tab.grid_columnconfigure((0, 1), weight=1)
        tab.grid_rowconfigure(1, weight=1)

        cfg = ctk.CTkFrame(tab, corner_radius=14)
        cfg.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=12)
        cfg.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.entry_host = self._small_labeled_entry(cfg, "监听地址", 0)
        self.entry_host.insert(0, DEFAULT_HOST)
        self.entry_port = self._small_labeled_entry(cfg, "端口", 1)
        self.entry_port.insert(0, str(DEFAULT_PORT))

        q_wrap = ctk.CTkFrame(cfg, fg_color="transparent")
        q_wrap.grid(row=0, column=2, columnspan=2, sticky="ew", padx=8, pady=8)
        q_wrap.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(q_wrap, text="默认问卷链接").grid(row=0, column=0, sticky="w")
        self.server_q_var = ctk.StringVar(value="")
        self.server_q_menu = ctk.CTkOptionMenu(
            q_wrap,
            variable=self.server_q_var,
            values=[""],
            command=self._on_server_q_menu_change,
        )
        self.server_q_menu.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        btns = ctk.CTkFrame(cfg, fg_color="transparent")
        btns.grid(row=0, column=4, sticky="ew", padx=8, pady=8)
        btns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btns, text="启动服务", command=self._start_server).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(btns, text="停止服务", command=self._stop_server).grid(row=0, column=1, padx=4, sticky="ew")

        panel = ctk.CTkFrame(tab, corner_radius=14)
        panel.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=(0, 12))
        panel.grid_columnconfigure(0, weight=3)
        panel.grid_columnconfigure(1, weight=2)
        panel.grid_rowconfigure(1, weight=1)

        self.server_info = ctk.CTkTextbox(panel)
        self.server_info.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))

        tools = ctk.CTkFrame(panel, fg_color="transparent")
        tools.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=12)
        tools.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(tools, text="打开首页", command=self._open_server_home).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(tools, text="打开默认问卷", command=self._open_server_questionnaire).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(tools, text="刷新状态", command=self._refresh_server_info).grid(row=0, column=2, padx=4, sticky="ew")

        qr_card = ctk.CTkFrame(panel, corner_radius=12, fg_color="#f8fbff")
        qr_card.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))
        qr_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(qr_card, text="扫码打开问卷", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )
        self.server_qr_label = ctk.CTkLabel(
            qr_card,
            text="启动服务后显示二维码",
            width=240,
            height=240,
            corner_radius=10,
            fg_color="#ffffff",
            text_color="#4f607f",
        )
        self.server_qr_label.grid(row=1, column=0, padx=12, pady=8, sticky="n")

        link_wrap = ctk.CTkFrame(qr_card, fg_color="transparent")
        link_wrap.grid(row=2, column=0, sticky="ew", padx=12, pady=(6, 10))
        link_wrap.grid_columnconfigure(0, weight=1)
        self.server_link_var = tk.StringVar(value="")
        self.server_link_entry = ctk.CTkEntry(link_wrap, textvariable=self.server_link_var, state="readonly")
        self.server_link_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(link_wrap, text="复制链接", width=92, command=self._copy_server_link).grid(
            row=0, column=1, sticky="e"
        )

    def _build_offline_tab(self) -> None:
        tab = self.tab_offline
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        card = ctk.CTkFrame(tab, corner_radius=14)
        card.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        card.grid_columnconfigure((0, 1), weight=1)

        qbox = ctk.CTkFrame(card, fg_color="transparent")
        qbox.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        qbox.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(qbox, text="选择问卷").grid(row=0, column=0, sticky="w")
        self.offline_q_var = ctk.StringVar(value="")
        self.offline_q_menu = ctk.CTkOptionMenu(qbox, variable=self.offline_q_var, values=[""])
        self.offline_q_menu.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        pbox = ctk.CTkFrame(card, fg_color="transparent")
        pbox.grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        pbox.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pbox, text="导出路径").grid(row=0, column=0, sticky="w")
        self.offline_path_var = tk.StringVar(value=str(self.service.paths.exports_dir / "offline_form.html"))
        self.offline_path_entry = ctk.CTkEntry(pbox, textvariable=self.offline_path_var)
        self.offline_path_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        bbar = ctk.CTkFrame(tab, fg_color="transparent")
        bbar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        bbar.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(bbar, text="选择路径", command=self._choose_offline_path).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(bbar, text="导出离线 HTML", command=self._export_offline).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(bbar, text="打开导出目录", command=self._open_export_dir).grid(row=0, column=2, padx=4, sticky="ew")

        self.offline_log = ctk.CTkTextbox(tab)
        self.offline_log.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _build_votes_tab(self) -> None:
        tab = self.tab_votes
        tab.grid_columnconfigure((0, 1), weight=1)
        tab.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(tab, corner_radius=14)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=12)
        top.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        box = ctk.CTkFrame(top, fg_color="transparent")
        box.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(box, text="选择问卷").grid(row=0, column=0, sticky="w")
        self.stats_q_var = ctk.StringVar(value="")
        self.stats_q_menu = ctk.CTkOptionMenu(box, variable=self.stats_q_var, values=[""])
        self.stats_q_menu.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        ctk.CTkButton(top, text="刷新票据", command=self._refresh_submissions).grid(row=0, column=2, padx=6, pady=8, sticky="ew")
        ctk.CTkButton(top, text="导入 .vote", command=self._import_votes).grid(row=0, column=3, padx=6, pady=8, sticky="ew")
        ctk.CTkButton(top, text="刷新查询模型", command=self._refresh_sql_workbench).grid(
            row=0, column=4, padx=6, pady=8, sticky="ew"
        )
        ctk.CTkButton(top, text="驳回选中票据", command=self._reject_selected_submission).grid(
            row=0, column=5, padx=6, pady=8, sticky="ew"
        )

        left = ctk.CTkFrame(tab, corner_radius=14)
        left.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)

        self.tree_submissions = ttk.Treeview(
            left,
            columns=("id", "time", "source", "name"),
            show="headings",
            height=18,
        )
        for col, text, width in [
            ("id", "票据ID", 140),
            ("time", "提交时间", 170),
            ("source", "来源", 90),
            ("name", "填写者", 140),
        ]:
            self.tree_submissions.heading(col, text=text)
            self.tree_submissions.column(col, width=width, anchor="w")
        self.tree_submissions.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        right = ctk.CTkFrame(tab, corner_radius=14)
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(4, weight=1)

        model_box = ctk.CTkFrame(right, fg_color="transparent")
        model_box.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        model_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(model_box, text="查询数据模型（只读）", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.sql_schema_text = ctk.CTkTextbox(model_box, height=120)
        self.sql_schema_text.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.sql_schema_text.configure(state="disabled")

        preset_bar = ctk.CTkFrame(right, fg_color="transparent")
        preset_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 4))
        preset_bar.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkLabel(preset_bar, text="SQL模板").grid(row=0, column=0, sticky="w")
        self.sql_view_var = ctk.StringVar(value="")
        self.sql_view_menu = ctk.CTkOptionMenu(preset_bar, variable=self.sql_view_var, values=[""])
        self.sql_view_menu.grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkButton(preset_bar, text="加载模板", command=self._load_sql_view_to_editor).grid(
            row=0, column=2, sticky="ew", padx=4
        )
        ctk.CTkButton(preset_bar, text="删除模板", command=self._remove_sql_view).grid(
            row=0, column=3, sticky="ew", padx=4
        )

        sql_box = ctk.CTkFrame(right, fg_color="transparent")
        sql_box.grid(row=2, column=0, sticky="ew", padx=10, pady=(2, 4))
        sql_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(sql_box, text="SQL 查询（仅 SELECT，可多条语句）", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.sql_editor = ctk.CTkTextbox(sql_box, height=130)
        self.sql_editor.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.sql_editor.insert("1.0", "SELECT * FROM submissions ORDER BY submitted_at DESC LIMIT 100")

        run_bar = ctk.CTkFrame(right, fg_color="transparent")
        run_bar.grid(row=3, column=0, sticky="ew", padx=10, pady=(2, 6))
        run_bar.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkButton(run_bar, text="执行查询", command=self._run_sql_query).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(run_bar, text="保存为模板", command=self._save_sql_view).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(run_bar, text="导出查询CSV", command=self._export_sql_result_csv).grid(
            row=0, column=2, padx=4, sticky="ew"
        )
        ctk.CTkButton(run_bar, text="查看原始票据", command=self._show_payload_preview).grid(
            row=0, column=3, padx=4, sticky="ew"
        )

        result_box = ctk.CTkFrame(right, fg_color="transparent")
        result_box.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 10))
        result_box.grid_columnconfigure(0, weight=1)
        result_box.grid_rowconfigure(0, weight=1)
        self.sql_console_text = ctk.CTkTextbox(result_box, font=ctk.CTkFont(family="Consolas", size=12))
        self.sql_console_text.grid(row=0, column=0, sticky="nsew")
        self.sql_console_text.insert("1.0", "SQL> 等待执行查询...\n")

        self.sql_status_var = ctk.StringVar(value="等待执行查询。")
        ctk.CTkLabel(right, textvariable=self.sql_status_var, text_color="#5d6b82").grid(
            row=5, column=0, sticky="w", padx=10, pady=(0, 8)
        )
        self.sql_result_sets: List[Dict[str, Any]] = []
        self.sql_active_result_index = 0
        self.sql_view_cache: List[Dict[str, Any]] = []

    def _build_settings_tab(self) -> None:
        tab = self.tab_settings
        tab.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(tab, corner_radius=14)
        card.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        card.grid_columnconfigure((0, 1, 2), weight=1)

        self.old_pwd = self._small_labeled_entry(card, "旧密码", 0, show="*")
        self.new_pwd = self._small_labeled_entry(card, "新密码", 1, show="*")
        self.new_pwd2 = self._small_labeled_entry(card, "确认新密码", 2, show="*")

        ctk.CTkButton(
            tab,
            text="更新管理员密码",
            command=self._change_password,
            width=180,
            height=36,
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))

        ctk.CTkButton(
            tab,
            text="创建数据备份",
            command=self._backup_data,
            width=180,
            height=36,
        ).grid(row=1, column=0, sticky="e", padx=12, pady=(0, 8))

        kernel_card = ctk.CTkFrame(tab, corner_radius=14)
        kernel_card.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        kernel_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(kernel_card, text="界面内核").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.runtime_kernel_var = ctk.StringVar(value="当前：网页内核")
        ctk.CTkLabel(kernel_card, textvariable=self.runtime_kernel_var).grid(row=0, column=1, sticky="w", padx=6, pady=10)
        self.switch_kernel_btn = ctk.CTkButton(
            kernel_card,
            text="切换到 tkinter 内核",
            command=self._toggle_runtime_kernel,
            width=190,
            height=34,
        )
        self.switch_kernel_btn.grid(row=0, column=2, sticky="e", padx=10, pady=10)
        self._refresh_runtime_kernel_controls()

        text = (
            "安全说明:\n"
            "1. 所有提交内容存储为 .vote 加密票据，采用 RSA-OAEP + AES-GCM。\n"
            "2. 解密历史票据需要管理员密码解锁私钥。\n"
            "3. 问卷可启用访问口令，局域网访问先口令验证再提交。"
        )
        box = ctk.CTkTextbox(tab, height=260)
        box.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        box.insert("1.0", text)
        box.configure(state="disabled")

    def _labeled_entry(
        self,
        parent: ctk.CTkFrame,
        label: str,
        row: int,
        column: int,
        show: str = "",
    ) -> ctk.CTkEntry:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=column, sticky="ew", padx=10, pady=8)
        box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(box, text=label).grid(row=0, column=0, sticky="w")
        entry = ctk.CTkEntry(box, show=show)
        entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        return entry

    def _small_labeled_entry(self, parent: ctk.CTkFrame, label: str, column: int, show: str = "") -> ctk.CTkEntry:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=0, column=column, sticky="ew", padx=8, pady=8)
        box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(box, text=label).grid(row=0, column=0, sticky="w")
        entry = ctk.CTkEntry(box, show=show)
        entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        return entry

    def _labeled_text(
        self,
        parent: ctk.CTkFrame,
        label: str,
        row: int,
        column: int,
        columnspan: int,
        height: int = 80,
    ) -> ctk.CTkTextbox:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=column, columnspan=columnspan, sticky="ew", padx=10, pady=8)
        box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(box, text=label).grid(row=0, column=0, sticky="w")
        txt = ctk.CTkTextbox(box, height=height)
        txt.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        return txt

    def _switch_tab(self, tab_name: str) -> None:
        try:
            self.tabs.set(tab_name)
        except Exception:
            return

    def _template_payload(self, template_name: str, options: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        tpl = scenario_templates.get_template_by_name(template_name)
        if not tpl:
            return None
        opts = options or {}
        payload = scenario_templates.build_payload(tpl["key"], options=opts)
        if not payload:
            return None
        payload_out = json.loads(json.dumps(payload, ensure_ascii=False))
        if isinstance(payload_out, dict):
            fields = payload_out.get("identity_fields", {})
            if not isinstance(fields, dict):
                fields = {}
            if "allow_same_device_repeat" in opts:
                fields["allow_same_device_repeat"] = bool(opts.get("allow_same_device_repeat", False))
            payload_out["identity_fields"] = fields
        return payload_out

    def _refresh_template_catalog(self) -> None:
        if not hasattr(self, "tree_templates"):
            return
        self.template_catalog = scenario_templates.list_templates()
        selected = self.tree_templates.selection()
        keep_key = selected[0] if selected else ""

        search = self.tpl_search_entry.get().strip().lower() if hasattr(self, "tpl_search_entry") else ""
        category = self.tpl_category_var.get().strip() if hasattr(self, "tpl_category_var") else "全部分类"
        support_label = self.tpl_support_var.get().strip() if hasattr(self, "tpl_support_var") else "全部支持级别"
        support_map = {
            "全部支持级别": "",
            "可直接使用": "direct",
            "可用（需调整）": "assisted",
            "规划中": "planned",
        }
        support_filter = support_map.get(support_label, "")

        rows: List[Dict[str, Any]] = []
        for item in self.template_catalog:
            if category != "全部分类" and item.get("category") != category:
                continue
            if support_filter and item.get("support_level") != support_filter:
                continue
            if search:
                searchable = [str(item.get("name", "")), str(item.get("description", ""))] + [str(x) for x in item.get("tags", [])]
                if not any(search in text.lower() for text in searchable):
                    continue
            rows.append(item)

        for node in self.tree_templates.get_children():
            self.tree_templates.delete(node)
        for item in rows:
            self.tree_templates.insert(
                "",
                "end",
                iid=item["key"],
                values=(item["name"], item["category"], item.get("support_text", "")),
            )

        if rows:
            target = keep_key if keep_key and self.tree_templates.exists(keep_key) else rows[0]["key"]
            self.tree_templates.selection_set(target)
            self.tree_templates.focus(target)
            self.tree_templates.see(target)
            self._on_template_selected()
        else:
            self.last_selected_template_key = ""
            self.tpl_detail_title_var.set("没有匹配模板")
            self.tpl_detail_text.delete("1.0", "end")
            self.tpl_detail_text.insert("1.0", "请调整搜索条件或筛选项。")

    def _selected_template_key(self) -> str:
        if not hasattr(self, "tree_templates"):
            return ""
        selected = self.tree_templates.selection()
        if not selected:
            return ""
        return str(selected[0]).strip()

    def _on_template_selected(self, _event=None) -> None:
        key = self._selected_template_key()
        if not key:
            return
        item = scenario_templates.get_template_by_key(key)
        if not item:
            return
        should_reset_options = key != self.last_selected_template_key
        self.last_selected_template_key = key
        self.tpl_detail_title_var.set(f"{item['name']}（{item['support_text']}）")
        lines = [
            f"分类：{item['category']}",
            f"场景类型：{item['archetype']}",
            f"支持级别：{item['support_text']}",
            f"标签：{', '.join(item.get('tags', [])) or '无'}",
            "",
            item.get("description", ""),
            "",
            "说明：可直接“加载到问卷编辑器”后继续逐题修改。"
            " 对于“可用（需调整）/规划中”模板，系统会在 schema.meta 写入流程能力设计，便于后续扩展。"
        ]
        self.tpl_detail_text.delete("1.0", "end")
        self.tpl_detail_text.insert("1.0", "\n".join(lines))
        if should_reset_options:
            self._reset_template_center_options()

    def _reset_template_center_options(self) -> None:
        key = self._selected_template_key()
        if not key:
            return
        payload = scenario_templates.build_payload(key, options={})
        if not payload:
            return

        schema = payload.get("schema", {})
        meta = schema.get("meta", {}) if isinstance(schema, dict) else {}
        workflow = meta.get("workflow", {}) if isinstance(meta, dict) else {}

        self.tpl_title_override.delete(0, "end")
        self.tpl_title_override.insert(0, payload.get("title", ""))
        self.tpl_passcode.delete(0, "end")

        mode = str(payload.get("identity_mode", "realname"))
        self.tpl_identity_var.set(MODE_VALUE_TO_LABEL.get(mode, "实名"))
        auth_mode = str(payload.get("auth_mode", "open"))
        self.tpl_auth_var.set(AUTH_VALUE_TO_LABEL.get(auth_mode, "开放作答"))

        if payload.get("requires_roster") and self.roster_cache:
            rid = str(self.roster_cache[0]["id"])
            rname = str(self.roster_cache[0]["name"])
            self.tpl_roster_var.set(f"{rid} | {rname}")
        elif not payload.get("requires_roster"):
            self.tpl_roster_var.set("")

        self.tpl_allow_repeat_var.set(bool(payload.get("allow_repeat", False)))
        fields = payload.get("identity_fields", {}) if isinstance(payload.get("identity_fields"), dict) else {}
        self.tpl_allow_same_device_repeat_var.set(bool(fields.get("allow_same_device_repeat", False)))
        self.tpl_use_roster_loop_var.set(
            any(
                str(q.get("repeat_from", "")).strip() == ROSTER_REPEAT_TOKEN
                or str(q.get("repeat_from", "")).strip().startswith("__list__:")
                for q in schema.get("questions", [])
            )
        )
        self.tpl_waitlist_var.set(bool(workflow.get("waitlist_enabled", False)))
        self.tpl_approval_var.set(bool(workflow.get("approval_required", False)))
        self.tpl_first_come_var.set(bool(workflow.get("first_come_enabled", False)))
        self.tpl_allow_modify_var.set(bool(workflow.get("allow_modify", False)))
        self.tpl_auto_ranking_var.set(bool(workflow.get("auto_ranking", False)))

        self.tpl_max_select.delete(0, "end")
        self.tpl_max_select.insert(0, "2")
        self.tpl_rating_min.delete(0, "end")
        self.tpl_rating_min.insert(0, "1")
        self.tpl_rating_max.delete(0, "end")
        self.tpl_rating_max.insert(0, "10")
        self.tpl_submission_limit.delete(0, "end")
        self.tpl_submission_limit.insert(0, str(workflow.get("submission_limit", 0)))

    def _collect_template_center_options(self) -> Dict[str, Any]:
        options: Dict[str, Any] = {
            "title_override": self.tpl_title_override.get().strip(),
            "passcode": self.tpl_passcode.get().strip(),
            "identity_mode": MODE_LABEL_TO_VALUE.get(self.tpl_identity_var.get().strip(), "realname"),
            "auth_mode": AUTH_LABEL_TO_VALUE.get(self.tpl_auth_var.get().strip(), "open"),
            "allow_repeat": bool(self.tpl_allow_repeat_var.get()),
            "allow_same_device_repeat": bool(self.tpl_allow_same_device_repeat_var.get()),
            "use_roster_loop": bool(self.tpl_use_roster_loop_var.get()),
            "waitlist_enabled": bool(self.tpl_waitlist_var.get()),
            "approval_required": bool(self.tpl_approval_var.get()),
            "first_come_enabled": bool(self.tpl_first_come_var.get()),
            "allow_modify": bool(self.tpl_allow_modify_var.get()),
            "auto_ranking": bool(self.tpl_auto_ranking_var.get()),
        }
        max_select = self.tpl_max_select.get().strip()
        rating_min = self.tpl_rating_min.get().strip()
        rating_max = self.tpl_rating_max.get().strip()
        submission_limit = self.tpl_submission_limit.get().strip()
        if max_select:
            options["max_select"] = max_select
        if rating_min:
            options["rating_min"] = rating_min
        if rating_max:
            options["rating_max"] = rating_max
        if submission_limit:
            options["submission_limit"] = submission_limit
        return options

    def _resolve_roster_for_payload(self, payload: Dict[str, Any], roster_combo_value: str) -> str:
        roster_id = self._extract_qid(roster_combo_value)
        if not payload.get("requires_roster"):
            if str(payload.get("auth_mode", "open")) == "open":
                return ""
            return roster_id

        if not roster_id and self.roster_cache:
            roster_id = str(self.roster_cache[0]["id"])
        if roster_id:
            return roster_id

        if not messagebox.askyesno("缺少名单", "该模板需要绑定名单。是否先自动创建示例名单？", parent=self):
            return ""
        return self._quick_create_demo_roster(show_message=False)

    def _clone_template_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        intro = str(schema.get("intro", "")).strip() if isinstance(schema, dict) else ""
        raw_meta = schema.get("meta", {}) if isinstance(schema, dict) else {}
        meta = raw_meta if isinstance(raw_meta, dict) else {}
        questions = schema.get("questions", []) if isinstance(schema, dict) else []
        return {
            "intro": intro,
            "meta": json.loads(json.dumps(meta, ensure_ascii=False)),
            "questions": self._clone_template_questions(questions if isinstance(questions, list) else []),
        }

    def _load_payload_to_editor(self, payload: Dict[str, Any], roster_id: str = "") -> None:
        schema = payload.get("schema", {}) if isinstance(payload.get("schema"), dict) else {}
        self.editing_qid = None
        self.entry_title.delete(0, "end")
        self.entry_title.insert(0, payload.get("title", ""))
        self.entry_desc.delete("1.0", "end")
        self.entry_desc.insert("1.0", payload.get("description", ""))
        self.entry_intro.delete("1.0", "end")
        self.entry_intro.insert("1.0", schema.get("intro", payload.get("intro", "")))
        self.entry_passcode.delete(0, "end")
        self.entry_passcode.insert(0, payload.get("passcode", ""))

        mode = str(payload.get("identity_mode", "realname"))
        self.mode_var.set(MODE_VALUE_TO_LABEL.get(mode, "实名"))
        self.repeat_var.set(bool(payload.get("allow_repeat", False)))
        auth_mode = str(payload.get("auth_mode", "open"))
        self.auth_mode_var.set(AUTH_VALUE_TO_LABEL.get(auth_mode, "开放作答"))

        if roster_id:
            roster_match = next((f"{r['id']} | {r['name']}" for r in self.roster_cache if str(r["id"]) == roster_id), roster_id)
            self.auth_roster_var.set(roster_match)
        else:
            self.auth_roster_var.set("")

        fields = payload.get("identity_fields", {})
        self.same_device_repeat_var.set(bool(fields.get("allow_same_device_repeat", False)))
        self.collect_name_var.set(bool(fields.get("collect_name", False)))
        self.collect_code_var.set(bool(fields.get("collect_code", False)))
        self.name_required_var.set(bool(fields.get("name_required", False)))
        self.code_required_var.set(bool(fields.get("code_required", False)))

        self.draft_schema_meta = schema.get("meta", {}) if isinstance(schema.get("meta", {}), dict) else {}
        self.draft_questions = self._clone_template_questions(schema.get("questions", []))
        self._refresh_draft_tree()
        self._cancel_question_edit()
        self._check_draft_configuration(show_success=False)

    def _create_questionnaire_from_payload(self, payload: Dict[str, Any], roster_id: str = "") -> str:
        schema = payload.get("schema", {}) if isinstance(payload.get("schema"), dict) else {}
        built_schema = self._clone_template_schema(schema)
        qid = self.service.create_questionnaire(
            title=payload.get("title", "").strip(),
            description=payload.get("description", "").strip(),
            identity_mode=payload.get("identity_mode", "realname"),
            allow_repeat=bool(payload.get("allow_repeat", False)),
            passcode=payload.get("passcode", ""),
            schema=built_schema,
            questionnaire_id=None,
            auth_mode=payload.get("auth_mode", "open"),
            auth_roster_id=roster_id,
            identity_fields=payload.get("identity_fields", {}),
        )
        self.service.db.set_questionnaire_status(qid, "active")
        return qid

    def _remap_rule_question_ids(self, rule: Any, mapping: Dict[str, str]) -> Any:
        if not isinstance(rule, dict):
            return rule
        if "all" in rule and isinstance(rule["all"], list):
            return {"all": [self._remap_rule_question_ids(item, mapping) for item in rule["all"]]}
        if "any" in rule and isinstance(rule["any"], list):
            return {"any": [self._remap_rule_question_ids(item, mapping) for item in rule["any"]]}
        if "not" in rule:
            return {"not": self._remap_rule_question_ids(rule.get("not"), mapping)}
        updated = dict(rule)
        qid = str(updated.get("question_id", "")).strip()
        if qid in mapping:
            updated["question_id"] = mapping[qid]
        return updated

    def _collect_rule_question_ids(self, rule: Any) -> List[str]:
        if not isinstance(rule, dict):
            return []
        refs: List[str] = []
        if "all" in rule and isinstance(rule["all"], list):
            for item in rule["all"]:
                refs.extend(self._collect_rule_question_ids(item))
            return refs
        if "any" in rule and isinstance(rule["any"], list):
            for item in rule["any"]:
                refs.extend(self._collect_rule_question_ids(item))
            return refs
        if "not" in rule:
            refs.extend(self._collect_rule_question_ids(rule.get("not")))
            return refs
        qid = str(rule.get("question_id", "")).strip()
        if qid:
            refs.append(qid)
        return refs

    def _clone_template_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        mapping: Dict[str, str] = {}
        cloned: List[Dict[str, Any]] = []
        for q in questions:
            item = dict(q)
            old_id = str(item.get("id", "")).strip() or make_question_id()
            new_id = make_question_id()
            mapping[old_id] = new_id
            item["id"] = new_id
            cloned.append(item)

        for item in cloned:
            repeat_from = str(item.get("repeat_from", "")).strip()
            if repeat_from in mapping:
                item["repeat_from"] = mapping[repeat_from]
            item["visible_if"] = self._remap_rule_question_ids(item.get("visible_if"), mapping)
            item["required_if"] = self._remap_rule_question_ids(item.get("required_if"), mapping)
        return cloned

    def _apply_selected_template(self) -> None:
        if self.design_logic_disabled:
            self._notify_design_disabled()
            return
        template_name = self.template_var.get().strip()
        if template_name == TEMPLATE_PLACEHOLDER:
            messagebox.showwarning("提示", "请先选择一个模板。", parent=self)
            return
        payload = self._template_payload(template_name)
        if not payload:
            messagebox.showerror("失败", "模板不存在。", parent=self)
            return
        roster_id = self._resolve_roster_for_payload(payload, self.auth_roster_var.get())
        if payload.get("requires_roster") and not roster_id:
            return
        if hasattr(self, "tpl_roster_var") and roster_id:
            roster_match = next((f"{r['id']} | {r['name']}" for r in self.roster_cache if str(r["id"]) == roster_id), roster_id)
            self.tpl_roster_var.set(roster_match)
        self._load_payload_to_editor(payload, roster_id=roster_id)
        messagebox.showinfo("模板已套用", "模板内容已写入编辑器，请检查后保存。", parent=self)

    def _apply_template_center_to_editor(self) -> None:
        if self.design_logic_disabled:
            self._notify_design_disabled()
            return
        key = self._selected_template_key()
        if not key:
            messagebox.showwarning("提示", "请先在左侧选择模板。", parent=self)
            return
        payload = scenario_templates.build_payload(key, options=self._collect_template_center_options())
        if not payload:
            messagebox.showerror("失败", "模板生成失败。", parent=self)
            return
        fields = payload.get("identity_fields", {}) if isinstance(payload.get("identity_fields"), dict) else {}
        fields["allow_same_device_repeat"] = bool(self.tpl_allow_same_device_repeat_var.get())
        payload["identity_fields"] = fields
        roster_id = self._resolve_roster_for_payload(payload, self.tpl_roster_var.get())
        if payload.get("requires_roster") and not roster_id:
            return
        if roster_id:
            roster_match = next((f"{r['id']} | {r['name']}" for r in self.roster_cache if str(r["id"]) == roster_id), roster_id)
            self.tpl_roster_var.set(roster_match)
        self._load_payload_to_editor(payload, roster_id=roster_id)
        self._switch_tab("问卷管理")
        messagebox.showinfo("已加载", "模板已加载到问卷编辑器，你可以继续逐题修改。", parent=self)

    def _create_from_template_center(self) -> None:
        if self.design_logic_disabled:
            self._notify_design_disabled()
            return
        key = self._selected_template_key()
        if not key:
            messagebox.showwarning("提示", "请先在左侧选择模板。", parent=self)
            return
        payload = scenario_templates.build_payload(key, options=self._collect_template_center_options())
        if not payload:
            messagebox.showerror("失败", "模板生成失败。", parent=self)
            return
        fields = payload.get("identity_fields", {}) if isinstance(payload.get("identity_fields"), dict) else {}
        fields["allow_same_device_repeat"] = bool(self.tpl_allow_same_device_repeat_var.get())
        payload["identity_fields"] = fields
        roster_id = self._resolve_roster_for_payload(payload, self.tpl_roster_var.get())
        if payload.get("requires_roster") and not roster_id:
            return
        try:
            qid = self._create_questionnaire_from_payload(payload, roster_id=roster_id)
            self._refresh_all()
            messagebox.showinfo("完成", f"已创建并启用问卷：{qid}", parent=self)
        except ServiceError as exc:
            messagebox.showerror("创建失败", str(exc), parent=self)

    def _check_draft_configuration(self, show_success: bool = True) -> None:
        errors: List[str] = []
        warnings: List[str] = []

        title = self.entry_title.get().strip()
        if not title:
            errors.append("问卷标题为空。")
        if not self.draft_questions:
            errors.append("至少需要 1 道题目。")

        auth_mode = AUTH_LABEL_TO_VALUE.get(self.auth_mode_var.get().strip(), "open")
        roster_id = self._extract_qid(self.auth_roster_var.get())
        if auth_mode != "open" and not roster_id:
            errors.append("身份验证方式为名单校验时，必须绑定名单。")

        qid_set: set[str] = set()
        duplicate_qid: set[str] = set()
        for q in self.draft_questions:
            qid = str(q.get("id", "")).strip()
            if not qid:
                errors.append("存在未设置题目 ID 的题目。")
                continue
            if qid in qid_set:
                duplicate_qid.add(qid)
            qid_set.add(qid)
        if duplicate_qid:
            errors.append(f"题目 ID 重复：{', '.join(sorted(duplicate_qid))}")

        for q in self.draft_questions:
            title_q = str(q.get("title", "")).strip()
            qid = str(q.get("id", "")).strip()
            qtype = str(q.get("type", "")).strip()
            if any(char.isspace() for char in qid):
                errors.append(f"{qid}：题目 ID 不能包含空白字符。")
            if not title_q:
                errors.append(f"{qid or '[无ID题目]'}：题目标题为空。")
            if qtype in {"single", "multi"}:
                options = q.get("options", [])
                if not isinstance(options, list) or len([x for x in options if str(x).strip()]) == 0:
                    errors.append(f"{qid}：单选/多选题必须设置选项。")
            if qtype == "rating":
                try:
                    min_v = int(q.get("min", 1))
                    max_v = int(q.get("max", 5))
                    if min_v >= max_v:
                        errors.append(f"{qid}：评分最小值必须小于最大值。")
                except Exception:
                    errors.append(f"{qid}：评分范围必须是整数。")

            repeat_from = str(q.get("repeat_from", "")).strip()
            repeat_filter = str(q.get("repeat_filter", "all")).strip().lower() or "all"
            if repeat_from:
                if repeat_from not in qid_set:
                    errors.append(f"{qid}：循环来源题目 ID 不存在（{repeat_from}）。")
                if repeat_filter not in {"all", "self", "peer"}:
                    warnings.append(f"{qid}：循环筛选值无效，建议改为 all/self/peer。")
            elif repeat_filter != "all":
                warnings.append(f"{qid}：设置了循环筛选但未配置循环来源。")

            visible_if = q.get("visible_if")
            for ref_qid in self._collect_rule_question_ids(visible_if):
                if ref_qid and ref_qid not in qid_set:
                    warnings.append(f"{qid}：显示条件引用了不存在的题目 ID（{ref_qid}）。")

            required_if = q.get("required_if")
            for ref_qid in self._collect_rule_question_ids(required_if):
                if ref_qid and ref_qid not in qid_set:
                    warnings.append(f"{qid}：必填条件引用了不存在的题目 ID（{ref_qid}）。")

        lines: List[str] = []
        if errors:
            lines.append("发现问题：")
            lines.extend([f"- {item}" for item in errors])
        if warnings:
            if lines:
                lines.append("")
            lines.append("提示项：")
            lines.extend([f"- {item}" for item in warnings])
        if not errors and not warnings:
            lines.append("配置体检通过：未发现明显问题。")

        if errors:
            messagebox.showerror("配置体检", "\n".join(lines), parent=self)
        elif warnings:
            messagebox.showwarning("配置体检", "\n".join(lines), parent=self)
        elif show_success:
            messagebox.showinfo("配置体检", "\n".join(lines), parent=self)

    def _quick_create_demo_roster(self, show_message: bool = True) -> str:
        try:
            demo_name = f"示例名单{len(self.roster_cache) + 1}"
            rid = self.service.create_roster(name=demo_name, description="系统自动创建的示例名单")
            sample_members = [
                ("张一", "S001", "K001"),
                ("李二", "S002", "K002"),
                ("王三", "S003", "K003"),
                ("赵四", "S004", "K004"),
                ("钱五", "S005", "K005"),
            ]
            for name, code, key in sample_members:
                self.service.add_roster_member(roster_id=rid, member_name=name, member_code=code, member_key=key)
            self._refresh_all()
            roster_match = next((f"{r['id']} | {r['name']}" for r in self.roster_cache if r["id"] == rid), rid)
            if hasattr(self, "auth_roster_var"):
                self.auth_roster_var.set(roster_match)
            if hasattr(self, "tpl_roster_var"):
                self.tpl_roster_var.set(roster_match)
            if show_message:
                messagebox.showinfo("完成", f"已创建示例名单：{rid}", parent=self)
            return rid
        except ServiceError as exc:
            messagebox.showerror("创建失败", str(exc), parent=self)
            return ""

    def _quick_create_template_questionnaire(self, template_name: str) -> None:
        if self.design_logic_disabled and not self.use_new_board_designer:
            self._notify_design_disabled()
            return
        payload = self._template_payload(template_name)
        if not payload:
            messagebox.showerror("失败", "模板不存在。", parent=self)
            return
        try:
            roster_id = self._resolve_roster_for_payload(payload, "")
            if payload.get("requires_roster") and not roster_id:
                return
            qid = self._create_questionnaire_from_payload(payload, roster_id=roster_id)
            self._refresh_all()
            messagebox.showinfo("完成", f"已创建并启用问卷：{qid}", parent=self)
        except ServiceError as exc:
            messagebox.showerror("创建失败", str(exc), parent=self)

    def _refresh_guide_status(self) -> None:
        if not hasattr(self, "guide_status_text"):
            return
        summary = self.service.summary_cards()
        items = self.service.list_questionnaires(active_only=False)
        active_count = len([q for q in items if q.get("status") == "active"])

        def mark(ok: bool) -> str:
            return "已完成" if ok else "未完成"

        step1 = summary.get("rosters", 0) > 0
        step2 = summary.get("questionnaires", 0) > 0
        step3 = active_count > 0
        step4 = self.server.is_running()
        step5 = summary.get("submissions", 0) > 0

        lines = [
            f"步骤1 建名单：{mark(step1)}",
            f"步骤2 建问卷：{mark(step2)}",
            f"步骤3 启用问卷：{mark(step3)}",
            f"步骤4 启动局域网服务：{mark(step4)}",
            f"步骤5 收到票据并统计：{mark(step5)}",
            "",
            f"当前数据：名单 {summary.get('rosters', 0)} 个，问卷 {summary.get('questionnaires', 0)} 个，票据 {summary.get('submissions', 0)} 条",
        ]

        if not step1:
            lines.append("下一步建议：先在“名单管理”导入或创建名单。")
        elif not step2:
            lines.append("下一步建议：去“问卷管理”套用模板并保存。")
        elif not step3:
            lines.append("下一步建议：在“问卷管理”把问卷状态设为“启用”。")
        elif not step4:
            lines.append("下一步建议：去“局域网服务”点击“启动服务”。")
        elif not step5:
            lines.append("下一步建议：先完成一次提交，再到“票据与SQL”查看结果。")
        else:
            lines.append("流程已跑通：你可以继续导出 CSV 或创建备份。")

        self.guide_status_text.delete("1.0", "end")
        self.guide_status_text.insert("1.0", "\n".join(lines))

    def _refresh_all(self) -> None:
        self._refresh_roster_list()
        if hasattr(self, "tree_board_questionnaires"):
            self._refresh_board_questionnaire_list()
        self._refresh_questionnaire_list()
        self._refresh_template_catalog()
        self._refresh_dashboard()
        self._refresh_server_info()
        self._refresh_q_menus()
        self._refresh_submissions()
        self._refresh_guide_status()

    def _refresh_dashboard(self) -> None:
        summary = self.service.summary_cards()
        self.card_q_count.configure(text=str(summary["questionnaires"]))
        self.card_s_count.configure(text=str(summary["submissions"]))
        self.card_server.configure(text="运行中" if self.server.is_running() else "已停止")
        self.card_rosters.configure(text=str(summary.get("rosters", 0)))

        lines = [
            f"数据目录: {self.service.paths.data_dir}",
            f"票据目录: {summary['votes_dir']}",
            f"导出目录: {self.service.paths.exports_dir}",
        ]
        self.dashboard_text.delete("1.0", "end")
        self.dashboard_text.insert("1.0", "\n".join(lines))

        srv = self.server.info()
        if srv:
            self.top_status.configure(text=f"服务运行中: {srv.base_url}")
        else:
            self.top_status.configure(text="服务未启动")

    def _selected_roster_id(self) -> str:
        selected = self.tree_rosters.selection()
        if not selected:
            return ""
        return str(self.tree_rosters.item(selected[0], "values")[0]).strip()

    def _refresh_roster_list(self) -> None:
        self.roster_cache = self.service.list_rosters()
        if hasattr(self, "tree_rosters"):
            for item in self.tree_rosters.get_children():
                self.tree_rosters.delete(item)
            for roster in self.roster_cache:
                self.tree_rosters.insert(
                    "",
                    "end",
                    values=(roster["id"], roster["name"], roster.get("member_count", 0)),
                )
        self._refresh_roster_members()

    def _refresh_roster_members(self) -> None:
        if not hasattr(self, "tree_roster_members"):
            return
        roster_id = self._selected_roster_id()
        for item in self.tree_roster_members.get_children():
            self.tree_roster_members.delete(item)
        if not roster_id:
            self.roster_title.configure(text="成员列表")
            self._configure_roster_member_tree([], [])
            return
        roster_columns = self.service.get_roster_columns(roster_id)
        self._configure_roster_member_tree(roster_columns, [])
        members = self.service.list_roster_members(roster_id, limit=100000)
        self._configure_roster_member_tree(roster_columns, members)
        dynamic_keys = [str(col.get("key", "")).strip() for col in roster_columns if str(col.get("key", "")).strip()]
        for member in members:
            values = member.get("values", {}) if isinstance(member.get("values", {}), dict) else {}
            row_values: List[Any] = [
                member["id"],
                member.get("member_key", ""),
            ]
            for key in dynamic_keys:
                row_values.append(values.get(key, ""))
            self.tree_roster_members.insert(
                "",
                "end",
                values=tuple(row_values),
            )
        self.roster_title.configure(text=f"成员列表 - {roster_id}（{len(members)}）")

    def _configure_roster_member_tree(self, roster_columns: List[Dict[str, Any]], members: List[Dict[str, Any]]) -> None:
        if not hasattr(self, "tree_roster_members"):
            return
        cols: List[str] = ["id", "key"]
        headers: Dict[str, str] = {"id": "行ID", "key": "唯一标识"}
        for idx, col in enumerate(roster_columns, start=1):
            key = str(col.get("key", "")).strip()
            if not key:
                continue
            col_id = f"c_{idx}_{key}"
            cols.append(col_id)
            headers[col_id] = str(col.get("label", "")).strip() or key
        self.tree_roster_members.configure(columns=tuple(cols), show="headings")
        for col_id in cols:
            self.tree_roster_members.heading(col_id, text=headers.get(col_id, col_id))
            if col_id == "id":
                self.tree_roster_members.column(col_id, width=60, anchor="w")
            elif col_id == "key":
                self.tree_roster_members.column(col_id, width=140, anchor="w")
            else:
                self.tree_roster_members.column(col_id, width=140, anchor="w")

    def _on_roster_selected(self, _event=None) -> None:
        self._refresh_roster_members()
        self._refresh_q_menus()

    def _create_roster(self) -> None:
        name = simpledialog.askstring("新建名单", "请输入名单名称：", parent=self)
        if name is None:
            return
        name = name.strip()
        if not name:
            messagebox.showwarning("提示", "名单名称不能为空。", parent=self)
            return
        desc = simpledialog.askstring("名单说明", "请输入名单说明（可选）：", parent=self) or ""
        raw_cols = simpledialog.askstring(
            "字段设置",
            "请输入名单字段（逗号分隔）。示例：昵称,姓名,部门,班级\n留空将使用默认字段：姓名,编号",
            parent=self,
        )
        if raw_cols is None:
            return
        columns = self._parse_roster_columns_text(raw_cols)
        try:
            rid = self.service.create_roster(name=name, description=desc, columns=columns)
            self._refresh_roster_list()
            messagebox.showinfo("成功", f"名单已创建：{rid}", parent=self)
        except ServiceError as exc:
            messagebox.showerror("失败", str(exc), parent=self)

    def _rename_selected_roster(self) -> None:
        roster_id = self._selected_roster_id()
        if not roster_id:
            messagebox.showwarning("提示", "请先选择名单。", parent=self)
            return
        roster = next((item for item in self.roster_cache if str(item.get("id", "")).strip() == roster_id), None)
        old_name = str(roster.get("name", "")).strip() if isinstance(roster, dict) else ""
        new_name = simpledialog.askstring(
            "重命名名单",
            "请输入新的名单名称：",
            initialvalue=old_name,
            parent=self,
        )
        if new_name is None:
            return
        new_name = new_name.strip()
        if not new_name:
            messagebox.showwarning("提示", "名单名称不能为空。", parent=self)
            return
        try:
            self.service.rename_roster(roster_id, new_name)
            self._refresh_all()
            messagebox.showinfo("成功", f"名单已重命名为：{new_name}", parent=self)
        except ServiceError as exc:
            messagebox.showerror("失败", str(exc), parent=self)

    def _copy_selected_roster(self) -> None:
        roster_id = self._selected_roster_id()
        if not roster_id:
            messagebox.showwarning("提示", "请先选择名单。", parent=self)
            return
        roster = next((item for item in self.roster_cache if str(item.get("id", "")).strip() == roster_id), None)
        old_name = str(roster.get("name", "")).strip() if isinstance(roster, dict) else roster_id
        new_name = simpledialog.askstring(
            "复制名单",
            "请输入副本名称：",
            initialvalue=f"{old_name}（副本）",
            parent=self,
        )
        if new_name is None:
            return
        new_name = new_name.strip()
        if not new_name:
            messagebox.showwarning("提示", "副本名称不能为空。", parent=self)
            return
        try:
            new_id = self.service.copy_roster(roster_id, new_name=new_name)
            self._refresh_all()
            messagebox.showinfo("成功", f"名单复制完成：{new_id}", parent=self)
        except ServiceError as exc:
            messagebox.showerror("复制失败", str(exc), parent=self)

    def _delete_selected_roster(self) -> None:
        roster_id = self._selected_roster_id()
        if not roster_id:
            messagebox.showwarning("提示", "请先选择名单。", parent=self)
            return
        roster = next((item for item in self.roster_cache if str(item.get("id", "")).strip() == roster_id), None)
        roster_name = str(roster.get("name", "")).strip() if isinstance(roster, dict) else roster_id
        if not messagebox.askyesno("确认删除", f"确定删除名单“{roster_name}”吗？", parent=self):
            return
        try:
            self.service.delete_roster(roster_id)
            self._refresh_all()
            messagebox.showinfo("完成", "名单已删除。", parent=self)
        except ServiceError as exc:
            messagebox.showerror("删除失败", str(exc), parent=self)

    def _parse_roster_columns_text(self, raw: str) -> List[Dict[str, Any]]:
        tokens = [x.strip() for x in str(raw or "").replace("，", ",").split(",") if x.strip()]
        if not tokens:
            tokens = ["姓名", "编号"]
        columns: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for idx, label in enumerate(tokens, start=1):
            key = label.replace(" ", "_").replace("-", "_")
            if key in {"姓名", "name"}:
                key = "member_name"
            elif key in {"编号", "工号", "学号", "code"}:
                key = "member_code"
            if key in seen:
                key = f"{key}_{idx}"
            seen.add(key)
            columns.append({"key": key, "label": label, "is_key": False})
        code_idx = next((i for i, col in enumerate(columns) if str(col.get("key", "")).strip() == "member_code"), 0)
        if columns:
            columns[code_idx]["is_key"] = True
        return columns

    def _configure_roster_columns(self) -> None:
        roster_id = self._selected_roster_id()
        if not roster_id:
            messagebox.showwarning("提示", "请先选择名单。", parent=self)
            return
        columns = self.service.get_roster_columns(roster_id)
        default_text = ",".join([str(col.get("label", "")).strip() or str(col.get("key", "")).strip() for col in columns])
        raw = simpledialog.askstring(
            "配置名单字段",
            "请输入新的字段名称（逗号分隔）。\n注意：已有数据会按“字段键”保留，重命名只改显示名。",
            initialvalue=default_text,
            parent=self,
        )
        if raw is None:
            return
        new_columns = self._parse_roster_columns_text(raw)
        try:
            self.service.set_roster_columns(roster_id, new_columns)
            self._refresh_roster_members()
            messagebox.showinfo("完成", "名单字段已更新。", parent=self)
        except ServiceError as exc:
            messagebox.showerror("失败", str(exc), parent=self)

    def _import_roster(self) -> None:
        roster_id = self._selected_roster_id()
        if not roster_id:
            messagebox.showwarning("提示", "请先选择名单。", parent=self)
            return
        path = filedialog.askopenfilename(
            parent=self,
            title="导入名单文件",
            filetypes=[("CSV/Excel 文件", "*.csv;*.xlsx;*.xlsm"), ("CSV 文件", "*.csv"), ("Excel 文件", "*.xlsx;*.xlsm")],
            initialdir=str(self.service.paths.root),
        )
        if not path:
            return
        replace = messagebox.askyesno("覆盖导入", "是否清空该名单原有成员后再导入？", parent=self)
        try:
            result = self.service.import_roster_file(roster_id, Path(path), replace_all=replace)
            self._refresh_roster_members()
            messagebox.showinfo(
                "导入完成",
                f"新增 {result['inserted']} 条，更新 {result['updated']} 条。",
                parent=self,
            )
        except ServiceError as exc:
            messagebox.showerror("导入失败", str(exc), parent=self)

    def _add_roster_member_manual(self) -> None:
        roster_id = self._selected_roster_id()
        if not roster_id:
            messagebox.showwarning("提示", "请先选择名单。", parent=self)
            return
        columns = self.service.get_roster_columns(roster_id)
        values: Dict[str, Any] = {}
        for col in columns:
            key = str(col.get("key", "")).strip()
            label = str(col.get("label", "")).strip() or key
            if not key:
                continue
            value = simpledialog.askstring("新增成员", f"{label}（可留空）：", parent=self)
            if value is None:
                return
            values[key] = str(value).strip()
        key = simpledialog.askstring("新增成员", "唯一标识（可选，留空自动生成）：", parent=self) or ""
        name = str(values.get("member_name", "")).strip()
        code = str(values.get("member_code", "")).strip()
        if not any(str(v).strip() for v in values.values()) and not key.strip():
            messagebox.showwarning("提示", "请至少填写一个字段值。", parent=self)
            return
        tags = simpledialog.askstring("新增成员", "标签（可选）：", parent=self) or ""
        try:
            self.service.add_roster_member(
                roster_id=roster_id,
                member_name=name,
                member_code=code,
                member_key=key,
                tags=tags,
                member_values=values,
            )
            self._refresh_roster_members()
        except ServiceError as exc:
            messagebox.showerror("失败", str(exc), parent=self)

    def _remove_selected_roster_member(self) -> None:
        selected = self.tree_roster_members.selection()
        if not selected:
            return
        member_id = int(self.tree_roster_members.item(selected[0], "values")[0])
        if not messagebox.askyesno("确认删除", f"确定删除成员行 ID {member_id} 吗？", parent=self):
            return
        self.service.remove_roster_member(member_id)
        self._refresh_roster_members()

    def _refresh_questionnaire_list(self) -> None:
        if not hasattr(self, "tree_questionnaires"):
            return
        items = self.service.list_questionnaires(active_only=False)
        for i in self.tree_questionnaires.get_children():
            self.tree_questionnaires.delete(i)
        for q in items:
            self.tree_questionnaires.insert(
                "",
                "end",
                values=(q["id"], q["title"], _pretty_mode(q["identity_mode"]), q["status"]),
            )

    def _refresh_q_menus(self) -> None:
        items = self.service.list_questionnaires(active_only=False)
        values = [f"{q['id']} | {q['title']}" for q in items] or [""]
        self.server_q_menu.configure(values=values)
        self.offline_q_menu.configure(values=values)
        self.stats_q_menu.configure(values=values, command=self._on_stats_q_menu_change)
        if values and values[0] != "":
            if not self.server_q_var.get():
                self.server_q_var.set(values[0])
            if not self.offline_q_var.get():
                self.offline_q_var.set(values[0])
            if not self.stats_q_var.get():
                self.stats_q_var.set(values[0])

        roster_values = [f"{r['id']} | {r['name']}" for r in self.roster_cache] or [""]
        if hasattr(self, "auth_roster_menu"):
            self.auth_roster_menu.configure(values=roster_values)
            if roster_values and roster_values[0] != "" and not self.auth_roster_var.get():
                self.auth_roster_var.set(roster_values[0])
        if hasattr(self, "board_auth_roster_menu"):
            self.board_auth_roster_menu.configure(values=roster_values)
            if roster_values and roster_values[0] != "" and not self.board_auth_roster_var.get():
                self.board_auth_roster_var.set(roster_values[0])
            self._board_sync_auto_lists(re_render=False)
        if hasattr(self, "tpl_roster_menu"):
            self.tpl_roster_menu.configure(values=roster_values)
            if roster_values and roster_values[0] != "" and not self.tpl_roster_var.get():
                self.tpl_roster_var.set(roster_values[0])
        self._update_server_qr()
        if hasattr(self, "tree_submissions"):
            self._refresh_submissions()

    def _on_server_q_menu_change(self, _value: str) -> None:
        self._refresh_server_info()

    def _on_stats_q_menu_change(self, _value: str) -> None:
        self._refresh_submissions()

    def _on_identity_mode_changed(self, mode_label: str) -> None:
        mode = MODE_LABEL_TO_VALUE.get(mode_label, "realname")
        self.collect_name_var.set(True)
        self.collect_code_var.set(True)
        self.name_required_var.set(mode in {"realname", "semi"})
        self.code_required_var.set(mode in {"realname", "semi"})

    def _save_questionnaire(self) -> None:
        if self.design_logic_disabled:
            self._notify_design_disabled()
            return
        title = self.entry_title.get().strip()
        passcode = self.entry_passcode.get().strip()
        desc = self.entry_desc.get("1.0", "end").strip()
        intro = self.entry_intro.get("1.0", "end").strip()
        mode_label = self.mode_var.get().strip()
        mode = MODE_LABEL_TO_VALUE.get(mode_label, "realname")
        allow_repeat = self.repeat_var.get()
        auth_mode = AUTH_LABEL_TO_VALUE.get(self.auth_mode_var.get().strip(), "open")
        auth_roster_id = self._extract_qid(self.auth_roster_var.get())
        identity_fields = {
            "collect_name": bool(self.collect_name_var.get()),
            "collect_code": bool(self.collect_code_var.get()),
            "name_required": bool(self.name_required_var.get()),
            "code_required": bool(self.code_required_var.get()),
            "allow_same_device_repeat": bool(self.same_device_repeat_var.get()),
        }
        if auth_mode != "open" and not auth_roster_id:
            messagebox.showwarning("提示", "名单校验模式下必须绑定名单。", parent=self)
            return
        if not title:
            messagebox.showwarning("提示", "请填写问卷标题。", parent=self)
            return
        if not self.draft_questions:
            messagebox.showwarning("提示", "请至少添加 1 道题目。", parent=self)
            return

        schema = {
            "intro": intro,
            "meta": self.draft_schema_meta if isinstance(self.draft_schema_meta, dict) else {},
            "questions": self.draft_questions,
        }
        try:
            qid = self.service.create_questionnaire(
                title=title,
                description=desc,
                identity_mode=mode,
                allow_repeat=allow_repeat,
                passcode=passcode,
                schema=schema,
                questionnaire_id=self.editing_qid,
                auth_mode=auth_mode,
                auth_roster_id=auth_roster_id,
                identity_fields=identity_fields,
            )
            messagebox.showinfo("成功", f"问卷已保存：{qid}", parent=self)
            self._refresh_all()
            self.editing_qid = qid
        except ServiceError as exc:
            messagebox.showerror("保存失败", str(exc), parent=self)

    def _selected_draft_question_id(self) -> str:
        selected = self.tree_draft_questions.selection()
        if not selected:
            return ""
        return str(self.tree_draft_questions.item(selected[0], "values")[0]).strip()

    def _find_draft_question_index(self, qid: str) -> int:
        for idx, item in enumerate(self.draft_questions):
            if str(item.get("id", "")).strip() == qid:
                return idx
        return -1

    def _select_draft_question(self, qid: str) -> None:
        for node in self.tree_draft_questions.get_children():
            values = self.tree_draft_questions.item(node, "values")
            if values and str(values[0]).strip() == qid:
                self.tree_draft_questions.selection_set(node)
                self.tree_draft_questions.focus(node)
                self.tree_draft_questions.see(node)
                break

    def _remap_question_references(self, old_qid: str, new_qid: str) -> None:
        if not old_qid or old_qid == new_qid:
            return
        mapping = {old_qid: new_qid}
        for question in self.draft_questions:
            repeat_from = str(question.get("repeat_from", "")).strip()
            if repeat_from == old_qid:
                question["repeat_from"] = new_qid
            question["visible_if"] = self._remap_rule_question_ids(question.get("visible_if"), mapping)
            question["required_if"] = self._remap_rule_question_ids(question.get("required_if"), mapping)

    def _set_question_edit_mode(self, qid: Optional[str]) -> None:
        self.editing_draft_qid = qid
        if qid:
            self.btn_add_question.configure(text="保存题目修改")
            self.btn_cancel_edit_question.configure(state="normal")
            self.q_edit_mode_var.set(f"当前编辑：{qid}")
            return
        self.btn_add_question.configure(text="新增题目")
        self.btn_cancel_edit_question.configure(state="disabled")
        self.q_edit_mode_var.set("当前为新增模式。")

    def _reset_question_form(self) -> None:
        self.entry_q_title.delete(0, "end")
        self.entry_q_id.delete(0, "end")
        self.entry_q_options.delete("1.0", "end")
        self.entry_visible_qid.delete(0, "end")
        self.entry_visible_value.delete(0, "end")
        self.entry_repeat_from.delete(0, "end")
        self.repeat_filter_var.set("全部循环项")
        self.entry_required_qid.delete(0, "end")
        self.entry_required_value.delete(0, "end")
        self.entry_logic_hint.delete(0, "end")
        self.entry_logic_hint.insert(0, "如：当上题=参加时必填")
        self.entry_max_select.delete(0, "end")
        self.entry_max_select.insert(0, "1")
        self.entry_rating_min.delete(0, "end")
        self.entry_rating_min.insert(0, "1")
        self.entry_rating_max.delete(0, "end")
        self.entry_rating_max.insert(0, "5")
        self.q_type.set("单选")
        self.q_required.set(True)
        self._set_question_edit_mode(None)

    def _build_question_from_form(self, existing_qid: Optional[str] = None) -> Optional[Dict[str, Any]]:
        title = self.entry_q_title.get().strip()
        custom_qid = self.entry_q_id.get().strip()
        q_type = QTYPE_LABEL_TO_VALUE.get(self.q_type.get(), "single")
        required = bool(self.q_required.get())
        options_text = self.entry_q_options.get("1.0", "end").strip()
        options = [line.strip() for line in options_text.splitlines() if line.strip()]
        visible_qid = self.entry_visible_qid.get().strip()
        visible_value = self.entry_visible_value.get().strip()
        required_qid = self.entry_required_qid.get().strip()
        required_value = self.entry_required_value.get().strip()
        repeat_from_raw = self.entry_repeat_from.get().strip()
        repeat_from = repeat_from_raw
        repeat_filter_label = self.repeat_filter_var.get().strip()
        repeat_filter = REPEAT_FILTER_LABEL_TO_VALUE.get(repeat_filter_label, "all")

        if not title:
            messagebox.showwarning("提示", "请填写题目标题。", parent=self)
            return None
        if custom_qid and any(char.isspace() for char in custom_qid):
            messagebox.showwarning("提示", "题目ID不能包含空白字符。", parent=self)
            return None
        if (visible_qid and not visible_value) or (visible_value and not visible_qid):
            messagebox.showwarning("提示", "显示条件需要同时填写“题目ID”和“值”。", parent=self)
            return None
        if (required_qid and not required_value) or (required_value and not required_qid):
            messagebox.showwarning("提示", "必填条件需要同时填写“题目ID”和“值”。", parent=self)
            return None

        question: Dict[str, Any] = {
            "id": custom_qid or existing_qid or make_question_id(),
            "title": title,
            "type": q_type,
            "required": required,
        }
        if q_type in {"single", "multi"}:
            if not options:
                messagebox.showwarning("提示", "单选/多选题需要提供选项。", parent=self)
                return None
            question["options"] = options
        if q_type == "multi":
            try:
                question["max_select"] = max(1, int(self.entry_max_select.get().strip() or "1"))
            except ValueError:
                messagebox.showwarning("提示", "最多可选必须是整数。", parent=self)
                return None
        if q_type == "rating":
            try:
                min_v = int(self.entry_rating_min.get().strip() or "1")
                max_v = int(self.entry_rating_max.get().strip() or "5")
            except ValueError:
                messagebox.showwarning("提示", "评分范围必须是整数。", parent=self)
                return None
            if min_v >= max_v:
                messagebox.showwarning("提示", "评分最小值需小于最大值。", parent=self)
                return None
            question["min"] = min_v
            question["max"] = max_v

        if visible_qid and visible_value:
            question["visible_if"] = {"question_id": visible_qid, "equals": visible_value}
        if required_qid and required_value:
            question["required_if"] = {"question_id": required_qid, "equals": required_value}
        if repeat_from:
            question["repeat_from"] = repeat_from
            if repeat_filter != "all":
                question["repeat_filter"] = repeat_filter
        return question

    def _add_question(self) -> None:
        question = self._build_question_from_form(existing_qid=self.editing_draft_qid)
        if not question:
            return
        new_qid = str(question.get("id", "")).strip()
        if not new_qid:
            messagebox.showwarning("提示", "题目ID不能为空。", parent=self)
            return
        duplicate = any(
            str(item.get("id", "")).strip() == new_qid and str(item.get("id", "")).strip() != str(self.editing_draft_qid or "")
            for item in self.draft_questions
        )
        if duplicate:
            messagebox.showwarning("提示", f"题目ID重复：{new_qid}。请修改后重试。", parent=self)
            return

        if self.editing_draft_qid:
            old_qid = str(self.editing_draft_qid).strip()
            if old_qid and old_qid != new_qid:
                self._remap_question_references(old_qid, new_qid)
            replaced = False
            for idx, item in enumerate(self.draft_questions):
                if str(item.get("id", "")).strip() == old_qid:
                    self.draft_questions[idx] = question
                    replaced = True
                    break
            if not replaced:
                self.draft_questions.append(question)
        else:
            self.draft_questions.append(question)
        self._refresh_draft_tree()
        self._select_draft_question(new_qid)
        self._reset_question_form()

    def _edit_selected_question(self) -> None:
        qid = self._selected_draft_question_id()
        if not qid:
            messagebox.showwarning("提示", "请先选择题目。", parent=self)
            return
        target = next((q for q in self.draft_questions if str(q.get("id", "")).strip() == qid), None)
        if not target:
            return
        self.entry_q_title.delete(0, "end")
        self.entry_q_title.insert(0, str(target.get("title", "")))
        self.entry_q_id.delete(0, "end")
        self.entry_q_id.insert(0, str(target.get("id", "")))
        self.q_type.set(QTYPE_VALUE_TO_LABEL.get(str(target.get("type", "single")), "单选"))
        self.q_required.set(bool(target.get("required", False)))

        options = target.get("options", [])
        self.entry_q_options.delete("1.0", "end")
        if isinstance(options, list):
            self.entry_q_options.insert("1.0", "\n".join([str(x) for x in options]))

        visible_if = target.get("visible_if")
        self.entry_visible_qid.delete(0, "end")
        self.entry_visible_value.delete(0, "end")
        if isinstance(visible_if, dict):
            self.entry_visible_qid.insert(0, str(visible_if.get("question_id", "")))
            visible_val = visible_if.get("equals")
            if visible_val is None:
                visible_val = visible_if.get("value", "")
            self.entry_visible_value.insert(0, str(visible_val))

        required_if = target.get("required_if")
        self.entry_required_qid.delete(0, "end")
        self.entry_required_value.delete(0, "end")
        if isinstance(required_if, dict):
            self.entry_required_qid.insert(0, str(required_if.get("question_id", "")))
            required_val = required_if.get("equals")
            if required_val is None:
                required_val = required_if.get("value", "")
            self.entry_required_value.insert(0, str(required_val))

        repeat_from = str(target.get("repeat_from", "")).strip()
        self.entry_repeat_from.delete(0, "end")
        if repeat_from:
            self.entry_repeat_from.insert(0, repeat_from)
        repeat_filter = str(target.get("repeat_filter", "all")).strip().lower() or "all"
        self.repeat_filter_var.set(REPEAT_FILTER_VALUE_TO_LABEL.get(repeat_filter, "全部循环项"))

        self.entry_max_select.delete(0, "end")
        self.entry_max_select.insert(0, str(target.get("max_select", 1)))
        self.entry_rating_min.delete(0, "end")
        self.entry_rating_min.insert(0, str(target.get("min", 1)))
        self.entry_rating_max.delete(0, "end")
        self.entry_rating_max.insert(0, str(target.get("max", 5)))
        self.entry_logic_hint.delete(0, "end")
        self.entry_logic_hint.insert(0, "编辑中：修改后点击“保存题目修改”")
        self._set_question_edit_mode(qid)

    def _cancel_question_edit(self) -> None:
        self._reset_question_form()

    def _duplicate_selected_question(self) -> None:
        qid = self._selected_draft_question_id()
        if not qid:
            messagebox.showwarning("提示", "请先选择题目。", parent=self)
            return
        idx = self._find_draft_question_index(qid)
        if idx < 0:
            return
        clone = json.loads(json.dumps(self.draft_questions[idx], ensure_ascii=False))
        old_qid = str(clone.get("id", "")).strip()
        new_qid = make_question_id()
        clone["id"] = new_qid
        if str(clone.get("repeat_from", "")).strip() == old_qid:
            clone["repeat_from"] = new_qid
        clone["visible_if"] = self._remap_rule_question_ids(clone.get("visible_if"), {old_qid: new_qid})
        clone["required_if"] = self._remap_rule_question_ids(clone.get("required_if"), {old_qid: new_qid})
        self.draft_questions.insert(idx + 1, clone)
        self._refresh_draft_tree()
        self._select_draft_question(new_qid)

    def _move_question_up(self) -> None:
        qid = self._selected_draft_question_id()
        if not qid:
            return
        idx = self._find_draft_question_index(qid)
        if idx <= 0:
            return
        self.draft_questions[idx - 1], self.draft_questions[idx] = self.draft_questions[idx], self.draft_questions[idx - 1]
        self._refresh_draft_tree()
        self._select_draft_question(qid)

    def _move_question_down(self) -> None:
        qid = self._selected_draft_question_id()
        if not qid:
            return
        idx = self._find_draft_question_index(qid)
        if idx < 0 or idx >= len(self.draft_questions) - 1:
            return
        self.draft_questions[idx + 1], self.draft_questions[idx] = self.draft_questions[idx], self.draft_questions[idx + 1]
        self._refresh_draft_tree()
        self._select_draft_question(qid)

    def _find_question_references(self, target_qid: str) -> List[str]:
        refs: List[str] = []
        for question in self.draft_questions:
            qid = str(question.get("id", "")).strip()
            if qid == target_qid:
                continue
            if str(question.get("repeat_from", "")).strip() == target_qid:
                refs.append(f"{qid}：循环来源")
            if target_qid in self._collect_rule_question_ids(question.get("visible_if")):
                refs.append(f"{qid}：显示条件")
            if target_qid in self._collect_rule_question_ids(question.get("required_if")):
                refs.append(f"{qid}：必填条件")
        return refs

    def _refresh_draft_tree(self) -> None:
        for i in self.tree_draft_questions.get_children():
            self.tree_draft_questions.delete(i)
        for q in self.draft_questions:
            self.tree_draft_questions.insert(
                "",
                "end",
                values=(q["id"], q["title"], QTYPE_VALUE_TO_LABEL.get(q["type"], q["type"]), "是" if q.get("required") else "否"),
            )

    def _remove_question(self) -> None:
        qid = self._selected_draft_question_id()
        if not qid:
            return
        refs = self._find_question_references(qid)
        if refs:
            ref_preview = "\n".join([f"- {item}" for item in refs[:8]])
            suffix = "\n- ..." if len(refs) > 8 else ""
            if not messagebox.askyesno(
                "删除确认",
                f"该题被其他题目引用：\n{ref_preview}{suffix}\n\n仍要删除吗？删除后请重新做“配置体检”。",
                parent=self,
            ):
                return
        self.draft_questions = [q for q in self.draft_questions if q["id"] != qid]
        if self.editing_draft_qid == qid:
            self._cancel_question_edit()
        self._refresh_draft_tree()

    def _clear_editor(self) -> None:
        self.editing_qid = None
        self.entry_title.delete(0, "end")
        self.entry_passcode.delete(0, "end")
        self.entry_desc.delete("1.0", "end")
        self.entry_intro.delete("1.0", "end")
        self.mode_var.set("实名")
        self.repeat_var.set(False)
        self.same_device_repeat_var.set(False)
        self.auth_mode_var.set("开放作答")
        self.auth_roster_var.set("")
        self.collect_name_var.set(False)
        self.collect_code_var.set(False)
        self.name_required_var.set(False)
        self.code_required_var.set(False)
        if hasattr(self, "template_var"):
            self.template_var.set(TEMPLATE_PLACEHOLDER)
        self.draft_schema_meta = {}
        self.draft_questions = []
        self._refresh_draft_tree()
        self._cancel_question_edit()

    def _selected_questionnaire_id(self) -> str:
        if not hasattr(self, "tree_questionnaires"):
            return ""
        selected = self.tree_questionnaires.selection()
        if not selected:
            return ""
        return self.tree_questionnaires.item(selected[0], "values")[0]

    def _load_selected_questionnaire(self) -> None:
        if self.design_logic_disabled:
            self._notify_design_disabled()
            return
        qid = self._selected_questionnaire_id()
        if not qid:
            messagebox.showwarning("提示", "请先在左侧列表选择问卷。", parent=self)
            return
        q = self.service.get_questionnaire(qid)
        if not q:
            return
        self.editing_qid = qid
        self.entry_title.delete(0, "end")
        self.entry_title.insert(0, q["title"])
        self.entry_desc.delete("1.0", "end")
        self.entry_desc.insert("1.0", q.get("description", ""))
        self.entry_intro.delete("1.0", "end")
        self.entry_intro.insert("1.0", q.get("schema", {}).get("intro", ""))
        self.mode_var.set(MODE_VALUE_TO_LABEL.get(q.get("identity_mode", "realname"), "实名"))
        self.repeat_var.set(bool(q.get("allow_repeat")))
        self.auth_mode_var.set(AUTH_VALUE_TO_LABEL.get(q.get("auth_mode", "open"), "开放作答"))
        roster_id = str(q.get("auth_roster_id", "")).strip()
        if roster_id:
            roster_match = next((f"{r['id']} | {r['name']}" for r in self.roster_cache if r["id"] == roster_id), roster_id)
            self.auth_roster_var.set(roster_match)
        else:
            self.auth_roster_var.set("")
        fields = q.get("identity_fields", {})
        self.same_device_repeat_var.set(bool(fields.get("allow_same_device_repeat", False)))
        self.collect_name_var.set(bool(fields.get("collect_name", False)))
        self.collect_code_var.set(bool(fields.get("collect_code", False)))
        self.name_required_var.set(bool(fields.get("name_required", False)))
        self.code_required_var.set(bool(fields.get("code_required", False)))
        self.entry_passcode.delete(0, "end")
        if hasattr(self, "template_var"):
            self.template_var.set(TEMPLATE_PLACEHOLDER)
        schema = q.get("schema", {}) if isinstance(q.get("schema"), dict) else {}
        raw_meta = schema.get("meta", {})
        self.draft_schema_meta = raw_meta if isinstance(raw_meta, dict) else {}
        self.draft_questions = json.loads(json.dumps(schema.get("questions", []), ensure_ascii=False))
        self._refresh_draft_tree()
        self._cancel_question_edit()
        messagebox.showinfo("提示", f"已载入问卷 {qid}，修改后点击保存。", parent=self)

    def _set_selected_status(self, status: str) -> None:
        qid = self._selected_questionnaire_id()
        if not qid:
            messagebox.showwarning("提示", "请先选择问卷。", parent=self)
            return
        self.service.db.set_questionnaire_status(qid, status)
        self._refresh_all()

    def _rename_selected_questionnaire(self) -> None:
        qid = self._selected_questionnaire_id()
        if not qid:
            messagebox.showwarning("提示", "请先选择问卷。", parent=self)
            return
        q = self.service.get_questionnaire(qid)
        if not q:
            messagebox.showerror("失败", "问卷不存在。", parent=self)
            return
        old_title = str(q.get("title", "")).strip()
        new_title = simpledialog.askstring(
            "重命名问卷",
            "请输入新的问卷标题：",
            initialvalue=old_title,
            parent=self,
        )
        if new_title is None:
            return
        new_title = new_title.strip()
        if not new_title:
            messagebox.showwarning("提示", "问卷标题不能为空。", parent=self)
            return
        try:
            self.service.rename_questionnaire(qid, new_title)
            self._refresh_all()
            messagebox.showinfo("成功", f"问卷已重命名为：{new_title}", parent=self)
        except ServiceError as exc:
            messagebox.showerror("失败", str(exc), parent=self)

    def _copy_selected_questionnaire(self) -> None:
        qid = self._selected_questionnaire_id()
        if not qid:
            messagebox.showwarning("提示", "请先选择问卷。", parent=self)
            return
        q = self.service.get_questionnaire(qid)
        if not q:
            messagebox.showerror("失败", "问卷不存在。", parent=self)
            return
        old_title = str(q.get("title", "")).strip() or qid
        new_title = simpledialog.askstring(
            "复制问卷",
            "请输入副本标题：",
            initialvalue=f"{old_title}（副本）",
            parent=self,
        )
        if new_title is None:
            return
        new_title = new_title.strip()
        if not new_title:
            messagebox.showwarning("提示", "副本标题不能为空。", parent=self)
            return
        try:
            new_qid = self.service.copy_questionnaire(qid, new_title=new_title)
            self._refresh_all()
            messagebox.showinfo("成功", f"问卷复制完成：{new_qid}", parent=self)
        except ServiceError as exc:
            messagebox.showerror("复制失败", str(exc), parent=self)

    def _delete_selected_questionnaire(self) -> None:
        qid = self._selected_questionnaire_id()
        if not qid:
            messagebox.showwarning("提示", "请先选择问卷。", parent=self)
            return
        q = self.service.get_questionnaire(qid)
        if not q:
            messagebox.showerror("失败", "问卷不存在。", parent=self)
            return
        submissions = self.service.list_submissions(questionnaire_id=qid)
        title = str(q.get("title", "")).strip() or qid
        msg = f"确定删除问卷“{title}”吗？\n将同时删除 {len(submissions)} 份票据记录。"
        if not messagebox.askyesno("确认删除", msg, parent=self):
            return
        try:
            self.service.delete_questionnaire(qid)
            if self.editing_qid == qid:
                self._clear_editor()
            self._refresh_all()
            messagebox.showinfo("完成", "问卷已删除。", parent=self)
        except ServiceError as exc:
            messagebox.showerror("删除失败", str(exc), parent=self)

    def _start_server(self) -> None:
        host = self.entry_host.get().strip() or DEFAULT_HOST
        try:
            port = int(self.entry_port.get().strip() or str(DEFAULT_PORT))
        except ValueError:
            messagebox.showwarning("提示", "端口必须是整数。", parent=self)
            return
        try:
            self.server.start(host=host, port=port)
            self._refresh_server_info()
            self._refresh_dashboard()
            messagebox.showinfo("成功", "局域网服务已启动。", parent=self)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("启动失败", str(exc), parent=self)

    def _stop_server(self) -> None:
        self.server.stop()
        self._refresh_server_info()
        self._refresh_dashboard()

    def _current_server_link(self) -> str:
        info = self.server.info()
        if not info:
            return ""
        selected = self._extract_qid(self.server_q_var.get())
        if selected:
            return f"{info.base_url}/q/{selected}"
        return f"{info.base_url}/"

    def _update_server_qr(self) -> None:
        link = self._current_server_link()
        self.server_link_var.set(link)
        if not link:
            self.server_qr_image = None
            self.server_qr_label.configure(image=None, text="启动服务后显示二维码")
            return
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(link)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        self.server_qr_image = ctk.CTkImage(light_image=image, dark_image=image, size=(220, 220))
        self.server_qr_label.configure(image=self.server_qr_image, text="")

    def _copy_server_link(self) -> None:
        link = self.server_link_var.get().strip()
        if not link:
            messagebox.showwarning("提示", "当前没有可复制的访问链接。", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(link)
        self.update()
        messagebox.showinfo("已复制", "问卷链接已复制到剪贴板。", parent=self)

    def _refresh_server_info(self) -> None:
        self.server_info.delete("1.0", "end")
        info = self.server.info()
        if not info:
            self.server_info.insert("1.0", "服务未启动。\n点击“启动服务”后同局域网设备可访问问卷。")
            self._update_server_qr()
            return
        selected = self._extract_qid(self.server_q_var.get())
        lines = [
            "服务状态: 运行中",
            f"监听地址: {info.host}:{info.port}",
            f"局域网地址: {info.base_url}",
            f"入口页: {info.base_url}/",
        ]
        if selected:
            lines.append(f"默认问卷: {info.base_url}/q/{selected}")
        self.server_info.insert("1.0", "\n".join(lines))
        self._update_server_qr()

    def _open_server_home(self) -> None:
        info = self.server.info()
        if not info:
            return
        webbrowser.open(f"{info.base_url}/")

    def _open_server_questionnaire(self) -> None:
        info = self.server.info()
        if not info:
            return
        qid = self._extract_qid(self.server_q_var.get())
        if not qid:
            return
        webbrowser.open(f"{info.base_url}/q/{qid}")

    def _choose_offline_path(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            title="选择离线问卷导出文件",
            defaultextension=".html",
            filetypes=[("HTML 文件", "*.html")],
            initialdir=str(self.service.paths.exports_dir),
        )
        if path:
            self.offline_path_var.set(path)

    def _export_offline(self) -> None:
        qid = self._extract_qid(self.offline_q_var.get())
        if not qid:
            messagebox.showwarning("提示", "请选择问卷。", parent=self)
            return
        q = self.service.get_questionnaire(qid)
        if not q:
            messagebox.showerror("失败", "问卷不存在。", parent=self)
            return
        schema_questions = q.get("schema", {}).get("questions", []) if isinstance(q.get("schema"), dict) else []
        needs_roster_data = q.get("auth_mode", "open") != "open"
        if needs_roster_data:
            roster_id = str(q.get("auth_roster_id", "")).strip()
            if not roster_id:
                messagebox.showerror("失败", "该问卷需要名单数据（名单校验），但未绑定名单。", parent=self)
                return
            q = dict(q)
            q["offline_auth_members"] = self.service.list_roster_members(roster_id, limit=100000)
        out = Path(self.offline_path_var.get().strip())
        if out.suffix.lower() != ".html":
            out = out.with_suffix(".html")
        try:
            output = export_offline_html(q, self.service.crypto.public_key_spki_b64(), out)
            self.offline_log.insert("end", f"导出成功: {output}\n")
            self.offline_log.see("end")
            messagebox.showinfo("成功", f"离线问卷已导出:\n{output}", parent=self)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("导出失败", str(exc), parent=self)

    def _open_export_dir(self) -> None:
        webbrowser.open(str(self.service.paths.exports_dir))

    def _extract_qid(self, combo_value: str) -> str:
        value = combo_value.strip()
        if not value:
            return ""
        if "|" in value:
            return value.split("|", 1)[0].strip()
        return value

    def _selected_submission_id(self) -> str:
        if not hasattr(self, "tree_submissions"):
            return ""
        selected = self.tree_submissions.selection()
        if not selected:
            return ""
        values = self.tree_submissions.item(selected[0], "values")
        if not values:
            return ""
        return str(values[0]).strip()

    def _refresh_submissions(self) -> None:
        qid = self._extract_qid(self.stats_q_var.get())
        for i in self.tree_submissions.get_children():
            self.tree_submissions.delete(i)
        self.sql_result_sets = []
        self.sql_active_result_index = 0
        self._render_sql_console("SQL> 等待执行查询...\n")
        if not qid:
            self._refresh_sql_schema_text("")
            self._refresh_sql_view_menu("")
            self._set_sql_status("请先选择问卷。")
            return
        rows = self.service.list_submissions(questionnaire_id=qid)
        for row in rows:
            name = row.get("respondent_name") or "-"
            self.tree_submissions.insert(
                "",
                "end",
                values=(row["id"], row["submitted_at"], row["source"], name),
            )
        self._refresh_sql_schema_text(qid)
        self._refresh_sql_view_menu(qid)
        self._set_sql_status(f"已加载 {len(rows)} 份票据，可执行 SQL 查询。")

    def _refresh_sql_workbench(self) -> None:
        self._refresh_submissions()

    def _refresh_sql_schema_text(self, questionnaire_id: str) -> None:
        if not hasattr(self, "sql_schema_text"):
            return
        self.sql_schema_text.configure(state="normal")
        self.sql_schema_text.delete("1.0", "end")
        qid = str(questionnaire_id or "").strip()
        if not qid:
            self.sql_schema_text.insert("1.0", "未选择问卷。")
            self.sql_schema_text.configure(state="disabled")
            return
        try:
            model = self.service.query_model_schema(qid)
        except ServiceError as exc:
            self.sql_schema_text.insert("1.0", f"读取查询模型失败：{exc}")
            self.sql_schema_text.configure(state="disabled")
            return
        lines: List[str] = []
        lines.append(f"问卷：{model.get('questionnaire_title', '')} ({qid})")
        lines.append(f"当前票据数：{model.get('submission_count', 0)}")
        lines.append("")
        lines.append("可查询表结构：")
        for table in model.get("table_defs", []):
            if not isinstance(table, dict):
                continue
            lines.append(f"- {table.get('name', '')}：{table.get('desc', '')}")
            for col in table.get("columns", []):
                if not isinstance(col, (list, tuple)) or len(col) < 3:
                    continue
                lines.append(f"    {col[0]} ({col[1]})  # {col[2]}")
        live_rule_tables = model.get("live_rule_table_defs", [])
        if isinstance(live_rule_tables, list) and live_rule_tables:
            lines.append("")
            lines.append("联合规则可用项目（字段级）：")
            for table in live_rule_tables:
                if not isinstance(table, dict):
                    continue
                lines.append(f"- {table.get('name', '')}：{table.get('desc', '')}")
                for col in table.get("columns", []):
                    if not isinstance(col, (list, tuple)) or len(col) < 3:
                        continue
                    lines.append(f"    {col[0]} ({col[1]})  # {col[2]}")
            suffix = str(model.get("live_rule_suffix", "")).strip()
            if suffix:
                lines.append("")
                lines.append(f"联合规则自动限制：{suffix}")
        identity_cols = model.get("identity_dynamic_columns", [])
        if isinstance(identity_cols, list) and identity_cols:
            lines.append("")
            lines.append("自动身份列（可直接在 SQL 中使用）：")
            for item in identity_cols:
                if not isinstance(item, dict):
                    continue
                col_name = str(item.get("column_name", "")).strip()
                label = str(item.get("field_label", "")).strip()
                key = str(item.get("field_key", "")).strip()
                if not col_name:
                    continue
                lines.append(f"  {col_name}  # 来自字段 {label or key}")
        lines.append("")
        lines.append("提示：支持多条 SELECT 语句，使用分号 ; 分隔，执行后会按 SQL[1]/SQL[2] 显示。")
        lines.append("")
        lines.append("示例 SQL：")
        for sql in model.get("examples", []):
            lines.append(f"  {sql}")
        live_rule_examples = model.get("live_rule_examples", [])
        if isinstance(live_rule_examples, list) and live_rule_examples:
            lines.append("")
            lines.append("联合规则示例 SQL（仅 1 条 SELECT，建议返回单值数字）：")
            for sql in live_rule_examples:
                lines.append(f"  {sql}")
        self.sql_schema_text.insert("1.0", "\n".join(lines))
        self.sql_schema_text.configure(state="disabled")

    def _refresh_sql_view_menu(self, questionnaire_id: str) -> None:
        if not hasattr(self, "sql_view_menu"):
            return
        qid = str(questionnaire_id or "").strip()
        self.sql_view_cache = self.service.list_sql_views(qid) if qid else []
        values = [str(item.get("name", "")).strip() for item in self.sql_view_cache if str(item.get("name", "")).strip()]
        if not values:
            values = [""]
        self.sql_view_menu.configure(values=values)
        if values[0]:
            self.sql_view_var.set(values[0])
        else:
            self.sql_view_var.set("")

    def _selected_sql_view(self) -> Optional[Dict[str, Any]]:
        name = str(self.sql_view_var.get() or "").strip()
        if not name:
            return None
        for item in self.sql_view_cache:
            if str(item.get("name", "")).strip() == name:
                return item
        return None

    def _load_sql_view_to_editor(self) -> None:
        item = self._selected_sql_view()
        if not item:
            messagebox.showwarning("提示", "请先选择SQL模板。", parent=self)
            return
        sql_text = str(item.get("sql_text", "")).strip()
        self.sql_editor.delete("1.0", "end")
        self.sql_editor.insert("1.0", sql_text)
        self._set_sql_status(f"已加载模板：{item.get('name', '')}")

    def _save_sql_view(self) -> None:
        qid = self._extract_qid(self.stats_q_var.get())
        if not qid:
            messagebox.showwarning("提示", "请先选择问卷。", parent=self)
            return
        sql_text = self.sql_editor.get("1.0", "end").strip()
        default_name = str(self.sql_view_var.get() or "").strip()
        name = simpledialog.askstring("保存SQL模板", "请输入模板名称：", initialvalue=default_name, parent=self)
        if name is None:
            return
        name = name.strip()
        if not name:
            messagebox.showwarning("提示", "模板名称不能为空。", parent=self)
            return
        try:
            self.service.save_sql_view(qid, name, sql_text)
            self._refresh_sql_view_menu(qid)
            self.sql_view_var.set(name)
            self._set_sql_status(f"SQL模板已保存：{name}")
        except ServiceError as exc:
            messagebox.showerror("保存失败", str(exc), parent=self)

    def _remove_sql_view(self) -> None:
        item = self._selected_sql_view()
        if not item:
            messagebox.showwarning("提示", "请先选择要删除的模板。", parent=self)
            return
        view_id = int(item.get("id", 0) or 0)
        name = str(item.get("name", "")).strip()
        if not view_id:
            messagebox.showwarning("提示", "模板不存在。", parent=self)
            return
        if not messagebox.askyesno("确认删除", f"确定删除SQL模板“{name}”吗？", parent=self):
            return
        try:
            self.service.remove_sql_view(view_id)
            qid = self._extract_qid(self.stats_q_var.get())
            self._refresh_sql_view_menu(qid)
            self._set_sql_status(f"已删除模板：{name}")
        except ServiceError as exc:
            messagebox.showerror("删除失败", str(exc), parent=self)

    def _render_sql_console(self, text: str) -> None:
        if not hasattr(self, "sql_console_text"):
            return
        self.sql_console_text.delete("1.0", "end")
        self.sql_console_text.insert("1.0", text)
        self.sql_console_text.see("1.0")

    def _format_result_set_table(self, columns: List[str], rows: List[List[Any]], max_col_width: int = 28) -> List[str]:
        if not columns:
            return ["(无列)"]
        widths: List[int] = []
        for idx, col in enumerate(columns):
            width = len(str(col))
            for row in rows:
                val = ""
                if idx < len(row) and row[idx] is not None:
                    val = str(row[idx])
                if len(val) > width:
                    width = len(val)
            widths.append(min(max(4, width), max_col_width))

        def cut(text: str, n: int) -> str:
            if len(text) <= n:
                return text
            if n <= 1:
                return text[:n]
            return text[: n - 1] + "…"

        sep = "+" + "+".join(["-" * (w + 2) for w in widths]) + "+"
        head_cells = [f" {cut(str(col), widths[i]).ljust(widths[i])} " for i, col in enumerate(columns)]
        out = [sep, "|" + "|".join(head_cells) + "|", sep]
        for row in rows:
            cells: List[str] = []
            for i, _col in enumerate(columns):
                val = ""
                if i < len(row) and row[i] is not None:
                    val = str(row[i])
                cells.append(f" {cut(val, widths[i]).ljust(widths[i])} ")
            out.append("|" + "|".join(cells) + "|")
        out.append(sep)
        return out

    def _set_sql_status(self, text: str) -> None:
        if hasattr(self, "sql_status_var"):
            self.sql_status_var.set(text)

    def _run_sql_query(self) -> None:
        qid = self._extract_qid(self.stats_q_var.get())
        if not qid:
            messagebox.showwarning("提示", "请先选择问卷。", parent=self)
            return
        sql_text = self.sql_editor.get("1.0", "end").strip()
        try:
            result = self.service.execute_sql_query(qid, sql_text, row_limit=5000)
        except ServiceError as exc:
            messagebox.showerror("查询失败", str(exc), parent=self)
            self._set_sql_status("SQL执行失败。")
            self._render_sql_console(f"SQL> 执行失败\n{exc}\n")
            return

        results = result.get("results", [])
        self.sql_result_sets = results if isinstance(results, list) else []
        self.sql_active_result_index = 0
        console_lines: List[str] = []
        for item in self.sql_result_sets:
            if not isinstance(item, dict):
                continue
            idx = int(item.get("index", 0) or 0)
            sql_line = str(item.get("sql", "")).strip()
            columns = item.get("columns", [])
            rows = item.get("rows", [])
            row_count = int(item.get("row_count", 0) or 0)
            truncated = bool(item.get("truncated", False))
            console_lines.append(f"SQL[{idx}]> {sql_line}")
            console_lines.append(f"-- {row_count} 行" + ("（已截断到 5000 行）" if truncated else ""))
            console_lines.extend(self._format_result_set_table(columns if isinstance(columns, list) else [], rows if isinstance(rows, list) else []))
            console_lines.append("")
        if not console_lines:
            console_lines = ["SQL> 未返回结果。"]
        self._render_sql_console("\n".join(console_lines))
        self._set_sql_status(f"查询完成：{len(self.sql_result_sets)} 组结果。")

    def _export_sql_result_csv(self) -> None:
        if not self.sql_result_sets:
            messagebox.showwarning("提示", "请先执行SQL查询并得到结果。", parent=self)
            return
        if len(self.sql_result_sets) > 1:
            pick = simpledialog.askinteger(
                "选择结果集",
                f"当前有 {len(self.sql_result_sets)} 组结果，请输入要导出的序号（1-{len(self.sql_result_sets)}）：",
                parent=self,
                minvalue=1,
                maxvalue=len(self.sql_result_sets),
            )
            if pick is None:
                return
            idx = int(pick) - 1
        else:
            idx = 0
        target = self.sql_result_sets[idx]
        columns = target.get("columns", []) if isinstance(target, dict) else []
        rows = target.get("rows", []) if isinstance(target, dict) else []
        if not columns:
            messagebox.showwarning("提示", "所选结果集没有列，无法导出。", parent=self)
            return
        qid = self._extract_qid(self.stats_q_var.get())
        default_file = self.service.paths.exports_dir / f"{qid or 'query'}_sql_result_{idx + 1}.csv"
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="导出查询结果 CSV",
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv")],
            initialfile=default_file.name,
            initialdir=str(self.service.paths.exports_dir),
        )
        if not file_path:
            return
        try:
            out = self.service.export_query_result_csv(
                columns=columns,
                rows=rows,
                output_file=Path(file_path),
            )
            self._set_sql_status(f"已导出查询结果：{out}")
            messagebox.showinfo("导出成功", f"已导出到:\n{out}", parent=self)
        except ServiceError as exc:
            messagebox.showerror("导出失败", str(exc), parent=self)

    def _import_votes(self) -> None:
        files = filedialog.askopenfilenames(
            parent=self,
            title="选择 .vote 票据文件",
            filetypes=[("Vote 文件", "*.vote")],
            initialdir=str(self.service.paths.root),
        )
        if not files:
            return
        ok_count = 0
        for p in files:
            ok, _msg = self.service.import_vote_file(Path(p))
            if ok:
                ok_count += 1
        self._refresh_submissions()
        self._refresh_dashboard()
        self._set_sql_status(f"归票完成：成功 {ok_count}，失败/跳过 {len(files) - ok_count}")
        messagebox.showinfo("导入完成", f"成功 {ok_count} 个，失败/跳过 {len(files) - ok_count} 个。", parent=self)

    def _reject_selected_submission(self) -> None:
        qid = self._extract_qid(self.stats_q_var.get())
        if not qid:
            messagebox.showwarning("提示", "请先选择问卷。", parent=self)
            return
        submission_id = self._selected_submission_id()
        if not submission_id:
            messagebox.showwarning("提示", "请先选择要驳回的票据。", parent=self)
            return
        if not messagebox.askyesno("确认驳回", f"确定驳回票据 {submission_id} 吗？", parent=self):
            return
        try:
            self.service.reject_submission(submission_id)
            self._refresh_submissions()
            self._refresh_dashboard()
            self._set_sql_status(f"票据已驳回：{submission_id}")
            messagebox.showinfo("完成", "票据已驳回。", parent=self)
        except ServiceError as exc:
            messagebox.showerror("驳回失败", str(exc), parent=self)

    def _show_payload_preview(self) -> None:
        qid = self._extract_qid(self.stats_q_var.get())
        if not qid:
            return
        try:
            payloads = self.service.decrypt_submission_payloads(qid)
        except ServiceError as exc:
            messagebox.showerror("读取失败", str(exc), parent=self)
            return
        preview = payloads[:3]
        win = ctk.CTkToplevel(self)
        win.title("原始票据预览（前3条）")
        win.geometry("900x560")
        txt = ctk.CTkTextbox(win)
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("1.0", json.dumps(preview, ensure_ascii=False, indent=2))
        txt.configure(state="disabled")

    def _change_password(self) -> None:
        old = self.old_pwd.get().strip()
        new = self.new_pwd.get().strip()
        new2 = self.new_pwd2.get().strip()
        if not old or not new or not new2:
            messagebox.showwarning("提示", "请完整输入旧密码和新密码。", parent=self)
            return
        if len(new) < 8:
            messagebox.showwarning("提示", "新密码至少 8 位。", parent=self)
            return
        if new != new2:
            messagebox.showwarning("提示", "两次新密码不一致。", parent=self)
            return
        try:
            self.service.change_admin_password(old, new)
            self.old_pwd.delete(0, "end")
            self.new_pwd.delete(0, "end")
            self.new_pwd2.delete(0, "end")
            messagebox.showinfo("成功", "管理员密码已更新。", parent=self)
        except ServiceError as exc:
            messagebox.showerror("失败", str(exc), parent=self)

    def _backup_data(self) -> None:
        default_file = self.service.paths.exports_dir / "votefree_backup.zip"
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="导出系统备份",
            defaultextension=".zip",
            filetypes=[("Zip 文件", "*.zip")],
            initialfile=default_file.name,
            initialdir=str(self.service.paths.exports_dir),
        )
        if not file_path:
            return
        try:
            output = self.service.create_backup(Path(file_path))
            messagebox.showinfo("备份完成", f"备份文件已生成：\n{output}", parent=self)
        except ServiceError as exc:
            messagebox.showerror("备份失败", str(exc), parent=self)

    def _refresh_runtime_kernel_controls(self) -> None:
        current = self.service.get_runtime_kernel()
        if hasattr(self, "runtime_kernel_var"):
            self.runtime_kernel_var.set(f"当前：{'tkinter 内核' if current == 'tkinter' else '网页内核'}")
        if hasattr(self, "switch_kernel_btn"):
            target = "web" if current == "tkinter" else "tkinter"
            target_text = "网页内核" if target == "web" else "tkinter 内核"
            self.switch_kernel_btn.configure(text=f"切换到 {target_text}")

    def _toggle_runtime_kernel(self) -> None:
        current = self.service.get_runtime_kernel()
        try:
            target = self.service.toggle_runtime_kernel(current)
            self._refresh_runtime_kernel_controls()
            target_text = "网页内核" if target == "web" else "tkinter 内核"
            messagebox.showinfo("已保存", f"默认内核已切换为：{target_text}\n重启程序后生效。", parent=self)
        except ServiceError as exc:
            messagebox.showerror("切换失败", str(exc), parent=self)

    def _on_close(self) -> None:
        if self.server.is_running():
            self.server.stop()
        self.destroy()


def run_gui(service: VoteFreeService) -> None:
    app = VoteFreeAdminApp(service)
    app.mainloop()

