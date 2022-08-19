#!/bin/bash

#################################################################################################################################################
#                                                                                                                                               #
#  original script from http://www.d0wn.com/using-bash-and-gatttool-to-get-readings-from-xiaomi-mijia-lywsd03mmc-temperature-humidity-sensor/   #
#                                                                                                                                               #
#  replace sensor name with your desired name and mac with that of your device                                                                  # 
#  rename and copy into sensors folder                                                                                                          #
#################################################################################################################################################

sensor_name="Name"
mac="XX:XX:XX:XX:XX:XX"
bt=$(timeout 15 gatttool -b $mac --char-write-req --handle='0x0038' --value="0100" --listen)
if [ -z "$bt" ]
    then
        echo "The reading failed"
    else
        temphexa=$(echo $bt | awk -F ' ' '{print $12$11}'| tr [:lower:] [:upper:] )
        humhexa=$(echo $bt | awk -F ' ' '{print $13}'| tr [:lower:] [:upper:])
        batthexa=$(echo $bt | awk -F ' ' '{print $14}'| tr [:lower:] [:upper:])
        temperature100=$(echo "ibase=16; $temphexa" | bc)
        humidity=$(echo "ibase=16; $humhexa" | bc)
        temperature=$(echo "scale=2;$temperature100/100" | bc)
        battery1000=$(echo "ibase=16;$batthexa" | bc)
        battery=$(echo "scale=3; $battery1000/1000" | bc)
        sensor_name_idx="$sensor_name"
        echo $sensor_name_idx", "$temperature", "$humidity", "$battery
fi