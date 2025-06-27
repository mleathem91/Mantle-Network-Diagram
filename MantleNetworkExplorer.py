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
        
        # If we found the BENEFIT ITEMS row, extract the header row and data
        if benefit_row >= 0:
            # The headers are in the row immediately after BENEFIT ITEMS
            header_row_index = benefit_row + 1
            data_start_index = benefit_row + 2
            
            # Extract the header row
            headers = df.iloc[header_row_index].copy()
            
            # Extract the data rows (starting from the row after headers)
            df = df.iloc[data_start_index:].copy()
            
            # Find the first blank row after the data starts
            blank_row = -1
            for index, row in df.iterrows():
                if row.isnull().all():
                    blank_row = index
                    break
            
            # If we found a blank row, filter to rows before it
            if blank_row >= 0:
                df = df.iloc[:blank_row].copy()
            
            df.reset_index(drop=True, inplace=True)
            
            # Now we have the actual headers - let's print them for debugging
            print("\\nActual column headers found:")
            for i, header in enumerate(headers):
                if pd.notna(header) and str(header).strip():
                    print(f"  Column {i}: '{header}' -> '{str(header).lower().strip()}'")
            
            # Let's also show a sample data row to understand the structure
            print("\\nFirst data row:")
            if len(df) > 0:
                first_row = df.iloc[0]
                for i in range(min(20, len(first_row))):
                    if pd.notna(first_row.iloc[i]):
                        header_name = headers.iloc[i] if i < len(headers) and pd.notna(headers.iloc[i]) else f"Col{i}"
                        print(f"  Column {i} ({header_name}): '{first_row.iloc[i]}'")
        else:
            print("Warning: Could not find 'BENEFIT ITEMS' section. Using all data.")
        
        # Try to find the is_quote column
        is_quote_col = None
        for col in df.columns:
            if col not in COLUMN_MAP.values():  # Skip already mapped columns
                # Check if this column contains 'is_quote' in its values
                col_values = df[col].astype(str).str.lower()
                if any(col_values.str.contains('is_quote', na=False)):
                    # Check the next column for the actual values
                    next_col = col + 1
                    if next_col in df.columns:
                        is_quote_col = next_col
                        print(f"Found is_quote column at index {is_quote_col}")
                        break
        
        # Filter out rows with is_quote = 1
        if is_quote_col is not None and is_quote_col in df.columns:
            before_count = len(df)
            df = df[df[is_quote_col].astype(str) != '1']
            after_count = len(df)
            print(f"Filtered out {before_count - after_count} items with is_quote = 1")
        else:
            print("Warning: Could not find is_quote column for filtering")
        
        print(f"Total items after filtering: {len(df)}")
        
        # Return both the dataframe and the headers
        return df, headers if 'headers' in locals() else None
    except Exception as e:
        print(f"Error reading or processing the CSV file: {e}")
        import traceback
        traceback.print_exc()
        return None

