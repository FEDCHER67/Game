## Все новые ID / All new IDs — G28

- `c01.syringe.offer`
- `c01.syringe.player_accept`
- `c01.syringe.player_decline`
- `c01.syringe.handover`
- `c01.syringe.paid`
- `c01.syringe.already_used`
- `c01.base.confirm`
- `c01.base.arrived_01`
- `c01.base.arrived_02`
- `c01.base.waiting`
- `c01.base.handover_01`
- `c01.base.handover_02`
- `c01.contact.first_sale`
- `c02.call.player_stock`
- `c02.call.player_terms`
- `c02.call.player_later`
- `c02.call.terms`
- `c02.call.player_book`
- `c02.call.meeting_point_01`
- `c02.call.meeting_point_02`
- `c02.call.player_confirm`
- `c02.call.player_cancel`
- `c02.call.cancel_before_arrival`
- `c02.call.already_booked`
- `c02.meeting.arrived_01`
- `c02.meeting.arrived_02`
- `c02.meeting.waiting_01`
- `c02.meeting.waiting_02`
- `c02.meeting.time_over`
- `c02.meeting.finish_group`
- `c02.case.open_01`
- `c02.case.open_02`
- `c02.case.inspect_01`
- `c02.case.inspect_02`
- `c02.trade.quote`
- `c02.haggle.ask_5`
- `c02.haggle.ask_10`
- `c02.haggle.ask_20`
- `c02.haggle.player_accept`
- `c02.haggle.player_refuse`
- `c02.haggle.accept_01`
- `c02.haggle.accept_02`
- `c02.haggle.refuse_first_01`
- `c02.haggle.refuse_first_02`
- `c02.haggle.counter`
- `c02.haggle.refuse_five`
- `c02.haggle.retry_five`
- `c02.haggle.retry_ten`
- `c02.haggle.second_refusal_01`
- `c02.haggle.second_refusal_02`
- `c02.haggle.breakdown_card`
- `c02.haggle.player_walkaway`
- `c02.trade.confirm`
- `c02.trade.paid_01`
- `c02.trade.paid_02`
- `c02.trade.unsuitable_01`
- `c02.trade.unsuitable_02`
- `c02.trade.unsuitable_card`
- `c02.quality.damaged_01`
- `c02.quality.acceptable_01`
- `c02.quality.good_01`
- `c02.quality.perfect_01`
- `c02.quality.perfect_plus_01`
- `c02.quality.damaged_02`
- `c02.quality.acceptable_02`
- `c02.quality.good_02`
- `c02.quality.perfect_02`
- `c02.quality.perfect_plus_02`
- `c02.cooler.missing_01`
- `c02.cooler.missing_02`
- `c02.cooler.inspection_ok`
- `c02.respect.level_1`
- `c02.respect.up_1`
- `c02.respect.down_1`
- `c02.respect.level_2`
- `c02.respect.up_2`
- `c02.respect.down_2`
- `c02.respect.level_3`
- `c02.respect.up_3`
- `c02.respect.down_3`
- `c02.respect.level_4`
- `c02.respect.up_4`
- `c02.respect.down_4`
- `c02.respect.level_5`
- `c02.respect.up_5`
- `c02.respect.down_5`
- `catalog.new.header`
- `catalog.new.card`
- `c02.special.hamlet_bodybuilder.pitch`
- `c02.special.hamlet_bodybuilder.clue_card`
- `c02.special.hamlet_bodybuilder.player_accept`
- `c02.special.hamlet_bodybuilder.accepted`
- `c02.special.hamlet_bodybuilder.player_decline`
- `c02.special.hamlet_bodybuilder.reminder_01`
- `c02.special.hamlet_bodybuilder.reminder_02`
- `c02.special.hamlet_bodybuilder.done`
- `c02.special.hamlet_bodybuilder.late`
- `c02.special.hamlet_bodybuilder.failed`
- `c02.special.hamlet_bodybuilder.wrong_target`
- `c02.special.hamlet_bodybuilder.wrong_quality`
- `c02.special.hamlet_bodybuilder.missing_packaging`
- `special.old_streamer.pitch`
- `special.old_streamer.clue_card`
- `special.old_streamer.player_accept`
- `special.old_streamer.accepted`
- `special.old_streamer.player_decline`
- `special.old_streamer.reminder_01`
- `special.old_streamer.reminder_02`
- `special.old_streamer.done`
- `special.old_streamer.late`
- `special.old_streamer.failed`
- `special.old_streamer.wrong_target`
- `special.old_streamer.wrong_quality`
- `special.old_streamer.missing_packaging`
- `special.shared.cancel_before_deadline`
- `special.shared.cancel_after_deadline`
- `special.shared.haggle_breakdown`
- `special.shared.handover_card`
- `special.shared.unsuitable_card`

# Тексты телефона покупателей — черновик / Buyer phone messages — draft

**Статус / Status:** черновик, не утверждён Федей и Вадимом. Ничего из этого файла не является требованием геймплея. / Draft, not approved. Nothing here is a gameplay requirement.

**Приоритет v02 / v02 priority:** `C:\Dev\Game\docs\specs\BUYERS_SPEC_2026-10-15_v02.md` — правила покупателей; `C:\Dev\Game\docs\VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md` — тон и лор. При расхождении старых реплик с v02 используются новые строки ниже. / Buyer rules follow v02; tone and lore follow the canon. Use the new v02 lines where legacy wording conflicts.

**Источники / Sources:** `docs/CITY_MAP_REFERENCE_SPEC.md` §6 (пролог, дед), §7 (сюжетная лестница), §8 (C01–C03, встречи, скрытое доверие), §13 (P01, P09), §20 (C-P02); `docs/VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md` §50–56 (чёрный рынок, перекупщик, спецзаказы, цены, передача товара), §72 (heat).

**Машиночитаемая версия / Machine-readable:** `docs/drafts/buyer_messages.json` — поля `id`, `buyer`, `situation`, `ru`, `en`, `placeholders`. Этот MD сгенерирован из тех же данных; при правках менять обе версии согласованно.

## Правила текста / Writing rules

- Тон: мультяшная чёрная комедия, короткие реплики в стиле переписки. Без крови на экране, без описаний тел и реальных медицинских процедур. Органы — только `{organ}` и игровые предметы.
- Покупатели получают только кровь (C01) или органы по своей специализации (C02, C03). Живых NPC и тела не принимают — C02 говорит это прямо (`c02.first.03`).
- Респект по v02: пять видимых названий, без числовой шкалы; старт — «новобранец». Старые `trust.*` — тональные варианты, не отдельная система доверия. / v02 respect uses five visible names without a numeric meter; starts at rookie. Legacy `trust.*` lines are tone variants, not a separate trust system.
- Heat без цифр: покупатели реагируют на «мигалки», «шум», «вопросы про фургон».
- Язык по умолчанию — английский; русский — полный параллельный перевод.

## Плейсхолдеры / Placeholders

| Плейсхолдер | Значение |
| --- | --- |
| `{organ}` | Название органа как игрового предмета (локализуется отдельно). |
| `{quality}` | Убитое / Сойдёт / Хорошее / Отличное / Идеальное; EN: Damaged / Acceptable / Good / Perfect / Perfect+ (v02). |
| `{price}` | Сумма с валютой, форматирует игра. |
| `{deadline}` | Абсолютный срок в игровом времени; спецзаказ — 48 игровых часов после согласования и явного принятия. |
| `{place}` | Название места встречи C03 (P09: основное или запасное) или иного места сделки. |

Дополнительные плейсхолдеры v02 перечислены ниже. Строка `c03.special.card` содержит переносы строк (`\n`) — это карточка «PRIVATE REQUEST» из канона §53.

## Что намеренно не написано / Deliberately left out

- **Дешёвый перекупщик «берёт всё»** (канон §51–52): роль пока не назначена (C-P02 не утверждено), поэтому C02 здесь принимает только органы, а не «всё». Реплики перекупщика — отдельной задачей после решения.
- **Приглашение на похороны** (`grandpa_funeral_invite`, достижение `ach.gp_funeral`) — идея Феди, в спецификации помечена как не утверждённая. Оставлено как опция.
- **Способ подсказки ремонта без деда** не выбран (§6.3, §21.2). Здесь предложены записки во дворе и одна системная подсказка; выбрать одно или несколько.
- Имена контактов в телефоне («Сантехник», «Бабушка») — шутки внутри реплик, не утверждённые названия.

## Открытые вопросы / Open questions

1. Как игра выбирает строку при нескольких вариантах (случайно, по порядку, по уровню доверия)?
2. C03 — «он»? В английском тексте C03 и клиент спецзаказа описаны как he; пол персонажей не задан в спецификации — поменять при необходимости.
3. Нужны ли отдельные реплики C02/C03 на провал после ареста или эвакуации бусика (сейчас есть только у C01, `comeback`)?

## Пролог: объявление на столбе (P01) / Prologue: the ad on the pole

