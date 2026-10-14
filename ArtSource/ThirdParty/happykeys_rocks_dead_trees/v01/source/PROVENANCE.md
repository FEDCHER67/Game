# G19 - provenance

Retrieved: 2026-10-14T02:27:17+03:00 (Europe/Moscow, UTC+03:00). Requested task date: 2026-10-14.

Asset: **Low poly rocks and trees**, by **Trekkerac**, itch.io account **happykeys**.
Source: https://happykeys.itch.io/rocks-and-dead-trees

## Licence evidence

Exact asset-page wording (non-breaking spaces normalised):

> Free to use for everyone under CC0
> Uses the pallete from here which is also CC0 -> https://milkandbanana.itch.io/gradient-color-pallete

The linked palette page independently lists **Asset license: Creative Commons Zero v1.0 Universal**.
Palette author as listed there: **jamesdev** (milkandbanana).
Licence reference: https://creativecommons.org/publicdomain/zero/1.0/

Both downloaded HTML snapshots preserve the retrieved public pages. No archive licence/readme/text file is present. The two archive members are OutisideBlocks.glb and OutisideBlocks.blend. The Blender file has no Text datablocks and the GLB has no licence-bearing extras. An ASCII licence/copyright scan found only the Blender DNA schema field `*copyright`, not a copyright or licence statement. No conflicting licence was found. This is a record of the publisher's CC0 statements, not independent verification of authorship.

## Download

The authorised free/name-your-price flow was used without an account or payment: page CSRF token, POST /download_url, generated download page, POST /file/13974721, then the returned signed file URL. Session URLs, cookies and tokens are not reproduced in this report. Public page snapshots can contain the page's ephemeral CSRF field.

The ZIP is byte-for-byte the downloaded response and has not been recompressed or modified.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `itch_page_2026-10-14.html` | 23,227 | `855bbb083dbb1955320a2d519fc74d278ee67ff5b867ea3194c232e0a015dd4b` |
| `LowPolyTreesAndRocks.zip` | 1,354,382 | `a088b1462c6d5dfcc32b0c17bc11447fa8c540e9e38263ac533d5e48f2486d17` |
| `palette_page_2026-10-14.html` | 46,601 | `38684c21a367461a49f18800f9cbc9ba23dbb41baf465cc527f84dc814d4704b` |

## Safe extraction and conversion

Archive paths were checked for traversal, absolute paths and symlinks before extraction. Both members were extracted as data. No archive code was executed. The native .blend was inspected using Blender library data loading with automatic script execution disabled; its scene was not run. Conversion uses the self-contained GLB (the native .blend refers to a palette image absent from the ZIP). The embedded PNG is preserved separately for FBX material remapping.

All helpers live outside the project in the task's temporary working directory. Project writes are limited to ArtSource/ThirdParty/happykeys_rocks_dead_trees/. Unity was not opened or controlled.
