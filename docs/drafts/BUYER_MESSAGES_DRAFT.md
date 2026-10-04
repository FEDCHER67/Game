# Тексты телефона покупателей — черновик / Buyer phone messages — draft

**Статус / Status:** черновик, не утверждён Федей и Вадимом. Ничего из этого файла не является требованием геймплея. / Draft, not approved. Nothing here is a gameplay requirement.

**Источники / Sources:** `docs/CITY_MAP_REFERENCE_SPEC.md` §6 (пролог, дед), §7 (сюжетная лестница), §8 (C01–C03, встречи, скрытое доверие), §13 (P01, P09), §20 (C-P02); `docs/VOLUNTEERS_ONLY_GAME_SPEC_AND_LORE_CURRENT_CANON.md` §50–56 (чёрный рынок, перекупщик, спецзаказы, цены, передача товара), §72 (heat).

**Машиночитаемая версия / Machine-readable:** `docs/drafts/buyer_messages.json` — поля `id`, `buyer`, `situation`, `ru`, `en`, `placeholders`. Этот MD сгенерирован из тех же данных; при правках менять обе версии согласованно.

## Правила текста / Writing rules

- Тон: мультяшная чёрная комедия, короткие реплики в стиле переписки. Без крови на экране, без описаний тел и реальных медицинских процедур. Органы — только `{organ}` и игровые предметы.
- Покупатели получают только кровь (C01) или органы по своей специализации (C02, C03). Живых NPC и тела не принимают — C02 говорит это прямо (`c02.first.03`).
- Доверие скрыто: нет шкалы и чисел. Оно видно только через тон (`trust_tone`, уровни t0→t3) и новые предложения (`trust_new_offer`, `intro_next_buyer`). Пороги — баланс, не задаются здесь.
- Heat без цифр: покупатели реагируют на «мигалки», «шум», «вопросы про фургон».
- Язык по умолчанию — английский; русский — полный параллельный перевод.

## Плейсхолдеры / Placeholders

| Плейсхолдер | Значение |
| --- | --- |
| `{organ}` | Название органа как игрового предмета (локализуется отдельно). |
| `{quality}` | Состояние: Normal / Good / Perfect / Perfect+ (шкала канона ещё не финальная). |
| `{price}` | Сумма с валютой, форматирует игра. |
| `{deadline}` | Срок в игровом формате («до утра», «2 игровых дня»). Канон §55: срок не должен душить. |
| `{place}` | Название места встречи C03 (P09: основное или запасное) или иного места сделки. |

Других плейсхолдеров нет. Строка `c03.special.card` содержит переносы строк (`\n`) — это карточка «PRIVATE REQUEST» из канона §53.

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
| `c01.first.syringes_02` | Ладно. Один раз заплачу. Из уважения к вашему энтузиазму. | Fine. I'll pay once. Out of respect for your enthusiasm. |
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
| `c01.offer.01` | Беру. Даю {price}. Буду через пару минут. | I'll take them. {price}. Be there in a couple of minutes. |
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
| `c01.intro_c02.01` | О, у вас колёса! Теперь вы серьёзные люди. Почти. | Oh, you've got wheels! You're serious people now. Almost. |
| `c01.intro_c02.02` | Есть знакомые, которые берут не только кровь. Здание между деревней и спальником. | I know people who take more than blood. A building between the village and the bedroom district. |
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
| `c02.first.01` | Вы от этого, с пакетами? Заходите. Обувь не снимайте. | You're from the bag guy? Come in. Keep your shoes on. |
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
| `c02.offer.01` | Приезжайте. Дверь сбоку. Звонок не работает, стучите три раза. | Come over. Side door. The bell's broken, knock three times. |
| `c02.offer.02` | За {organ} ({quality}) дам {price}. | For the {organ} ({quality}), I'll give {price}. |
| `c02.offer.03` | {organ}? Беру. {price}. Кладите на стол. Нет, не на этот. На чистый. | {organ}? I'll take it. {price}. Put it on the table. No, not that one. The clean one. |
| `c02.offer.low_quality` | Это {quality}? Видел я такое в банке с огурцами. Могу дать {price}. Из жалости. | That's {quality}? I've seen better in a pickle jar. I can do {price}. Out of pity. |
| `c02.offer.not_my_line` | Кровь? Это к вашему другу с пакетами. Я сентиментальный, но не настолько. | Blood? Take that to your bag friend. I'm sentimental, but not that much. |

### Согласие / Accept

| ID | RU | EN |
| --- | --- | --- |
| `c02.accept.player` | Идёт. | Deal. |
| `c02.accept.01` | Деньги в конверте. Конверт не возвращать, он у меня последний. | Money's in the envelope. Keep the envelope, I'm out anyway. |
| `c02.accept.02` | Хорошая работа. Дверь закрывайте мягко, она нервная. | Good work. Close the door gently, it's nervous. |

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
| `c02.haggle.repeat` | Ещё раз спросите — цена начнёт падать. Проверим? | Ask again and the price starts going down. Want to test it? |

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
| `c02.late.player_02` | Я закрываюсь на обед. Обед у меня длинный. Приезжайте позже. | I'm closing for lunch. My lunches are long. Come back later. |
| `c02.late.order_expired` | Заказ на {organ} сгорел. Ничего. Будет другой. Я не злопамятный. Почти. | The {organ} order has expired. That's fine. There'll be another. I don't hold grudges. Mostly. |

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

Всего строк / Total lines: 191.
