import time
import numpy as np
import os
import sys
import pygame
from datetime import datetime
from bleak import BleakClient
from bleak import BleakScanner
import asyncio

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# BLE sensor characteristic
BLE_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
RX_CHARACTERISTIC_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
TX_CHARACTERISTIC_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

baseline_data = None
data_record = []


def notification_handler(sender, data):
    global data_record, baseline_data
    """Notification handler for receiving BLE data."""
    print(f"Data received: {data}")
    data_str = data.decode('utf-8')
    data_values = [str for str in data_str.split(',') if str != '']
    try:
        data_in_floats = np.array([float(value) for value in data_values])

        if data_in_floats.size == 30:
            valid_data = data_in_floats.reshape(2, 5, 3)
            data_record.append(valid_data)
        else:
            print(f"Received data is not in the correct format: 30 elements")
        if(baseline_data is None):
            baseline_data = data_record[0]
    
    except ValueError as e:
        print(f"Error converting data to float: {e}")
        data_record = []
        
    

# Cannot use this, sensor not permit read
async def read_sensor_data(client):
    """Read sensor data from the BLE device's characteristic."""
    try:
        data = await client.read_gatt_char(RX_CHARACTERISTIC_UUID)
        return np.array(data)
    except Exception as e:
        print(f"Error reading sensor data: {e}")
        return None


async def visualize_ble(viz_mode="3axis", scaling=7.0, record=False):
    global data_record, baseline_data
    device = None
    devices = await BleakScanner.discover()
    for d in devices:
        if BLE_SERVICE_UUID in d.metadata['uuids']:
            print(f"Found device with the wanted UUID: device: {d.name}, address: {d.address}")
            device = d
    if(d is None):
        print(f"No device found with the wanted UUID: {BLE_SERVICE_UUID}")
        return None

    
    # Connect to the BLE sensor via the provided Bluetooth address.
    client = BleakClient(device.address)
    await client.connect()
    if not client.is_connected:
        print("Failed to connect to the BLE device.")
        return

    # Start the sensor data stream
    time.sleep(1.0)

    pygame.init()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    bg_image_path = os.path.join(dir_path, "viz_bg.png")
    bg_image = pygame.image.load(bg_image_path)
    image_width, image_height = bg_image.get_size()
    aspect_ratio = image_height / image_width
    desired_width = 400
    desired_height = int(desired_width * aspect_ratio)

    chip_locations = np.array(
        [
            [204, 222],  # center
            [130, 222],  # left
            [279, 222],  # right
            [204, 157],  # up
            [204, 290],  # down
        ]
    )
    chip_xy_rotations = np.array([-np.pi / 2, -np.pi / 2, np.pi, np.pi / 2, 0.0])

    bg_image = pygame.transform.scale(bg_image, (desired_width, desired_height))
    window = pygame.display.set_mode((desired_width, desired_height), pygame.SRCALPHA)
    background_surface = pygame.Surface(window.get_size(), pygame.SRCALPHA)
    background_color = (234, 237, 232, 255)
    background_surface.fill(background_color)
    background_surface.blit(bg_image, (0, 0))
    pygame.display.set_caption("Sensor Data Visualization")

    def visualize_data(data):
        data = data.reshape(-1, 3)
        data_mag = np.linalg.norm(data, axis=1)
        for magid, chip_location in enumerate(chip_locations):
            if viz_mode == "magnitude":
                pygame.draw.circle(
                    window, (255, 83, 72), chip_location, data_mag[magid] / scaling
                )
            elif viz_mode == "3axis":
                if data[magid, -1] < 0:
                    width = 2
                else:
                    width = 0
                pygame.draw.circle(
                    window,
                    (255, 0, 0),
                    chip_location,
                    np.abs(data[magid, -1]) / scaling,
                    width,
                )
                arrow_start = chip_location
                rotation_mat = np.array(
                    [
                        [
                            np.cos(chip_xy_rotations[magid]),
                            -np.sin(chip_xy_rotations[magid]),
                        ],
                        [
                            np.sin(chip_xy_rotations[magid]),
                            np.cos(chip_xy_rotations[magid]),
                        ],
                    ]
                )
                data_xy = np.dot(rotation_mat, data[magid, :2])
                arrow_end = (
                    chip_location[0] + data_xy[0] / scaling,
                    chip_location[1] + data_xy[1] / scaling,
                )
                pygame.draw.line(window, (0, 255, 0), arrow_start, arrow_end, 2)
    baseline = np.zeros_like(np.zeros(3))
    frame_num = 0
    running = True
    data = []
    clock = pygame.time.Clock()
    FPS = 60
    while running:
        window.blit(background_surface, (0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                print(f"Mouse clicked at ({x}, {y})")
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_b:
                    print("Baseline updated...")
                    baseline = np.zeros_like(baseline)

        # Read the sensor data from BLE
        await client.start_notify(RX_CHARACTERISTIC_UUID, notification_handler)
        await asyncio.sleep(0.1)
        await client.stop_notify(RX_CHARACTERISTIC_UUID)
        print(f"Two set: {data_record}")
        if len(data_record) > 0:
            print(f"Data to visualize: {data_record[0]}")
            data.append(data_record[0] - baseline_data)
            visualize_data(data_record[0] - baseline_data)
            
         

        frame_num += 1
        pygame.display.update()
        clock.tick(FPS)
        data_record = []

    pygame.quit()
    await client.disconnect()

    if record:
        np.savetxt(f"{filename}.txt", data)


def main():
    asyncio.run(visualize_ble(viz_mode="3axis", scaling=7.0, record=False))


if __name__ == "__main__":
    main()
