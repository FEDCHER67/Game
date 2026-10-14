# G24 port of Unity Grass Instancer

Source: https://github.com/MangoButtermilch/Unity-Grass-Instancer/tree/f5983739d6159dbad115950e9ac349a1dd44e78e

Copyright (c) 2022 MangoButtermilch. MIT; see LICENSE.txt. The untouched complete archive and licence are in ArtSource/ThirdParty/MangoButtermilch_GrassInstancer/v01/.

Selected foundation: approach **3. Frustum Culling + Chunking**. The map is finite and its district masks need an editor bake, so the infinite generator is inappropriate. Approach 5 adds screen-depth occlusion without mipmapped conservative depth and records shadow artifacts in its own README; that path is not imported or enabled without proof against the map's URP depth pipeline.

Modified subset:
- `ChunkedGrassRenderer24.cs`: the source's chunk buffer, source buffer, visible append buffer, indirect count, render bounds and lifetime flow. Replaced the matrix payload with 32-byte baked blade records and 4-byte visible IDs; moved to `Graphics.RenderMeshIndirect`; fixed resource release; per-camera buffers; no synchronous gameplay readback.
- `GrassVisibility24.compute`: `ChunkRender` retained as the kernel; one group per chunk, conservative plane/AABB test instead of corner containment; exact end bounds instead of source's extra instance; added dispatch bounds, per-blade frustum/distance tests.
- `TallGrass24.shader`: original Unity 6 URP implementation using UnityIndirect.cginc, with broad 3-triangle geometry, palette gradient, world-space travelling gusts, colour patches, receiving shadows, built-in fog, and matching depth/depth-normal deformation. Material properties deliberately outside UnityPerMaterial opt out only this grass shader from SRP Batcher. No global SRP Batcher change.

No upstream model, noise library, screenshot, texture or showcase asset is imported. The mesh is original project geometry. Our placement, district policy, evidence tooling and immutable baked dataset live in Map/Grass separately from this port.
