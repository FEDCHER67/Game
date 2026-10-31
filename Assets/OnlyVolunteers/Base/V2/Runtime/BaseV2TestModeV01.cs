using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using OnlyVolunteers.Capture;
using OnlyVolunteers.Capture.V2;
using OnlyVolunteers.Economy;
using OnlyVolunteers.Map;
using OnlyVolunteers.Vehicles;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.LowLevel;
using UnityEngine.Rendering.Universal;

namespace OnlyVolunteers.BaseV2
{
    /// <summary>
    /// V2 base P1 scripted checks inside a player build (Fedya 31.10; the pattern of Vadim's HangarTestMode). Idle unless the
    /// player starts with <c>-baseTest &lt;shop|persist|dock|all&gt;</c> (MenuTestSkipV01 skips the start menu then); start
    /// it with -batchmode: no window, every shot is rendered into a RenderTexture. Keyboard and mouse are ignored. The world
    /// saves into a test slot (ov_v2_base_test.json; deleted first except in "persist"); writes PASS/FAIL lines, shots and
    /// done.txt to <c>-baseTestOut &lt;folder&gt;</c>; the caller stops the process (no Quit, no settings saved).
    /// shop: hover the baton display without money (red), buy refused, F8 test money, hover (amber), buy, a second buy
    ///   refused, owned (green), the save holds it; the baton drawn bonks a standing NPC (down, 4 s), cooldown, a miss.
    /// persist: a second run on the same test save: the team still owns the baton, the fund kept.
    /// dock: the van creeps through the dock zone too fast (no dock), then at 0.35 m/s (dock, driver out at a free spot,
    ///   lift up, bubble, menu), the engine tier bought through the mechanic (puff, one charge, top speed up), Готово lowers.
    /// </summary>
    [DefaultExecutionOrder(32000)]
    public sealed class BaseV2TestModeV01 : MonoBehaviour
    {
        public const string SaveSlot = "ov_v2_base_test.json";
        private readonly StringBuilder log = new StringBuilder();
        private string outDir;
        private int pass, fail;
        private CaptureDirector director;
        private Camera shotCam;
        private RenderTexture rt;
        private Rigidbody creepBody;
        private Vector3 creepVelocity;

        private static string Arg(string key)
        {
            string[] a = System.Environment.GetCommandLineArgs();
            int i = System.Array.IndexOf(a, key);
            return i >= 0 && i + 1 < a.Length ? a[i + 1] : null;
        }

        private void Awake()
        {
            string mode = Arg("-baseTest");
            if (mode == null) return;
            BlockInput();
            CaptureTestHooks.SaveSlot = SaveSlot;
            if (mode == "persist") return;
            string dir = Path.Combine(Application.persistentDataPath, "OnlyVolunteers");
            if (Directory.Exists(dir))
                foreach (string f in Directory.GetFiles(dir, SaveSlot + "*")) File.Delete(f);
        }

        private IEnumerator Start()
        {
            string mode = Arg("-baseTest");
            if (mode == null) { enabled = false; yield break; }
            Application.runInBackground = true;
            outDir = Arg("-baseTestOut") ?? Path.Combine(Application.persistentDataPath, "basetest");
            Directory.CreateDirectory(outDir);
            Line($"baseTest {mode}: scene {gameObject.scene.name}, batch {Application.isBatchMode}, save slot {SaveSlot}");
            float until = Time.realtimeSinceStartup + 60f;
            while (Time.realtimeSinceStartup < until)
            {
                director = CaptureDirector.Instance;
                if (director != null && director.Ready && director.Loaded && director.Pawn != null && director.Van != null &&
                    BaseV2DirectorV01.Instance != null && BaseV2DirectorV01.EconomyReady && CaptureV2Rig.Instance != null && CaptureV2Rig.Instance.Hands != null) break;
                yield return null;
            }
            if (director == null || BaseV2DirectorV01.Instance == null || !BaseV2DirectorV01.EconomyReady) { Check(false, "scene ready (director, economy, V2 base director)"); Done(); yield break; }
            yield return new WaitForSecondsRealtime(2f);
            Line($"ready: fund ${BaseV2DirectorV01.Balance}, workshop open {TeamEconomy.Instance.ServerState.WorkshopUnlocked}, engine tier {TeamEconomy.Instance.ServerState.VanTier(VanBranch.Engine)}, " +
                 $"van StartAtMax {(director.Van.TryGetComponent(out VanUpgrades up) ? up.StartAtMax.ToString() : "?")}, top speed {director.Van.MaxSpeedKmh:0} km/h");
            Check(TeamEconomy.Instance.ServerState.WorkshopUnlocked, "V2: the workshop is open from the start (no M06)");
            if (mode == "shop" || mode == "all") yield return Shop();
            if (mode == "persist") Persist();
            if (mode == "dock" || mode == "all") yield return Dock();
            Done();
        }

