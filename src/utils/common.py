import math
import numpy as np
import time
import random
import string
from scipy.signal import savgol_filter

def rotate(origin, point, angle):
    """
    Rotate a point counterclockwise by a given angle around a given origin.

    Parameters:
        origin (tuple): (x, y) coordinates of the rotation origin
        point (tuple): (x, y) coordinates of the point to rotate
        angle (float): Rotation angle in degrees

    Returns:
        tuple: (x, y) coordinates of the rotated point
    """
    angle = math.radians(angle)

    ox, oy = origin
    px, py = point

    qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
    qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
    return qx, qy


def get_segmented_value(value, segements):
    """
    Map a value to a segment based on predefined thresholds.
    
    Parameters:
        value (float): The input value to be mapped
        segements (list): List of threshold values defining the segments
        
    Returns:
        float: The segment value that the input maps to
    """
    for i in range(len(segements)-1):
        if value < segements[i+1]:
            value = segements[i]
            break
    if value >= segements[-1]:
        value = segements[-1]
    return value

def calculate_next_status(x, y, v, steering, acceleration, 
                            v_ego, steering_ego, acceleration_ego, delta_t):
    """
    Calculate the next position and velocity of an object relative to ego vehicle.
    
    Parameters:
        x, y (float): Current position coordinates
        v (float): Current velocity magnitude
        steering (float): Current steering angle in radians
        acceleration (float): Current acceleration magnitude
        v_ego (float): Ego vehicle velocity magnitude
        steering_ego (float): Ego vehicle steering angle in radians
        acceleration_ego (float): Ego vehicle acceleration magnitude
        delta_t (float): Time step
        
    Returns:
        tuple: (x_new, y_new, vx_new, vy_new) New position and velocity components
    """
    # Calculate ego displacement
    dx_ego = v_ego * np.cos(steering_ego) * delta_t + 0.5 * acceleration_ego * np.cos(steering_ego) * delta_t**2
    dy_ego = v_ego * np.sin(steering_ego) * delta_t + 0.5 * acceleration_ego * np.sin(steering_ego) * delta_t**2
    
    # Calculate NPC displacement
    dx_v = v * np.cos(steering) * delta_t + 0.5 * acceleration * np.cos(steering) * delta_t**2
    dy_v = v * np.sin(steering) * delta_t + 0.5 * acceleration * np.sin(steering) * delta_t**2
    
    # Calculate new position
    x_new = np.round(x + (dx_v - dx_ego), 4)
    y_new = np.round(y + (dy_v - dy_ego), 4)

    # Calculate new velocity
    v_new = v + acceleration * delta_t
    vx_new = np.round(v_new * np.cos(steering), 4)
    vy_new = np.round(v_new * np.sin(steering), 4)
    
    return x_new, y_new, vx_new, vy_new

def smooth_data(data, window_length=11, polyorder=3):
    """
    Smooth data using Savitzky-Golay filter.
    
    Parameters:
        data (array-like): Input data to be smoothed
        window_length (int): Length of the filter window (must be odd and less than data length)
        polyorder (int): Order of the polynomial used for filtering
        
    Returns:
        array: Smoothed data array
    """
    if len(data) < window_length:
        window_length = len(data) // 2
    return savgol_filter(data, window_length, polyorder)

def generate_random_name_string():
    """
    Generate a unique name string using current timestamp and random characters.
    
    Returns:
        str: A unique identifier in the format "timestamp-randomstring"
    """
    # Get current timestamp (seconds since epoch)
    current_time = int(time.time())
    
    # Generate a random 7-character string
    chars = string.ascii_letters + string.digits  # equivalent to a-zA-Z0-9
    rand_string = ''.join(random.choice(chars) for _ in range(7))
    
    # Create the save name
    save_name = f"{current_time}-{rand_string}"
    
    return save_name