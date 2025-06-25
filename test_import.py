try:
    from highcharts import Highchart
    print("Success: highcharts.Highchart imported")
except ImportError as e:
    print(f"Failed to import highcharts.Highchart: {e}")

try:
    import highcharts
    print("Success: highcharts module imported")
    print(f"Available attributes: {dir(highcharts)}")
except ImportError as e:
    print(f"Failed to import highcharts module: {e}")