### Объявление / Ad

| ID | RU | EN |
| --- | --- | --- |
| `p01.ad.title` | ПОКУПАЮ КРОВЬ. ДОРОГО. | BUYING BLOOD. GOOD MONEY. |
| `p01.ad.body` | Любая группа. Без справок. Без очереди. Без лишних вопросов. | Any type. No paperwork. No queue. No awkward questions. |
| `p01.ad.phone` | Тел.: 0-НЕ-ВАМПИР | Tel: 0-NOT-A-VAMPIRE |
| `p01.ad.small_print` | Мелким шрифтом: «Я правда не вампир. Вампиры не платят наличными». | Small print: "Really not a vampire. Vampires don't pay cash." |
| `p01.ad.tabs` | Отрывные листочки с номером. Одного уже нет — кто-то успел первым. | Tear-off tabs with the number. One is already gone. Someone got there first. |
| `p01.ad.remember_hint` | Где-то было объявление про кровь… На столбе у дороги. | There was an ad about blood somewhere… On the pole by the road. |
| `p01.ad.call_prompt` | Позвонить по объявлению? | Call the number from the ad? |

## C01 — первый покупатель крови / First blood buyer

### Первый контакт / First contact

| ID | RU | EN |
| --- | --- | --- |
| `c01.first.player_call` | Здравствуйте. Я по объявлению. | Hi. I'm calling about the ad. |
| `c01.first.01` | Кровь есть? Отлично. Где вы? | You've got blood? Great. Where are you? |
| `c01.first.02` | Вагон в лесу? Романтично. Еду. | A train car in the woods? Romantic. On my way. |
| `c01.first.03` | Я у вагона. Не машите руками, я вас и так вижу. | I'm at the train car. Stop waving, I can see you. |
| `c01.first.syringes_01` | Это что, шприцы? Ребята, это не бизнес, это кружок юных натуралистов. | Syringes? Guys, this isn't a business, it's a science-fair project. |
| `c01.first.syringes_02` | Ладно. Один шприц за $10, один раз, без торга. | Fine. One syringe for $10. Once, no haggling. |
| `c01.first.bags_rule` | Дальше — только в пакетах. Нормальных. Аптека в деревне, дойдёте пешком. | From now on, bags only. Proper ones. The village pharmacy has them, it's walking distance. |
| `c01.first.bags_rule_02` | Без пакетов не звоните. С пакетами — хоть ночью. | No bags, no calls. With bags, call me even at night. |
| `c01.first.save_contact` | Сохраните номер. Подпишите как-нибудь прилично. «Сантехник», например. | Save my number. Name it something respectable. "Plumber", maybe. |

### Наводка на деда / Grandpa tip

| ID | RU | EN |
| --- | --- | --- |
| `c01.grandpa_tip.01` | Пешком вы до пенсии не заработаете. Вам нужны колёса. | On foot you'll be working till retirement. You need wheels. |
| `c01.grandpa_tip.02` | На краю деревни живёт дед. У него во дворе бусик. Ржавый, как моя совесть. | There's an old man at the edge of the village. Got a van in his yard. Rusty as my conscience. |
| `c01.grandpa_tip.03` | Говорят, продаёт недорого. Деду деньги нужнее, чем бусик. Сами поймёте. | Word is he's selling cheap. He needs the money more than the van. You'll see why. |
| `c01.grandpa_tip.04` | И будьте с ним повежливее. Он хороший дед. Редкая порода. | And be nice to him. He's a good old man. Rare breed. |

### Стандартные предложения / Standard offers

| ID | RU | EN |
| --- | --- | --- |
| `c01.offer.player_has_stock` | Есть пакеты. | Got bags. |
| `c01.offer.01` | Беру. Предварительно {price}. К базе подъеду через час. | I’ll take it. Estimated {price}. At your base in an hour. |
| `c01.offer.02` | {price} за всё. Ставьте чайник. Шучу, не ставьте, я быстро. | {price} for the lot. Put the kettle on. Kidding, don't, I'll be quick. |
| `c01.offer.03` | Еду. Пакеты не трясите, они не погремушки. | On my way. Don't shake the bags, they're not maracas. |
| `c01.offer.arrived` | Я на месте. Выходите с пакетами и с хорошим настроением. Пакеты важнее. | I'm here. Come out with the bags and a good mood. Bags first. |
| `c01.offer.no_stock` | Вы позвонили просто поболтать? Мило. Но нет. | You called just to chat? Sweet. But no. |
| `c01.offer.not_bagged` | Это не пакет. Это пакет из-под кефира. Не принимаю. | That's not a bag. That's a milk carton. Not taking it. |
| `c01.offer.not_bagged_02` | Вводная акция закончилась. Аптека открыта. Вперёд. | The intro offer is over. The pharmacy is open. Off you go. |

### Согласие / Accept

| ID | RU | EN |
| --- | --- | --- |
| `c01.accept.player` | Договорились. | Deal. |
| `c01.accept.01` | Приятно иметь дело с людьми, у которых есть пакеты. | Always nice doing business with people who own bags. |
| `c01.accept.02` | Деньги ваши. Пакеты мои. Мир прекрасен. | Money's yours. Bags are mine. Life is beautiful. |

### Отказ / Decline

| ID | RU | EN |
| --- | --- | --- |
| `c01.decline.player` | Не, дёшево. | Nah, too cheap. |
| `c01.decline.01` | Цена как у всех. Ну, у всех, кто покупает кровь у вагона в лесу. | Same price as everyone. Well, everyone buying blood by a train car in the woods. |
| `c01.decline.02` | Ладно. Я никуда не денусь. Я постоянный, как насморк. | Fine. I'm not going anywhere. I'm permanent, like a cold. |

### Торг / Haggling

| ID | RU | EN |
| --- | --- | --- |
| `c01.haggle.player` | Накинь немного? | Throw in a bit more? |
| `c01.haggle.success` | Ладно, {price}. Но только потому, что пакеты ровные. | Fine, {price}. Only because the bags are nice and neat. |
| `c01.haggle.fail` | Я не аукцион. {price} — или я еду домой смотреть сериал. | I'm not an auction. {price}, or I go home and watch my show. |
| `c01.haggle.repeat` | Вы торгуетесь как моя тёща. Это не комплимент. | You haggle like my mother-in-law. That's not a compliment. |

### Доверие: тон / Trust: tone

| ID | RU | EN |
| --- | --- | --- |
| `c01.trust.t0` | Пакеты. Деньги. До свидания. | Bags. Money. Goodbye. |
| `c01.trust.t1` | Опять вы. Ладно, это уже почти стабильность. | You again. Okay, this is almost stability. |
| `c01.trust.t2` | Мои любимые поставщики. Никому не говорите, что у меня есть любимые. | My favourite suppliers. Don't tell anyone I have favourites. |
| `c01.trust.t3` | Для вас — {price}. Остальным не рассказывайте, обидятся. | For you, {price}. Don't tell the others, they'll get jealous. |

### Доверие: новые предложения / Trust: new offers

| ID | RU | EN |
| --- | --- | --- |
| `c01.trust.new_offer_bulk` | Наберёте побольше — заберу всё одним рейсом и накину сверху. | Collect more and I'll take it all in one trip and add a little extra. |
| `c01.trust.new_offer_night` | Ночью тоже звоните. Для своих у меня бессонница. | Call at night too. For regulars, I have insomnia. |

### Знакомство со следующим покупателем / Intro to next buyer

| ID | RU | EN |
| --- | --- | --- |
| `c01.intro_c02.01` | Первая кровь продана. Пора расширять знакомства. | First blood sale done. Time to expand your contacts. |
| `c01.intro_c02.02` | Есть знакомый, берёт органы. Номер скину; точку встречи сообщит сам. | Know someone who buys organs. I’ll send the number; he’ll tell you where to meet. |
| `c01.intro_c02.03` | Скажете, что от меня. Только не говорите, что я хороший. Мне там репутацию держать. | Say I sent you. Just don't tell them I'm nice. I have a reputation to keep. |
| `c01.intro_c02.04` | А кровь всё равно мне несите. Я ревнивый. | But keep bringing the blood to me. I get jealous. |

### Опоздание или неявка / Late or no-show

| ID | RU | EN |
| --- | --- | --- |
| `c01.late.self_01` | Опаздываю. Пробка. Из одного трактора. | Running late. Traffic jam. One tractor. |
| `c01.late.self_02` | Ещё пять минут. Пакеты не скисли? Шучу. Не скисли же? | Five more minutes. The bags haven't gone off? Kidding. They haven't, right? |
| `c01.late.player_01` | Я на месте. Вас нет. Пакетов, видимо, тоже. | I'm here. You're not. Neither are the bags, I guess. |
| `c01.late.player_02` | Уехал. Позвоните, когда материализуетесь. | I left. Call me when you materialise. |

### Внимание полиции / Police heat

