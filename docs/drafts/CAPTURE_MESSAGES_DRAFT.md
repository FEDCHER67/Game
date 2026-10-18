## Все новые ID / All new IDs — G33

- `capture.van.knock_01`
- `capture.van.knock_02`
- `capture.van.knock_03`
- `capture.van.plead_01`
- `capture.van.plead_02`
- `capture.van.plead_03`
- `capture.van.threat_01`
- `capture.van.threat_02`
- `capture.van.threat_03`
- `capture.tied.hands_01`
- `capture.tied.hands_02`
- `capture.tied.hands_03`
- `capture.tied.feet_01`
- `capture.tied.feet_02`
- `capture.tied.feet_03`
- `capture.tied.both_01`
- `capture.tied.both_02`
- `capture.tied.both_03`
- `capture.bag.muffled_01`
- `capture.bag.muffled_02`
- `capture.bag.muffled_03`
- `capture.bag.lost_01`
- `capture.bag.lost_02`
- `capture.bag.lost_03`
- `capture.bag.bonk_01`
- `capture.bag.bonk_02`
- `capture.bag.bonk_03`
- `capture.bag_feet.pull_01`
- `capture.bag_feet.pull_02`
- `capture.bag_feet.hop_01`
- `capture.bag_feet.hop_02`
- `capture.bag_feet.fall_01`
- `capture.bag_feet.fall_02`
- `capture.bag_feet.fall_03`
- `capture.bag_hands.run_01`
- `capture.bag_hands.run_02`
- `capture.burrito.roll_01`
- `capture.burrito.roll_02`
- `capture.sleep.mumble_01`
- `capture.sleep.mumble_02`
- `capture.sleep.mumble_03`
- `capture.sleep.mumble_04`
- `capture.wake.01`
- `capture.wake.02`
- `capture.wake.03`
- `capture.wake.04`
- `capture.hint.van_full_01`
- `capture.hint.van_full_02`
- `capture.hint.van_full_03`
- `capture.hint.struggling_01`
- `capture.hint.struggling_02`
- `capture.hint.struggling_03`
- `capture.hint.no_blood_corpse_01`
- `capture.hint.no_blood_corpse_02`
- `capture.hint.no_ties_01`
- `capture.hint.no_ties_02`
- `capture.hint.no_ties_03`
- `capture.prompt.tie_hands`
- `capture.prompt.tie_feet`
- `capture.prompt.untie_hands`
- `capture.prompt.untie_feet`
- `capture.prompt.bag_on`
- `capture.prompt.bag_off`
- `capture.cloud.poof_01`
- `capture.cloud.poof_02`
- `capture.cloud.poof_03`
- `capture.clothes.hat_01`
- `capture.clothes.hat_02`
- `capture.clothes.hat_03`
- `capture.clothes.glasses_01`
- `capture.clothes.glasses_02`
- `capture.clothes.glasses_03`
- `capture.hint.accessories_fell`

# [G33] Захват и доставка: тексты RU / EN

Дата: 18 октября 2026. Статус: редакционный черновик, не утверждённые реплики и не новая механика.

Источник: `C:\Dev\Game\docs\specs\CAPTURE_DELIVERY_SPEC_2026-10-18_v01.md`, прочитан целиком. Ограничения крови и наркоза — OPERATIONS §§5, 10, 11; стиль и формат — BUYER_MESSAGES_DRAFT.md и buyer_messages.json.

JSON — плоский массив с теми же полями `id`, `buyer`, `situation`, `ru`, `en`, `placeholders`. `capture.*` — новый префикс в существующем стиле: строчные слова, точки, варианты `_01`/`_02`; `buyer` здесь сохраняет форму таблицы и обозначает говорящего (`NPC`/`SYSTEM`), а не нового покупателя. Привязка к коду не выполнена.

Предлагаемая подача: английский по умолчанию, русский полностью параллельный; короткие бытовые жалобы и физическая комедия. Подсказки сначала объясняют действие. Никаких реальных препаратов, доз, медицинских инструкций, лута из карманов или денег за тело. Звуки стука, падения и эффект приглушения — не текстовые команды движку.

## Выбор реплик и условия

