import os
import sys
import shutil
import traceback
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
from general import run_actions_check_reaction, set_log_context

USERNAME = os.getenv("APP_USERNAME", "sersebasti")
PASSWORD = os.getenv("APP_PASSWORD", "Merca10tello")
LOGIN_URL = "https://solar.siseli.com/#/user/login?redirect=%23%2Fuser%2Flogin"

delay_short = 1000
delay_medium = 5000
delay_long = 10000


def archive_previous_logs(script_name: str) -> Path:
    script_log_root = Path("logs") / script_name
    old_dir = script_log_root / "old"

    script_log_root.mkdir(parents=True, exist_ok=True)
    old_dir.mkdir(parents=True, exist_ok=True)

    for item in script_log_root.iterdir():
        if item.name == "old":
            continue

        destination = old_dir / item.name

        if destination.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destination = old_dir / f"{item.name}_{timestamp}"

        shutil.move(str(item), str(destination))

    return script_log_root


SCRIPT_NAME = Path(__file__).stem
TODAY_STR = datetime.now().strftime("%Y-%m-%d")
RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")

SCRIPT_LOG_ROOT = archive_previous_logs(SCRIPT_NAME)
LOGS_DIR = SCRIPT_LOG_ROOT / TODAY_STR
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / f"run_{RUN_TS}.log"


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


def run_step(page, step_name, actions, reaction):
    print("\n" + "=" * 100)
    print(f"START STEP: {step_name}")
    print("=" * 100)

    ok = run_actions_check_reaction(page, actions, reaction)
    print(f"Esito reaction {step_name}: {ok}")

    if not ok:
        raise RuntimeError(f"Step fallito: {step_name}")

    print(f"END STEP: {step_name}")


def main():
    if not USERNAME or not PASSWORD:
        raise RuntimeError("APP_USERNAME o APP_PASSWORD non impostati")

    set_log_context(LOGS_DIR)

    with open(LOG_FILE, "a", encoding="utf-8") as log_fp:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = Tee(sys.stdout, log_fp)
        sys.stderr = Tee(sys.stderr, log_fp)

        try:
            print(f"Script name: {SCRIPT_NAME}")
            print(f"Log dir: {LOGS_DIR.resolve()}")
            print(f"Log file: {LOG_FILE.resolve()}")

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--window-size=1900,1000",
                        "--window-position=0,0",
                    ]
                )

                context = browser.new_context(
                    ignore_https_errors=True,
                    no_viewport=True
                )
                page = context.new_page()

                ##############################################################################################
                step_name = "Login"
                actions = [
                    {"type": "goto", "url": LOGIN_URL, "timeout": 120000},
                    {"type": "wait", "ms": delay_medium},
                    {"type": "fill", "selector": "#account", "value": USERNAME},
                    {"type": "wait", "ms": delay_short},
                    {"type": "fill", "selector": "#password", "value": PASSWORD},
                    {"type": "wait", "ms": delay_short},
                    {"type": "click", "selector": "button[type='submit']"},
                    {"type": "wait", "ms": delay_medium},
                    {"type": "custom_screenshot", "name": f"after_{step_name.lower()}.png"},
                ]

                reaction = {
                    "type": "element_present",
                    "selector": "div.ant-menu-submenu-title:has-text('Operations')",
                }

                run_step(page, step_name, actions, reaction)
                ##############################################################################################

                ##############################################################################################
                step_name = "Station Device click"
                actions = [
                    {"type": "click", "selector": "div.ant-menu-submenu-title:has-text('Station Device')"},
                    {"type": "wait", "ms": delay_short},
                    {"type": "custom_screenshot", "name": f"after_{step_name.lower()}.png"},
                ]

                reaction = {
                    "type": "element_present",
                    "selector": "a[href='#/operator/stationDevice/deviceList']"
                }

                run_step(page, step_name, actions, reaction)
                ##############################################################################################

                ##############################################################################################
                step_name = "Device List click"
                actions = [
                    {"type": "click", "selector": "a[href='#/operator/stationDevice/deviceList']"},
                    {"type": "wait", "ms": delay_medium},
                    {"type": "custom_screenshot", "name": f"after_{step_name.lower()}.png"},
                ]

                reaction = {
                    "type": "element_present",
                    "selector": "tr[data-row-key='416360187241136128'] td"
                }

                run_step(page, step_name, actions, reaction)
                ##############################################################################################

                ##############################################################################################
                step_name = "View click"
                actions = [
                    {"type": "click", "selector": "tr[data-row-key='416360187241136128'] a:has-text('View'):visible"},
                    {"type": "wait", "ms": delay_medium},
                    {"type": "custom_screenshot", "name": f"after_{step_name.lower()}.png"},
                ]

                reaction = {
                    "type": "element_present",
                    "selector": "div:has-text('Device Info')"
                }

                run_step(page, step_name, actions, reaction)
                ##############################################################################################


        except Exception as e:
            print("\n" + "!" * 100)
            print("ERRORE BLOCCANTE:", e)
            traceback.print_exc()
            print("!" * 100)

        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr


if __name__ == "__main__":
    main()