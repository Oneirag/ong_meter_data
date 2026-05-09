# Ong_meter_data
Functions to read data from several sources

## Requirements

* Python 3.11 or higher
* Dependencies defined in `requirements.txt`
* Configuration loaded from `~/.config/ongpi/ong_config.yaml`
* TSDB client settings use `url`, `admin_token`, `read_token`, and `write_token`

Install dependencies:

```bash
pip install -r requirements.txt
```

Or install the package locally:

```bash
pip install -e .
```

## Data from I-DE (former Iberdrola Distribución)

To read data from I-DE you need:

* Username (`i-de_usr`)
* Password (`i-de_pwd`)
* Metering point number (CUPS) from your bill

The project uses the cookie file `~/.config/ongpi/i-de_cookies.json` to avoid captchas and keep the session alive.

Example cookie file:

```json
{
    "JSESSIONID": "12348THfXX5KzwMknn5oF9f18DA:1f6c1hJk9",
    "bm_sz": "1234FECD49F900DEBACFBB5F3C8D0E0F...",
    "user_agent": "Mozilla/5.0 ..."
    "other_cookies": "other value..."
}
```

### Read historical hourly data

Run:

```bash
python -m ong_meter_data.update_i_de
```

Reads historical data once and the re-reads it every day at 16:42 Madrid time.

### Automatically update cookies with Playwright

Run:

```bash
python -m ong_meter_data.update_cookies_playwright
```

Additional requirements for this option:

* Graphical interface available
* `playwright` installed
* Browsers downloaded with `playwright install`
* `i-de_usr` and `i-de_pwd` configured in `~/.config/ongpi/ong_config.yaml`

Example config:

```yaml
log: {}
ong_meter_data:
  i-de_usr: your_user
  i-de_pwd: your_password
```

If the website requests SMS MFA, the script will wait for the code when running in an interactive session with `I_DE_INTERACTIVE` enabled.

## PVPC Prices

Uses `ong_esios` available at https://github.com/Oneirag/ong_esios.

Run:

```bash
python -m ong_meter_data.update_pvpc
```

This task downloads PVPC data from the ESIOS API and writes it into the configured TSDB database.

## Real-time meter data

Data can be read from Mirubee, Smappee, or Tuya devices.

Run:

```bash
python -m ong_meter_data.update_meter
```

Currently the script uses `seeedstudio` by default; other devices are present but commented out in the code.

## Troubleshooting

* If you use Mirubee or Smappee devices, add their hostnames and IP addresses to `/etc/hosts`.
* If the I-DE session expires, regenerate cookies with `python -m ong_meter_data.update_cookies_playwright`.
* Make sure `~/.config/ongpi/ong_config.yaml` contains the required settings.

