#!/usr/bin/env python3
"""
Medeo Video Generator — AI-powered video creation via Medeo API.

Flow: Upload Media → Create Video (Compose) → Render Video
API:  https://api.prd.medeo.app

Requires:
  - pip install requests
  - Config with Medeo API key
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


try:
    import requests
except ImportError:
    print(json.dumps({
        "error": "requests package not installed",
        "install_command": "pip install requests"
    }), file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STATE_DIR = Path(os.path.expanduser("~/.openclaw/workspace/medeo-video"))
CONFIG_FILE = STATE_DIR / "config.json"
LAST_JOB_FILE = STATE_DIR / "last_job.json"
HISTORY_DIR = STATE_DIR / "history"

# Defaults
DEFAULT_ENV = os.environ.get("MEDEO_ENV", "stg")

ENV_DEFAULTS = {
    "stg": {
        "baseUrl": "https://api.stg.medeo.app",
        "ossBaseUrl": "https://oss.stg.medeo.app",
        "apiKeyUrl": os.environ.get(
            "MEDEO_SIGNUP_URL",
            "https://stg.medeo.app/dev/apikey",
        ),
    },
    "prd": {
        "baseUrl": "https://api.prd.medeo.app",
        "ossBaseUrl": "https://oss.prd.medeo.app",
        "apiKeyUrl": os.environ.get(
            "MEDEO_SIGNUP_URL",
            "https://medeo.app/dev/apikey",
        ),
    },
}

# Top-up / recharge URL (for insufficient credits)
MEDEO_TOPUP_URL = os.environ.get("MEDEO_TOPUP_URL", "https://medeo.app/")

# Network
CONNECT_TIMEOUT = 15   # seconds — TCP handshake
READ_TIMEOUT = 60      # seconds — wait for response body
MAX_RETRIES = 2

# Polling
POLL_INITIAL_INTERVAL = 3     # seconds
POLL_MAX_INTERVAL = 10        # seconds
POLL_BACKOFF_FACTOR = 1.5
UPLOAD_MAX_ATTEMPTS = 90      # ~5 min
COMPOSE_MAX_ATTEMPTS = 360    # ~30 min
RENDER_MAX_ATTEMPTS = 360     # ~30 min

# Valid asset sources
VALID_ASSET_SOURCES = ["ai_images", "ai_videos", "my_uploaded_assets", "stock_videos"]
VALID_ASPECT_RATIOS = ["16:9", "9:16"]

# Sessions Spawn defaults
SPAWN_TIMEOUT_SECONDS = 2400  # 40 minutes


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class MedeoApiError(Exception):
    """Raised when a Medeo API call fails."""
    def __init__(self, message: str, code: str = "", case: str = "",
                 status_code: int = 0, details: Any = None):
        super().__init__(message)
        self.code = code
        self.case = case
        self.status_code = status_code
        self.details = details

    def to_dict(self) -> dict:
        d = {"error": str(self), "code": self.code, "case": self.case}
        if self.status_code:
            d["http_status"] = self.status_code
        if self.details:
            d["details"] = self.details
        return d


class MedeoPollTimeout(Exception):
    """Raised when polling exceeds max attempts."""
    def __init__(self, stage: str, attempts: int, elapsed: float,
                 last_status: str = ""):
        msg = (f"{stage} polling timed out after {attempts} attempts "
               f"({elapsed:.0f}s), last status: {last_status}")
        super().__init__(msg)
        self.stage = stage
        self.attempts = attempts
        self.elapsed = elapsed
        self.last_status = last_status


class MedeoPollFailed(Exception):
    """Raised when a polled job enters a terminal failure state."""
    def __init__(self, stage: str, status: str, error_detail: Any = None):
        msg = f"{stage} failed with status: {status}"
        super().__init__(msg)
        self.stage = stage
        self.status = status
        self.error_detail = error_detail


# ---------------------------------------------------------------------------
# Config / Credential Loading
# ---------------------------------------------------------------------------

def _ensure_dir():
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_history_dir():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _load_raw_config() -> dict:
    """Load raw config from config.json (fallback only)."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _load_config_from_env(env: Optional[str] = None) -> dict:
    """
    Load Medeo config from environment variables (primary source).

    Environment variable: MEDEO_API_KEY (set via raw-config.json → env section)

    Base URLs are derived automatically.
    """
    api_key = os.environ.get("MEDEO_API_KEY", "")

    return {
        "env": env or DEFAULT_ENV,
        "apiKey": api_key,
    }


def _load_config_from_file(env: Optional[str] = None) -> dict:
    """
    Fallback: load config from config.json.

    Supports:
    - Multi-env format: {"prd": {"apiKey": "..."}}
    - Flat format: {"apiKey": "..."}
    """
    raw = _load_raw_config()
    if not raw:
        return {}

    target = env or DEFAULT_ENV

    # Multi-env format
    if target in raw and isinstance(raw[target], dict):
        cfg = dict(raw[target])
        cfg.setdefault("env", target)
        return cfg

    # Flat format
    if "apiKey" in raw:
        cfg = dict(raw)
        cfg.setdefault("env", target)
        return cfg

    return {"env": target}


