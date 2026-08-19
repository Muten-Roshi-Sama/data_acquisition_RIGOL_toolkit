import numpy as np
import matplotlib.pyplot as plt
import time

def capture_waveform(osc, channel='CHAN1', verbose=True):
    """Capture waveform using proper IEEE block format (WORKING VERSION)"""
    
    # Configure oscilloscope
    osc.write(f':WAV:SOUR {channel}')
    time.sleep(0.2)
    osc.write(':WAV:MODE NORM')
    time.sleep(0.2)
    osc.write(':WAV:FORM BYTE')
    time.sleep(0.2)
    
    # Get preamble (metadata about the waveform)
    preamble = osc.query(':WAV:PRE?')
    preamble_values = preamble.split(',')
    
    points = int(preamble_values[2])           # How many samples
    x_increment = float(preamble_values[4])    # Time between samples
    x_origin = float(preamble_values[5])       # Starting time
    y_increment = float(preamble_values[7])    # Voltage per unit
    y_origin = float(preamble_values[8])       # Zero voltage
    y_reference = int(preamble_values[9])      # Center byte value (usually 127)
    
    if verbose:
        print(f"  Capturing {points} samples from {channel}...")
    
    # CRITICAL: Write the query command FIRST
    osc.write(':WAV:DATA?')
    time.sleep(0.5)  # Let scope prepare data
    
    # Set timeout for binary data
    original_timeout = osc.inst.timeout
    osc.inst.timeout = 30000  # 30 second timeout
    
    try:
        # Read the IEEE block header first
        # Format: #9000001200 (11 bytes) where 9=num_digits, 000001200=data_length
        header = osc.inst.read_raw(11)
        
        if header[0:1] != b'#':
            raise ValueError(f"Expected IEEE header starting with '#', got {header}")
        
        # Parse header to get actual data length
        num_digits = int(header[1:2])
        data_length_str = header[2:2+num_digits].decode('utf-8')
        data_length = int(data_length_str)
        
        if verbose: print(f"  Header: {header}, data_length={data_length}")
        
        # Now read the actual sample bytes
        raw_bytes = osc.inst.read_raw(data_length)
        
        # FIXED: Convert bytes to numpy array and use actual mean as reference
        # This removes the DC offset issue from y_reference/y_origin mismatch
        byte_array = np.frombuffer(raw_bytes, dtype=np.uint8)
        y_data = (byte_array - np.mean(byte_array)) * y_increment
        
        # Create time axis
        time_axis = np.arange(len(y_data)) * x_increment + x_origin
        
        preamble_dict = {
            'points': points,
            'x_increment': x_increment,
            'x_origin': x_origin,
            'y_increment': y_increment,
            'y_origin': y_origin,
            'y_reference': y_reference
        }
        
        if verbose: print(f"  ✓ Captured {len(y_data)} points successfully")
        return time_axis, y_data, preamble_dict
        
    finally:
        osc.inst.timeout = original_timeout


import json
import os
from pathlib import Path


def save_waveform_capture(filepath, time_array, voltage_array, preamble, 
                          metadata=None, verbose=True):
    """
    Save a waveform capture from capture_waveform() to a file.
    
    Uses NPZ format (compressed NumPy) for binary data (time/voltage) and JSON
    for metadata/preamble info for easy inspection and portability.
    
    Args:
        filepath: Path to save to (string or Path). Will create .npz and .json files.
        time_array: Time axis from capture_waveform()
        voltage_array: Voltage samples from capture_waveform()
        preamble: Preamble dict from capture_waveform()
        metadata: Optional dict with extra info (e.g., 'channel', 'gain', 'frequency')
        verbose: Print confirmation
    
    Returns:
        dict with keys 'npz_path', 'json_path'
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove extension if present, we'll add our own
    base = filepath.with_suffix('')
    npz_path = base.with_suffix('.npz')
    json_path = base.with_suffix('.json')
    
    # Save binary data (time, voltage) as NPZ
    np.savez_compressed(
        npz_path,
        time_array=time_array,
        voltage_array=voltage_array
    )
    
    # Save metadata and preamble as JSON
    json_data = {
        'preamble': preamble,
        'metadata': metadata or {},
        'num_samples': len(voltage_array),
        'time_range_ms': (np.min(time_array), np.max(time_array)) if len(time_array) > 0 else (0, 0),
        'voltage_range_v': (float(np.min(voltage_array)), float(np.max(voltage_array))) if len(voltage_array) > 0 else (0, 0),
    }
    
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    if verbose:
        print(f"✓ Saved waveform capture:")
        print(f"  Binary data: {npz_path}")
        print(f"  Metadata:   {json_path}")
    
    return {'npz_path': str(npz_path), 'json_path': str(json_path)}


def load_waveform_capture(filepath):
    """
    Load a previously saved waveform capture.
    
    Args:
        filepath: Path to .npz or .json file (will find both automatically)
    
    Returns:
        dict with keys:
            'time_array': Time axis
            'voltage_array': Voltage samples
            'preamble': Oscilloscope preamble dict
            'metadata': User-provided metadata
            'num_samples': Number of samples
            'voltage_range_v': (min_v, max_v)
            'time_range_ms': (min_t, max_t)
    """
    filepath = Path(filepath)
    base = filepath.with_suffix('')
    
    npz_path = base.with_suffix('.npz')
    json_path = base.with_suffix('.json')
    
    if not npz_path.exists() or not json_path.exists():
        raise FileNotFoundError(f"Waveform files not found. Looking for:\n  {npz_path}\n  {json_path}")
    
    # Load binary data
    data = np.load(npz_path)
    time_array = data['time_array']
    voltage_array = data['voltage_array']
    
    # Load metadata
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    return {
        'time_array': time_array,
        'voltage_array': voltage_array,
        'preamble': json_data['preamble'],
        'metadata': json_data.get('metadata', {}),
        'num_samples': json_data['num_samples'],
        'voltage_range_v': json_data['voltage_range_v'],
        'time_range_ms': json_data['time_range_ms']
    }


