"""Per-instance runtime settings.

The defaults reproduce the single-instance behaviour exactly, so running the app
with no environment variables behaves as it always did. Setting the variables
lets a second instance (a twin bot) run beside the first one instead of both
attaching to the same Chrome.

Read the values through :meth:`RuntimeConfig.from_env` at the moment a component
is built, not at import time: the app calls ``load_dotenv()`` after its imports,
and shell variables must win over the file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_WORKER_ID = "default"
DEFAULT_CHROME_DEBUG_HOST = "localhost"
DEFAULT_CHROME_DEBUG_PORT = 8989

ENV_WORKER_ID = "AUTOPAGE_WORKER_ID"
ENV_CHROME_DEBUG_HOST = "AUTOPAGE_CHROME_DEBUG_HOST"
ENV_CHROME_DEBUG_PORT = "AUTOPAGE_CHROME_DEBUG_PORT"
ENV_DATA_DIR = "AUTOPAGE_DATA_DIR"


def _parse_port(raw: object, name: str) -> int:
    """Return a valid TCP port or raise ValueError with the offending value."""
    try:
        port = int(str(raw).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a TCP port number, got {raw!r}") from None
    if not 1 <= port <= 65535:
        raise ValueError(f"{name} must be between 1 and 65535, got {port}")
    return port


@dataclass(frozen=True)
class RuntimeConfig:
    """Settings that must differ per running instance.

    Attributes:
        worker_id: Label for the instance, used in logs to tell workers apart.
        chrome_debug_host: Host of the Chrome debugging endpoint to attach to.
        chrome_debug_port: Port of the Chrome debugging endpoint to attach to.
        data_dir: Where this instance keeps mutable files (logs, caches,
            generated workbooks). Reserved for the twin-bot rollout; the app
            still writes to its own folder today.
    """

    worker_id: str = DEFAULT_WORKER_ID
    chrome_debug_host: str = DEFAULT_CHROME_DEBUG_HOST
    chrome_debug_port: int = DEFAULT_CHROME_DEBUG_PORT
    data_dir: str = PROJECT_DIR

    @property
    def chrome_debugger_address(self) -> str:
        """Value for the Selenium ``debuggerAddress`` capability."""
        return f"{self.chrome_debug_host}:{self.chrome_debug_port}"

    @property
    def log_dir(self) -> str:
        return os.path.join(self.data_dir, "logs")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "RuntimeConfig":
        """Build a config from the environment, falling back to the defaults."""
        source = os.environ if env is None else env

        worker_id = (source.get(ENV_WORKER_ID) or "").strip() or DEFAULT_WORKER_ID
        host = (source.get(ENV_CHROME_DEBUG_HOST) or "").strip() or DEFAULT_CHROME_DEBUG_HOST
        data_dir = (source.get(ENV_DATA_DIR) or "").strip() or PROJECT_DIR

        raw_port = source.get(ENV_CHROME_DEBUG_PORT)
        port = DEFAULT_CHROME_DEBUG_PORT if raw_port is None or not str(raw_port).strip() \
            else _parse_port(raw_port, ENV_CHROME_DEBUG_PORT)

        return cls(
            worker_id=worker_id,
            chrome_debug_host=host,
            chrome_debug_port=port,
            data_dir=data_dir,
        )