| ID | RU | EN |
| --- | --- | --- |
| `c01.heat.01` | У вас там мигалки. Я не приеду, пока не утихнет. Я человек легальный. Относительно. | There are flashing lights near you. I'm not coming till it calms down. I'm a legal guy. Relatively. |
| `c01.heat.02` | Слишком шумно. Позвоните, когда станет скучно. | Too noisy over there. Call me when it gets boring. |
| `c01.heat.03` | Встречу отменяю. Если спросят — я собираю марки. Красные. | Meeting's off. If anyone asks, I collect stamps. Red ones. |

### Восстановление после провала / Comeback

| ID | RU | EN |
| --- | --- | --- |
| `c01.comeback.01` | Опять с нуля? Ничего. Кровь — как классика: всегда в моде. | Back to square one? No problem. Blood is a classic. Never goes out of style. |
| `c01.comeback.02` | Бусик отобрали? Бывает. Я на своём уже третий раз выкупаю. | Van got towed? Happens. I've bailed mine out three times. |

### Редкие шутки / Rare jokes

| ID | RU | EN |
| --- | --- | --- |
| `c01.joke.01` | Пейте воду. Это я не вам. Это я себе напоминаю. | Drink water. Not you. I'm reminding myself. |
| `c01.joke.02` | Спросили, чем я занимаюсь. Сказал: логистика. Почти не соврал. | Someone asked what I do. I said logistics. Barely a lie. |
| `c01.joke.03` | Купил новые пакеты для себя. В магазине. Для продуктов. Вот так и живу. | Bought some bags for myself today. At the store. For groceries. That's my life now. |

### Реакция на смерть деда / Grandpa-dead reaction

| ID | RU | EN |
| --- | --- | --- |
| `gpd.c01_react.01` | Дед больше не продаёт? Понятно. Только его мне не несите. Пробег большой. | The old man's not selling anymore? Got it. Don't bring him to me. Too many miles on the clock. |
| `gpd.c01_react.02` | Я же просил повежливее. Ладно. Бусик хоть заведите. Записки там у него везде. | I asked you to be nice. Fine. At least get the van running. He left notes everywhere. |

## C02 — теневая приёмка / Shadow intake

### Первый контакт / First contact

| ID | RU | EN |
| --- | --- | --- |
| `c02.first.01` | Вы от этого, с пакетами? Номер сохранил. Точку встречи сообщу. | You’re from the blood-bag fellow? Saved your number. I’ll send the meeting point. |
| `c02.first.02` | Кровь — это для романтиков. Я работаю с запчастями. | Blood is for romantics. I deal in spare parts. |
| `c02.first.03` | Правило одно: только товар. Людей не привозить. Целиком — тоже. | One rule: goods only. No people. Not in one piece, not at all. |
| `c02.first.04` | Хотите работы — езжайте в спальник. Там половина людей спит даже днём. | Want work? Go to the bedroom district. Half the people there sleep even in daytime. |
| `c02.first.05` | Вот пара наводок. Тихие люди. Их даже соседи не помнят. | Here are a couple of tips. Quiet folks. Even their neighbours forget them. |
| `c02.first.06` | Номер мой сохраните. Подпишите «Приёмка». Или «Бабушка». Бабушке никто не завидует. | Save my number. Call it "Intake". Or "Grandma". Nobody gets suspicious of Grandma. |

### Первый заказ / First order

| ID | RU | EN |
| --- | --- | --- |
| `c02.first_order.01` | Первый заказ: {organ}. Качество — хотя бы {quality}. Плачу {price}. | First order: {organ}. Quality: {quality} at least. I pay {price}. |
| `c02.first_order.02` | Срок — {deadline}. Не торопитесь. Но и не тяните. | Deadline: {deadline}. No rush. But don't stall. |
| `c02.first_order.03` | Это не всё, что у меня есть. Это проверка. | This isn't everything I've got. It's a test. |
| `c02.first_order.done` | Сдали. Неплохо. Я почти улыбнулся. Не привыкайте. | Delivered. Not bad. I almost smiled. Don't get used to it. |

### Стандартные предложения / Standard offers

| ID | RU | EN |
| --- | --- | --- |
| `c02.offer.player_has_stock` | Есть товар. Приеду? | Got stock. Can I come by? |
| `c02.offer.01` | Назначим встречу. Точку пришлю, буду через час. | Let’s book a meeting. I’ll send the spot. Be there in an hour. |
| `c02.offer.02` | За {organ} ({quality}) дам {price}. | For the {organ} ({quality}), I'll give {price}. |
| `c02.offer.03` | {organ}? Беру. Пока {price}. Загружайте в багажник. | {organ}? Buying. Current offer: {price}. Load it into the boot. |
| `c02.offer.low_quality` | Это {quality}? Видел я такое в банке с огурцами. Могу дать {price}. Из жалости. | That's {quality}? I've seen better in a pickle jar. I can do {price}. Out of pity. |
| `c02.offer.not_my_line` | Кровь? Это к вашему другу с пакетами. Я сентиментальный, но не настолько. | Blood? Take that to your bag friend. I'm sentimental, but not that much. |

### Согласие / Accept

| ID | RU | EN |
| --- | --- | --- |
| `c02.accept.player` | Идёт. | Deal. |
| `c02.accept.01` | Деньги в конверте. Конверт не возвращать, он у меня последний. | Money's in the envelope. Keep the envelope, I'm out anyway. |
| `c02.accept.02` | Хорошая работа. Багажник закрывайте мягко, он нервный. | Good work. Close the boot gently. It’s nervous. |

### Отказ / Decline

| ID | RU | EN |
| --- | --- | --- |
| `c02.decline.player` | Не, оставлю себе. | Nah, I'll keep it. |
| `c02.decline.01` | Ваше дело. Только он у вас не свежеет. | Your call. It's not getting any fresher, though. |
| `c02.decline.02` | Кладите в холодильник и думайте. Думать можно, портиться нельзя. | Put it in the fridge and think. Thinking is fine. Spoiling isn't. |

### Торг / Haggling

| ID | RU | EN |
| --- | --- | --- |
| `c02.haggle.player` | Можно побольше? | Can you do better? |
| `c02.haggle.success` | {price}. Не потому, что вы убедили. Потому что у меня хорошее настроение. | {price}. Not because you convinced me. Because I'm in a good mood. |
| `c02.haggle.fail` | Нет. Здесь не рынок. Здесь приёмка. Это хуже. | No. This isn't a market. It's an intake. That's worse. |
| `c02.haggle.repeat` | Второй отказ — и этот вид три часа не беру. Решайте. | A second refusal means I won’t buy this organ type for three hours. Your call. |

### Доверие: тон / Trust: tone

| ID | RU | EN |
| --- | --- | --- |
| `c02.trust.t0` | Кто вы? А. Вы. Ладно. | Who are you? Oh. You. Fine. |
| `c02.trust.t1` | Стучите два раза. Три — это для чужих. | Knock twice. Three is for strangers. |
| `c02.trust.t2` | Чай будете? Это не забота. Это ритуал. | Want some tea? It's not kindness. It's a ritual. |

### Доверие: новые предложения / Trust: new offers

| ID | RU | EN |
| --- | --- | --- |
| `c02.trust.new_offer_tips` | Есть ещё наводки. Для своих. Вы почти свои. | I've got more tips. For regulars. You're almost regulars. |
| `c02.trust.new_offer_order` | Есть заказ получше: {organ}, {quality}, {price}. Срок — {deadline}. | Got a better order: {organ}, {quality}, {price}. Deadline: {deadline}. |

### Знакомство со следующим покупателем / Intro to next buyer

| ID | RU | EN |
| --- | --- | --- |
| `c02.intro_c03.01` | У меня есть знакомый в больнице. Ему нужно качество, и платит он лучше меня. | I know someone at the hospital. He wants quality, and he pays better than I do. |
| `c02.intro_c03.02` | Не говорите ему, что я так сказал. Номер я вам скинул. | Don't tell him I said that. I've sent you the number. |
| `c02.intro_c03.03` | Будьте с ним вежливы. Он моет руки чаще, чем я дышу. | Be polite with him. He washes his hands more often than I breathe. |

### После знакомства / After the intro

| ID | RU | EN |
| --- | --- | --- |
| `c02.after_c03.01` | Больничный зазнался? Ничего. Я всегда тут. Без креста, зато без очереди. | Hospital guy got picky? No problem. I'm always here. No cross on the roof, but no queue either. |

### Опоздание или неявка / Late or no-show

| ID | RU | EN |
| --- | --- | --- |
| `c02.late.player_01` | Обещали час назад. Я уже начал волноваться. За товар, не за вас. | You said an hour ago. I'm getting worried. About the goods, not you. |
| `c02.late.player_02` | Три часа прождал. Уезжаю. Позвоните — назначим новую встречу. | Waited three hours. I’m leaving. Call to book another meeting. |
| `c02.late.order_expired` | Срок заказа на {organ} вышел. +25% сняты, выторгованный процент остаётся. Сдать ещё можно. | Deadline for {organ} passed. The +25% bonus is gone; your agreed haggle bonus stays. You can still deliver. |

