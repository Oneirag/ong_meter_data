"""
Opens i-de website in a browser, gets cookies from it and writes them to the config file
"""

import json
from ong_meter_data import JSON_CONFIG_FILE, config

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    args = []
    # disable navigator.webdriver:true flag
    args.append("--disable-blink-features=AutomationControlled")
    # Make sure to run headed.
    browser = p.chromium.launch(headless=False,
                                args=args
                                )

    # Setup context however you like.
    context = browser.new_context() # Pass any options
    # context.route('**/*', lambda route: route.continue_())

    # Pause the page, and start recording manually.
    page = context.new_page()
    page.goto("https://www.i-de.es/consumidores/web/guest/login")
    page.wait_for_load_state("domcontentloaded")
    # Close cookies maessage
    page.get_by_label("email").fill(config("i-de_usr"))
    page.get_by_label("contraseña").fill(config("i-de_pwd"))
    page.get_by_role("button", name="Rechazarlas todas").click()
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.wait_for_url("")
    # page.pause()
    # Close popup (if found)
    page.keyboard.press("Escape")
    page.locator("app-consumption-history-module").get_by_role("link", name="Ver detalle >").click()
    cookies_dict = {c['name']: c['value'] for c in context.cookies()}
    cookies_json = {k: v for k, v in cookies_dict.items() if k in ("JSESSIONID", "mb_sz")}
    print(cookies_json)
    cookies_json['bm_sz'] = None    # Not used anymore but needed
    JSON_CONFIG_FILE.write_text(json.dumps(cookies_json))
    page.pause()