        // ================================================================== shop + baton

        private IEnumerator Shop()
        {
            ShopDisplayItemV2 display = ShopDisplayItemV2.Find(GearCatalogV2.Baton);
            GameObject spotGo = GameObject.Find(BaseV2Names.ShopCustomerSpot);
            if (display == null || spotGo == null) { Check(false, "shop: the baton display and the customer spot exist"); yield break; }
            GreyboxPawn pawn = director.Pawn;
            CaptureV2Hands hands = CaptureV2Rig.Instance.Hands;
            int price = GearCatalogV2.Find(GearCatalogV2.Baton).Price;
            int fund0 = BaseV2DirectorV01.Balance;
            Line($"shop: fund at start ${fund0}, baton price ${price}");
            yield return Aim(pawn, hands, spotGo.transform.position, display.AimPoint);
            Check(display.AimedBy(pawn), "shop: aiming from the customer spot hits the baton display");
            display.Offer(pawn, out string label);
            Line("shop: hint (no money) = " + label + " | effect = " + display.LastEffect);
            Check(label.StartsWith("Не хватает"), "shop: no money shows the honest 'not enough' line");
            yield return Shot(pawn.ViewCamera, "shop_01_hover_not_enough_firstperson");
            bool? ok = null; string text = "";
            display.ScriptBuy((o, t) => { ok = o; text = t; });
            yield return new WaitUntil(() => ok.HasValue);
            Check(ok == false && BaseV2DirectorV01.Balance == fund0 && !BaseV2DirectorV01.TeamOwns(GearCatalogV2.Baton), $"shop: buying without money refused, nothing charged ({text})");
            BaseV2DirectorV01.Instance.GiveTestCash();
            yield return new WaitForSecondsRealtime(1.2f);
            int fund1 = BaseV2DirectorV01.Balance;
            display.Offer(pawn, out label);
            Line($"shop: fund after F8 ${fund1}; hint = {label}");
            Check(label.StartsWith("E — купить"), "shop: with money the hint offers E");
            yield return Shot(pawn.ViewCamera, "shop_02_hover_can_buy_firstperson");
            yield return ShotFrom(BaseV2Names.ShopReviewCam, "shop_03_hover_can_buy_ground", () => display.ScriptHover(0));
            var topMarker = new GameObject("BaseV2 review cam GEAR top (test)");
            topMarker.transform.SetPositionAndRotation(display.AimPoint + Vector3.up * 9f, Quaternion.LookRotation(Vector3.down, Flat(display.AimPoint - spotGo.transform.position)));
            yield return ShotFrom(topMarker.name, "shop_05_counter_top_outline", null, null, true);
            Destroy(topMarker);
            ok = null;
            display.ScriptBuy((o, t) => { ok = o; text = t; });
            yield return new WaitUntil(() => ok.HasValue);
            Check(ok == true && BaseV2DirectorV01.Balance == fund1 - price && BaseV2DirectorV01.TeamOwns(GearCatalogV2.Baton), $"shop: bought, charged ${price} once ({text})");
            ok = null;
            display.ScriptBuy((o, t) => { ok = o; text = t; });
            yield return new WaitUntil(() => ok.HasValue);
            Check(ok == false && BaseV2DirectorV01.Balance == fund1 - price, $"shop: a second press charges nothing ({text})");
            yield return new WaitForSecondsRealtime(1.2f);
            display.Offer(pawn, out label);
            Line("shop: hint (owned) = " + label);
            Check(label.Contains("уже есть"), "shop: owned state shown");
            yield return Shot(pawn.ViewCamera, "shop_04_hover_owned_firstperson");
            // the team save holds it (the economy commit writes the save)
            string save = Path.Combine(Application.persistentDataPath, "OnlyVolunteers", SaveSlot);
            float until = Time.realtimeSinceStartup + 8f;
            bool saved = false;
            while (Time.realtimeSinceStartup < until && !saved)
            {
                saved = File.Exists(save) && File.ReadAllText(save).Contains(EconomyState.GearKey(GearCatalogV2.Baton));
                if (!saved) yield return new WaitForSecondsRealtime(0.25f);
            }
            Check(saved, "shop: the save file " + SaveSlot + " holds gear:baton_rubber");
            yield return BatonChecks(pawn, hands);
        }

