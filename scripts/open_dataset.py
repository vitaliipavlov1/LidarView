"""Open a sample PCAP in LidarView with the correct reader and sensor model.

Run it at startup:
    ./scripts/run_lidarview.sh --script scripts/open_dataset.py
or paste the same calls into the GUI's Python Shell (View -> Python Shell).

Exists because LidarView cannot infer the sensor for these legacy captures:
picking the file alone yields a wrong interpreter (parse failure) or a 16-laser
VLP-16 profile. Set PCAP / LIDAR_MODEL below to use a different capture.
"""
import os

from paraview.simple import (ColorBy, CreateRenderView, GetActiveView, Render,
                             ResetCamera, Show, VelodyneLiDARReader)

try:  # --script executes this file as a string, where __file__ is undefined
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    ROOT = os.environ.get("LV_ROOT", os.getcwd())
PCAP = os.path.join(ROOT, "data", "HDL32-V2_Tunnel.pcap")
LIDAR_MODEL = "HDL-32"

reader = VelodyneLiDARReader(registrationName=os.path.basename(PCAP),
                             FileName=PCAP, LidarModel=LIDAR_MODEL)
reader.UpdatePipelineInformation()

# reuse LidarView's own LiDAR view; creating one would split the layout
view = GetActiveView() or CreateRenderView()
display = Show(reader, view)
display.SetRepresentationType("Points")
ColorBy(display, ("POINTS", "intensity"))
display.RescaleTransferFunctionToDataRange(True, False)
ResetCamera()
Render()

frames = list(reader.TimestepValues)
print("opened %s" % PCAP)
print("sensor model : %s" % LIDAR_MODEL)
print("frames       : %d" % len(frames))
print("Status bar may still read 'Velodyne-VLP-16' -- that label is stale;")
print("the data is interpreted as %s (laser_id 0..31)." % LIDAR_MODEL)
print("Now: press Play in the LiDAR Player, then Filters -> Alphabetical -> SLAM (online).")
