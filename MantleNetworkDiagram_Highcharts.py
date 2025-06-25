import pandas as pd
import json
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
    
    # Get the column ranges for parsing dependencies
    col_start_1 = get_column_index(PARAMS1_COLS[0])
    col_end_1 = get_column_index(PARAMS1_COLS[1])
    col_start_2 = get_column_index(PARAMS2_COLS[0])
    col_end_2 = get_column_index(PARAMS2_COLS[1])
    
    # Process each row to create nodes and edges
    for index, row in df.iterrows():
        item_id = row['ItemID']
        item_name = row['ItemName']
        item_type = row['ItemType']
        
        # Skip empty rows
        if pd.isna(item_id) or item_id == '':
            continue
            
        # Create node for this item
        node_color = get_node_color(item_type)
        nodes.append({
            'id': str(item_id),
            'name': str(item_name) if pd.notna(item_name) else str(item_id),
            'title': f"ID: {item_id}<br>Name: {item_name}<br>Type: {item_type}",
            'color': node_color,
            'marker': {'radius': 8}
        })
        
        # Process dependencies in first range (DF to HV)
        for col_idx in range(col_start_1, col_end_1 + 1):
            if col_idx < len(row):
                dep_value = row.iloc[col_idx]
                if pd.notna(dep_value) and str(dep_value).strip() != '':
                    edges.append({
                        'from': str(dep_value),
                        'to': str(item_id),
                        'name': f"Dependency"
                    })
        
        # Process dependencies in second range (HW to MN)
        for col_idx in range(col_start_2, col_end_2 + 1):
            if col_idx < len(row):
                dep_value = row.iloc[col_idx]
                if pd.notna(dep_value) and str(dep_value).strip() != '':
                    edges.append({
                        'from': str(dep_value),
                        'to': str(item_id),
                        'name': f"Dependency"
                    })
    
    return nodes, edges

def get_node_color(item_type):
    """Returns a color based on the item type."""
    color_map = {
        'Component': '#FF6B6B',
        'Service': '#4ECDC4',
        'Database': '#45B7D1',
        'API': '#96CEB4',
        'Interface': '#FFEAA7',
        'Process': '#DDA0DD',
        'System': '#98D8C8'
    }
    
    if pd.isna(item_type):
        return '#97C2FC'  # Default color
    
    item_type_str = str(item_type).strip()
    return color_map.get(item_type_str, '#97C2FC')

