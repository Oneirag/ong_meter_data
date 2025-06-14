# Ong_meter_data
Functions to read data from several sources

## Data read from I-DE (former Iberdrola Distribucion)
First, you'll need a user, password and number of the metering point (CUPS) , all that 
information is available in any spanish power invoice.

You can register in www.i-de.es, only if in i-de distribution area. Login in the page and get the `JSESSIONID` cookie,
and store it in the file `JSESSIONID.txt` in the same folder as `update_i_de.py`

The program must be kept opened so session is not closed. It reads historical hourly data every 6 hours.
It could read also real time data, but code is commented out as it cannot be read more than 20 times per day
so Iberdrola does not ban you!

Execute `python -m ong_meter_data.update_i_de`

## PVPC prices
Using ong_esios

Execute `python -m ong_meter_data.update_pvpc`

## Real time (every second) meter information
From mirubee, smappe or tuya device

Execute `python -m ong_meter_data.update_meter`

## Troubleshooting

Needs two servers (mirubee and smappee) to be defined in `etc/hosts` file with the correct ip addresses
