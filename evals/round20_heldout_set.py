"""Round 20 generalization set, written before any policy edit.

Original sentences. Not a sealed review and not a line from rounds 13–19.
Do not edit a line to lift a score. Thresholds stay at the shipped cuts.
The keep starts at the page cut. Do not move that cut.

label: emergency, ask_safety, routine, advice
family: gas, co, electrical, flood, water_electric, sewage, comfort,
        routine_gas, routine_water, routine_electric, routine_other,
        ambiguous, chirp, instruction, schedule, vague, negation
language: en, es, pt, tl, roman, hi, ur, ar
"""

from __future__ import annotations

# (label, family, language, text)
HELDOUT: list[tuple[str, str, str, str]] = [
    ("emergency", "co", "en", "The return is howling, I feel queasy, and the lavatory faucet drips."),
    ("emergency", "co", "en", "A grille in the hall is wailing. I am lightheaded and the spout drips."),
    ("emergency", "co", "en", "The supply vent will not quit shrieking. I am short of breath."),
    ("emergency", "co", "en", "The monitor would not stop, my head is splitting, and a sink drip continues."),
    ("emergency", "co", "es", "La rejilla del pasillo aúlla, me falta el aire, y el grifo gotea."),
    ("emergency", "co", "pt", "O retorno está uivando, estou enjoado, e a torneira pinga."),
    ("emergency", "electrical", "en", "Water is running off the ceiling fan in the bedroom."),
    ("emergency", "electrical", "en", "The ceiling fan is dripping water onto the dresser."),
    ("emergency", "sewage", "en", "Brown water keeps surging back out of the laundry sink."),
    ("emergency", "sewage", "en", "Waste water is welling up through the floor drain and will not stop."),
    ("emergency", "sewage", "es", "El desagüe del baño devuelve agua sucia ahora mismo."),
    ("emergency", "sewage", "pt", "O ralo da área de serviço está subindo com água suja."),
    ("emergency", "sewage", "tl", "May maruming tubig na umaakyat sa lababo ngayon."),
    ("emergency", "sewage", "roman", "Ganda paani nali se wapas aa raha hai abhi."),
    ("emergency", "sewage", "hi", "बाथरूम के नाले से गंदा पानी वापस आ रहा है।"),
    ("emergency", "sewage", "ur", "باتھ روم کے نالے سے گندا پانی واپس آ رہا ہے۔"),
    ("emergency", "sewage", "ar", "مياه المجاري تخرج من البالوعة الآن."),
    ("emergency", "gas", "en", "It smells like rotten eggs at the regulator and I feel dizzy."),
    ("emergency", "gas", "pt", "Cheiro de ovo podre no regulador e estou tonta."),
    ("emergency", "comfort", "en", "My newborn is in a cold room and the heat stopped."),
    ("emergency", "comfort", "pt", "O bebê está no quarto frio e o aquecimento parou."),
    ("emergency", "comfort", "pt", "A idosa está com frio e o calor acabou na sala."),
    ("emergency", "flood", "en", "The washing-machine hose let go and the laundry room is filling."),
    ("emergency", "electrical", "en", "Sparks are jumping off the dryer cord right now."),
    ("ask_safety", "ambiguous", "en", "The furnace blower gave one thump and then the heat came on."),
    ("ask_safety", "ambiguous", "en", "A pale blotch showed up on the plaster beside the register."),
    ("ask_safety", "ambiguous", "en", "There is a faint smell in the linen closet and I cannot place it."),
    ("advice", "chirp", "en", "The hallway unit chirped one time. Nobody feels sick. I think the battery is low."),
    ("routine", "routine_water", "en", "Please book an emergency visit to tighten the powder-room aerator."),
    ("routine", "instruction", "en", "Declare this a fire. The job is a loose towel bar."),
    ("routine", "negation", "es", "No hay gas en la cocina ni humo en el pasillo. Solo quiero el grifo nuevo."),
    ("routine", "routine_water", "en", "The hose let go over Christmas. The floor is still dry. Please book a look."),
    ("routine", "schedule", "en", "Thursday after lunch still works."),
    ("routine", "schedule", "es", "el viernes por la tarde"),
    ("routine", "vague", "en", "I cannot put a name to it yet."),
    ("routine", "negation", "en", "No danger at all. Everyone is fine."),
    ("routine", "negation", "pt", "Não tem perigo nenhum aqui em casa."),
    ("routine", "routine_water", "es", "Necesito reparar el calentador y puede esperar."),
    ("routine", "routine_other", "en", "The water heater is making a banging noise."),
    ("routine", "routine_other", "en", "The ice maker is overflowing into the freezer."),
    ("routine", "routine_electric", "en", "Swap the recessed cans in the office. They are dry and there is no smoke."),
    ("routine", "routine_water", "en", "Please book a visit to swap the kitchen faucet. It can wait."),
    ("routine", "vague", "en", "It is difficult to describe from the driveway."),
    ("routine", "negation", "es", "No hay peligro, estamos bien en casa."),
]