        private IEnumerator BatonChecks(GreyboxPawn pawn, CaptureV2Hands hands)
        {
            CaptureV2BatonV01 baton = hands.GetComponent<CaptureV2BatonV01>();
            if (baton == null) { Check(false, "baton: component on the hands"); yield break; }
            baton.Toggle(true);
            yield return null;
            Check(baton.Drawn, "baton: X draws it once owned");
            // like Vadim's slap test: one NPC stood in the open hall and held there (free NPCs run from a walker within 7 m)
            GreyboxNpc target = null;
            foreach (GreyboxNpc n in GreyboxNpc.All)
                if (n != null && n.isActiveAndEnabled && n.State == NpcState.Free) { target = n; break; }
            CaptureV2Npc cn = target != null ? CaptureV2Rig.Instance.Ensure(target) : null;
            GameObject hall = GameObject.Find("Hangar_Base_v01");
            if (cn == null || hall == null) { Check(false, "baton: a standing NPC to test on"); yield break; }
            Vector3 at = hall.transform.TransformPoint(new Vector3(-14f, 0.05f, -2f));
            cn.TestPlaceStanding(at, 0f);
            cn.TestHold(true);
            yield return null;
            Vector3 front = Flat(cn.transform.forward);
            pawn.Teleport(at + front * 1.9f, Quaternion.LookRotation(-front).eulerAngles.y);
            yield return null;
            hands.Aim(at + Vector3.up * 1.45f);
            yield return null;
            hands.Aim(at + Vector3.up * 1.45f);
            yield return null;
            int swings0 = baton.Swings;
            Check(baton.ScriptStrike(), "baton: LMB taken by the baton");
            yield return new WaitForSeconds(0.3f);
            float downAt = Time.time;
            Line($"baton: swings {baton.Swings - swings0}, landed {baton.LastLanded}, NPC {target.name} state {target.State}, mode {cn.Current}, KO {cn.LastKnockOut:0.0} s, stun left {target.StunLeft:0.0}, slaps on him {cn.SlapCount}");
            Check(baton.LastLanded && target.IsDown && Mathf.Abs(cn.LastKnockOut - 4f) < 0.01f && cn.Current == CaptureV2Npc.Mode.KnockedOut, "baton: the bonk drops a standing NPC where he stands, out cold 4 s");
            Check(cn.Handprints == 0, "baton: no handprint (that is the slap's)");
            yield return Shot(pawn.ViewCamera, "baton_01_bonk_firstperson", 0.05f);
            int swings1 = baton.Swings;
            baton.ScriptStrike();
            Check(baton.Swings == swings1, "baton: a press inside the 0.9 s cooldown does not swing");
            float wake = -1f;
            while (Time.time - downAt < 12f)
            {
                if (target.State != NpcState.Down) { wake = Time.time - downAt + 0.3f - Tuning16(baton); break; }
                yield return null;
            }
            Line($"baton: he got up {wake:0.0} s after the contact (KO 4 s)");
            Check(wake > 3.6f && wake < 5.5f, "baton: out cold for the baton's 4 s, then up");
            // a miss: nobody in reach
            yield return new WaitForSecondsRealtime(1f);
            Vector3 empty = pawn.Position + Vector3.up * 1.4f;
            yield return Aim(pawn, hands, pawn.Position, empty + Vector3.up * 3f);
            int s2 = baton.Swings;
            baton.ScriptStrike();
            yield return new WaitForSecondsRealtime(0.4f);
            Check(baton.Swings == s2 + 1 && !baton.LastLanded, "baton: a swing at the air lands on nobody");
            baton.Draw(false);
        }

