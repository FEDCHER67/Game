# V2 capture: slap, drag, cling, throw into the van (Vadim 30-31.10.2026)

Core rule: this action repeats all game long, so it must never get boring. Keep every locked animation short, let physics make each case different, add random faces, sounds and landings, and make it juicy (hit-stop, camera kick, heavy sound, the van rocks).

## 1. Slap (agreed)

- One slap on Q (also LMB with empty hands). Wide wind-up about 0.5 s, a loud smack, hit-stop 0.08 s, small camera shake.
- The NPC spins half a turn with a shocked face, then drops into a full ragdoll **like a sack**.
- Later options, not now: a double slap (second press), a kick in the butt.

## 2. Knocked out (agreed)

- Out cold for a short time: **2.5 s** (tunable).
- Face as funny as possible while out: X or spiral eyes, tongue out to the side, stars circling the head (readable from far).
- 0.5 s before waking the face changes to "huh?.." as a warning.

## 3. Grab points (agreed)

One player holds ONE point: the **head**, the **collar (shirt scruff)**, **one arm** (left or right), or **one leg** (left or right). Nobody holds two legs alone. Each point has its own carry animation, its own resistance animation and its own throw (left/right mirrored).

| Grab | Carry | How he resists once awake |
| --- | --- | --- |
| Head | dragged by the head, body trailing | grabs your wrist, kicks, digs heels |
| Collar | dragged on his back, heels scraping | digs heels in, kicks the air, grabs your hand |
| Arm | pulled along, knee-shuffling | yanks the arm back, tries to bite, other hand clings |
| Leg | dragged face down, head bonking on bumps | claws the ground, clings to everything, kicks with the other leg |
| Two players (e.g. arm + leg) | "hammock", full speed | only squirms, cannot cling; escape meter fills at half speed |

Speeds: the collar and head are fastest, about 85 %; the arm is medium; the leg is slowest, about 65 %; a two-player carry is 100 %. Tune them in play.

## 4. Cling and yank (agreed, direction option A)

- While dragged he grabs whatever is near: a post, fence, door frame, another NPC, even the van wheel. You stop dead.
- The mouse turns **heavy**, like pulling an aircraft yoke on take-off: the camera barely turns. An arrow shows where to pull, always away from what he holds (post on the right means pull left). So the direction changes every time.
- You need fast, strong mouse flicks along the arrow. A strength bar grows with flick speed and drains when you stop; slow dragging does nothing.
- Bar full: a loud "POP", he tears off, you both stumble back, his face says "nooo!", and sometimes a piece of the fence stays in his hand.
- **The key feel (Vadim 31.10):** the mouse actively fights back. While he clings, a counter-force keeps pulling your view and your hold toward what he holds; if you stop or move slowly, the camera is dragged back toward him. Only fast, strong flicks away from the anchor overpower it and tear him off. It should feel like physically wrenching him off the thing.
- With two players, both players' flicks add up.
- Alternative: slap him (Q) on the hands. He lets go at once, but each slap knocks him out for less time (2.5 → 1.5 → 0.7 s).

## 5. Throw into the van: only at the door, on E (agreed)

- No free throwing anywhere (it would be abused). The prompt "E — throw in" shows only within about 2 m of an open van door.
- E plays a short juicy throw, about 0.8 s, done like you own the place, with its own animation per grab:
  - collar or head: grab and fling him over, head first, like a sack of potatoes;
  - leg: half a hammer-thrower spin, then let go;
  - arm: spin him round and fling.
- Juice: hit-stop 0.1 s on release, a camera kick, a heavy "BOOM", the van dips on its springs and rocks. Inside he tumbles and lands in a seat, the belt goes "clack", and his face says "WTF".
- Variety: several landings (straight into the seat; upside down then flips; smacks the ceiling and drops), 8-10 faces, 15-20 screams.
- If all seats are full, the door won't take him: he bounces back (canon).

## 6. Two players: "one-two-three" (agreed)

- Two players holding the same NPC at the door see "ONE… TWO… THREE".
- Each E press swings the body between them (one, two). On "three" both press E.
- If they hit it together, it's a super throw: further, a special landing, longer hit-stop, a bigger van rock.
- If they're out of sync, it's a comic fail: he slips and flops on the ground by the door, and they grab him again. This should make players count out loud in voice chat.

## 7. Waking up (basic now, details later: Vadim "пробуждение потом проработаем")

- He wakes in your hands and an **escape meter** starts. It fills faster the longer and further you drag him, which is why the van should come close.
- He resists according to the grab (table in §3) and looks for something to cling to (§4).
- Meter full: he breaks free and runs off with a panicked face.
- Open: what more he can do (bite and drop, wriggle out of his jacket, shout for help so a nearby NPC hits you with a bag, play dead and then sprint). To be settled with Vadim.

## Build order

1. Slap → ragdoll sack fall → out-cold face → grab-point detection (head / collar / arm L/R / leg L/R), with a carry pose and speed for each → basic wake-up and escape meter → E throw at the van door with juice and variety. Single player, in the hangar test scene.
2. Cling and the heavy-mouse yank with the arrow and strength bar; the slap on the hands.
3. Two players: the hammock carry, summed yanks, the "one-two-three" throw (FishNet, host + client).
4. Wake-up details after the talk with Vadim.

Existing code to build on: PhysicsGrabber / NetworkGrabber (grab any ragdoll bone, up to 3 holds per NPC), NpcRagdoll / NpcRagdollPart, GreyboxNpc stun phases (Out / Groggy), GreyboxVanCargo / GreyboxVanSeat (seats, doors), CaptureNpc.