- Stage A: ван, стяжки, сон/пробуждение, подсказки, облако и упавшие аксессуары. Stage B: мешок и все комбинации; грузовые улучшения также B. Наличие текста не включает Stage B.
- Proposed: выбирать один вариант на событие без немедленного повтора, не накладывать несколько реплик одного NPC. Числовой cooldown не задан. Приоритет состояний: сон → мешок/комбинация → стяжки → обычная реплика фургона. Точные паузы/случайный выбор остаются открыты.
- `bag_feet_*` — только ноги связаны, руки свободны: NPC тянет мешок, затем падает, мешок остаётся. При связанных руках — `bag_hands` или `burrito`. Падение здесь не обещает смертельный исход; сам мешок не убивает.
- `van_full_*` используется при превышении текущей вместимости; для стокового фургона это четвёртый NPC. Реплики не предполагают, что на апгрейде по-прежнему всего три места.
- `struggling_*` относится к отказу забора крови, а не к запрету всех взаимодействий с бодрым NPC. Спящий либо надёжно связанный NPC допустим; достаточно ли одних рук/ног — открытый вопрос D7/CD-05.
- Отказ для трупа имеет приоритет над отказом из-за движения. Нельзя обещать кровь после смерти. Никакой реплики «безопасная доза»: пробуждение не обнуляет остаток наркоза, ops §10.
- `{interact}` — локализованная текущая кнопка взаимодействия, не жёстко заданная клавиша. Применение стяжек и мешка — удержание. Для снятия мешка не придуман таймер. Срезание требует допустимого ножа/скальпеля; отдельный полевой инструмент ещё не решён (§11).
- Шапка/очки говорят только при наличии соответствующей вещи и бодром NPC; спящий бормочет. `accessories_fell` показывать только если упали оба предмета. Вещи остаются мусором рядом со столом, ничего не начисляют.
- Облако полностью закрывает смену одежды; тот же NPC появляется в пациентских шортах. `poof_01` — нейтральная основная подпись; остальные — предлагаемые редкие варианты. Не менять голову, лицо или телосложение.

## Реплики / Lines

### Стучит в фургоне / Van knocking

Stage A; capture D6; §4. Situation: `van_knock`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.van.knock_01` | Эй! У вас багажник разговаривает! | Hey! Your cargo bay is talking! |
| `capture.van.knock_02` | Тук-тук! Это не подвеска! | Knock knock! That’s not the suspension! |
| `capture.van.knock_03` | Дверь откройте! Я уже постучал! | Open up! I’ve knocked already! |

### Просит выпустить / Van pleading

Stage A; capture D6; §4. Situation: `van_plead`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.van.plead_01` | Высадите здесь. Мне пешком полезно. | Drop me here. Walking’s good for me. |
| `capture.van.plead_02` | Я тихо выйду. Даже дверью не хлопну. | I’ll leave quietly. Won’t even slam the door. |
| `capture.van.plead_03` | Можно остановку? Навсегда. | Can we stop? Permanently. |

### Возмущается и угрожает / Van threats

Stage A; capture D6; §4. Situation: `van_threat`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.van.threat_01` | Я номер запомню! Как только увижу! | I’ll remember your plate! Once I see it! |
| `capture.van.threat_02` | Я на вас жалобу напишу. Длинную. | I’m writing a complaint. A long one. |
| `capture.van.threat_03` | У вас даже ручки изнутри нет! Это нарушение! | No handle on the inside! That’s a violation! |

### Связаны руки / Hands tied

Stage A; capture D2; §5.2. Situation: `hands_tied`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.tied.hands_01` | Я бы вам показал, но руки заняты. | I’d give you a gesture, but my hands are tied. |
| `capture.tied.hands_02` | Можно руки? Они вообще-то мои. | Can I have my hands back? They’re mine. |
| `capture.tied.hands_03` | Нос чешется. Вот теперь я злой. | My nose itches. Now I’m angry. |

### Связаны ноги: прыжки / Feet tied: hopping

Stage A; capture D2; §5.2. Situation: `feet_tied`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.tied.feet_01` | Я вам что, мешок для прыжков? | Is this a sack race? |
| `capture.tied.feet_02` | Шаг отменяется. Буду прыгать. | Walking’s off. Hopping it is. |
| `capture.tied.feet_03` | Не смейтесь. Это временная походка. | Don’t laugh. It’s a temporary walk. |

### Гусеница / Caterpillar

Stage A; capture D2; §5.2. Situation: `hands_and_feet_tied`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.tied.both_01` | Я человек, а не гусеница! | I’m a person, not a caterpillar! |
| `capture.tied.both_02` | Разверните меня. Не в ту сторону качусь. | Turn me round. I’m rolling the wrong way. |
| `capture.tied.both_03` | До двери докачусь — поговорим. | We’ll talk when I roll to the door. |

### Мешок: приглушённые реплики / Bag: muffled