def _load_api_key_from_sys_env() -> str:
    """Last resort: read MEDEO_API_KEY from /etc/openclaw-claude.env."""
    env_file = Path("/etc/openclaw-claude.env")
    if env_file.exists():
        try:
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("MEDEO_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip("'\"")
                        if key:
                            return key
        except IOError:
            pass
    return ""


def _get_config(env: Optional[str] = None) -> dict:
    """
    Get full resolved config.

    Resolution priority:
      1. Environment variable MEDEO_API_KEY (set via raw-config.json env section)
      2. Skill-local config file (~/.openclaw/workspace/medeo-video/config.json)
      3. System env file (/etc/openclaw-claude.env)
      4. Built-in defaults (base URLs)
    """
    target = env or DEFAULT_ENV
    defaults = ENV_DEFAULTS.get(target, ENV_DEFAULTS["stg"])

    # 1) Environment variable (primary — from raw-config.json env section)
    env_cfg = _load_config_from_env(target)
    api_key = env_cfg.get("apiKey", "")

    # 2) Fallback to config.json
    file_cfg = {}
    if not api_key:
        file_cfg = _load_config_from_file(target)
        api_key = file_cfg.get("apiKey", "")

    # 3) Last resort: /etc/openclaw-claude.env
    if not api_key:
        api_key = _load_api_key_from_sys_env()

    return {
        "env": target,
        "apiKey": api_key,
        "baseUrl": file_cfg.get("baseUrl", defaults["baseUrl"]),
        "ossBaseUrl": file_cfg.get("ossBaseUrl", defaults["ossBaseUrl"]),
    }


def _check_api_key(config: dict):
    """Exit with instructions if API key is missing."""
    if not config.get("apiKey"):
        get_key_url = ENV_DEFAULTS.get(DEFAULT_ENV, ENV_DEFAULTS["stg"])["apiKeyUrl"]
        print(json.dumps({
            "error": "Medeo API key not configured",
            "setup_required": True,
            "step1": f"Visit {get_key_url} to get your Medeo API key (starts with mk_)",
            "step2": 'Run: python3 scripts/medeo_video.py config-init --api-key "mk_your_key_here"',
        }, indent=2), file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Low-Level HTTP Helpers
# ---------------------------------------------------------------------------

def _headers(api_key: str, idempotency_key: Optional[str] = None) -> dict:
    h = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if idempotency_key:
        h["Idempotency-Key"] = idempotency_key
    return h


def _parse_error_response(resp: requests.Response) -> MedeoApiError:
    """Parse a Medeo error response into a MedeoApiError."""
    try:
        body = resp.json()
        return MedeoApiError(
            message=body.get("message", f"HTTP {resp.status_code}"),
            code=str(body.get("code", "")),
            case=body.get("case", ""),
            status_code=resp.status_code,
            details=body.get("details"),
        )
    except (ValueError, KeyError):
        return MedeoApiError(
            message=f"HTTP {resp.status_code}: {resp.text[:500]}",
            status_code=resp.status_code,
        )


def _api_get(base_url: str, path: str, api_key: str,
             params: Optional[dict] = None) -> dict:
    """GET request to Medeo API with retry."""
    url = f"{base_url}{path}"
    last_err = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url,
                headers=_headers(api_key),
                params=params,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            if resp.status_code == 200:
                return resp.json()
            last_err = _parse_error_response(resp)
            # Don't retry 4xx
            if 400 <= resp.status_code < 500:
                raise last_err
        except MedeoApiError:
            raise
        except requests.RequestException as e:
            last_err = MedeoApiError(
                message=f"Network error: {e}",
                case="network_error",
            )

        if attempt < MAX_RETRIES:
            time.sleep(2 ** attempt)

    raise last_err or MedeoApiError("Unknown error after retries")


def _api_get_public(base_url: str, path: str,
                    params: Optional[dict] = None) -> dict:
    """GET request to a public Medeo endpoint (no auth)."""
    url = f"{base_url}{path}"
    last_err = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url,
                headers={"Accept": "application/json"},
                params=params,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            if resp.status_code == 200:
                return resp.json()
            last_err = _parse_error_response(resp)
            if 400 <= resp.status_code < 500:
                raise last_err
        except MedeoApiError:
            raise
        except requests.RequestException as e:
            last_err = MedeoApiError(
                message=f"Network error: {e}",
                case="network_error",
            )

        if attempt < MAX_RETRIES:
            time.sleep(2 ** attempt)

    raise last_err or MedeoApiError("Unknown error after retries")


def _api_post(base_url: str, path: str, api_key: str,
              body: dict, idempotency_key: Optional[str] = None) -> dict:
    """POST request to Medeo API with retry."""
    url = f"{base_url}{path}"
    idem_key = idempotency_key or str(uuid.uuid4())
    last_err = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.post(
                url,
                headers=_headers(api_key, idem_key),
                json=body,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            if resp.status_code == 200:
                return resp.json()
            last_err = _parse_error_response(resp)
            if 400 <= resp.status_code < 500:
                raise last_err
        except MedeoApiError:
            raise
        except requests.RequestException as e:
            last_err = MedeoApiError(
                message=f"Network error: {e}",
                case="network_error",
            )

        if attempt < MAX_RETRIES:
            time.sleep(2 ** attempt)

    raise last_err or MedeoApiError("Unknown error after retries")


# ---------------------------------------------------------------------------
# Progress Reporting (stderr)
# ---------------------------------------------------------------------------

def _log(msg: str):
    """Print progress info to stderr."""
    print(f"[medeo] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Medeo API Endpoint Functions
# ---------------------------------------------------------------------------

def api_list_recipes(config: dict, limit: int = 20, order: str = "desc",
                     starting_after: Optional[str] = None) -> dict:
    """List available video recipes (public endpoint)."""
    params = {"limit": limit, "order": order}
    if starting_after:
        params["starting_after"] = starting_after
    return _api_get_public(config["baseUrl"], "/api/v2/recipes", params)


def api_create_media_from_url(config: dict, url: str,
                              project_id: Optional[str] = None) -> dict:
    """Upload a media asset from URL (async). Returns job info."""
    body: Dict[str, Any] = {"url": url}
    if project_id:
        body["project_id"] = project_id
    return _api_post(
        config["baseUrl"],
        "/api/v2/medias:create_from_url",
        config["apiKey"],
        body,
    )


def api_get_media_job_status(config: dict, job_id: str) -> dict:
    """Poll media creation job status."""
    return _api_get(
        config["baseUrl"],
        "/api/v2/medias:create_medias_job",
        config["apiKey"],
        params={"job_id": job_id},
    )


def api_initiate_video_creation(config: dict, message_text: str,
                                media_ids: Optional[List[str]] = None,
                                settings: Optional[dict] = None) -> dict:
    """Initiate AI video creation workflow."""
    body: Dict[str, Any] = {
        "message": {
            "sender_id": f"sk_{config['apiKey'][-8:]}",
            "content": [
                {
                    "text": {
                        "type": "text",
                        "text": message_text,
                    }
                }
            ],
        },
        "settings": settings or {},
    }
    if media_ids:
        body["media_ids"] = media_ids
    return _api_post(
        config["baseUrl"],
        "/api/v2/create_video_jobs:initiate_video_creation",
        config["apiKey"],
        body,
    )


def api_get_last_task_status(config: dict, chat_session_id: str) -> dict:
    """Poll video creation task status."""
    return _api_get(
        config["baseUrl"],
        f"/api/v2/chat_sessions/{chat_session_id}/last_task_status",
        config["apiKey"],
    )


def api_create_render_job(config: dict,
                          video_draft_op_record_id: str) -> dict:
    """Create a video rendering job."""
    return _api_post(
        config["baseUrl"],
        "/api/v2/render_video_jobs",
        config["apiKey"],
        {"video_draft_op_record_id": video_draft_op_record_id},
    )


def api_query_render_job(config: dict,
                         video_draft_op_record_id: str) -> dict:
    """Query video rendering job status."""
    return _api_get(
        config["baseUrl"],
        "/api/v2/render_video_jobs",
        config["apiKey"],
        params={"video_draft_op_record_id": video_draft_op_record_id},
    )


# ---------------------------------------------------------------------------
# Polling Functions
# ---------------------------------------------------------------------------

def poll_media_upload(config: dict, job_id: str,
                      label: str = "Upload") -> dict:
    """
    Poll media upload job until completed.
    Returns: {"id": ..., "state": "completed", "media_ids": [...]}
    """
    interval = POLL_INITIAL_INTERVAL
    start = time.time()

    for attempt in range(1, UPLOAD_MAX_ATTEMPTS + 1):
        time.sleep(interval)
        result = api_get_media_job_status(config, job_id)
        state = result.get("state", "")
        elapsed = time.time() - start

        if attempt % 3 == 0 or state in ("completed", "failed"):
            _log(f"{label}: attempt {attempt}, state={state}, "
                 f"elapsed={elapsed:.0f}s")

        if state == "completed":
            media_ids = result.get("media_ids", [])
            if media_ids:
                return result
            # state is completed but media_ids empty — keep polling briefly
            _log(f"{label}: completed but media_ids empty, continuing...")

        if state == "failed":
            raise MedeoPollFailed("upload", state, result)

        interval = min(interval * POLL_BACKOFF_FACTOR, POLL_MAX_INTERVAL)

    elapsed = time.time() - start
    raise MedeoPollTimeout("upload", UPLOAD_MAX_ATTEMPTS, elapsed, state)


def poll_video_creation(config: dict, chat_session_id: str) -> dict:
    """
    Poll video creation (compose) until completed.
    Returns: {"status": "completed", "video_draft_op_record_id": "..."}
    """
    interval = POLL_INITIAL_INTERVAL
    start = time.time()
    last_status = ""

    for attempt in range(1, COMPOSE_MAX_ATTEMPTS + 1):
        time.sleep(interval)
        result = api_get_last_task_status(config, chat_session_id)
        status = result.get("status", "")
        last_status = status
        elapsed = time.time() - start

        if attempt % 5 == 0 or status in ("completed", "failed", "aborted"):
            _log(f"Compose: attempt {attempt}, status={status}, "
                 f"elapsed={elapsed:.0f}s")

        if status == "completed":
            op_id = result.get("video_draft_op_record_id", "")
            if op_id:
                return result
            _log("Compose: completed but no video_draft_op_record_id, "
                 "continuing...")

        if status in ("failed", "aborted"):
            raise MedeoPollFailed("compose", status, result)

        interval = min(interval * POLL_BACKOFF_FACTOR, POLL_MAX_INTERVAL)

    elapsed = time.time() - start
    raise MedeoPollTimeout("compose", COMPOSE_MAX_ATTEMPTS, elapsed,
                           last_status)


def poll_render_job(config: dict,
                    video_draft_op_record_id: str) -> dict:
    """
    Poll render job until completed.
    Returns full render result with url and metadata.
    """
    interval = POLL_INITIAL_INTERVAL
    start = time.time()
    last_status = ""

    for attempt in range(1, RENDER_MAX_ATTEMPTS + 1):
        time.sleep(interval)
        result = api_query_render_job(config, video_draft_op_record_id)
        status = result.get("status", "")
        last_status = status
        elapsed = time.time() - start

        if attempt % 3 == 0 or status in ("completed", "failed", "stopped"):
            _log(f"Render: attempt {attempt}, status={status}, "
                 f"elapsed={elapsed:.0f}s")

        if status == "completed":
            res = result.get("result", {})
            if res and res.get("url"):
                return result
            _log("Render: completed but no URL yet, continuing...")

        if status in ("failed", "stopped"):
            raise MedeoPollFailed("render", status,
                                  result.get("result", {}).get("error"))

        interval = min(interval * POLL_BACKOFF_FACTOR, POLL_MAX_INTERVAL)

    elapsed = time.time() - start
    raise MedeoPollTimeout("render", RENDER_MAX_ATTEMPTS, elapsed,
                           last_status)


# ---------------------------------------------------------------------------
# High-Level Operations
# ---------------------------------------------------------------------------

def resolve_video_url(config: dict, relative_url: str) -> str:
    """Convert a relative video URL to a full OSS URL."""
    if relative_url.startswith("http://") or relative_url.startswith("https://"):
        return relative_url
    oss_base = config["ossBaseUrl"].rstrip("/")
    return f"{oss_base}/{relative_url.lstrip('/')}"


def upload_media_urls(config: dict, urls: List[str]) -> List[str]:
    """
    Upload multiple media URLs and return their media_ids.
    Each URL is uploaded and polled until complete.
    """
    all_media_ids = []

    for i, url in enumerate(urls, 1):
        _log(f"Uploading media {i}/{len(urls)}: {url}")
        job = api_create_media_from_url(config, url)
        job_id = job.get("id", "")
        _log(f"Upload job created: {job_id}")

        result = poll_media_upload(config, job_id,
                                   label=f"Upload {i}/{len(urls)}")
        media_ids = result.get("media_ids", [])
        _log(f"Upload {i}/{len(urls)} complete: media_ids={media_ids}")
        all_media_ids.extend(media_ids)

    return all_media_ids


def build_settings(args) -> dict:
    """Build VideoCreationSettings from CLI args."""
    settings: Dict[str, Any] = {}

    if hasattr(args, "recipe_id") and args.recipe_id:
        settings["recipe_id"] = args.recipe_id

    if hasattr(args, "duration_ms") and args.duration_ms:
        settings["duration_ms"] = args.duration_ms

    if hasattr(args, "aspect_ratio") and args.aspect_ratio:
        settings["aspect_ratio"] = args.aspect_ratio

    if hasattr(args, "voice_id") and args.voice_id:
        settings["voice_id"] = args.voice_id

    if hasattr(args, "video_style_id") and args.video_style_id:
        settings["video_style_id"] = args.video_style_id

    if hasattr(args, "asset_sources") and args.asset_sources:
        settings["asset_sources"] = args.asset_sources

    return settings


def save_job_record(record: dict):
    """Save job record to last_job.json and history."""
    _ensure_dir()
    with open(LAST_JOB_FILE, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    # Save to history
    _ensure_history_dir()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    hist_file = HISTORY_DIR / f"job_{ts}.json"
    with open(hist_file, "w") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    # Prune old history (keep last 50)
    history_files = sorted(HISTORY_DIR.glob("job_*.json"))
    if len(history_files) > 50:
        for old_file in history_files[:-50]:
            old_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Sessions Spawn Task Builder
# ---------------------------------------------------------------------------

def build_spawn_task(message, media_urls=None, media_ids=None,
                     recipe_id=None, duration_ms=None,
                     aspect_ratio=None, voice_id=None,
                     video_style_id=None, asset_sources=None,
                     no_render=False, script_path=None):
    """Build a sessions_spawn payload for async video generation.

    Returns a dict with 'sessions_spawn_args' ready to pass to the
    OpenClaw sessions_spawn tool, plus the raw command for reference.
    """
    if script_path is None:
        script_path = str(Path(__file__).resolve())

    cmd_parts = ["python3", script_path]
    cmd_parts.append("generate")
    cmd_parts.extend(["--message", json.dumps(message, ensure_ascii=False)])

    if media_urls:
        cmd_parts.append("--media-urls")
        for u in media_urls:
            cmd_parts.append(json.dumps(u))
    if media_ids:
        cmd_parts.append("--media-ids")
        cmd_parts.extend(media_ids)
    if recipe_id:
        cmd_parts.extend(["--recipe-id", recipe_id])
    if duration_ms is not None:
        cmd_parts.extend(["--duration-ms", str(duration_ms)])
    if aspect_ratio:
        cmd_parts.extend(["--aspect-ratio", aspect_ratio])
    if voice_id:
        cmd_parts.extend(["--voice-id", voice_id])
    if video_style_id:
        cmd_parts.extend(["--video-style-id", video_style_id])
    if asset_sources:
        cmd_parts.append("--asset-sources")
        cmd_parts.extend(asset_sources)
    if no_render:
        cmd_parts.append("--no-render")

    cmd_str = " ".join(cmd_parts)

    task_text = (
        "You are a video generation worker. Execute the following command "
        "and report the result back to the user.\n\n"
        "Command:\n"
        "```\n"
        "{cmd}\n"
        "```\n\n"
        "This command runs the full Medeo video pipeline "
        "(upload -> compose -> render) and typically takes 5-30 minutes. "
        "Wait for the command to complete — do NOT background it.\n\n"
        "When the command finishes:\n"
        "- If the JSON output contains \"status\": \"completed\":\n"
        "  1. Extract \"video_url\", \"thumbnail_url\", and "
        "\"total_duration_seconds\" from the JSON output.\n"
        "  2. **Deliver the video using the best method for the current "
        "IM channel:**\n"
        "     - **Feishu**: Download the video locally, then send via feishu_send_video.py "
        "with cover image and duration:\n"
        "       ```\n"
        "       curl -sL -o /tmp/medeo_result.mp4 \"<video_url>\"\n"
        "       # Use thumbnail_url from JSON as cover (preferred)\n"
        "       # If thumbnail_url is empty, extract first frame as fallback:\n"
        "       # ffmpeg -i /tmp/medeo_result.mp4 -vframes 1 -q:v 2 "
        "/tmp/medeo_cover.jpg -y 2>/dev/null\n"
        "       python3 {base_dir}/scripts/feishu_send_video.py "
        "--video /tmp/medeo_result.mp4 --to \"<user_id>\" "
        "--cover-url \"<thumbnail_url>\" "
        "--duration <duration_ms>\n"
        "       ```\n"
        "     - **Other channels**: Share the video_url with a brief "
        "summary (duration, resolution).\n"
        "  3. Always include a short text summary: prompt used, "
        "duration, resolution.\n"
        "- If the error indicates insufficient credits (积分不足 / "
        "insufficient balance / quota exceeded), inform the user that their "
        "Medeo credits have run out and guide them to top up at "
        "{topup_url} — once recharged, they can ask to retry.\n"
        "- For other failures, announce the error message and suggest the "
        "user try again or adjust their prompt."
    ).format(cmd=cmd_str, topup_url=MEDEO_TOPUP_URL,
             base_dir=str(Path(__file__).resolve().parent.parent))

    label = message[:60] + "..." if len(message) > 60 else message

    return {
        "sessions_spawn_args": {
            "task": task_text,
            "label": "medeo: " + label,
            "runTimeoutSeconds": SPAWN_TIMEOUT_SECONDS,
        },
        "command": cmd_str,
    }


# ---------------------------------------------------------------------------
# CLI Command Handlers
# ---------------------------------------------------------------------------

def cmd_spawn_task(args, config):
    """Generate sessions_spawn payload for async video generation."""
    _check_api_key(config)

    result = build_spawn_task(
        message=args.message,
        media_urls=args.media_urls,
        media_ids=args.media_ids if hasattr(args, "media_ids") else None,
        recipe_id=getattr(args, "recipe_id", None),
        duration_ms=getattr(args, "duration_ms", None),
        aspect_ratio=getattr(args, "aspect_ratio", None),
        voice_id=getattr(args, "voice_id", None),
        video_style_id=getattr(args, "video_style_id", None),
        asset_sources=getattr(args, "asset_sources", None),
        no_render=getattr(args, "no_render", False),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_recipes(args, config: dict):
    """List available video recipes."""
    params = {"limit": args.limit, "order": args.order}
    if args.starting_after:
        params["starting_after"] = args.starting_after

    result = api_list_recipes(config, **params)
    recipes = result.get("recipes", result.get("list", []))

    output = {
        "count": len(recipes),
        "has_more": result.get("has_more", False),
        "next_cursor": result.get("next_cursor"),
        "recipes": [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "description": r.get("description"),
                "aspect_ratio": (r.get("video_settings") or {}).get("aspect_ratio"),
                "duration_ms": (r.get("video_settings") or {}).get("duration_ms"),
                "asset_sources": (r.get("video_settings") or {}).get("asset_sources"),
                "user_prompt": r.get("user_prompt"),
                "label": r.get("label"),
                "is_new": r.get("is_new"),
                "status": r.get("status"),
            }
            for r in recipes
        ],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


def cmd_upload(args, config: dict):
    """Upload media from URL."""
    _check_api_key(config)

    _log(f"Uploading media from: {args.url}")
    job = api_create_media_from_url(config, args.url, args.project_id)
    job_id = job.get("id", "")
    _log(f"Upload job created: {job_id}")

    if args.no_wait:
        print(json.dumps({
            "job_id": job_id,
            "state": job.get("state", "initial"),
            "message": "Upload initiated. Use upload-status to poll.",
        }, indent=2))
        return

    result = poll_media_upload(config, job_id)
    media_ids = result.get("media_ids", [])
    _log(f"Upload complete! media_ids: {media_ids}")

    print(json.dumps({
        "job_id": job_id,
        "state": "completed",
        "media_ids": media_ids,
    }, indent=2))


def cmd_generate(args, config: dict):
    """Full pipeline: upload → compose → render."""
    _check_api_key(config)

    started_at = datetime.now(timezone.utc)
    stage_durations = {}
    media_ids = list(args.media_ids) if args.media_ids else []
    settings = build_settings(args)

    # --- Stage 1: Upload ---
    if args.media_urls:
        _log("=== Stage 1/3: Upload Media ===")
        t0 = time.time()
        uploaded_ids = upload_media_urls(config, args.media_urls)
        media_ids.extend(uploaded_ids)
        stage_durations["upload"] = {
            "duration_seconds": round(time.time() - t0, 1),
            "media_ids": uploaded_ids,
        }
        _log(f"Upload stage complete: {len(uploaded_ids)} media(s)")
    else:
        _log("=== Stage 1/3: Upload Media (skipped — no URLs) ===")

    # Auto-add my_uploaded_assets if user uploaded media
    if media_ids and settings.get("asset_sources"):
        if "my_uploaded_assets" not in settings["asset_sources"]:
            settings["asset_sources"].append("my_uploaded_assets")
    elif media_ids and "asset_sources" not in settings:
        settings["asset_sources"] = ["my_uploaded_assets"]

    # --- Stage 2: Compose ---
    _log("=== Stage 2/3: Create Video (Compose) ===")
    t0 = time.time()

    compose_result = api_initiate_video_creation(
        config, args.message, media_ids or None, settings
    )
    project_id = compose_result.get("project_id", "")
    video_draft_id = compose_result.get("video_draft_id", "")
    chat_session_id = compose_result.get("chat_session_id", "")

    _log(f"Video creation initiated: project={project_id}, "
         f"chat_session={chat_session_id}")

    task_result = poll_video_creation(config, chat_session_id)
    video_draft_op_record_id = task_result.get(
        "video_draft_op_record_id", "")

    stage_durations["compose"] = {
        "duration_seconds": round(time.time() - t0, 1),
        "project_id": project_id,
        "video_draft_id": video_draft_id,
        "chat_session_id": chat_session_id,
        "video_draft_op_record_id": video_draft_op_record_id,
    }
    _log(f"Compose complete: op_record_id={video_draft_op_record_id}")

    # --- Stage 3: Render ---
    if args.no_render:
        _log("=== Stage 3/3: Render (skipped — --no-render) ===")
        output = {
            "status": "compose_completed",
            "created_at": started_at.isoformat(),
            "project_id": project_id,
            "video_draft_id": video_draft_id,
            "video_draft_op_record_id": video_draft_op_record_id,
            "chat_session_id": chat_session_id,
            "media_ids": media_ids,
            "settings": settings,
            "stages": stage_durations,
            "message": "Compose completed. Use 'render' command to render.",
        }
        save_job_record(output)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    _log("=== Stage 3/3: Render Video ===")
    t0 = time.time()

    api_create_render_job(config, video_draft_op_record_id)
    _log("Render job created, polling...")

    render_result = poll_render_job(config, video_draft_op_record_id)
    result_data = render_result.get("result", {})
    raw_url = result_data.get("url", "")
    video_url = resolve_video_url(config, raw_url)
    metadata = result_data.get("metadata", {})
    # Extract thumbnail URL (relative path like assets/medias/media_xxx.png)
    raw_thumbnail = render_result.get("thumbnail_url", "")
    thumbnail_url = resolve_video_url(config, raw_thumbnail) if raw_thumbnail else ""

    stage_durations["render"] = {
        "duration_seconds": round(time.time() - t0, 1),
    }
    _log(f"Render complete! Video URL: {video_url}")

    # --- Final Output ---
    total_duration = sum(
        s.get("duration_seconds", 0) for s in stage_durations.values()
    )
    output = {
        "status": "completed",
        "created_at": started_at.isoformat(),
        "total_duration_seconds": round(total_duration, 1),
        "project_id": project_id,
        "video_draft_id": video_draft_id,
        "video_draft_op_record_id": video_draft_op_record_id,
        "video_url": video_url,
        "thumbnail_url": thumbnail_url,
        "metadata": metadata,
        "media_ids": media_ids,
        "settings": settings,
        "stages": stage_durations,
    }
    save_job_record(output)
    print(json.dumps(output, indent=2, ensure_ascii=False))


def cmd_compose(args, config: dict):
    """Initiate video creation (compose only, no upload or render)."""
    _check_api_key(config)

    media_ids = list(args.media_ids) if args.media_ids else None
    settings = build_settings(args)

    _log("Initiating video creation...")
    result = api_initiate_video_creation(
        config, args.message, media_ids, settings
    )

    project_id = result.get("project_id", "")
    video_draft_id = result.get("video_draft_id", "")
    chat_session_id = result.get("chat_session_id", "")

    _log(f"Video creation initiated: project={project_id}, "
         f"chat_session={chat_session_id}")

    if args.no_wait:
        print(json.dumps({
            "status": "initiated",
            "project_id": project_id,
            "video_draft_id": video_draft_id,
            "chat_session_id": chat_session_id,
            "message": "Use compose-status to poll progress.",
        }, indent=2))
        return

    task_result = poll_video_creation(config, chat_session_id)
    video_draft_op_record_id = task_result.get(
        "video_draft_op_record_id", "")
    _log(f"Compose complete: op_record_id={video_draft_op_record_id}")

    print(json.dumps({
        "status": "completed",
        "project_id": project_id,
        "video_draft_id": video_draft_id,
        "chat_session_id": chat_session_id,
        "video_draft_op_record_id": video_draft_op_record_id,
    }, indent=2))


def cmd_render(args, config: dict):
    """Render a video from a draft operation record."""
    _check_api_key(config)

    op_id = args.video_draft_op_record_id
    _log(f"Creating render job for: {op_id}")

    api_create_render_job(config, op_id)
    _log("Render job created, polling...")

    if args.no_wait:
        print(json.dumps({
            "status": "started",
            "video_draft_op_record_id": op_id,
            "message": "Use render-status to poll progress.",
        }, indent=2))
        return

    result = poll_render_job(config, op_id)
    result_data = result.get("result", {})
    raw_url = result_data.get("url", "")
    video_url = resolve_video_url(config, raw_url)
    metadata = result_data.get("metadata", {})

    _log(f"Render complete! Video URL: {video_url}")

    print(json.dumps({
        "status": "completed",
        "video_draft_op_record_id": op_id,
        "video_url": video_url,
        "metadata": metadata,
    }, indent=2))


def cmd_upload_status(args, config: dict):
    """Check media upload job status."""
    _check_api_key(config)
    result = api_get_media_job_status(config, args.job_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_compose_status(args, config: dict):
    """Check video creation (compose) task status."""
    _check_api_key(config)
    result = api_get_last_task_status(config, args.chat_session_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_render_status(args, config: dict):
    """Check render job status."""
    _check_api_key(config)
    result = api_query_render_job(config, args.video_draft_op_record_id)

    # Resolve URL if completed
    if result.get("status") == "completed":
        res = result.get("result", {})
        raw_url = res.get("url", "")
        if raw_url:
            result["resolved_video_url"] = resolve_video_url(config, raw_url)

    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_config(args, config: dict):
    """Show current configuration."""
    safe_config = dict(config)
    key = safe_config.get("apiKey", "")
    if key and len(key) > 10:
        safe_config["apiKey"] = key[:8] + "..." + key[-4:]
    safe_config["source_env_var"] = "MEDEO_API_KEY"
    safe_config["config_file"] = str(CONFIG_FILE)
    safe_config["state_dir"] = str(STATE_DIR)
    print(json.dumps(safe_config, indent=2, ensure_ascii=False))


def cmd_config_init(args, config: dict):
    """Initialize or update config.json."""
    _ensure_dir()

    target = getattr(args, 'env', None) or DEFAULT_ENV

    raw = _load_raw_config()
    if not raw:
        raw = {"env": target}

    if target not in raw:
        raw[target] = {}

    if args.api_key:
        if not args.api_key.startswith("mk_"):
            print(json.dumps({
                "warning": "API key should start with 'mk_'. Please verify you copied it correctly.",
                "received_prefix": args.api_key[:8] + "...",
            }, indent=2), file=sys.stderr)
        raw[target]["apiKey"] = args.api_key

    # Set defaults
    defaults = ENV_DEFAULTS.get(target, ENV_DEFAULTS["stg"])
    raw[target].setdefault("baseUrl", defaults["baseUrl"])
    raw[target].setdefault("ossBaseUrl", defaults["ossBaseUrl"])
    raw["env"] = target

    with open(CONFIG_FILE, "w") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

    _log(f"Config saved to {CONFIG_FILE}")
    print(json.dumps({
        "status": "ok",
        "config_file": str(CONFIG_FILE),
    }, indent=2))


def cmd_last_job(args, config: dict):
    """Show the last job record."""
    if not LAST_JOB_FILE.exists():
        print(json.dumps({"message": "No job records found."}))
        return
    with open(LAST_JOB_FILE, "r") as f:
        record = json.load(f)
    print(json.dumps(record, indent=2, ensure_ascii=False))


def cmd_history(args, config: dict):
    """Show job history."""
    if not HISTORY_DIR.exists():
        print(json.dumps({"message": "No history found.", "jobs": []}))
        return

    files = sorted(HISTORY_DIR.glob("job_*.json"), reverse=True)
    limit = args.limit
    jobs = []

    for f in files[:limit]:
        try:
            with open(f, "r") as fh:
                record = json.load(fh)
            jobs.append({
                "file": f.name,
                "status": record.get("status", "unknown"),
                "created_at": record.get("created_at", ""),
                "video_url": record.get("video_url", ""),
                "total_duration_seconds": record.get(
                    "total_duration_seconds", ""),
            })
        except (json.JSONDecodeError, IOError):
            pass

    print(json.dumps({
        "count": len(jobs),
        "total_records": len(files),
        "jobs": jobs,
    }, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# CLI Parser
# ---------------------------------------------------------------------------

def _add_settings_args(parser):
    """Add common video creation settings args to a parser."""
    parser.add_argument("--recipe-id", default=None,
                        help="Recipe/template ID to use")
    parser.add_argument("--duration-ms", type=int, default=None,
                        help="Target video duration in ms (e.g. 30000)")
    parser.add_argument("--aspect-ratio", default=None,
                        choices=VALID_ASPECT_RATIOS,
                        help="Video aspect ratio (default: 16:9)")
    parser.add_argument("--voice-id", default=None,
                        help="Voice ID for narration")
    parser.add_argument("--video-style-id", default=None,
                        help="Video style template ID")
    parser.add_argument("--asset-sources", nargs="+", default=None,
                        choices=VALID_ASSET_SOURCES,
                        help="Allowed asset sources")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="medeo_video",
        description="Medeo Video Generator — AI-powered video creation",
    )
    parser.add_argument("--env", choices=list(ENV_DEFAULTS.keys()),
                        default=None,
                        help=f"Environment (default: {DEFAULT_ENV})")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # --- recipes ---
    p_recipes = sub.add_parser("recipes",
                               help="List available video recipes")
    p_recipes.add_argument("--limit", type=int, default=20,
                           help="Number of recipes (1-100, default 20)")
    p_recipes.add_argument("--order", default="desc",
                           choices=["asc", "desc"],
                           help="Sort order (default: desc)")
    p_recipes.add_argument("--starting-after", default=None,
                           help="Cursor for pagination")

    # --- upload ---
    p_upload = sub.add_parser("upload",
                              help="Upload media from URL")
    p_upload.add_argument("--url", required=True,
                          help="Media URL to upload")
    p_upload.add_argument("--project-id", default=None,
                          help="Optional project ID")
    p_upload.add_argument("--no-wait", action="store_true",
                          help="Don't wait for completion")

    # --- generate (full pipeline) ---
    p_gen = sub.add_parser("generate",
                           help="Full pipeline: upload → compose → render")
    p_gen.add_argument("--message", required=True,
                       help="Video creation prompt / description")
    p_gen.add_argument("--media-urls", nargs="+", default=None,
                       help="Media URLs to upload first")
    p_gen.add_argument("--media-ids", nargs="+", default=None,
                       help="Pre-uploaded media IDs (skip upload)")
    p_gen.add_argument("--no-render", action="store_true",
                       help="Stop after compose (don't render)")
    _add_settings_args(p_gen)

    # --- compose ---
    p_compose = sub.add_parser("compose",
                               help="Create video (compose only)")
    p_compose.add_argument("--message", required=True,
                           help="Video creation prompt / description")
    p_compose.add_argument("--media-ids", nargs="+", default=None,
                           help="Media IDs to include")
    p_compose.add_argument("--no-wait", action="store_true",
                           help="Don't wait for completion")
    _add_settings_args(p_compose)

    # --- render ---
    p_render = sub.add_parser("render",
                              help="Render a video draft")
    p_render.add_argument("--video-draft-op-record-id", required=True,
                          help="Video draft operation record ID")
    p_render.add_argument("--no-wait", action="store_true",
                          help="Don't wait for completion")

    # --- upload-status ---
    p_us = sub.add_parser("upload-status",
                          help="Check media upload job status")
    p_us.add_argument("--job-id", required=True,
                      help="Upload job ID")

    # --- compose-status ---
    p_cs = sub.add_parser("compose-status",
                          help="Check compose task status")
    p_cs.add_argument("--chat-session-id", required=True,
                      help="Chat session ID")

    # --- render-status ---
    p_rs = sub.add_parser("render-status",
                          help="Check render job status")
    p_rs.add_argument("--video-draft-op-record-id", required=True,
                      help="Video draft operation record ID")

    # --- config ---
    sub.add_parser("config", help="Show current configuration")

    # --- config-init ---
    p_ci = sub.add_parser("config-init",
                          help="Initialize or update config")
    p_ci.add_argument("--api-key", required=True,
                      help="Medeo API key")

    # --- spawn-task ---
    p_spawn = sub.add_parser("spawn-task",
                             help="Build sessions_spawn payload for async generation")
    p_spawn.add_argument("--message", required=True,
                         help="Video creation prompt / description")
    p_spawn.add_argument("--media-urls", nargs="+", default=None,
                         help="Media URLs to upload first")
    p_spawn.add_argument("--media-ids", nargs="+", default=None,
                         help="Pre-uploaded media IDs")
    p_spawn.add_argument("--no-render", action="store_true",
                         help="Stop after compose (don't render)")
    _add_settings_args(p_spawn)

    # --- last-job ---
    sub.add_parser("last-job", help="Show last job record")

    # --- history ---
    p_hist = sub.add_parser("history", help="Show job history")
    p_hist.add_argument("--limit", type=int, default=20,
                        help="Number of records to show")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

COMMAND_MAP = {
    "recipes": cmd_recipes,
    "upload": cmd_upload,
    "generate": cmd_generate,
    "spawn-task": cmd_spawn_task,
    "compose": cmd_compose,
    "render": cmd_render,
    "upload-status": cmd_upload_status,
    "compose-status": cmd_compose_status,
    "render-status": cmd_render_status,
    "config": cmd_config,
    "config-init": cmd_config_init,
    "last-job": cmd_last_job,
    "history": cmd_history,
}


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Resolve config
    config = _get_config(env=getattr(args, 'env', None))

    handler = COMMAND_MAP.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(1)

    try:
        handler(args, config)
    except MedeoApiError as e:
        print(json.dumps(e.to_dict(), indent=2, ensure_ascii=False),
              file=sys.stderr)
        sys.exit(1)
    except MedeoPollTimeout as e:
        print(json.dumps({
            "error": str(e),
            "stage": e.stage,
            "attempts": e.attempts,
            "elapsed_seconds": round(e.elapsed, 1),
            "last_status": e.last_status,
        }, indent=2), file=sys.stderr)
        sys.exit(1)
    except MedeoPollFailed as e:
        print(json.dumps({
            "error": str(e),
            "stage": e.stage,
            "status": e.status,
            "detail": e.error_detail,
        }, indent=2), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        _log("Interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