### Внимание полиции / Police heat

| ID | RU | EN |
| --- | --- | --- |
| `c02.heat.01` | Не приезжайте сейчас. Под окнами патруль ест шаурму. Медленно. | Don't come now. There's a patrol outside eating a kebab. Slowly. |
| `c02.heat.02` | Подождите, пока район остынет. Товар — в холодильник. | Wait till the area cools down. Goods go in the fridge. |
| `c02.heat.03` | Про ваш фургон спрашивали. Я сказал, что тут склад тапочек. | Someone asked about your van. I said this is a slipper warehouse. |

### Редкие шутки / Rare jokes

| ID | RU | EN |
| --- | --- | --- |
| `c02.joke.01` | Я не теневой. Я просто лампочку не поменял. | I'm not shady. I just never changed the light bulb. |
| `c02.joke.02` | Вывеска? Вывеска — для тех, кто платит налоги. | A sign? Signs are for people who pay taxes. |
| `c02.joke.03` | Купил кактус. Для уюта. Он уже на меня косо смотрит. | Bought a cactus. For coziness. It already looks at me funny. |

## C03 — контакт из больницы / Hospital contact

### Первый контакт / First contact

| ID | RU | EN |
| --- | --- | --- |
| `c03.first.player_call` | Алло? Мне дали ваш номер… | Hello? I was given your number… |
| `c03.first.01` | Знаю, кто дал. Не называйте имён по телефону. Вообще ничего не называйте. | I know who gave it. No names on the phone. No anything on the phone. |
| `c03.first.02` | Я работаю в больнице, а не в сказке. Мне нужно качество. Минимум {quality}. | I work at a hospital, not in a fairy tale. I need quality. {quality} minimum. |
| `c03.first.03` | Встреча: {place}. Подъезжайте и ждите в машине. Я сам подойду. | Meeting: {place}. Pull up and wait in the car. I'll come to you. |
| `c03.first.04` | В больницу не заходите. Никогда. Там очередь, и я на работе. | Never come into the hospital. Ever. There's a queue, and I'm at work. |

### Стандартные предложения / Standard offers

| ID | RU | EN |
| --- | --- | --- |
| `c03.offer.player_has_stock` | Есть хороший товар. | Got some quality goods. |
| `c03.offer.01` | {organ}, {quality}? Беру за {price}. Место: {place}. | {organ}, {quality}? {price}. Place: {place}. |
| `c03.offer.02` | Как обычно: {place}. Через десять минут. Я считаю. | Usual spot: {place}. Ten minutes. I'm counting. |
| `c03.offer.03` | Приезжайте на {place}. Если на месте будет голубь — это не я. | Come to {place}. If there's a pigeon there, it's not me. |
| `c03.offer.low_quality` | Это не {quality}. Это надежда на {quality}. Не беру. | That's not {quality}. That's hope for {quality}. Not taking it. |
| `c03.offer.low_quality_02` | Отвезите это в приёмку. Там люди проще. | Take that to the intake. They're less fussy there. |

### Согласие / Accept

| ID | RU | EN |
| --- | --- | --- |
| `c03.accept.player` | Договорились. | Deal. |
| `c03.accept.01` | Хорошо. Перчатки у меня свои. | Good. I brought my own gloves. |
| `c03.accept.02` | Принято. Оплата уже у вас. Уезжайте спокойно, не как в кино. | Received. Payment's with you. Drive off calmly, not like in the movies. |

### Отказ / Decline

| ID | RU | EN |
| --- | --- | --- |
| `c03.decline.player` | Пока нет. | Not right now. |
| `c03.decline.01` | Понимаю. Другие поймут быстрее. | I understand. Others understand faster. |
| `c03.decline.02` | Хорошо. Я записал, что вы думаете. Думайте быстрее. | Fine. I've noted that you're thinking. Think faster. |

### Торг / Haggling

| ID | RU | EN |
| --- | --- | --- |
| `c03.haggle.player` | А если чуть больше? | What about a bit more? |
| `c03.haggle.success` | {price}. Это за пунктуальность, а не за красноречие. | {price}. That's for punctuality, not eloquence. |
| `c03.haggle.fail` | Я не торгуюсь. Я сверяюсь с прайсом. | I don't haggle. I check the price list. |
| `c03.haggle.repeat` | Ещё раз — и следующая встреча будет у полицейского участка. Шучу. Наполовину. | One more time and our next meeting is outside the police station. Joking. Half joking. |

### Места встречи / Meeting points

| ID | RU | EN |
| --- | --- | --- |
| `c03.place.usual` | Как обычно: {place}. | Usual spot: {place}. |
| `c03.place.move_heat_01` | Меняем точку. У обычного места слишком много фуражек. Новое: {place}. | Changing the spot. Too many police caps at the usual one. New spot: {place}. |
| `c03.place.move_heat_02` | Старое место отменяется. Там стоит тот, кого я не хочу видеть. Едем на {place}. | Old spot's off. Someone I don't want to see is standing there. Go to {place}. |
| `c03.place.move_heat_03` | Запасной вариант: {place}. Не перепутайте. Там две скамейки, нужна скучная. | Backup spot: {place}. Don't mix it up. There are two benches, I'm at the boring one. |
| `c03.place.return` | Стало тихо. Возвращаемся на {place}. | It's quiet again. Back to {place}. |
| `c03.place.cancel` | Отменяю. На {place} подъехала патрульная машина. Позвоните позже. | Cancelled. A patrol car just pulled up at {place}. Call me later. |

### Опоздание или неявка / Late or no-show

| ID | RU | EN |
| --- | --- | --- |
| `c03.late.self_01` | Задерживаюсь. Пациент решил выздороветь не по графику. | Running late. A patient decided to get better ahead of schedule. |
| `c03.late.self_02` | Буду через пять минут. В больничных минутах это пятнадцать. | Five minutes. In hospital minutes, that's fifteen. |
| `c03.late.player_01` | Я жду. Я не люблю ждать. | I'm waiting. I don't like waiting. |
| `c03.late.player_02` | Вас не было. Я ушёл. Позвоню, когда перестану обижаться. | You didn't show. I left. I'll call when I stop being offended. |
| `c03.late.player_03` | Второй раз подряд. Я начинаю считать вас слухом. | Second time in a row. I'm starting to think you're a rumour. |

### Внимание полиции / Police heat

| ID | RU | EN |
| --- | --- | --- |
| `c03.heat.01` | В городе шумно. Это вы шумите? Не шумите. | The city's noisy. Is that you? Stop it. |
| `c03.heat.02` | Коллега говорит, спрашивали про фургон. Ваш фургон. Поскучайте пару часов. | A colleague says someone asked about a van. Your van. Be boring for a while. |
| `c03.heat.03` | Пока за вами хвост, меня нет. Даже в контактах. | While you've got a tail, I don't exist. Not even in your contacts. |

### Доверие: тон / Trust: tone

| ID | RU | EN |
| --- | --- | --- |
| `c03.trust.t0` | Принято. Свободны. | Received. You may go. |
| `c03.trust.t1` | Неплохо. Продолжайте не разочаровывать. | Not bad. Keep not disappointing me. |
| `c03.trust.t2` | Вы стали надёжны. Не привыкайте к комплиментам, это был единственный. | You've become reliable. Don't get used to compliments, that was the only one. |
| `c03.trust.t3_tone` | Это вы. Хорошо. Сегодня можно без пароля. | It's you. Good. No password today. |

### Доверие: новые предложения / Trust: new offers

| ID | RU | EN |
| --- | --- | --- |
| `c03.trust.t3_unlock` | Иногда у меня бывают особые просьбы. И особые деньги. Интересно? | Sometimes I get special requests. With special money. Interested? |

### Спецзаказы / Special orders

