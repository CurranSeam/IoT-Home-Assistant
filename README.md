# IoT Home Assistant on Raspberry Pi
This project is a stand-alone home assistant system. There are similar full fledged systems that already exist, however, this is for learning and experimenting.

This system consists of a web app and Telegram bot, has a fault tolerant design, and AI/ML integration.

<p align="center">
   <img src="doc/BSR_demo.gif">
</p>

## Services
<details>
<summary>Web interface</summary>
    &emsp;
    - Provides a dashboard to all services. 
</details>

<details>
<summary>Monitoring</summary>
   &emsp;
   - Video <br>
   &emsp;&emsp;
   - Reading from IP camera streams <br>
   &emsp;&emsp;
   - Object detection on camera streams (uses coral TPU for hardware acceleration) <br>
   &emsp;&emsp;
   - Set detection configs (confidence threshold, etc) <br>
   &emsp;
   - Alerting <br>
   &emsp;&emsp;
   - Telegram alerts when people are detected around property <br>
   &emsp;&emsp;
   - SMS alerting as a backup when Telegram is down <br>
   &emsp;&emsp;
   - Alert message settings (on/off, message cooloff time, etc)
</details>

<details>
<summary>Telegram</summary>
   &emsp;
   - Secure identification <br>
   &emsp;&emsp;
   - Authenticates users coming from app via a hashed value <br>
   &emsp;&emsp;
   - Telegram bot only responds to authenticated users <br>
   &emsp;
   - Bot services <br>
   &emsp;&emsp;
   - Trivia (multiple categories and difficulties)<br>
   &emsp;&emsp;
   - Device interfacing (toggling devices, get power consumption stats, etc)<br>
   &emsp;&emsp;
   - Tell jokes <br>
   &emsp;&emsp;
   - Tell facts <br>
</details>

<details>
<summary>IoT</summary>
   &emsp;
   - MQTT broker running on rpi <br>
   &emsp;
   - Sensors <br>
   &emsp;&emsp;
   - Add/remove sensors on LAN for your house <br>
   &emsp;&emsp;
   - Get periodic sensor data (e.g temp/humidity) <br>
   &emsp;
   - Devices <br>
   &emsp;&emsp;
   - Add/remove devices on LAN in your house (devices plugged into a smart plug) <br>
   &emsp;&emsp;
   - Toggle devices via web interface or Telegram <br>
   &emsp;&emsp;
   - Change the telemetry period of device (frequency that data is published) <br>
   &emsp;&emsp;
   - Get periodic device data (stats, etc) <br>
   &emsp;
   - Scenes <br>
   &emsp;&emsp;
   - Set up scenes for daily routines (e.g. morning routine, away from house, etc) <br>
   &emsp;&emsp;
   - Create scene actions for your scene (e.g turning lights on/off at specific times, temperature control, etc) <br>
</details>

<details>
<summary>Scheduling</summary>
   &emsp;
   - Reminders <br>
   &emsp;&emsp;
   - Add/remove reminders <br>
   &emsp;&emsp;
   - Set reminder time, recurrence, description, etc  <br>
   &emsp;&emsp;
   - Telegram bot will notify you of reminders <br>
   &emsp;
   - Morning message <br>
   &emsp;&emsp;
   - Telegram bot sends all active users a morning message with a joke <br>
   &emsp;
   - IoT scheduling <br>
   &emsp;&emsp;
   - Schedules and runs scene actions from scenes. <br>
</details>

<br>
<br>

## Setup TFLite Runtime Environment on Your Device
### Raspberry Pi
Follow the [Raspberry Pi setup guide](https://github.com/EdjeElectronics/TensorFlow-Lite-Object-Detection-on-Android-and-Raspberry-Pi/blob/master/deploy_guides/Raspberry_Pi_Guide.md) to install TFLite Runtime on a Raspberry Pi 3 or 4 and run a TensorFlow Lite model. This guide also shows how to use the Google Coral USB Accelerator to greatly increase the speed of quantized models on the Raspberry Pi.
