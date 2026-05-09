#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Reads meter data from i-DE (former Iberdrola Distribucion)
A user name and a password is needed to log in
"""
import time
import pandas as pd
import requests

from ong_meter_data import config, logger, LOCAL_TZ
from ong_tsdb.client import OngTsdbClient
from ong_utils import OngTimer, is_debugging
from ong_meter_data import JSON_CONFIG_FILE
from ong_meter_data.browser_login import browser_login
import json
import schedule

from dataclasses import dataclass

@dataclass
class SensorConfig:
    name: str
    url_template: str
    metric: str
    period: str = "1h"
    
_sensors = [
    SensorConfig(name="i-de_consumo_1h", 
                 url_template="/consumidores/rest/consumoNew/obtenerDatosConsumoDH/{start_date}/{end_date}/horas/USU/",
                 metric="Consumo"),
    SensorConfig(name="i-de_facturado_1h", 
                 url_template="/consumidores/rest/consumoNew/obtenerDatosConsumoFacturado/numFactura/null//fechaDesde//{start_date}00:00:00//fechaHasta//{end_date}23:59:00/true/",
                 metric="ConsumoFacturado"),
]

_bucket = config('bucket')

URL_BASE = "https://www.i-de.es"
SECONDS_SLEEP = 60 * 10     # 10 min


class IberdrolaSession(object):

    def __init__(self, user_name: str = None, password: str = None):
        """Inits session object, getting JSESSIONID and bm_sz from ~/.config/ongpi/i-de_cookies.json to avoid captcha"""

        self.cups = config("cups")
        self.USERNAME = user_name or config("i-de_usr")
        self.PASSWORD = password or config("i-de_pwd")
        self.next_keep_session = 0      # timestamp for a next keep session request MUST be sent
        self.requests_session = requests.session()
        if JSON_CONFIG_FILE.exists():
            json_config = json.loads(JSON_CONFIG_FILE.read_text())
            self.user_agent = json_config.pop("user_agent")
            self.requests_session.cookies.update(json_config)
        else:
            self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/"
        
    def get_headers(self) -> dict:
        """
        Returns headers for request, including cookies
        :return: a dict to use in urllib3.request
        """
        headers = {
            'authority': URL_BASE,
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'es-ES,es;q=0.9,en;q=0.8',
            'appversion': 'v2',
            'cache-control': 'no-cache',
            'content-type': 'application/json; charset=UTF-8',
            'dispositivo': 'desktop',
            'origin': URL_BASE,
            'pragma': 'no-cache',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            #'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'user-agent': self.user_agent
        }
        
        
        
        return headers

    def do_request(self, method: str, url: str, headers: dict = None, when=None, json=None, return_cookies=False, **kwargs):
        """
        Returns json (or None if failed) for a request to the url (relative to BASE_URL)
        :param method: get or post
        :param url: url (relative to BASE_URL. The actual url to open will be BASE_URL + url)
        :param headers: headers for request (dict). If None, self.get_headers() will be used
        :param when: if not None, a parameter "when" will be added to the query
        :param json: if not None, body data to send in post request
        :param return_cookies: if true, returns a tuple of json-converted response and dict of cookies
        :return: a dict with the json content of the response, or if return_cookies a tuple with two elements,
        first the dict of the json of the response and second a dict with the cookies
        """
        if when is not None:
            fields = {"_": get_timestamp(when)}
        else:
            fields = None
        if headers is None:
            headers = self.get_headers()
        resp = self.requests_session.request(method, URL_BASE + url, headers=headers, params=fields, json=json, **kwargs)
        if resp.status_code != 200:
            logger.error(f"Error in query to {url=}: {resp.status_code=} {resp.content=}")
            if return_cookies:
                return None, None
            else:
                return None
        else:
            if resp.headers.get("Content-Type").split(";")[0] == "application/json":
                js = resp.json()
            else:
                js = resp.content
            if not return_cookies:
                return js
            else:
                cks = resp.cookies
                return js, cks

    def _keep_sesion_opened(self) -> bool:
        """Sends a "keep-alive" request to keep session opened.
        Returns OK if session is opened, False if a new login is needed"""
        now = pd.Timestamp.now(tz="UTC").timestamp()
        if now < self.next_keep_session:
            return True         # avoid unnecessary log ins
        js, cookies = self.do_request("post", '/consumidores/rest/loginNew/mantenerSesion/',
                                      return_cookies=True)
        if not js or not js.get("usSes"):
            logger.info("Session closed".format(js))
            return False
        else:
            self.next_keep_session = now + (int(js['total']) - int(js['aviso'])) * 60
            logger.info("Status: {}".format(js))
            return True

    def read_monthly_history(self, sensor: SensorConfig, when=None, frecuencia="dias", acumular="false") -> list:
        """
        Reads historical hourly data from meter
        :param sensor: SensorConfig object with name and url_template for reading data
        :param when: date from which data will be read. Data will be read from month start to month end of this date. If
        when is None (default) today is used as reference date so this month's date will be read
        :param frecuencia: frequency for accumulation in spanish ("dias" as default, meaning days)
        :param acumular: whether accumulate or not in spanish ("false" as default)
        :return: a list of tuples for use in OngTsdbClient.write
        """
        when = when or pd.Timestamp.today()
        dt_from = when.normalize().replace(day=1)         # month start
        dt_to = dt_from + pd.tseries.offsets.MonthEnd(1)  + pd.tseries.offsets.Day(1) - pd.offsets.Second(1)  # month end
        df = pd.DataFrame(columns=[sensor.metric])
        str_dt_from = dt_from.strftime("%d-%m-%Y")
        str_dt_to = dt_to.strftime("%d-%m-%Y")
        
        url = sensor.url_template.format(
            start_date=str_dt_from, end_date=str_dt_to 
        )
        js = self.do_request("get", url)
        if isinstance(js, dict):
            consumo = js['y']['data'][0]
        else:
            consumo = js[0]['valores']
        fecha_dato = dt_from
        if consumo:
            for index, data_point in enumerate(consumo):
                # logger.info(f"{index=} {data_point=}")
                if isinstance(data_point, dict):
                    data_point = data_point.get("valor")
                if data_point:
                    df.loc[fecha_dato.value, sensor.metric] = data_point
                fecha_dato += pd.to_timedelta(1, unit='h')

        retval = list()
        for idx_ts, row in df.iterrows():
            not_nan = ~row.isna()
            if not_nan.any():
                keys = list(row.keys()[not_nan])
                values = list(float(f) for f in row.values[not_nan])
                retval.append((_bucket, sensor.name, keys, values, idx_ts))
        return retval

    def _do_logout(self):
        """Logs out, deleting cookies and config file"""
        self.do_request("get", "/consumidores/rest/loginNew/logOut")
        JSON_CONFIG_FILE.unlink(missing_ok=True)
        self.requests_session.cookies.clear()
        logger.info("Logged out, cookies cleared")


    def _do_login(self) -> tuple:
        """
        Logs in with user and password and returns a tuple bool, str with the true or false of the login and the reason
        :return: True, None if successfully logged in
                False, None if there is any connection trouble
                False, js_response otherwise (can see if there is a need for a captcha, bad password...)
        """
        js = browser_login()
        if js and "JSESSIONID" in js:
            logger.info("Log in successful")
            return True, js
        else:
            logger.error("Could not login. Review logs to check error")
            return False, js

    def read_meter(self):
        """Reads instantaneous values from meter"""
        params = (
            ('_', get_timestamp()),
        )

        # First, validate is connection to meter is allowed
        resp_auth = self.do_request("get", "/consumidores/rest/escenarioNew/validarComunicacionContador/")
        if isinstance(resp_auth, dict):
            if resp_auth.get("permitirConexion"):
                logger.info("Connection to meter allowed")
                meter_url = '/consumidores/rest/escenarioNew/obtenerMedicionOnline/24'
                resp = self.do_request("get", meter_url, headers=self.get_headers())
                return resp
            else:
                logger.error(f"Could not connect to meter: {resp_auth}")
                return None


def get_timestamp(when=None):
    if when is None:
        when = pd.Timestamp.now(tz="UTC")
    if isinstance(when, int):
        return when
    return int(when.value / 1e6)


def read_historical_meter_reading(session: IberdrolaSession, ongtsdb_client: OngTsdbClient) -> bool:
    """
    Reads historical meter reading from i-de meter and stores into ong_tsdb database.
    :param session: an already opened IberdrolaSession object , from where data will be read
    :param ongtsdb_client: an already initialized OngTsdbClient, where data will be writen
    :return: True if data could be read and write, false otherwise
    """
    for sensor in _sensors:
        date = ongtsdb_client.get_lasttimestamp(_bucket, sensor.name)
        if not date:
            date = pd.Timestamp("2018-01-01", tz=LOCAL_TZ).normalize()  # Story starts in 2018
        else:
            # Convert from timestamp to date + 3600s
            date = pd.Timestamp.fromtimestamp(date, tz=LOCAL_TZ) + pd.tseries.offsets.Hour(1)
        now = pd.Timestamp.now(tz=LOCAL_TZ).normalize()
        month_start = now.replace(day=1)
        if now.minute < 2 and now.hour < 4 or True:
            for when in pd.date_range(min(date, month_start).replace(day=1),
                                    pd.Timestamp.now(tz=LOCAL_TZ) + pd.offsets.MonthEnd(1), freq="MS"):
                sequence = session.read_monthly_history(sensor, when)
                if sequence:
                    ongtsdb_client.write(sequence)
                    logger.info(f"Historical data for {sensor.name} in month {when} saved")
    return True


if __name__ == "__main__":
    
    ongtsdb_client = OngTsdbClient(url=config('url'), token=config('admin_token'), validate_server_version=False)
    ongtsdb_client.create_db(_bucket)
    for sensor in _sensors:
        ongtsdb_client.create_sensor(_bucket, sensor.name, sensor.period, metrics=[sensor.metric],
                                        read_key=config('read_token'), write_key=config('write_token'))
    
    session = IberdrolaSession()
    
    def historical_job(ongtsdb_client: OngTsdbClient, session: IberdrolaSession):
        if not session._keep_sesion_opened():
            login_ok, _ = session._do_login()
            if not login_ok:
                logger.error("Cannot do historical data read because login failed")
                return
        read_historical_meter_reading(session, ongtsdb_client)
        logger.info(f"Historical data read")
        session._do_logout()

    historical_job(ongtsdb_client, session)
    schedule.every().day.at("16:42", "Europe/Madrid").do(historical_job)
    while True:
        schedule.run_pending()
        time.sleep(1)
