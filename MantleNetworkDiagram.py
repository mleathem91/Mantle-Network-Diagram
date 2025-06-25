import pandas as pd
from pyvis.network import Network
import os

def get_column_index(col_str):
    """Converts Excel-style column letters (A, B, AA, DF) to a zero-based index."""
    index = 0
    for char in col_str:
        index = index * 26 + (ord(char.upper()) - ord('A')) + 1
    return index - 1

def create_mantle_network_diagram(csv_file_path, output_file_name="mantle_network.html"):
    """
    Parses a Mantle benefits CSV file and creates an interactive network diagram.

    Args:
        csv_file_path (str): The path to the input CSV file.
        output_file_name (str): The name of the output HTML file.
    """
    if not os.path.exists(csv_file_path):
        print(f"Error: The file '{csv_file_path}' was not found.")
        return

    # --- 1. Data Loading and Preparation ---
    # The main data starts at row 25 (index 24). We read it without a header.
    try:
        # We read the entire sheet and then select the relevant slice
        # to avoid issues with varying row lengths.
        df_full = pd.read_csv(csv_file_path, header=None, low_memory=False)
        # Benefit items section starts from row 24 onwards (row 25 in Excel)
        df = df_full.iloc[24:].copy()
        df.reset_index(drop=True, inplace=True)

        # Assign meaningful names to the first few columns for easier access
        col_map = {
            0: 'ItemID',
            1: 'ItemName',
            2: 'ItemType'
        }
        df.rename(columns=col_map, inplace=True)

    except Exception as e:
        print(f"Error reading or processing the CSV file: {e}")
        return

    # --- 2. Initialize Network Graph ---
    # Create a pyvis network object. It's a directed graph.
    # The size of the canvas is set here.
    net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white", directed=True)

    # --- 3. Define Column Ranges for Parameter Parsing ---
    # These ranges are based on the user's description.
    # Function 1 (Items and first node of Series): DF to HV
    # DF=109, DG=110, HV=229
    # We look for parameter names in DG, DI, DK, etc.
    params1_start_col = get_column_index('DG')
    params1_end_col = get_column_index('HV')

    # Function 2 (Subsequent nodes of Series): HW to MN
    # HW=230, HX=231, MN=351
    # We look for parameter names in HX, HZ, IB, etc.
    params2_start_col = get_column_index('HX')
    params2_end_col = get_column_index('MN')


    # --- 4. Populate Graph Nodes ---
    # First, add all valid items from Column A as nodes to the graph.
    # This ensures that even items that are only referenced, but not defined
    # in the file (or have no outgoing links), are included in the graph.
    valid_items = df.dropna(subset=['ItemID'])
    for index, row in valid_items.iterrows():
        item_id = str(row['ItemID'])
        item_name = str(row['ItemName'])
        item_type = str(row['ItemType'])
        
        title = f"ID: {item_id}<br>Name: {item_name}<br>Type: {item_type}"
        
        # Assign colors based on item type for better visual distinction
        color = "#007bff" # Default blue
        if "Series" in item_type:
            color = "#28a745" # Green for Series
        elif "Item" in item_type:
            color = "#ffc107" # Yellow for Items
            
        net.add_node(item_id, label=item_id, title=title, color=color, shape='dot', size=15)


    # --- 5. Populate Graph Edges (Dependencies) ---
    # Now, iterate through the items again to find their dependencies and create edges.
    for index, row in valid_items.iterrows():
        source_node_id = str(row['ItemID'])

        # This function processes a range of columns for a given row
        def parse_dependencies(row_data, start_col, end_col):
            # Parameter names are in every second column (start, start+2, ...)
            for i in range(start_col, end_col, 2):
                param_name_col = i
                param_value_col = i + 1

                # Check if columns exist in the dataframe
                if param_name_col >= len(row_data) or param_value_col >= len(row_data):
                    continue

                param_info = row_data.iloc[param_name_col]
                
                # Check if the parameter info is a valid string and contains our delimiter ':'
                if isinstance(param_info, str) and ':' in param_info:
                    param_type = param_info.split(':')[-1].strip()
                    
                    # If the parameter type is 'Item', it's a dependency
                    if param_type in ['Item', 'Series']:
                        target_node_id = str(row_data.iloc[param_value_col])
                        
                        # Add a directed edge from the current item to its dependency
                        if pd.notna(target_node_id) and target_node_id != 'nan':
                            net.add_edge(source_node_id, target_node_id)
        
        # Parse the first set of parameters
        parse_dependencies(row, params1_start_col, params1_end_col)
        
        # If the item is a 'Series', parse the second set of parameters as well
        if "Series" in str(row['ItemType']):
            parse_dependencies(row, params2_start_col, params2_end_col)


    # --- 6. Generate and Save the Visualization ---
    try:
        # Set physics options for a better layout
        net.set_options("""
        var options = {
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -30000,
              "centralGravity": 0.3,
              "springLength": 150,
              "springConstant": 0.05,
              "damping": 0.09,
              "avoidOverlap": 0.1
            },
            "maxVelocity": 50,
            "minVelocity": 0.1,
            "solver": "barnesHut",
            "stabilization": {
              "enabled": true,
              "iterations": 1000,
              "updateInterval": 100,
              "onlyDynamicEdges": false,
              "fit": true
            },
            "timestep": 0.5
          },
          "interaction": {
            "hover": true,
            "navigationButtons": true,
            "keyboard": true
          }
        }
        """)
        net.save_graph(output_file_name)
        print(f"Successfully generated network diagram: '{output_file_name}'")

    except Exception as e:
        print(f"Error generating the HTML file: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    # The script will look for the CSV in the same directory where it is run.
    # Make sure your CSV file is named 'mantle_benefits_8052.csv'
    # or change the file name below.
    csv_file = 'mantle_benefits_8052.csv'
    create_mantle_network_diagram(csv_file)