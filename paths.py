# -*- coding: utf-8 -*-
"""兼容别名：旧代码里的 `import paths` 依然可用。

路径逻辑已经统一到 A.py，这里只做转发，避免出现两套实现。
"""

from A import (                    # noqa: F401
    app_dir,
    bundle_dir,
    ensure_lib_dir,
    is_frozen,
    resource,
)
