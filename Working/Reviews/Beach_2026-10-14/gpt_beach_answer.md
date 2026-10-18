## 1. Why v01 fails

- **Five outfits, very few characters.** The approved pool suggests a particular person with particular bad habits. These suggest categories from an asset store.
- **The silhouettes repeat:** tall capsule, modest torso, thin legs, small hat, arms hanging similarly. The duck ring changes one outline; everyone else needs their accessories inspected.
- **The detector carries the treasure hunter’s entire identity.** Remove it and he becomes a pensioner in shorts. Nothing communicates his spectacularly misplaced confidence.
- **The sunburn is the strongest starting point, but stops at “red skin.”** The duck float, panama and sunglasses are familiar beach decorations without a single organising joke.
- **The nudist’s censor is the only distinctive feature.** Otherwise he shares the holidaymaker’s hat and the hunter’s sandals. His belly is too restrained to establish a memorable profile.
- **The ordinary holidaymaker is exceptionally forgettable.** Orange tee, blue shorts, small pattern, pleasant smile: no exaggeration, contradiction or recognisable holiday behaviour.
- **The corn seller looks like a generic moustached vendor.** A small bucket and one cob are visually weaker than the burdensome, improvised selling rigs associated with this role.
- **Faces and palettes soften everything.** Similar attentive eyes and mild expressions; evenly distributed cheerful colours. The approved characters have stronger hierarchies: one dominant colour mass, one absurd feature, one readable attitude.

## 2. Fifteen options

**Shared implementation:** faces below are baked mixes. Gags use existing animations, dropped props and ordinary ragdoll collisions; **no new animations required**. Large costume pieces need simple collision proxies where snagging is part of the joke. Each option names one signature hook; supporting details reinforce it.

### 1. Treasure hunter — confidently stupid

**A. The Bottle-Cap Tsar**

- **Pitch:** He has discovered the beach’s greatest treasure: thousands of worthless beer caps. **Hook:** a gigantic bottle-cap crown.
- **Silhouette:** five oversized, crimp-edged caps form a broad crown above his existing headphones; thin body, arms at 70°. **Face:** Happy > Surprised, tiny Blink contribution; one missing upper tooth, magnifying prescription lenses. **Palette:** olive, cream, tarnished gold; acid-yellow accent.
- **Gag:** he drops the detector when frightened, but his royal crown remains on the ragdoll. The “king” arrives at the hideout head-first. **Reference:** the detector enthusiast proudly displaying a bag of rubbish as archaeological treasure. **Cost:** cap crown, simple crown collider, reused detector/headphones.

**B. The Foil Professor**

- **Pitch:** He trusts his detector completely and distrusts every invisible signal around it. **Hook:** an enormous pointed foil helmet.
- **Silhouette:** tall, crumpled silver cone with broad ear flaps; narrow body, arms at 68°. **Face:** Worried > Happy with Surprised; pursed mouth, uneven stubble, thick corrective glasses. **Palette:** silver, burgundy, charcoal; lime accent.
- **Gag:** the detector drops at first danger. The supposedly protected professor immediately uses the existing hide animation, leaving the conspicuous silver cone visible. **Reference:** the *шапочка из фольги* conspiracy crank transplanted to a resort beach. **Cost:** faceted helmet; existing clothes and detector.

**C. The Walking Sieve**

- **Pitch:** He brought industrial equipment to find three roubles. **Hook:** a huge sand sieve worn like a rigid apron.
- **Silhouette:** circular sieve reaches from chest to knees, making a broad disc around a skinny capsule; arms at 60° to clear it. **Face:** Happy > Surprised, slight Blink; buck teeth, chalky sunscreen across nose. **Palette:** rust orange, khaki, cream; turquoise accent.
- **Gag:** his dropped detector becomes an obstacle while the sieve makes rotating him through the van doorway awkward. **Reference:** the overequipped DIY hobbyist whose solution is larger than the problem. **Cost:** sieve frame with baked perforation texture, harness, simple disc collider.

### 2. Sunburnt tourist — confidently cooked

**A. The Vest That Isn’t There**

- **Pitch:** He removed his vest, but the vest-shaped tan line stayed. **Hook:** a giant white tank-top silhouette painted onto lobster-red skin.
- **Silhouette:** maximum permitted belly, tiny royal-blue shorts, no torso garment; two thick, pale “straps” remain readable from behind. Arms at 72°. **Face:** Surprised > Worried, trace Happy; red nose, white sunscreen moustache, watery-looking painted eye rims. **Palette:** lobster red, ivory, royal blue; lemon accent.
- **Gag:** panic running makes the pale belly billboard bob through the crowd; it remains identifiable while he is dragged upside down. **Reference:** “I only lay down for twenty minutes” and the classic *майка-загар*. **Cost:** skin texture and belly adjustment; existing shorts.

**B. The Sour-Cream Prescription**

