import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

# ----------------------------------------
# User Input for battery_id
# ----------------------------------------
battery_id = input("Enter the battery_id (e.g. B0047) or keep blank to select all: ").strip()

# ----------------------------------------
# Step 1: Load and Parse metadata.csv
# ----------------------------------------
metadata = pd.read_csv('cleaned_dataset/metadata.csv')

def parse_matlab_time(str_time):
    str_time = str_time.strip().strip('[]')
    parts = str_time.split()
    # If not exactly 6 parts, return NaT
    if len(parts) != 6:
        return pd.NaT
    arr = [float(x) for x in parts]
    year, month, day, hour, minute, sec = arr
    sec_int = int(sec)
    microseconds = int(round((sec - sec_int) * 1_000_000))
    return pd.Timestamp(year=int(year), month=int(month), day=int(day),
                        hour=int(hour), minute=int(minute), second=sec_int, microsecond=microseconds)

metadata['start_time'] = metadata['start_time'].apply(parse_matlab_time)
metadata = metadata.sort_values('start_time').reset_index(drop=True)

# Convert numerical columns
metadata['Re'] = pd.to_numeric(metadata['Re'], errors='coerce')
metadata['Rct'] = pd.to_numeric(metadata['Rct'], errors='coerce')
metadata['Capacity'] = pd.to_numeric(metadata['Capacity'], errors='coerce')

# ----------------------------------------
# Filter by user-selected battery_id
# ----------------------------------------
if battery_id:
    metadata = metadata[metadata['battery_id'] == battery_id].copy()
else:
    battery_id = 'all Batteries '

# If no rows for this battery_id, just print a message and stop
if len(metadata) == 0:
    print(f"No data found for battery_id {battery_id}. Please try another ID.")
    # You could either exit here or continue with no data.
    # We'll just exit this script:
    raise SystemExit

# ----------------------------------------
# Separate operations by type
# ----------------------------------------
impedance_data = metadata[metadata['type'] == 'impedance'].copy()
discharge_data = metadata[metadata['type'] == 'discharge'].copy()

# Assign cycle numbers to discharge operations
discharge_data = discharge_data.sort_values('start_time').reset_index(drop=True)
discharge_data['cycle_number'] = discharge_data.index + 1

# Sort impedance operations by time and assign a measurement number
impedance_data = impedance_data.sort_values('start_time').reset_index(drop=True)
impedance_data['impedance_cycle_number'] = impedance_data.index + 1

# ----------------------------------------
# Function to safely parse Rectified_Impedance
# ----------------------------------------
def to_complex_or_float(x):
    if pd.isnull(x):
        return np.nan
    if isinstance(x, (float, int)):
        # Already a number, just convert to complex (real only)
        return complex(x)
    if isinstance(x, str):
        x = x.strip().strip('()')
        if not x:
            return np.nan
        try:
            return complex(x)
        except ValueError:
            # If it's not a valid complex string, just return NaN
            return np.nan
    return np.nan

# ----------------------------------------
# Extract Rectified_Impedance from data files
# ----------------------------------------
def get_rectified_impedance(file_path):
    if not os.path.exists(file_path):
        # File doesn't exist
        return np.nan
    try:
        df = pd.read_csv(file_path)
        if 'Rectified_Impedance' in df.columns:
            df['Rectified_Impedance'] = df['Rectified_Impedance'].apply(to_complex_or_float)
            # Take the real part if complex, or value if float
            real_values = df['Rectified_Impedance'].apply(lambda c: c.real if isinstance(c, complex) else c)
            # Example: take median to represent the measurement
            return real_values.median()
        else:
            # Column not found, return NaN
            return np.nan
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return np.nan

data_base_path = 'cleaned_dataset/data/'
rectified_values = []
for idx, row in impedance_data.iterrows():
    fname = row['filename']
    file_path = os.path.join(data_base_path, fname)
    rect_val = get_rectified_impedance(file_path)
    rectified_values.append(rect_val)

impedance_data['Rectified_Impedance'] = rectified_values

# ----------------------------------------
# Check data distributions before filtering
# ----------------------------------------
print("Summary of Re, Rct, Rectified_Impedance before filtering:")
print(impedance_data[['Re','Rct','Rectified_Impedance']].describe())

# ----------------------------------------
# Filtering Data
impedance_data_clean = impedance_data.dropna(subset=['Re','Rct','Rectified_Impedance'])

impedance_data_clean = impedance_data_clean[
    (impedance_data_clean['Re'] > 0) & (impedance_data_clean['Re'] < 10) &
    (impedance_data_clean['Rct'] > 0) & (impedance_data_clean['Rct'] < 10) &
    (impedance_data_clean['Rectified_Impedance'] > 0) & (impedance_data_clean['Rectified_Impedance'] < 10)
]

print("Original impedance_data length:", len(impedance_data))
print("Filtered impedance_data length:", len(impedance_data_clean))

# Update references for plotting
impedance_data = impedance_data_clean

# If no data after cleaning:
if len(impedance_data) == 0:
    print("No impedance data after filtering. Adjust your filters or check the data.")
    # We can proceed but the plots will be empty.
    
# ----------------------------------------
# Plotting with Plotly
# ----------------------------------------
# Plot Re and Rct
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=impedance_data['impedance_cycle_number'],
    y=impedance_data['Re'],
    mode='lines+markers',
    name='Electrolyte Resistance (Re)'
))
fig.add_trace(go.Scatter(
    x=impedance_data['impedance_cycle_number'],
    y=impedance_data['Rct'],
    mode='lines+markers',
    name='Charge Transfer Resistance (Rct)',
    yaxis='y2'
))

fig.update_layout(
    title=f'Re and Rct Over Impedance Measurements for {battery_id}',
    xaxis_title='Impedance Measurement Number',
    yaxis_title='Re (Ohms)',
    yaxis2=dict(
        title='Rct (Ohms)',
        overlaying='y',
        side='right'
    ),
    legend=dict(x=0, y=1.1, orientation='h'),
    template='plotly_white'
)
fig.show()

# Plot Rectified_Impedance
fig_batt = go.Figure()
fig_batt.add_trace(go.Scatter(
    x=impedance_data['impedance_cycle_number'],
    y=impedance_data['Rectified_Impedance'],
    mode='lines+markers',
    name='Battery Impedance (Rectified)'
))
fig_batt.update_layout(
    title=f'Battery (Rectified) Impedance Over Impedance Measurements for {battery_id}',
    xaxis_title='Impedance Measurement Number',
    yaxis_title='Rectified Impedance (Ohms)',
    template='plotly_white'
)
fig_batt.show()

# Plot Capacity to show aging (for discharge data)
fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=discharge_data['cycle_number'],
    y=discharge_data['Capacity'],
    mode='lines+markers',
    name='Capacity (Ahr)'
))

fig2.update_layout(
    title=f'Capacity Fade Over Discharge Cycles for {battery_id}',
    xaxis_title='Cycle Number',
    yaxis_title='Capacity (Ahr)',
    template='plotly_white'
)
fig2.show()

print("Plots generated successfully. ")