| ID | RU | EN |
| --- | --- | --- |
| `c03.special.header` | ЧАСТНЫЙ ЗАПРОС | PRIVATE REQUEST |
| `c03.special.card` | {organ}<br>Качество: {quality}<br>Оплата: {price}<br>Срок: {deadline}<br>Место: {place} | {organ}<br>Quality: {quality}<br>Offer: {price}<br>Deadline: {deadline}<br>Place: {place} |
| `c03.special.pitch_01` | Клиент важный. Очень нетерпеливый. Очень платёжеспособный. Нужен {organ}, {quality}. | The client is important. Very impatient. Very solvent. Needs {organ}, {quality}. |
| `c03.special.pitch_02` | Нужен {organ}. Не ниже {quality}. {price}. До {deadline}. Не продавайте такое кому попало. | Looking for: {organ}. {quality} or better. {price}. By {deadline}. Don't sell that kind of thing to just anyone. |
| `c03.special.urgent` | СРОЧНО: {organ}, {quality}. Плачу {price}. Срок — {deadline}. Время есть, но не на кофе. | URGENT: {organ}, {quality}. Paying {price}. Deadline: {deadline}. There's time, but not for coffee. |
| `c03.special.accept` | Берёмся. Ждём на {place} до {deadline}. | We're in. Meet at {place} by {deadline}. |
| `c03.special.decline` | Не возьмём. Запомню. Без обид. Почти. | Pass. Noted. No hard feelings. Mostly. |
| `c03.special.reminder` | Напоминаю про {organ}. Срок — {deadline}. Клиент уже выбрал галстук на выписку. | Reminder: {organ}. Deadline: {deadline}. The client has already picked a tie for going home. |
| `c03.special.done` | Клиент доволен. Он даже улыбнулся. Не знал, что он умеет. | The client is happy. He even smiled. Didn't know he could. |
| `c03.special.failed` | Срок вышел. Клиент нашёл другого. Не расстраивайтесь, я расстроился за нас обоих. | Deadline's passed. The client found someone else. Don't be upset, I was upset for both of us. |
| `c03.special.wrong_quality` | Просили {quality}. Это не {quality}. Клиент заметит. Клиенты всегда замечают. | I asked for {quality}. This isn't {quality}. The client will notice. Clients always notice. |
| `c03.special.final_tease` | Есть заказ, который я никому не предлагаю. Человек живёт выше всех в этом городе. Позже. | There's an order I don't offer anyone. The client lives higher up than anyone in this city. Later. |

### Редкие шутки / Rare jokes

| ID | RU | EN |
| --- | --- | --- |
| `c03.joke.01` | Не присылайте мне смайлики. Я на работе. | Don't send me emojis. I'm at work. |
| `c03.joke.02` | Почерк у меня ужасный. Зато цены хорошие. | My handwriting is terrible. My prices aren't. |
| `c03.joke.03` | Сегодня мне сказали «спасибо, доктор». Я не доктор. Но приятно. | Someone said "thank you, doctor" today. I'm not a doctor. Still nice. |

## Дед (жив) / Grandpa (alive)

### Приветствие / Greeting

| ID | RU | EN |
| --- | --- | --- |
| `gp.greet.01` | А, молодёжь. Вы насчёт бусика? Мне сказали, что придёте. Кто сказал — не помню. | Ah, young people. About the van? I was told you'd come. By whom, I forget. |
| `gp.greet.02` | Он не красавец. Я тоже. Но мы оба ещё заводимся. Иногда. | He's no beauty. Neither am I. But we both still start up. Sometimes. |

### Продажа бусика / Selling the van

| ID | RU | EN |
| --- | --- | --- |
| `gp.sale.01` | Мне много не надо. Хватит на нормальные похороны — и ладно. | I don't need much. Enough for a proper funeral, that's all. |
| `gp.sale.02` | Хочу, чтобы был оркестр. Но короткий. Люди же торопятся. | I want a brass band. A short one. People are busy. |
| `gp.sale.price` | Дайте {price} — и он ваш. С ключами и с характером. | Give me {price} and he's yours. Keys and attitude included. |
| `gp.sale.paid` | Вот и славно. Теперь у меня есть деньги, а у вас — проблемы с ремонтом. | Lovely. Now I have money and you have a repair job. |

### Подсказки ремонта / Repair hints

| ID | RU | EN |
| --- | --- | --- |
| `gp.repair.01` | Я бы сам починил, но спина у меня бастует с восемьдесят шестого. | I'd fix it myself, but my back has been on strike since eighty-six. |
| `gp.repair.battery` | Аккумулятор в сарае, на полке. Новый. Берёг для кого-то. Видимо, для вас. | Battery's in the shed, on the shelf. Brand new. Was saving it for someone. Turns out, you. |
| `gp.repair.tyres` | Насос у крыльца. Качайте шины, пока не станут круглыми. Круглые — это правильно. | Pump's by the porch. Pump the tyres till they're round. Round is correct. |
| `gp.repair.order` | Сначала аккумулятор, потом колёса. Можно наоборот, но я буду ворчать. | Battery first, then tyres. You can do it the other way, but I'll grumble. |
| `gp.repair.stall` | Глохнет? Это он с вами знакомится. | It stalls? That's him getting to know you. |
| `gp.repair.done` | Заводится! Берегите его. Он помнит больше, чем я. | It starts! Take care of him. He remembers more than I do. |

### Прощание / Farewell

| ID | RU | EN |
| --- | --- | --- |
| `gp.farewell.01` | Езжайте. И не гоняйте. Он старенький, а я ещё не всё оркестру объяснил. | Off you go. Don't speed. He's old, and I haven't finished briefing the band. |

### Приглашение на похороны (идея, не утверждено) / Funeral invite (idea, not approved)

| ID | RU | EN |
| --- | --- | --- |
| `gp.funeral_invite.01` | Приходите потом на похороны. Не сейчас. Я ещё сообщу. Если успею — лично. | Come to my funeral later. Not now. I'll let you know. In person, if I can manage. |
| `gp.funeral_invite.phone` | Это дед. Внучка соседа научила меня писать сообщения. Приглашение в силе. Оркестр короткий, как договаривались. | It's Grandpa. The neighbour's granddaughter taught me texting. The invitation stands. Short band, as agreed. |

## Дед мёртв: записки во дворе / Grandpa dead: notes in the yard

### Подсказки ремонта без деда / Repair hints without Grandpa

| ID | RU | EN |
| --- | --- | --- |
| `gpd.note.shed` | Записка на сарае: «Памятка себе. 1. Аккумулятор — на полке. 2. Шины — насос у крыльца. 3. Не забыть, что пункт 1 был первым». | Note on the shed: "Reminder to self. 1. Battery: shelf. 2. Tyres: pump by the porch. 3. Remember that step 1 comes first." |
| `gpd.note.dashboard` | Записка на приборной панели: «Не заводится — аккумулятор. Заводится — не трогай». | Note on the dashboard: "Won't start: battery. Starts: don't touch anything." |
| `gpd.note.pump` | Бирка на насосе: «Качать, пока колесо не станет круглым. Круглое — это правильно». | Tag on the pump: "Pump until the wheel is round. Round is correct." |
| `gpd.note.funeral_jar` | Банка с надписью «НА ОРКЕСТР». Пустая. | A jar labelled "FOR THE BAND". Empty. |

## Системные подсказки / System hints

### Подсказки ремонта без деда / Repair hints without Grandpa

| ID | RU | EN |
| --- | --- | --- |
| `gpd.hint.ui` | Подсказка: всё для ремонта есть во дворе. | Hint: everything you need for the repair is in the yard. |

## Достижения: мирная ветка деда / Achievements: peaceful grandpa ending

### Мирная ветка / Peaceful ending

| ID | RU | EN |
| --- | --- | --- |
| `ach.gp_paid.name` | Деньги на оркестр | Money for the Band |
| `ach.gp_paid.desc` | Купить бусик у деда честно. | Buy the van from Grandpa fair and square. |
| `ach.gp_alive.name` | Продавец всё ещё дышит | Seller Still Breathing |
| `ach.gp_alive.desc` | Получить первый бусик, оставив деда в живых. | Get your first van and leave Grandpa alive. |
| `ach.gp_repair.name` | Круглое — это правильно | Round Is Correct |
| `ach.gp_repair.desc` | Починить бусик под руководством деда. | Fix the van while Grandpa supervises. |
| `ach.gp_grandkids.name` | Внуков не было, были вы | No Grandkids, Just You |
| `ach.gp_grandkids.desc` | Выслушать все советы деда до конца. | Listen to all of Grandpa's advice to the end. |
| `ach.gp_funeral.name` | Приглашение заранее | RSVP: Funeral |
| `ach.gp_funeral.desc` | Получить от деда приглашение на его похороны. | Get invited to Grandpa's funeral by Grandpa. |

---

Всего строк / Total lines: 310.


## Дополнение G28 — v02 / G28 extension — v02

C02 используется как редакционный слот первого скупщика; окончательное соответствие канонному C02 остаётся открытым в v02. Новые строки задают мобильную встречу по v02 и заменяют старые реплики о приёмке. Отправитель позднего заказа `special.old_streamer.*` — `UNASSIGNED`: v02 не назначает его C03. / C02 is the draft slot for the first fence; final canon mapping remains open. New v02 mobile-meeting lines supersede legacy premises dialogue. The later streamer order has no assigned buyer yet.

Первый заказ — только `HAMLET_BODYBUILDER`, Хутор, от третьего уровня респекта. Стример — поздний заказ, после доступа в Даунтаун и получения пилы. Оба используют общий торг +5/+10/+20 при принятии, затем условия фиксируются. `special.shared.haggle_breakdown` заменяет обычный срыв продажи для предложения заказа. Первый отказ на +5% даёт только исходную цену или выход; на второй попытке показывается лишь меньшая надбавка. Точную встречную цену подставляет игра: формула в v02 открыта. / First order: Hamlet bodybuilder, respect level 3+. Streamer: later, with Downtown access and a saw. Both use the shared +5/+10/+20 acceptance negotiation, then lock their terms. The special breakdown line applies to an order offer. After a +5% refusal, only the original offer or leaving is available; retry choices must be lower than the first ask. Counteroffer calculation remains open in v02.

