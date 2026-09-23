"""Playwright screenshots of every page (light + dark) → reports/ui/*.png. Starts its own server
from this folder on a free port (set FR_URL to reuse a running one instead).

    ./run.sh shots                       # all
    ./run.sh shots --only pipeline lead-hot
    ./run.sh shots --fresh               # beat (a) runs the real pipeline in the light pass (costs ~1.5 cents)
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "ui"
VIEWPORT = {"width": 1400, "height": 900}


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _up(url: str) -> bool:
    try:
        urllib.request.urlopen(url + "/api/status", timeout=1).read()
        return True
    except Exception:
        return False


def start_server(with_key: bool = True, cache_dir: Path | None = None) -> tuple[str, subprocess.Popen | None]:
    url = os.environ.get("FR_URL")
    if with_key and url and _up(url):
        return url, None
    port = _free_port()
    env = dict(os.environ)
    if not with_key:
        for name in ("TYPESAFE_API_KEY", "JEV_API_KEY", "FIRSTREAD_FAKE"):
            env.pop(name, None)
    if cache_dir is not None:
        env["FIRSTREAD_CACHE_DIR"] = str(cache_dir)
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "leadqualifier.server:app", "--port", str(port), "--log-level", "warning"], cwd=ROOT, env=env)
    url = f"http://127.0.0.1:{port}"
    for _ in range(80):
        if _up(url):
            break
        time.sleep(0.25)
    return url, proc


def shot(page, name: str, scheme: str, full: bool = False) -> None:
    page.wait_for_timeout(300)
    page.evaluate("() => { const t = document.querySelector('#toast'); if (t) t.hidden = true; }")
    path = OUT / f"{name}-{scheme}.png"
    page.screenshot(path=str(path), full_page=full)
    print("saved", path.relative_to(ROOT))


def wait_results(page, n_min: int = 1) -> None:
    page.wait_for_function(f"() => Object.keys(window.FR.state.results).length >= {n_min}", timeout=120_000)


def no_key_shots(browser, schemes: list[str]) -> None:
    """A fresh clone without TYPESAFE_API_KEY: empty cache, banner on every page, Run explains the key."""
    with tempfile.TemporaryDirectory(prefix="firstread-nokey-") as tmp:
        url, proc = start_server(with_key=False, cache_dir=Path(tmp))
        try:
            for scheme in schemes:
                ctx = browser.new_context(viewport=VIEWPORT, color_scheme=scheme, device_scale_factor=1)
                page = ctx.new_page()
                page.goto(f"{url}/?theme={scheme}#pipeline")
                page.wait_for_selector("#key-banner:not([hidden])", timeout=30_000)
                page.wait_for_timeout(900)
                page.evaluate("() => { window.FR.run(false); }")
                page.wait_for_selector("#toast:not([hidden])", timeout=15_000)
                page.wait_for_timeout(300)
                path = OUT / f"no-key-pipeline-{scheme}.png"
                page.screenshot(path=str(path))
                print("saved", path.relative_to(ROOT))
                ctx.close()
        finally:
            if proc:
                proc.terminate()


def run(only: list[str] | None, schemes: list[str], fresh: bool) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    url, proc = start_server()
    try:
        urllib.request.urlopen(urllib.request.Request(url + "/api/icp/reset", method="POST"), timeout=5).read()
        with sync_playwright() as p:
            browser = p.chromium.launch()
            if not only or "no-key" in only:
                no_key_shots(browser, schemes)
            for scheme in schemes:
                ctx = browser.new_context(viewport=VIEWPORT, color_scheme=scheme, device_scale_factor=1)
                page = ctx.new_page()
                want = lambda n: not only or n in only  # noqa: E731
                page.goto(f"{url}/?theme={scheme}#pipeline")
                page.wait_for_selector("#board .col")
                page.wait_for_timeout(900)  # fonts
                has_results = page.evaluate("() => Object.keys(window.FR.state.results).length") > 0
                if not has_results:
                    page.evaluate("() => { window.FR.run(false); }")  # no return: evaluate must not await the run
                    page.wait_for_function("() => !window.FR.state.running && Object.keys(window.FR.state.results).length > 0", timeout=180_000)

                if want("demo-panel"):
                    page.evaluate("() => window.FR.openDemo(true)")
                    beat = 0 if (fresh and scheme == schemes[0]) else 1
                    page.evaluate(f"() => {{ window.FR.runBeat({beat}); }}")
                    if beat == 0:
                        page.wait_for_function("() => window.FR.state.running", timeout=20_000)
                        page.wait_for_function("() => document.querySelectorAll('#board .lcard').length >= 20", timeout=120_000)
                        shot(page, "pipeline-streaming", scheme)
                    page.wait_for_function(f"() => window.FR.demo.done.has({beat})", timeout=180_000)
                    page.wait_for_timeout(600)
                    shot(page, "demo-panel", scheme)
                    page.evaluate("() => window.FR.openDemo(false)")
                    page.wait_for_timeout(400)

                if want("pipeline"):
                    page.evaluate("() => window.FR.showPage('pipeline')")
                    page.wait_for_selector("#board .lcard")
                    page.wait_for_timeout(500)
                    shot(page, "pipeline", scheme)
                    shot(page, "pipeline-full", scheme, full=True)

                for name, lead_id in (("lead-hot", "L001"), ("lead-vendor", "L047"), ("lead-existing", "L060"), ("lead-warm", "L022")):
                    if want(name):
                        page.evaluate(f"() => window.FR.openLead('{lead_id}')")
                        page.wait_for_selector("#tier-card .tier-big", timeout=60_000)
                        page.wait_for_timeout(500)
                        shot(page, name, scheme)
                        if name in ("lead-hot", "lead-existing"):
                            shot(page, f"{name}-full", scheme, full=True)

                if want("icp"):
                    page.evaluate("() => window.FR.showPage('icp')")
                    page.wait_for_selector("#icp-form .card")
                    page.wait_for_function("() => document.querySelectorAll('#icp-live .live-tier').length === 5", timeout=30_000)
                    page.wait_for_timeout(400)
                    shot(page, "icp", scheme)
                    # preview a stricter revenue gate: tiers move from cache, zero API calls
                    page.evaluate("() => { window.FR.state.icpDraft.min_revenue_band = '30k_100k'; window.FR.renderICPForm(); return window.FR.refreshLive(true); }")
                    page.wait_for_function("() => document.querySelectorAll('#icp-live .move').length > 0", timeout=30_000)
                    page.wait_for_timeout(400)
                    shot(page, "icp-live", scheme)
                    shot(page, "icp-full", scheme, full=True)
                    page.evaluate("() => { window.FR.state.icpDraft = JSON.parse(JSON.stringify(window.FR.state.icp)); window.FR.renderICPForm(); return window.FR.refreshLive(); }")

                if want("accuracy"):
                    page.evaluate("() => window.FR.showPage('accuracy')")
                    page.wait_for_selector("#acc-kpis .kpi", timeout=30_000)
                    page.wait_for_timeout(400)
                    shot(page, "accuracy", scheme, full=True)

                if want("explore"):
                    page.evaluate("() => window.FR.showPage('explore')")
                    page.wait_for_selector("#scatter svg circle", timeout=30_000)
                    page.wait_for_timeout(400)
                    shot(page, "explore", scheme, full=True)

                if want("connect"):
                    page.evaluate("() => window.FR.showPage('connect')")
                    page.wait_for_selector("#connect-inputs .connector")
                    page.wait_for_timeout(400)
                    shot(page, "connect", scheme, full=True)
                ctx.close()
            browser.close()
    finally:
        if proc:
            proc.terminate()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--schemes", nargs="*", default=["light", "dark"])
    ap.add_argument("--fresh", action="store_true", help="beat (a) really re-runs the pipeline in the first scheme")
    a = ap.parse_args()
    run(a.only, a.schemes, a.fresh)
