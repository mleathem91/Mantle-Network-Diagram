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
            'marker': {
                'radius': 8
            },
            'color': node.get('color', '#97C2FC')
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
            #container {{
                width: 100%;
                height: 900px;
                margin: 0 auto;
            }}
            
            .card {{
                margin: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
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
                        color: '#ffffff'
                    }}
                }},
                subtitle: {{
                    text: 'Interactive Force-Directed Network Graph',
                    align: 'center',
                    style: {{
                        color: '#cccccc'
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
                        radius: 8
                    }}
                }}],
                credits: {{
                    enabled: false
                }},
                legend: {{
                    enabled: false
                }}
            }});
        </script>
    </body>
</html>"""

    # Write the HTML file
    with open(output_file_name, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"Successfully generated network diagram: '{{output_file_name}}'")


def generate_diagram_old_vis_js(nodes, edges, output_file_name):
    """Configures and saves the network diagram to an HTML file using vis.js."""
    
    # Convert nodes and edges to vis.js format
    vis_nodes = []
    vis_edges = []
    
    # Convert nodes
    for node in nodes:
        vis_node = {
            'id': node['id'],
            'label': node['name'],
            'title': node['title'],
            'color': node['color'],
            'size': node['marker']['radius'],
            'shape': 'dot',
            'font': {'color': 'white'}
        }
        vis_nodes.append(vis_node)
    
    # Convert edges  
    for edge in edges:
        vis_edge = {
            'from': edge['from'],
            'to': edge['to'],
            'label': edge.get('name', '')
        }
        vis_edges.append(vis_edge)
    
    # Create the HTML template with vis.js
    html_template = f"""<html>
    <head>
        <meta charset="utf-8">
        
            <script src="lib/bindings/utils.js"></script>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/dist/vis-network.min.css" integrity="sha512-WgxfT5LWjfszlPHXRmBWHkV2eceiWTOBvrKCNbdgDYTHrT2AeLCGbF4sZlZw3UMN3WtL0tGUoIAKsu8mllg/XA==" crossorigin="anonymous" referrerpolicy="no-referrer" />
            <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js" integrity="sha512-LnvoEWDFrqGHlHmDD2101OrLcbsfkrzoSpvtSQtxK3RMnRV0eOkhhBN2dXHKRrUU8p2DGRTk35n4O8nWSVe1mQ==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
            
        
