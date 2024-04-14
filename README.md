## Flash Tasmota On Sonoff Devices
This script helps to flash the latest tasmota-lite on any Sonoff device that supports [DIY Mode](http://developers.sonoff.tech/sonoff-diy-mode-api-protocol.html)
How to use:
1. Put the device into DIY mode. Usually this means long-pressing (5 seconds) the button immediately after power up (*not before power up*)
2. Connect to the ITEAD-XXXX AP. The password is ```12345678```
3. Navigate to http://10.10.7.1/
4. Configure the device to connect to your WiFi AP
5. Now run the script in this repository. It should detect the device and start flashing it immediately.

It takes quite a while to finish flashing. Just wait till the script stops printing message on the console, and then give it 3 or 4 minutes more. Once it's done, you should see a new ```tasmota-XXXX``` AP show up. Sometimes you need to power cycle the device before it shows up. Then just connect to the AP and configure the device using the normal Tasmota steps.

Note:
This script always flashes the tasmota-lite firmware. If you need the full firmware, you can flash it again using the Tasmota interface once tasmota-lite is installed and running.
