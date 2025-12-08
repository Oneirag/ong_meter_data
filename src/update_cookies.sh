ENV=/home/$USER/PycharmProjects/ong_meter_data/.venv
# Mark execution as interactive (so program can ask user instead of exiting with error)
I_DE_INTERACTIVE=1

xvfb-run $ENV/bin/python -m ong_meter_data.update_cookies_playwright
