from pathlib import Path
from playwright.sync_api import Page
from typing import List, Dict, Any

DEFAULT_TIMEOUT = 30000
CURRENT_LOG_DIR = Path("logs")


def set_log_context(log_dir: Path) -> None:
    global CURRENT_LOG_DIR
    CURRENT_LOG_DIR = Path(log_dir)
    CURRENT_LOG_DIR.mkdir(parents=True, exist_ok=True)


def safe_name(value: str, max_len: int = 120) -> str:
    text = str(value)
    for old, new in [
        ('#', ''),
        ('.', '_'),
        ('/', '_'),
        (':', '_'),
        ("'", ''),
        ('"', ''),
        (' ', '_'),
        ('[', '_'),
        (']', '_'),
        ('(', '_'),
        (')', '_'),
        ('=', '_'),
    ]:
        text = text.replace(old, new)

    text = text.strip('_')
    if not text:
        text = "unnamed"

    return text[:max_len]


def build_log_path(filename: str) -> str:
    return str(CURRENT_LOG_DIR / filename)


def safe_screenshot(page: Page, filename: str) -> None:
    full_path = build_log_path(filename)
    try:
        page.screenshot(path=full_path, full_page=True, timeout=5000)
        print(f"Screenshot salvato: {full_path}")
    except Exception as screenshot_error:
        print(f"Impossibile salvare screenshot {full_path}: {screenshot_error}")


def save_debug_html(page: Page, filename: str) -> None:
    full_path = build_log_path(filename)
    try:
        html = page.content()
        Path(full_path).write_text(html, encoding="utf-8")
        print(f"HTML salvato: {full_path}")
    except Exception as html_error:
        print(f"Impossibile salvare HTML {full_path}: {html_error}")


def get_action_timeout(action: Dict[str, Any]) -> int:
    return action.get("timeout", DEFAULT_TIMEOUT)


def require_field(data: Dict[str, Any], field_name: str, context: str) -> Any:
    if field_name not in data:
        raise ValueError(f"Campo obbligatorio mancante '{field_name}' in {context}: {data}")
    return data[field_name]


def run_actions_check_reaction(page: Page, actions: List[Dict[str, Any]], reaction: Dict[str, Any]) -> bool:
    print("Eseguo sequenza actions:", actions)

    for idx, action in enumerate(actions, start=1):
        action_type = action.get("type")
        if not action_type:
            raise ValueError(f"[ACTION {idx}] Campo 'type' mancante: {action}")

        try:
            action_timeout = get_action_timeout(action)

            if action_type == "goto":
                url = require_field(action, "url", f"ACTION {idx}")
                print(f"[ACTION {idx}] goto url={url} timeout={action_timeout}")
                page.goto(
                    url,
                    wait_until=action.get("wait_until", "domcontentloaded"),
                    timeout=action_timeout
                )
                try:
                    print(f"[ACTION {idx}] goto completato url_finale={page.url} title={page.title()!r}")
                except Exception as info_error:
                    print(f"[ACTION {idx}] goto completato ma non riesco a leggere title/url dettaglio: {info_error}")

            elif action_type == "fill":
                selector = require_field(action, "selector", f"ACTION {idx}")
                value = require_field(action, "value", f"ACTION {idx}")
                locator = page.locator(selector)

                print(f"[ACTION {idx}] fill selector={selector} - attendo visibilità timeout={action_timeout}")
                locator.first.wait_for(state="visible", timeout=action_timeout)
                print(f"[ACTION {idx}] fill selector={selector} - elemento visibile count_now={locator.count()}")
                locator.first.fill(value)
                print(f"[ACTION {idx}] fill completato selector={selector}")

            elif action_type == "click":
                selector = require_field(action, "selector", f"ACTION {idx}")
                locator = page.locator(selector)

                print(f"[ACTION {idx}] click selector={selector} - attendo visibilità timeout={action_timeout}")
                locator.first.wait_for(state="visible", timeout=action_timeout)
                print(f"[ACTION {idx}] click selector={selector} - elemento visibile count_now={locator.count()}")
                locator.first.click()
                print(f"[ACTION {idx}] click completato selector={selector}")

            elif action_type == "wait":
                ms = require_field(action, "ms", f"ACTION {idx}")
                print(f"[ACTION {idx}] wait ms={ms}")
                page.wait_for_timeout(ms)

            elif action_type == "wait_visible":
                selector = require_field(action, "selector", f"ACTION {idx}")
                locator = page.locator(selector)

                print(f"[ACTION {idx}] wait_visible selector={selector} - attendo visibilità timeout={action_timeout}")
                locator.first.wait_for(state="visible", timeout=action_timeout)
                print(f"[ACTION {idx}] wait_visible selector={selector} - elemento visibile count_now={locator.count()}")

            elif action_type == "custom_screenshot":
                name = require_field(action, "name", f"ACTION {idx}")
                safe_screenshot(page, name)

            else:
                raise ValueError(f"Azione non supportata: {action_type}")

        except Exception as e:
            print(f"[ACTION {idx}] Errore durante action {action_type}: {e}")
            print(f"[ACTION {idx}] URL corrente: {page.url}")
            print(f"[ACTION {idx}] Selector: {action.get('selector')}")

            filename_png = f"action_fail_{idx}_{action_type}_{safe_name(action.get('selector', 'no_selector'))}.png"
            filename_html = f"action_fail_{idx}_{action_type}_{safe_name(action.get('selector', 'no_selector'))}.html"

            safe_screenshot(page, filename_png)
            save_debug_html(page, filename_html)
            raise

    print("Verifico reaction:", reaction)

    reaction_type = reaction.get("type")
    if not reaction_type:
        raise ValueError(f"Campo 'type' mancante nella reaction: {reaction}")

    if reaction_type == "element_present":
        try:
            reaction_timeout = reaction.get("timeout", DEFAULT_TIMEOUT)
            selector = require_field(reaction, "selector", "REACTION")
            locator = page.locator(selector)

            print(f"[REACTION] selector={selector} - attendo visibilità url={page.url} timeout={reaction_timeout}")
            locator.first.wait_for(state="visible", timeout=reaction_timeout)
            print(f"[REACTION] OK selector visibile={selector} count_now={locator.count()} url={page.url}")

        except Exception as e:
            print(f"Elemento non trovato o non visibile: {reaction.get('selector')} | errore: {e}")

            filename_png = f"reaction_fail_{safe_name(reaction.get('selector', 'no_selector'))}.png"
            filename_html = f"reaction_fail_{safe_name(reaction.get('selector', 'no_selector'))}.html"

            safe_screenshot(page, filename_png)
            save_debug_html(page, filename_html)
            return False
    else:
        raise ValueError(f"Reaction non supportata: {reaction_type}")

    return True