import urequests
import network
import neopixel
import machine
import time

# Networking
ssid = 'your_SSID'
password = 'your_password'

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

while not wlan.isconnected():
    pass

print('Connected to Wi-Fi')

# API URL
base_url = 'http://YOUR_URL'
status_url = f'{base_url}/api/printer'
temperature_url = f'{base_url}/printer/objects/query?heater_bed&extruder'

s_pin = 14

# NeoPixel setup
status_pin = machine.Pin(s_pin, machine.Pin.OUT)    # This is the pin on the Pico
status_npix = neopixel.NeoPixel(status_pin, 36)     # Status LEDs and the amount

# State variables for non-blocking animations
animation_state = None
animation_step = 0
animation_start_time = time.ticks_ms()

def set_status_leds(color, brightness=1.0):
    """Set the color of the status LEDs with specified brightness."""
    for i in range(status_npix.n):
        r, g, b = color
        status_npix[i] = (int(r * brightness), int(g * brightness), int(b * brightness))
    status_npix.write()

def get_print_status():
    response = urequests.get(status_url)
    data = response.json()
    job_state = data.get('state', {}).get('text')
    job_percentage = data.get('result', {}).get('progress', {}).get('completion', 0)
    print_duration = data.get('result', {}).get('print_stats', {}).get('print_duration', 0)
    response.close()
    return job_state, job_percentage, print_duration

def get_temperatures():
    response = urequests.get(temperature_url)
    data = response.json()
    bed_temp = data.get('result', {}).get('status', {}).get('heater_bed', {}).get('temperature')
    extruder_temp = data.get('result', {}).get('status', {}).get('extruder', {}).get('temperature')
    response.close()
    return bed_temp, extruder_temp

def set_leds_based_on_temp(bed_temp):
    """Update the status LEDs based on the bed temperature."""
    if bed_temp <= 30:
        color = (0, 0, 255)  # Blue
    elif 30 < bed_temp <= 60:
        color = (255, 165, 0)  # Orange
    elif 60 < bed_temp <= 90:
        color = (255, 0, 0)  # Red
    else:
        color = (255, 255, 255)  # White for temperatures above 90°C (optional)

    for i in range(status_npix.n):
        status_npix[i] = color
    status_npix.write()

def status_idle_animation_step(step):
    """Run one step of the rainbow animation on the status LED strip."""
    def wheel(pos):
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        pos -= 170
        return (0, pos * 3, 255 - pos * 3)

    for i in range(status_npix.n):
        color = wheel((i + step) & 255)
        status_npix[i] = color
    status_npix.write()
    return (step + 1) % 256

def flash_red_step(step):
    """Flash the LEDs red to indicate an error."""
    now = time.ticks_ms()
    if step % 2 == 0:
        set_status_leds((255, 0, 0))  # Red
    else:
        set_status_leds((0, 0, 0))    # Off
    return step + 1, now

def set_pause_animation_step(step, direction):
    """Run one step of the pause animation on the status LEDs."""
    if direction == 1:
        status_npix[step] = (0, 255, 0)  # Green
    else:
        status_npix[step] = (0, 0, 255)  # Blue
    status_npix.write()
    return (step + direction) % status_npix.n, direction

def special_green_effect_step(step):
    """Run one step of the special green effect animation."""
    if step < status_npix.n:
        status_npix[step] = (0, 255, 0)  # Green
    elif step < 2 * status_npix.n:
        status_npix[2 * status_npix.n - step - 1] = (0, 255, 0)  # Green
    else:
        set_status_leds((0, 255, 0))  # Green flash
    status_npix.write()
    return step + 1

# Main loop
while True:
    current_state, job_percentage, print_duration = get_print_status()
    bed_temp, extruder_temp = get_temperatures()

    now = time.ticks_ms()

    if current_state == 'Operational' and bed_temp >= 30:
        set_leds_based_on_temp(bed_temp)
        animation_state = 'idle'
        animation_step = 0
    elif current_state == 'Printing':
        set_green_led()
        set_leds_based_on_temp(bed_temp)
        animation_state = None
    elif current_state == 'Error':
        if time.ticks_diff(now, animation_start_time) > 500:
            animation_step, animation_start_time = flash_red_step(animation_step)
    elif current_state == 'Paused':
        if time.ticks_diff(now, animation_start_time) > 50:
            animation_step, direction = set_pause_animation_step(animation_step, 1 if animation_step % status_npix.n == 0 else -1)
            animation_start_time = now
    elif current_state == 'Completed':
        if time.ticks_diff(now, animation_start_time) > 50:
            animation_step = special_green_effect_step(animation_step)
            animation_start_time = now
    else:
        animation_step = status_idle_animation_step(animation_step)

    # Print temperatures, job status, and print duration to console
    print("REPORT:")
    print(f"Bed Temperature: {bed_temp}°C")
    print(f"Extruder Temperature: {extruder_temp}°C")
    print(f"The current state of the print job is: {current_state}")
    print(f"Print Duration: {print_duration} seconds")

    time.sleep(0.05)  # Adjust polling interval as needed
