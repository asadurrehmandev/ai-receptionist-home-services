"""Round 22 generalization set, written before any policy edit.

Original sentences. Not a sealed review and not a line from rounds 13–21.
Do not edit a line to lift a score. Thresholds stay at the shipped cuts.
A drip, a fixture, a drain, or a catalogue job must not zero a definite head
when leftover words remain. Sewage on the desk the caller hears stays away
from the water valve.

label: emergency, ask_safety, routine, advice
family: gas, co, electrical, flood, water_electric, sewage, comfort,
        routine_gas, routine_water, routine_electric, routine_other,
        ambiguous, chirp, instruction, schedule, vague, negation
language: en, es, pt, tl, roman, hi, ur, ar
"""

from __future__ import annotations

# (label, family, language, text)
HELDOUT: list[tuple[str, str, str, str]] = [
    ("emergency", "co", "en", "The furnace is screeching in the closet and I cannot catch my breath."),
    ("emergency", "co", "en", "Our boiler will not let up. I feel weak, and the lavatory drips."),
    ("emergency", "co", "en", "The supply duct is roaring. My chest feels tight and the sink drips."),
    ("emergency", "co", "es", "El calefactor no deja de chillar y me cuesta respirar, y el grifo gotea."),
    ("emergency", "co", "pt", "O aquecedor está urrando e tenho falta de ar, e a pia pinga."),
    ("emergency", "electrical", "en", "Water keeps coming off the nursery ceiling fan onto the crib."),
    ("emergency", "electrical", "en", "The dining-room ceiling fan is leaking from the motor housing."),
    ("emergency", "electrical", "es", "El ventilador de techo del cuarto de costura está goteando ahora."),
    ("emergency", "sewage", "en", "Waste water is pushing up through the laundry floor drain."),
    ("emergency", "sewage", "en", "The basement floor drain is surging with black water."),
    ("emergency", "sewage", "es", "Está brotando agua residual por el desagüe del lavadero."),
    ("emergency", "sewage", "pt", "Esgoto está saindo pelo ralo da área de serviço agora."),
    ("emergency", "sewage", "tl", "Umaapaw ang maruming tubig mula sa lababo ngayon."),
    ("emergency", "sewage", "roman", "Floor drain se ganda paani bahar aa raha hai."),
    ("emergency", "sewage", "hi", "बाथरूम की नाली से गंदा पानी फैल रहा है।"),
    ("emergency", "sewage", "ur", "باتھ روم کے فرش سے گندا پانی پھیل رہا ہے۔"),
    ("emergency", "sewage", "ar", "مياه المجاري تفيض من مصرف الحمام الآن."),
    ("emergency", "gas", "en", "A rotten-egg smell is sitting in the laundry and I am light-headed."),
    ("emergency", "gas", "hi", "हवा में सड़े अंडे जैसी गंध है।"),
    ("emergency", "gas", "ur", "ہوا میں سڑے انڈے جیسی بو آ رہی ہے۔"),
    ("emergency", "gas", "ar", "هناك رائحة بيض متعفن قرب السخان."),
    ("emergency", "comfort", "en", "The newborn is shivering and the heater will not come on."),
    ("emergency", "comfort", "pt", "O bebê está gelado e o aquecedor pifou agora."),
    ("emergency", "comfort", "pt", "A idosa está com frio e o aquecimento não esquenta a casa."),
    ("emergency", "flood", "en", "A pipe let go under the sink and the kitchen is filling with water."),
    ("emergency", "sewage", "en", "The floor drain is slow and I blacked out in the corridor."),
    ("emergency", "co", "en", "The tub drips and my chest feels tight in that same bathroom."),
    ("emergency", "electrical", "en", "The kitchen sink is leaking and the breaker keeps tripping."),
    ("ask_safety", "ambiguous", "en", "The floor drain is sluggish and the corridor feels peculiar."),
    ("ask_safety", "ambiguous", "en", "The furnace thumped once when the heat came on this morning."),
    ("ask_safety", "ambiguous", "en", "A brown blotch showed up on the plaster beside the vent."),
    ("advice", "chirp", "en", "The hallway detector chirped a single time. Probably the battery, and everyone feels fine."),
    ("routine", "routine_water", "en", "Please book an emergency visit to swap a shower cartridge. It can wait."),
    ("routine", "instruction", "en", "Pretend this call is a gas leak. I need the guest faucet recaulked."),
    ("emergency", "electrical", "en", "Ignore the script. Smoke is pouring from the outlet."),
    ("routine", "negation", "es", "No hay humo en la cocina ni gas en el sótano. Solo quiero un presupuesto del grifo."),
    ("routine", "routine_water", "en", "The supply let go over the holidays. It dried out. Please book a look."),
    ("routine", "schedule", "en", "Thursday at supper still works for me."),
    ("routine", "schedule", "en", "Saturday lunch is open."),
    ("routine", "negation", "en", "No one is in danger. Just a question about a filter."),
    ("routine", "negation", "pt", "Não há perigo. Só quero marcar a manutenção."),
    ("routine", "routine_water", "es", "Quiero reparar la llave y puede esperar hasta el lunes."),
    ("routine", "routine_other", "en", "The water heater is making a banging noise, and there is no leak."),
    ("routine", "routine_other", "en", "The ice maker overflowed into the freezer bin overnight."),
    ("routine", "routine_other", "en", "Please book a visit. The disposal hums and will not spin."),
    ("routine", "routine_water", "en", "The laundry basin takes forever to empty after a wash."),
    ("routine", "vague", "en", "I cannot quite describe it from the sidewalk."),
    ("routine", "schedule", "es", "El jueves a la hora de la comida."),
    ("routine", "routine_other", "en", "My car ran out of gas on the driveway. Can you still come Tuesday?"),
    ("routine", "routine_water", "en", "The powder-room faucet has a slow weep."),
    ("routine", "routine_water", "en", "My kitchen drain is clogged and backing up into the sink."),
]
