"""Synthetic hazard lines for the learned head.

Templates and paraphrases only. The trainer drops any string that also appears
in a frozen eval or in the round-13 held-out file.
"""

from __future__ import annotations

import random

PLACES_EN = (
    "kitchen",
    "basement",
    "hallway",
    "garage",
    "laundry room",
    "bathroom",
    "furnace room",
    "bedroom",
    "dining room",
    "office",
)

# (text, hazard, service, family, language)
Row = tuple[str, str, str, str, str]


def _typo(rng: random.Random, text: str) -> str:
    words = text.split()
    if len(words) < 4:
        return text
    index = rng.randrange(len(words))
    word = words[index]
    if len(word) < 5 or not word.isalpha():
        return text
    cut = rng.randrange(1, len(word) - 1)
    kind = rng.choice(("drop", "swap", "double"))
    if kind == "drop":
        word = word[:cut] + word[cut + 1 :]
    elif kind == "swap" and cut + 1 < len(word):
        word = word[:cut] + word[cut + 1] + word[cut] + word[cut + 2 :]
    else:
        word = word[:cut] + word[cut] + word[cut:]
    words[index] = word
    return " ".join(words)


def _add(rows: list[Row], text: str, hazard: str, service: str, family: str, language: str) -> None:
    cleaned = " ".join((text or "").split())
    if cleaned:
        rows.append((cleaned, hazard, service, family, language))


def _registers(rng: random.Random, text: str) -> list[str]:
    base = " ".join(text.split())
    buried = (
        "After I moved the boxes and checked the filter and called my sister, "
        + base[0].lower()
        + base[1:]
    )
    mid = "before the phone number, " + base[0].lower() + base[1:]
    panic = "oh no " + base[0].lower() + base[1:]
    ramble = "we were sorting mail and then " + base[0].lower() + base[1:]
    return [base, base.lower(), _typo(rng, base), buried, mid, panic, ramble]


def _english(rng: random.Random, rows: list[Row]) -> None:
    gas = (
        "I smell gas in the {place}",
        "There is a rotten egg odor in the {place}",
        "The {place} smells like sulfur",
        "Propane is leaking in the {place}",
        "A gas odor just started in the {place}",
        "The gas line in the {place} is hissing",
        "We walked in and the {place} reeks of gas",
        "Natural gas odor in the {place} right now",
    )
    co = (
        "The carbon monoxide alarm is sounding in the {place} and someone has a headache",
        "The CO detector in the {place} will not stop and people feel dizzy",
        "Monoxide alarm in the {place} is going off and I feel nauseous",
        "The {place} CO alarm is screaming and a child is drowsy",
        "Carbon monoxide detector in the {place} plus a pounding headache",
    )
    electrical = (
        "Sparks are coming out of the outlet in the {place}",
        "Smoke is pouring from the breaker panel in the {place}",
        "The cord in the {place} smells like it is burning",
        "The socket in the {place} is throwing sparks",
        "A burning smell is coming from the panel in the {place}",
        "The appliance cord in the {place} is smoking",
    )
    flood = (
        "A pipe burst in the {place} and water is pouring out",
        "The {place} is flooding and the water will not stop",
        "Water is gushing across the {place} floor",
        "The supply line in the {place} split and it is spraying",
        "There is standing water spreading through the {place}",
    )
    water_electric = (
        "Water is running onto the extension cord in the {place}",
        "The light in the {place} is dripping and sparking",
        "A leak is landing on the breaker panel in the {place}",
        "Water is pouring onto the outlet in the {place}",
    )
    sewage = (
        "Sewage is coming up through the drain in the {place}",
        "Brown water is overflowing in the {place}",
        "Sewer water is backing out of the floor drain in the {place}",
        "Black water is rising in the {place}",
    )
    comfort = (
        "No heat in the {place}, the baby is home, and it is 42 degrees inside",
        "The furnace quit, my grandmother is here, and it is 40 inside the {place}",
        "We lost cooling, the infant is in the {place}, and it is 98 degrees",
        "The heater died, dad is 87, and the {place} is 41 degrees",
        "No air conditioning, a newborn is here, and the {place} is 101 degrees",
    )
    families = (
        (gas, "gas", "emergency"),
        (co, "co", "emergency"),
        (electrical, "electrical", "emergency"),
        (flood, "flood", "emergency"),
        (water_electric, "water_electric", "emergency"),
        (sewage, "sewage", "emergency"),
        (comfort, "comfort", "emergency"),
    )
    for templates, family, service in families:
        for place in PLACES_EN:
            for template in templates:
                for line in _registers(rng, template.format(place=place)):
                    _add(rows, line, "emergency", service, family, "en")

    asks = (
        "There might be a faint odor in the {place} and I cannot tell what it is",
        "The outlet in the {place} feels a little warm and I am not sure",
        "Possibly a smell in the {place}, or maybe it is just the trash",
        "The lights flicker whenever the microwave in the {place} runs",
        "A damp spot showed up in the {place} and it is not dripping yet",
    )
    for place in PLACES_EN:
        for template in asks:
            _add(rows, template.format(place=place), "ask_safety", "other", "ambiguous", "en")

    routines = (
        ("Can you service the gas fireplace in the {place}? It does not smell.", "fireplace", "routine_gas"),
        ("The gas grill in the {place} needs a new hose, no odor.", "grill_gas", "routine_gas"),
        ("My gas bill is high and I want the furnace in the {place} checked.", "heat", "routine_gas"),
        ("Please install a dryer gas line in the {place}, no leak.", "dryer_gas", "routine_gas"),
        ("The faucet in the {place} has a slow drip.", "faucet", "routine_water"),
        ("Flush the water heater in the {place}, it is due for maintenance.", "water_heater", "routine_water"),
        ("The toilet in the {place} keeps running.", "toilet", "routine_water"),
        ("The sink in the {place} drains slowly.", "drain", "routine_water"),
        ("The outlet cover in the {place} is cracked. No sparks and nothing is hot.", "other", "routine_electric"),
        ("No smoke and no sparks. The lamp in the {place} just flickers.", "lighting", "routine_electric"),
        ("I want a quote to replace the shower head in the {place}.", "shower_head", "routine_other"),
        ("Can you recaulk the tub in the {place}?", "caulk", "routine_other"),
        ("The pilot on the fireplace is out and I do not smell anything in the {place}.", "fireplace", "routine_gas"),
        ("The water heater in the {place} is making a banging noise.", "water_heater", "routine_water"),
        ("Popping noise from the water heater in the {place}, no leak.", "water_heater", "routine_water"),
        ("The CO detector in the {place} chirps once and the battery is low.", "other", "chirp"),
        ("Single chirp from the carbon monoxide alarm in the {place}, nobody is sick.", "other", "chirp"),
    )
    for place in PLACES_EN:
        for template, service, family in routines:
            line = template.format(place=place)
            label = "routine"
            _add(rows, line, label, service, family, "en")
            _add(rows, line.lower(), label, service, family, "en")

    others = (
        "Helena van der Meer",
        "Farooq Ali bin Yusuf",
        "Rosa de la Cruz",
        "yes",
        "the earliest you have",
        "512-555-0199",
        "1400 Maple Avenue",
        "hello",
        "I would like to book a visit",
        "si quiero agendar",
    )
    for line in others:
        _add(rows, line, "other", "other", "other", "en")


