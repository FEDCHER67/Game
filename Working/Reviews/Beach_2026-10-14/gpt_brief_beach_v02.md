You are a character designer helping the lead of a small indie game. Answer in English, compact markdown, no preamble.

## The game
VOLUNTEERS ONLY: a first-person co-op (1-4 players) physical-comedy game. Players knock out cartoon ADULT NPCs, physically drag the floppy ragdoll into their van, drive to a hideout and do a short cartoon "operation" (no gore). Systemic comedy: stories come from players, NPCs, props and the van. The world mixes post-Soviet / CIS everyday life (courtyards, village, dachas, Black Sea beach resorts like Anapa or Sochi) with a stylised American downtown. Humour is meme-literate and absurd, never sexual, never gory.

## Art and technical limits
- Stylised low-poly "sausage" NPCs: one shared body (a tall capsule head-and-neck, big round eyes, round nose, mitten hands), one shared skeleton and one shared animation set (idle, panic run, trip, play dead, hide, phone the police, double-take flee, sit on a bench, lie on the beach on the back).
- A type = clothes, hair, props, face paint, facial hair/teeth/glasses, a baked face (a mix of Happy, Surprised, Worried, Blink), body sliders (belly, thin, muscle, bust, glutes, game scale 0.9-1.1), the hang angle of the arms in idle (normally 64-72 degrees down; a small value means arms held out from the body), skin colour.
- Hand props are rigid in the hands and drop to the floor at the first danger. Worn props (hats, rigs, harnesses) stay on through the ragdoll. Budget about 12-18k triangles. A type must read in one second at 30-50 m by silhouette and colour.

## Images
- Image 1: the APPROVED pool of 30 types by district. The owner, Vadim, liked these because each is a very specific, instantly recognisable stereotype or meme with one exaggerated hook. Examples: the village granny-fashionista (rose headscarf, rhinestone cat-eye glasses, quilted telogreika, galoshes), the accordion grandpa in flowery family boxers and a kartuz, Karen with a "LIVE LAUGH LOVE" tee and a chihuahua in her bag, the loser rapper (faded smiley tee, cartoon willy pendant on a fake-gold chain, broken star shades, acne), the IRL streamer with a selfie stick.
- Image 2: the first five CITY BEACH types (v01), all REJECTED. Vadim: "crap; they do not stand out; every character needs its own signature twist; it is obvious this is idea-less neural slop". Your own earlier diagnosis: five costumes, not five characters; repeated silhouettes; mild faces; evenly spread cheerful colours. Approved types have one dominant colour mass, one absurd feature and one readable attitude.

## The new beach cast (Vadim's own words, translated)
Vadim replaced the cast. He now wants exactly these four:
1. **The beach corn seller** — "like on CIS beaches: walks the beach in slippers, dumb and pushy". The v01 (skinny tanned guy, gold chain, belly bag, rolled-up track pants, red cap, small blue bucket of cobs) was rejected. Your earlier options were a corn-cob ring around the waist, a giant mayonnaise bottle on the back and a huge aluminium boiler pot on a chest harness. You may keep, merge or beat them.
2. **The dumb sand-castle builder** (new) — an adult on the beach building sand castles, "dumb".
3. **The sunburnt one who lies on a lounger and also walks around** — the same type is placed lying on his back on a beach lounger (sun lounger, about 0.35 m high) and also walks around the beach. When lying he is seen mostly from above and from the side by a standing player; when walking, from all sides. The hook must read in BOTH states.
4. **The macho lifeguard, but also dumb** — a beach lifeguard who poses as a macho hero and is an idiot.

## What I need
1. For EACH of the four roles: 3 concept options. Each option is built around ONE strong signature hook and lists:
   - pitch (one line);
   - the hook;
   - silhouette change readable at 40 m that only this type has (hat, big worn prop, body slider, arm angle...);
   - face (expression mix plus paint, facial hair, teeth, glasses);
   - palette: 2-3 colours plus one accent;
   - hand prop (dropped at first danger) and worn props (stay on in ragdoll);
   - in-game gag that uses our mechanics (noticing the player, fleeing, being grabbed and dragged, being loaded into the van, the operation, dropping hand props, being a witness); no new animations unless unavoidable, and say so if one is needed;
   - the CIS or meme reference Vadim would recognise;
   - build cost (what new geometry).
2. Your single best option per role, with a one-line reason.
3. Make the four read as a set at one glance: give each a different dominant colour mass and a different silhouette shape (tall / wide / low / long), and say which is which.

## Rules
- Adults only. No sexualised content (the lifeguard's macho act is comic vanity, not sexy). No likeness of a specific real person (parody archetypes are fine; flag any idea that leans on a real person, e.g. a famous TV lifeguard actor). No gore.
- Plain socks with sandals, plain sunglasses, a plain panama, a plain towel, a plain whistle or plain red shorts are NOT hooks on their own. Avoid generic "beach tourist" filler.
- The joke must be visible on the model, not only in a backstory.
