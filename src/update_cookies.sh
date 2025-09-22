ENV=/home/$USER/PycharmProjects/ong_meter_data/.venv

xvfb-run $ENV/bin/python -m ong_meter_data.update_cookies_playwright