def _fill(template: str, places: tuple[str, ...]) -> list[str]:
    if "{place}" not in template:
        return [template]
    return [template.format(place=place) for place in places]


def _other_languages(rows: list[Row]) -> None:
    tables: dict[str, dict[str, tuple[str, ...]]] = {
        "es": {
            "places": ("la cocina", "el sotano", "el bano", "el pasillo", "la lavanderia", "el garaje"),
            "gas": (
                "Huele a gas en {place}",
                "Hay olor a huevo podrido en {place}",
                "Fuga de gas en {place} ahora mismo",
                "Sale olor a azufre de {place}",
            ),
            "co": (
                "La alarma de monoxido en {place} no para y me duele la cabeza",
                "El detector de CO en {place} esta sonando y estamos mareados",
                "Suena el monoxido en {place} y hay nauseas",
            ),
            "electrical": (
                "Salen chispas del enchufe en {place}",
                "Hay humo en el tablero de {place}",
                "El cable en {place} huele a quemado",
            ),
            "flood": (
                "Se revento un tubo en {place} y el agua no para",
                "Hay una inundacion en {place}",
                "El agua corre por el piso de {place}",
            ),
            "water_electric": (
                "Cae agua sobre el cable en {place}",
                "El enchufe de {place} se esta mojando y echa chispas",
            ),
            "sewage": (
                "Suben aguas negras en {place}",
                "El drenaje de {place} devuelve agua sucia",
            ),
            "comfort": (
                "No hay calefaccion, mi abuela esta en {place} y hace 40 grados",
                "No hay aire, el bebe esta en {place} y hace 99 grados",
                "Perdimos la calefaccion, mi padre tiene 86 anos y {place} esta helado",
            ),
            "routine_gas": ("Quiero servicio de la chimenea de gas en {place}, no huele",),
            "routine_water": ("El grifo de {place} gotea despacio", "El inodoro de {place} no para"),
            "routine_electric": ("Quiero cambiar la tapa del enchufe en {place}, sin chispas",),
        },
        "pt": {
            "places": ("a cozinha", "o porao", "o banheiro", "o corredor", "a lavanderia", "a garagem"),
            "gas": (
                "Tem cheiro de gas em {place}",
                "Cheiro de ovo podre em {place}",
                "Vazamento de gas em {place} agora",
            ),
            "co": (
                "O alarme de monoxido em {place} nao para e estou tonto",
                "O detector de CO em {place} disparou e estou com dor de cabeca",
            ),
            "electrical": (
                "Estao saindo faiscas da tomada em {place}",
                "Sai fumaca do quadro em {place}",
                "O fio em {place} cheira a queimado",
            ),
            "flood": (
                "O cano em {place} estourou e a agua nao para",
                "Esta alagando em {place}",
            ),
            "water_electric": ("A agua esta caindo no fio em {place}",),
            "sewage": ("O esgoto esta voltando em {place}",),
            "comfort": (
                "Nao tem aquecimento, minha avo esta em {place} e faz muito frio",
                "Sem ar condicionado, o bebe esta em {place} e faz 100 graus",
            ),
            "routine_gas": ("Quero manutencao da lareira a gas em {place}, sem cheiro",),
            "routine_water": ("A torneira de {place} pinga devagar",),
            "routine_electric": ("Quero trocar a tampa da tomada em {place}, sem faiscas",),
        },
        "tl": {
            "places": ("kusina", "basement", "banyo", "hallway", "laundry", "garahe"),
            "gas": (
                "May amoy ng gas sa {place}",
                "Amoy bulok na itlog sa {place}",
                "May tagas ng gas sa {place} ngayon",
            ),
            "co": (
                "Tumutunog ang monoxide alarm sa {place} at nahihilo ako",
                "Ang CO detector sa {place} ay hindi tumitigil at sumasakit ang ulo ko",
            ),
            "electrical": (
                "May spark sa saksakan ng {place}",
                "May usok sa breaker ng {place}",
                "Amoy sunog ang cord sa {place}",
            ),
            "flood": (
                "Pumutok ang tubo sa {place} at bumabaha",
                "May bumubuhos na tubig sa {place}",
            ),
            "water_electric": ("May tubig sa extension cord ng {place}",),
            "sewage": ("Bumubalik ang dumi sa drain ng {place}",),
            "comfort": (
                "Walang init sa {place}, nandito ang lola ko at sobrang lamig",
                "Walang aircon, nandito ang sanggol sa {place} at sobrang init",
            ),
            "routine_gas": ("Service lang ng gas fireplace sa {place}, walang amoy",),
            "routine_water": ("Tumutulo nang dahan ang gripo sa {place}",),
            "routine_electric": ("Papalitan ang takip ng outlet sa {place}, walang spark",),
        },
        "roman": {
            "places": ("kitchen", "basement", "bathroom", "hallway", "laundry", "garage"),
            "gas": (
                "{place} mein gas ki tez boo aa rahi hai",
                "{place} se ande jaisi smell aa rahi hai",
                "{place} mein gas leak ho raha hai abhi",
            ),
            "co": (
                "{place} ka monoxide alarm band nahi ho raha aur ulti aa rahi hai",
                "{place} mein CO detector baj raha hai aur sar dard hai",
            ),
            "electrical": (
                "{place} ke socket se chingariyan nikal rahi hain",
                "{place} ke breaker se dhuan aa raha hai",
                "{place} ki taar se jalne ki boo aa rahi hai",
            ),
            "flood": (
                "{place} ka pipe phat gaya aur paani ruk nahi raha",
                "{place} mein paani bhar raha hai",
            ),
            "water_electric": ("{place} ke extension cord par paani gir raha hai",),
            "sewage": ("{place} ke drain se ganda paani wapas aa raha hai",),
            "comfort": (
                "Heater band hai, dadi {place} mein hain aur bahut thand hai",
                "AC band hai, baccha {place} mein hai aur 100 degree garmi hai",
            ),
            "routine_gas": ("{place} ke gas fireplace ki service chahiye, koi boo nahi",),
            "routine_water": ("{place} ka nal dheere tapak raha hai",),
            "routine_electric": ("{place} ke outlet ka cover badalna hai, chingari nahi",),
        },
        "hi": {
            "places": ("किचन", "बेसमेंट", "बाथरूम", "हॉल", "लॉन्ड्री", "गैरेज"),
            "gas": (
                "{place} में गैस की तेज़ गंध आ रही है",
                "{place} में अंडे जैसी बदबू है",
                "{place} में गैस लीक हो रही है",
            ),
            "co": (
                "{place} का मोनोऑक्साइड अलार्म नहीं रुक रहा और उल्टी आ रही है",
                "{place} में सीओ डिटेक्टर बज रहा है और सिर दर्द है",
            ),
            "electrical": (
                "{place} के सॉकेट से चिंगारियाँ निकल रही हैं",
                "{place} के ब्रेकर से धुआँ आ रहा है",
            ),
            "flood": (
                "{place} का पाइप फट गया है और पानी नहीं रुक रहा",
                "{place} में पानी भर रहा है",
            ),
            "water_electric": ("{place} की तार पर पानी गिर रहा है",),
            "sewage": ("{place} की नाली से गंदा पानी वापस आ रहा है",),
            "comfort": (
                "हीटर बंद है, दादी {place} में हैं और बहुत ठंड है",
                "एसी बंद है, बच्चा {place} में है और 100 डिग्री गर्मी है",
            ),
            "routine_gas": ("{place} की गैस फायरप्लेस की सर्विस चाहिए, गंध नहीं",),
            "routine_water": ("{place} का नल टपक रहा है",),
            "routine_electric": ("{place} के आउटलेट का कवर बदलना है, चिंगारी नहीं",),
        },
        "ur": {
            "places": ("کچن", "بیسمنٹ", "باتھ روم", "ہال", "لانڈری", "گیراج"),
            "gas": (
                "{place} میں گیس کی تیز بو آ رہی ہے",
                "{place} میں انڈے جیسی بو ہے",
                "{place} میں گیس لیک ہو رہی ہے",
            ),
            "co": (
                "{place} کا مونو آکسائیڈ الارم نہیں رک رہا اور الٹی آ رہی ہے",
                "{place} میں سی او ڈیٹیکٹر بج رہا ہے اور سر درد ہے",
            ),
            "electrical": (
                "{place} کے ساکٹ سے چنگاریاں نکل رہی ہیں",
                "{place} کے بریکر سے دھواں آ رہا ہے",
            ),
            "flood": (
                "{place} کا پائپ پھٹ گیا ہے اور پانی نہیں رک رہا",
                "{place} میں پانی بھر رہا ہے",
            ),
            "water_electric": ("{place} کی تار پر پانی گر رہا ہے",),
            "sewage": ("{place} کے ڈرین سے گندا پانی واپس آ رہا ہے",),
            "comfort": (
                "ہیٹر بند ہے، دادی {place} میں ہیں اور بہت ٹھنڈ ہے",
                "اے سی بند ہے، بچہ {place} میں ہے اور 100 ڈگری گرمی ہے",
            ),
            "routine_gas": ("{place} کی گیس فائر پلیس کی سروس چاہیے، بو نہیں",),
            "routine_water": ("{place} کا نل ٹپک رہا ہے",),
            "routine_electric": ("{place} کے آؤٹ لیٹ کا کور بدلنا ہے، چنگاری نہیں",),
        },
        "ar": {
            "places": ("المطبخ", "القبو", "الحمام", "الممر", "المغسلة", "المرأب"),
            "gas": (
                "توجد رائحة غاز في {place}",
                "رائحة بيض فاسد في {place}",
                "تسرب غاز في {place} الآن",
            ),
            "co": (
                "إنذار أول أكسيد الكربون في {place} لا يتوقف وأشعر بالغثيان",
                "كاشف أول أكسيد الكربون في {place} يعمل وعندي صداع",
            ),
            "electrical": (
                "تخرج شرارات من المقبس في {place}",
                "يخرج دخان من اللوحة في {place}",
            ),
            "flood": (
                "انفجر أنبوب في {place} والماء لا يتوقف",
                "الماء يغمر {place}",
            ),
            "water_electric": ("يسقط الماء على السلك في {place}",),
            "sewage": ("مياه الصرف ترجع في {place}",),
            "comfort": (
                "لا توجد تدفئة وجدتي في {place} والبرد شديد",
                "لا يوجد تبريد والرضيع في {place} والحر شديد",
            ),
            "routine_gas": ("أريد صيانة مدفأة الغاز في {place} بلا رائحة",),
            "routine_water": ("الصنبور في {place} يقطر ببطء",),
            "routine_electric": ("أريد تغيير غطاء المقبس في {place} بلا شرارات",),
        },
    }
    emergency_families = ("gas", "co", "electrical", "flood", "water_electric", "sewage", "comfort")
    for language, table in tables.items():
        places = table["places"]
        for family in emergency_families:
            for template in table[family]:
                for line in _fill(template, places):
                    _add(rows, line, "emergency", "emergency", family, language)
                    _add(rows, line.lower(), "emergency", "emergency", family, language)
        for family in ("routine_gas", "routine_water", "routine_electric"):
            service = {"routine_gas": "fireplace", "routine_water": "faucet", "routine_electric": "other"}[family]
            for template in table[family]:
                for line in _fill(template, places):
                    _add(rows, line, "routine", service, family, language)


def build(rng: random.Random) -> list[Row]:
    rows: list[Row] = []
    _english(rng, rows)
    _other_languages(rows)
    return rows
