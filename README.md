# moxaiiot-ciss-to-thingspro
Publish Bosch CISS sensor data to ThingsPro Gateway

[Bosch CISS sensor information] (https://www.bosch-connectivity.com/de/produkte/industrie-4-0/connected-industrial-sensor-solution/downloads/)

[ThingsPro Gateway information]
(https://www.moxa.com/en/products/industrial-computing/system-software/thingspro-2)

1. Getting started

2. Requirements

3. Configuration

4. Test 

5. ToDo's

*******************************************************************************
### 1. Getting started 

* Download and Install ThingsPro Gateway software v2.5.x
* Configure Modbus Data Acquisition Virtual Tags using ThingsPro Gateway Web UI
* Modify sensor.json file with your configuration
* Package the user program in tar.gz format
* Upload the Compressed folder to the ThingsPro Gateway

### 2. Requirements
* UC-XXXX with ThingsPro Gateway v2.5.x installed
* Bosch CISS Sensor connected to UC-XXXX USB
* Bosch Python script CissUsbConnectord.py (optional, current version already included)
* Additional Python Libs:
	- pySerial 
	- statistics (optional)

### 3. Configuration

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
	
publish: Bit value, enables publishing. If "1" (0x01), publish current sensor values to ThingsPro Gateway. If "2” (0x02), publish all collected values including calculated values, like statistics (optional). If 4 (0x04) and for all xyz sensors, publish also all xyz values.  “0” disables publishing. 
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


### 4. Testing the configuration

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

### 5. ToDo's 

There is still a lot to do, let me know your experience or if you have some feedback.
* Running the sensors in event mode.

### 6. Restrictions
* Only USB connection supported
* Only streaming mode supported




