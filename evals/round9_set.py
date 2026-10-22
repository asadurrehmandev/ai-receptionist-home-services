"""Fresh dev lines for round 9. Written and hashed before the round-9 edits.

Do not edit a line to lift the score. The scorer is evals/round9.py.
Labels are the intended class. Wording is original to this file.

Content sha256 of the labeled lines, before any rule change:
dc04696d30d4b3a32aa7647af126b05c77f602fd0500aa67693de250c3072934

Before those changes, on this file: transfer 11/25, routine 12/14,
false pages 2/14. Safety answers: clear 4/6, page 15/15.
That before score is the dev-set number. It is not a sealed review.
"""

from __future__ import annotations

# (label, text). label is transfer or routine.
ROUND9: list[tuple[str, str]] = [
    ("transfer", "The hall ceiling is bulging and full of water."),
    ("transfer", "The plaster overhead is ballooning and water is sitting in it."),
    ("transfer", "Water is pressing the spare-room ceiling into a sag."),
    ("transfer", "The kitchen faucet tingles when I touch it."),
    ("transfer", "My hand tingles on the metal railing by the washer."),
    ("transfer", "I got a shock off the porch light."),
    ("transfer", "I called about a slow drain and a filter quote and the Saturday rate. There is smoke in the attic."),
    ("transfer", "Please price a faucet cartridge and a noisy bath fan and a new thermostat battery. Water is pouring through the dining room ceiling."),
    ("transfer", "Czuję gaz w kuchni i mam zawroty głowy."),
    ("transfer", "Piwnica jest zalana."),
    ("transfer", "Prąd kopnął mnie przy umywalce."),
    ("transfer", "Me dio un calambre el grifo de la cocina."),
    ("transfer", "Dhuaan aa raha hai heater se."),
    ("transfer", "Aag lag gayi hai panel mein."),
    ("transfer", "Paani bhar gaya hai basement mein."),
    ("transfer", "باورچی خانے میں دھواں ہے۔"),
    ("transfer", "Huele a gas junto a la estufa."),
    ("transfer", "El sótano está inundado y el agua sigue subiendo."),
    ("transfer", "گھر میں گیس کی بو آ رہی ہے۔"),
    ("transfer", "The laundry ceiling has water pressing on it and the drywall is swollen."),
    ("transfer", "Hay humo saliendo del calentador."),
    ("transfer", "Gas ki bu aa rahi hai kitchen se."),
    ("transfer", "W kotłowni jest pożar."),
    ("transfer", "The light fixture in the stairwell just shocked me."),
    ("transfer", "Smoke is pouring from the hall closet right now."),
    ("routine", "Last winter the disposal threw sparks and we replaced it. I want a quote for a new one."),
    ("routine", "What would the after-hours fee be if we ever needed a gas-line repair?"),
    ("routine", "How much is a gas line visit compared with a normal service call?"),
    ("routine", "The first cold morning always smells like dusty heat when the furnace starts."),
    ("routine", "When the heat kicks on each October there is a burning-dust smell for an hour."),
    ("routine", "We are writing a household emergency plan and want you to walk the house."),
    ("routine", "Please run a new gas line to the pool heater. There is no odor."),
    ("routine", "If the ceiling ever sagged, who would we call?"),
    ("routine", "Kitna lagega gas line ka, koi leak nahi."),
    ("routine", "I want the yearly heat pump check."),
    ("routine", "Yesterday the outlet sparked once and it has been quiet since."),
    ("routine", "A practice fire drill is on our calendar. Nothing is wrong in the house."),
    ("routine", "The crawl space smells like warm dust on the first heating day."),
    ("routine", "Please quote a new gas line for the garage heater. No smell at all."),
]

# Answers to the safety question.
SAFETY9: list[tuple[str, str]] = [
    ("page", "Yes, we already stepped outside."),
    ("page", "Yes. Everyone left the house."),
    ("page", "Yeah, we got out and we are on the lawn."),
    ("page", "Yes, I am scared and we left."),
    ("page", "Yep, we evacuated to the driveway."),
    ("page", "Yes, we are outside now."),
    ("page", "Yeah we left the building."),
    ("page", "Yes. We got everybody out."),
    ("page", "Yep, standing outside."),
    ("page", "Yes, we moved out to the porch."),
    ("page", "Yeah, I am frightened and we left."),
    ("page", "Yes we exited the house."),
    ("page", "Yep, we are out on the sidewalk."),
    ("page", "Yes, the family got out."),
    ("page", "Yeah, we went outside and stayed there."),
    ("clear", "No thanks, the house is calm and the drain is only slow."),
    ("clear", "Nah, not a bit. I want a weekday visit."),
    ("clear", "We're okay. Nothing urgent about the noisy pump."),
    ("clear", "Not that I can tell. It can wait."),
    ("clear", "All clear here. Please just schedule the maintenance."),
    ("clear", "No one is in danger. The tub drains slowly."),
]
