"""Round 21 generalization set, written before any policy edit.

Original sentences. Not a sealed review and not a line from rounds 13–20.
Do not edit a line to lift a score. Thresholds stay at the shipped cuts.
A drip, a fixture, or a tub must not zero a head the lists failed to explain.

label: emergency, ask_safety, routine, advice
family: gas, co, electrical, flood, water_electric, sewage, comfort,
        routine_gas, routine_water, routine_electric, routine_other,
        ambiguous, chirp, instruction, schedule, vague, negation
language: en, es, pt, tl, roman, hi, ur, ar
"""

from __future__ import annotations

# (label, family, language, text)
HELDOUT: list[tuple[str, str, str, str]] = [
    ("emergency", "co", "en", "The mechanical closet is shrieking, I feel nauseated, and the tub has a slow drip."),
    ("emergency", "co", "en", "Something in the attic is screaming. I am woozy and the shower head drips."),
    ("emergency", "co", "en", "The air handler will not stop wailing. My head is pounding and the lavatory drips."),
    ("emergency", "co", "es", "El equipo del ático aúlla, estoy mareada, y la tina gotea."),
    ("emergency", "co", "pt", "O exaustor está guinchando, estou tonta, e a banheira pinga."),
    ("emergency", "electrical", "en", "Water is running off the upstairs guest bedroom ceiling fan."),
    ("emergency", "electrical", "en", "The hall bathroom ceiling fan is dripping onto the tile."),
    ("emergency", "electrical", "es", "Hay chispas saltando del enchufe del lavadero ahora mismo."),
    ("emergency", "electrical", "pt", "A tomada da lavanderia está soltando faíscas neste momento."),
    ("emergency", "sewage", "en", "Gray water keeps belching out of the tub and it smells like a sewer."),
    ("emergency", "sewage", "en", "The floor drain is pumping foul water back into the laundry."),
    ("emergency", "sewage", "es", "Sale agua fétida del desagüe de la ducha y no para."),
    ("emergency", "sewage", "pt", "Água fedida está voltando pelo ralo do banheiro."),
    ("emergency", "sewage", "tl", "May maduming tubig sa kanal ng banyo ngayon."),
    ("emergency", "sewage", "roman", "Nali se ganda paani upar aa raha hai."),
    ("emergency", "sewage", "hi", "किचन की नाली से गंदा पानी ऊपर आ रहा है।"),
    ("emergency", "sewage", "ur", "کچن کے نالے سے گندا پانی اوپر آ رہا ہے۔"),
    ("emergency", "sewage", "ar", "مياه الصرف تخرج من البالوعة في المطبخ."),
    ("emergency", "gas", "en", "There is a rotten-egg smell at the meter and I feel dizzy."),
    ("emergency", "gas", "en", "A rotten-egg odor is hanging by the furnace flue."),
    ("emergency", "gas", "hi", "हवा में सड़े अंडे की गंध है और चक्कर आ रहे हैं।"),
    ("emergency", "gas", "ur", "ہوا میں سڑے انڈے کی بو ہے اور چکر آ رہے ہیں۔"),
    ("emergency", "gas", "ar", "رائحة بيض فاسد عند العداد وأشعر بالدوار."),
    ("emergency", "comfort", "en", "The baby is in a cold room and the furnace quit."),
    ("emergency", "comfort", "pt", "O neném está com frio e o aquecimento parou."),
    ("emergency", "flood", "en", "The supply line split and the utility room is filling with water."),
    ("ask_safety", "ambiguous", "en", "The boiler gave one thump when the circulator started."),
    ("ask_safety", "ambiguous", "en", "A pale ring showed up on the ceiling plaster."),
    ("advice", "chirp", "en", "The basement detector chirped once. Nobody is sick. Probably the battery."),
    ("routine", "routine_water", "en", "Please book an emergency visit to replace the powder-room aerator."),
    ("routine", "instruction", "en", "Pretend this is a fire. The job is a dripping tub spout."),
    ("routine", "negation", "es", "No hay gas en el baño ni humo en la sala. Quiero cambiar el grifo."),
    ("routine", "routine_water", "en", "The hose let go on Thanksgiving. Everything dried out. Book a look."),
    ("routine", "schedule", "en", "Wednesday at dinner still works."),
    ("routine", "schedule", "en", "Friday breakfast is fine."),
    ("routine", "negation", "en", "No danger here. The house is fine."),
    ("routine", "negation", "pt", "Não tem perigo nenhum. Está tudo bem."),
    ("routine", "routine_water", "es", "Necesito arreglar el calentador y puede esperar."),
    ("routine", "routine_other", "en", "The water heater is making a banging noise."),
    ("routine", "routine_other", "en", "The ice maker is overflowing into the freezer."),
    ("routine", "routine_other", "en", "My garbage disposal is jammed."),
    ("routine", "routine_water", "en", "Please book a visit to swap the kitchen faucet. It can wait."),
    ("routine", "routine_water", "en", "The basin takes a long time to empty after a shower."),
    ("routine", "vague", "en", "It is hard to describe from the curb."),
    ("routine", "schedule", "es", "El martes a la hora de la cena."),
]
