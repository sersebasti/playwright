import os
import time
import traceback
from playwright.sync_api import sync_playwright
from general import run_actions_check_reaction

USERNAME = "user"
PASSWORD = "pass"
LOGIN_URL = "https://solar.siseli.com/#/user/login?redirect=%23%2Fuser%2Flogin"

delay_short = 1000
delay_medium = 5000
delay_long = 10000

def main():
    try:
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

            try:
                ok = run_actions_check_reaction(page, actions, reaction)
                print("Esito reaction login:", ok)
            except Exception as e:
                print(f"Errore durante l'esecuzione delle actions: {e}")
                traceback.print_exc()
            #############################################################################################

            #############################################################################################
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

            try:
                ok = run_actions_check_reaction(page, actions, reaction)
                print("Esito reaction Station Device click:", ok)
            except Exception as e:
                print(f"Errore durante l'esecuzione delle actions: {e}")
                traceback.print_exc()
            #############################################################################################

            #############################################################################################
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

            try:
                ok = run_actions_check_reaction(page, actions, reaction)
                print("Esito reaction Device List click:", ok)
            except Exception as e:
                print(f"Errore durante l'esecuzione delle actions: {e}")
                traceback.print_exc()
            

          



            '''
            step_name = "View click"
            actions = [
                {"type": "click", "selector": "tr[data-row-key='416360187241136128'] a:has-text('View')"},
                {"type": "wait", "ms": delay_short},
                {"type": "custom_screenshot", "name": f"after_{step_name.lower()}.png"},
            ]

            reaction = {
                "type": "element_present",
                "selector": "button:has-text('Data Overview')"
            }

            try:
                ok = run_actions_check_reaction(page, actions, reaction)
                print("Esito reaction Station Device click:", ok)
            except Exception as e:
                print(f"Errore durante l'esecuzione delle actions: {e}")
                traceback.print_exc()
            '''



            browser.close()

    except Exception as e:
        print("ERRORE:", e)
        traceback.print_exc()

if __name__ == "__main__":
    main()