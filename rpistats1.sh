#!/bin/bash
echo "Server: SeamNet" > ~/git/RaspberryPi-Surveillance-System/rpistats.txt
# echo

# uptime
# uptime -p|sed "s/up/Uptime:/g"
echo Uptime: $(uptime -p) >> ~/git/RaspberryPi-Surveillance-System/rpistats.txt
# echo

# load
# cat /proc/loadavg| awk '{print "Load: "$1 " " $2 " " $3}'|tr -d ','
echo $(cat /proc/loadavg| awk '{print "Load: "$1 " " $2 " " $3}'|tr -d ',') >> ~/git/RaspberryPi-Surveillance-System/rpistats.txt
# echo

# cpu temperature
cputemp=$(cat /sys/class/thermal/thermal_zone0/temp | tr -cd '[[:digit:]]')

cpuTemp0=$(/usr/bin/vcgencmd measure_temp)
cpuTemp0=${cpuTemp0//\'C/}
cpuTemp0=${cpuTemp0//temp=/}

echo CPU temperature: $cpuTemp0 >> ~/git/RaspberryPi-Surveillance-System/rpistats.txt
# echo CPU temp: ${cputemp:0:2}"."${cputemp:2:1}$'\u00b0'C

# gpu temperature
gputemp=$(vcgencmd measure_temp | tr -cd '[[:digit:]]')
# echo GPU temp: ${gputemp:0:2}"."${gputemp:2:1}$'\u00b0'C
# echo

# swap used
echo "Swap used:" $(free -m|grep -i swap|awk '{ print $3 }'|tr -d '\n')MB >> ~/git/RaspberryPi-Surveillance-System/rpistats.txt
# echo

# processes
echo "Processes:" $(ps -ef|wc -l) >> ~/git/RaspberryPi-Surveillance-System/rpistats.txt
# echo

# network usage
echo $(/usr/sbin/ifconfig eth0|grep 'X packets'|sed 's/^ *//'|awk '{print $1 " " $2 ": "$6 $7}'|tr -d '('|tr -d ')')  >> ~/git/RaspberryPi-Surveillance-System/rpistats.txt
