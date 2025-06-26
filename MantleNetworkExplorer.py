import pandas as pd
import json
import os
import argparse
import sys
from collections import defaultdict, deque

# --- Configuration Constants ---
DATA_START_ROW = 24  # The data starts at row 25 (0-indexed)
COLUMN_MAP = {
    0: 'ItemID',
    1: 'ItemName',
    2: 'ItemType'
}
# Column ranges for parsing dependencies
PARAMS1_COLS = ('DF', 'HV')
PARAMS2_COLS = ('HW', 'MN')

# --- Helper Functions ---
def get_column_index(col_str):
    """Converts Excel-style column letters (A, B, AA, DF) to a zero-based index."""
    index = 0
    for char in col_str:
        index = index * 26 + (ord(char.upper()) - ord('A')) + 1
    return index - 1

def load_and_prepare_data(csv_file_path):
    """Loads and prepares the data from the Mantle CSV file."""
    if not os.path.exists(csv_file_path):
        print(f"Error: The file '{csv_file_path}' was not found.")
        return None

    try:
        # Load the CSV file
        df_full = pd.read_csv(csv_file_path, header=None, low_memory=False)
        
        # Use the existing logic to extract data
        df = df_full.iloc[DATA_START_ROW:].copy()
        df.reset_index(drop=True, inplace=True)
        df.rename(columns=COLUMN_MAP, inplace=True)
        
        # Find the row with "BENEFIT ITEMS"
        benefit_row = -1
        for index, row in df.iterrows():
            for col, value in row.items():
                if isinstance(value, str) and "BENEFIT ITEMS" in value:
                    benefit_row = index
                    break
            if benefit_row >= 0:
                break
        
        # If we found the BENEFIT ITEMS row, filter to rows after it
        if benefit_row >= 0:
            df = df.iloc[benefit_row+1:].copy()
            
            # Find the first blank row after BENEFIT ITEMS
            blank_row = -1
            for index, row in df.iterrows():
                if row.isnull().all():
                    blank_row = index
                    break
            
            # If we found a blank row, filter to rows before it
            if blank_row >= 0:
                df = df.iloc[:blank_row].copy()
            
            df.reset_index(drop=True, inplace=True)
        else:
            print("Warning: Could not find 'BENEFIT ITEMS' section. Using all data.")
        
        # Try to find the is_quote column
        is_quote_col = None
        for col in df.columns:
            if col not in COLUMN_MAP.values():  # Skip already mapped columns
                col_values = df[col].astype(str).str.lower()
                if any(col_values.str.contains('is_quote')):
                    # The column after this one should have the values
                    is_quote_col = col + 1
                    break
        
        # Filter out rows with is_quote = 1
        if is_quote_col is not None and is_quote_col in df.columns:
            df = df[df[is_quote_col].astype(str) != '1']
        
        return df
    except Exception as e:
        print(f"Error reading or processing the CSV file: {e}")
        import traceback
        traceback.print_exc()
        return None

