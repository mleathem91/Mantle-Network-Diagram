# Mantle Network Explorer

This project provides an interactive network visualization tool to explore complex relationships within the Mantle network, focusing on benefit items.

## Features

*   **Interactive Network Graph**: Visualize dependencies and relationships between items in the Mantle network.
*   **Benefit Items Focus**: The visualization is specifically tailored to display "Benefit Items" from the data source.
*   **Dynamic Filtering**:
    *   Items with `is_quote = 1` are excluded.
*   **Customizable Display**:
    *   Item names are formatted as: `id_item - id_event - display_group - item_name`.
*   **Adjustable Depth**: Explore relationships up to 4 levels deep.
*   **Web-Based UI**: A user-friendly web interface powered by Highcharts.js.

## How to Use

1.  **Run the Script**:
    ```bash
    python MantleNetworkExplorer.py mantle_benefits_8052.csv
    ```
2.  **Open the HTML File**:
    Open the generated `mantle_network_explorer.html` file in your web browser to view and interact with the network diagram.

## File Descriptions

*   `MantleNetworkExplorer.py`: The main Python script to process the data and generate the HTML interface.
*   `mantle_benefits_8052.csv`: The data source containing the Mantle network information.
*   `mantle_network_explorer.html`: The output HTML file for the visualization.
*   `requirements.txt`: Required Python packages.
*   `CHANGELOG.md`: A log of changes to the project.
*   `LICENSE`: The project's license.
