# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-06-25

### Added
- **Interactive Network Explorer** (`MantleNetworkExplorer.py`) - Major new feature
  - Item selection dropdown with ID, name, and type display
  - Configurable relationship depth (1-4 levels)
  - Real-time network generation with loading indicators
  - Network statistics display (node/edge counts)
  - Clear function to reset visualization
  - Focused visualization for performance and usability
- **Highcharts Implementation** (`MantleNetworkDiagram_Highcharts.py`)
  - Full network visualization using Highcharts
  - Excellent Microsoft Edge compatibility
  - Professional styling and tooltips
  - Force-directed layout with physics simulation
- **Enhanced Documentation**
  - Comprehensive README with usage examples
  - Installation instructions and troubleshooting
  - Performance tips and browser recommendations
  - Node color coding documentation

### Improved
- **Microsoft Edge Compatibility**
  - Fixed loading bar stuck at 0% issue
  - Added fallback timeout mechanisms
  - Improved event handling for stabilization
  - Console logging for debugging
- **Performance Optimization**
  - Faster loading times (1-3 seconds vs 30+ seconds)
  - Efficient BFS algorithm for relationship traversal
  - Client-side processing for instant responses
  - Reduced network complexity for focused views
- **User Interface**
  - Modern Bootstrap-based design
  - Responsive layout for different screen sizes
  - Professional color scheme and typography
  - Loading indicators and user feedback

### Changed
- **Project Structure**
  - Multiple implementation options for different use cases
  - Modular approach with specialized scripts
  - Better separation of concerns
- **Data Processing**
  - Improved relationship graph building
  - Enhanced node and edge data structures
  - Better error handling and validation
- **Visualization Options**
  - Three different chart implementations (Interactive, Highcharts, vis.js)
  - Configurable depth and filtering options
  - Dynamic network generation

### Fixed
- **Browser Compatibility Issues**
  - Resolved Microsoft Edge loading problems
  - Fixed stabilization event handling
  - Improved cross-browser performance
- **Performance Issues**
  - Addressed large network rendering problems
  - Optimized data processing and visualization
  - Reduced memory usage and loading times
- **User Experience**
  - Better error messages and feedback
  - Improved loading states and indicators
  - Enhanced tooltips and interactions

### Technical Details
- **Dependencies**: Added pandas for data processing
- **Chart Libraries**: 
  - Highcharts 9.1.2+ for network graphs
  - vis.js 9.1.2 for legacy support
  - Bootstrap 5.0.0 for UI components
- **Browser Support**:
  - Microsoft Edge: Excellent (Highcharts versions)
  - Chrome/Firefox: Excellent (all versions)
  - Safari: Good (Highcharts versions)
  - Internet Explorer: Not supported

## [1.0.0] - 2025-06-24

### Added
- Initial implementation with vis.js
- Basic network diagram generation
- CSV file processing
- Node and edge creation
- Physics-based layout
- Interactive network exploration

### Features
- Force-directed graph layout
- Node highlighting and selection
- Edge visualization with arrows
- Loading progress indicator
- Stabilization animation
- Export to HTML format
