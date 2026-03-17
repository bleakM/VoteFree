from __future__ import annotations

import socket
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional

from flask import Flask, jsonify, render_template, request, session
from werkzeug.serving import make_server

from .config import AppPaths
from .services import ServiceError, VoteFreeService


def discover_lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


class ServerThread(threading.Thread):
    def __init__(self, app: Flask, host: str, port: int):
        super().__init__(daemon=True)
        self._server = make_server(host, port, app, threaded=True)
        self._ctx = app.app_context()
        self._ctx.push()

    def run(self) -> None:
        self._server.serve_forever()

    def shutdown(self) -> None:
        self._server.shutdown()


@dataclass
class RunningInfo:
    host: str
    port: int
    lan_ip: str

    @property
    def base_url(self) -> str:
        return f"http://{self.lan_ip}:{self.port}"


class SurveyServer:
    def __init__(self, service: VoteFreeService, paths: AppPaths):
        self.service = service
        self.paths = paths
        self._thread: Optional[ServerThread] = None
        self._info: Optional[RunningInfo] = None
        self.app = self._build_flask_app()

    def _build_flask_app(self) -> Flask:
        app = Flask(
            "VoteFreeSurveyServer",
            template_folder=str(self.paths.templates_dir),
            static_folder=str(self.paths.static_dir),
        )
        app.secret_key = self.service.flask_secret()

        @app.get("/")
        def index():
            questionnaires = self.service.list_questionnaires(active_only=True)
            return render_template("index.html", questionnaires=questionnaires)

        @app.get("/q/<questionnaire_id>")
        def questionnaire_page(questionnaire_id: str):
            q = self.service.get_questionnaire(questionnaire_id)
            if not q or q.get("status") != "active":
                return render_template("not_found.html"), 404
            passcode_enabled = bool(q.get("passcode_hash"))
            unlocked = bool(session.get(f"unlock_{questionnaire_id}"))
            return render_template(
                "survey.html",
                questionnaire_id=questionnaire_id,
                title=q["title"],
                description=q.get("description", ""),
                passcode_enabled=passcode_enabled,
                unlocked=unlocked,
                auth_required=(q.get("auth_mode", "open") != "open"),
            )

        @app.post("/api/q/<questionnaire_id>/unlock")
        def unlock_questionnaire(questionnaire_id: str):
            q = self.service.get_questionnaire(questionnaire_id)
            if not q:
                return jsonify({"ok": False, "error": "问卷不存在"}), 404
            if not q.get("passcode_hash"):
                session[f"unlock_{questionnaire_id}"] = True
                return jsonify({"ok": True})
            payload = request.get_json(silent=True) or {}
            passcode = str(payload.get("passcode", "")).strip()
            if not passcode:
                return jsonify({"ok": False, "error": "口令不能为空"}), 400
            if not self.service.verify_questionnaire_passcode(q, passcode):
                return jsonify({"ok": False, "error": "口令错误"}), 403
            session[f"unlock_{questionnaire_id}"] = True
            return jsonify({"ok": True})

        @app.get("/api/q/<questionnaire_id>/schema")
        def questionnaire_schema(questionnaire_id: str):
            q = self.service.get_questionnaire(questionnaire_id)
            if not q:
                return jsonify({"ok": False, "error": "问卷不存在"}), 404
            if q.get("passcode_hash") and not session.get(f"unlock_{questionnaire_id}"):
                return jsonify({"ok": False, "error": "需要先通过口令验证"}), 403
            return jsonify(
                {
                    "ok": True,
                    "questionnaire": {
                        "id": q["id"],
                        "title": q["title"],
                        "description": q.get("description", ""),
                        "identity_mode": q.get("identity_mode", "realname"),
                        "allow_repeat": bool(q.get("allow_repeat")),
                        "allow_same_device_repeat": bool(
                            (q.get("identity_fields", {}) or {}).get("allow_same_device_repeat", False)
                        ),
                        "identity_fields": q.get("identity_fields", {}),
                        "auth_mode": q.get("auth_mode", "open"),
                        "auth_required": q.get("auth_mode", "open") != "open",
                        "roster_repeat_items": self.service.get_roster_repeat_items(questionnaire_id),
                        "template_version": int(q.get("current_version", 1)),
                        "schema": q.get("schema", {}),
                    },
                }
            )

        @app.post("/api/q/<questionnaire_id>/verify")
        def verify_identity(questionnaire_id: str):
            q = self.service.get_questionnaire(questionnaire_id)
            if not q:
                return jsonify({"ok": False, "error": "问卷不存在"}), 404
            if q.get("passcode_hash") and not session.get(f"unlock_{questionnaire_id}"):
                return jsonify({"ok": False, "error": "需要先通过口令验证"}), 403
            payload: Dict[str, Any] = request.get_json(silent=True) or {}
            try:
                result = self.service.verify_submission_identity(
                    questionnaire_id=questionnaire_id,
                    member_code=str(payload.get("member_code", "")),
                    member_name=str(payload.get("member_name", "")),
                    identity_data=payload.get("identity_data", {}),
                )
                return jsonify({"ok": True, **result})
            except ServiceError as exc:
                return jsonify({"ok": False, "error": str(exc)}), 400

        @app.post("/api/q/<questionnaire_id>/live-check")
        def live_check(questionnaire_id: str):
            q = self.service.get_questionnaire(questionnaire_id)
            if not q:
                return jsonify({"ok": False, "error": "问卷不存在"}), 404
            if q.get("passcode_hash") and not session.get(f"unlock_{questionnaire_id}"):
                return jsonify({"ok": False, "error": "需要先通过口令验证"}), 403
            payload: Dict[str, Any] = request.get_json(silent=True) or {}
            respondent = payload.get("respondent") or {}
            try:
                data = self.service.check_live_rules(
                    questionnaire_id=questionnaire_id,
                    answers=payload.get("answers") or {},
                    respondent_name=str(respondent.get("name", "")),
                    respondent_code=str(respondent.get("code", "")),
                    respondent_identity=respondent.get("identity_data", {}),
                )
                return jsonify({"ok": True, **data})
            except ServiceError as exc:
                return jsonify({"ok": False, "error": str(exc)}), 400
            except Exception as exc:  # noqa: BLE001
                return jsonify({"ok": False, "error": f"系统异常: {exc}"}), 500

        @app.post("/api/q/<questionnaire_id>/submit")
        def submit(questionnaire_id: str):
            q = self.service.get_questionnaire(questionnaire_id)
            if not q:
                return jsonify({"ok": False, "error": "问卷不存在"}), 404
            if q.get("passcode_hash") and not session.get(f"unlock_{questionnaire_id}"):
                return jsonify({"ok": False, "error": "需要先通过口令验证"}), 403

            payload: Dict[str, Any] = request.get_json(silent=True) or {}
            answers = payload.get("answers") or {}
            respondent = payload.get("respondent") or {}
            try:
                result = self.service.submit_response(
                    questionnaire_id=questionnaire_id,
                    answers=answers,
                    respondent_name=str(respondent.get("name", "")),
                    respondent_code=str(respondent.get("code", "")),
                    respondent_identity=respondent.get("identity_data", {}),
                    client_token=str(payload.get("client_token", "")),
                    source="lan",
                    relation_type=str(payload.get("relation_type", "")),
                    target_label=str(payload.get("target_label", "")),
                    auth_token=str(payload.get("auth_token", "")),
                )
                return jsonify({"ok": True, "submission_id": result.submission_id})
            except ServiceError as exc:
                return jsonify({"ok": False, "error": str(exc)}), 400
            except Exception as exc:  # noqa: BLE001
                return jsonify({"ok": False, "error": f"系统异常: {exc}"}), 500

        return app

    def start(self, host: str, port: int) -> RunningInfo:
        if self._thread and self._thread.is_alive():
            return self._info  # type: ignore[return-value]
        self.app.secret_key = self.service.flask_secret()
        self._thread = ServerThread(self.app, host, port)
        self._thread.start()
        self._info = RunningInfo(host=host, port=port, lan_ip=discover_lan_ip())
        return self._info

    def stop(self) -> None:
        if self._thread:
            self._thread.shutdown()
            self._thread.join(timeout=2)
        self._thread = None
        self._info = None

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def info(self) -> Optional[RunningInfo]:
        return self._info
