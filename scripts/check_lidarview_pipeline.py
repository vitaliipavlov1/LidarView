#!/usr/bin/env python3
"""Headless pipeline check: LidarView's Velodyne reader + Kitware SLAM on a PCAP.

Drives VelodyneLiDARReader and the SLAMonline filter (LidarSlamPlugin) with default
settings, then reports frame counts, point attributes, trajectory and map sizes and a
PASS/FAIL verdict. This is the headless equivalent of the manual GUI workflow.

Must be run with LidarView's interpreter:
    runtime/LidarView-5.3.0/bin/lvpython scripts/check_lidarview_pipeline.py <file.pcap> [slam_frames]
"""
import math
import sys
import time

from paraview.simple import VelodyneLiDARReader, SLAMonline
import paraview.servermanager as sman

# SLAMonline output ports, as exposed by LidarSlamPlugin 3.1
PORTS = {0: "Current transformed frame", 1: "Trajectory", 2: "Edge map",
         3: "Intensity edge map", 4: "Planar map", 5: "Current edge keypoints",
         6: "Current intensity edge keypoints", 7: "Current planar keypoints"}


def main(pcap, slam_frames=40, model="HDL-32"):
    print("== reader ==")
    t0 = time.time()
    reader = VelodyneLiDARReader(registrationName="check", FileName=pcap, LidarModel=model)
    reader.UpdatePipelineInformation()
    frames = list(reader.TimestepValues)
    if not frames:
        print("FAIL: reader produced no frames")
        return 1
    print("file            : %s" % pcap)
    print("sensor model    : %s" % model)
    print("frames indexed  : %d  (%.1f s)" % (len(frames), time.time() - t0))
    print("time range      : %.3f .. %.3f  (%.1f s of data)" % (
        frames[0], frames[-1], frames[-1] - frames[0]))

    for idx in (0, len(frames) // 2, len(frames) - 1):
        reader.UpdatePipeline(frames[idx])
        print("  frame %5d  points=%7d" % (idx, reader.GetDataInformation().GetNumberOfPoints()))

    reader.UpdatePipeline(frames[len(frames) // 2])
    pdi = reader.GetPointDataInformation()
    print("point attributes: %d" % pdi.GetNumberOfArrays())
    for i in range(pdi.GetNumberOfArrays()):
        a = pdi.GetArray(i)
        lo, hi = a.GetRange(0)
        print("  %-18s range = %.5g .. %.5g" % (a.GetName(), lo, hi))
    print("bounds (m)      : X %.1f..%.1f  Y %.1f..%.1f  Z %.1f..%.1f"
          % reader.GetDataInformation().GetBounds())

    print()
    print("== built-in SLAM (LidarSlamPlugin, default settings) ==")
    slam = SLAMonline(registrationName="slam", PointCloud=reader)
    n = min(slam_frames, len(frames))
    t0 = time.time()
    for i in range(n):
        slam.UpdatePipeline(frames[i])
    dt = time.time() - t0
    print("processed       : %d frames in %.1f s (%.2f s/frame)" % (n, dt, dt / n))
    for i in range(slam.GetNumberOfOutputPorts()):
        di = slam.GetOutputPort(i).GetDataInformation()
        if di.GetNumberOfPoints():
            print("  port %d %-24s points=%8d" % (i, PORTS.get(i, ""), di.GetNumberOfPoints()))

    traj = sman.Fetch(slam, idx=1)
    npose = traj.GetNumberOfPoints()
    pd = traj.GetPointData()
    print("trajectory poses: %d (expected %d)" % (npose, n))
    print("trajectory arrays: %s" % [pd.GetArrayName(i) for i in range(pd.GetNumberOfArrays())])
    if npose >= 2:
        first, last = traj.GetPoint(0), traj.GetPoint(npose - 1)
        length = sum(math.dist(traj.GetPoint(k), traj.GetPoint(k + 1)) for k in range(npose - 1))
        print("first pose      : %8.3f %8.3f %8.3f" % first)
        print("last  pose      : %8.3f %8.3f %8.3f" % last)
        print("net displacement: %.2f m   path length: %.2f m" % (math.dist(first, last), length))

    map_pts = slam.GetOutputPort(2).GetDataInformation().GetNumberOfPoints()
    ok = npose == n and map_pts > 0
    print()
    print("RESULT: %s" % ("PASS - LidarView read the dataset and its built-in SLAM "
                          "produced a trajectory and a map" if ok else
                          "FAIL - SLAM did not produce the expected trajectory/map"))
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 40))
