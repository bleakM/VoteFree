from __future__ import annotations

import base64
import io
import json
import os
import sys
import tempfile
import threading
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import qrcode
from flask import Flask, jsonify, render_template, request
from werkzeug.datastructures import FileStorage
from werkzeug.serving import make_server

from .config import APP_NAME, DEFAULT_HOST, DEFAULT_PORT, AppPaths
from .offline_export import export_offline_html
from . import scenario_templates
from .server import SurveyServer
from .services import ServiceError, VoteFreeService


class _ServerThread(threading.Thread):
    def __init__(self, app: Flask):
        super().__init__(daemon=True)
        self._server = make_server("127.0.0.1", 0, app, threaded=True)
        self.port = int(self._server.socket.getsockname()[1])
        self._ctx = app.app_context()
        self._ctx.push()

    def run(self) -> None:
        self._server.serve_forever()

    def shutdown(self) -> None:
        self._server.shutdown()


@dataclass
class ShellInfo:
    port: int

    @property
    def admin_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/admin"


class WebAdminShell:
    def __init__(self, service: VoteFreeService, paths: AppPaths):
        self.service = service
        self.paths = paths
        self.survey_server = SurveyServer(service=service, paths=paths)
        self.default_questionnaire_id = ""
        self.last_sql_result: Dict[str, Any] = {"columns": [], "rows": []}

        self.app = self._build_app()
        self._thread: Optional[_ServerThread] = None
        self._info: Optional[ShellInfo] = None

    def _json_ok(self, **kwargs: Any):
        return jsonify({"ok": True, **kwargs})

    def _json_error(self, message: str, status_code: int = 400):
        return jsonify({"ok": False, "error": message}), status_code

    def _require_unlocked(self) -> None:
        if not self.service.crypto.unlocked:
            raise ServiceError("管理员密钥尚未解锁，请先输入管理员密码。")

    def _safe_int(self, raw: Any, default: int, min_value: int, max_value: int) -> int:
        try:
            val = int(str(raw).strip())
        except Exception:
            return default
        return max(min_value, min(max_value, val))

    def _resolve_output_path(self, raw_path: str, default_name: str) -> Path:
        text = str(raw_path or "").strip()
        if not text:
            return self.paths.exports_dir / default_name
        p = Path(text).expanduser()
        if not p.is_absolute():
            p = (self.paths.root / p).resolve()
        return p

    def _save_uploaded_file(self, upload: FileStorage, suffix: str = "") -> Path:
        real_suffix = suffix or Path(upload.filename or "").suffix or ".tmp"
        fd, temp_name = tempfile.mkstemp(prefix="votefree_upload_", suffix=real_suffix)
        os.close(fd)
        tmp_path = Path(temp_name)
        upload.save(str(tmp_path))
        return tmp_path

    def _open_path(self, path: Path) -> None:
        target = path.resolve()
        if sys.platform.startswith("win"):
            os.startfile(str(target))  # type: ignore[attr-defined]
            return
        webbrowser.open(target.as_uri())

    def _make_qr_data_uri(self, text: str) -> str:
        payload = str(text or "").strip()
        if not payload:
            return ""
        img = qrcode.make(payload)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"

    def _active_questionnaire_id(self) -> str:
        if self.default_questionnaire_id:
            if self.service.get_questionnaire(self.default_questionnaire_id):
                return self.default_questionnaire_id
        active = self.service.list_questionnaires(active_only=True)
        if not active:
            return ""
        self.default_questionnaire_id = str(active[0].get("id", "")).strip()
        return self.default_questionnaire_id

    def _server_payload(self) -> Dict[str, Any]:
        running = self.survey_server.is_running()
        info = self.survey_server.info()
        if not running or not info:
            return {
                "running": False,
                "host": "",
                "port": 0,
                "lan_ip": "",
                "base_url": "",
                "home_url": "",
                "default_questionnaire_id": self._active_questionnaire_id(),
                "default_url": "",
                "qr_data_uri": "",
            }
        qid = self._active_questionnaire_id()
        home_url = f"{info.base_url}/"
        default_url = f"{info.base_url}/q/{qid}" if qid else ""
        return {
            "running": True,
            "host": info.host,
            "port": info.port,
            "lan_ip": info.lan_ip,
            "base_url": info.base_url,
            "home_url": home_url,
            "default_questionnaire_id": qid,
            "default_url": default_url,
            "qr_data_uri": self._make_qr_data_uri(default_url or home_url),
        }

    def _guide_status_lines(self) -> List[str]:
        summary = self.service.summary_cards()
        q_count = int(summary.get("questionnaires", 0))
        r_count = int(summary.get("rosters", 0))
        s_count = int(summary.get("submissions", 0))
        return [
            f"1. 名单管理：{'已完成' if r_count > 0 else '未完成'}（当前 {r_count} 份）",
            f"2. 问卷管理：{'已完成' if q_count > 0 else '未完成'}（当前 {q_count} 份）",
            f"3. 局域网服务：{'已启动' if self.survey_server.is_running() else '未启动'}",
            f"4. 票据收集：{'已有数据' if s_count > 0 else '暂无票据'}（当前 {s_count} 条）",
            "5. SQL查询：进入“票据与SQL”页执行 SELECT 查询。",
        ]

    def _bootstrap_payload(self) -> Dict[str, Any]:
        questionnaires = self.service.list_questionnaires(active_only=False)
        rosters = self.service.list_rosters()
        templates = scenario_templates.list_templates()
        if not self.default_questionnaire_id and questionnaires:
            self.default_questionnaire_id = str(questionnaires[0].get("id", "")).strip()
        runtime_kernel = self.service.get_runtime_kernel()
        return {
            "summary": self.service.summary_cards(),
            "questionnaires": questionnaires,
            "rosters": rosters,
            "templates": templates,
            "guide_lines": self._guide_status_lines(),
            "exports_dir": str(self.paths.exports_dir),
            "default_host": DEFAULT_HOST,
            "default_port": DEFAULT_PORT,
            "server": self._server_payload(),
            "live_rule_suffix": self.service.live_rule_auto_filter_suffix(),
            "runtime_kernel": runtime_kernel,
            "runtime_kernel_next": "tkinter" if runtime_kernel == "web" else "web",
        }

    def _build_app(self) -> Flask:
        app = Flask(
            "VoteFreeAdminShell",
            template_folder=str(self.paths.templates_dir),
            static_folder=str(self.paths.static_dir),
        )
        app.secret_key = self.service.flask_secret()

        @app.get("/admin")
        def admin_page():
            return render_template("admin_shell.html", app_name=APP_NAME)

        @app.get("/api/admin/status")
        def admin_status():
            return self._json_ok(
                bootstrapped=self.service.is_bootstrapped(),
                unlocked=bool(self.service.crypto.unlocked),
            )

        @app.post("/api/admin/init")
        def admin_init():
            payload: Dict[str, Any] = request.get_json(silent=True) or {}
            password = str(payload.get("password", "")).strip()
            if len(password) < 8:
                return self._json_error("管理员密码至少 8 位。", 400)
            try:
                self.service.initialize_admin(password)
                self.service.unlock_admin(password)
                return self._json_ok()
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/unlock")
        def admin_unlock():
            payload: Dict[str, Any] = request.get_json(silent=True) or {}
            password = str(payload.get("password", "")).strip()
            if not password:
                return self._json_error("请输入管理员密码。", 400)
            try:
                self.service.unlock_admin(password)
                return self._json_ok()
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.get("/api/admin/bootstrap")
        def admin_bootstrap():
            try:
                self._require_unlocked()
                return self._json_ok(**self._bootstrap_payload())
            except ServiceError as exc:
                return self._json_error(str(exc), 403)

        @app.get("/api/admin/guide/status")
        def admin_guide_status():
            try:
                self._require_unlocked()
                return self._json_ok(lines=self._guide_status_lines())
            except ServiceError as exc:
                return self._json_error(str(exc), 403)

        @app.post("/api/admin/guide/quick-demo-roster")
        def admin_quick_demo_roster():
            try:
                self._require_unlocked()
                demo_name = f"示例名单{len(self.service.list_rosters()) + 1}"
                roster_id = self.service.create_roster(name=demo_name, description="系统自动创建的示例名单")
                for name, code, key in [
                    ("张一", "S001", "K001"),
                    ("李二", "S002", "K002"),
                    ("王三", "S003", "K003"),
                    ("赵四", "S004", "K004"),
                    ("钱五", "S005", "K005"),
                ]:
                    self.service.add_roster_member(roster_id=roster_id, member_name=name, member_code=code, member_key=key)
                return self._json_ok(roster_id=roster_id, rosters=self.service.list_rosters())
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/guide/quick-template-questionnaire")
        def admin_quick_template_questionnaire():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                template_name = str(payload.get("template_name", "")).strip()
                if not template_name:
                    return self._json_error("模板名称不能为空。", 400)
                tpl = scenario_templates.get_template_by_name(template_name)
                if not tpl:
                    return self._json_error("模板不存在。", 404)
                tpl_payload = scenario_templates.build_payload(str(tpl.get("key", "")).strip(), options={})
                if not isinstance(tpl_payload, dict):
                    return self._json_error("模板构建失败。", 400)

                roster_id = ""
                if bool(tpl_payload.get("requires_roster", False)):
                    rosters = self.service.list_rosters()
                    if rosters:
                        roster_id = str(rosters[0].get("id", "")).strip()
                    else:
                        demo_name = f"示例名单{len(rosters) + 1}"
                        roster_id = self.service.create_roster(name=demo_name, description="系统自动创建的示例名单")
                        for name, code, key in [
                            ("张一", "S001", "K001"),
                            ("李二", "S002", "K002"),
                            ("王三", "S003", "K003"),
                            ("赵四", "S004", "K004"),
                            ("钱五", "S005", "K005"),
                        ]:
                            self.service.add_roster_member(
                                roster_id=roster_id,
                                member_name=name,
                                member_code=code,
                                member_key=key,
                            )

                schema = tpl_payload.get("schema", {})
                if not isinstance(schema, dict):
                    schema = {}
                qid = self.service.create_questionnaire(
                    title=str(tpl_payload.get("title", "")).strip(),
                    description=str(tpl_payload.get("description", "")).strip(),
                    identity_mode=str(tpl_payload.get("identity_mode", "realname")).strip() or "realname",
                    allow_repeat=bool(tpl_payload.get("allow_repeat", False)),
                    passcode=str(tpl_payload.get("passcode", "")).strip(),
                    schema=json.loads(json.dumps(schema, ensure_ascii=False)),
                    questionnaire_id=None,
                    auth_mode=str(tpl_payload.get("auth_mode", "open")).strip() or "open",
                    auth_roster_id=roster_id,
                    identity_fields=tpl_payload.get("identity_fields", {}),
                )
                self.service.db.set_questionnaire_status(qid, "active")
                return self._json_ok(
                    questionnaire_id=qid,
                    questionnaires=self.service.list_questionnaires(active_only=False),
                    rosters=self.service.list_rosters(),
                )
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.get("/api/admin/templates")
        def admin_templates():
            try:
                self._require_unlocked()
                return self._json_ok(
                    templates=scenario_templates.list_templates(),
                    recommended=scenario_templates.RECOMMENDED_TEMPLATE_NAMES,
                )
            except ServiceError as exc:
                return self._json_error(str(exc), 403)

        @app.post("/api/admin/template/build")
        def admin_template_build():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                template_name = str(payload.get("template_name", "")).strip()
                if not template_name:
                    return self._json_error("模板名称不能为空。", 400)
                tpl = scenario_templates.get_template_by_name(template_name)
                if not tpl:
                    return self._json_error("模板不存在。", 404)
                options = payload.get("options", {})
                if not isinstance(options, dict):
                    options = {}
                tpl_payload = scenario_templates.build_payload(str(tpl.get("key", "")).strip(), options=options)
                if not isinstance(tpl_payload, dict):
                    return self._json_error("模板构建失败。", 400)
                roster_id = str(payload.get("roster_id", "")).strip() or str(tpl_payload.get("auth_roster_id", "")).strip()
                if bool(tpl_payload.get("requires_roster", False)) and not roster_id:
                    rosters = self.service.list_rosters()
                    if rosters:
                        roster_id = str(rosters[0].get("id", "")).strip()
                if roster_id:
                    tpl_payload["auth_roster_id"] = roster_id
                return self._json_ok(payload=tpl_payload, roster_id=roster_id)
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.get("/api/admin/summary")
        def admin_summary():
            try:
                self._require_unlocked()
                return self._json_ok(
                    summary=self.service.summary_cards(),
                    questionnaires=self.service.list_questionnaires(active_only=False),
                    rosters=self.service.list_rosters(),
                    server=self._server_payload(),
                )
            except ServiceError as exc:
                return self._json_error(str(exc), 403)

        @app.get("/api/admin/questionnaires")
        def admin_questionnaires():
            try:
                self._require_unlocked()
                return self._json_ok(questionnaires=self.service.list_questionnaires(active_only=False))
            except ServiceError as exc:
                return self._json_error(str(exc), 403)

        @app.post("/api/admin/questionnaire/status")
        def admin_questionnaire_status():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                questionnaire_id = str(payload.get("questionnaire_id", "")).strip()
                status = str(payload.get("status", "")).strip().lower()
                if not questionnaire_id:
                    return self._json_error("请先选择问卷。", 400)
                if status not in {"active", "paused"}:
                    return self._json_error("状态仅支持 active 或 paused。", 400)
                if not self.service.get_questionnaire(questionnaire_id):
                    return self._json_error("问卷不存在。", 404)
                self.service.db.set_questionnaire_status(questionnaire_id, status)
                return self._json_ok(questionnaires=self.service.list_questionnaires(active_only=False))
            except ServiceError as exc:
                return self._json_error(str(exc), 403)

        @app.post("/api/admin/questionnaire/rename")
        def admin_questionnaire_rename():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                questionnaire_id = str(payload.get("questionnaire_id", "")).strip()
                new_title = str(payload.get("new_title", "")).strip()
                self.service.rename_questionnaire(questionnaire_id, new_title)
                return self._json_ok(questionnaires=self.service.list_questionnaires(active_only=False))
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/questionnaire/copy")
        def admin_questionnaire_copy():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                questionnaire_id = str(payload.get("questionnaire_id", "")).strip()
                new_title = str(payload.get("new_title", "")).strip()
                new_id = self.service.copy_questionnaire(questionnaire_id, new_title=new_title)
                return self._json_ok(new_questionnaire_id=new_id, questionnaires=self.service.list_questionnaires(active_only=False))
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/questionnaire/delete")
        def admin_questionnaire_delete():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                questionnaire_id = str(payload.get("questionnaire_id", "")).strip()
                self.service.delete_questionnaire(questionnaire_id)
                return self._json_ok(questionnaires=self.service.list_questionnaires(active_only=False))
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.get("/api/admin/questionnaire/detail")
        def admin_questionnaire_detail():
            try:
                self._require_unlocked()
                questionnaire_id = str(request.args.get("questionnaire_id", "")).strip()
                if not questionnaire_id:
                    return self._json_error("请先选择问卷。", 400)
                questionnaire = self.service.get_questionnaire(questionnaire_id)
                if not questionnaire:
                    return self._json_error("问卷不存在。", 404)
                return self._json_ok(questionnaire=questionnaire)
            except ServiceError as exc:
                return self._json_error(str(exc), 403)

        @app.post("/api/admin/questionnaire/save")
        def admin_questionnaire_save():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                questionnaire_id = str(payload.get("questionnaire_id", "")).strip() or None
                title = str(payload.get("title", "")).strip()
                description = str(payload.get("description", "")).strip()
                intro = str(payload.get("intro", "")).strip()
                passcode = str(payload.get("passcode", "")).strip()
                allow_repeat = bool(payload.get("allow_repeat", False))
                auth_mode = str(payload.get("auth_mode", "open")).strip() or "open"
                auth_roster_id = str(payload.get("auth_roster_id", "")).strip()

                raw_collect = payload.get("collect_fields", [])
                collect_fields: List[Dict[str, str]] = []
                if isinstance(raw_collect, list):
                    for idx, item in enumerate(raw_collect, start=1):
                        if isinstance(item, dict):
                            key = str(item.get("key", "")).strip() or f"field_{idx}"
                            label = str(item.get("label", "")).strip() or key
                        else:
                            text = str(item or "").strip()
                            if not text:
                                continue
                            key = text.replace(" ", "_").replace("-", "_")
                            label = text
                        if key:
                            collect_fields.append({"key": key, "label": label})

                identity_fields = {
                    "collect_fields": collect_fields,
                    "allow_same_device_repeat": bool(payload.get("allow_same_device_repeat", False)),
                }

                schema = payload.get("schema", {})
                if not isinstance(schema, dict):
                    schema = {}
                schema["intro"] = intro

                qid = self.service.create_questionnaire(
                    title=title,
                    description=description,
                    identity_mode="realname",
                    allow_repeat=allow_repeat,
                    passcode=passcode,
                    schema=schema,
                    questionnaire_id=questionnaire_id,
                    auth_mode=auth_mode,
                    auth_roster_id=auth_roster_id,
                    identity_fields=identity_fields,
                )
                return self._json_ok(questionnaire_id=qid, questionnaires=self.service.list_questionnaires(active_only=False))
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.get("/api/admin/rosters")
        def admin_rosters():
            try:
                self._require_unlocked()
                return self._json_ok(rosters=self.service.list_rosters())
            except ServiceError as exc:
                return self._json_error(str(exc), 403)

        @app.post("/api/admin/roster/create")
        def admin_roster_create():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                name = str(payload.get("name", "")).strip()
                description = str(payload.get("description", "")).strip()
                roster_id = self.service.create_roster(name=name, description=description)
                return self._json_ok(roster_id=roster_id, rosters=self.service.list_rosters())
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/roster/rename")
        def admin_roster_rename():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                roster_id = str(payload.get("roster_id", "")).strip()
                new_name = str(payload.get("new_name", "")).strip()
                self.service.rename_roster(roster_id, new_name)
                return self._json_ok(rosters=self.service.list_rosters())
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/roster/copy")
        def admin_roster_copy():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                roster_id = str(payload.get("roster_id", "")).strip()
                new_name = str(payload.get("new_name", "")).strip()
                new_id = self.service.copy_roster(roster_id, new_name=new_name)
                return self._json_ok(new_roster_id=new_id, rosters=self.service.list_rosters())
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/roster/delete")
        def admin_roster_delete():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                roster_id = str(payload.get("roster_id", "")).strip()
                self.service.delete_roster(roster_id)
                return self._json_ok(rosters=self.service.list_rosters())
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.get("/api/admin/roster/<roster_id>/members")
        def admin_roster_members(roster_id: str):
            try:
                self._require_unlocked()
                limit = self._safe_int(request.args.get("limit", "1000"), default=1000, min_value=1, max_value=50000)
                members = self.service.list_roster_members(roster_id, limit=limit)
                columns = self.service.get_roster_columns(roster_id)
                return self._json_ok(members=members, columns=columns)
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.get("/api/admin/roster/list-objects")
        def admin_roster_list_objects():
            try:
                self._require_unlocked()
                roster_id = str(request.args.get("roster_id", "")).strip()
                if not roster_id:
                    return self._json_error("请先选择名单。", 400)
                list_objects = self.service.build_roster_column_list_objects(roster_id)
                return self._json_ok(list_objects=list_objects)
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/roster/columns")
        def admin_roster_columns():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                roster_id = str(payload.get("roster_id", "")).strip()
                columns = payload.get("columns", [])
                if not roster_id:
                    return self._json_error("请先选择名单。", 400)
                if not isinstance(columns, list):
                    return self._json_error("字段配置格式错误。", 400)
                self.service.set_roster_columns(roster_id, columns)
                return self._json_ok(
                    columns=self.service.get_roster_columns(roster_id),
                    members=self.service.list_roster_members(roster_id, limit=5000),
                    rosters=self.service.list_rosters(),
                )
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/roster/member/add")
        def admin_roster_member_add():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                roster_id = str(payload.get("roster_id", "")).strip()
                values = payload.get("values", {}) if isinstance(payload.get("values", {}), dict) else {}
                member_name = str(payload.get("member_name", values.get("member_name", ""))).strip()
                member_code = str(payload.get("member_code", values.get("member_code", ""))).strip()
                member_key = str(payload.get("member_key", values.get("member_key", ""))).strip()
                self.service.add_roster_member(
                    roster_id=roster_id,
                    member_name=member_name,
                    member_code=member_code,
                    member_key=member_key,
                    member_values=values,
                )
                return self._json_ok(members=self.service.list_roster_members(roster_id, limit=5000))
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/roster/member/remove")
        def admin_roster_member_remove():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                member_id = self._safe_int(payload.get("member_id", 0), default=0, min_value=0, max_value=10**9)
                roster_id = str(payload.get("roster_id", "")).strip()
                if member_id <= 0:
                    return self._json_error("请先选择成员。", 400)
                self.service.remove_roster_member(member_id)
                members = self.service.list_roster_members(roster_id, limit=5000) if roster_id else []
                return self._json_ok(members=members)
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/roster/import")
        def admin_roster_import():
            try:
                self._require_unlocked()
                roster_id = str(request.form.get("roster_id", "")).strip()
                replace_all = str(request.form.get("replace_all", "0")).strip() in {"1", "true", "True", "yes", "on"}
                upload = request.files.get("file")
                if not roster_id:
                    return self._json_error("请先选择名单。", 400)
                if upload is None or not upload.filename:
                    return self._json_error("请先选择导入文件。", 400)
                tmp = self._save_uploaded_file(upload)
                try:
                    result = self.service.import_roster_file(roster_id=roster_id, file_path=tmp, replace_all=replace_all)
                finally:
                    try:
                        tmp.unlink(missing_ok=True)
                    except Exception:
                        pass
                members = self.service.list_roster_members(roster_id, limit=5000)
                return self._json_ok(result=result, members=members)
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/server/start")
        def admin_server_start():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                host = str(payload.get("host", DEFAULT_HOST)).strip() or DEFAULT_HOST
                port = self._safe_int(payload.get("port", DEFAULT_PORT), default=DEFAULT_PORT, min_value=1, max_value=65535)
                self.default_questionnaire_id = str(payload.get("default_questionnaire_id", "")).strip() or self._active_questionnaire_id()
                self.survey_server.start(host=host, port=port)
                return self._json_ok(server=self._server_payload())
            except ServiceError as exc:
                return self._json_error(str(exc), 400)
            except Exception as exc:  # noqa: BLE001
                return self._json_error(f"启动失败: {exc}", 500)

        @app.post("/api/admin/server/stop")
        def admin_server_stop():
            try:
                self._require_unlocked()
                self.survey_server.stop()
                return self._json_ok(server=self._server_payload())
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.get("/api/admin/server/info")
        def admin_server_info():
            try:
                self._require_unlocked()
                return self._json_ok(server=self._server_payload())
            except ServiceError as exc:
                return self._json_error(str(exc), 403)

        @app.post("/api/admin/server/open-home")
        def admin_server_open_home():
            try:
                self._require_unlocked()
                home = str(self._server_payload().get("home_url", "")).strip()
                if not home:
                    return self._json_error("请先启动局域网服务。", 400)
                webbrowser.open(home)
                return self._json_ok()
            except ServiceError as exc:
                return self._json_error(str(exc), 403)

        @app.post("/api/admin/server/open-default")
        def admin_server_open_default():
            try:
                self._require_unlocked()
                data = self._server_payload()
                url = str(data.get("default_url", "")).strip() or str(data.get("home_url", "")).strip()
                if not url:
                    return self._json_error("请先启动局域网服务。", 400)
                webbrowser.open(url)
                return self._json_ok()
            except ServiceError as exc:
                return self._json_error(str(exc), 403)

        @app.post("/api/admin/offline/export")
        def admin_offline_export():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                questionnaire_id = str(payload.get("questionnaire_id", "")).strip()
                output_path = self._resolve_output_path(str(payload.get("output_path", "")), f"offline_{questionnaire_id or 'form'}.html")
                questionnaire = self.service.get_questionnaire_for_offline_export(questionnaire_id)
                if not questionnaire:
                    return self._json_error("问卷不存在。", 404)
                out = export_offline_html(questionnaire, self.service.crypto.public_key_spki_b64(), output_path)
                return self._json_ok(output_path=str(out))
            except ServiceError as exc:
                return self._json_error(str(exc), 400)
            except Exception as exc:  # noqa: BLE001
                return self._json_error(f"导出失败: {exc}", 500)

        @app.post("/api/admin/offline/open-export-dir")
        def admin_offline_open_export_dir():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                path = self._resolve_output_path(str(payload.get("output_path", "")), "offline_form.html")
                target_dir = path.parent if path.suffix else path
                target_dir.mkdir(parents=True, exist_ok=True)
                self._open_path(target_dir)
                return self._json_ok()
            except ServiceError as exc:
                return self._json_error(str(exc), 400)
            except Exception as exc:  # noqa: BLE001
                return self._json_error(f"打开失败: {exc}", 500)

        @app.get("/api/admin/submissions")
        def admin_submissions():
            try:
                self._require_unlocked()
                questionnaire_id = str(request.args.get("questionnaire_id", "")).strip()
                items = self.service.list_submissions(questionnaire_id=questionnaire_id or None)
                return self._json_ok(submissions=items)
            except ServiceError as exc:
                return self._json_error(str(exc), 403)

        @app.get("/api/admin/submissions/payload-preview")
        def admin_submissions_payload_preview():
            try:
                self._require_unlocked()
                questionnaire_id = str(request.args.get("questionnaire_id", "")).strip()
                if not questionnaire_id:
                    return self._json_error("请先选择问卷。", 400)
                limit = self._safe_int(request.args.get("limit", 3), default=3, min_value=1, max_value=20)
                payloads = self.service.decrypt_submission_payloads(questionnaire_id)
                return self._json_ok(preview=payloads[:limit], total=len(payloads))
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/submission/reject")
        def admin_submission_reject():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                submission_id = str(payload.get("submission_id", "")).strip()
                self.service.reject_submission(submission_id)
                return self._json_ok()
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/vote/import")
        def admin_vote_import():
            try:
                self._require_unlocked()
                upload = request.files.get("file")
                if upload is None or not upload.filename:
                    return self._json_error("请先选择 .vote 文件。", 400)
                tmp = self._save_uploaded_file(upload, suffix=Path(upload.filename).suffix or ".vote")
                try:
                    ok, message = self.service.import_vote_file(tmp)
                finally:
                    try:
                        tmp.unlink(missing_ok=True)
                    except Exception:
                        pass
                if not ok:
                    return self._json_error(message, 400)
                return self._json_ok(message=message)
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.get("/api/admin/sql/schema")
        def admin_sql_schema():
            try:
                self._require_unlocked()
                questionnaire_id = str(request.args.get("questionnaire_id", "")).strip()
                if not questionnaire_id:
                    return self._json_error("请先选择问卷。", 400)
                return self._json_ok(schema=self.service.query_model_schema(questionnaire_id))
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.get("/api/admin/sql/views")
        def admin_sql_views():
            try:
                self._require_unlocked()
                questionnaire_id = str(request.args.get("questionnaire_id", "")).strip()
                if not questionnaire_id:
                    return self._json_ok(views=[])
                return self._json_ok(views=self.service.list_sql_views(questionnaire_id))
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/sql/view/save")
        def admin_sql_view_save():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                questionnaire_id = str(payload.get("questionnaire_id", "")).strip()
                name = str(payload.get("name", "")).strip()
                sql_text = str(payload.get("sql_text", "")).strip()
                view_id = self.service.save_sql_view(questionnaire_id, name, sql_text)
                views = self.service.list_sql_views(questionnaire_id)
                return self._json_ok(view_id=view_id, views=views)
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/sql/view/delete")
        def admin_sql_view_delete():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                view_id = self._safe_int(payload.get("view_id", 0), default=0, min_value=0, max_value=10**9)
                questionnaire_id = str(payload.get("questionnaire_id", "")).strip()
                self.service.remove_sql_view(view_id)
                views = self.service.list_sql_views(questionnaire_id) if questionnaire_id else []
                return self._json_ok(views=views)
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/sql/run")
        def admin_sql_run():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                questionnaire_id = str(payload.get("questionnaire_id", "")).strip()
                sql_text = str(payload.get("sql_text", "")).strip()
                row_limit = self._safe_int(payload.get("row_limit", 2000), default=2000, min_value=1, max_value=50000)
                result = self.service.execute_sql_query(questionnaire_id, sql_text, row_limit=row_limit)
                first = (result.get("results") or [{}])[0]
                self.last_sql_result = {
                    "columns": first.get("columns", []),
                    "rows": first.get("rows", []),
                }
                return self._json_ok(result=result)
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/rule/validate-sql")
        def admin_rule_validate_sql():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                sql_text = str(payload.get("sql_text", "")).strip()
                normalized = self.service.validate_live_rule_sql(sql_text)
                return self._json_ok(sql=normalized, suffix=self.service.live_rule_auto_filter_suffix())
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/sql/export-csv")
        def admin_sql_export_csv():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                columns = payload.get("columns", self.last_sql_result.get("columns", []))
                rows = payload.get("rows", self.last_sql_result.get("rows", []))
                if not isinstance(columns, list) or not columns:
                    return self._json_error("没有可导出的结果列。", 400)
                if not isinstance(rows, list):
                    return self._json_error("导出数据格式错误。", 400)
                output = self._resolve_output_path(str(payload.get("output_path", "")), "sql_result.csv")
                out = self.service.export_query_result_csv(columns=columns, rows=rows, output_file=output)
                return self._json_ok(output_path=str(out))
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/password/change")
        def admin_password_change():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                old_password = str(payload.get("old_password", "")).strip()
                new_password = str(payload.get("new_password", "")).strip()
                confirm_password = str(payload.get("confirm_password", "")).strip()
                if len(new_password) < 8:
                    return self._json_error("新密码至少 8 位。", 400)
                if new_password != confirm_password:
                    return self._json_error("两次输入的新密码不一致。", 400)
                self.service.change_admin_password(old_password, new_password)
                return self._json_ok(message="管理员密码已更新。")
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.get("/api/admin/settings/runtime-kernel")
        def admin_settings_runtime_kernel_get():
            try:
                self._require_unlocked()
                current = self.service.get_runtime_kernel()
                return self._json_ok(
                    kernel=current,
                    next_kernel="tkinter" if current == "web" else "web",
                )
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/settings/runtime-kernel")
        def admin_settings_runtime_kernel_set():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                target_raw = str(payload.get("kernel", "")).strip().lower()
                if target_raw in {"web", "tkinter"}:
                    current = self.service.set_runtime_kernel(target_raw)
                else:
                    current = self.service.toggle_runtime_kernel(self.service.get_runtime_kernel())
                return self._json_ok(
                    kernel=current,
                    next_kernel="tkinter" if current == "web" else "web",
                    restart_required=True,
                    message="已保存。重启程序后生效。",
                )
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        @app.post("/api/admin/backup/create")
        def admin_backup_create():
            try:
                self._require_unlocked()
                payload: Dict[str, Any] = request.get_json(silent=True) or {}
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                output = self._resolve_output_path(str(payload.get("output_path", "")), f"votefree_backup_{ts}.zip")
                backup_file = self.service.create_backup(output)
                return self._json_ok(output_path=str(backup_file))
            except ServiceError as exc:
                return self._json_error(str(exc), 400)

        return app

    def start(self) -> ShellInfo:
        if self._thread and self._thread.is_alive():
            return self._info  # type: ignore[return-value]
        self._thread = _ServerThread(self.app)
        self._thread.start()
        self._info = ShellInfo(port=self._thread.port)
        return self._info

    def stop(self) -> None:
        try:
            if self.survey_server.is_running():
                self.survey_server.stop()
        except Exception:
            pass
        if self._thread:
            self._thread.shutdown()
            self._thread.join(timeout=2)
        self._thread = None
        self._info = None


def run_web_shell(service: VoteFreeService) -> None:
    shell = WebAdminShell(service=service, paths=service.paths)
    info = shell.start()
    try:
        import webview  # type: ignore
    except Exception as exc:  # noqa: BLE001
        shell.stop()
        raise RuntimeError(f"无法启动浏览器内核（pywebview）: {exc}") from exc

    try:
        webview.create_window(
            f"{APP_NAME} 管理端",
            info.admin_url,
            width=1420,
            height=920,
            min_size=(1180, 760),
            text_select=True,
        )
        webview.start()
    finally:
        shell.stop()
