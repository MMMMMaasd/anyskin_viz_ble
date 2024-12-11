import argparse
import time
import numpy as np
import uuid
import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import pygame
from bleak import BleakClient
from bleak import BleakScanner
import asyncio
import struct


# BLE sensor characteristic
BLE_SERVICE_UUID = uuid.UUID("6e400001-b5a3-f393-e0a9-e50e24dcca9e")
RX_CHARACTERISTIC_UUID = uuid.UUID("6e400003-b5a3-f393-e0a9-e50e24dcca9e")
TX_CHARACTERISTIC_UUID = uuid.UUID("6e400002-b5a3-f393-e0a9-e50e24dcca9e")

baseline_data = None
data_record = []

NUM_BOARDS = 1


def notification_handler(sender, data):
    global data_record, baseline_data
    """Notification handler for receiving BLE data."""
    # print(f"Data received: {data}")
    data_decoded = struct.unpack("@15f", data)
    # data_str = data.decode('utf-8')
    # data_values = [str for str in data_str.split(',') if str != '']
    try:
        # data_in_floats = np.array([float(value) for value in data_values])
        data_in_floats = np.array(data_decoded)
        if data_in_floats.size == NUM_BOARDS * 15:
            valid_data = data_in_floats.reshape(-1, 5, 3)
            data_record.append(valid_data)
        else:
            print("Received data is not in the correct format: 30 elements")
        if baseline_data is None:
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


async def visualize_ble(viz_mode="3axis", scaling=7.0):
    global data_record, baseline_data
    device = None
    devices = await BleakScanner.discover(return_adv=True)
    for k, dev_adv_data in devices.items():
        dev_data = dev_adv_data[0]
        adv_data = dev_adv_data[1]
        for serv_uuid in adv_data.service_uuids:
            serv_addr = uuid.UUID(serv_uuid)
            if serv_addr.int == BLE_SERVICE_UUID.int:
                print(f"Device {k}: {dev_adv_data}")
                device = dev_data
        if device is not None:
            break

    if device is None:
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
    bg_image_path = os.path.join(dir_path, "imgs/viz_bg.png")
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
                    width = 3
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
                pygame.draw.line(window, (0, 255, 0), arrow_start, arrow_end, 4)

    last_data = None
    frame_num = 0
    running = True
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
                    baseline_data = last_data

        # Read the sensor data from BLE
        await client.start_notify(RX_CHARACTERISTIC_UUID, notification_handler)
        await asyncio.sleep(1.0 / FPS)
        # await clock.tick(FPS)
        await client.stop_notify(RX_CHARACTERISTIC_UUID)
        # print(f"Two set: {data_record}")
        if len(data_record) > 0:
            # print(data_record[0])
            # data.append(data_record[0] - baseline_data)
            visualize_data(data_record[0] - baseline_data)
            last_data = data_record[0]
        elif last_data is not None:
            visualize_data(last_data - baseline_data)

        frame_num += 1
        pygame.display.update()
        # clock.tick(FPS)
        data_record = []

    pygame.quit()
    await client.disconnect()


def main(scaling=7.0):
    asyncio.run(visualize_ble(viz_mode="3axis", scaling=scaling))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize sensor data from BLE")
    parser.add_argument(
        "--scaling",
        "-s",
        type=float,
        default=7.0,
        help="Scaling factor for the sensor data visualization",
    )
    args = parser.parse_args()
    main(scaling=args.scaling)
