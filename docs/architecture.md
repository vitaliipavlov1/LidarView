# LidarView Architecture

A conceptual walkthrough: what LidarView is made of, where data lives, how maps are saved and
loaded, how the SLAM engine is plugged in, and what governs real-time behaviour. Everything below
was verified on LidarView 5.3.0 (plugin manifests, binaries, runtime introspection), not taken
from marketing material.

## Core idea

**LidarView is ParaView with LiDAR plugins.** It is not a standalone application but a ParaView 6.1
build plus a set of shared-object plugins:

```
ParaView 6.1              engine: pipeline, 3D view, Python, file formats
  + LidarCorePlugin       shared readers, filters, writers
  + VelodynePlugin        \
    HesaiPlugin            |
    OusterPlugin           |  sensor packets → points
    RobosensePlugin        |  (one interpreter per vendor)
    LivoxPlugin            |
    LeishenPlugin         /
  + DatasetIOPlugin       read/write standard point-cloud formats
  + LidarSlamPlugin.so    Kitware SLAM, 6.9 MB
  + GUI layer             LiDAR Player, measurement grid, toolbars
```

The plugins are wired in through manifests:

```
bin/LidarView.conf
  ../lib/paraview-6.1/plugins/paraview.plugins.xml
  ../lib/lidarview/plugins/lidarview.plugins.xml
  ../lib/slam/plugins/slam.plugins.xml
```

Almost everything else follows from this: any ParaView filter, file format, script or technique
also works in LidarView, and it is extended the same way, with a plugin.

## Where data lives

The release contains exactly four directories:

```
bin/      LidarView, lvpython, lvbatch, lvserver, PacketFileSender
lib/      libraries + the lidarview/ and slam/ plugin trees
plugins/  Qt plugins (platform, image formats)
share/    sensor calibrations and licences
```

LidarView ships **no `data` or `samples` directory** and keeps no data of its own; files are opened
from anywhere. `share/` holds only calibration files (`HDL_32.xml`, `VLP_16.xml`, `Pandar*.csv`,
`Alpha_Prime.xml`, …).

The `data/` directory in this repository is a separate download area for sample captures and is
unrelated to the LidarView install.

## Raw capture vs. finished cloud

These are two different kinds of data, and they are routinely confused.

| | Raw sensor capture | Finished cloud / map |
|---|---|---|
| Contents | UDP packets exactly as they crossed the network | XYZ points in metres |
| Format | `.pcap` | `.vtp`, `.pcd`, `.las`, `.ply`, `.xyz` |
| Calibration needed | **yes**: a packet carries no geometry | no |
| Opened with | `Velodyne / Hesai / Ouster … LiDAR Reader` | standard ParaView readers |
| Time dimension | frames, playable | usually one static set |

### Saving a map after SLAM

Select the output (`Edge map`, `Planar map`, `Trajectory`) → `File → Save Data` → choose a format.
The build provides:

| Writer | Format | Use |
|---|---|---|
| `XMLPolyDataWriter` | `.vtp` | native VTK, lossless |
| `PCDWriter` | `.pcd` | exchange with PCL |
| `PLASWriter` | `.las` | surveying, GIS |
| `PPLYWriter` | `.ply` | mesh editors |
| `TemporalTransformsWriter` | — | trajectory with orientations |
| `MCAPPointSetWriter` | `.mcap` | ROS 2 |
| `LidarKITTIDataSetWriter` | KITTI | benchmarks |

### Loading a finished cloud back

`File → Open` treats it as a plain point cloud. No SLAM and no calibration are involved and nothing
is recomputed. Readers: `PLYReader`, `XYZReader`, ParaView's `.vtp` readers,
`LidarKITTIDataSetReader`, `ROS2PointCloudMCAPReader`.

### Saving the whole session

`File → Save State` (`.pvsm`) stores the pipeline, camera, colour maps and filter parameters. It
holds **references to files, not data**, so a state file is only useful together with its sources.

## Replacing the SLAM engine without rebuilding

SLAM is attached as an ordinary plugin through a plain-text manifest:

```xml
<!-- lib/slam/plugins/slam.plugins.xml -->
<Plugins>
  <Plugin name="LidarSlamPlugin" auto_load="1" delayed_load="0" version="3.1"
          description="Kitware SLAM lib available as a Paraview Plugin"/>
</Plugins>
```

The binaries contain `pqManagePluginsReaction`, `pqPluginDialog` and support for the
`PV_PLUGIN_PATH` and `PV_PLUGIN_CONFIG_FILE` environment variables, which means a **third-party
plugin can be loaded into the release** without rebuilding it.

| Level | What to do | Compilation | GUI |
|---|---|---|---|
| Programmable Filter | Python, directly in the GUI | none | unchanged |
| Custom ParaView plugin | `.so` + XML on `PV_PLUGIN_PATH` or via `Tools → Manage Plugins` | plugin only | unchanged |
| Rebuild LidarView | superbuild of LVCore + ParaView | everything | unchanged, but modifiable |

**The GUI does not change in any of these cases.** A custom filter appears under `Filters` next to
`SLAM (online)`, because menus are generated from plugin XML descriptions.

Rebuilding from source is only required to change **LidarView itself** (toolbars, player, readers).
Changing the **algorithm** does not require it.

## Real-time behaviour

The pipeline is **pull-based**: the view requests a frame → the filter computes → the reader
decodes. For a live sensor the file reader is replaced by a stream (`VelodyneLiDARStream`,
`HesaiLiDARStream`, `OusterLiDARStream`, `RobosenseLiDARStream`, `LivoxLiDARStream`,
`LeishenLiDARStream`) that listens on a UDP port and emits frames as they arrive.

The constraint is that **SLAM and rendering share the CPU**. On the reference 4-thread machine the
SLAM engine ran at 0.10–0.14 s/frame (the cost grows with the map) against a ≈0.085 s budget at the
captures' ≈11.7 Hz: already slower than real time before any rendering cost.

When it cannot keep up, tune in descending order of effect:

1. **Thin the input**: `Firings Skip` in the reader, `Ratio of points` in SLAM.
2. **Fewer keypoints**: `Maximum keypoints number`.
3. **Coarser map**: increase `Edges/Planes map resolution` (larger voxels).
4. **`Keypoint maps output mode → Sub-maps`**: avoid pushing the entire map to the renderer. On large
   maps this is the biggest single win.
5. **Threads**: `Number of threads`; giving all four threads of a 4-thread CPU to SLAM starves the
   renderer.
6. **Hide unneeded outputs**: see the "purple screen" row in the symptom table in
   [settings.md](settings.md).

The governing principle: **SLAM must keep up with the sensor; rendering need not.** The view can
drop to 5–10 FPS with no consequence, whereas a skipped SLAM frame breaks tracking. Optimise
rendering first, never the algorithm.
