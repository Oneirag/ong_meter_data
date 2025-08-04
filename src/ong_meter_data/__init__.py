from ong_utils import OngConfig, LOCAL_TZ, create_pool_manager
from pathlib import Path

__version__ = "0.0.5"

_util = OngConfig("ong_meter_data", cfg_filename="ong_config.yml")
logger = _util.logger
config = _util.config
http = create_pool_manager(None)
add_app_config = _util.add_app_config

# Configuration of the cache file
__COOKIES_FILE = "i-de_cookies.json"
config_file_path = Path("~/.config/ongpi/").expanduser()
config_file_path.mkdir(parents=True, exist_ok=True)
JSON_CONFIG_FILE = config_file_path / __COOKIES_FILE