`respect.up_1` и `respect.down_5` — запасные локализационные строки для полного набора пяти уровней. На обычном переходе вверх в уровень 1 и вниз в уровень 5 они не вызываются. Падение ниже уровня 3 не отменяет уже принятый заказ. / `respect.up_1` and `respect.down_5` are completeness fallbacks, not ordinary transition triggers. Falling below level 3 does not cancel an accepted order.

`late` — просрочка, а не провал: −4 респекта один раз, без +25%, согласованный торг сохраняется, слот занят. `failed` — закрытие без сдачи; системная строка отмены выбирается по сроку (−2 до срока, без нового штрафа после). Выполнение вовремя даёт +5 респекта и +150 XP сверх продажи; новый контакт выдаётся только после первого своевременного спецзаказа. / Late is not failed: one −4 respect penalty, no +25%, agreed haggling retained, slot occupied. Failed means closed without delivery; cancellation uses the appropriate before/after-deadline system line. On-time completion awards +5 respect and +150 XP on top of the sale; the next contact unlocks only on the first on-time special-order completion.

Часы и конкретное место стримера не заданы источником: `{appearance_hours}`, `{clue_place}` заполняются только после утверждения. Фото, тайники и области поиска — ссылки/локализованные данные, не выдуманные адреса. / Streamer hours and exact location are unspecified; fill them only after approval. Photos, stashes and search areas reference authored data.

Дополнительные плейсхолдеры / Additional placeholders: `{arrival_time}` — прибытие / arrival; `{wait_until}` — конец ожидания / wait end; `{time_left}` — оставшееся игровое время / remaining game time; `{markup}` — согласованный процент без знака % / agreed percentage without %; `{reason}` — локализованный результат проверки / localised check result; `{xp_bonus}` — бонус новинки одному участнику, без обычных 20 XP / first-sale bonus per player excluding the usual 20 XP; `{photo}` — фото цели / target photo; `{search_area}` — область поиска / search area; `{stash}` — тайник / stash; `{clue_place}` — место появления / location; `{appearance_hours}` — часы появления / appearance hours. `{price}` всегда включает валюту / always includes currency. `catalog.new.card` относится к органам: почка/печень/глаз +100, лёгкие +150, сердце +200, мозг +250 XP каждому присутствующему; кровь использует отдельный бонус +50 сверх 5 XP. / The organ catalogue card uses kidney/liver/eye +100, lungs +150, heart +200, brain +250 XP per player in the session; blood has its separate +50 bonus on top of 5 XP.

### C01 — кровь и база / Blood and base

| ID | RU | EN |
| --- | --- | --- |
| `c01.syringe.offer` | Один шприц крови возьму за $10. Один раз, без торга. Дальше — пакеты. | I’ll take one syringe of blood for $10. Once, no haggling. Blood bags after that. |
| `c01.syringe.player_accept` | За $10 договорились. | Deal. $10. |
| `c01.syringe.player_decline` | Пока оставим себе. | We’ll keep it for now. |
| `c01.syringe.handover` | Давай шприц в руки. Багажник тут ни при чём. | Hand me the syringe. No need for the boot. |
| `c01.syringe.paid` | Шприц забрал. $10 ваши. Пробный период окончен. | Got the syringe. Your $10. Free trial’s over. |
| `c01.syringe.already_used` | Шприц я уже покупал. Акция была разовая. Теперь только пакеты. | Already bought a syringe from you. One-time offer. Blood bags now. |
| `c01.base.confirm` | Подъеду к вашей базе через час. Время прибытия — {arrival_time}. | I’ll be at your base in an hour. Arrival: {arrival_time}. |
| `c01.base.arrived_01` | Я у базы. Жду три часа, до {wait_until}. Выходите с товаром. | At your base. I’ll wait three hours, until {wait_until}. Bring the goods out. |
| `c01.base.arrived_02` | Подъехал к базе. До {wait_until} я ваш. Потом я занят собой. | At the base. Yours until {wait_until}. Then I’ve got plans with myself. |
| `c01.base.waiting` | Я ещё у базы. Осталось {time_left}. Кровь сама до меня не дойдёт. | Still at the base. {time_left} left. The blood won’t walk over here. |
| `c01.base.handover_01` | Передавайте пакеты прямо мне в руки. По одному, я не жонглёр. | Hand the bags straight to me. One at a time. I don’t juggle. |
| `c01.base.handover_02` | Пакеты сюда. Руки у меня заняты только бизнесом. | Bags over here. My hands are free for business. |
| `c01.contact.first_sale` | Первая кровь продана. Скидываю номер скупщика органов. Кровь по-прежнему мне. | First blood sale done. Sending you an organ buyer’s number. Blood still comes to me. |

### Первый скупщик / First fence

