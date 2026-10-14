# G18g aerial shaders v01

WaterAerial19V01 is a scoped derivative of the existing G14 UberStylizedWater shader, MIT, upstream https://github.com/MatrixRex/Uber-Stylized-Water/tree/1fdd16c6312611fef7fb248dee86cdd3fd456a1e. Existing SPDX/provenance headers retained; only its fog subgraph and shader name/target change.

Glass and smoke forwards derive from the project-pinned Unity URP package shaders. Original package license and source remain in Packages / Library/PackageCache. These project-specific copies change only final fog evaluation and retain original shader behavior. No downloaded code or assets.

Aerial19V01.hlsl is shared by opaque and transparent receivers. Scene-owned numeric globals and a persistent height texture are scoped to the active camera; there is no pipeline asset modification.
