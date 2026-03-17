from __future__ import annotations

import argparse

from votefree_app.config import AppPaths
from votefree_app.gui import run_gui
from votefree_app.services import VoteFreeService
from votefree_app.web_shell import run_web_shell


def main() -> None:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--web-shell", action="store_true", help="使用浏览器内核管理界面")
    parser.add_argument("--legacy-gui", action="store_true", help="使用原桌面管理界面")
    args = parser.parse_args()
    if args.web_shell and args.legacy_gui:
        parser.error("--web-shell 与 --legacy-gui 不能同时使用。")

    paths = AppPaths.build()
    service = VoteFreeService(paths)
    service.initialize()

    # 参数优先于设置；未指定参数时读取设置页保存的默认内核。
    if args.legacy_gui:
        run_gui(service)
        return
    if args.web_shell:
        run_web_shell(service)
        return

    preferred = service.get_runtime_kernel()
    if preferred == "tkinter":
        run_gui(service)
        return
    try:
        run_web_shell(service)
    except Exception:
        # 非强制 web 启动时，浏览器内核失败自动回退桌面内核。
        run_gui(service)


if __name__ == "__main__":
    main()
