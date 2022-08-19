# Description
This repository is a collection of scripts and tools for my homeserver.

The script in the xiaomi folder lets you read data from a Mi Temperature and Humidity sensor of the second generation via bluetooth and write it to a .csv file.
# How to use the Xiaomi Mi Temperature and Humidity Sensor script
1. Place the sensor in range of your bluetooth device
2. Scan for the sensor with `bluetoothctl scan on`, it should show up like this: `[NEW] Device A4:XX:XX:XX:XX:XX LYWSD03MMC`
3. Copy the template file to the sensor directory, rename it to `get_Mi_Temp_Humid_**.sh`, where ** is the location of the sensor
   1. Change the `name` variable to the desired name/location of the sensor
   2. Copy the MAC address from the output and paste it into the `mac` variable
4. Make the script executable with `chmod +x get_Mi_Temp_Humid_**.sh`
5. Run the python script with `python3 xiaomi/./read_Mi_Temp_Humid.py`
6. (Optional) add a cronjob to run the script every minute with `crontab -e`
   - Example: `*/10 6-23 * * * /usr/bin/python3 /path/to/this/folder/xiaomi/read_Mi_Temp_Humid.py` to run every 10 minutes between 6am and midnight and `*/30 0-5  * * * /usr/bin/python3 /path/to/this/folder/xiaomi/read_Mi_Temp_Humid.py` to run every 30 minutes between midnight and 6am
## Future improvements
- [ ] add influxdb connection to visualize data with grafana
- [x] add battery life to statistics
- [x] add better documentation