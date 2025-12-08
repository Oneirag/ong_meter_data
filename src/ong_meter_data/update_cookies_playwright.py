"""
Opens i-de website in a browser, gets cookies from it and writes them to the config file
"""
import os
print(os.getenv("PYTHONPATH"))
from time import sleep
import json
from ong_meter_data import JSON_CONFIG_FILE, config, logger
from fake_useragent import UserAgent
from playwright.sync_api import sync_playwright, Response

ua = UserAgent()


with sync_playwright() as p:
    args = []
    # disable navigator.webdriver:true flag
    args.append("--disable-blink-features=AutomationControlled")
    headless=False	# This works
#    headless=True	# fails due to https2 protocol error
#    # Make sure to run headed.
    # Use headless browser under xvfd. Run first: Xvfb :99 -screen 0 1024x768x16 & export DISPLAY=:99
    logger.info("Opening web browser")
    browser = p.chromium.launch(headless=headless,
                                args=args
                                )

    # Setup context however you like.
    context = browser.new_context(user_agent=ua.random) # Pass any options
    # context.route('**/*', lambda route: route.continue_())

    # Pause the page, and start recording manually.
    page = context.new_page()
    logger.info("Navigating to i-de login page")
    page.goto("https://www.i-de.es/consumidores/web/guest/login")
    page.wait_for_load_state("domcontentloaded")
    # Close cookies maessage
    logger.info("Filling username and password")
    page.get_by_label("email").fill(config("i-de_usr"))
    page.get_by_label("contraseña").fill(config("i-de_pwd"))
    page.get_by_role("button", name="Rechazarlas todas").click()
    page.get_by_role("button", name="Entrar", exact=True).click()

    # 2️⃣ Registramos todas las respuestas que finalicen
    errors = []

    def handle_response(response: Response):
        # Si el status indica error, lo guardamos
        logger.debug(response)
        if response.status >= 400:
            errors.append({
                "url": response.url,
                "status": response.status,
                "method": response.request.method
            })

    page.on("response", handle_response)
    # 3️⃣ Esperamos que la página cargue lo necesario (puedes ajustar la espera)
    sleep(2)

    # 4️⃣ Revisamos si hubo errores
    if errors:
        for err in errors:
            logger.error(f"❌ Petición fallida: {err['method']} {err['url']} -> {err['status']}")
        # Opcional: lanzar excepción para que el test falle
        raise AssertionError(f"{len(errors)} peticiones HTTP fallaron.")
    else:
        logger.info("Todas las peticiones HTTP de login fueron exitosas.")    
    errors = []

    logger.info("Checking for MFA code")
    if page.get_by_role("button", name="Enviar código").is_visible():
        # Page is asking for a MFA by a code received in the phone. Ask user for the code
        page.get_by_role("button", name="Enviar código").click()
        logger.info("Page requested a MFA code. Please wait for SMS with the code")
        if not os.environ.get("I_DE_INTERACTIVE"):
            logger.error("Not interactive session, MFA code requested, could not login")
            exit(12345)
        sms_code=input("Code received by sms: ")
        page.get_by_role("textbox", name="Código SMS").fill(sms_code)
        page.get_by_role("button", name="Aceptar").click()
    else:
        logger.info("No MFA code request received")
    logger.info("Waiting for login")
    page.wait_for_load_state("domcontentloaded")
    # page.wait_for_load_state("networkidle", timeout=60000)  # Extend timeout
    # page.wait_for_url("")
    sleep(5)    # Hardcoded sleep, as others don't work
    logger.info("Login page found. Closing any modal popup")
    for i_dialog in reversed(range(5)):
        dialog = page.locator(f"#mat-dialog-{i_dialog}")
        if dialog.is_visible(timeout=100):
            logger.info(f"Closing modal popup #{i_dialog}")
            dialog.get_by_role("img").nth(0).click()
            page.keyboard.press("Escape")
        sleep(.1)
    # page.pause()
    # Close popup (if found)
    #page.keyboard.press("Escape")
    logger.info("Navigating to a page for getting cookie")
    page.locator("app-consumption-history-module").get_by_role("link", name="Ver detalle >").click(force=True)
    cookies_dict = {c['name']: c['value'] for c in context.cookies()}
    cookies_json = {k: v for k, v in cookies_dict.items() if k in ("JSESSIONID", "mb_sz")}
    logger.info("Cookie found, writing to file")
    print(cookies_json)
    cookies_json['bm_sz'] = None    # Not used anymore but needed
    JSON_CONFIG_FILE.write_text(json.dumps(cookies_json))
    logger.info(f"Updated file {JSON_CONFIG_FILE}")
#    page.pause()
    exit(1)