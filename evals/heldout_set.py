"""Held-out hazard lines written before the round-5 tune.

These sentences are not the frozen desk set and not a review file.
Do not edit them to lift the score.
"""

from __future__ import annotations

# label: transfer (page), ask (safety question), advice (battery chirp), routine (book or decline)
HELDOUT: list[tuple[str, str]] = [
    # Water moving from a ceiling or an appliance.
    ("transfer", "Water is streaming out of the dining room light."),
    ("transfer", "A steady stream is coming down from the upstairs bath into the hall."),
    ("transfer", "The washer hose popped and water is running across the laundry floor."),
    ("transfer", "The ice maker line let go and water is spraying the cabinets."),
    ("transfer", "Water is pouring through the living room ceiling."),
    ("transfer", "The supply line under the dishwasher is spraying and it will not stop."),
    ("transfer", "There is standing water spreading from the water heater closet."),
    ("transfer", "The vanity supply is shooting water onto the bathroom floor."),
    ("transfer", "Water keeps coming through the ceiling around the can light."),
    ("transfer", "The fridge line burst and the kitchen floor is soaked."),
    # Sewage moving back through a fixture.
    ("transfer", "Sewage is coming up through the shower drain."),
    ("transfer", "The floor drain is pushing sewer water into the basement."),
    ("transfer", "Brown water is overflowing from the toilet onto the tile."),
    ("transfer", "Wastewater is backing out of the laundry drain."),
    ("transfer", "Black water is rising out of the basement floor drain."),
    ("transfer", "The guest bath drain is sending sewer water onto the floor."),
    # Alarm readings and a sounding detector, without naming the gas.
    ("transfer", "The hallway alarm is reading 180 and it will not stop."),
    ("transfer", "The detector by the bedrooms is shrieking and shows a high number."),
    ("transfer", "Everyone feels sick and the wall unit will not quit."),
    ("transfer", "The monitor next to the furnace reads 90 and keeps sounding."),
    ("transfer", "That detector is screaming and the display says 140."),
    ("transfer", "The alarm upstairs will not stop and people feel dizzy."),
    # Scorch, a hot surface, burning.
    ("transfer", "The drywall beside the furnace is brown and too hot to touch."),
    ("transfer", "I smell something burning and the panel cover is hot."),
    ("transfer", "The closet around the water heater looks scorched and feels hot."),
    ("transfer", "There is a charred patch on the wall behind the dryer."),
    ("transfer", "The breaker door is discolored and warm enough to hurt."),
    ("transfer", "A burning smell is coming from the outlet and the plate is melted."),
    # Indoor-rain and flood metaphors.
    ("transfer", "It is raining in the kitchen from the ceiling."),
    ("transfer", "The family room has water everywhere, like an indoor rainstorm."),
    ("transfer", "The ceiling turned into a sprinkler over the hallway."),
    ("transfer", "We are basically swimming in the laundry room, water on every side."),
    ("transfer", "Rain is falling indoors through the bedroom ceiling."),
    # Vulnerable person and no heat. These page.
    ("transfer", "The furnace quit and the baby is home. It is 48 degrees inside."),
    ("transfer", "No heat and my infant is in the house."),
    ("transfer", "The heater will not start and my newborn is here."),
    ("transfer", "We lost heat and my 80 year old mother is home."),
    ("transfer", "It is 46 degrees inside and the toddler is shivering."),
    ("transfer", "The boiler died and grandpa uses oxygen."),
    # Clear hazards the desk already owes the caller.
    ("transfer", "I smell rotten eggs by the furnace right now."),
    ("transfer", "The gas line is hissing in the utility room."),
    ("transfer", "Sparks are shooting out of the outlet."),
    ("transfer", "The basement pipe burst and water is pouring out."),
    ("transfer", "There is a gas odor in the kitchen and it is strong."),
    ("transfer", "Smoke is coming from the breaker panel."),
    # Borderline. Ask, do not page and do not ignore.
    ("ask", "The ceiling has a damp spot that showed up this morning."),
    ("ask", "I might be smelling something near the furnace, but I am not sure."),
    ("ask", "The outlet is a little warm and I cannot tell if that is normal."),
    ("ask", "There is a faint odor by the water heater and I do not know what it is."),
    ("ask", "A wet mark appeared on the ceiling and it is not dripping yet."),
    ("ask", "The detector beeped once and I am not sure it means anything."),
    ("ask", "Possibly a gas smell, or maybe it is just the trash."),
    ("ask", "The wall by the panel feels slightly warm. Nothing else is wrong."),
    # Battery chirp stays advice.
    ("advice", "The carbon monoxide alarm chirps once every minute. I think the battery is low."),
    ("advice", "Our detector chirps at night and the battery is due."),
    ("advice", "It only chirps. I already bought a battery for the carbon monoxide alarm."),
    ("advice", "Single chirp from the CO detector, no headache, just the battery."),
    # Explicit negations and status-ok checks stay routine.
    ("routine", "The outlet cover is cracked, but there are no sparks and nothing is hot."),
    ("routine", "The detector light is green. I just want it tested."),
    ("routine", "No sparks from the switch. It only clicks."),
    ("routine", "There is no smell of gas. The pilot is fine and I need a tune-up."),
    ("routine", "The alarm shows green and I only want the annual test."),
    ("routine", "No smoke and no sparks. The lamp just flickers."),
    ("routine", "I do not smell gas. Please quote a new thermostat."),
    # A finished repair stays routine.
    ("routine", "We had a gas leak in March. They repaired it and it has been quiet."),
    ("routine", "The pipe was repaired last spring and I am calling about a slow faucet."),
    ("routine", "A gas leak was resolved in January. Nothing is happening now."),
    ("routine", "They fixed the sewer backup months ago. I want a camera quote."),
    ("routine", "The furnace leak got repaired and I have not smelled anything since."),
    ("routine", "That burst line was already repaired. This call is for a dripping tub faucet."),
    # Ordinary work.
    ("routine", "The kitchen faucet drips when it is off."),
    ("routine", "The AC is not cooling the spare room."),
    ("routine", "The bathroom sink drains slowly."),
    ("routine", "I need a quote to replace a toilet."),
    ("routine", "Can you flush the water heater next week?"),
    ("routine", "The disposal hums and does not spin."),
    ("routine", "How much is the diagnostic fee?"),
    ("routine", "I only have an emergency fund question, not a leak."),
    ("routine", "The car is out of gas in the driveway."),
    ("routine", "We want to convert the stove from electric to gas."),
    ("routine", "The gas bill looks high. No odor."),
    ("routine", "Just asking how fast you can get here for a clog."),
    ("routine", "The tub is backing up a little. No sewage."),
    ("routine", "A single drip under the sink, nothing else."),
    ("routine", "The house is 72 and the blower is loud."),
    ("routine", "Please book a seasonal tune-up."),
    ("routine", "No heat in the guest room, everyone is fine and it is 70 inside."),
    ("routine", "The toddler locked the bathroom door. This is not a plumbing problem."),
    ("routine", "I smell burnt toast, not the furnace."),
    ("routine", "The detector needs a new battery and it is not sounding."),
    # Spanish is a supported hazard check, not a booking language.
    ("transfer", "Huele a gas en la cocina ahora mismo."),
    ("transfer", "Sale agua a chorros por el techo de la sala."),
    ("transfer", "Hay aguas negras subiendo por la regadera."),
    ("routine", "El grifo de la cocina gotea un poco."),
    ("routine", "Quiero una cita para el calentador, no hay olor a gas."),
    ("routine", "El aire no enfría y la casa está a 74."),
    ("advice", "El detector de monóxido solo pita por la pila."),
]
