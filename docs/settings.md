# LidarView Settings for HDL-32E Captures

A reference for the two bundled datasets (`HDL32-V2_*.pcap`: Velodyne HDL-32E, ≈11.8 Hz, roof-mounted
on a car). Defaults and descriptions come from LidarView 5.3.0's own XML definitions; figures are
measurements taken on these files. For how LidarView itself is put together, see
[architecture.md](architecture.md).

## The minimum you need

The GUI exposes hundreds of parameters; in practice seven matter. First, a mental model of where
to look.

### Three panels = three pipeline stages

| Panel | Controls | Takes effect |
|---|---|---|
| **Pipeline Browser** | what exists and what is visible | immediately |
| **Properties** | how data is **computed** (reader / filter parameters) | on **Apply**; recomputes data |
| **Display** | how data is **drawn** (colour, point size) | immediately; data untouched |

The most common confusion: changing colour is a Display setting and triggers no recomputation;
changing the sensor model is a Properties setting and needs Apply.

### The seven parameters that matter

**Open the data (reader Properties)**
1. **Sensor model**: the only mandatory one. Geometry is wrong without it.

**See it (Display + Color Map Editor)**
2. **Coloring**: which field to colour by: `intensity`, `Z`, `distance_m`, `laser_id`.
3. **Scale range**: almost always set manually (see below).
4. **Point Size**: 1–3.

**Play it (LiDAR Player)**
5. **Speed = `All Frames`**: process every frame. Other modes drop frames.

**Build a map (SLAM Properties)**
6. **`Mapping mode = Update`** + **`Keypoint maps output mode = Full maps`**: otherwise no map.
7. **Map resolution** (`Edges/Planes map resolution`): voxel size in metres.

Everything else keeps the engine defaults for ground-vehicle capture. Leave it until there is a
specific problem.

### Why the colour scale drifts

The Color Map Editor defaults to:

```
Automatic Rescale Range = "Grow and update on 'Apply'"
```

"**Grow**" means the range can only **expand**, never shrink. It therefore creeps upward as the map
accumulates (200 → 240 → 250), and a manually entered 0…45 gets overwritten. Order of operations:
set **`Automatic Rescale Range → Never`** first, then the range.

### Three rules for any LiDAR data

1. **Calibrate first.** A wrong sensor model produces a plausible but incorrect picture. Check that
   `laser_id` reaches N−1 beams and `vertical_angle` matches the sensor spec.
2. **Set the colour scale manually.** LiDAR data has a long tail: median intensity 11 against a
   maximum of 250. An automatic scale shows the tail and hides everything else.
3. **SLAM is streaming.** It sees only the frames actually requested, in order. Seeking is not
   processing.

### Debugging by symptom

| Symptom | Where to look |
|---|---|
| Map is a single blob | frames were not played sequentially from the start |
| Map "drifts" | colour by `Z` and view from the side: vertical drift |
| Everything one colour | scale range and `Automatic Rescale Range` |
| Purple screen | too many visible outputs; GPU texture limit reached |
| Nothing visible after Apply | the eye icon is off, or Zoom to Data is needed |

## Measured dataset properties

| | `HDL32-V2_R into Butterfield…` |
|---|---|
| Frames / duration | 530 / 45 s (≈11.8 Hz) |
| Points per frame | ~51,000 |
| Range | 1.37 … 105 m, median **8.5 m** |
| Ground plane | Z = −2.38 m, so the sensor sits ~2.4 m above the road |
| Return mode | **single return** (every `Dual Return Filter` setting yields exactly 51,477 points) |
| Intensity | p50=11, p90=33, **p95=45**, p99=75, max=213 |
| Speed (from SLAM) | 98 m in 10 s = 9.8 m/s (**35 km/h**) |

## Recommended settings

### Reader (`Velodyne LiDAR Reader`)

| Parameter | Value | Why |
|---|---|---|
| **Lidar Model** | **HDL-32** | The only mandatory change. The default is VLP-16, giving 16 beams instead of 32 and corrupted geometry. |
| Calibration File | empty | Selecting a model loads the bundled `share/HDL_32.xml`. Setting a file by hand makes no difference to the model. |
| Use Auto Calibration | leave alone | Despite the name this means "accept calibration over the network" and applies **only to HDL-64**. It has nothing to do with a file on disk. |
| Dual Return Filter | `Dual` | The capture is single-return; the parameter has no effect (verified). |
| Lidar Port | 2368 | Matches the data. `-1` reads all ports. |
| Ignore Zero Distances | on | Drops "no return" points (sky, absorbing surfaces). |
| Show Partial Frames | off | The first and last frames are incomplete revolutions. |
| Framing Method | `Interpreter provided` | One frame = one revolution, split where azimuth crosses 0°. Correct for a spinning Velodyne. |
| Display Packet Time | `Network Time` | The capture contains GPS packets (8,948 on port 8308), so network time can be synchronised. |
| Enable Advanced Arrays | optional | Adds `X`, `Y`, `Z`, `distance_raw`. |

