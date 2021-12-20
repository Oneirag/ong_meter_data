### Ong_meter_data
Functions to read data from:

## Data read from I-DE (former Iberdrola Distribucion)
First, you'll need a user (to be read in `config("i-de_usr")`), password (`config("i-de_pwd")`) and number of the metering point (CUPS, `config("cups")`) , all that 
information is available in any spanish power invoice.

You can register in www.i-de.es, only if in i-de distribution area. 

Once setup, it will read meter data in real time 
(can only be read 6 times per day not be) and also meter readings and meter invoiced readings
Currently hourly readings are read

## PVPC prices
Using ong_esios

## Real time (every second) meter information
From two devices: a mirubee device and a smappee device
