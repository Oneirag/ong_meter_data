## finds ip of mirubee and smappee
from ong_meter_data import http, logger


masks = {
    "mirubee": "http://{ip}/index.html",
    "smappe": "http://{ip}/smappee.html"
}
retval = {}


for adr in range(38, 50):
    if len(retval) == len(masks):
        break
    ip = f"192.168.1.{adr}"
    logger.info(f"Testing {ip}")
    for device, mask in masks.items():
        if device in retval:
            continue
        url = mask.format(ip=ip)
        try:
            # resp = http.urlopen("get", url, retries=1, timeout=2)
            resp = http.urlopen("get", mask.format(ip=ip), retries=1)
        except:
            pass
        else:
            if resp.status == "200":
                print(device, resp)
                retval[device] = resp
            else:
                logger.info(f"Device in {ip} did nor respond to {url}")
print(retval)