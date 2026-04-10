from playwright.sync_api import Page
from typing import List, Dict, Any

timeout = 15000

def safe_name(value: str) -> str:
    return str(value).replace('#', '').replace('.', '_').replace('/', '_').replace(':', '_').replace("'", "")

def run_actions_check_reaction(page: Page, actions: List[Dict[str, Any]], reaction: Dict[str, Any]) -> bool:
    print("Eseguo sequenza actions:", actions)

    for idx, action in enumerate(actions, start=1):
        try:
            action_timeout = action.get("timeout", timeout)

            if action['type'] == 'goto':
                page.goto(
                    action['url'],
                    wait_until=action.get('wait_until', 'domcontentloaded'),
                    timeout=action_timeout
                )

            elif action['type'] == 'fill':
                locator = page.locator(action['selector'])
                print(f"[ACTION {idx}] fill selector={action['selector']} count={locator.count()}")
                locator.first.wait_for(state="visible", timeout=action_timeout)
                locator.first.fill(action['value'])

            elif action['type'] == 'click':
                locator = page.locator(action['selector'])
                print(f"[ACTION {idx}] click selector={action['selector']} count={locator.count()}")
                locator.first.wait_for(state="visible", timeout=action_timeout)
                locator.first.click()

            elif action['type'] == 'wait':
                page.wait_for_timeout(action['ms'])

            elif action['type'] == 'custom_screenshot':
                page.screenshot(path=action['name'], full_page=True)
                print(f"Salvato screenshot: {action['name']}")

            else:
                raise ValueError(f"Azione non supportata: {action['type']}")

        except Exception as e:
            print(f"[ACTION {idx}] Errore durante action {action['type']}: {e}")
            print(f"[ACTION {idx}] URL corrente: {page.url}")
            print(f"[ACTION {idx}] Selector: {action.get('selector')}")
            filename = f"action_fail_{idx}_{action['type']}_{safe_name(action.get('selector', 'no_selector'))}.png"
            page.screenshot(path=filename, full_page=True)
            print(f"[ACTION {idx}] Screenshot salvato: {filename}")
            raise

    print("Verifico reaction:", reaction)

    if reaction['type'] == 'element_present':
        try:
            reaction_timeout = reaction.get("timeout", timeout)
            locator = page.locator(reaction['selector'])
            print(f"[REACTION] selector={reaction['selector']} count={locator.count()} url={page.url}")
            locator.first.wait_for(state="visible", timeout=reaction_timeout)
        except Exception:
            print(f"Elemento non trovato o non visibile: {reaction['selector']}")
            filename = f"reaction_fail_{safe_name(reaction['selector'])}.png"
            page.screenshot(path=filename, full_page=True)
            print(f"Screenshot salvato: {filename}")
            return False
    else:
        raise ValueError(f"Reaction non supportata: {reaction['type']}")

    return True