Stage B; capture D2; §5.2. Situation: `bag_muffled`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.bag.muffled_01` | Ммф! Я ещё не закончил возмущаться! | Mmph! I wasn’t done complaining! |
| `capture.bag.muffled_02` | Ммф! Тут кто-нибудь снаружи есть? | Mmph! Anyone out there? |
| `capture.bag.muffled_03` | Ммф… Я вообще-то вас слышу. | Mmph… I can still hear you. |

### Мешок: потерял направление / Bag: disoriented

Stage B; capture D2; §5.2. Situation: `bag_disoriented`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.bag.lost_01` | Где тут вперёд? У мешка нет стрелочки! | Which way’s forward? No arrow on this bag! |
| `capture.bag.lost_02` | Я к выходу иду? Или к шкафу? | Am I heading for the exit? Or a cupboard? |
| `capture.bag.lost_03` | Кто выключил вообще всё? | Who switched everything off? |

### Мешок: стукнулся / Bag: bonk

Stage B; capture D2; §5.2. Situation: `bag_bonk`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.bag.bonk_01` | Ммф! Стена нашлась. | Mmph! Found the wall. |
| `capture.bag.bonk_02` | Ой. Значит, не туда. | Ow. Wrong way, then. |
| `capture.bag.bonk_03` | Опять столб? У вас их сколько? | Another post? How many have you got? |

### Мешок + ноги: тянет мешок / Bag + feet: pulling

Stage B; capture D2; §5.2. Situation: `bag_feet_pull`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.bag_feet.pull_01` | Сейчас сниму эту… | I’ll just get this off… |
| `capture.bag_feet.pull_02` | Так. За край и… | Right. Grab the edge and… |

### Мешок + ноги: прыгает / Bag + feet: hopping

Stage B; capture D2; §5.2. Situation: `bag_feet_hop`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.bag_feet.hop_01` | Сначала прыгну. Потом разберусь. | Hop first. Work it out later. |
| `capture.bag_feet.hop_02` | Равновесие есть. Почти. | Got my balance. Almost. |

### Мешок + ноги: упал, мешок остался / Bag + feet: fall

Stage B; capture D2; §5.2. Situation: `bag_feet_fall`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.bag_feet.fall_01` | Ммф! Мешок победил. | Mmph! The bag wins. |
| `capture.bag_feet.fall_02` | Пол нашёл. Выход пока нет. | Found the floor. Still no exit. |
| `capture.bag_feet.fall_03` | Не помогло. Повторять не буду… | Didn’t work. Not trying that again… |

### Мешок + руки / Bag + hands

Stage B; capture D2; §5.2. Situation: `bag_hands`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.bag_hands.run_01` | Руль бы мне. И руки. | Could use a steering wheel. And my hands. |
| `capture.bag_hands.run_02` | Я бегу на звук! Не двигайте звук! | I’m running towards the sound! Keep it still! |

### Полный буррито / Full burrito

Stage B; capture D2; §5.2. Situation: `bag_hands_feet`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.burrito.roll_01` | Ммф! Я не свёрток! | Mmph! I’m not a parcel! |
| `capture.burrito.roll_02` | Ммф… Доставка возражает. | Mmph… This delivery objects. |

### Спит: бормочет / Asleep: mumbling

Stage A; capture D1; D6; §5.2. Situation: `asleep_mumble`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.sleep.mumble_01` | Мне без лука… | No onions for me… |
| `capture.sleep.mumble_02` | Ещё пять минуточек… | Five more minutes… |
| `capture.sleep.mumble_03` | Я чек сохранил… | I kept the receipt… |
| `capture.sleep.mumble_04` | Кот… верни тапок… | Cat… give my slipper back… |

### Просыпается / Waking after anesthesia

Stage A; capture D1; D6; ops §10. Situation: `anesthesia_waking`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.wake.01` | Так. Кто переставил потолок? | Right. Who moved the ceiling? |
| `capture.wake.02` | А где то место, где я был? | Where’s the place I was before? |
| `capture.wake.03` | Я что-то пропустил? Кроме остановки. | Did I miss something? Apart from my stop. |
| `capture.wake.04` | Последнее помню — был против. | Last thing I remember, I objected. |

### Фургон переполнен / Van over capacity

