import re

from ong_meter_data.update_meter import combine_url
from ong_meter_data.devices.base import MeteringDevice


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
