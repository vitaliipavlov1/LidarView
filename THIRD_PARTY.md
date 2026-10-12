# Third-Party Software and Data

The MIT licence in [LICENSE](LICENSE) covers the scripts and documentation in this repository only.
The components below are downloaded at setup time by `scripts/fetch.sh`, are **not** redistributed
here (`runtime/` and `data/` are git-ignored), and remain under their owners' licences.

| Component | Owner | Obtained from | Licence |
|---|---|---|---|
| LidarView 5.3.0 | Kitware, Inc. | [Kitware GitLab](https://gitlab.kitware.com/LidarView/lidarview) package registry | Apache-2.0 |
| ParaView 6.1 (LidarView core) | Kitware, Inc. | bundled in the LidarView release | BSD-3-Clause |
| Kitware SLAM (`LidarSlamPlugin`) | Kitware, Inc. | bundled in the LidarView release | Apache-2.0 |
| Sample PCAPs (Velodyne HDL-32E) | Kitware collection | [data.kitware.com](https://data.kitware.com) | per collection terms |

Integrity: the release archive is pinned by SHA-256 and each sample capture by SHA-512 in
[scripts/fetch.sh](scripts/fetch.sh); downloads that do not match are rejected.

Licence identifiers above were checked against the licence files shipped in the release under
`share/licenses/` (`lidarview/`, `slam/`, `ParaView/`). The release also bundles further
third-party libraries (Eigen, PDAL, Python, …), each with its own licence in that directory.
Consult it before redistributing anything.