def build_relationship_graph(df):
    """Builds a complete relationship graph from the data."""
    relationships = defaultdict(set)  # item_id -> set of dependent item_ids
    reverse_relationships = defaultdict(set)  # item_id -> set of items it depends on
    all_items = {}  # item_id -> item_info
    
    # Get the column ranges for parsing dependencies
    col_start_1 = get_column_index(PARAMS1_COLS[0])
    col_end_1 = get_column_index(PARAMS1_COLS[1])
    col_start_2 = get_column_index(PARAMS2_COLS[0])
    col_end_2 = get_column_index(PARAMS2_COLS[1])
    
    # Find columns for formatting item names
    id_item_col = None
    id_event_col = None
    display_group_col = None
    item_name_col = None
    
    # Look for header rows that might contain column names
    for col in range(len(df.columns)):
        col_values = df.iloc[:min(5, len(df)), col].astype(str).str.lower()
        if any(col_values.str.contains('id_item')):
            id_item_col = col + 1  # The values would be in the next column
        elif any(col_values.str.contains('id_event')):
            id_event_col = col + 1
        elif any(col_values.str.contains('display_group')):
            display_group_col = col + 1
        elif any(col_values.str.contains('item_name')) and col != 1:  # Avoid confusing with the renamed column
            item_name_col = col + 1
    
    # Process each row
    for index, row in df.iterrows():
        item_id = row['ItemID']
        default_item_name = row['ItemName']
        item_type = row['ItemType']
        
        # Skip empty rows
        if pd.isna(item_id) or item_id == '':
            continue
            
        item_id = str(item_id).strip()
        
        # Format item name: id_item - id_event - display_group - item_name
        formatted_name_parts = []
        
        # Add id_item
        if id_item_col is not None and id_item_col < len(row):
            value = row.iloc[id_item_col]
            if pd.notna(value):
                formatted_name_parts.append(str(value))
        else:
            formatted_name_parts.append(item_id)  # Use ItemID as fallback
        
        # Add id_event
        if id_event_col is not None and id_event_col < len(row):
            value = row.iloc[id_event_col]
            if pd.notna(value):
                formatted_name_parts.append(str(value))
        
        # Add display_group
        if display_group_col is not None and display_group_col < len(row):
            value = row.iloc[display_group_col]
            if pd.notna(value):
                formatted_name_parts.append(str(value))
        
        # Add item_name
        if item_name_col is not None and item_name_col < len(row):
            value = row.iloc[item_name_col]
            if pd.notna(value):
                formatted_name_parts.append(str(value))
        else:
            formatted_name_parts.append(str(default_item_name) if pd.notna(default_item_name) else "")
        
        formatted_name = " - ".join(formatted_name_parts)
        
        # Store item information
        all_items[item_id] = {
            'id': item_id,
            'name': formatted_name.strip(),
            'type': str(item_type) if pd.notna(item_type) else 'Unknown',
            'color': get_node_color(item_type)
        }
        
        # Process dependencies in first range (DF to HV)
        for col_idx in range(col_start_1, col_end_1 + 1):
            if col_idx < len(row):
                dep_value = row.iloc[col_idx]
                if pd.notna(dep_value) and str(dep_value).strip() != '':
                    dep_id = str(dep_value).strip()
                    relationships[dep_id].add(item_id)
                    reverse_relationships[item_id].add(dep_id)
        
        # Process dependencies in second range (HW to MN)
        for col_idx in range(col_start_2, col_end_2 + 1):
            if col_idx < len(row):
                dep_value = row.iloc[col_idx]
                if pd.notna(dep_value) and str(dep_value).strip() != '':
                    dep_id = str(dep_value).strip()
                    relationships[dep_id].add(item_id)
                    reverse_relationships[item_id].add(dep_id)
    
    return relationships, reverse_relationships, all_items

def get_related_items(item_id, relationships, reverse_relationships, all_items, max_depth=2):
    """Gets all items related to the given item_id up to max_depth levels."""
    if item_id not in all_items:
        return [], []
    
    visited = set()
    nodes = []
    edges = []
    
    # BFS to find related items
    queue = deque([(item_id, 0)])  # (item_id, depth)
    visited.add(item_id)
    
    while queue:
        current_id, depth = queue.popleft()
        
        # Add current node
        if current_id in all_items:
            node_info = all_items[current_id].copy()
            node_info['depth'] = depth
            node_info['marker'] = {'radius': max(6, 12 - depth * 2)}
            nodes.append(node_info)
        
        if depth < max_depth:
            # Add dependencies (items this depends on)
            for dep_id in reverse_relationships.get(current_id, set()):
                if dep_id not in visited and dep_id in all_items:
                    visited.add(dep_id)
                    queue.append((dep_id, depth + 1))
                    edges.append([dep_id, current_id])
            
            # Add dependents (items that depend on this)
            for dependent_id in relationships.get(current_id, set()):
                if dependent_id not in visited and dependent_id in all_items:
                    visited.add(dependent_id)
                    queue.append((dependent_id, depth + 1))
                    edges.append([current_id, dependent_id])
    
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
        return '#97C2FC'
    
    item_type_str = str(item_type).strip()
    return color_map.get(item_type_str, '#97C2FC')

