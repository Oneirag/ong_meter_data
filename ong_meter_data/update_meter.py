#!/usr/bin/python
import time
import re

from ong_meter_data import logger, config, http
import urllib3
import threading
from ong_tsdb.client import OngTsdbClient
from ong_utils import OngTimer
from tinytuya.Contrib.WiFiDualMeterDevice import WiFiDualMeterDevice
from tuya_connector import TuyaOpenAPI

from ong_meter_data.update_i_de import SECONDS_SLEEP

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
        
        
class TinyTuyaDevice(MeteringDevice):
    """Configuration of a tinytuya device. Sample data:
    {"dps":{"1":false,"2":0,"3":0,"4":0,"5":0,"6":0,"7":0,"8":0,"9":0,"10":0,"11":0,"12":0,"13":0,"14":0,"15":0,"16":0}}
    """

    def __init__(self, name, base_url, circuits: tuple, usr="", pwd=""):
        """
        Inits the class that reads metering device
        :param name: name of the metering device (to use as measurement name in influx)
        :param base_url: base url of the device (it will be the IP of the device. Can be "auto" for auto discovery)
        :param circuits: list of circuits names in the same order as they appear in the meter
        :param usr: it will be the ID of the device
        :param pwd: it will be the local key of the device
        """
        super().__init__(name, base_url, circuits, usr, pwd)
        self.device = WiFiDualMeterDevice(
            dev_id=usr,
            local_key=pwd,
            address=base_url,
            version=3.4 
        )
        self.last_status = None
        if pwd:     # If no password is supplied then no need to test connection as it will be child class
            data = self.device.status()
            if data:
                logger.debug(f"Connected to device {self.name} and received {data=}")
            else:
                logger.error("Could not connect to device " + self.name)


    def get_status(self) -> dict:
        """Returns current device status. it is a dict with two keys, dps and timestamp, like {"dps: {'1': 0, '101': 542.3...}"""
        #  DP_REFRESH: 18, // Request refresh of DPS  UPDATEDPS / LAN_QUERY_DP
        # payload = wdm.generate_payload(command=18, data=[4, 5, 6, 18, 19, 20])
        # print(wdm.receive())
        # print(wdm.send(payload))
        # res = wdm.receive()
        # print(res)
        self.device.updatedps([4, 5, 6, 18, 19, 20])
        # from time import sleep
        # sleep(5)
        status = self.device.status()
        status['timestamp'] = time.time_ns()
        return status

    def read_meter_url(self):
        status = self.get_status()
        if status != self.last_status:
            logger.debug(f"Status changed for {self.name} from {self.last_status} to {status}")
            self.last_status = status
        self.data = dict()
        # There are 2 circuits, first circuit is general, second is lavadora
        circuit_dict = dict(zip("ab", self.circuits))
        
        def get_values_circuits(attr, status_data=None):
            """Devuelve una lista de valores para cada circuito"""
            retval = list()
            for clamp, circuit in circuit_dict.items():
                if attr.endswith("_"):
                    dps_code = f"{attr}{clamp.upper()}"
                else:
                    dps_code = attr
                dict_values = self.device.get_value(dps_code=getattr(self.device, dps_code), status_data=status_data)
                numeric_value = next(iter(dict_values.values()))
                retval.append(numeric_value)
            return retval
        
        self.timestamp_ns = status['timestamp']
        self.data['active_power'] = get_values_circuits("DPS_POWER_", status_data=status)
        self.data['current'] = get_values_circuits("DPS_CURRENT_", status_data=status)
        self.data['voltage'] = get_values_circuits("DPS_VOLTAGE", status_data=status)
        logger.debug("Leido " + self.name)
        
