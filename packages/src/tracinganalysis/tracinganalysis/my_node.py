import sys
sys.path.insert(0, '/home/ubuntu/tracing/src/tracetools_analysis/tracetools_analysis')
from tracetools_analysis.utils.ros2 import Ros2DataModelUtil
from tracetools_analysis.processor.ros2 import Ros2Handler
from tracetools_analysis.loading import load_file
import pandas as pd
import numpy as np
from bokeh.models import PrintfTickFormatter
from bokeh.models import DatetimeTickFormatter
from bokeh.models import ColumnDataSource
from bokeh.layouts import row
from bokeh.io import show
from bokeh.plotting import output_notebook
from bokeh.plotting import figure
import datetime as dt
# Add paths to tracetools_analysis and tracetools_read.
# There are two options:
#   1. from source, assuming a workspace with:
#       src/tracetools_analysis/
#       src/ros2/ros2_tracing/tracetools_read/
sys.path.insert(0, '../')
sys.path.insert(0, '../../../ros2/ros2_tracing/tracetools_read/')
#   2. from Debian packages, setting the right ROS 2 distro:
# ROS_DISTRO = 'rolling'
# sys.path.insert(0, f'/opt/ros/{ROS_DISTRO}/lib/python3.8/site-packages')
module_name = Ros2DataModelUtil.__module__

# Import the module dynamically
module = __import__(module_name)

# Print the file path
print(module.__file__)


def main():
    print('Hi from tracinganalysis.')


if __name__ == '__main__':
    main()
    path = '~/workspace/traces/ABCABCABC/ust/'
    events = load_file(path)
    # handler = Ros2Handler.process(events)
    # handler.data.print_data()
    # data_util = Ros2DataModelUtil(handler.data)
    # print(data_util)
    # data_util.get_callback_symbols()
    from tracetools_analysis.loading import load_file
    from tracetools_analysis.processor import Processor
    from tracetools_analysis.processor.cpu_time import CpuTimeHandler
    from tracetools_analysis.processor.ros2 import Ros2Handler
    from tracetools_analysis.utils.cpu_time import CpuTimeDataModelUtil
    from tracetools_analysis.utils.ros2 import Ros2DataModelUtil

    # Load trace directory or converted trace file
    # events = load_file('/path/to/trace/or/converted/file')

    # Process
    ros2_handler = Ros2Handler()
    cpu_handler = CpuTimeHandler()

    Processor(ros2_handler).process(events)
    # Processor(ros2_handler, cpu_handler).process(events)

    # Use data model utils to extract information
    ros2_util = Ros2DataModelUtil(ros2_handler.data)
    # cpu_util = CpuTimeDataModelUtil(cpu_handler.data)

    callback_symbols = ros2_util.get_callback_symbols()
    callback_object, callback_symbol = list(callback_symbols.items())[0]
    print(len(list(callback_symbols.items())))
    callback_durations = ros2_util.get_callback_durations(callback_object)
    #print(callback_symbols)
    # time_per_thread = cpu_util.get_time_per_thread()
    # ...

    # Display, e.g., with bokeh, matplotlib, print, etc.
    print(callback_symbol)
    print(callback_durations)
    timing = []
    callbacks = list(callback_symbols.items())
    for callback_object, callback_symbol in callbacks:
        callback_durations = ros2_util.get_callback_durations(callback_object)
        #print(callback_durations["duration"])
        avg = np.array(callback_durations["duration"]).mean()
        # print(callback_symbol + ": " + str(avg))
        timing.append({"obj": callback_symbol, "avg": avg})
    for entry in sorted(timing, key=lambda x: x["avg"]):
        callback_symbol = entry["obj"]
        avg = entry["avg"]
        print(callback_symbol + ": " + str(avg))
        


    # print(time_per_thread)
    # ...
