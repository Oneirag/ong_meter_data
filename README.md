# Ong_meter_data
Functions to read data from several sources

## Data read from I-DE (former Iberdrola Distribucion)
First, you'll need a user, password and number of the metering point (CUPS) , all that 
information is available in any spanish power invoice.

You can register in www.i-de.es, only if in i-de distribution area. Login in the page and get the `JSESSIONID` and  `bm_sz` cookies,
from the request either to `mantenerSesion` or `eks` endpoints, 
and store it in the file `~/.config/ongpi/i-de_cookies.json`. The file should look like this:
```json
{
    "JSESSIONID": "12348THfXX5KzwMknn5oF9f18DA:1f6c1hJk9",
    "bm_sz": "1234FECD49F900DEBACFBB5F3C8D0E0F~YAAQeqYXAvViZ32VJQAAVvK0gBuRYPcUMMlM8t5wuVx00ybXukF+TD881VzYiDybLaHPC5fcPQhR/Lr2Jr3KrahqYO4tNR879jyHnYzdbe9sehIkat9HF2oGqVY4eJW5wbjyNZEHpImNHflb0m878Ic5pJlImQs5DrtecjNBWHy2aDF16WqClOg1l9tPQB6/Ulu+SabXZLA8KEu41xN0sanZPQrhK6A1/XQKbj5dInzcjV3OAQjQg1FKuIUxnzAwuFURzzV7dMTzaDjol/9BXQvXxlLh3Fp9ccwPpCofH8uzCzApY5mnr9FQ2Ctu1FoX325M6rLDPoQaDJYIre4Wq7uh9dlMs0OeK999uUNfatu9C3CuPrqVYtWAybIQqAmu9DDAFT1tSM6F0aW79xxpz99qQDSwxL49oRt+IzYufu7M9azbiLoE1FMBRTBZR171~3425602~3496608"
}
```

The program must be kept opened so session is not closed. It reads historical hourly data every 6 hours.
It could read also real time data, but code is commented out as it cannot be read more than 20 times per day
so Iberdrola does not ban you!

Execute `python -m ong_meter_data.update_i_de`

### Script for automatically login to i-de website and get cookies

Execute `python -m ong_meter_data.update_cookies_playwright` to use playwright to log in to i-de site and create the
cookies file automatically. It needs:
* A graphical interface
* Install playwright (with `pip install playwright`)
* Download browsers (with `playwright download`)
* Set up username and password in the `i-de_usr` and `i-de_pwd` keys of the config file (located in `~/.config/ongpi/ong_config.yaml`) under the section `ong_meter_data`.
An example of the config file would be:
```yaml
log: {}
ong_meter_data:
  i-de_usr: your_user
  i-de_pwd: your_password
```

## PVPC prices
Using `ong_esios` availabe [here](https://github.com/Oneirag/ong_esios)

Execute `python -m ong_meter_data.update_pvpc`

## Real time (every second) meter information
From mirubee, smappe or tuya device

Execute `python -m ong_meter_data.update_meter`

## Troubleshooting

Needs two servers (mirubee and smappee) to be defined in `etc/hosts` file with the correct ip addresses
