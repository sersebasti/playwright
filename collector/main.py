import os
import sys
import json
import shutil
import traceback
import pymysql
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
from general import run_actions_check_reaction, set_log_context, safe_screenshot

USERNAME = os.getenv("APP_USERNAME", "sersebasti")
PASSWORD = os.getenv("APP_PASSWORD", "Merca10tello")

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "solar")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_ROOT_PASSWORD", "local")

LOGIN_URL = "https://solar.siseli.com/"

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
    def __init__(self, *streams, timestamp_format="%Y-%m-%d %H:%M:%S"):
        self.streams = streams
        self.timestamp_format = timestamp_format
        self._buffer = ""

    def _timestamp(self) -> str:
        return datetime.now().strftime(self.timestamp_format)

    def write(self, data):
        if not data:
            return

        self._buffer += data

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)

            if line.strip():
                out = f"[{self._timestamp()}] {line}\n"
            else:
                out = "\n"

            for stream in self.streams:
                stream.write(out)
                stream.flush()

    def flush(self):
        if self._buffer:
            if self._buffer.strip():
                out = f"[{self._timestamp()}] {self._buffer}"
            else:
                out = self._buffer

            for stream in self.streams:
                stream.write(out)
                stream.flush()

            self._buffer = ""

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


def save_page_html(page, output_path: Path):
    html = page.content()
    output_path.write_text(html, encoding="utf-8")
    print(f"HTML pagina salvato in: {output_path}")


def save_device_info_json(page, output_path: Path):
    data = {}

    tables = page.locator("table")
    table_count = tables.count()

    target_table = None

    for i in range(table_count):
        table = tables.nth(i)
        try:
            text = " ".join(table.inner_text().split())
            if "Inverter Program Version" in text and "Input Voltage" in text:
                target_table = table
                break
        except Exception:
            continue

    if target_table is None:
        raise RuntimeError("Tabella Device Info corretta non trovata")

    rows = target_table.locator("tr.ant-descriptions-row")
    row_count = rows.count()

    i = 0
    while i < row_count - 1:
        label_row = rows.nth(i)
        value_row = rows.nth(i + 1)

        labels = label_row.locator("span.ant-descriptions-item-label")
        values = value_row.locator("span.ant-descriptions-item-content")

        label_count = labels.count()
        value_count = values.count()

        if label_count == value_count and label_count > 0:
            for j in range(label_count):
                key = " ".join(labels.nth(j).inner_text().split())
                value = " ".join(values.nth(j).inner_text().split())
                data[key] = value
            i += 2
        else:
            i += 1

    try:
        update_text = page.locator("text=UpdateTime").first.inner_text().strip()
        data["_update_time"] = " ".join(update_text.split())
    except Exception:
        pass

    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"JSON salvato in: {output_path}")


def verify_json_file(json_path: Path):
    if not json_path.exists():
        raise RuntimeError(f"File JSON non trovato: {json_path}")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Il file non è un JSON valido: {json_path} | errore: {e}")

    if not isinstance(data, dict):
        raise RuntimeError(f"Il JSON non contiene un oggetto dict: {json_path}")

    print(f"JSON verificato correttamente: {json_path}")
    print(f"Chiavi trovate: {len(data)}")

    for key, value in data.items():
        print(f"  - {key}: {value}")

    return data