<center>
<h1></h1>
</center>

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


        <center>
          <h1>Mantle Network Diagram</h1>
        </center>
        <style type="text/css">

             #mynetwork {{
                 width: 100%;
                 height: 900px;
                 background-color: #222222;
                 border: 1px solid lightgray;
                 position: relative;
                 float: left;
             }}

             
             #loadingBar {{
                 position:absolute;
                 top:0px;
                 left:0px;
                 width: 100%;
                 height: 900px;
                 background-color:rgba(200,200,200,0.8);
                 -webkit-transition: all 0.5s ease;
                 -moz-transition: all 0.5s ease;
                 -ms-transition: all 0.5s ease;
                 -o-transition: all 0.5s ease;
                 transition: all 0.5s ease;
                 opacity:1;
             }}

             #bar {{
                 position:absolute;
                 top:0px;
                 left:0px;
                 width:20px;
                 height:20px;
                 margin:auto auto auto auto;
                 border-radius:11px;
                 border:2px solid rgba(30,30,30,0.05);
                 background: rgb(0, 173, 246);
                 box-shadow: 2px 0px 4px rgba(0,0,0,0.4);
             }}

             #border {{
                 position:absolute;
                 top:10px;
                 left:10px;
                 width:500px;
                 height:23px;
                 margin:auto auto auto auto;
                 box-shadow: 0px 0px 4px rgba(0,0,0,0.2);
                 border-radius:10px;
             }}

             #text {{
                 position:absolute;
                 top:8px;
                 left:530px;
                 width:30px;
                 height:50px;
                 margin:auto auto auto auto;
                 font-size:22px;
                 color: #000000;
             }}

             div.outerBorder {{
                 position:relative;
                 top:400px;
                 width:600px;
                 height:44px;
                 margin:auto auto auto auto;
                 border:8px solid rgba(0,0,0,0.1);
                 background: rgb(252,252,252);
                 background: -moz-linear-gradient(top,  rgba(252,252,252,1) 0%, rgba(237,237,237,1) 100%);
                 background: -webkit-gradient(linear, left top, left bottom, color-stop(0%,rgba(252,252,252,1)), color-stop(100%,rgba(237,237,237,1)));
                 background: -webkit-linear-gradient(top,  rgba(252,252,252,1) 0%,rgba(237,237,237,1) 100%);
                 background: -o-linear-gradient(top,  rgba(252,252,252,1) 0%,rgba(237,237,237,1) 100%);
                 background: -ms-linear-gradient(top,  rgba(252,252,252,1) 0%,rgba(237,237,237,1) 100%);
                 background: linear-gradient(to bottom,  rgba(252,252,252,1) 0%,rgba(237,237,237,1) 100%);
                 filter: progid:DXImageTransform.Microsoft.gradient( startColorstr='#fcfcfc', endColorstr='#ededed',GradientType=0 );
                 border-radius:72px;
                 box-shadow: 0px 0px 10px rgba(0,0,0,0.2);
             }}
             
        </style>
    </head>

    <body>
        <div class="card" style="width: 100%">
            <div id="mynetwork" class="card-body"></div>
        </div>

        <div id="loadingBar">
              <div class="outerBorder">
                <div id="text">0%</div>
                <div id="border">
                  <div id="bar"></div>
                </div>
              </div>
        </div>

        <script type="text/javascript">
              var edges;
              var nodes;
              var allNodes;
              var allEdges;
              var nodeColors;
              var originalNodes;
              var network;
              var container;
              var options, data;
              var seed = 2;

              function drawGraph() {{
                  var container = document.getElementById('mynetwork');

                  nodes = new vis.DataSet({json.dumps(vis_nodes)});
                  edges = new vis.DataSet({json.dumps(vis_edges)});

                  nodeColors = {{}};
                  allNodes = nodes.get({{ returnType: "Object" }});
                  for (nodeId in allNodes) {{
                    nodeColors[nodeId] = allNodes[nodeId].color;
                  }}
                  allEdges = edges.get({{ returnType: "Object" }});
                  
                  data = {{nodes: nodes, edges: edges}};

                  var options = {{
                      "nodes": {{
                          "font": {{"size": 12, "face": "Tahoma"}},
                          "borderWidth": 2
                      }}, 
                      "edges": {{
                          "width": 0.5, 
                          "arrows": {{"to": {{"enabled": true, "scaleFactor": 0.5}}}}, 
                          "color": {{"inherit": true}}, 
                          "smooth": {{"type": "continuous"}}
                      }}, 
                      "interaction": {{
                          "hover": true, 
                          "hoverConnectedEdges": true, 
                          "navigationButtons": true, 
                          "keyboard": true, 
                          "tooltipDelay": 200
                      }}, 
                      "physics": {{
                          "enabled": true, 
                          "barnesHut": {{
                              "gravitationalConstant": -25000, 
                              "centralGravity": 0.1, 
                              "springLength": 120, 
                              "springConstant": 0.05, 
                              "damping": 0.09, 
                              "avoidOverlap": 0.5
                          }}, 
                          "stabilization": {{
                              "enabled": true, 
                              "iterations": 1000, 
                              "fit": true
                          }}, 
                          "solver": "barnesHut"
                      }}
                  }};

                  network = new vis.Network(container, data, options);

                  // Add a fallback timeout in case stabilization events don't fire (Edge compatibility)
                  var stabilizationTimeout = setTimeout(function() {{
                      console.log("Stabilization timeout reached - forcing completion");
                      document.getElementById('text').innerHTML = '100%';
                      document.getElementById('bar').style.width = '496px';
                      document.getElementById('loadingBar').style.opacity = 0;
                      setTimeout(function () {{document.getElementById('loadingBar').style.display = 'none';}}, 1500);
                  }}, 15000); // 15 second timeout

                  network.on("stabilizationProgress", function(params) {{
                      console.log("Stabilization progress:", Math.round((params.iterations/params.total)*100) + "%");
                      document.getElementById('loadingBar').removeAttribute("style");
                      var maxWidth = 496;
                      var minWidth = 20;
                      var widthFactor = params.iterations/params.total;
                      var width = Math.max(minWidth,maxWidth * widthFactor);
                      document.getElementById('bar').style.width = width + 'px';
                      document.getElementById('text').innerHTML = Math.round(widthFactor*100) + '%';
                  }});
                  
                  network.once("stabilizationIterationsDone", function() {{
                      console.log("Stabilization complete!");
                      clearTimeout(stabilizationTimeout); // Clear the fallback timeout
                      document.getElementById('text').innerHTML = '100%';
                      document.getElementById('bar').style.width = '496px';
                      document.getElementById('loadingBar').style.opacity = 0;
                      setTimeout(function () {{document.getElementById('loadingBar').style.display = 'none';}}, 1500);
                  }});

                  return network;
              }}
              
              drawGraph();
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