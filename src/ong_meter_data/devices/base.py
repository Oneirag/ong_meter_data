import time

import urllib3

from ong_meter_data import http, logger, _bucket, init_ongtsdb_client
from ong_utils import OngTimer

timer = OngTimer(False)


class MeteringDevice(object):

    def __init__(self, name, base_url, circuits: tuple, usr="", pwd=""):
        """
        Inits the class that reads metering device
        :param name: name of the metering device (to use as measurement name in influx)
        :param base_url: base url of the device
        :param circuits: list of circuits names in the same order as they appear in the meter
        :param usr: user name (basic http_auth) for read url "url", can be empty if no basic auth will be used
        :param pwd: user name (basic http_auth)
        """
        assert (name != "")
        self.name = name
        self.timestamp_ns = None
        self.data = None
        self.base_url = base_url[:-1] if base_url.endswith("/") else base_url
        self.url = None
        if usr:
            self.headers = urllib3.util.make_headers(basic_auth=usr + ":" + pwd)
        else:
            self.headers = dict()
        self.url_logon = None
        self.http = http
        self.parse_dict = None
        self.circuits = circuits
        self.timestamp_ns = None

    def read_write_meter(self):
        """Reads meter data and then writes it to db"""
        self.read_meter_url()
        self.write_meter_db()

    def read_meter_url(self):
        """Reads from meter device integrated web server and parses data into self.data """
        resp = self.__read_url()
        if resp is None:
            logger.info(f"Could not read {self.name}")
            return
        else:
            body = resp.data
            timer.tic("processing answer")
            values = dict()
            for k, regex in self.parse_dict.items():
                a = regex.findall(body)
                # print(a)
                values[k] = [float(v) for v in a]
            self.data = values
            timer.toc("processing answer")
            self.timestamp_ns = time.time_ns()
            logger.debug("Leido " + self.name + " from url " + self.url)
            logger.debug(body)
            logger.debug(self.data)


    def write_meter_db(self):
        """Write last data read into influx db"""
        ongtsdb_client = init_ongtsdb_client()
        logger.debug("Writing in Database " + self.name)
        if self.data is None or len(self.data) == 0:
            logger.debug(f"No data written for {self.name}")
            return
        try:
            sequence = list()
            for metric, measurements in self.data.items():
                measurements_list = [f"{circuit}.{metric}={datapoint}" for circuit, datapoint
                                     in zip(self.circuits, measurements)]
                if measurements_list:
                    point = "{name},circuit={circuit} {measurements} {ts}".format(
                        name=_bucket, circuit=self.name, measurements=",".join(measurements_list), ts=self.timestamp_ns)
                    sequence.append(point)
            if sequence:
                retval = ongtsdb_client.write(sequence)
                if not retval:
                    logger.info(f"Error writing {self.name} to db")
        except Exception as e:
            logger.info(f"Error writing {self.name}")
            logger.info(e)

    def logon(self):
        """Performs logon on self.url_logon address. Returns true on success"""
        if not self.url_logon:
            return False  # If no logon address, return false
        H = {"Content-type": "application/json"}
        headers = dict(**H, **self.headers)
        r = self.http.urlopen('POST', self.url_logon, headers=headers, body="admin")
        if r.status == 200:
            logger.info("Logged in")
            return True
        else:
            logger.error("HTTP Error {code} reading {url}".format(
                code=r.status, url=self.url_logon))
            return False

    def __read_url(self, max_retries=2, timeout_secs=0.5):
        """Reads url. Retries 3 times and returns None in case of error and request object otherwise"""
        for _ in range(max_retries):
            response = None
            try:
                response = self.http.urlopen('GET', self.url, timeout=timeout_secs, headers=self.headers)
            except Exception as e:
                logger.debug(f"Error in read_url for {self.name}: {e}")
                continue
            if response.status != 200:
                logger.debug("HTTP Error {code} reading {url}".format(
                    code=response.status, url=self.url))
                continue
            else:
                body = response.data
            if body.startswith(b"{\"error") & (self.url_logon != ""):
                logger.info("Logon required")
                self.logon()
                continue
            else:
                logger.debug(f"Data read_url OK for {self.name} in url {self.url}")
                return response
        logger.info(f"Could not read data in read_url for {self.name} in url {self.url}")
        return  # Tried max_retries and no luck