| ID | RU | EN |
| --- | --- | --- |
| `c02.call.player_stock` | Есть органы. Назначим встречу? | Got organs. Shall we meet? |
| `c02.call.player_terms` | Что берёшь и как встречаемся? | What do you buy? How do we meet? |
| `c02.call.player_later` | Позже наберём. | We’ll call back later. |
| `c02.call.terms` | Беру все виды органов, даже «Убитое». Кровь — C01. Звонить можно круглосуточно. | I buy every organ type, even Damaged. Blood goes to C01. Call any time, day or night. |
| `c02.call.player_book` | Назначай. Будем с товаром. | Set it up. We’ll bring the goods. |
| `c02.call.meeting_point_01` | Встречаемся: {place}. Буду через час, в {arrival_time}. Точка закреплена. | Meet at {place}. I’ll be there in an hour, at {arrival_time}. That’s our spot for this meeting. |
| `c02.call.meeting_point_02` | Сегодня — {place}. Приеду в {arrival_time}, через час. Багажник узнаете. | Today’s spot: {place}. Arrival: {arrival_time}, one hour from now. You’ll know the boot when you see it. |
| `c02.call.player_confirm` | Принято. Едем к {place}. | Got it. Heading to {place}. |
| `c02.call.player_cancel` | Отменяем встречу. | Cancel the meeting. |
| `c02.call.cancel_before_arrival` | Ещё не приехал, так что без обид. Новую встречу назначим, когда будете готовы. | I’m not there yet, so no hard feelings. Call when you’re ready to book again. |
| `c02.call.already_booked` | Уже договорились: {place}, {arrival_time}. Второй я туда не приедет. | Already booked: {place}, {arrival_time}. There isn’t a second me to send. |
| `c02.meeting.arrived_01` | Я на {place}. Жду три часа, до {wait_until}. Товар — в багажник. | At {place}. Waiting three hours, until {wait_until}. Goods go in the boot. |
| `c02.meeting.arrived_02` | На месте: {place}. До {wait_until} принимаю. Потом багажник закрывается вместе со мной. | Here at {place}. Open until {wait_until}. Then both the boot and I close for business. |
| `c02.meeting.waiting_01` | Осталось {time_left}. Я тут уже все трещины в асфальте выучил. | {time_left} left. I’ve memorised every crack in the tarmac. |
| `c02.meeting.waiting_02` | Ещё {time_left} жду на {place}. Парковка хорошая. Компания пока так себе. | Waiting another {time_left} at {place}. Nice parking spot. Company could be better. |
| `c02.meeting.time_over` | Время вышло. Уезжаю. Респекта поубавилось, но звонить можно сразу. | Time’s up. I’m off. Lost a little respect for you. You can call to book again now. |
| `c02.meeting.finish_group` | Этот вид закончим — начали вовремя. Следующий уже на новой встрече. | We’ll finish this organ type; we started in time. Next type needs another meeting. |
| `c02.case.open_01` | Открываю кейс. Посмотрим, что у вас за комплектация. | Opening the case. Let’s see what’s in this model. |
| `c02.case.open_02` | Так, крышку сюда. Я люблю, когда товар видно. | Lid over here. I like to see what I’m buying. |
| `c02.case.inspect_01` | Сейчас осмотрю. Гарантийный талон не ищите. | Let me inspect it. Don’t bother looking for the warranty. |
| `c02.case.inspect_02` | Вижу. Проверю состояние и назову цену. | Right. I’ll check the condition and give you a price. |
| `c02.trade.quote` | За эту группу {organ} сейчас {price}. Перед продажей сверим сумму ещё раз. | Current offer for this batch of {organ}: {price}. We’ll check the total again before the sale. |
| `c02.haggle.ask_5` | Накинь 5%. На бензин. | Add 5%. Petrol money. |
| `c02.haggle.ask_10` | Давай на 10% больше. Мы довезли. | Make it 10% more. We got it here. |
| `c02.haggle.ask_20` | Плюс 20% — и по рукам. | Add 20% and we’ve got a deal. |
| `c02.haggle.player_accept` | Согласны на {price}. | We’ll take {price}. |
| `c02.haggle.player_refuse` | Не продаём. Забираем товар. | No sale. We’re taking it back. |
| `c02.haggle.accept_01` | Ладно, надбавка {markup}%. Убедили. Не привыкайте. | Fine. {markup}% extra. You convinced me. Don’t get used to it. |
| `c02.haggle.accept_02` | Согласен на {markup}% сверху. Считайте, у меня сегодня доброе лицо. | Agreed. {markup}% extra. Must be my friendly face today. |
| `c02.haggle.refuse_first_01` | Такую надбавку не дам. Можете взять встречную цену или попросить меньше. | Not adding that much. Take my counteroffer or ask for a smaller increase. |
| `c02.haggle.refuse_first_02` | Размах хороший. Цена — нет. Берите встречную или снижайте запрос. | Nice ambition. Wrong price. Take my counteroffer or lower your ask. |
| `c02.haggle.counter` | Моя встречная — {price}. Согласны? | My counteroffer: {price}. Deal? |
| `c02.haggle.refuse_five` | Даже 5% не добавлю. Исходные {price} — или забирайте товар. | Not even 5% extra. Original offer: {price}. Take it or take the goods back. |
| `c02.haggle.retry_five` | Тогда просим только +5%. | Then we’re asking for just +5%. |
| `c02.haggle.retry_ten` | Тогда просим только +10%. | Then we’re asking for just +10%. |
| `c02.haggle.second_refusal_01` | Второй раз — нет. Этот вид три часа не беру. Остальное показывайте. | Second no. I won’t buy this organ type for three hours. Show me the rest. |
| `c02.haggle.second_refusal_02` | Не сошлись. Этот вид забирайте, вернёмся к нему через три часа. | No deal. Take this organ type back. We can try again in three hours. |
| `c02.haggle.breakdown_card` | Сделка сорвана. Респект −1. Товар остаётся у команды. Этот вид органов недоступен для продажи покупателю 3 игровых часа. | Deal fell through. Respect −1. The team keeps the goods. This buyer won’t buy this organ type for 3 game hours. |
| `c02.haggle.player_walkaway` | Забирайте. До холодильника лучше без экскурсии. | Take it back. Best skip the scenic route to the cooler. |
| `c02.trade.confirm` | Итого сейчас: {price}. Подтверждаете продажу? | Current total: {price}. Confirm the sale? |
| `c02.trade.paid_01` | Товар мой, {price} ваши. Удобная система. | Goods for me, {price} for you. Handy system. |
| `c02.trade.paid_02` | Принято. {price} в общий фонд. Можете считать, я не тороплю. | Accepted. {price} into the team fund. Count it if you like. Take your time. |
| `c02.trade.unsuitable_01` | Это я не принимаю. Забирайте. Мы же про органы договаривались. | I don’t buy this. Take it back. We agreed on organs. |
| `c02.trade.unsuitable_02` | Товар не подходит. Остаётся у вас. И давайте без сюрпризов. | Wrong item. You keep it. Let’s stick to what we agreed. |
| `c02.trade.unsuitable_card` | Продажи нет: {reason}. Товар остаётся у команды. Респект −1 за подтверждённую попытку; повторная проверка того же экземпляра на этой встрече без нового штрафа. | No sale: {reason}. The team keeps the item. Respect −1 for the confirmed attempt; checking the same item again at this meeting adds no penalty. |
| `c02.quality.damaged_01` | Убитое. Видало жизнь. Возьму по состоянию. | Damaged. Seen better days. I’ll pay for what’s left. |
| `c02.quality.acceptable_01` | Сойдёт. Без восторга, но в дело пойдёт. | Acceptable. No applause, but it’ll do. |
| `c02.quality.good_01` | Хорошее. Вот это уже товар. | Good. Now that’s stock. |
| `c02.quality.perfect_01` | Отличное. Приятно открыть кейс. | Perfect. A pleasure to open the case. |
| `c02.quality.perfect_plus_01` | Идеальное. Хоть на витрину. Если бы у меня была витрина. | Perfect+. Display-window material. If I had a display window. |
| `c02.quality.damaged_02` | Убитое. Не музейный экспонат. Но куплю. | Damaged. No collector’s piece. Still buying. |
| `c02.quality.acceptable_02` | Сойдёт. Скромно. По цене тоже. | Acceptable. Modest. So’s the price. |
| `c02.quality.good_02` | Хорошее. Можно работать. | Good. We can work with that. |
| `c02.quality.perfect_02` | Отличное. Умеете, когда хотите. | Perfect. You can do it when you try. |
| `c02.quality.perfect_plus_02` | Идеальное. Крышку открывал зря. И так любовался бы. | Perfect+. Almost a shame to close the lid. |
| `c02.cooler.missing_01` | Без мини-холодильника? Минус 10% к оплате. Багажник у вас не зима. | No mini-cooler? Payment’s 10% lower. Your boot isn’t winter. |
| `c02.cooler.missing_02` | На охлаждении сэкономили. На оплате тоже сэкономим: минус 10%. | Saved on cooling? We’ll save on payment too. Minus 10%. |
| `c02.cooler.inspection_ok` | Для осмотра достали — нормально. Довезли в холоде, штрафа нет. | Taking it out for inspection is fine. Delivered chilled, so no penalty. |
| `c02.respect.level_1` | ууу хиляк | weakling |
| `c02.respect.up_1` | Респект вырос. Теперь вы — «ууу хиляк». Продажами поправите дело. | Respect up. You’re now “weakling”. A few sales will help. |
| `c02.respect.down_1` | Респект упал до «ууу хиляк». Торговать можно. Уважение вернём делом. | Respect down to “weakling”. We can still trade. Earn the respect back with sales. |
| `c02.respect.level_2` | новобранец | rookie |
| `c02.respect.up_2` | Респект вырос. Теперь вы — «новобранец». Уже узнаю номер. | Respect up. You’re now “rookie”. I recognise the number now. |
| `c02.respect.down_2` | Респект упал до «новобранец». Номер сохраню. Доверие придётся вернуть. | Respect down to “rookie”. Keeping your number. You’ll have to earn the trust back. |
| `c02.respect.level_3` | бывалый | old hand |
| `c02.respect.up_3` | Респект вырос. Теперь вы — «бывалый». Можно обсуждать спецзаказы. | Respect up. You’re now “old hand”. We can talk special orders. |
| `c02.respect.down_3` | Респект упал до «бывалый». Номер сохраню. Доверие придётся вернуть. | Respect down to “old hand”. Keeping your number. You’ll have to earn the trust back. |
| `c02.respect.level_4` | проверенный | trusted |
| `c02.respect.up_4` | Респект вырос. Теперь вы — «проверенный». С вами можно планировать. | Respect up. You’re now “trusted”. I can make plans with you. |
| `c02.respect.down_4` | Респект упал до «проверенный». Номер сохраню. Доверие придётся вернуть. | Respect down to “trusted”. Keeping your number. You’ll have to earn the trust back. |
| `c02.respect.level_5` | своячок | one of us |
| `c02.respect.up_5` | Респект вырос. Теперь вы — «своячок». Своих узнаю без подписи. | Respect up. You’re now “one of us”. I know my people without caller ID. |
| `c02.respect.down_5` | Респект упал до «своячок». Номер сохраню. Доверие придётся вернуть. | Respect down to “one of us”. Keeping your number. You’ll have to earn the trust back. |

### Каталог / Catalogue

| ID | RU | EN |
| --- | --- | --- |
| `catalog.new.header` | Новинка в каталоге | New in the catalogue |
| `catalog.new.card` | Новинка в каталоге: {organ}, +{xp_bonus} XP<br>Бонус первой продажи каждому участнику сессии. Обычные 20 XP за орган начислены отдельно. | New in the catalogue: {organ}, +{xp_bonus} XP<br>First-sale bonus for each player in the session. The usual 20 XP for the organ are awarded separately. |

### Первый спецзаказ / First special order

