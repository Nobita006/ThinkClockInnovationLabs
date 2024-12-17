# High-Level Overview of ThinkClock Innovation Labs Assignment - Sayan Das

The code performs the following tasks:

1. User Input: Prompts the user to enter a specific battery_id or leave it blank to consider all batteries in the dataset.
2. Data Loading: Reads a metadata.csv file, which serves as a master index linking each operation to a data file and providing derived parameters (Re, Rct, Capacity).
3. Data Parsing and Cleaning: Converts times into a Python datetime format, converts numeric fields to floats, and optionally filters the data by a selected battery.
4. Data Subsetting: Separates the dataset into different operation types (impedance, discharge), assigns cycle numbers to represent the battery’s aging, and extracts impedance measurements (including Rectified_Impedance) from additional CSV files.
5. Filtering Outliers: Applies filtering criteria to remove non-physical or unrealistic values that can distort the plots.
6. Plotting: Uses Plotly to create interactive line plots showing how Re, Rct, and Rectified Impedance evolve over the impedance measurement sequence, and how Capacity fades over discharge cycles.

# Demonstration


https://github.com/user-attachments/assets/53329fa8-6d37-4bea-ac8f-e16efd57b878