        private static float Tuning16(CaptureV2BatonV01 b) => b.Tuning.Windup;

        private void Persist()
        {
            bool owned = BaseV2DirectorV01.TeamOwns(GearCatalogV2.Baton);
            Line($"persist: fund ${BaseV2DirectorV01.Balance}, baton owned {owned}");
            Check(owned, "persist: after a restart the team still owns the baton (V2 save)");
            ShopDisplayItemV2 display = ShopDisplayItemV2.Find(GearCatalogV2.Baton);
            Check(display != null, "persist: the display is still on the counter (not loot)");
        }

        // ================================================================== dock + workshop

        private IEnumerator Dock()
        {
            WorkshopDockV2 dock = WorkshopDockV2.Instance;
            if (dock == null || dock.Service == null || dock.Service.VanPark == null) { Check(false, "dock: the workshop dock and lift service exist"); yield break; }
            WorkshopServiceV01 service = dock.Service;
            TeamEconomy economy = TeamEconomy.Instance;
            int price = EconomyPrices.VanTierPrice(VanBranch.Engine, economy.ServerState.VanTier(VanBranch.Engine) + 1);
            while (BaseV2DirectorV01.Balance < price) { BaseV2DirectorV01.Instance.GiveTestCash(); yield return null; }
            VanController van = director.Van;
            var body = van.GetComponent<Rigidbody>();
            var seat = van.GetComponent<GreyboxVanSeat>();
            Transform park = service.VanPark;
            float speed0 = van.MaxSpeedKmh;
            Line($"dock: van {van.name} top speed {speed0:0} km/h, engine tier {economy.ServerState.VanTier(VanBranch.Engine)}, price of the next ${price}, fund ${BaseV2DirectorV01.Balance}");
            // A: too fast through the zone: no dock
            yield return PlaceVan(van, body, park, -4.5f);
            yield return EnterSeat(seat);
            Check(seat.Driving, "dock: the player is at the wheel");
            int docks0 = dock.Docks;
            Creep(body, park.forward * 1.4f);
            yield return new WaitForSeconds(3.1f);
            Line($"dock: fast pass: van {LocalTo(park, van.transform.position)} speed {Speed(body):0.00} m/s, docks {dock.Docks - docks0}");
            Check(dock.Docks == docks0 && !service.Session.Active, "dock: 1.4 m/s through the zone does not dock");
            Creep(null, Vector3.zero);
            yield return PlaceVan(van, body, park, -2.7f); // just out of the zone (re-armed), still driving
            // B: slow creep: docks
            Creep(body, park.forward * 0.45f);
            float t0 = Time.time;
            float nextProbe = 0f;
            while (dock.Docks == docks0 && Time.time - t0 < 30f)
            {
                if (Time.time >= nextProbe) { nextProbe = Time.time + 0.5f; Line($"dock: creep {Time.time - t0:0.0} s: {dock.Probe}"); }
                yield return null;
            }
            Creep(null, Vector3.zero);
            Check(dock.Docks == docks0 + 1, "dock: a slow creep (under 0.5 m/s) into the zone docks once");
            Line($"dock: docked after {Time.time - t0:0.0} s at {LocalTo(park, van.transform.position)}; driver out {(!seat.Driving)}, player at {LocalTo(park, director.Pawn.Position)}; {dock.LastSignalNote}");
            Check(!seat.Driving, "dock: the driver stepped out");
            t0 = Time.time;
            while (service.Phase != LiftPhase.Up && Time.time - t0 < 15f) yield return null;
            Check(service.Phase == LiftPhase.Up, $"dock: the lift raised the van ({service.Height:0.00} m)");
            yield return new WaitForSeconds(0.4f);
            Clearance(van, service);
            Check(dock.Bubble != null && dock.Bubble.Showing && dock.Bubble.Line == dock.Greeting, "dock: the mechanic's bubble says «" + dock.Greeting + "»");
            Check(dock.MenuOpen, "dock: the upgrade menu is open for the driver");
            Line($"dock: bubble panel {dock.Bubble.PanelSize.x:0.00} x {dock.Bubble.PanelSize.y:0.00} m around text {dock.Bubble.TextSize.x:0.00} x {dock.Bubble.TextSize.y:0.00} m (text re-centred by {dock.Bubble.TextShift.x:+0.000;-0.000}, {dock.Bubble.TextShift.y:+0.000;-0.000} m)");
            WorkshopDockV2.EngineRow row = dock.Row();
            Line($"dock: menu engine row: tier {row.Tier} ({row.Now}) -> {row.Next} ({row.Then}), ${row.Price}, affordable {row.Affordable}");
            yield return ShotFrom(BaseV2Names.WorkshopReviewCam, "dock_01_van_raised_bubble_ground", null, dock.Bubble);
            yield return ShotFrom(BaseV2Names.WorkshopTopCam, "dock_02_van_raised_top", null, null, true);
            // the customer's own view from the spot he stepped out at: the mechanic and his bubble
            WorkshopMechanicBrainV01 brain = WorkshopMechanicBrainV01.Instance;
            if (brain != null && brain.HasBody)
            {
                CaptureV2Hands hands = CaptureV2Rig.Instance.Hands;
                hands.Aim(brain.BodyPosition + Vector3.up * 1.9f);
                yield return null;
                hands.Aim(brain.BodyPosition + Vector3.up * 1.9f);
                yield return Shot(director.Pawn.ViewCamera, "dock_04_customer_view_firstperson", 0.3f);
            }
            int fund0 = BaseV2DirectorV01.Balance;
            Check(dock.ScriptBuyEngine(), "dock: «Купить» sent");
            t0 = Time.time;
            while (dock.Busy && Time.time - t0 < 25f) yield return null;
            yield return new WaitForSeconds(0.2f);
            int tier = economy.ServerState.VanTier(VanBranch.Engine);
            Line($"dock: purchase answer «{dock.LastStatus}»; engine tier {tier}, fund ${fund0} -> ${BaseV2DirectorV01.Balance}, top speed {speed0:0} -> {van.MaxSpeedKmh:0} km/h, puffs {CountPuffs()}");
            Check(tier == row.Next && BaseV2DirectorV01.Balance == fund0 - row.Price, "dock: one engine tier bought, charged once");
            Check(van.MaxSpeedKmh > speed0 + 1f, "dock: the upgrade changes the driving (top speed up)");
            yield return ShotFrom(BaseV2Names.WorkshopReviewCam, "dock_03_after_upgrade_ground", null, dock.Bubble);
            dock.ScriptDone();
            t0 = Time.time;
            while ((service.Session.HoldsVan || service.Session.Active) && Time.time - t0 < 15f) yield return null;
            yield return new WaitForSeconds(0.5f);
            Check(!service.Session.HoldsVan && body != null && !body.isKinematic, "dock: «Готово» lowered and released the van");
            int docks1 = dock.Docks;
            yield return new WaitForSeconds(2f);
            Check(dock.Docks == docks1, "dock: a lowered van does not dock again in place");
            yield return EnterSeat(seat);
            Creep(body, -park.forward * 1.2f);
            yield return new WaitForSeconds(3.5f);
            Creep(null, Vector3.zero);
            Line($"dock: drove back out to {LocalTo(park, van.transform.position)}, driving {seat.Driving}");
        }

