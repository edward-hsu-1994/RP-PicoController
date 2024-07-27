import time
import threading
from network import WLAN, STA_IF
from machine import Pin, PWM
from dht import DHT11
from umqtt.simple import MQTTClient
from mq135 import MQ135

DEVICE_NAME = "PicoController"

# Wifi Configuration
WIFI_SSID = 'default_ssid'
WIFI_PWD = 'default_password'

MQTT_HOST = 'default_host'
MQTT_PORT = 1883
MQTT_USER = 'default_user'
MQTT_PWD = 'default_password'
MQTT_TOPIC_TEMPERATURE = 'homeassistant/temperature/xxxxx'
MQTT_TOPIC_HUMIDITY = 'homeassistant/humidity/xxxxx'
MQTT_TOPIC_CO2 = 'homeassistant/co2/xxxxx'
MQTT_TOPIC_AIRCON_CTRL = 'homeassistant/airconditioner/xxxxx'

PIN_POWER_LED_R = 12
PIN_POWER_LED_G = 13
PIN_POWER_LED_ONBOARD = 'LED'
PIN_POWER_SENSOR_DHT11 = 14
PIN_SIGNAL_SENSOR_DHT11 = 15
PIN_SIGNAL_SENSOR_MQ135 = 26
PIN_SIGNAL_CTRL_IR = 16

SCAN_LOOP_DELAY = 5


IR_FREQUENCY = 38000

# THIS IS MY AIR CON's IR signal records.
IR_AIR_CON_OFF = [6631,-7320,530,-1426,561,-3379,524,-1441,525,-1428,562,-3368,529,-1441,552,-3376,529,-1429,570,-3368,525,-3409,525,-1440,556,-1403,557,-1411,553,-1411,552,-1411,552,-1409,557,-3368,529,-1441,552,-1411,552,-1411,548,-1404,566,-1397,566,-1397,571,-1392,558,-1411,557,-1403,561,-1407,552,-1397,566,-1411,553,-1411,553,-1402,561,-1407,557,-1407,548,-1411,552,-1411,557,-1404,553,-1411,557,-1411,525,-3405,525,-1433,529,-1426,539,-1426,534,-1440,520,-1440,519,-1434,534,-1441,516,-1440,528,-1422,534,-1440,519,-1433,534,-1426,529,-1441,524,-1441,525,-3402,530,-1440,525,-1440,521,-1440,520,-3412,516,-1440,524,-1441,525,-3405,520,-3412,520,-1440,519,-1442,525,-7374,641,-100007]
IR_AIR_CON_ON  = [6643,-7296,557,-1397,566,-3371,561,-1396,566,-1406,561,-3376,561,-1393,557,-3369,566,-1400,561,-3376,561,-3368,566,-3376,547,-1411,552,-1411,552,-1404,529,-1441,548,-1409,557,-3376,561,-1403,556,-1411,552,-1411,548,-1411,552,-1411,556,-1399,562,-1396,561,-1411,557,-1411,553,-1396,566,-1403,561,-1397,571,-1392,562,-1396,566,-1409,557,-1404,557,-1396,566,-1396,571,-1407,552,-1397,566,-1404,557,-3375,557,-1411,553,-1396,561,-1404,561,-1411,524,-1441,525,-1426,538,-1422,534,-1433,529,-1440,525,-1440,520,-1440,547,-1411,557,-1399,562,-1396,566,-3376,557,-1411,552,-1400,562,-1396,561,-3375,556,-1411,552,-1404,557,-3380,552,-3380,553,-3383,548,-1412,547,-7360,631,-100013]


def connect_wifi():
    try:
        wlan = WLAN(STA_IF)
        wlan.active(False)
        wlan.active(True)
        wlan.connect(WIFI_SSID, WIFI_PWD)
        return wlan
    except:
        return None


irLED = PWM(Pin(PIN_SIGNAL_CTRL_IR))
irLED.freq(IR_FREQUENCY)
highDuty = 21843
lowDuty = 0
irLED.duty_u16(lowDuty)
def send_ir_signal(pulses):
    for pluse in pulses:
        if pluse > 0:
            irLED.duty_u16(highDuty)
            time.sleep_us(pluse)
            irLED.duty_u16(lowDuty)
        else:
            time.sleep_us(-pluse)
    irLED.duty_u16(0)

