#!/usr/bin/python
import time
import re

from ong_meter_data import logger, config, http
import urllib3
import threading
from ong_tsdb.client import OngTsdbClient
from ong_utils import OngTimer

timer = OngTimer(False)


def combine_url(base, endpoint) -> str:
    """Combines a base_url and an endpoint, avoiding double // that happens when base ends ad endpoint starts by / """
    if base.endswith("/") and endpoint.startswith("/"):
        return base + endpoint[1:]
    else:
        return base + endpoint


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
                ongtsdb_client.write(sequence)
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


class MirubeeDevice(MeteringDevice):
    """Configuration for a mirubee device. Sample data:
    <smartplug><version>0.8.1c</version><type>PROLIFICS-PL8331</type><pm><volts>234.2000</volts><current>2.7000</current><freq>0.0000</freq><power>588.4000</power><power_factor>0.0000</power_factor><reactive_power>237.1000</reactive_power><energy>12776.0781</energy><vrms>234.2000</vrms><irms>0.0000</irms><watt>0.0000</watt><var>0.0000</var><kwh>573.0120</kwh></pm><load><state>OFF</state></load><usersetup><remote_ip>wattius.mirubee.com</remote_ip><remote_port>8500</remote_port><time_stamp>1</time_stamp><report_time>1</report_time></usersetup><registerdev><devid>PTC4000020F85EAD7F0F</devid></registerdev><protectdev><ocp_type>USA</ocp_type><uvp_type>reserve</uvp_type></protectdev><sdk_version>2.5.1.b3.006</sdk_version></smartplug>
    """

    def __init__(self, name, base_url, circuits: tuple, usr="", pwd=""):
        super().__init__(name, base_url, circuits, usr, pwd)
        self.url = combine_url(self.base_url, "/gainspan/profile/smartplug")
        mirubee_re = {
            "active_power": re.compile(b"<(?:power|watt)>([^<]+)"),
            "voltage": re.compile(b"<(?:volts|vrms)>([^<]+)"),
            "reactive_power": re.compile(b"<(?:reactive_power|var)>([^<]+)"),
            # "current": re.compile(b"<(?:current|irms)>([^<]+)")
        }
        self.parse_dict = mirubee_re


class SmappeeDevice(MeteringDevice):
    """Configuration of a smapee device. Sample data:
    {"report":"Instantaneous values:<BR>voltage=233.0 Vrms<BR>FFTComponents:<BR>Phase 1:<BR>\\tcurrent=2.427 A, activePower=495.737 W, reactivePower=272.569 var, apparentPower=565.729 VA, cosfi=87, quadrant=0, phaseshift=0.0, phaseDiff=0.0<BR>\\tFFTComponents:<BR>Phase 2:<BR>\\tcurrent=2.129 A, activePower=481.152 W, reactivePower=121.657 var, apparentPower=496.294 VA, cosfi=96, quadrant=0, phaseshift=0.0, phaseDiff=0.0<BR>\\tFFTComponents:<BR>Phase 3:<BR>\\tcurrent=0.265 A, activePower=30.604 W, reactivePower=53.883 var, apparentPower=61.968 VA, cosfi=48, quadrant=0, phaseshift=0.0, phaseDiff=0.0<BR>\\tFFTComponents:<BR><BR><BR>Phase 1, peak active power 9067.184 W at 19/01/2018 11:39:30<BR>Phase 2, peak active power 2809.924 W at 25/02/2019 06:09:25<BR>Phase 3, peak active power 4022.822 W at 14/12/2020 12:26:30<BR>active energy RMS per phase mapping combination<BR>phase mapping -1=0.0 kWh [* -1/3]<BR>phase mapping -1=0.0 kWh [ -1/3]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR><BR>active energy RMS (solar) per phase mapping combination<BR>phase mapping -1=0.0 kWh [* -1/3]<BR>phase mapping -1=0.0 kWh [ -1/3]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR><BR>"}
    """

    def __init__(self, name, base_url, circuits: tuple, usr="", pwd=""):
        super().__init__(name, base_url, circuits, usr, pwd)
        self.url = combine_url(self.base_url, "/gateway/apipublic/reportInstantaneousValues")
        self.url_logon = combine_url(base_url, "/gateway/apipublic/logon")
        smappee_re = {
            "active_power": re.compile(b" activePower=(\S+)"),
            "voltage": re.compile(b"voltage=(\S+)"),
            "reactive_power": re.compile(b" reactivePower=(\S+)"),
            # "current": re.compile(b"tcurrent=(\S+)"),
        }
        self.parse_dict = smappee_re


meters = dict()
meters['mirubee'] = MirubeeDevice('mirubee', base_url=config("mirubee_base_url"),
                                  circuits=('general', 'lights'),
                                  usr=config("meter_user"), pwd=config("meter_pwd")
                                  )
meters['smapee'] = SmappeeDevice('smappee', base_url=config("smappee_base_url"),
                                  circuits=('general', 'lavadora', 'nevera'),
                                  usr=config("meter_user"), pwd=config("meter_pwd")
                                  )

# Generate database and sensors, if needed
_bucket = config('bucket')
ongtsdb_client = OngTsdbClient(url=config('url'), token=config('admin_token'))
ongtsdb_client.create_db(_bucket)
for sensor in meters.keys():
    ongtsdb_client.create_sensor(_bucket, sensor, "1s", metrics=list(),
                                 read_key=config('read_token'), write_key=config('write_token'))

while True:
    start_t = time.time()
    #   if True:
    # threads = [threading.Thread(target=M.read_write_meter) for M in meters.values()]
    # for thread in threads:
    #     thread.start()
    # for thread in threads:
    #     thread.join()

    for M in meters.values():
        try:
            M.read_write_meter()
        except Exception as e:
            logger.error(e)
    logger.debug("Elapsed Time: %s" % (time.time() - start_t))
    time.sleep(max(0.0, start_t + 1 - time.time()))