        private void Clearance(VanController van, WorkshopServiceV01 service)
        {
            Bounds vb = default;
            bool any = false;
            foreach (Renderer r in van.GetComponentsInChildren<Renderer>())
            {
                if (!r.enabled || r is ParticleSystemRenderer) continue;
                if (!any) { vb = r.bounds; any = true; } else vb.Encapsulate(r.bounds);
            }
            GameObject beam = GameObject.Find("C_lift_beam");
            float beamY = beam != null && beam.TryGetComponent(out Collider bc) ? bc.bounds.min.y : float.NaN;
            float floorY = service.VanPark.position.y;
            Line($"dock: raised van top {vb.max.y - floorY:0.00} m above the floor, lift beam underside {beamY - floorY:0.00} m: clearance {beamY - vb.max.y:0.00} m; van width with mirrors {vb.size.x:0.00} x {vb.size.z:0.00} (world AABB)");
            Check(float.IsNaN(beamY) || beamY - vb.max.y > 0.1f, "dock: the raised roof clears the lift beam");
        }

        private static int CountPuffs()
        {
            int n = 0;
            foreach (var t in FindObjectsByType<Transform>(FindObjectsSortMode.None)) if (t.name.Contains("Puff") || t.name.Contains("puff")) n++;
            return n;
        }

