# moxaiiot-ciss-to-thingspro
Publish Bosch CISS sensor data to ThingsPro Gateway

### [Bosch CISS sensor information](https://www.bosch-connectivity.com/de/produkte/industrie-4-0/connected-industrial-sensor-solution/downloads/)

### [ThingsPro Gateway information](https://www.moxa.com/en/products/industrial-computing/system-software/thingspro-2)

[1. Getting started](#getting-started)

[2. Requirements](#requirements)

[3. Installation](#installation)

[4. Configuration](#configuration)

[5. Test](#test)

[6. ToDo's](#todos)

*******************************************************************************
<a name="getting-started"></a>
### 1. Getting started 

* Download and Install ThingsPro Gateway software v2.6.x
* Modify sensor.json file with your configuration
* Package the user program in tar.gz format
* Upload the Compressed folder to the ThingsPro Gateway

### How does this User Program integrate into ThingsPro Gateway?
This User Program is the Southbound Interface to Bosch CISS Sensor (USB).

![ThingsPro Gateway Basic Architecture](media/TPG_arch1.png?raw=true "ThingsPro Gatway")


<a name="requirements"></a>
### 2. Requirements
* UC-XXXX with ThingsPro Gateway v2.6.x installed
* Bosch CISS Sensor connected to UC-XXXX USB
* Bosch Python script CissUsbConnectord.py (optional, current version 2.3 already included)
* Additional Python 2 Libs:
	- pySerial 
	- statistics (optional)
	
ThingsPro Gateway 2.6.0 uses Python 3 by default, due to the CissUsbConnectored.py is currently only available for Python 2 we need to install the required Python libs for Python 2, that means while using the pip installer you need to specify this for python 2.

	python2 -m pip install setuptools
	python2 -m pip install wheel
	python2 -m pip install requests
	python2 -m pip install pySerial
	python2 -m pip install statistics
	python2 -m pip install enum34
	
Finaly we need to link the ThingsPro library to python 2 direcoty (only needed in 2.6.0).

	ln -s /usr/lib/python3.5/libmxidaf_py.py /usr/lib/python2.7/libmxidaf_py.py




<a name="installation"></a>
### 3. Installation

The build_tpg_bundle.sh script can be used to build a ThingsPro User Program bundle which can be directly downloaded to ThingsPro.

	cd <user program directory>
	bash build_tpg_bundle.sh <your version info>
	
The resulting *.tgz file is inside the same directory where build_tpg_bundle.sh is located. The name may be like moxaiiot-ciss-to-thingspro_v0.3.1.tgz

While configuring the user program you may use the -p parameter to specify the USB device name, with that you do not need to change any configuration file if the default settings fit your environment.

![ThingsPro Gateway User Program](media/User-Program-Setup.png?raw=true "ThingsPro Gateway")

In case the hardware has different USB ports the CISS sensor can be fixed to a dedicated device name by using udev rules.
Below an example configuration using "/dev/cissSensor0" as device name.
You may need to create the file /etc/udev/rules.d/50-usb.rules if not already present.

	moxa@Moxa:~$ cat /etc/udev/rules.d/50-usb.rules
	# CISS Sensor
	SUBSYSTEM=="tty", ATTRS{idVendor}=="108c", 	ATTRS{idProduct}=="01a2", ATTRS{serial}=="XX:XX:XX:XX:XX:XX", 	SYMLINK+="cissSensor0"
	moxa@Moxa:~$

XX:XX:XX:XX needs to be replaced by your devices serial id, which can be queried by using

Below command shows the USB port the CISS Sensor is attached to (needed in next command)

	moxa@Moxa:~$ dmesg | grep -i ciss
	[    4.651707] usb 2-1.1: Product: CISS
	[    7.033209] scsi 0:0:0:0: Direct-Access              CISS             1.00 PQ: 0 ANSI: 5

Use the USB port to query the SerialNumber and original device name, in this example **2-1.1**

	moxa@Moxa:~$ dmesg | grep -i 2-1.1
	[    1.740131] hub 2-1:1.0: USB hub found
	[    1.744237] hub 2-1:1.0: 4 ports detected
	[    4.490193] usb 2-1.1: new full-speed USB device number 5 using musb-hdrc
	[    4.632430] usb 2-1.1: New USB device found, idVendor=108c, idProduct=01a2
	[    4.644324] usb 2-1.1: New USB device strings: Mfr=1, Product=2, SerialNumber=3
	[    4.651707] usb 2-1.1: Product: CISS
	[    4.655299] usb 2-1.1: SerialNumber: XX:XX:XX:XX:XX:XX
	[    5.974247] cdc_acm 2-1.1:1.1: ttyACM0: USB ACM device
	[    6.017395] usb-storage 2-1.1:1.0: USB Mass Storage device detected
	[    6.028151] scsi host0: usb-storage 2-1.1:1.0
	moxa@Moxa:~$

[    4.655299] usb 2-1.1: **SerialNumber: XX:XX:XX:XX:XX:XX**

[    5.974247] cdc_acm 2-1.1:1.1: **ttyACM0**: USB ACM device



<a name="configuration"></a>
### 4. Configuration

The application uses one json formatted configuration file which can be selected with command line argument "-c <config.json>", if not provided it will use the default "sensor.json" file included in the main application directory. 

The configuration file has two main sections:
* Main Application configuration
* CISS sensor configurations (list of CISS sensors)

	"tpg_vtag_template": "CissSensor"
	
tpg_vtag_template: Configures the ThingsPro Custom Equipment Name, used to publish the sensor data too. This name shall match the Template name configured in ThingsPro Virtual Tag section.	
All the tags, which are published to ThingsPro, will use this information for the Equipment section.
The Tag name is built from sensor information. The tag name format is descripted in the sensor configuration section.
	
	"tpg_publish_interval": 5
	
tpg_publish_interval: The interval (in seconds) for publishing the collected data from CISS sensors. 
In this example, the streamed CISS sensor values are collected for 5 seconds, and then the latest one is published to ThingsPro Gateway.

	"ciss_nodes" : {
	
ciss_nodes: This section contains the configuration dedicated to one of the CISS sensors.
Multiple sensors can be configured, but only one is currently supported on a ThingsPro Gateway.

	"cissACM0": {
	
The "cissACM0" is a unique id used to indicate a Sensor in the user program. If not needed keep the default. (Use the serial COM port number for unique ID)

	"name": "CissACM0"
	
name: The name of the CISS node. This name is used to construct the ThingsPro Tag name in combination with the sensor Name and the sensor published value. The name shall be unique as well.
The Tag name build rule:

	TagName = "%s-%s-%s"% name, sensor_name, value_name
	
E.g.: CissACM0-ACCL-current

	"ini_print": "True"
	
ini_print: Enables logging functions inside CissUsbConnectord.py provided by Bosch
 
	"com_port": "/dev/ttyACM0"
	
com_port: The serial communication port used for the CISS node. Usually on ThingsPro installations, it is /dev/ttyACM0, but may be different depending on the model. 
			
	"sensors": {
	
sensors: This section contains the configuration for the individual sensors inside the CISS node. 
Each Sensor has its own configuration section.

	"Accl": {
	
This "Accl" key is the unique id indicating the dedicated sensor in the CISS node. Each sensor has the same configuration structure but may differ with some sensor specific information if required. Currently only Accl sensor has this option. The unique sensor key shall not be changed as it is used in the application to map the sensors.

	"name": "ACCL"
	
name: This information is used to build the Tag Name for publishing to ThingsPro Gateway. See "name" in above section for the rules.

	"unit": "n/a"
	
unit: The unit used to publish the values. It's depending on the sensor and is optional

	"enabled": 1
	
enabled: Enables the sensor in main program, if not enabled no values are stored for this sensor.

	"publish": 6
	
publish: Bit value, enables publishing. If "1" (0x01), publish current sensor values to ThingsPro Gateway. If "2â€� (0x02), publish all collected values including calculated values, like statistics (optional). If 4 (0x04) and for all xyz sensors, publish also all xyz values.  â€œ0â€� disables publishing. 
e.g.: 6 = 0000 0110 = publish all values if xyz also sub values.

	"enable_statistics": 1
	
enable_statistics: Enables statistic information for sensor values. If set and Pythons statistics module is installed, it calculates "mean" and "std" values based on the last 10 (default) collected values from CISS node. A higher number then 10 will set the number of last collected values used for statistics.
	
	"stream_enabled": 1,
	"stream_period": 100000,
	"event_enabled": 0,
	"event_threshold": 0,
	"range": 16,
	
These Values are based on the original Bosch CISS python script and are passed directly to the original CISSUsbConnectored.py script. Please check CISS sensor descriptions for details.
For environmental sensors the max value from Temp, Humi, Pres is used.
As of current CISS documentation:
* Temp, Humi, Pres and Light share the same value (configued in seconds)
* Accl, Gyro, Magn share the same value (configured in micro seconds)
* Nois not yet implemented

<a name="test"></a>
### 5. Testing the configuration

Copy the project folder to UC e.g.: /home/moxa

Check USB device name for CISS Sensor, check with 

	$ dmesg | grep -i ttyACM

ajust the sensor.json configuration file if needed and execute the main script

	$ sudo python2 ciss_to_tpg.py -v

or to specify a dedicated configuration file

	$ sudo python2 ciss_to_tpg.py -c /home/moxa/my_ciss_config.json -v

If Virtual Tags are configured, select the Tags in the Application configuration section to be published to external brokers (Generic MQTT, Azure, AWS, ...) 

If everything is ok, repack the whole folder content in a *.tgz file and upload it to ThingsPro Gateway user applications. (See ThingsPro user manual for full procedure)

Best practice: Use the same name for the User Application as used for the CISS node.

<a name="todos"></a>
### 6. ToDo's 

There is still a lot to do, let me know your experience or if you have some feedback.
* Running the sensors in event mode.

<a name="restrictions"></a>
### 7. Restrictions
* Only USB connection supported
* Only streaming mode supported