| ID | RU | EN |
| --- | --- | --- |
| `c02.special.hamlet_bodybuilder.pitch` | Нужна почка колхозного качка из Хутора. Клиент говорит: «На парном молоке, натуральная». Плачу на 25% больше. | Need the Hamlet bodybuilder’s kidney. Client says it’s “farm-fresh, all natural”. Paying 25% extra. |
| `c02.special.hamlet_bodybuilder.clue_card` | Почка колхозного качка<br>Цель: HAMLET_BODYBUILDER<br>Фото: {photo}<br>Наводка: по утрам 06:00–10:00 качается на турнике на площади Хутора.<br>Область поиска: {search_area}. Точного маркера над целью нет.<br>Нужна почка именно этого NPC. При сдаче: не ниже «Хорошее» (60%), обязательная упаковка.<br>Оплата: {price}, с надбавкой заказа +25% и согласованным торгом. После принятия — 48 игровых часов. Сдача через тайник: {stash}. | Hamlet bodybuilder’s kidney<br>Target: HAMLET_BODYBUILDER<br>Photo: {photo}<br>Clue: works out on the pull-up bar in Hamlet square in the mornings, 06:00–10:00.<br>Search area: {search_area}. No exact marker above the target.<br>Must be this NPC’s kidney. On delivery: Good (60%) or better, required packaging.<br>Payment: {price}, including the +25% order bonus and agreed haggle bonus. 48 game hours after acceptance. Deliver through the stash: {stash}. |
| `c02.special.hamlet_bodybuilder.player_accept` | Условия согласованы. Берём заказ на 48 игровых часов. | Terms agreed. We accept the order with a 48-game-hour deadline. |
| `c02.special.hamlet_bodybuilder.accepted` | Принято. Срок — {deadline}. Тайник — {stash}. Теперь часы пошли. | Accepted. Deadline: {deadline}. Stash: {stash}. Clock starts now. |
| `c02.special.hamlet_bodybuilder.player_decline` | Пока пропустим. Заказ не принимаем. | We’ll pass for now. Not accepting the order. |
| `c02.special.hamlet_bodybuilder.reminder_01` | Как там натуральная почка? Качок утром на турнике: 06:00–10:00, площадь Хутора. Срок — {deadline}. | How’s the all-natural kidney? Bodybuilder’s on the pull-up bar, 06:00–10:00, Hamlet square. Deadline: {deadline}. |
| `c02.special.hamlet_bodybuilder.reminder_02` | До срока {time_left}. Нужны «Хорошее» или выше и упаковка. Тайник — {stash}. | {time_left} until the deadline. Good or better, packaged. Stash: {stash}. |
| `c02.special.hamlet_bodybuilder.done` | Почка принята вовремя. {price} в общий фонд. Клиент доволен сельским хозяйством. Скидываю следующий контакт. | Kidney delivered on time. {price} into the team fund. Client’s pleased with local farming. Sending the next contact. |
| `c02.special.hamlet_bodybuilder.late` | Срок вышел. Надбавки заказа +25% больше нет, выторгованный процент остаётся. Штраф респекта уже учтён. Сдать ещё можно; слот занят до сдачи или отказа. | Deadline passed. The +25% order bonus is gone; your agreed haggle bonus stays. Respect penalty applied. You can still deliver; the slot stays occupied until delivery or cancellation. |
| `c02.special.hamlet_bodybuilder.failed` | Заказ закрыт без сдачи. Почку больше не жду. Слот свободен. | Order closed without delivery. No longer waiting for the kidney. Order slot’s free. |
| `c02.special.hamlet_bodybuilder.wrong_target` | Почка есть. Качок не тот. Нужен именно HAMLET_BODYBUILDER из Хутора. | It’s a kidney. Wrong bodybuilder. Must be HAMLET_BODYBUILDER from Hamlet. |
| `c02.special.hamlet_bodybuilder.wrong_quality` | Нужно не ниже «Хорошее» (60%) при сдаче. Эту почку по заказу не приму. | Needs to be Good (60%) or better on delivery. Can’t take this kidney for the order. |
| `c02.special.hamlet_bodybuilder.missing_packaging` | Качок тот. Упаковки нет. Без неё заказ не приму. | Right bodybuilder. No packaging. Can’t accept the order without it. |

### Поздний заказ Даунтауна / Later Downtown order

| ID | RU | EN |
| --- | --- | --- |
| `special.old_streamer.pitch` | Поздний заказ из Даунтауна: мозг IRL-стримера с разноцветными волосами. Клиент хочет мысли без рекламы. Надбавка +25%. | Later Downtown order: the rainbow-haired IRL streamer’s brain. Client wants thoughts without ads. Pays 25% extra. |
| `special.old_streamer.clue_card` | Мозг IRL-стримера<br>Цель: OLD_STREAMER, разноцветные волосы. Район: Даунтаун.<br>Фото: {photo}<br>Место: {clue_place}. Часы появления: {appearance_hours}. Область поиска: {search_area}. Точного маркера над целью нет.<br>Нужен мозг именно этого NPC. При сдаче: не ниже «Отличное» (80%), обязательная упаковка.<br>Доступ: Даунтаун и пила для зоны головы.<br>Оплата: {price}, с надбавкой заказа +25% и согласованным торгом. После принятия — 48 игровых часов. Сдача через тайник: {stash}. | IRL streamer’s brain<br>Target: OLD_STREAMER, rainbow hair. District: Downtown.<br>Photo: {photo}<br>Location: {clue_place}. Appearance hours: {appearance_hours}. Search area: {search_area}. No exact marker above the target.<br>Must be this NPC’s brain. On delivery: Perfect (80%) or better, required packaging.<br>Requires Downtown access and the saw for the head zone.<br>Payment: {price}, including the +25% order bonus and agreed haggle bonus. 48 game hours after acceptance. Deliver through the stash: {stash}. |
| `special.old_streamer.player_accept` | Условия согласованы. Берём заказ на 48 игровых часов. | Terms agreed. We accept the order with a 48-game-hour deadline. |
| `special.old_streamer.accepted` | Заказ принят. Срок — {deadline}. Тайник — {stash}. Пошёл отсчёт, без заставки. | Order accepted. Deadline: {deadline}. Stash: {stash}. Countdown starts now. No intro. |
| `special.old_streamer.player_decline` | Этот заказ пока пропустим. | We’ll pass on this order for now. |
| `special.old_streamer.reminder_01` | Напомню: OLD_STREAMER, разноцветные волосы, Даунтаун. Смотрите фото и область поиска. Срок — {deadline}. | Reminder: OLD_STREAMER, rainbow hair, Downtown. Check the photo and search area. Deadline: {deadline}. |
| `special.old_streamer.reminder_02` | Осталось {time_left}. Мозг — «Отличное» или выше, в упаковке. Тайник — {stash}. Чат ждать не будет. | {time_left} left. Brain: Perfect or better, packaged. Stash: {stash}. Chat won’t wait. |
| `special.old_streamer.done` | Мозг принят вовремя. {price} в общий фонд. Клиент просил без подписки. Всё получилось. | Brain delivered on time. {price} into the team fund. Client wanted no subscription. Delivered. |
| `special.old_streamer.late` | Срок вышел. +25% за заказ снимаются, согласованный торг сохраняется. Штраф респекта уже учтён. Сдача ещё доступна; слот занят до сдачи или отказа. | Deadline passed. The +25% order bonus is removed; the agreed haggle bonus stays. Respect penalty applied. Delivery remains available; the slot stays occupied until delivery or cancellation. |
| `special.old_streamer.failed` | Заказ закрыт без сдачи. Эфир окончен. Слот свободен. | Order closed without delivery. Stream’s over. Order slot’s free. |
| `special.old_streamer.wrong_target` | Другой мозг не подойдёт. Нужен OLD_STREAMER из Даунтауна, тот, что с разноцветными волосами. | Another brain won’t do. Need OLD_STREAMER from Downtown. The one with rainbow hair. |
| `special.old_streamer.wrong_quality` | Для этого заказа нужно не ниже «Отличное» (80%) при сдаче. Пока не подходит. | This order needs Perfect (80%) or better on delivery. This doesn’t qualify. |
| `special.old_streamer.missing_packaging` | Мозг нужный, упаковки нет. Заказ пока не приму. | Right brain, no packaging. Can’t accept the order yet. |

### Общие строки спецзаказов / Shared special-order lines

| ID | RU | EN |
| --- | --- | --- |
| `special.shared.cancel_before_deadline` | Заказ отменён до срока. Респект −2. Слот свободен. | Order cancelled before the deadline. Respect −2. Order slot’s free. |
| `special.shared.cancel_after_deadline` | Просроченный заказ отменён. Дополнительного штрафа нет. Слот свободен. | Overdue order cancelled. No additional penalty. Order slot’s free. |
| `special.shared.haggle_breakdown` | Второй отказ. Респект −1. Предложение недоступно 3 игровых часа. Заказ не принят, отсчёт 48 часов не начат. | Second refusal. Respect −1. Offer unavailable for 3 game hours. Order not accepted; the 48-hour clock hasn’t started. |
| `special.shared.handover_card` | Положите товар в тайник {stash} и подтвердите сдачу отдельно. До подтверждения можно забрать товар. Причина несоответствия: {reason}. | Put the item in stash {stash}, then confirm delivery separately. You can retrieve it before confirmation. Requirement check: {reason}. |
| `special.shared.unsuitable_card` | Неподходящий товар остаётся у команды. Подтверждённая попытка: респект −1 один раз за экземпляр в этом заказе. Повторное нажатие не добавляет штраф. | The team keeps unsuitable goods. Confirmed attempt: respect −1 once per item for this order. Repeated confirmation adds no penalty. |