- **Pitch:** His entire sunburn treatment came from the supermarket dairy aisle. **Hook:** a visibly sour-cream-smeared torso.
- **Silhouette:** broad belly beneath a cropped, open beach shirt; an oversized sour-cream tub in one hand exaggerates the initial outline. The persistent hook is thick white body patches. **Face:** Worried > Surprised, slight Blink; miserable mouth, pink eyelid paint. **Palette:** coral red, dairy white, navy; green accent.
- **Gag:** he abandons his precious tub at first danger. Its rigid lid and tub roll separately if the existing prop system supports detachable pieces; otherwise use one piece. **Reference:** the recognisable home-remedy image of a tourist coated in *сметана*—a joke, not treatment advice. **Cost:** body texture, tub; optional separate lid.

**C. The Human Beach Stamp**

- **Pitch:** He fell asleep on a patterned lounger and woke up upholstered. **Hook:** huge alternating red-and-white burn stripes.
- **Silhouette:** widest shoulders available, narrow legs, small swim shorts; uncovered striped torso forms a bold rectangular colour mass. Arms at 66°. **Face:** Happy > Worried with Surprised; oblivious grin, one raised eyebrow, peeling-nose paint. **Palette:** crimson, pale cream, petrol blue; orange accent.
- **Gag:** his striped ragdoll is immediately recognisable among everyone piled in the van; the owner of the “matching” lounger can become a witness through existing behaviour. **Reference:** the holiday photo where a disastrous tan is presented as a successful vacation. **Cost:** skin texture only, reused shorts.

### 3. Old nudist — nonsexual cartoon eccentric

**Coverage for every option:** use an **opaque pelvis mesh covering front, back, sides and underside**, with large pixel blocks. Keep it attached through every animation and ragdoll pose. This gives dependable visual coverage; it is not a guarantee of platform approval.

**A. Censored Beyond All Reason**

- **Pitch:** A tiny old man has been classified as a gigantic broadcasting emergency. **Hook:** an absurdly oversized pixel-censor box.
- **Silhouette:** thin body at scale 0.9; a wide, rigid censor cuboid projects well beyond both hips. Arms at 72°. **Face:** Happy > Blink, slight Surprised; magnificent white horseshoe moustache, bald crown, two visible teeth. **Palette:** warm tan, charcoal, pale grey; cyan accent.
- **Gag:** his censor box jams across the van opening; players must rotate the entire dignified pensioner to load him. **Reference:** Sims censorship and television mosaics inflated into physical slapstick. **Cost:** opaque textured box and box collider; moustache.

**B. The Walking Privacy Booth**

- **Pitch:** He believes a changing booth counts as being dressed. **Hook:** a rigid striped changing screen worn around his waist.
- **Silhouette:** tall oval enclosure from waist to below knees, with skinny calves underneath; no hat. Arms at 64°. **Face:** Happy > Surprised, slight Blink; curled white moustache, smug closed mouth, round reading glasses. **Palette:** faded mint, cream, tan; vermilion accent.
- **Gag:** the enclosure hides his pelvis but makes his hiding animation hilariously ineffective; dragging him produces a mobile, toppled beach booth. **Reference:** municipal changing cabins and the grandfather who has found a technical loophole. **Cost:** lightweight booth shell, straps, oval collider; opaque inner coverage.

**C. The Censorship Officer**

- **Pitch:** He has brought his own official prohibition sign. **Hook:** a giant red-and-white “STOP” plaque mounted over the censor.
- **Silhouette:** broad octagonal hip plate against a round belly; bare bald head, arms at 70°. The sign shape works without reading its text. **Face:** Worried > Happy with Blink; stern white eyebrows, clipped moustache, one gold tooth. **Palette:** tan, white, dark brown; signal-red accent.
- **Gag:** the existing phone-police animation makes him look like a walking complaint department; when dragged, his sign becomes an unhelpful instruction to the players. **Reference:** the self-appointed beach rule enforcer and Soviet-style prohibition signage. **Cost:** sign plate, mounting straps, opaque wraparound censor.

### 4. Ordinary holidaymaker — BASE NPC, plain tee and shorts

These stay deliberately simpler than the other roles. Their joke comes from one exaggerated holiday habit.

**A. The Buffet Sphere**

- **Pitch:** He booked seven days of unlimited food and intends to collect every portion. **Hook:** the largest belly the shared body permits, inside a stretched plain tee.
- **Silhouette:** unmistakable pear shape: huge middle, narrow shoulders and calves; scale 1.05, arms at 72°. No accessory required. **Face:** Happy > Blink, trace Surprised; deeply contented smile, faint sauce stain at one mouth corner. **Palette:** butter yellow, burgundy, cream; tomato-red accent.
- **Gag:** play-dead turns him into an apparently immovable holiday parcel; narrow van loading becomes a cooperative rotation problem. **Reference:** the recognisable “all-inclusive must pay for itself” holiday mentality. **Cost:** belly slider and tee fit adjustment; face texture.

**B. Room-Key Hostage**

- **Pitch:** The hotel trusts him with a key attached to half a chopping board. **Hook:** an enormous hotel key fob hanging on his chest.
- **Silhouette:** long, bright rectangular fob from sternum to upper thighs; otherwise untouched BASE NPC, plain tee and shorts, arms at 68°. **Face:** Worried > Surprised, slight Happy; anxious smile, asymmetric eyebrows, light stubble. **Palette:** pale blue, navy, cream; fluorescent-orange accent.
- **Gag:** he drops his hand-held phone but keeps the absurd key attached; even inside the van, he visibly belongs to “Room 404.” **Reference:** oversized boarding-house key tags and the guest terrified of losing the deposit. **Cost:** rigid key/fob and short strap; no secondary-motion system.

