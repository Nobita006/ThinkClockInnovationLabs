import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

# ----------------------------------------
# User Input for battery_id
# ----------------------------------------
battery_input = input("Enter battery IDs separated by commas (e.g., B0047,B0050) or keep blank to select all: ").strip()

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
# Filter by user-selected battery_ids
# ----------------------------------------
if battery_input:
    # Split the input string into a list of battery IDs
    selected_batteries = [b_id.strip() for b_id in battery_input.split(',')]
    metadata = metadata[metadata['battery_id'].isin(selected_batteries)].copy()
else:
    selected_batteries = metadata['battery_id'].unique()
    battery_input = 'all Batteries'

# If no rows for these battery_ids, print a message and exit
if len(metadata) == 0:
    print(f"No data found for battery IDs {selected_batteries}. Please try other IDs.")
    raise SystemExit

# ----------------------------------------
# Separate operations by type
# ----------------------------------------
impedance_data = metadata[metadata['type'] == 'impedance'].copy()
discharge_data = metadata[metadata['type'] == 'discharge'].copy()

# Assign cycle numbers per battery
# For discharge operations
discharge_data = discharge_data.sort_values(['battery_id', 'start_time']).reset_index(drop=True)
discharge_data['cycle_number'] = discharge_data.groupby('battery_id').cumcount() + 1

# For impedance operations
impedance_data = impedance_data.sort_values(['battery_id', 'start_time']).reset_index(drop=True)
impedance_data['impedance_cycle_number'] = impedance_data.groupby('battery_id').cumcount() + 1

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
# Filtering Data
# Remove entries with NaNs and outliers
impedance_data_clean = impedance_data.dropna(subset=['Re','Rct','Rectified_Impedance'])

# Apply filtering thresholds based on realistic ranges
impedance_data_clean = impedance_data_clean[
    (impedance_data_clean['Re'] > 0) & (impedance_data_clean['Re'] < 1) &
    (impedance_data_clean['Rct'] > 0) & (impedance_data_clean['Rct'] < 1) &
    (impedance_data_clean['Rectified_Impedance'] > 0) & (impedance_data_clean['Rectified_Impedance'] < 1)
]

print("\nOriginal impedance_data length:", len(impedance_data))
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
import plotly.express as px

# Get list of battery_ids in the data
battery_ids = impedance_data['battery_id'].unique()

# Plot Re and Rct together with dual y-axes
fig_combined = go.Figure()

# Loop over each battery to add traces for Re and Rct
for b_id in battery_ids:
    battery_data = impedance_data[impedance_data['battery_id'] == b_id]
    
    # Re trace
    fig_combined.add_trace(go.Scatter(
        x=battery_data['impedance_cycle_number'],
        y=battery_data['Re'],
        mode='lines+markers',
        name=f'Re ({b_id})',
        yaxis='y1'
    ))
    
    # Rct trace
    fig_combined.add_trace(go.Scatter(
        x=battery_data['impedance_cycle_number'],
        y=battery_data['Rct'],
        mode='lines+markers',
        name=f'Rct ({b_id})',
        yaxis='y2'
    ))

# Update layout with dual y-axes
fig_combined.update_layout(
    title=dict(
        text=f'Re and Rct Over Impedance Measurements for {battery_input}',
        x=0.5,  # Center align title
        y=0.95,  # Adjust title's vertical position
        font=dict(size=18),  # Increase font size
    ),
    xaxis_title='Impedance Measurement Number',
    yaxis=dict(
        title='Re (Ohms)',
        automargin=True  # Auto-adjust left margin
    ),
    yaxis2=dict(
        title='Rct (Ohms)',
        overlaying='y',
        side='right',
        automargin=True  # Auto-adjust right margin
    ),
    margin=dict(t=100, b=70),  # Top and bottom margin
    legend=dict(
        x=0.5, y=-0.2,  # Move legend below the graph
        xanchor='center', yanchor='top',
        orientation='h'
    ),
    template='plotly_white'
)

fig_combined.show()

# Plot Rectified Impedance for each battery
fig_rect = go.Figure()
for b_id in battery_ids:
    battery_data = impedance_data[impedance_data['battery_id'] == b_id]
    fig_rect.add_trace(go.Scatter(
        x=battery_data['impedance_cycle_number'],
        y=battery_data['Rectified_Impedance'],
        mode='lines+markers',
        name=f'Rectified Impedance ({b_id})'
    ))

# Rectified Impedance Plot
fig_rect.update_layout(
    title=dict(
        text=f'Rectified Impedance Over Impedance Measurements for {battery_input}',
        x=0.5, y=0.95,
        font=dict(size=18),
    ),
    xaxis_title='Impedance Measurement Number',
    yaxis_title='Rectified Impedance (Ohms)',
    margin=dict(t=100, b=70),
    legend=dict(
        x=0.5, y=-0.2,
        xanchor='center', yanchor='top',
        orientation='h'
    ),
    template='plotly_white'
)
fig_rect.show()

# Plot Capacity over cycles for each battery
battery_ids_discharge = discharge_data['battery_id'].unique()

fig2 = go.Figure()
for b_id in battery_ids_discharge:
    battery_data = discharge_data[discharge_data['battery_id'] == b_id]
    fig2.add_trace(go.Scatter(
        x=battery_data['cycle_number'],
        y=battery_data['Capacity'],
        mode='lines+markers',
        name=f'Capacity ({b_id})'
    ))

fig2.update_layout(
    title=dict(
        text=f'Capacity Fade Over Discharge Cycles for {battery_input}',
        x=0.5, y=0.95,
        font=dict(size=18),
    ),
    xaxis_title='Cycle Number',
    yaxis_title='Capacity (Ahr)',
    margin=dict(t=100, b=70),
    legend=dict(
        x=0.5, y=-0.2,
        xanchor='center', yanchor='top',
        orientation='h'
    ),
    template='plotly_white'
)
fig2.show()

print("\nPlots generated successfully.")
