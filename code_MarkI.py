import board
import busio
import time
import struct

import digitalio
import rotaryio
import analogio

import adafruit_bme680
import adafruit_icm20x
import adafruit_tca9548a  #mux

from adafruit_ra8875 import ra8875
from adafruit_ra8875.ra8875 import color565

from math import atan2, sqrt, copysign, pi

## battery

vbat_voltage = analogio.AnalogIn(board.A2)

## some values - update later
## For low pass filtering
filtered_x_value = 0.0
filtered_y_value = 0.0
pitch = 0.0
roll = 0.0
pitch_bias = 0.0
roll_bias = 0.0

### Rotary encoder setup

## Define the CLK and DT pins (no SW pin for this project)
clk_pin = board.A0
dt_pin = board.A1

## Initialize the rotary encoder
encoder = rotaryio.IncrementalEncoder(clk_pin, dt_pin)

## Initial rotary parameters
val = 0
max_scn = 3
min_scn = 0
last_position = encoder.position

### end rotary encoder setup

### TFT display setup

## Initialize SPI communication
spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI)

## Initialize Chip Select (and Reset pin, when applicable...not for this project)
cs = digitalio.DigitalInOut(board.A3)

## Initialize display
display = ra8875.RA8875(spi, cs, baudrate=4000000)
display.init()

## Define some colors to use
BLACK = color565(0, 0, 0)
GREEN = color565(0, 200, 0)  # Green

### end TFT display setup

### multiplexer setup for i2c devices

i2c = board.STEMMA_I2C()
mux = adafruit_tca9548a.TCA9548A(i2c)  # create mux object and pass the bus to it

## Create BME680 object
bme680 = adafruit_bme680.Adafruit_BME680_I2C(mux[0])  # sensor plugged into 0

## Initial BME680 values (calibrated, checked for Snoqualmie and against another thermometer)
bme680.sea_level_pressure = 1013
temperature_offset = -7.2

## Create ICM20948 object
icm20948 = adafruit_icm20x.ICM20948(mux[1])  # sensor plugged into 1

### end multiplexer setup

### Initialize timer in order to update sensor information on specific screens

## time approach
last_temp_update_time = 0
current_time = time.monotonic()

