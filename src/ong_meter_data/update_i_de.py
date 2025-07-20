#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Reads meter data from i-DE (former Iberdrola Distribucion)
A user name and a password is needed to log in
"""
import time
from datetime import datetime
import logging

import pandas as pd
import requests

from ong_meter_data import config, logger, LOCAL_TZ
from ong_tsdb.client import OngTsdbClient
from ong_utils import OngTimer, is_debugging
from ong_meter_data.eks import run_eks
from ong_meter_data import JSON_CONFIG_FILE
import json
import schedule

_bucket = config('bucket')
_sensors = dict(sensor_1h="i-de_1h", sensor_1s="i-de_1s", sensor_15m="i-de_15m")
URL_BASE = "https://www.i-de.es"
SECONDS_SLEEP = 60 * 10     # 10 min


class IberdrolaSession(object):

    def __init__(self, user_name: str = None, password: str = None):
        """Inits session object, getting JSESSIONID and bm_sz from ~/.config/ongpi/i-de_cookies.json to avoid captcha"""

        self.cups = config("cups")
        self.USERNAME = user_name or config("i-de_usr")
        self.PASSWORD = password or config("i-de_pwd")
        if not JSON_CONFIG_FILE.exists():
            error_msg = (f"File {JSON_CONFIG_FILE} does not exist. Cannot proceed with login.\n" +
                f"Please create it with JSESSIONID and bm_sz cookies from a requests to mantenerSesion or to eks from www.i-de.es.\n"
                "Minimum content is:\n"
                f'{{"JSESSIONID": "your_jsessionid", "bm_sz": "your_bm_sz"}}\n' 
            )
                
            logger.error(error_msg)
            raise ValueError(error_msg)

        json_config = json.loads(JSON_CONFIG_FILE.read_text())

        self.JSESSIONID = json_config["JSESSIONID"]
        self.bm_sz = json_config.get("bm_sz")
        self.next_keep_session = 0      # timestamp for a next keep session request MUST be sent
        self.requests_session = requests.session()
        self.requests_session.cookies.update({"JSESSIONID": self.JSESSIONID})
        if self.bm_sz:
            self.requests_session.cookies.update({"bm_sz": self.bm_sz})


    def save_config(self):
        """Dumps JSESSIONID to avoid multiple login that will make captcha to appear"""
        JSON_CONFIG_FILE.write_text(json.dumps(dict(JSESSIONID=self.JSESSIONID, bm_sz=None)))

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
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
        if self.bm_sz:
            logger.info(f"Run eks: {run_eks(self.requests_session)}")
        now = pd.Timestamp.utcnow().timestamp()
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

    def read_monthly_history(self, sensor_name: str, when=None, frecuencia="dias", acumular="false") -> list:
        """
        Reads historical hourly data from meter
        :param sensor_name: name of sensor for writing in DB
        :param when: date from which data will be read. Data will be read from month start to month end of this date. If
        when is None (default) today is used as reference date so this month's date will be read
        :param frecuencia: frequency for accumulation in spanish ("dias" as default, meaning days)
        :param acumular: whether accumulate or not in spanish ("false" as default)
        :return: a list of tuples for use in OngTsdbClient.write
        """
        # when_str = "03-10-201800:00:00"
        when = when or pd.Timestamp.today()
        dt_from = when.normalize().replace(day=1)         # month start
        dt_to = dt_from + pd.tseries.offsets.MonthEnd(1)  + pd.tseries.offsets.Day(1) - pd.offsets.Second(1)  # month end
        when_str = when.strftime("%d-%m-%Y00:00:00")
        mask_url_consumo_facturado = "/consumidores/rest/consumoNew" \
                                     "/obtenerDatosConsumoFacturado/numFactura/null/fechaDesde/{desde}/fechaHasta/{hasta}/"
        mask_url_consumo = "/consumidores/rest/consumoNew/" \
                           "obtenerDatosConsumo/fechaInicio/{fechainicio}/colectivo/USU/frecuencia/{frecuencia}/" \
                           "acumular/{acumular}/"
        url_consumo = mask_url_consumo.format(fechainicio=when_str, frecuencia=frecuencia, acumular=acumular)
        url_consumo_facturado = mask_url_consumo_facturado.format(
            desde=dt_from.strftime("%d-%m-%Y00:00:00"),
            hasta=dt_to.strftime("%d-%m-%Y23:59:59"),
        )
        urls = {"Consumo": url_consumo, "ConsumoFacturado": url_consumo_facturado}
        df = pd.DataFrame(columns=urls.keys())

        for column, url in urls.items():
            js = self.do_request("get", url + "?_{timestamp}".format(
                timestamp=get_timestamp()))
            if js:
                fecha_dato = datetime.strptime(js['fechaPeriodo'], "%d-%m-%Y%H:%M:%S")
                fecha_dato = pd.Timestamp(fecha_dato).replace(hour=0).tz_localize(LOCAL_TZ)
                for dt in js['y']['data']:
                    for index, data_point in enumerate(dt):
                        # logger.info(f"{index=} {data_point=}")
                        if data_point:
                            df.loc[fecha_dato.value, column] = data_point['valor']
                        fecha_dato += pd.to_timedelta(1, unit='h')
        retval = list()
        for idx_ts, row in df.iterrows():
            not_nan = ~row.isna()
            if not_nan.any():
                keys = list(row.keys()[not_nan])
                values = list(float(f) for f in row.values[not_nan])
                retval.append((_bucket, sensor_name, keys, values, idx_ts))
        return retval

    def _do_login(self) -> tuple:
        """
        Logs in with user and password and returns a tuple bool, str with the true or false of the login and the reason
        :return: True, None if successfully logged in
                False, None if there is any connection trouble
                False, js_response otherwise (can see if there is a need for a captcha, bad password...)
        """
        # raise ValueError("Cannot preform automatic login due to protections")
        json_data = [
            self.USERNAME,
            self.PASSWORD,
            None,
            'Mac OS X 10_15_7',
            'PC',
            'Chrome 120.0.0.0',
            '0',
            '',
            's',
            None,
            None,
        ]

        js, c5 = self.do_request("post", "/consumidores/rest/loginNew/login", json=json_data, return_cookies=True)
        if js is None:
            return False, None
        if "success" not in js:
            if "captcha" in js:
                logger.info("Captcha needed")
                # exit(2)  # Need for a captcha...nothing to do here
            else:
                logger.info(f"Login invalid for unknown reasons: {js}")
            return False, js
        if js["success"] != "true":
            return False, js
        self.JSESSIONID = c5["JSESSIONID"]
        self.save_config()
        logger.info("Log in successful")
        return True, js

    def keep_login(self) -> bool:
        """Does (or keeps) login"""
        keep_ok = self._keep_sesion_opened()
        if keep_ok:
            return True

        for errores_captcha in range(3):
            login_ok, js_login = self._do_login()
            if login_ok:
                logger.info(f"Session opened: {js_login}")
                self._keep_sesion_opened()
                return True
            else:
                if "captcha" in js_login:
                    min_wait = 30
                    logger.warning(f"Captcha needed, waiting {min_wait} min: {js_login}")
                    time.sleep(min_wait * 60)  # wait 30 min...
                else:
                    min_wait = 5
                    logger.warning(f"Logg in failed for unknown reason, waiting {min_wait} min: {js_login}")
                    time.sleep(min_wait * 60)  # wait 5 min...

        logger.critical("Could not log in")
        exit(-1)

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
    sensor_meter = _sensors['sensor_1h']
    date = ongtsdb_client.get_lasttimestamp(_bucket, sensor_meter)
    if not date:
        date = pd.Timestamp.now(tz=LOCAL_TZ).normalize() - pd.tseries.offsets.YearBegin(4)  # 4 year's history
    else:
        # Convert from timestamp to date + 3600s
        date = pd.Timestamp.utcfromtimestamp(date).tz_convert("UTC").astimezone(LOCAL_TZ) + \
               pd.tseries.offsets.Hour(1)
    now = pd.Timestamp.now(tz=LOCAL_TZ).normalize()
    month_start = now.replace(day=1)
    if now.minute < 2 and now.hour < 4 or True:
        for when in pd.date_range(min(date, month_start),
                                  pd.Timestamp.now(tz=LOCAL_TZ) + pd.offsets.MonthEnd(1), freq="MS"):
            sequence = session.read_monthly_history(sensor_meter, when)
            if sequence:
                ongtsdb_client.write(sequence)
                logger.info(f"Historical data for month {when} saved")
    return True


def read_current_meter_reading(session: IberdrolaSession, ongtsdb_client: OngTsdbClient, retries: int = 4) -> bool:
    """
    Reads current meter reading from i-de meter and stores into ong_tsdb database. If data could not be read
    then retries after 30s of sleep
    :param session: an already opened IberdrolaSession object , from where data will be read
    :param ongtsdb_client: an already initialized OngTsdbClient, where data will be writen
    :param retries: number of retries if data is invalid
    :return: True if data could be read and write, false otherwise
    """
    for retry_meter in range(retries):
        attempt = retry_meter + 1
        now_ts = pd.Timestamp.now(tz=LOCAL_TZ).value
        with OngTimer(msg=f"Reading meter {attempt=}", logger=logger, log_level=logging.INFO):
            res = session.read_meter()
        if isinstance(res, dict):
            logger.info(f"{attempt=}: Meter read from i-de meter: {res}")
            # valor = float(res.get('valMagnitud', -1))
            meter_reading = float(res.get('valLecturaContador', -1))
            sensor_meter = _sensors['sensor_1h']
            if meter_reading > 0:
                if ongtsdb_client.write(
                        [f"{_bucket},sensor={sensor_meter} LecturaContador={meter_reading} {now_ts}"]):
                    # Write also in the 15 min sensor (to better know when it was written)
                    ongtsdb_client.write(
                        [f"{_bucket},sensor={_sensors['sensor_15m']} LecturaContador={meter_reading} {now_ts}"])
                    logger.info(f"{attempt=}: Data writen to ong_tsdb database ok")
                    return True
            else:
                logger.error(f"{attempt=}: Could not write i-de meter data, dictionary data invalid")
        else:
            logger.error(f"{attempt=}: Invalid data read from i-de meter: {res}")
        session.keep_login()
        time.sleep((attempt + 1) * 30)  # increase sleep time each retry, 30 additional seconds
    return False


if __name__ == "__main__":
    def keep_login_job():
        ongtsdb_client = OngTsdbClient(url=config('url'), token=config('admin_token'), validate_server_version=False)
        ongtsdb_client.create_db(_bucket)
        for sensor in _sensors.values():
            ongtsdb_client.create_sensor(_bucket, sensor, sensor.split("_")[1], metrics=list(),
                                         read_key=config('read_token'), write_key=config('write_token'))
        session = IberdrolaSession()
        login_ok = session.keep_login()
        logger.info(f"Login ok: {login_ok}")

    def historical_job():
        ongtsdb_client = OngTsdbClient(url=config('url'), token=config('admin_token'), validate_server_version=False)
        ongtsdb_client.create_db(_bucket)
        for sensor in _sensors.values():
            ongtsdb_client.create_sensor(_bucket, sensor, sensor.split("_")[1], metrics=list(),
                                         read_key=config('read_token'), write_key=config('write_token'))
        session = IberdrolaSession()
        login_ok = session.keep_login()
        read_historical_meter_reading(session, ongtsdb_client)
        logger.info(f"Historical data read")

    schedule.every(4).minutes.do(keep_login_job)
    schedule.every(6).hours.do(historical_job)
    keep_login_job()
    historical_job()
    while True:
        schedule.run_pending()
        time.sleep(1)

    exit(0)

    start_ts = pd.Timestamp.now()
    while True:
        now = pd.Timestamp.now()
        if (now - start_ts).seconds > 60 * 60 * 5:      # Give up after 5 hours
            logger.error(f"Started at {start_ts}, cannot connect after 5h, giving up.")
            break
        login_ok = session.keep_login()

        if now.minute < 15 or is_debugging():
            read_historical_meter_reading(session, ongtsdb_client)
        if read_current_meter_reading(session, ongtsdb_client):
            notify()
            break       # Exit while loop on successful read
        time.sleep(SECONDS_SLEEP)
        logger.info(f"Retrying after {SECONDS_SLEEP}")
