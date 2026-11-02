import sys

try:
    from zhiyeteam.galaxy import main

    sys.exit(main())
except Exception as exc:
    import ctypes
    import os
    import traceback
    from pathlib import Path

    target = (
        Path(os.environ.get("LOCALAPPDATA", Path.home()))
        / "ZhiYeTeam/galaxy-startup.log"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(traceback.format_exc(), encoding="utf-8")
    ctypes.windll.user32.MessageBoxW(
        0,
        "知识星图未能启动。请确认已安装 Microsoft Edge WebView2 Runtime。\n\n"
        + str(exc)
        + "\n\n诊断日志："
        + str(target),
        "知页启动提示",
        0x10,
    )
    sys.exit(1)
