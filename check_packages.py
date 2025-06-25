import os
import site

# Check what's in site-packages
site_packages = site.getsitepackages()[0] if site.getsitepackages() else None
if not site_packages:
    # For virtual environments
    site_packages = os.path.join(os.path.dirname(os.__file__), 'site-packages')

print(f"Site packages directory: {site_packages}")

if os.path.exists(site_packages):
    packages = [d for d in os.listdir(site_packages) if 'highchart' in d.lower()]
    print(f"Highchart-related packages: {packages}")
    
    # Try different import possibilities
    import_attempts = [
        'python_highcharts',
        'pythonhighcharts', 
        'highcharts_python',
        'highchart'
    ]
    
    for module_name in import_attempts:
        try:
            module = __import__(module_name)
            print(f"Successfully imported: {module_name}")
            print(f"Module attributes: {[attr for attr in dir(module) if not attr.startswith('_')]}")
            break
        except ImportError:
            print(f"Failed to import: {module_name}")
