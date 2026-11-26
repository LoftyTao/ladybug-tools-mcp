# Corresponding Source Notice & Inventory (`lbt-mcp` 1.3.0)

Under the terms of the **GNU Affero General Public License v3.0 (`AGPL-3.0-only`)**, **GNU General Public
License (`GPL-3.0-or-later`, `GPL-2.0-or-later`)**, and **GNU Lesser General Public License (`LGPL-3.0`,
`LGPL-2.1-only`)**, the machine-readable Corresponding Source for `lbt-mcp` and its
copyleft binary dependencies is provided via:

1. **Offline Release Archive**: `lbt-mcp-1.3.0-corresponding-source.tar.zst` (distributed alongside
   the Windows offline installer), containing:
   - The full `lbt-mcp` source tree (matching `MANIFEST.in`: `LICENSE`, `pyproject.toml`,
     `MANIFEST.in`, `src/`, `rune_viewer/`, `vendor/rune/`, `src/ironbug_bridge/`,
     `src/pyhygrothermfem_native/`, `vendor/pyHygroThermFEM-Fairyfly/`,
     `scripts/distribution/launcher/`, and `licenses/`).
   - Upstream source tarballs for bundled copyleft binary dependencies (`gmsh` `4.15.2`,
     `GEOS` `3.14.1`, `Ironbug` `1.26.1` — `ironbug-win-1.26.1.zip`
     `net48` `Ironbug.Console.exe` + `netstandard2.0` `Ironbug.*.dll`, paired with `BSD-3-Clause`
     `NREL.OpenStudio.win` `3.11.0` C# DLLs hardlinked from
     `runtimes/openstudio/3.11.0/CSharp/openstudio/`).
   - Machine-readable source inventory [`licenses/SOURCE_MANIFEST.json`](SOURCE_MANIFEST.json).
2. **Upstream Source Repositories & Written Offer**:
   - `lbt-mcp`: https://github.com/LoftyTao/ladybug-tools-mcp
   - `gmsh` `4.15.2`: https://gmsh.info/src/gmsh-4.15.2-source.tgz
   - `GEOS` `3.14.1`: https://download.osgeo.org/geos/geos-3.14.1.tar.bz2
   - `Ironbug` `1.26.1`: https://github.com/MingboPeng/Ironbug/archive/refs/tags/v1.26.1.tar.gz
   - Optional DES / OpenDSS (`dss_python_backend` / `KLUSolveX`, if distributed):
     https://github.com/dss-extensions/dss_python_backend, https://github.com/dss-extensions/dss_capi, https://github.com/dss-extensions/klusolve

## Corresponding Source Matrix

| Component | Version | License | Bundled in Standard Installer | Source Packaging / Archive | SHA-256 |
|---|---|---|---|---|---|
| `ladybug-tools-mcp` | `1.3.0` | `AGPL-3.0-only` | Yes | `repo_sdist` | `*(resolved at offline build / see `SOURCE_MANIFEST.json`)*` |
| `lbt-rune-viewer` | `0.1.0` | `GPL-3.0-or-later AND MIT AND OFL-1.1` | Yes | `in_repo_workspace` | `*(resolved at offline build / see `SOURCE_MANIFEST.json`)*` |
| `gmsh` | `4.15.2` | `GPL-2.0-or-later` | Yes | `gmsh-4.15.2-source.tgz` | `be3f66f225d27ba9fa014f07e83169285da8a051b0e8ab7103d88066b39bdd3e` |
| `geos` | `3.14.1` | `LGPL-2.1-only` | Yes | `geos-3.14.1.tar.bz2` | `3c20919cda9a505db07b5216baa980bacdaa0702da715b43f176fb07eff7e716` |
| `ironbug` | `1.26.1` | `LGPL-3.0-or-later` | Yes | `Ironbug-1.26.1.tar.gz` | `9ea1daa3b85499e9068f6faf652f2f2e7fac974406109a024aafad901299d428` |
| `dss_python_backend` | `optional-des-opendss` | `LGPL-3.0-only AND LGPL-2.1-or-later AND BSD-3-Clause` | Optional (only if distributed) | `upstream_repositories` | `*(resolved at offline build / see `SOURCE_MANIFEST.json`)*` |

> Note: Permissively licensed or non-copyleft runtime components (such as `OpenStudio(R)` `3.11.0`
> `BSD-3-Clause`, unmodified `EnergyPlus version 25.2.0`, `Radiance` `5.4`,
> `Evalglare` 2.0, `Python` `3.12.16` `PSF-2.0`, and optional `URBANopt` `1.4.0-rc1`
> `BSD-2-Clause`/`BSD-3-Clause`) keep their verbatim licenses and notices in
> [`licenses/THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and [`licenses/components/`](components/).
