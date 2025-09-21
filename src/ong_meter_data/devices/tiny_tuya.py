import time

from tinytuya.Contrib.WiFiDualMeterDevice import WiFiDualMeterDevice
from tuya_connector import TuyaOpenAPI

from ong_meter_data import logger
from ong_meter_data.devices.base import MeteringDevice


class MyWifiDualMeterDevice(WiFiDualMeterDevice):
    """A version of WifiDualMeterDevice with the right mapping of data, as my device has a bit different settings"""
    # My device has different settings as the standard
    # Power A is 111
    # Power B is 106
    # Frequency is 102
    # Voltage is 101
    DPS_POWER_A = "111"
    DPS_POWER_B = "106"
    DPS_FREQ = "102"
    DPS_VOLTAGE = "101"
    DPS_CURRENT_A = "110"
    DPS_CURRENT_B = "105"

    def __init__(
            self, dev_id, address=None, local_key="", dev_type="default", connection_timeout=5, version=3.1,
            persist=False, cid=None, node_id=None, parent=None, connection_retry_limit=5, connection_retry_delay=5,
            port=6668
    ):
        persist = True  # Make connection persistent by default
        super().__init__(dev_id, address, local_key, dev_type, connection_timeout, version, persist, cid, node_id,
                         parent, connection_retry_limit, connection_retry_delay, port)
        # Scaling is also different than standard. Fix it
        self.dps_data[self.DPS_POWER_A]['scale'] = 10  # Instead of 100
        self.dps_data[self.DPS_POWER_B]['scale'] = 10  # Instead of 100
        self.dps_data[self.DPS_CURRENT_A]['scale'] = 1000  # In Amps (original reading is in mA)
        self.dps_data[self.DPS_CURRENT_B]['scale'] = 1000  # In Amps (original reading is in mA)


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
        self.device = MyWifiDualMeterDevice(
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
        dps = {str(d['dp_id']): d['value'] for d in last_status}

        timestamp = int(last_timestamp * 1e6)
        return dict(dps=dps, timestamp=timestamp)