def generate_diagram(nodes, edges, output_file_name):
    """Configures and saves the network diagram to an HTML file using Highcharts."""
    
    # Convert edges to Highcharts format: [from, to] pairs
    highcharts_data = []
    for edge in edges:
        highcharts_data.append([edge['from'], edge['to']])
    
    # Convert nodes to Highcharts format
    highcharts_nodes = {}
    for node in nodes:
        highcharts_nodes[node['id']] = {
            'id': node['id'],
            'name': node['name'],
            'marker': {
                'radius': 8
            },
            'color': node.get('color', '#97C2FC'),
            'dataLabels': {
                'enabled': True
            }
        }
    
    # Convert to JSON
    data_json = json.dumps(highcharts_data, indent=2)
    nodes_json = json.dumps(list(highcharts_nodes.values()), indent=2)
    
    html_template = f"""<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <title>Mantle Network Diagram</title>
        <script src="https://code.highcharts.com/highcharts.js"></script>
        <script src="https://code.highcharts.com/modules/networkgraph.js"></script>
        <script src="https://code.highcharts.com/modules/accessibility.js"></script>
        
        <link
          href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css"
          rel="stylesheet"
          integrity="sha384-eOJMYsd53ii+scO/bJGFsiCZc+5NDVN2yr8+0RDqr0Ql0h+rP48ckxlpbzKgwra6"
          crossorigin="anonymous"
        />
        <script
          src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js"
          integrity="sha384-JEW9xMcG8R+pH31jmWH6WWP0WintQrMb4s7ZOdauHnUtxwoG2vI5DkLtS3qm9Ekf"
          crossorigin="anonymous"
        ></script>

        <style type="text/css">
            body {{
                background-color: #f5f5f5;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            
            #container {{
                width: 100%;
                height: 900px;
                margin: 0 auto;
                background-color: #222222;
                border-radius: 10px;
                border: 1px solid #ddd;
            }}
            
            .card {{
                margin: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }}
            
            h1 {{
                color: #333;
                margin: 20px 0;
                font-weight: 300;
            }}
        </style>
    </head>

    <body>
        <center>
          <h1>Mantle Network Diagram</h1>
        </center>

        <div class="card" style="width: 100%">
            <div id="container" class="card-body"></div>
        </div>

        <script type="text/javascript">
            // Data for the network graph
            const networkData = {data_json};
            const networkNodes = {nodes_json};

            // Add the nodes option through an event call
            Highcharts.addEvent(
                Highcharts.Series,
                'afterSetOptions',
                function (e) {{
                    if (
                        this instanceof Highcharts.Series.types.networkgraph &&
                        e.options.id === 'mantle-network'
                    ) {{
                        e.options.nodes = networkNodes;
                    }}
                }}
            );

            Highcharts.chart('container', {{
                chart: {{
                    type: 'networkgraph',
                    height: '100%',
                    backgroundColor: '#222222'
                }},
                title: {{
                    text: 'Mantle Network Diagram',
                    align: 'center',
                    style: {{
                        color: '#ffffff',
                        fontSize: '24px',
                        fontWeight: 'bold'
                    }}
                }},
                subtitle: {{
                    text: 'Interactive Force-Directed Network Graph',
                    align: 'center',
                    style: {{
                        color: '#cccccc',
                        fontSize: '14px'
                    }}
                }},
                plotOptions: {{
                    networkgraph: {{
                        keys: ['from', 'to'],
                        layoutAlgorithm: {{
                            enableSimulation: true,
                            friction: -0.9,
                            gravitationalConstant: 0.06,
                            maxIterations: 1000,
                            maxSpeed: 10
                        }},
                        dataLabels: {{
                            enabled: true,
                            linkFormat: '',
                            style: {{
                                fontSize: '10px',
                                fontWeight: 'normal',
                                color: '#ffffff',
                                textOutline: '1px contrast'
                            }}
                        }},
                        point: {{
                            events: {{
                                click: function() {{
                                    console.log('Clicked node:', this.name);
                                }}
                            }}
                        }},
                        link: {{
                            color: '#666666',
                            width: 1,
                            opacity: 0.7
                        }}
                    }}
                }},
                series: [{{
                    accessibility: {{
                        enabled: false
                    }},
                    id: 'mantle-network',
                    data: networkData,
                    color: '#97C2FC',
                    marker: {{
                        radius: 8,
                        lineWidth: 2,
                        lineColor: '#ffffff'
                    }}
                }}],
                credits: {{
                    enabled: false
                }},
                legend: {{
                    enabled: false
                }},
                tooltip: {{
                    headerFormat: '<b>{{point.key}}</b><br>',
                    pointFormat: 'Connections: {{point.linksTo.length}}<br>',
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    style: {{
                        color: '#ffffff'
                    }}
                }}
            }});
        </script>
    </body>
</html>"""

    # Write the HTML file
    with open(output_file_name, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"Successfully generated network diagram: '{output_file_name}'")


# --- Main Execution ---
def main():
    """Main function to run the script from the command line."""
    parser = argparse.ArgumentParser(
        description="Generates an interactive network diagram from a Mantle benefits CSV file using Highcharts.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "csv_file",
        help="Path to the input CSV file (e.g., mantle_benefits_8052.csv)"
    )
    parser.add_argument(
        "-o", "--output",
        default="mantle_network_highcharts.html",
        help="Name for the output HTML file (default: mantle_network_highcharts.html)"
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