        private IEnumerator PlaceVan(VanController van, Rigidbody body, Transform park, float along)
        {
            Vector3 p = park.position + park.forward * along + Vector3.up * 0.06f;
            if (body != null)
            {
                body.linearVelocity = Vector3.zero;
                body.angularVelocity = Vector3.zero;
                body.position = p;
                body.rotation = park.rotation;
            }
            van.transform.SetPositionAndRotation(p, park.rotation);
            yield return new WaitForSeconds(1f);
        }

        private IEnumerator EnterSeat(GreyboxVanSeat seat)
        {
            if (seat == null || seat.Driving) yield break;
            director.Pawn.Teleport(seat.transform.TransformPoint(seat.DoorPoint) + Vector3.up * 0.05f, seat.transform.eulerAngles.y);
            yield return new WaitForSeconds(0.3f);
            seat.Enter();
            yield return new WaitForSeconds(0.3f);
        }

        private void Creep(Rigidbody body, Vector3 velocity)
        {
            creepBody = body;
            creepVelocity = velocity;
        }

        private void FixedUpdate()
        {
            if (creepBody == null) return;
            VanController v = creepBody.GetComponent<VanController>();
            if (v != null) { v.Handbrake = false; v.Throttle = 0f; }
            creepBody.linearVelocity = new Vector3(creepVelocity.x, creepBody.linearVelocity.y, creepVelocity.z);
        }

        private static float Speed(Rigidbody b) => b == null ? 0f : new Vector3(b.linearVelocity.x, 0f, b.linearVelocity.z).magnitude;
        private static string LocalTo(Transform park, Vector3 w) { Vector3 l = park.InverseTransformPoint(w); return $"(across {l.x:+0.00;-0.00}, along {l.z:+0.00;-0.00})"; }
        private static Vector3 Flat(Vector3 v) { v.y = 0f; return v.sqrMagnitude > 1e-6f ? v.normalized : Vector3.forward; }

        // ================================================================== helpers

        /// <summary>Stands the player at 'feet' and turns the view to 'look' (KCC yaw / pitch).</summary>
        private IEnumerator Aim(GreyboxPawn pawn, CaptureV2Hands hands, Vector3 feet, Vector3 look)
        {
            Vector3 d = look - (feet + Vector3.up * 1.6f);
            float yaw = Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg;
            float pitch = -Mathf.Atan2(d.y, new Vector2(d.x, d.z).magnitude) * Mathf.Rad2Deg;
            pawn.Teleport(feet, yaw);
            yield return null;
            for (int i = 0; i < 6; i++)
            {
                Camera cam = pawn.ViewCamera;
                if (cam != null)
                {
                    Vector3 e = look - cam.transform.position;
                    yaw = Mathf.Atan2(e.x, e.z) * Mathf.Rad2Deg;
                    pitch = -Mathf.Atan2(e.y, new Vector2(e.x, e.z).magnitude) * Mathf.Rad2Deg;
                }
                hands.SetView(yaw, pitch);
                yield return null;
            }
            yield return new WaitForSecondsRealtime(0.3f);
        }

        private RenderTexture Rt()
        {
            if (rt == null) { rt = new RenderTexture(1920, 1080, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 }; rt.Create(); }
            return rt;
        }

        private IEnumerator Shot(Camera cam, string name, float wait = 0.6f)
        {
            yield return new WaitForSecondsRealtime(wait);
            yield return null;
            if (cam == null) { Line("no camera for " + name); yield break; }
            Save(cam, name);
        }

