# G22 sky — provenance v01

Prepared 14 October 2026. Runtime package: original code and shader authored for Only Volunteers. No paid assets, accounts, cloud generation, textures, third-party shaders or third-party packages are required. No COZY source or asset files were obtained.

## Allowed free bases inspected, not incorporated

| Repository | Pinned inspected commit | Licence file verified | Decision |
| --- | --- | --- | --- |
| [ZenoxZX/Celestia](https://github.com/ZenoxZX/celestia) | `1251f7c872fa5957a3366b3a4ef059b3d0ec723b` | `LICENSE.md`, MIT, copyright 2026 Aygün Özgür | Read README and licence; original small clock is sufficient here. No code copied. |
| [jiaozi158/UnityVolumetricCloudsURP](https://github.com/jiaozi158/UnityVolumetricCloudsURP) | `26c59bd371cc2af7b70741f6aea01adfdc8cc7bc` | `LICENSE`, MIT, copyright 2024 jiaozi158 | Read README and licence; avoid adding a renderer feature or package to the shared map. No code copied. |
| [Daniel Shervheim/unity-stylized-sky](https://github.com/danielshervheim/unity-stylized-sky) | `f5612b9d14cbd68a2563465afdd8dcf338dea9d9` | `LICENSE`, BSD-3-Clause, copyright 2018 Daniel Shervheim | Read README and licence; original URP shader authored. No code copied. |

Exact licence text snapshots and SHA-256 values are in `References/*_LICENSE.txt` and `References/licence_audit_v01.json`. These are research records outside Assets, not runtime dependencies. MIT requires preserving copyright/permission notices if code is later incorporated. BSD additionally requires the disclaimer/conditions in source and binary documentation and prohibits implied endorsement.

## Visual references (review use only)

- [COZY day image, Distant Lands](https://distantlands.space/images/cozy-case-study/cozy_4.jpg)
- [COZY night image, Distant Lands](https://distantlands.space/images/cozy-case-study/cozy_1.jpg)
- [COZY: Stylized Weather 3, Asset Store](https://assetstore.unity.com/packages/vfx/shaders/cozy-stylized-weather-3-271742)

The two published promotional JPEGs were downloaded unchanged to `References/` solely to study the user-supplied references and prepare the requested internal comparison. They are copyrighted promotional images, **not free game assets**. Keep them and any comparison containing them out of shipped Assets and distributable game packages. The COZY branding in the references belongs to Distant Lands; no endorsement is implied.

Observed direction: broad rounded clouds, restrained cloud-edge detail, pale cyan horizon and blue upper sky, warm light against cool shaded foliage, deep navy night, concentrated tiny stars and warm windows. The G22 shader does not sample either JPEG. It calculates its own noise, cloud density, lighting, sky gradient, stars and moon.

## Other inputs

- Existing v19 `DistrictBlend19` and public district/weather arrays are project-owned integration dependencies; they are referenced, never copied or edited.
- Unity 6000.5.11f1 built-in primitive meshes and URP 17.5.0 Lit shader are used by the review scene under the project's existing Unity installation. Pine crowns and terrain mesh are original procedural geometry.
- No new third-party runtime licensing obligations are introduced by G22 v01. Original project work follows the repository's ownership/licensing policy; this report does not relicense the game.
