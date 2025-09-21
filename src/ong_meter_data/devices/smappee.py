import re

from ong_meter_data.update_meter import combine_url
from ong_meter_data.devices.base import MeteringDevice


class SmappeeDevice(MeteringDevice):
    """Configuration of a smapee device. Sample data:
    {"report":"Instantaneous values:<BR>voltage=233.0 Vrms<BR>FFTComponents:<BR>Phase 1:<BR>\\tcurrent=2.427 A, activePower=495.737 W, reactivePower=272.569 var, apparentPower=565.729 VA, cosfi=87, quadrant=0, phaseshift=0.0, phaseDiff=0.0<BR>\\tFFTComponents:<BR>Phase 2:<BR>\\tcurrent=2.129 A, activePower=481.152 W, reactivePower=121.657 var, apparentPower=496.294 VA, cosfi=96, quadrant=0, phaseshift=0.0, phaseDiff=0.0<BR>\\tFFTComponents:<BR>Phase 3:<BR>\\tcurrent=0.265 A, activePower=30.604 W, reactivePower=53.883 var, apparentPower=61.968 VA, cosfi=48, quadrant=0, phaseshift=0.0, phaseDiff=0.0<BR>\\tFFTComponents:<BR><BR><BR>Phase 1, peak active power 9067.184 W at 19/01/2018 11:39:30<BR>Phase 2, peak active power 2809.924 W at 25/02/2019 06:09:25<BR>Phase 3, peak active power 4022.822 W at 14/12/2020 12:26:30<BR>active energy RMS per phase mapping combination<BR>phase mapping -1=0.0 kWh [* -1/3]<BR>phase mapping -1=0.0 kWh [ -1/3]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR><BR>active energy RMS (solar) per phase mapping combination<BR>phase mapping -1=0.0 kWh [* -1/3]<BR>phase mapping -1=0.0 kWh [ -1/3]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR>phase mapping -1=0.0 kWh [ 1/1]<BR><BR>"}
    """

    def __init__(self, name, base_url, circuits: tuple, usr="", pwd=""):
        super().__init__(name, base_url, circuits, usr, pwd)
        self.url = combine_url(self.base_url, "/gateway/apipublic/reportInstantaneousValues")
        self.url_logon = combine_url(base_url, "/gateway/apipublic/logon")
        smappee_re = {
            "active_power": re.compile(br" activePower=(\S+)"),
            "voltage": re.compile(br"voltage=(\S+)"),
            "reactive_power": re.compile(br" reactivePower=(\S+)"),
            # "current": re.compile(br"tcurrent=(\S+)"),
        }
        self.parse_dict = smappee_re