## Define screens
def display_screen_0():
    global last_temp_update_time, current_time  # globals for sensor updates

    should_exit = False  # Initialize the exit condition
    last_encoder_value = encoder.position  # Store the initial encoder value

	## static screen information
	## temperature
    display.fill(BLACK)
    time.sleep(0.1)  # delay to allow the screen to completely darken

    ## Header
    display.txt_set_cursor(15, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("*Atmosphere*")

    display.txt_set_cursor(235, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("S.P.E.C.I.A.L.")

    display.txt_set_cursor(485, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Heading")

    display.txt_set_cursor(630, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Inventory")

    display.line(15, 50, 780, 50, GREEN)

    ## Page Content
    display.txt_set_cursor(20, 60)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Temp (deg C): ")
	
    display.txt_set_cursor(20, 100)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Temp (deg F): ")
	
	## humidity
    display.txt_set_cursor(20, 160)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Humidity: ")
	
	## gas
    display.txt_set_cursor(20, 220)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Gas (VOC): ")
	
    display.txt_set_cursor(20, 260)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Std Range - 200 to 350")  # added for context
	
	## pressure
    display.txt_set_cursor(20, 320)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Pressure: ")
	
    display.txt_set_cursor(20, 360)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Reference Pressure - 1013 hPa")
	
	## altitude
    display.txt_set_cursor(20, 420)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Altitude: ")
	
	## battery level
    display.txt_set_cursor(420, 420)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Battery Level: ")

    ## draw a cloud
    display.curve(500, 290, 60, 60, 0, GREEN)  # 50 down
    display.curve(500, 290, 60, 60, 1, GREEN)
    display.line(500, 350, 700, 350, GREEN)
    display.curve(700, 270, 80, 80, 3, GREEN)
    display.curve(700, 270, 80, 80, 2, GREEN)
    display.curve(700, 250, 80, 60, 1, GREEN)
    display.curve(580, 230, 80, 60, 1, GREEN)
    display.curve(580, 210, 60, 40, 2, GREEN)

    ## draw a sun behind the cloud
    display.curve(640, 170, 60, 60, 1, GREEN)  # 50 down
    display.curve(640, 170, 60, 60, 2, GREEN)
    display.curve(680, 170, 20, 20, 3, GREEN)

    ## draw some sunrays for fun
    display.line(640, 70, 640, 100, GREEN)  # 50 down
    display.line(700, 120, 780, 70, GREEN)
    display.line(580, 120, 500, 70, GREEN)
    display.line(570, 150, 540, 150, GREEN)
    display.line(710, 150, 740, 150, GREEN)

    while not should_exit:
        current_time = time.monotonic()  # current time
        time.sleep(0.1)

        # Check if the encoder value has changed
        if encoder.position != last_encoder_value:
            should_exit = True
            display.fill(BLACK)
        else:
            # display update code here
            if current_time - last_temp_update_time > 5:
                time.sleep(0.1)
                display.txt_set_cursor(230,60)
                display.txt_trans(GREEN)
                display.txt_size(1)
                temp = bme680.temperature
                display.txt_write("{:.2f} C".format(temp))
				
                display.txt_set_cursor(230,100)
                display.txt_trans(GREEN)
                display.txt_size(1)
                tempF = ((9/5)*bme680.temperature) + 32
                display.txt_write("{:.2f} F".format(tempF))
				
                display.txt_set_cursor(230,160)
                display.txt_trans(GREEN)
                display.txt_size(1)
                hum = bme680.relative_humidity - 0.01  # because the sensor starts at 100% and it looks funny when it's first read
                display.txt_write("{:.2f} %".format(hum))
				
                display.txt_set_cursor(230,220)
                display.txt_trans(GREEN)
                display.txt_size(1)
                gas = bme680.gas/1000
                display.txt_write("{:.2f} % kohm".format(gas))
				
                display.txt_set_cursor(230,320)
                display.txt_trans(GREEN)
                display.txt_size(1)
                pres = bme680.pressure
                display.txt_write("{:.2f} hPa".format(pres))
				
                display.txt_set_cursor(230,420)
                display.txt_trans(GREEN)
                display.txt_size(1)
                alt = bme680.altitude/1000  # meters is default
                display.txt_write("{:.2f} km".format(alt))
				
                def get_voltage(pin):
                    return (pin.value*3.3)/(65536*2)
				
                battery_voltage = get_voltage(vbat_voltage)
                battery_level = (battery_voltage/4.2)*100
				
                display.txt_set_cursor(650, 420)
                display.txt_trans(GREEN)
                display.txt_size(1)
                display.txt_write("{:.2f} %".format(battery_level))
				
                last_temp_update_time = current_time

        # Other actions or checks can be placed here

        time.sleep(2)  # Add a small sleep to prevent excessive loop execution

    ## Perform cleanup actions here if needed when the loop exits

def display_screen_1():
    display.fill(BLACK)
    time.sleep(0.1)

    ## Header
    display.txt_set_cursor(15, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Atmosphere")

    display.txt_set_cursor(200, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("*S.P.E.C.I.A.L.*")

    display.txt_set_cursor(485, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Heading")

    display.txt_set_cursor(630, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Inventory")

    display.line(15, 50, 780, 50, GREEN)

    ## Page Content
    def convert_555_to_565(rgb):
        return (rgb & 0x7FE0) << 1 | 0x20 | rgb & 0x001F

    class BMP:
        def __init__(self, filename):
            self.filename = filename
            self.colors = None
            self.data = 0
            self.data_size = 0
            self.bpp = 0
            self.width = 0
            self.height = 0
            self.read_header()

        def read_header(self):
            if self.colors:
                return
            with open(self.filename, "rb") as f:
                f.seek(10)
                self.data = int.from_bytes(f.read(4), "little")
                f.seek(18)
                self.width = int.from_bytes(f.read(4), "little")
                self.height = int.from_bytes(f.read(4), "little")
                f.seek(28)
                self.bpp = int.from_bytes(f.read(2), "little")
                f.seek(34)
                self.data_size = int.from_bytes(f.read(4), "little")
                f.seek(46)
                self.colors = int.from_bytes(f.read(4), "little")

        def draw(self, disp, x=0, y=0):
#             print("{:d}x{:d} image".format(self.width, self.height))
#             print("{:d}-bit encoding detected".format(self.bpp))
            line = 0
            line_size = self.width * (self.bpp // 8)
            if line_size % 4 != 0:
                line_size += 4 - line_size % 4
            current_line_data = b""
            with open(self.filename, "rb") as f:
                f.seek(self.data)
                disp.set_window(x, y, self.width, self.height)
                for line in range(self.height):
                    current_line_data = b""
                    line_data = f.read(line_size)
                    for i in range(0, line_size, self.bpp // 8):
                        if (line_size - i) < self.bpp // 8:
                            break
                        if self.bpp == 16:
                            color = convert_555_to_565(line_data[i] | line_data[i + 1] << 8)
                        if self.bpp in (24, 32):
                            color = color565(
                                line_data[i + 2], line_data[i + 1], line_data[i]
                            )
                            current_line_data = current_line_data + struct.pack(">H", color)
                    disp.setxy(x, self.height - line + y)
                    disp.push_pixels(current_line_data)
                disp.set_window(0, 0, disp.width, disp.height)

    bitmap = BMP("/s2.bmp")
    x_position = 90
    y_position = (display.height // 2) - (bitmap.height // 2)
    bitmap.draw(display, x_position, y_position)

    display.txt_set_cursor(400, 60)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Strength      6")

    display.txt_set_cursor(400, 120)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Perception    4")

    display.txt_set_cursor(400, 180)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Endurance     8")

    display.txt_set_cursor(400, 240)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Charisma      5")

    display.txt_set_cursor(400, 300)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Intelligence  7")

    display.txt_set_cursor(400, 360)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Agility       3")

    display.txt_set_cursor(400, 420)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Luck          2")

def display_screen_2():
    global last_temp_update_time, current_time, pitch, roll, pitch_bias, roll_bias  # globals for sensor updates

    should_exit = False  # Initialize the exit condition
    last_encoder_value = encoder.position  # Store the initial encoder value

	## static screen information
	## acceleration
    display.fill(BLACK)
    time.sleep(0.1)  # delay to allow the screen to completely darken

    ## Header
    display.txt_set_cursor(15, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Atmosphere")

    display.txt_set_cursor(210, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("S.P.E.C.I.A.L.")

    display.txt_set_cursor(460, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("*Heading*")

    display.txt_set_cursor(630, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Inventory")

    display.line(15, 50, 780, 50, GREEN)

    ## Page Content
    ## top cone:
    display.line(600, 60, 630, 200, GREEN)
    display.line(600, 60, 570, 200, GREEN)

    ## right cone
    display.line(630, 200, 770, 230, GREEN)
    display.line(770, 230, 630, 260, GREEN)

    ## bottom cone
    display.line(630, 260, 600, 400, GREEN)
    display.line(600, 400, 570, 260, GREEN)

    ## left cone
    display.line(570, 260, 430, 230, GREEN)
    display.line(430, 230, 570, 200, GREEN)

    ## small upper right cone
    display.line(685, 145, 672, 209, GREEN)
    display.line(685, 145, 621, 158, GREEN)

    ## small lower right cone
    display.line(685, 315, 672, 251, GREEN)
    display.line(685, 315, 621, 302, GREEN)

    ## small lower left cone
    display.line(515, 315, 579, 302, GREEN)
    display.line(515, 315, 528, 251, GREEN)

    ## small upper left cone
    display.line(515, 145, 528, 209, GREEN)
    display.line(515, 145, 579, 158, GREEN)

    display.txt_set_cursor(20, 170)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Heading: ")

    display.txt_set_cursor(20, 300)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Compass: ")

    while not should_exit:
        current_time = time.monotonic()  # current time
        time.sleep(0.1)

        ## Check if the encoder value has changed
        if encoder.position != last_encoder_value:
            should_exit = True
            display.fill(BLACK)
        else:
            ## display update code
            if current_time - last_temp_update_time > 5:
                time.sleep(0.1)

                def degrees_to_heading(degrees):
                    heading = ""
                    if (degrees > 337) or (degrees >= 0 and degrees <= 22):
                        heading = 'N '
                    elif degrees > 22 and degrees <= 67:
                        heading = "NE"
                    elif degrees > 67 and degrees <= 112:
                        heading = "E "
                    elif degrees > 112 and degrees <= 157:
                        heading = "SE"
                    elif degrees > 157 and degrees <= 202:
                        heading = "S "
                    elif degrees > 202 and degrees <= 247:
                        heading = "SW"
                    elif degrees > 247 and degrees <= 292:
                        heading = "W "
                    elif degrees > 292 and degrees <= 337:
                        heading = "NW"
                    return heading

                def low_pass_filter(raw_value, remembered_value):
                    alpha = 0.8
                    filtered = (alpha * remembered_value) + (1.0 - alpha) * raw_value
                    return filtered

                def get_reading():
                    global filtered_y_value, filtered_x_value

                    x, y, z = icm20948.acceleration
                    mag_x, mag_y, mag_z = icm20948.magnetic

                    # Pitch and Roll in Radians
                    roll_rad = atan2(-x, sqrt((z * z) + (y * y)))
                    pitch_rad = atan2(z, copysign(y, y) * sqrt((0.01 * x * x) + (y * y)))

                    # Pitch and Roll in Degrees
                    pitch = pitch_rad * 180 / pi
                    roll = roll_rad * 180 / pi

                    filtered_x_value = low_pass_filter(mag_x, filtered_x_value)
                    filtered_y_value = low_pass_filter(mag_y, filtered_y_value)

                    az = 90 - atan2(filtered_y_value, filtered_x_value) * 180 / pi

                    if az < 0:
                        az += 360

                    pitch -= pitch_bias
                    roll -= roll_bias

                    heading = degrees_to_heading(az)

                    return x, y, z, pitch, roll, az, heading
				
                x, y, z, pitch_bias, roll_bias, az, heading_value = get_reading()

                display.txt_set_cursor(220, 150)
                display.txt_trans(GREEN)
                display.txt_size(10)
                display.txt_write("{}".format(heading_value))

                display.txt_set_cursor(220, 300)
                display.txt_trans(GREEN)
                display.txt_size(1)
#                 display.txt_write("Pitch {} Roll {} Compass {} Heading {}".format(round(pitch, 1), round(roll, 1), az, heading_value))
                display.txt_write("{} degrees".format(az))

                last_temp_update_time = current_time

        # Other actions or checks can be placed here

        time.sleep(2)  # Add a small sleep to prevent excessive loop execution

    # Perform cleanup actions here if needed when the loop exits

def display_screen_3():
    display.fill(BLACK)
    time.sleep(0.1)

    ## Header
    display.txt_set_cursor(15, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Atmosphere")

    display.txt_set_cursor(210, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("S.P.E.C.I.A.L.")

    display.txt_set_cursor(460, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Heading")

    display.txt_set_cursor(600, 10)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("*Inventory*")

    display.line(15, 50, 780, 50, GREEN)

    ## Page Content
    display.txt_set_cursor(80, 60)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("** Baseball **")

    display.txt_set_cursor(80, 120)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Desk Fan")

    display.txt_set_cursor(80, 180)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Duct Tape (2)")

    display.txt_set_cursor(80, 240)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Fancy Hairbrush (2)")

    display.txt_set_cursor(80, 300)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Ladle")

    display.txt_set_cursor(80, 360)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Oven Mitt")

    display.txt_set_cursor(80, 420)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Paint Can")

    display.txt_set_cursor(600, 280)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Cork (2)")

    display.txt_set_cursor(600, 320)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Leather")

    display.txt_set_cursor(550, 360)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Weight      0.5")

    display.txt_set_cursor(550, 400)
    display.txt_trans(GREEN)
    display.txt_size(1)
    display.txt_write("Value       0.5")

current_screen = None

try:
    while True:
        current_position = encoder.position
        if current_position > last_position:
            val += 1
            if val > max_scn:
                val = min_scn
            last_position = current_position
        elif current_position < last_position:
            val -= 1
            if val < min_scn:
                val = max_scn
            last_position = current_position

        if val != current_screen:
            current_screen = val
            if val == 0:
                display_screen_0()
            elif val == 1:
                display_screen_1()
            elif val == 2:
                display_screen_2()
            else:
                display_screen_3()

        time.sleep(0.1)  # Adjust the sleep interval if needed


## ctrl+c handling, the clearing the screen to reset things.
except KeyboardInterrupt:
    pass
finally:
    display.fill(BLACK)  # Clear the display