def received_event(topic, msg):
    print(f'Received event: {topic}')
    if topic.decode("utf-8") == MQTT_TOPIC_AIRCON_CTRL:
        if msg.decode("utf-8") == "ON":
            print("TURN ON AIRCONDITIONER")
            send_ir_signal(IR_AIR_CON_ON)
        else:
            print("TURN OFF AIRCONDITIONER")
            send_ir_signal(IR_AIR_CON_OFF)

def connect_mqtt():
    try:
        client = MQTTClient(DEVICE_NAME, MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PWD)
        client.set_callback(received_event)
        client.connect()
        client.subscribe(MQTT_TOPIC_AIRCON_CTRL)
        return client
    except:
        return None





rgbStatusLED_R = Pin(PIN_POWER_LED_R, Pin.OUT)
rgbStatusLED_G = Pin(PIN_POWER_LED_G, Pin.OUT)
powerStatusLED = Pin(PIN_POWER_LED_ONBOARD, machine.Pin.OUT)
dht11powerPin = Pin(PIN_POWER_SENSOR_DHT11, Pin.OUT)
dht11SensorSignalPin = Pin(PIN_SIGNAL_SENSOR_DHT11)

rgbStatusLED_R.off()
rgbStatusLED_G.off()
powerStatusLED.on()
dht11powerPin.on()





wlan = None
mqtt = None


def listen_mqtt_event():
    while True:
        if mqtt is None:
            time.sleep(5)
            print(f'mqtt is none')
            continue
        print(f'wait mqtt msg')
        mqtt.wait_msg()
        time.sleep(1)
    
listenMqttThread = threading.Thread(target=listen_mqtt_event)
listenMqttThread.start()

while True:
    try:
        rgbStatusLED_R.on()
        print('Start Initial')
        
        # Connect to Wifi
        if wlan == None or wlan.isconnected() == False :
            wlan = connect_wifi()
            if wlan == None or wlan.isconnected() == False:
                raise Exception(f"Failed connect to Wifi: {WIFI_SSID}")
            print(f'Success connect to Wifi: {WIFI_SSID}, ConnectionInfo: {wlan}')
        
        if mqtt == None:
            mqtt = connect_mqtt()
            if mqtt == None:
                raise Exception(f"Failed connect to MQTT: {MQTT_HOST}")
                    
        # Setup DHT11Sensor DataPin
        dht11Sensor=DHT11(dht11SensorSignalPin)
        print(f'Success initial DHT11 Sensor')
        
        mq135Sensor=MQ135(Pin(PIN_SIGNAL_SENSOR_MQ135))
        print(f'Success initial MQ135 Sensor')

        rgbStatusLED_R.off()
        print('Finish Initial')
        
        print('Boot Scan Loop')
        while True:
            time.sleep(SCAN_LOOP_DELAY)
            rgbStatusLED_G.on()
            
            # Temperature And Humidity
            dht11Sensor.measure()                    # start to measure
            temperature=dht11Sensor.temperature()        # return the temperature
            humidity=dht11Sensor.humidity()        # return the humidity
                        
            mqtt.publish(MQTT_TOPIC_TEMPERATURE, str(temperature))
            print(f'Publish To Topic: {MQTT_TOPIC_TEMPERATURE}')
            mqtt.publish(MQTT_TOPIC_HUMIDITY, str(humidity))
            print(f'Publish To Topic: {MQTT_TOPIC_HUMIDITY}')
            
            # CO2
            co2_ppm = mq135Sensor.get_corrected_ppm(float(temperature),float(humidity))
            #co2_ppm = mq135Sensor.get_ppm()  
            mqtt.publish(MQTT_TOPIC_CO2, str(co2_ppm))
            print(f'Publish To Topic: {MQTT_TOPIC_CO2}')
                        
            rgbStatusLED_G.off()
            
            print(f'humidity={humidity}', end=",")
            print(f'temperature={temperature}', end=",")
            print(f'co2={co2_ppm}')
    except Exception as error:
        rgbStatusLED_G.off()
        rgbStatusLED_R.on()
        print(f'Error:\r\n{error}')
        print('Restart...')
        time.sleep(10)
