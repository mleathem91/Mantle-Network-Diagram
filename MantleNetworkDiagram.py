import pandas as pd
from highcharts import Highchart
import os
import argparse
import sys

# --- Configuration Constants ---
# These values can be easily changed here instead of being hardcoded in functions.
DATA_START_ROW = 24  # The data starts at row 25 (0-indexed)
COLUMN_MAP = {
    0: 'ItemID',
    1: 'ItemName',
    2: 'ItemType'
}
# Column ranges for parsing dependencies, based on the file structure.
# Function 1 (Items and first node of Series): DF to HV
PARAMS1_COLS = ('DF', 'HV')
# Function 2 (Subsequent nodes of Series): HW to MN
PARAMS2_COLS = ('HW', 'MN')

# --- Helper Function ---
def get_column_index(col_str):
    """Converts Excel-style column letters (A, B, AA, DF) to a zero-based index."""
    index = 0
    for char in col_str:
        index = index * 26 + (ord(char.upper()) - ord('A')) + 1
    return index - 1

# --- Core Functions ---
def load_and_prepare_data(csv_file_path):
    """Loads and prepares the data from the Mantle CSV file."""
    if not os.path.exists(csv_file_path):
        print(f"Error: The file '{csv_file_path}' was not found.")
        return None

    try:
        df_full = pd.read_csv(csv_file_path, header=None, low_memory=False)
        df = df_full.iloc[DATA_START_ROW:].copy()
        df.reset_index(drop=True, inplace=True)
        df.rename(columns=COLUMN_MAP, inplace=True)
        return df
    except Exception as e:
        print(f"Error reading or processing the CSV file: {e}")
        return None

def create_network_data(df):
    """Creates nodes and edges for the network diagram."""
    nodes = []
    edges = []
    
    valid_items = df.dropna(subset=['ItemID']).copy()
    valid_item_ids = set(valid_items['ItemID'].astype(str))

    # Create a dictionary to store the degree of each node
    degrees = {str(item_id): 0 for item_id in valid_item_ids}

    params1_start_col = get_column_index(PARAMS1_COLS[0])
    params1_end_col = get_column_index(PARAMS1_COLS[1])
    params2_start_col = get_column_index(PARAMS2_COLS[0])
    params2_end_col = get_column_index(PARAMS2_COLS[1])

    def parse_dependencies(row_data, start_col, end_col):
        source_node_id = str(row_data['ItemID'])
        for i in range(start_col, end_col, 2):
            param_name_col = i
            param_value_col = i + 1

            if param_name_col >= len(row_data) or param_value_col >= len(row_data):
                continue

            param_info = row_data.iloc[param_name_col]
            
            if isinstance(param_info, str) and ':' in param_info:
                param_name, param_type = [x.strip() for x in param_info.split(':', 1)]
                
                if param_type in ['Item', 'Series']:
                    target_node_id = str(row_data.iloc[param_value_col])
                    
                    if pd.notna(target_node_id) and target_node_id != 'nan' and target_node_id in valid_item_ids:
                        edges.append({'from': source_node_id, 'to': target_node_id, 'name': param_name})
                        degrees[source_node_id] += 1
                        degrees[target_node_id] += 1

    for index, row in valid_items.iterrows():
        parse_dependencies(row, params1_start_col, params1_end_col)
        if "Series" in str(row['ItemType']):
            parse_dependencies(row, params2_start_col, params2_end_col)

    for index, row in valid_items.iterrows():
        item_id = str(row['ItemID'])
        item_name = str(row['ItemName'])
        item_type = str(row['ItemType'])
        
        title = f"<b>{item_name}</b><br>ID: {item_id}<br>Type: {item_type}"
        
        color = "#007bff"  # Default blue
        if "Series" in item_type:
            color = "#28a745"  # Green
        elif "Item" in item_type:
            color = "#ffc107"  # Yellow

        degree = degrees.get(item_id, 0)
        radius = 5 + (degree * 2)

        nodes.append({
            'id': item_id,
            'name': item_name,
            'title': title,
            'marker': {'radius': radius, 'fillColor': color},
            'color': color
        })
        
    return nodes, edges


def generate_diagram(nodes, edges, output_file_name):
    """Configures and saves the network diagram to an HTML file."""
    chart = Highchart(width=1200, height=800)

    options = {
        'chart': {
            'type': 'networkgraph',
            'marginTop': 80
        },
        'title': {
            'text': 'Mantle Network Diagram'
        },
        'plotOptions': {
            'networkgraph': {
                'keys': ['from', 'to'],
                'layoutAlgorithm': {
                    'enableSimulation': True,
                    'friction': -0.9
                }
            }
        },
        'series': [{
            'dataLabels': {
                'enabled': True,
                'linkFormat': ''
            },
            'id': 'mantle-network',
            'data': edges,
            'nodes': nodes
        }]
    }

    chart.set_dict_options(options)
    
    chart.save_file(output_file_name)
    print(f"Successfully generated network diagram: '{output_file_name}'")


# --- Main Execution ---
def main():
    """Main function to run the script from the command line."""
    parser = argparse.ArgumentParser(
        description="Generates an interactive network diagram from a Mantle benefits CSV file.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "csv_file",
        help="Path to the input CSV file (e.g., mantle_benefits_8052.csv)"
    )
    parser.add_argument(
        "-o", "--output",
        default="mantle_network.html",
        help="Name for the output HTML file (default: mantle_network.html)"
    )
    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    args = parser.parse_args()

    # --- Script Workflow ---
    df = load_and_prepare_data(args.csv_file)
    if df is not None:
        nodes, edges = create_network_data(df)
        generate_diagram(nodes, edges, args.output)

if __name__ == "__main__":
    main()