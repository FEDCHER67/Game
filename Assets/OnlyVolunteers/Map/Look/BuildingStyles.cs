namespace OnlyVolunteers.Map.Look
{
    // Proportions and parts of one building recipe (map look bible: constant human scale - door 2.1 m, floor ~3 m,
    // sill 0.9 m). Colours come from the look json palette; these are the shapes.
    public sealed class BuildingStyle
    {
        public string Name = "oldtown";
        public string Special = "";
        public string WallMat = "mat/wall/oldtown", RoofMat = "mat/roof/tile", TrimMat = "mat/trim";
        public float PlinthH = 0.5f;
        public string PlinthHex = "#6B6660";
        public float WinW = 1.2f, WinH = 1.6f, Sill = 0.9f, Pitch = 3.5f, EdgeMargin = 0.8f;
        public int InsetMaxFloors = 4;
        public float InsetDepth = 0.16f, FrameW = 0.08f;
        public bool FloorBands, Cornice, Balconies, StairStrips, Shopfront, RibbonWindows, HighBandWindows, ArchedWindows, Bars;
        public bool NeonStrips, GlassFront;
        public float RoofPitch = 30f, Eaves = 0.5f, ParapetH;
        public bool MachineRoom, Chimney, Hvac;
        public float DoorW = 1.0f, DoorH = 2.1f;
        public bool ArchedDoor, Porch, RollerDoor;
        public int Steps;
        public float CanopyW, CanopyD;
        public float GlassLit = 0.15f;
        public float SignH = 0.6f;
        public string SignMat = "mat/sign";
        public bool Modern;
        public int TriangleBudget = 2500;
    }

    public static class BuildingStyles
    {
        public static BuildingStyle For(LookBuilding b)
        {
            BuildingStyle s = Base(b.style ?? "", b.roof ?? "");
            s.WallMat = "mat/wall/" + (string.IsNullOrEmpty(b.style) ? "oldtown" : b.style);
            switch (b.kind)
            {
                case "slab":
                    s.Balconies = true;
                    s.StairStrips = true;
                    s.TriangleBudget = 12000;
                    break;
                case "tower":
                    s.WinW = 1.4f;
                    s.WinH = 1.4f;
                    s.Pitch = 3.0f;
                    s.Balconies = true;
                    s.CanopyW = 4f;
                    s.CanopyD = 2f;
                    s.TriangleBudget = 10000;
                    break;
            }
            if (b.kind == "functional") s.TriangleBudget = 6000;
            switch (b.type)
            {
                case "water_tower": s.Special = "water_tower"; break;
                case "industrial_chimney": s.Special = "chimney"; break;
                case "church":
                    s.Special = "church";
                    s.ArchedWindows = true;
                    s.WinW = 0.8f;
                    s.WinH = 2.4f;
                    s.Pitch = 3.4f;
                    s.ArchedDoor = true;
                    s.DoorW = 1.6f;
                    s.DoorH = 2.8f;
                    s.CanopyW = 0f;
                    s.RoofMat = "mat/roof/sheet";
                    break;
                case "gas_station":
                    s.Special = "gas_station";
                    s.Shopfront = true;
                    s.SignH = 1.0f;
                    break;
                case "casino":
                    s.Special = "casino";
                    s.GlassFront = true;
                    s.NeonStrips = true;
                    s.SignH = 2.0f;
                    break;
                case "nightclub":
                    s.Special = "nightclub";
                    s.NeonStrips = true;
                    s.SignH = 1.2f;
                    break;
                case "bowling_arcade":
                    s.Special = "bowling";
                    s.NeonStrips = true;
                    s.GlassFront = true;
                    s.SignH = 1.2f;
                    break;
                case "hospital":
                    s.Special = "hospital";
                    s.RibbonWindows = true;
                    s.WinW = 1.5f;
                    s.WinH = 1.5f;
                    s.Pitch = 2.0f;
                    s.CanopyW = 6f;
                    s.CanopyD = 4f;
                    s.SignH = 0.9f;
                    break;
                case "police_station":
                    s.Special = "police";
                    s.Bars = true;
                    s.WinW = 1.2f;
                    s.WinH = 1.5f;
                    s.Steps = 3;
                    break;
                case "bank":
                    s.Special = "bank";
                    s.Steps = 3;
                    s.Cornice = true;
                    break;
                case "supermarket":
                    s.Special = "supermarket";
                    s.Shopfront = true;
                    s.GlassFront = true;
                    s.SignH = 1.5f;
                    s.SignMat = "mat/red";
                    s.Hvac = true;
                    break;
                case "kiosk": s.Special = "kiosk"; break;
                case "bus_stop": s.Special = "bus_stop"; break;
                case "advertising_pole": s.Special = "ad_pole"; break;
                case "atm_pavilion": s.Special = "atm"; break;
                case "wagon_base": s.Special = "wagon"; break;
                case "mansion":
                case "prestige_base":
                    s.Modern = b.roof == "flat";
                    break;
                case "shop_24h":
                case "village_shop":
                case "pharmacy":
                case "bar":
                case "cafe":
                    s.Shopfront = true;
                    break;
                case "car_workshop":
                case "depot":
                case "tow_yard":
                case "garage_base":
                case "maintenance_shed":
                case "barn_yard":
                case "warehouse":
                    s.RollerDoor = true;
                    break;
            }
            if (b.roof == "none" && string.IsNullOrEmpty(s.Special)) s.Special = "ruin";
            return s;
        }

        private static BuildingStyle Base(string style, string roof)
        {
            var s = new BuildingStyle { Name = style };
            switch (style)
            {
                case "panel":
                    s.PlinthH = 0.6f;
                    s.WinW = 1.5f;
                    s.WinH = 1.5f;
                    s.Pitch = 3.6f;
                    s.InsetMaxFloors = 4;
                    s.ParapetH = 1.0f;
                    s.MachineRoom = true;
                    s.DoorW = 1.2f;
                    s.CanopyW = 2.4f;
                    s.CanopyD = 1.5f;
                    s.RoofMat = "mat/roof/flat";
                    s.PlinthHex = "#7A7670";
                    break;
                case "oldtown":
                    s.PlinthH = 0.5f;
                    s.WinW = 1.2f;
                    s.WinH = 1.8f;
                    s.Pitch = 2.8f;
                    s.EdgeMargin = 0.6f;
                    s.FloorBands = true;
                    s.Chimney = true;
                    s.ArchedDoor = true;
                    s.DoorH = 2.3f;
                    s.Steps = 2;
                    s.CanopyW = 1.6f;
                    s.CanopyD = 0.8f;
                    s.RoofPitch = 30f;
                    s.Eaves = 0.5f;
                    s.PlinthHex = "#6B5B4E";
                    break;
                case "rural_wood":
                    s.PlinthH = 0.6f;
                    s.WinW = 1.0f;
                    s.WinH = 1.3f;
                    s.Pitch = 3.2f;
                    s.FrameW = 0.15f;
                    s.RoofPitch = 38f;
                    s.Eaves = 0.45f;
                    s.Chimney = true;
                    s.Porch = true;
                    s.RoofMat = "mat/roof/sheet";
                    s.PlinthHex = "#8A8578";
                    s.GlassLit = 0.1f;
                    break;
                case "shed":
                    s.PlinthH = 0.3f;
                    s.WinW = 0.6f;
                    s.WinH = 0.6f;
                    s.Sill = 1.4f;
                    s.Pitch = 9f;
                    s.RoofPitch = 15f;
                    s.Eaves = 0.3f;
                    s.RoofMat = "mat/roof/sheet";
                    s.PlinthHex = "#6E6A60";
                    s.GlassLit = 0f;
                    break;
                case "civic":
                    s.PlinthH = 0.6f;
                    s.WinW = 1.2f;
                    s.WinH = 1.8f;
                    s.Pitch = 3.0f;
                    s.FloorBands = true;
                    s.Cornice = true;
                    s.DoorW = 1.6f;
                    s.DoorH = 2.4f;
                    s.CanopyW = 3.2f;
                    s.CanopyD = 1.6f;
                    s.RoofPitch = 28f;
                    s.ParapetH = roof == "flat" ? 0.8f : 0f;
                    s.PlinthHex = "#7A7068";
                    break;
                case "commercial":
                    s.PlinthH = 0.3f;
                    s.WinW = 1.6f;
                    s.WinH = 1.6f;
                    s.Pitch = 3.4f;
                    s.Shopfront = true;
                    s.DoorW = 1.6f;
                    s.CanopyW = 3f;
                    s.CanopyD = 1.2f;
                    s.ParapetH = roof == "flat" ? 0.6f : 0f;
                    s.Hvac = roof == "flat";
                    s.RoofMat = roof == "flat" ? "mat/roof/flat" : "mat/roof/sheet";
                    s.SignH = 0.8f;
                    break;
                case "neon":
                    s.PlinthH = 0.3f;
                    s.WinW = 1.6f;
                    s.WinH = 1.8f;
                    s.Pitch = 3.6f;
                    s.InsetMaxFloors = 0;
                    s.ParapetH = 0.8f;
                    s.DoorW = 2.4f;
                    s.DoorH = 2.6f;
                    s.CanopyW = 8f;
                    s.CanopyD = 3f;
                    s.RoofMat = "mat/roof/flat";
                    s.PlinthHex = "#2A2530";
                    s.GlassLit = 0.3f;
                    break;
                case "villa":
                    s.PlinthH = 0.4f;
                    s.WinW = 1.2f;
                    s.WinH = 2.1f;
                    s.Pitch = 2.6f;
                    s.Cornice = true;
                    s.DoorW = 1.5f;
                    s.DoorH = 2.4f;
                    s.CanopyW = 4f;
                    s.CanopyD = 2.5f;
                    s.RoofPitch = 28f;
                    s.Eaves = 0.4f;
                    s.ParapetH = roof == "flat" ? 0.5f : 0f;
                    s.RoofMat = roof == "flat" ? "mat/roof/flat" : "mat/roof/tile";
                    s.PlinthHex = "#9A948A";
                    s.Steps = 3;
                    break;
                case "industrial":
                    s.PlinthH = 0.5f;
                    s.WinW = 1.0f;
                    s.WinH = 0.6f;
                    s.Pitch = 2.4f;
                    s.HighBandWindows = true;
                    s.InsetMaxFloors = 0;
                    s.DoorW = 1.2f;
                    s.RoofPitch = 18f;
                    s.Eaves = 0.3f;
                    s.ParapetH = roof == "flat" ? 0.6f : 0f;
                    s.RoofMat = roof == "flat" ? "mat/roof/flat" : "mat/roof/corrugated";
                    s.PlinthHex = "#5E615F";
                    s.GlassLit = 0.05f;
                    break;
            }
            return s;
        }
    }
}
