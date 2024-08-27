import urequests
import network
import neopixel
import machine
import time
# Networking for wifi
ssid = 'SSID'
password = 'SSIDPASSWORD'

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

while not wlan.isconnected():
    pass

print('Connected to Wi-Fi')

# API key and URL
api_key = 'YOUR_API_KEY'
base_url = 'http://YOUR_URL' # This is the URL you use to connect to mainsail in your browser (.local works too)
status_url = f'{base_url}/api/printer'
temperature_url = f'{base_url}/printer/objects/query?heater_bed&extruder'


# Change your board pins here
s_pin = 10
p_pin = 11
# NeoPixel setup 
status_pin = machine.Pin(s_pin, machine.Pin.OUT)    # this is the pin on the pico
status_npix = neopixel.NeoPixel(status_pin, 30)  # Status LEDs and the amount
progress_pin = machine.Pin(p_pin, machine.Pin.OUT)  # this is the pin on the pico
progress_npix = neopixel.NeoPixel(progress_pin, 36)  # Progress LEDs and the  amount




# Utility functions
def set_status_leds(color, brightness=1.0):
    """Set the color of the status LEDs with specified brightness."""
    for i in range(status_npix.n):
        r, g, b = color
        status_npix[i] = (int(r * brightness), int(g * brightness), int(b * brightness))
    status_npix.write()

def set_green_led():
    """Set the status LEDs to green."""
    for i in range(len(status_npix)):
        status_npix[i] = (255, 255, 0)  # Green color
    status_npix.write()
    time.sleep(1)

def flash_red():
    """Flash the LEDs red to indicate an error."""
    for _ in range(3):
        set_status_leds((255, 0, 0))  # Red
        time.sleep(0.5)
        set_status_leds((0, 0, 0))  # Off
        time.sleep(0.5)

def special_green_effect():
    """Display a special green effect on the LEDs to indicate a completed print."""
    for _ in range(100):
        # Roll effect
        for i in range(status_npix.n):
            status_npix[i] = (0, 255, 0)  # Green
            status_npix.write()
            time.sleep(0.05)
        for i in range(status_npix.n - 1, -1, -1):
            status_npix[i] = (0, 255, 0)  # Green
            status_npix.write()
            time.sleep(0.05)
        # Flash all lights
        for _ in range(3):
            set_status_leds((0, 255, 0))  # Green
            time.sleep(0.5)
            set_status_leds((0, 0, 0))  # Off
            time.sleep(0.5)

def set_progress_leds(percentage):
    """Update the progress bar LEDs based on the print percentage."""
    num_leds = int((percentage / 100) * progress_npix.n)
    for i in range(progress_npix.n):
        progress_npix[i] = (0, 255, 0) if i < num_leds else (0, 0, 0)
    progress_npix.write()

def status_idle_animation():
    """Run a rainbow animation on the status LED strip when idle."""
    def wheel(pos):
        """Generate a color wheel effect."""
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        pos -= 170
        return (0, pos * 3, 255 - pos * 3)

    for j in range(256):  # One cycle of all 256 colors in the wheel
        for i in range(status_npix.n):
            color = wheel((i + j) & 255)
            status_npix[i] = color
        status_npix.write()
        

def progress_idle_animation():
    """Run a rainbow animation on the progress LED strip when idle."""
    def wheel(pos):
        """Generate a color wheel effect."""
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        pos -= 170
        return (0, pos * 3, 255 - pos * 3)

    for j in range(256):  # One cycle of all 256 colors in the wheel
        for i in range(progress_npix.n):
            color = wheel((i + j) & 255)
            progress_npix[i] = color
        progress_npix.write()
        

def get_print_status():
    response = urequests.get(status_url, headers={'X-Api-Key': api_key})
    data = response.json()
    job_state = data.get('state', {}).get('text')
    job_percentage = data.get('result', {}).get('progress', {}).get('completion', 0)
    print_duration = data.get('result', {}).get('print_stats', {}).get('print_duration', 0)
    print(job_state)
    response.close()
    return job_state, job_percentage, print_duration

def get_temperatures():
    response = urequests.get(temperature_url, headers={'X-Api-Key': api_key})
    data = response.json()
    # print("temp Data")
    # print(data)
    
    bed_temp = data.get('result', {}).get('status', {}).get('heater_bed', {}).get('temperature')
    extruder_temp = data.get('result', {}).get('status', {}).get('extruder', {}).get('temperature')
    response.close()
    return bed_temp, extruder_temp

def set_progress_leds_based_on_temp(bed_temp):
    """Update the progress bar LEDs based on the bed temperature."""
    if bed_temp <= 30:
        color = (0, 0, 255)  # Blue
    elif 31 <= bed_temp <= 60:
        color = (255, 165, 0)  # Orange
    elif 61 <= bed_temp <= 90:
        color = (255, 0, 0)  # Red
    else:
        color = (255, 255, 255)  # White for temperatures above 90°C (optional)

    for i in range(progress_npix.n):
        progress_npix[i] = color
    progress_npix.write()

# Main loop
while True:
    current_state, job_percentage, print_duration = get_print_status()
    bed_temp, extruder_temp = get_temperatures()

    # Handle print job status
    if current_state == 'Error':
        flash_red()
    elif current_state == 'Complete':
        special_green_effect()
    elif current_state == 'Printing':
        set_green_led()

    # Change progress strip color based on bed temperature when "Operational"
    if current_state == 'Operational':
        set_progress_leds_based_on_temp(bed_temp)
    
    if current_state == 'Printing':
        progress_idle_animation()

    # Print temperatures, job status, and print duration to console
    print("REPORT:")
    print(f"Bed Temperature: {bed_temp}°C")
    print(f"Extruder Temperature: {extruder_temp}°C")
    print(f"The current state of the print job is: {current_state}")
    print(f"Print Duration: {print_duration} seconds")

    # Run idle animation if needed
    # if current_state in ['unknown', 'idle', 'Operational'] and current_state != 'Operational':
     #   idle_animation()

    time.sleep(0.2)  # Adjust polling interval as needed