Stage A; capture D5; §4. Situation: `van_over_capacity`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.hint.van_full_01` | Тесно, не влезает. | Too cramped. Won’t fit. |
| `capture.hint.van_full_02` | Лишний пассажир. Кузов не растянется. | One passenger too many. The van won’t stretch. |
| `capture.hint.van_full_03` | Мест нет. Убери одного из кузова. | No room. Take someone out. |

### Цель дёргается / Target struggling

Stage A; capture D7; CD-05. Situation: `blood_target_struggling`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.hint.struggling_01` | Он дёргается — свяжи или усыпи. | He’s struggling. Tie him up or put him to sleep. |
| `capture.hint.struggling_02` | Сначала свяжи или усыпи. Сейчас не получится. | Tie him up or put him to sleep first. Not like this. |
| `capture.hint.struggling_03` | Для забора крови он слишком бодрый. | Too lively for blood collection. |

### Кровь у трупа / Dead target

Stage A; capture D7; D10; CD-05. Situation: `blood_target_dead`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.hint.no_blood_corpse_01` | Нельзя взять кровь у трупа. | Can’t draw blood from a corpse. |
| `capture.hint.no_blood_corpse_02` | Он мёртв. Кровь взять нельзя. | He’s dead. No blood collection. |

### Стяжки кончились / Out of zip ties

Stage A; capture D2; §5.1. Situation: `zip_ties_empty`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.hint.no_ties_01` | Стяжки кончились. | Out of zip ties. |
| `capture.hint.no_ties_02` | Нужны стяжки. Эти уже закончились. | Need zip ties. You’re all out. |
| `capture.hint.no_ties_03` | Связать нечем — стяжек нет. | Nothing to tie him with. No zip ties. |

### Действие: руки / Prompt: tie hands

Stage A; capture D2; §5.1. Situation: `tie_hands_prompt`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.prompt.tie_hands` | Удерживать {interact}: связать руки | Hold {interact}: tie hands |

### Действие: ноги / Prompt: tie feet

Stage A; capture D2; §5.1. Situation: `tie_feet_prompt`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.prompt.tie_feet` | Удерживать {interact}: связать ноги | Hold {interact}: tie feet |

### Действие: освободить руки / Prompt: free hands

Stage A; capture D2; §5.1. Situation: `untie_hands_prompt`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.prompt.untie_hands` | Удерживать {interact}: срезать стяжки с рук | Hold {interact}: cut hand ties |

### Действие: освободить ноги / Prompt: free feet

Stage A; capture D2; §5.1. Situation: `untie_feet_prompt`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.prompt.untie_feet` | Удерживать {interact}: срезать стяжки с ног | Hold {interact}: cut foot ties |

### Действие: надеть мешок / Prompt: bag on

Stage B; capture D2; §5.1. Situation: `bag_on_prompt`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.prompt.bag_on` | Удерживать {interact}: надеть мешок | Hold {interact}: put bag on |

### Действие: снять мешок / Prompt: bag off

Stage B; capture D2; §5.1. Situation: `bag_off_prompt`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.prompt.bag_off` | {interact}: снять мешок | {interact}: remove bag |

### Облако смены одежды / Undress cloud

Stage A; capture D12; CD-02. Situation: `undress_cloud`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.cloud.poof_01` | Пуф! | Poof! |
| `capture.cloud.poof_02` | Пуф. Дресс-код соблюдён. | Poof. Dress code sorted. |
| `capture.cloud.poof_03` | Пуф. Теперь по форме. | Poof. Uniform on. |

### Упала шапка / Hat falls

Stage A; capture D12; ops §18. Situation: `hat_falls`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.clothes.hat_01` | Шапку-то за что? | What did my hat ever do? |
| `capture.clothes.hat_02` | Шапку не топчите. Она ещё хорошая. | Don’t tread on the hat. It’s still good. |
| `capture.clothes.hat_03` | Шапка вышла первой. | My hat got out first. |

### Упали очки / Glasses fall

Stage A; capture D12; ops §18. Situation: `glasses_fall`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.clothes.glasses_01` | Очки на полу. Очень удобно. | Glasses on the floor. Very handy. |
| `capture.clothes.glasses_02` | Без очков я вас не запомню. Повезло вам. | Can’t remember your faces without my glasses. Lucky you. |
| `capture.clothes.glasses_03` | Очки верните. Я ещё возмущаюсь. | Glasses back, please. I’m still complaining. |

### Подсказка: упавшие вещи / Fallen accessories hint

Stage A; capture D12; ops §18. Situation: `clothes_cleanup`.

| ID | RU | EN |
| --- | --- | --- |
| `capture.hint.accessories_fell` | Шапка и очки упали рядом со столом. Подбери. | Hat and glasses fell beside the table. Pick them up. |