**C. The Lounger Turtle**

- **Pitch:** He carries his own folding lounger because every beach charges too much. **Hook:** a folded lounger strapped vertically to his back.
- **Silhouette:** rectangular chair frame rises above his head and extends behind his calves; BASE body, plain tee and shorts, arms at 70°. **Face:** Happy > Worried with Blink; stubborn smile, thick brows, pale nose-sunscreen stripe. **Palette:** forest green, sand, aluminium grey; orange accent.
- **Gag:** the chair keeps him visibly exposed during hide; dragging him backwards makes the frame catch at the van threshold. **Reference:** the frugal dacha dad who brings his own solution to every paid convenience. **Cost:** folded chair, straps, simplified frame collider.

### 5. Corn seller — pushy beach entrepreneur

**A. The Corn Satellite**

- **Pitch:** He has converted himself into a mobile corn kiosk. **Hook:** a huge, fixed corn-stock ring around his waist.
- **Silhouette:** broad yellow cob-filled hoop below a narrow torso; dark shorts, slippers, arms at 58° to clear the stock. **Face:** Happy > Surprised, slight Worried; forceful grin, uneven moustache, one gold tooth. **Palette:** maize yellow, dark green, charcoal; red accent.
- **Gag:** he drops one sales cob at danger, but his attached kiosk remains; two players discover that loading a horizontal corn ring takes negotiation. **Reference:** “Горячая кукуруза!” as relentless beach infrastructure. **Cost:** rigid ring/basket, a few reused cob meshes, broad simple collider.

**B. The Sauce Mortar**

- **Pitch:** He has enough mayonnaise to service the entire coastline. **Hook:** a gigantic squeeze bottle mounted vertically on his back.
- **Silhouette:** oversized white bottle with a pointed red nozzle towers above his cap; thin body, arms at 66°. **Face:** Happy > Worried with Surprised; salesman’s fixed grin, brush moustache, sweat paint. **Palette:** cream, maize yellow, dark blue; ketchup-red accent.
- **Gag:** his ordinary hand bucket drops immediately, while the enormous nozzle makes hiding behind low objects futile. Loading him feet-first leaves the nozzle sticking up like a distress marker. **Reference:** the beach seller who insists every purchase needs an extra topping. **Cost:** rigid bottle, harness, bottle collider; reused bucket/corn.

**C. The Boiler Salesman**

- **Pitch:** He walks the beach carrying a pot large enough to feed a wedding. **Hook:** an enormous corn boiler hanging from a chest harness.
- **Silhouette:** silver drum projects in front of the belly; chunky legs, slippers, arms at 60°. **Face:** Surprised > Happy, trace Worried; open sales-call mouth, heavy moustache, missing side tooth. **Palette:** aluminium grey, faded purple, maize yellow; turquoise accent.
- **Gag:** his sample cob drops, but the attached boiler makes him roll awkwardly when dragged sideways and complicates entry into the van. **Reference:** improvised beach catering with battered household cookware and unstoppable sales patter. **Cost:** pot, fixed lid, harness, drum collider; no steam simulation needed.

## 3. Best option per role

| Role | Pick | Reason |
|---|---|---|
| Treasure hunter | **Bottle-Cap Tsar** | His worthless “treasure” becomes a permanent, readable monument to his stupidity. |
| Sunburnt tourist | **Vest That Isn’t There** | The joke reads instantly, survives ragdoll chaos and costs almost no geometry. |
| Old nudist | **Censored Beyond All Reason** | The required coverage becomes the character’s silhouette and physical-comedy hook. |
| Ordinary holidaymaker | **Buffet Sphere** | Preserves the BASE NPC brief while giving plain clothes a recognisable person inside them. |
| Corn seller | **Corn Satellite** | Identifies his trade at distance and turns pushy beach commerce into a loading problem. |

## 4. Two stronger extra beach types

**The Banana-Ride Captain**

An adult rental hustler wears a **ridiculously long inflatable banana around his waist**, with tiny fake passenger handles. Navy rash vest, yellow inflatable, white visor; red accent. Baked Happy > Surprised face, nautical moustache, one gold tooth. The banana stays attached while he panics and becomes a spectacular crosswise obstacle at the van door. Recognisable CIS *водный банан* reference; one rigid inflatable mesh, harness and capsule collider.

**The Churchkhela Chandelier**

An adult beach confectionery seller wears a **vast rigid shoulder yoke hung with thick, colourful churchkhela strings**, forming a walking chandelier. Plum apron, walnut brown, cream; grape-purple accent. Baked Happy > Worried face, booming open mouth and heavy brows. A sample drops at first danger; the attached display keeps advertising his location during hide and becomes a ridiculous frame around his dragged body. Recognisable Black Sea “чурчхела!” seller; one yoke, instanced low-poly confection strings and a simple outer collider.