class TuyaCloudDevice(TinyTuyaDevice):
    def __init__(self, name, cloud_api_base_url, circuits: tuple, access_id, access_key, device_id):
        """
        Inits the class that reads metering device
        :param name: name of the metering device (to use as measurement name in influx)
        :param cloud_api_base_url: base url for the tuya cloud
        :param circuits: list of circuits names in the same order as they appear in the meter
        :param access_id: application access_id for the cloud
        :param access_key: application access_key for the cloud
        :param device_id: device_id to be read from the cloud
        """
        super().__init__(name, "", circuits, usr=device_id)
        # Init OpenAPI and connect
        self.openapi = TuyaOpenAPI(cloud_api_base_url, access_id, access_key)
        res = self.openapi.connect()
        if res['success']:
            logger.info("Connected to cloud")
        else:
            raise ConnectionError("Could not connect to cloud api. Review cloud_api_base_url, access_id and access_key")
        self.DEVICE_ID = device_id

        # Call any API from Tuya
        response = self.openapi.get("/v1.0/statistics-datas-survey", dict())
        print(response)

        print(response := self.openapi.get(f"/v1.0/devices/datas-survey", dict()))
        # print(response := self.openapi.get(f"/v1.0/devices", dict(page_no=0, page_size=10)))
        print(response := self.openapi.get(f"/v1.0/devices/{self.DEVICE_ID}", dict()))

        # Gets MAC address
        self.openapi.get("/v1.0/devices/factory-infos", dict(device_ids=self.DEVICE_ID))

        # logs_types=",".join(map(str, range(1, 11)))
        # start_t = int(datetime.datetime.today().replace(hour=1).timestamp()*1000)
        # end_t = int(datetime.datetime.today().timestamp()*1000)
        # print(response := openapi.get(f"/v1.0/devices/{DEVICE_ID}/logs", dict(type=logs_types,
        #                               start_time=start_t, end_time=end_t, size=100)))


    def get_status(self) -> dict:
        last_data = self.openapi.get(f"/v2.0/cloud/thing/{self.DEVICE_ID}/shadow/properties", dict())
        last_status = last_data['result']['properties']
        timestamps = {str(d['dp_id']): d['time'] for d in last_status}
        last_timestamp = max(timestamps.values())
        # Power A is 111
        # Power B is 106
        # Frequency is 102
        # Voltage is 101
        dps = {str(d['dp_id']): d['value'] for d in last_status}
        # My device has different settings as the standard
        self.device.DPS_POWER_A = "111"
        self.device.DPS_POWER_B = "106"
        self.device.DPS_FREQ = "102"
        self.device.DPS_VOLTAGE = "101"
        self.device.DPS_CURRENT_A = "110"
        self.device.DPS_CURRENT_B = "105"

        self.device.dps_data[self.device.DPS_POWER_A]['scale'] = 10     # Instead of 100
        self.device.dps_data[self.device.DPS_POWER_B]['scale'] = 10     # Instead of 100
        self.device.dps_data[self.device.DPS_CURRENT_A]['scale'] = 1000    # In Amps (original reading is in mA)
        self.device.dps_data[self.device.DPS_CURRENT_B]['scale'] = 1000  # In Amps (original reading is in mA)

        timestamp = int(last_timestamp * 1e6)
        return dict(dps=dps, timestamp=timestamp)


meters = dict()
# meters['mirubee'] = MirubeeDevice('mirubee', base_url="http://mirubee",
#                                   circuits=('general', 'lights'),
#                                   usr=config("meter_user"), pwd=config("meter_pwd")
#                                   )
# meters['smapee'] = SmappeeDevice('smappee', base_url="http://smappee",
#                                   circuits=('general', 'lavadora', 'nevera'),
#                                   usr=config("meter_user"), pwd=config("meter_pwd")
#                                   )
# meters['tinytuya'] = TinyTuyaDevice('tinytuya', base_url=config("tinytuya_wdm_base_url"),
#                                     circuits=('general', 'lavadora'),
#                                     usr=config("tinytuya_wdm_usr"), pwd=config("tinytuya_wdm_pwd")
#                                     )
meters['tinytuya'] = TuyaCloudDevice('tinytuya', cloud_api_base_url=config("tuyacloud_api_endoint"),
                                    circuits=('general', 'lavadora'),
                                    access_id=config("tuyacloud_access_id"), access_key=config("tuyacloud_access_key"),
                                    device_id=config("tuyacloud_device_id")
                                    )


# Generate database and sensors, if needed
_bucket = config('bucket')
ongtsdb_client = OngTsdbClient(url=config('url'), token=config('admin_token'), validate_server_version=False)
ongtsdb_client.create_db(_bucket)
for sensor in meters.keys():
    # ongtsdb_client.delete_sensor(_bucket, sensor)
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
    SECONDS_SLEEP = 10      # To avoid problems with cloud (previously I used every second)
    time.sleep(max(0.0, start_t + SECONDS_SLEEP - time.time()))
