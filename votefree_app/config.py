from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


@dataclass(frozen=True)
class AppPaths:
    root: Path
    data_dir: Path
    votes_dir: Path
    exports_dir: Path
    keys_dir: Path
    db_file: Path
    templates_dir: Path
    static_dir: Path

    @classmethod
    def build(cls) -> "AppPaths":
        root = project_root()
        data_dir = root / "data"
        res_root = resource_root()
        templates_dir = res_root / "templates"
        static_dir = res_root / "static"
        if not templates_dir.exists():
            templates_dir = res_root / "votefree_app" / "templates"
        if not static_dir.exists():
            static_dir = res_root / "votefree_app" / "static"
        return cls(
            root=root,
            data_dir=data_dir,
            votes_dir=data_dir / "votes",
            exports_dir=data_dir / "exports",
            keys_dir=data_dir / "keys",
            db_file=data_dir / "votefree.db",
            templates_dir=templates_dir,
            static_dir=static_dir,
        )

    def ensure(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.votes_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)


APP_NAME = "VoteFree"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = int(os.environ.get("VOTEFREE_PORT", "5050"))