### Display

| Parameter | Value | Why |
|---|---|---|
| Coloring | `intensity`, range **0…45** | Auto-scale stretches to 213 because of ~0.1% retroreflectors, while the median is 11, flattening 95% of the cloud into dark blue. 0…45 = p95. |
| Representation | `Points`, Point Size 2 | |
| Alternative colourings | `laser_id`: beam rings; `Z`: height; `distance_m`: range | |

### SLAM (online)

The SLAM defaults are tuned for exactly this scenario (car, outdoor), so very little needs
changing.

| Parameter | Default | Comment |
|---|---|---|
| **Ego-Motion mode** | `Motion extrapolation` | Keep. Suits a smoothly moving car. |
| **Undistortion mode** | `Refined` | Keep. During one revolution (0.1 s) the car travels ~1 m; without compensation the frame is smeared. |
| Mapping mode | `Update` | Builds and updates the map. `Add keypoints` only adds; `Disabled` is pure odometry. |
| Keypoint maps output mode | `Full maps` | Required for the map to be visible. `Sub-maps` shows only a local piece. |
| Number of threads | `4` | Already equals the CPU thread count. |
| Use edges / intensity edges / planes | 1 / 1 / 1 | Keep. |
| Use blobs | 0 | Blobs are for unstructured scenes (vegetation). Not needed in a city. |
| Verbosity level | 0 | Raise to `1` or `2` for the first run to see per-frame timing. |
| Failure detection | 0 | Worth enabling: catches SLAM divergence. |
| Use loop closure constraint | 0 | The capture never returns to the same place, so there is nothing to close. |
| 2d mode / Planar trajectory | 0 | Would lock Z; not appropriate for a road with slope. |

Map resolutions (advanced tab) are voxel edge lengths and are already set for outdoor use:
`Edges map resolution` 0.3 m, `Intensity edges` 0.2 m, `Planes map` 0.6 m, `Blobs map` 0.5 m,
`Rolling grid resolution` 10 m, `Voxel grid resolution` 1 m. Go finer for interiors and tunnels,
coarser for highways.

**Result with defaults, 120 frames:** 98.0 m in 10.0 s, 0.48–1.17 m per frame step (no jumps),
1.33 m Z drift, 0.12 s/frame against a ≈0.085 s real-time budget (≈11.8 Hz).

## What the main setting groups mean

**Calibration (`Lidar Model`).** A Velodyne packet carries only range, azimuth and laser number.
The elevation angle of each of the 32 beams and their corrections live in the calibration file.
Without the right model, ranges are laid out at wrong angles: the cloud looks plausible but is
geometrically wrong. Verify with `laser_id` (0…31) and `vertical_angle` (−30.67°…+10.67° for the
HDL-32E).

**Framing.** A frame is a convention, not a property of the data. `Interpreter provided` cuts the
stream where azimuth wraps through 0°, so one frame = one revolution. `Time` cuts on network time in
multiples of `Frame Duration`, which is needed when several sensors must be aligned to a common
clock.

**Ego-Motion.** The initial guess of inter-frame motion, before the main registration.
`Motion extrapolation` continues the previous motion, `Registration on previous frame` registers
against the previous frame (more accurate, more expensive), `External` takes it from IMU/odometry.

**Undistortion.** The lidar sweeps for 0.1 s and the platform moves meanwhile, so points at the
start and end of a revolution are captured from different positions. `Refined` re-projects every
point to a common instant using the estimated trajectory. For a moving car the effect is visible.

**Keypoints (edges / planes / intensity edges / blobs).** SLAM does not align whole clouds; it
extracts distinctive points: `edges` (poles, building corners), `planes` (walls, road),
`intensity edges` (boundaries by reflectivity: lane markings, signs) and `blobs` (everything else).
Registration runs on these, so the keypoint set determines both accuracy and speed.

**Map resolution.** The map is stored as a voxel grid; resolution is the voxel edge in metres.
Finer is more accurate and heavier on memory. `Rolling grid` is the size of the sliding map window
around the current position.

**Loop closure.** Recognising a previously visited place and removing accumulated drift (Ceres and
g2o ship with the release for this). In LidarView 5.3.0 the detector defaults to `External`, so
closure points are supplied manually or from outside rather than found automatically.

## SLAM outputs

| Port | Name | What it is |
|---|---|---|
| 0 | `Current transformed frame` | The current frame in world coordinates |
| 1 | `Trajectory` | One pose per frame: `Time`, `Orientation(Quaternion)`, `Orientation(AxisAngle)`, `Covariance` |
| 2 | `Edge map` | Accumulated edge map |
| 3 | `Intensity edge map` | Reflectivity-boundary map (sparse here: bright points are 0.1%) |
| 4 | `Planar map` | Accumulated plane map |
| 5–7 | `Current … keypoints` | Keypoints of the current frame; empty until **Output current keypoints** is ticked |
