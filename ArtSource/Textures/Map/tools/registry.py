"""Texture registry: each generator registers its name, size and Unity hints."""

TEXTURES = []

URP_LIT = "Universal Render Pipeline/Lit"
URP_DECAL = "Shader Graphs/Decal (URP Decal Projector)"


def texture(name, category, size, world_m, tiling="both", kind="tile", normal_strength=4.0,
            unity=None, notes="", atlas=None, ao_radius=6.0, ao_amount=4.0, emission=False):
    """Register a generator fn(name, (h, w), rng, ctx) -> Surface.

    size: (width, height) in px. world_m: (width, height) in metres covered by one tile
    (None for atlases). tiling: "both", "u", "v" or "none".
    """
    def deco(fn):
        TEXTURES.append({
            "name": name, "category": category, "size": list(size),
            "world_m": list(world_m) if world_m else None, "tiling": tiling, "kind": kind,
            "normal_strength": normal_strength, "unity_extra": unity or {}, "notes": notes,
            "atlas": atlas, "ao": (ao_radius, ao_amount), "emission": emission, "fn": fn,
        })
        return fn
    return deco


def map_files(t):
    """File names written for an entry (also used by --manifest-only)."""
    n = t["name"]
    files = {"albedo": f"{n}_albedo.png", "normal": f"{n}_normal.png",
             "roughness": f"{n}_roughness.png", "mask_urp": f"{n}_mask.png"}
    if t["emission"]:
        files["emission"] = f"{n}_emission.png"
    return files


def unity_settings(t, files):
    """Suggested Unity 6 / URP import + material settings for one entry."""
    decal = t["kind"] in ("decal", "decal_atlas")
    wrap = {"both": "Repeat", "u": "Repeat U / Clamp V", "v": "Clamp U / Repeat V",
            "none": "Clamp"}[t["tiling"]]
    s = {
        "shader": URP_DECAL if decal else URP_LIT,
        "workflow": "Metallic",
        "surface": "Transparent (alpha from albedo)" if decal else "Opaque",
        "import": {
            files.get("albedo", ""): "Default, sRGB on" + (", Alpha Is Transparency" if decal else ""),
            files.get("normal", ""): "Normal map (OpenGL +Y, no flip)",
            files.get("roughness", ""): "Default, sRGB off (reference only; URP uses the mask)",
            files.get("mask_urp", ""): "Default, sRGB off -> Metallic Map, Smoothness Source = Metallic Alpha",
        },
        "wrap_mode": wrap,
        "filter": "Trilinear, Aniso 4" if t["category"] in ("ground", "roofs") else "Trilinear, Aniso 2",
        "max_size": max(t["size"]),
        "metallic_value": 1.0,
        "smoothness_scale": 1.0,
        "normal_scale": 1.0,
    }
    if "emission" in files:
        s["import"][files["emission"]] = "Default, sRGB on -> Emission Map (HDR colour ~1.5-3 at night)"
    if t["world_m"]:
        s["tiling_per_metre"] = [round(1.0 / t["world_m"][0], 4), round(1.0 / t["world_m"][1], 4)]
    s.update(t["unity_extra"])
    return {k: v for k, v in s.items() if v != ""}
