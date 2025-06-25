# Mantle Network Diagram Generator

A powerful tool for generating interactive network diagrams from Mantle benefits CSV data. This project provides multiple visualization options, including a focused interactive explorer and full network views.

## 🚀 Features

- **Interactive Network Explorer** - Select specific items and relationship depths
- **Full Network Visualization** - Complete overview of all relationships
- **Multiple Chart Libraries** - Support for both Highcharts and vis.js
- **Microsoft Edge Compatible** - Optimized for all modern browsers
- **Configurable Depth** - Explore 1-4 levels of relationships
- **Real-time Generation** - Fast, dynamic network creation
- **Professional UI** - Modern, responsive web interface

## 📁 Project Structure

- `MantleNetworkExplorer.py` - **Main interactive explorer** (Recommended)
- `MantleNetworkDiagram_Highcharts.py` - Full network with Highcharts
- `MantleNetworkDiagram.py` - Original vis.js implementation
- `mantle_benefits_8052.csv` - Sample input data
- `requirements.txt` - Python dependencies

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/MantleNetworkDiagram.git
   cd MantleNetworkDiagram
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## 🎯 Quick Start

### Interactive Explorer (Recommended)

Generate an interactive web interface for exploring specific items and their relationships:

```bash
python MantleNetworkExplorer.py mantle_benefits_8052.csv
```

Open `mantle_network_explorer.html` in your browser and:
1. Select an Item ID from the dropdown
2. Choose relationship depth (1-4 levels)
3. Click "Generate Network"
4. Explore the interactive diagram

### Full Network Diagram

Generate a complete network visualization:

```bash
# Highcharts version (Edge compatible)
python MantleNetworkDiagram_Highcharts.py mantle_benefits_8052.csv

# vis.js version (original)
python MantleNetworkDiagram.py mantle_benefits_8052.csv
```

## 📊 Usage Examples

### Basic Usage
```bash
# Generate interactive explorer
python MantleNetworkExplorer.py data.csv

# Generate full network with custom output
python MantleNetworkDiagram_Highcharts.py data.csv -o my_network.html
```

### Command Line Options
```bash
# Interactive Explorer
python MantleNetworkExplorer.py <csv_file> [-o output.html]

# Full Network
python MantleNetworkDiagram_Highcharts.py <csv_file> [-o output.html]
```

## 🎨 Visualization Types

### 1. Interactive Explorer
- **Best for:** Focused analysis of specific items
- **Performance:** Very fast (1-3 seconds)
- **Features:** Item selection, depth control, statistics
- **Browser:** Excellent Edge compatibility

### 2. Highcharts Full Network
- **Best for:** Complete network overview
- **Performance:** Fast for medium networks
- **Features:** Professional styling, tooltips, zoom
- **Browser:** Excellent Edge compatibility

### 3. vis.js Full Network
- **Best for:** Large networks with physics simulation
- **Performance:** Slower, may have Edge issues
- **Features:** Advanced physics, stabilization progress
- **Browser:** Better in Chrome/Firefox

## 🔧 Configuration

### CSV File Format
The script expects CSV files with:
- **Row 25+**: Data starts (configurable via `DATA_START_ROW`)
- **Column A**: ItemID
- **Column B**: ItemName  
- **Column C**: ItemType
- **Columns DF-HV**: First dependency range
- **Columns HW-MN**: Second dependency range

### Customization
Edit the configuration constants in the Python files:
```python
DATA_START_ROW = 24  # Adjust data start row
PARAMS1_COLS = ('DF', 'HV')  # First dependency range
PARAMS2_COLS = ('HW', 'MN')  # Second dependency range
```

## 🎨 Node Colors

Items are automatically colored by type:
- **Component**: Red (#FF6B6B)
- **Service**: Teal (#4ECDC4)
- **Database**: Blue (#45B7D1)
- **API**: Green (#96CEB4)
- **Interface**: Yellow (#FFEAA7)
- **Process**: Purple (#DDA0DD)
- **System**: Light Green (#98D8C8)
- **Default**: Light Blue (#97C2FC)

## 🚀 Performance Tips

### For Large Networks:
1. **Use the Interactive Explorer** for focused analysis
2. **Start with depth 1-2** and increase gradually
3. **Filter by item type** if needed
4. **Use Highcharts version** for better performance

### Browser Recommendations:
- **Microsoft Edge**: Use Highcharts versions
- **Chrome/Firefox**: All versions work well
- **Internet Explorer**: Not supported

## 🐛 Troubleshooting

### Common Issues:

**Loading stuck at 0% in Edge:**
- Use `MantleNetworkExplorer.py` or `MantleNetworkDiagram_Highcharts.py`
- Avoid the original vis.js version in Edge

**Network too large:**
- Use the Interactive Explorer with limited depth
- Filter data before processing
- Consider network optimization

**Dependencies not found:**
- Ensure `requirements.txt` packages are installed
- Check CSV file format and column mappings

## 📝 Output Files

- `mantle_network_explorer.html` - Interactive explorer interface
- `mantle_network_highcharts.html` - Full Highcharts network
- `mantle_network.html` - Original vis.js network

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support, please open an issue on GitHub or contact the development team.

## 🔄 Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history and updates.
