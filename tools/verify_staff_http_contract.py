"""Opt-in loopback-only proof: real Python API against the Staff Java HTTP client.

Example:
  python tools/verify_staff_http_contract.py --staff-repo ../EnthusiaStaff-Ai-AllDecisions-GUI

Uses random ephemeral credentials, synthetic messages and a temporary SQLite file.
Never connects to a deployed server, Discord, Minecraft or the OpenAI advisory API.
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import os
import secrets
import socket
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx  # pyright: ignore[reportMissingImports]
import uvicorn  # pyright: ignore[reportMissingImports]

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "service"))

from moderation_api.app import create_app  # noqa: E402
from moderation_api.config import ClientCredential, Settings  # noqa: E402
from moderation_api.models import (  # noqa: E402
    ClassificationInput,
    Label,
    MessageAction,
    ReviewPriority,
)

from tests.helpers import result  # noqa: E402


class SyntheticClassifier:
    async def classify(self, item: ClassificationInput):
        match item.current.text:
            case "block":
                return result(action=MessageAction.BLOCK, label=Label.LOW_LEVEL_HARASSMENT)
            case "review":
                return result(label=Label.AMBIGUOUS_REVIEW, review=ReviewPriority.NORMAL)
            case _:
                return result(label=Label.SAFE)

    def health(self) -> dict[str, object]:
        return {"ready": True, "mode": "synthetic", "model_version": "contract-v1"}


def loopback_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def seeded_clients() -> tuple[tuple[ClientCredential, ...], dict[str, str]]:
    tokens = {name: secrets.token_urlsafe(24) for name in ("publisher", "staff", "reader")}
    clients = (
        ClientCredential("contract-publisher", tokens["publisher"], frozenset({"moderate"})),
        ClientCredential(
            "contract-staff", tokens["staff"], frozenset({"review:read", "review:write"})
        ),
        ClientCredential("contract-reader", tokens["reader"], frozenset({"review:read"})),
    )
    return clients, tokens


def await_live(base_url: str) -> None:
    for _ in range(70):
        try:
            if httpx.get(base_url + "/health/live", timeout=0.3).status_code == 200:
                return
        except httpx.RequestError:
            pass
        time.sleep(0.1)
    raise RuntimeError("isolated API did not become ready")


def seed_records(base_url: str, token: str) -> dict[str, str]:
    headers = {"X-Client-Id": "contract-publisher", "Authorization": f"Bearer {token}"}
    events: dict[str, str] = {}
    with httpx.Client(timeout=3.0) as client:
        for label in ("ordinary", "review", "block"):
            response = client.post(base_url + "/v1/moderate", headers=headers, json={
                "platform": "minecraft",
                "channel_profile": "minecraft_public",
                "scope_id": "synthetic-contract-only",
                "channel_id": "local",
                "external_message_id": f"contract-{label}-{secrets.token_hex(5)}",
                "sender_id": "synthetic-player",
                "occurred_at": datetime.now(UTC).isoformat(),
                "text": label,
            })
            if response.status_code != 200:
                raise RuntimeError(f"synthetic seed {label} failed ({response.status_code})")
            events[label] = str(response.json()["event_id"])
    return events


def verify_with_staff(staff_repo: Path, base_url: str, tokens: dict[str, str],
                      events: dict[str, str]) -> None:
    staff_repo = staff_repo.resolve(strict=True)
    if not staff_repo.is_dir() or not (staff_repo / ".git").exists():
        raise RuntimeError("Staff source checkout is missing or not a Git working tree")
    if not (staff_repo / "gradle" / "wrapper" / "gradle-wrapper.jar").is_file():
        raise RuntimeError("Staff checkout is missing its Gradle wrapper JAR")
    environment = os.environ.copy()
    environment.update({
        "ENTHUSIA_CONTRACT_BASE_URL": base_url,
        "ENTHUSIA_CONTRACT_STAFF_TOKEN": tokens["staff"],
        "ENTHUSIA_CONTRACT_READER_TOKEN": tokens["reader"],
        "ENTHUSIA_CONTRACT_BLOCK_ID": events["block"],
    })
    # Call the trusted Gradle wrapper directly through Java, with no shell, fixed
    # arguments and a verified local checkout. Secrets are passed only via env.
    asyncio.run(run_gradle(staff_repo, environment))


async def run_gradle(staff_repo: Path, environment: dict[str, str]) -> None:
    process = await asyncio.create_subprocess_exec(
        "java", "-cp", "gradle/wrapper/gradle-wrapper.jar",
        "org.gradle.wrapper.GradleWrapperMain", ":paper:test", "--tests",
        "net.enthusia.staff.paper.aireview.AiReviewRealApiContractTest",
        "--rerun-tasks", "--no-daemon", "--console=plain",
        cwd=str(staff_repo), env=environment,
    )
    try:
        exit_code = await asyncio.wait_for(process.wait(), timeout=240)
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        raise RuntimeError("Gradle contract verification timed out") from exc
    if exit_code != 0:
        raise RuntimeError(f"Gradle contract verification failed (exit {exit_code})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staff-repo", type=Path, required=True)
    args = parser.parse_args()
    clients, tokens = seeded_clients()
    with tempfile.TemporaryDirectory(prefix="enthusia-contract-") as temporary:
        settings = Settings(
            database_path=Path(temporary) / "synthetic.sqlite3",
            clients=clients,
            request_timeout_ms=1200,
            classifier_timeout_ms=600,
            request_workers=2,
            openai_advisory_enabled=False,
        )
        port = loopback_port()
        base_url = f"http://127.0.0.1:{port}"
        uvicorn_config = uvicorn.Config(
            create_app(settings=settings, classifier=SyntheticClassifier()),
            host="127.0.0.1", port=port, log_level="error", access_log=False,
        )
        server = uvicorn.Server(uvicorn_config)
        thread = threading.Thread(target=server.run, name="synthetic-api", daemon=True)
        thread.start()
        try:
            await_live(base_url)
            events = seed_records(base_url, tokens["publisher"])
            verify_with_staff(args.staff_repo.resolve(), base_url, tokens, events)
            print("PASS: local Python API + actual Java Staff client (synthetic data only)")
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError("isolated API did not shut down")
            gc.collect()  # sqlite3 context managers commit but do not explicitly close.
            time.sleep(0.2)


if __name__ == "__main__":
    main()