def save_device_info_to_db(json_path: Path, device_row_key: str):
    if not json_path.exists():
        raise RuntimeError(f"JSON non trovato: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise RuntimeError(f"Il file non contiene un oggetto JSON valido: {json_path}")

    update_time = data.get("_update_time")
    json_payload = json.dumps(data, ensure_ascii=False)

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )

    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO device_snapshots (
                    device_row_key,
                    update_time,
                    json_data
                ) VALUES (%s, %s, %s)
            """
            cursor.execute(sql, (
                device_row_key,
                update_time,
                json_payload
            ))

        print("Dati salvati su DB correttamente")
        print(f"  - device_row_key: {device_row_key}")
        print(f"  - update_time: {update_time}")
    finally:
        conn.close()


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

                page.on("console", lambda msg: print(f"[BROWSER CONSOLE] {msg.type}: {msg.text}"))
                page.on("pageerror", lambda exc: print(f"[PAGE ERROR] {exc}"))
                page.on("requestfailed", lambda req: print(f"[REQUEST FAILED] {req.method} {req.url} -> {req.failure}"))
                page.on("response", lambda res: print(f"[RESPONSE >=400] {res.status} {res.url}") if res.status >= 400 else None)

                ##############################################################################################
                step_name = "Login"
                actions = [
                    {"type": "goto", "url": LOGIN_URL, "timeout": 120000},
                    {"type": "wait_visible", "selector": "#account", "timeout": 30000},
                    {"type": "fill", "selector": "#account", "value": USERNAME},
                    {"type": "wait_visible", "selector": "#password", "timeout": 30000},
                    {"type": "fill", "selector": "#password", "value": PASSWORD},
                    {"type": "wait_visible", "selector": "button[type='submit']", "timeout": 30000},
                    {"type": "click", "selector": "button[type='submit']"},
                ]

                reaction = {
                    "type": "element_present",
                    "selector": "div.ant-menu-submenu-title:has-text('Operations')",
                    "timeout": 30000
                }

                run_step(page, step_name, actions, reaction)
                safe_screenshot(page, "after_login.png")
                ##############################################################################################

                ##############################################################################################
                step_name = "Station Device click"
                actions = [
                    {"type": "click", "selector": "div.ant-menu-submenu-title:has-text('Station Device')"},
                ]

                reaction = {
                    "type": "element_present",
                    "selector": "a[href='#/operator/stationDevice/deviceList']",
                    "timeout": 30000
                }

                run_step(page, step_name, actions, reaction)
                safe_screenshot(page, "after_station_device_click.png")
                ##############################################################################################

                ##############################################################################################
                step_name = "Device List click"
                actions = [
                    {"type": "click", "selector": "a[href='#/operator/stationDevice/deviceList']"},
                ]

                reaction = {
                    "type": "element_present",
                    "selector": "tr[data-row-key='416360187241136128'] td",
                    "timeout": 30000
                }

                run_step(page, step_name, actions, reaction)
                safe_screenshot(page, "after_device_list_click.png")
                ##############################################################################################

                ##############################################################################################
                step_name = "View click"
                actions = [
                    {"type": "click", "selector": "tr[data-row-key='416360187241136128'] a:has-text('View'):visible"},
                ]

                reaction = {
                    "type": "element_present",
                    "selector": ".ant-descriptions-view >> text=Battery Voltage",
                    "timeout": 30000
                }

                run_step(page, step_name, actions, reaction)
                safe_screenshot(page, "after_view_click.png")
                ##############################################################################################

                ##############################################################################################
                step_name = "Save data to file"

                print("\n" + "=" * 100)
                print(f"START STEP: {step_name}")
                print("=" * 100)

                html_path = LOGS_DIR / "device_info_page.html"
                json_path = LOGS_DIR / "device_info.json"

                save_page_html(page, html_path)
                save_device_info_json(page, json_path)
                verify_json_file(json_path)

                print(f"END STEP: {step_name}")
                ##############################################################################################

                ##############################################################################################
                step_name = "Save data to db"
                print("\n" + "=" * 100)
                print(f"START STEP: {step_name}")
                print("=" * 100)

                json_path = LOGS_DIR / "device_info.json"

                verify_json_file(json_path)
                save_device_info_to_db(
                    json_path=json_path,
                    device_row_key="416360187241136128"
                )

                print(f"END STEP: {step_name}")
                ##############################################################################################

                ##############################################################################################
                step_name = "Open user menu"
                actions = [
                    {"type": "click", "selector": f"span.ant-dropdown-trigger:has(span:has-text('{USERNAME}'))"},
                ]

                reaction = {
                    "type": "element_present",
                    "selector": "li[role='menuitem']:has-text('Logout')",
                    "timeout": 30000
                }

                run_step(page, step_name, actions, reaction)
                safe_screenshot(page, "after_open_user_menu.png")
                ##############################################################################################

                ##############################################################################################
                step_name = "Logout click"
                actions = [
                    {"type": "click", "selector": "li[role='menuitem']:has-text('Logout')"},
                ]

                reaction = {
                    "type": "element_present",
                    "selector": "button.ant-btn.ant-btn-primary:has-text('OK')",
                    "timeout": 30000
                }

                run_step(page, step_name, actions, reaction)
                safe_screenshot(page, "after_logout_click.png")
                ##############################################################################################

                ##############################################################################################
                step_name = "Confirm logout"
                actions = [
                    {"type": "click", "selector": "button.ant-btn.ant-btn-primary:has-text('OK')"},
                ]

                reaction = {
                    "type": "element_present",
                    "selector": "button[type='submit']",
                    "timeout": 30000
                }

                run_step(page, step_name, actions, reaction)
                safe_screenshot(page, "after_confirm_logout.png")
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