def generate_web_interface(csv_file_path, output_file_name):
    """Generates an interactive web interface for exploring the network."""
    
    # Load and process data
    df = load_and_prepare_data(csv_file_path)
    if df is None:
        return
    
    relationships, reverse_relationships, all_items = build_relationship_graph(df)
    
    # Get list of all item IDs for the dropdown
    item_list = sorted(all_items.keys())
    item_options = []
    # Remove the 100 item limit to include all items
    for item_id in item_list:
        item_info = all_items[item_id]
        item_options.append({
            'id': item_id,
            'name': item_info['name'],
            'type': item_info['type']
        })
    
    # Convert data to JSON for embedding
    all_items_json = json.dumps(all_items)
    relationships_json = json.dumps({k: list(v) for k, v in relationships.items()})
    reverse_relationships_json = json.dumps({k: list(v) for k, v in reverse_relationships.items()})
    item_options_json = json.dumps(item_options, indent=2)
    
    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Mantle Network Explorer</title>
    <script src="https://code.highcharts.com/highcharts.js"></script>
    <script src="https://code.highcharts.com/modules/networkgraph.js"></script>
    <script src="https://code.highcharts.com/modules/accessibility.js"></script>
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js"></script>
    
    <style type="text/css">
        body {{
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        .control-panel {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
            margin: 20px;
        }}
        
        #container {{
            width: 800px;
            height: 800px;
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
        
        .form-select {{
            max-width: 400px;
        }}
        
        .stats {{
            background: #e9ecef;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }}
        
        .loading {{
            display: none;
            text-align: center;
            padding: 20px;
        }}
        
        .spinner-border {{
            width: 3rem;
            height: 3rem;
        }}
    </style>
</head>

<body>
    <center>
        <h1>Mantle Network Explorer</h1>
    </center>

    <div class="control-panel">
        <div class="row">
            <div class="col-md-4">
                <label for="itemSelect" class="form-label">Select Item ID:</label>
                <select class="form-select" id="itemSelect">
                    <option value="">Choose an item...</option>
                </select>
            </div>
            <div class="col-md-3">
                <label for="depthSelect" class="form-label">Relationship Depth:</label>
                <select class="form-select" id="depthSelect">
                    <option value="1">1 - Direct relationships only</option>
                    <option value="2" selected>2 - Include 2nd level</option>
                    <option value="3">3 - Include 3rd level</option>
                    <option value="4">4 - Include 4th level</option>
                </select>
            </div>
            <div class="col-md-3">
                <label class="form-label">&nbsp;</label>
                <button class="btn btn-primary form-control" onclick="generateNetwork()">Generate Network</button>
            </div>
            <div class="col-md-2">
                <label class="form-label">&nbsp;</label>
                <button class="btn btn-secondary form-control" onclick="clearNetwork()">Clear</button>
            </div>
        </div>
        
        <div class="stats" id="networkStats" style="display: none;">
            <strong>Network Statistics:</strong>
            <span id="nodeCount">0</span> nodes, 
            <span id="edgeCount">0</span> edges
        </div>
    </div>

    <div class="loading" id="loadingIndicator">
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <p>Generating network diagram...</p>
    </div>

    <div class="card">
        <div id="container" class="card-body"></div>
    </div>

    <script type="text/javascript">
        // Data from Python
        const allItems = {all_items_json};
        const relationships = {relationships_json};
        const reverseRelationships = {reverse_relationships_json};
        const itemOptions = {item_options_json};
        
        let currentChart = null;
        
        // Populate the item dropdown
        function populateItemSelect() {{
            const select = document.getElementById('itemSelect');
            
            itemOptions.forEach(item => {{
                const option = document.createElement('option');
                option.value = item.id;
                option.textContent = `${{item.id}} - ${{item.name}} (${{item.type}})`;
                select.appendChild(option);
            }});
        }}
        
        // Get related items with BFS
        function getRelatedItems(itemId, maxDepth) {{
            if (!allItems[itemId]) {{
                return {{ nodes: [], edges: [] }};
            }}
            
            const visited = new Set();
            const nodes = [];
            const edges = [];
            const queue = [[itemId, 0]]; // [item_id, depth]
            
            visited.add(itemId);
            
            while (queue.length > 0) {{
                const [currentId, depth] = queue.shift();
                
                // Add current node
                if (allItems[currentId]) {{
                    const nodeInfo = {{ ...allItems[currentId] }};
                    nodeInfo.depth = depth;
                    nodeInfo.marker = {{ radius: Math.max(6, 12 - depth * 2) }};
                    
                    // Highlight the root node
                    if (depth === 0) {{
                        nodeInfo.color = '#FF4444';
                        nodeInfo.marker.radius = 15;
                    }}
                    
                    nodes.push(nodeInfo);
                }}
                
                if (depth < maxDepth) {{
                    // Add dependencies (items this depends on)
                    const deps = reverseRelationships[currentId] || [];
                    deps.forEach(depId => {{
                        if (!visited.has(depId) && allItems[depId]) {{
                            visited.add(depId);
                            queue.push([depId, depth + 1]);
                            edges.push([depId, currentId]);
                        }}
                    }});
                    
                    // Add dependents (items that depend on this)
                    const dependents = relationships[currentId] || [];
                    dependents.forEach(dependentId => {{
                        if (!visited.has(dependentId) && allItems[dependentId]) {{
                            visited.add(dependentId);
                            queue.push([dependentId, depth + 1]);
                            edges.push([currentId, dependentId]);
                        }}
                    }});
                }}
            }}
            
            return {{ nodes, edges }};
        }}
        
        // Generate network diagram
        function generateNetwork() {{
            const itemId = document.getElementById('itemSelect').value;
            const depth = parseInt(document.getElementById('depthSelect').value);
            
            if (!itemId) {{
                alert('Please select an item ID');
                return;
            }}
            
            // Show loading indicator
            document.getElementById('loadingIndicator').style.display = 'block';
            document.getElementById('container').style.opacity = '0.3';
            
            // Small delay to allow UI to update
            setTimeout(() => {{
                try {{
                    const {{ nodes, edges }} = getRelatedItems(itemId, depth);
                    
                    // Update statistics
                    document.getElementById('nodeCount').textContent = nodes.length;
                    document.getElementById('edgeCount').textContent = edges.length;
                    document.getElementById('networkStats').style.display = 'block';
                    
                    // Convert nodes for Highcharts
                    const highchartsNodes = nodes.map(node => ({{
                        id: node.id,
                        name: node.name,
                        marker: node.marker,
                        color: node.color,
                        dataLabels: {{ enabled: true }}
                    }}));
                    
                    // Create/update chart
                    createChart(edges, highchartsNodes);
                    
                }} catch (error) {{
                    console.error('Error generating network:', error);
                    alert('Error generating network diagram');
                }} finally {{
                    // Hide loading indicator
                    document.getElementById('loadingIndicator').style.display = 'none';
                    document.getElementById('container').style.opacity = '1';
                }}
            }}, 100);
        }}
        
        // Create Highcharts network
        function createChart(edges, nodes) {{
            // Add nodes through event
            Highcharts.addEvent(Highcharts.Series, 'afterSetOptions', function (e) {{
                if (this instanceof Highcharts.Series.types.networkgraph && e.options.id === 'network') {{
                    e.options.nodes = nodes;
                }}
            }});
            
            // Destroy existing chart
            if (currentChart) {{
                currentChart.destroy();
            }}
            
            currentChart = Highcharts.chart('container', {{
                chart: {{
                    type: 'networkgraph',
                    height: '100%',
                    backgroundColor: '#222222'
                }},
                title: {{
                    text: 'Network Relationships',
                    style: {{ color: '#ffffff', fontSize: '20px' }}
                }},
                plotOptions: {{
                    networkgraph: {{
                        keys: ['from', 'to'],
                        layoutAlgorithm: {{
                            enableSimulation: true,
                            friction: -0.9,
                            gravitationalConstant: 0.1,
                            maxIterations: 200,
                            maxSpeed: 10
                        }},
                        dataLabels: {{
                            enabled: true,
                            style: {{
                                fontSize: '9px',
                                color: '#ffffff',
                                textOutline: '1px contrast'
                            }}
                        }},
                        point: {{
                            events: {{
                                click: function() {{
                                    console.log('Clicked:', this.name, '(', this.id, ')');
                                    // Could add functionality to drill down from here
                                }}
                            }}
                        }},
                        link: {{
                            color: '#666666',
                            width: 2,
                            opacity: 0.8
                        }}
                    }}
                }},
                series: [{{
                    id: 'network',
                    data: edges,
                    marker: {{
                        lineWidth: 2,
                        lineColor: '#ffffff'
                    }}
                }}],
                credits: {{ enabled: false }},
                legend: {{ enabled: false }},
                tooltip: {{
                    headerFormat: '<b>{{point.key}}</b><br>',
                    pointFormat: 'Type: {{point.type}}<br>Connections: {{point.linksTo.length}}',
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    style: {{ color: '#ffffff' }}
                }}
            }});
        }}
        
        // Clear network
        function clearNetwork() {{
            if (currentChart) {{
                currentChart.destroy();
                currentChart = null;
            }}
            document.getElementById('networkStats').style.display = 'none';
            document.getElementById('itemSelect').value = '';
        }}
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {{
            populateItemSelect();
        }});
    </script>
</body>
</html>"""

    # Write the HTML file
    with open(output_file_name, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"Successfully generated interactive web interface: '{output_file_name}'")
    print(f"Features:")
    print(f"- Select from {len(item_options)} available items")
    print(f"- Adjustable relationship depth (1-4 levels)")
    print(f"- Real-time network generation")
    print(f"- Network statistics display")

# --- Main Execution ---
def main():
    """Main function to run the script from the command line."""
    parser = argparse.ArgumentParser(
        description="Generates an interactive web interface for exploring the Mantle network.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "csv_file",
        help="Path to the input CSV file (e.g., mantle_benefits_8052.csv)"
    )
    parser.add_argument(
        "-o", "--output",
        default="mantle_network_explorer.html",
        help="Name for the output HTML file (default: mantle_network_explorer.html)"
    )
    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    args = parser.parse_args()

    # Generate the web interface
    generate_web_interface(args.csv_file, args.output)

if __name__ == "__main__":
    main()