        /// <summary>A review shot from a marker the builder placed (its forward = the view; top = straight down, wider).</summary>
        private IEnumerator ShotFrom(string marker, string name, System.Action before, SpeechBubbleV2 bubble = null, bool top = false)
        {
            GameObject m = GameObject.Find(marker);
            if (m == null) { Line("no marker " + marker); yield break; }
            before?.Invoke();
            if (shotCam == null)
            {
                shotCam = new GameObject("BaseV2 test shot camera").AddComponent<Camera>();
                shotCam.enabled = false;
                shotCam.nearClipPlane = 0.05f;
                shotCam.farClipPlane = 400f;
                var cd = shotCam.GetUniversalAdditionalCameraData();
                cd.renderPostProcessing = true;
                cd.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
            }
            shotCam.transform.SetPositionAndRotation(m.transform.position, m.transform.rotation);
            shotCam.fieldOfView = top ? 24f : 62f;
            SpeechBubbleV2.Viewer = shotCam.transform;
            List<Renderer> hidden = top ? HideOverhead() : null;
            yield return new WaitForSecondsRealtime(0.4f);
            yield return null;
            Save(shotCam, name);
            SpeechBubbleV2.Viewer = null;
            if (hidden != null) foreach (Renderer r in hidden) if (r != null) r.enabled = true;
        }

        /// <summary>Top view: the hangar roof, trusses, pendants and the rooms' ceilings / roof tops / lamps off for the shot.</summary>
        private static List<Renderer> HideOverhead()
        {
            var list = new List<Renderer>();
            GameObject hangar = GameObject.Find("Hangar_Base_v01");
            if (hangar == null) return list;
            string[] keys = { "roof", "truss", "pendant", "ceiling", "lamp", "light" };
            foreach (Renderer r in hangar.GetComponentsInChildren<Renderer>())
            {
                if (!r.enabled) continue;
                string n = (r.name + " " + (r.transform.parent != null ? r.transform.parent.name : "")).ToLowerInvariant();
                foreach (string k in keys) if (n.Contains(k)) { r.enabled = false; list.Add(r); break; }
            }
            return list;
        }

        private void Save(Camera cam, string name)
        {
            var prev = cam.targetTexture;
            cam.targetTexture = Rt();
            cam.aspect = 16f / 9f;
            cam.Render();
            cam.targetTexture = prev;
            cam.ResetAspect();
            var active = RenderTexture.active;
            RenderTexture.active = rt;
            var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
            tex.Apply();
            RenderTexture.active = active;
            string f = Path.Combine(outDir, name + ".png");
            File.WriteAllBytes(f, tex.EncodeToPNG());
            Destroy(tex);
            Line("shot " + f);
        }

        private void Check(bool ok, string what)
        {
            if (ok) pass++; else fail++;
            Line((ok ? "PASS " : "FAIL ") + what);
        }

        private void Line(string s)
        {
            Debug.Log("[BASEV2TEST] " + s);
            log.AppendLine(s);
        }

        private void Done()
        {
            Creep(null, Vector3.zero);
            Line($"done: {pass} PASS, {fail} FAIL");
            File.WriteAllText(Path.Combine(outDir, "log.txt"), log.ToString());
            File.WriteAllText(Path.Combine(outDir, "done.txt"), fail == 0 ? "PASS" : "FAIL");
        }

        private static void BlockInput()
        {
            PlayerLoopSystem loop = PlayerLoop.GetCurrentPlayerLoop();
            for (int i = 0; i < loop.subSystemList.Length; i++)
            {
                System.Type t = loop.subSystemList[i].type;
                if (t != typeof(UnityEngine.PlayerLoop.FixedUpdate) && t != typeof(UnityEngine.PlayerLoop.Update) &&
                    t != typeof(UnityEngine.PlayerLoop.PreLateUpdate)) continue;
                var list = new List<PlayerLoopSystem>(loop.subSystemList[i].subSystemList);
                list.Insert(0, new PlayerLoopSystem { type = typeof(BaseV2TestModeV01), updateDelegate = Input.ResetInputAxes });
                loop.subSystemList[i].subSystemList = list.ToArray();
            }
            PlayerLoop.SetPlayerLoop(loop);
            if (Keyboard.current != null) InputSystem.DisableDevice(Keyboard.current);
            if (Mouse.current != null) InputSystem.DisableDevice(Mouse.current);
        }
    }

    /// <summary>Names of the objects BaseV2BuilderV01 places (the test and review shots find them).</summary>
    public static class BaseV2Names
    {
        public const string Root = "Base_V2_P1 (Fedya)";
        public const string ShopCustomerSpot = "BaseV2 shop customer spot";
        public const string ShopReviewCam = "BaseV2 review cam GEAR";
        public const string WorkshopReviewCam = "BaseV2 review cam workshop";
        public const string WorkshopTopCam = "BaseV2 review cam workshop top";
    }
}