def build_relationship_graph(df, headers=None):
    """Builds a complete relationship graph from the data."""
    relationships = defaultdict(set)  # item_id -> set of dependent item_ids
    reverse_relationships = defaultdict(set)  # item_id -> set of items it depends on
    all_items = {}  # item_id -> item_info
    
    # Get the column ranges for parsing dependencies
    col_start_1 = get_column_index(PARAMS1_COLS[0])
    col_end_1 = get_column_index(PARAMS1_COLS[1])
    col_start_2 = get_column_index(PARAMS2_COLS[0])
    col_end_2 = get_column_index(PARAMS2_COLS[1])
    
    # Now we can properly detect columns using the actual headers
    print("\\nDetecting columns using actual headers...")
    
    # Initialize column indices
    id_item_col = None
    id_event_col = None
    display_group_col = None
    item_name_col = None
    
    # Search through the headers for the columns we need (if headers are available)
    if headers is not None:
        print("\\nSearching for columns in headers...")
        for col_idx, header in enumerate(headers):
            if pd.notna(header):
                header_str = str(header).lower().strip()
                
                # Look for exact matches first, then partial matches
                if header_str == 'id_item':
                    id_item_col = col_idx
                    print(f"*** Found id_item (exact) at column {col_idx}: '{header}'")
                elif header_str == 'id_event':
                    id_event_col = col_idx
                    print(f"*** Found id_event (exact) at column {col_idx}: '{header}'")
                elif header_str == 'display_group':
                    display_group_col = col_idx
                    print(f"*** Found display_group (exact) at column {col_idx}: '{header}'")
                elif header_str == 'item_name':
                    item_name_col = col_idx
                    print(f"*** Found item_name (exact) at column {col_idx}: '{header}'")
        
        # If we didn't find exact matches, try partial matches
        if not all([id_item_col, id_event_col, display_group_col, item_name_col]):
            print("\\nTrying partial matches...")
            for col_idx, header in enumerate(headers):
                if pd.notna(header):
                    header_str = str(header).lower().strip()
                    
                    if id_item_col is None and 'id_item' in header_str:
                        id_item_col = col_idx
                        print(f"*** Found id_item (partial) at column {col_idx}: '{header}'")
                    elif id_event_col is None and 'id_event' in header_str:
                        id_event_col = col_idx
                        print(f"*** Found id_event (partial) at column {col_idx}: '{header}'")
                    elif display_group_col is None and ('display_group' in header_str or 'group' in header_str):
                        display_group_col = col_idx
                        print(f"*** Found display_group (partial) at column {col_idx}: '{header}'")
                    elif item_name_col is None and 'item_name' in header_str:
                        item_name_col = col_idx
                        print(f"*** Found item_name (partial) at column {col_idx}: '{header}'")
        
        # If we still don't have all columns, try pattern-based detection in data
        if not all([id_item_col, id_event_col, display_group_col, item_name_col]) and len(df) > 0:
            print("\\nTrying pattern-based detection in sample data...")
            sample_row = df.iloc[0]
            
            for col_idx in range(min(30, len(sample_row))):
                try:
                    value = str(sample_row.iloc[col_idx]).strip() if pd.notna(sample_row.iloc[col_idx]) else ""
                    
                    # Look for id_event pattern (contains colon like "6:Active retirement")
                    if id_event_col is None and ':' in value and len(value.split(':')) == 2:
                        id_event_col = col_idx
                        print(f"*** Found id_event (pattern) at column {col_idx}: '{value}'")
                    
                    # Look for display_group pattern (descriptive text, not numbers/boolean)
                    elif display_group_col is None and value and len(value) > 5:
                        if not value.isdigit() and value not in ['TRUE', 'FALSE', '0', '1']:
                            # Check if it looks like a group name
                            if any(word in value.lower() for word in ['calculation', 'input', 'benefit', 'service', 'rate']):
                                display_group_col = col_idx
                                print(f"*** Found display_group (pattern) at column {col_idx}: '{value}'")
                except:
                    continue
    else:
        print("No headers available, using simplified approach")
    
    print(f"\\nColumn mapping: id_item={id_item_col}, id_event={id_event_col}, display_group={display_group_col}, item_name={item_name_col}")

    
    # Process each row
    for index, row in df.iterrows():
        # Determine the canonical item_id for this row. This will be the key for relationships.
        # We prioritize the detected 'id_item' column, but fall back to the hardcoded 'ItemID' (col 0).
        if id_item_col is not None and id_item_col < len(row) and pd.notna(row.iloc[id_item_col]):
            item_id = str(row.iloc[id_item_col]).strip()
        else:
            item_id = str(row['ItemID']).strip()

        # Skip rows with no item_id
        if not item_id:
            continue

        item_type = row['ItemType']

        # --- Build the formatted name for display ---
        # This name will be shown in the dropdown.
        # The goal is: id_item - id_event - display_group - item_name
        
        formatted_name_parts = []

        # Part 1: id_item
        # Use the value from the detected id_item_col, or the canonical item_id as a fallback.
        if id_item_col is not None and id_item_col < len(row) and pd.notna(row.iloc[id_item_col]):
             formatted_name_parts.append(str(row.iloc[id_item_col]).strip())
        else:
             formatted_name_parts.append(item_id)

        # Part 2: id_event
        if id_event_col is not None and id_event_col < len(row) and pd.notna(row.iloc[id_event_col]):
            formatted_name_parts.append(str(row.iloc[id_event_col]).strip())

        # Part 3: display_group
        if display_group_col is not None and display_group_col < len(row) and pd.notna(row.iloc[display_group_col]):
            formatted_name_parts.append(str(row.iloc[display_group_col]).strip())

        # Part 4: item_name
        if item_name_col is not None and item_name_col < len(row) and pd.notna(row.iloc[item_name_col]):
            formatted_name_parts.append(str(row.iloc[item_name_col]).strip())
        else:  # Fallback to default ItemName from column 1
            default_item_name = row['ItemName']
            if pd.notna(default_item_name):
                formatted_name_parts.append(str(default_item_name).strip())
        
        # --- End of name building ---

        # De-duplicate parts while preserving order, then join.
        # This prevents issues like "12345 - 12345 - ..."
        unique_parts = [p for p in formatted_name_parts if p] # Filter out empty strings
        unique_parts = list(dict.fromkeys(unique_parts))
        formatted_name = " - ".join(unique_parts)
        
        # For the node label in the graph, we want just the most descriptive part (usually the last one).
        node_display_name = unique_parts[-1] if unique_parts else item_id
        
        # Debug print for the first few items to verify the new logic
        if index < 5:
            print(f"\n--- Item {index+1} ---")
            print(f"  Canonical ID:    {item_id}")
            print(f"  Raw Name Parts:  {formatted_name_parts}")
            print(f"  Unique Parts:    {unique_parts}")
            print(f"  Dropdown Name:   {formatted_name}")
            print(f"  Node Label:      {node_display_name}")

        # Store item information
        all_items[item_id] = {
            'id': item_id,
            'name': formatted_name,
            'node_name': node_display_name,
            'type': str(item_type) if pd.notna(item_type) else 'Unknown',
            'color': get_node_color(item_type)
        }
        
        # Process dependencies in first range (DF to HV)
        for col_idx in range(col_start_1, col_end_1 + 1):
            if col_idx < len(row):
                dep_value = row.iloc[col_idx]
                if pd.notna(dep_value) and str(dep_value).strip() != '':
                    dep_value = str(dep_value).strip()
                    # Extract just the ID part (before the colon) if format is id:name
                    dep_id = dep_value.split(':')[0] if ':' in dep_value else dep_value
                    relationships[dep_id].add(item_id)
                    reverse_relationships[item_id].add(dep_id)
        
        # Process dependencies in second range (HW to MN)
        for col_idx in range(col_start_2, col_end_2 + 1):
            if col_idx < len(row):
                dep_value = row.iloc[col_idx]
                if pd.notna(dep_value) and str(dep_value).strip() != '':
                    dep_value = str(dep_value).strip()
                    # Extract just the ID part (before the colon) if format is id:name
                    dep_id = dep_value.split(':')[0] if ':' in dep_value else dep_value
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
            nodes.append(node_info)
        
        if depth < max_depth:
            # Process items this depends on
            for dep_id in reverse_relationships.get(current_id, []):
                if dep_id not in visited and dep_id in all_items:
                    visited.add(dep_id)
                    queue.append((dep_id, depth + 1))
                    edges.append((dep_id, current_id))
            
            # Process items that depend on this
            for dependent_id in relationships.get(current_id, []):
                if dependent_id not in visited and dependent_id in all_items:
                    visited.add(dependent_id)
                    queue.append((dependent_id, depth + 1))
                    edges.append((current_id, dependent_id))
    
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
    result = load_and_prepare_data(csv_file_path)
    if result is None:
        return
    
    # Handle both old return format (just df) and new format (df, headers)
    if isinstance(result, tuple):
        df, headers = result
    else:
        df, headers = result, None
    
    relationships, reverse_relationships, all_items = build_relationship_graph(df, headers)
    
    # Advanced filtering: Keep only items that have relationships with items where actuarial_liability OR payment_risk OR payment_insured = 1
    def filter_by_actuarial_payment_relationships(relationships, reverse_relationships, all_items, df):
        # Find columns for actuarial_liability, payment_risk, payment_insured
        actuarial_col = None
        payment_risk_col = None
        payment_insured_col = None
        
        for col in df.columns:
            col_values = df[col].astype(str).str.lower()
            if any(col_values.str.contains('actuarial_liability', na=False)):
                actuarial_col = col + 1 if col + 1 in df.columns else None
            elif any(col_values.str.contains('payment_risk', na=False)):
                payment_risk_col = col + 1 if col + 1 in df.columns else None
            elif any(col_values.str.contains('payment_insured', na=False)):
                payment_insured_col = col + 1 if col + 1 in df.columns else None
        
        # Find items where any of these flags = 1
        flagged_items = set()
        for index, row in df.iterrows():
            item_id = str(row['ItemID']).strip()
            if item_id in all_items:
                is_flagged = False
                
                # Check actuarial_liability
                if actuarial_col and actuarial_col < len(row):
                    if str(row.iloc[actuarial_col]).strip() == '1':
                        is_flagged = True
                
                # Check payment_risk
                if payment_risk_col and payment_risk_col < len(row):
                    if str(row.iloc[payment_risk_col]).strip() == '1':
                        is_flagged = True
                
                # Check payment_insured
                if payment_insured_col and payment_insured_col < len(row):
                    if str(row.iloc[payment_insured_col]).strip() == '1':
                        is_flagged = True
                
                if is_flagged:
                    flagged_items.add(item_id)
        
        print(f"Found {{len(flagged_items)}} items with actuarial/payment flags")
        
        # Find all items that have relationships (direct or indirect) with flagged items
        def find_connected_items(start_items, relationships, reverse_relationships, max_depth=10):
            connected = set(start_items)
            queue = deque([(item, 0) for item in start_items])
            
            while queue:
                current_item, depth = queue.popleft()
                if depth >= max_depth:
                    continue
                
                # Add items this depends on
                for dep in reverse_relationships.get(current_item, []):
                    if dep not in connected and dep in all_items:
                        connected.add(dep)
                        queue.append((dep, depth + 1))
                
                # Add items that depend on this
                for dependent in relationships.get(current_item, []):
                    if dependent not in connected and dependent in all_items:
                        connected.add(dependent)
                        queue.append((dependent, depth + 1))
            
            return connected
        
        if flagged_items:
            connected_items = find_connected_items(flagged_items, relationships, reverse_relationships)
            print(f"Found {{len(connected_items)}} items connected to actuarial/payment items")
            
            # Filter all_items, relationships, and reverse_relationships
            filtered_all_items = {{k: v for k, v in all_items.items() if k in connected_items}}
            filtered_relationships = {{k: v.intersection(connected_items) for k, v in relationships.items() if k in connected_items}}
            filtered_reverse_relationships = {{k: v.intersection(connected_items) for k, v in reverse_relationships.items() if k in connected_items}}
            
            # Remove empty relationships
            filtered_relationships = {{k: v for k, v in filtered_relationships.items() if v}}
            filtered_reverse_relationships = {{k: v for k, v in filtered_reverse_relationships.items() if v}}
            
            return filtered_relationships, filtered_reverse_relationships, filtered_all_items
        else:
            print("No actuarial/payment flagged items found, keeping all items")
            return relationships, reverse_relationships, all_items
    
    # Apply the advanced filtering
    relationships, reverse_relationships, all_items = filter_by_actuarial_payment_relationships(
        relationships, reverse_relationships, all_items, df
    )

    # Debug: Print first 5 items and their relationships
    print("Sample of items and their relationships:")
    for idx, item_id in enumerate(list(all_items.keys())[:5]):
        deps = reverse_relationships.get(item_id, set())
        dependents = relationships.get(item_id, set())
        print(f"ItemID: {item_id} | Depends on: {list(deps)} | Dependents: {list(dependents)}")
    print(f"Total items: {len(all_items)}")
    print(f"Total relationships: {sum(len(v) for v in relationships.values())}")

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
                    
                    console.log("Nodes:", nodes.length, nodes);
                    console.log("Edges:", edges.length, edges);
                    
                    // Update statistics
                    document.getElementById('nodeCount').textContent = nodes.length;
                    document.getElementById('edgeCount').textContent = edges.length;
                    document.getElementById('networkStats').style.display = 'block';
                    
                    // Convert nodes for Highcharts
                    const highchartsNodes = nodes.map(node => ({{
                        id: node.id,
                        name: node.node_name || node.name, // Use short name for display
                        fullName: node.name, // Keep full name for tooltip
                        marker: node.marker,
                        color: node.color,
                        dataLabels: {{ enabled: true }},
                        type: node.type
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
                            gravitationalConstant: 0.05,
                            maxIterations: 100,
                            maxSpeed: 5,
                            linkLength: 100
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
                                    const nodeId = this.id;
                                    const nodeName = this.options.fullName || this.name;
                                    const nodeType = this.options.type;
                                    
                                    // Show node info
                                    const info = `
                                        <div style="background: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.3); max-width: 400px;">
                                            <h4>Node Information</h4>
                                            <p><strong>ID:</strong> ${{nodeId}}</p>
                                            <p><strong>Name:</strong> ${{nodeName}}</p>
                                            <p><strong>Type:</strong> ${{nodeType}}</p>
                                            <button onclick="makeMainNode('${{nodeId}}')" style="background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-right: 10px;">Make Main Node</button>
                                            <button onclick="closeNodeInfo()" style="background: #6c757d; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Close</button>
                                        </div>
                                    `;
                                    
                                    // Create or update info popup
                                    let popup = document.getElementById('nodeInfoPopup');
                                    if (!popup) {{
                                        popup = document.createElement('div');
                                        popup.id = 'nodeInfoPopup';
                                        popup.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1000;';
                                        document.body.appendChild(popup);
                                    }}
                                    popup.innerHTML = info;
                                    popup.style.display = 'block';
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
                    pointFormat: '<b>Full Name:</b> {{point.fullName}}<br><b>Type:</b> {{point.type}}<br><b>Connections:</b> {{point.linksTo.length}}<br><i>Click for more options</i>',
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
        
        // Helper functions for node interaction
        function makeMainNode(nodeId) {{
            document.getElementById('itemSelect').value = nodeId;
            closeNodeInfo();
            generateNetwork();
        }}
        
        function closeNodeInfo() {{
            const popup = document.getElementById('nodeInfoPopup');
            if (popup) {{
                popup.style.display = 'none';
            }}
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
