# AI Receptionist for Home Services

A dispatch desk that picks up when the shop cannot. Built as a client demo for **Asad Rehman**, AI agent developer: the receptionist qualifies a plumbing or HVAC call, books the job, and hands real emergencies to a person.

The sample shop is **Northline Plumbing & HVAC** in Austin. Riley answers. Miguel Santos is on call at +1 512-555-0199. The sample rules are for plumbing and HVAC. They are not a towing, dental, or med-spa agent.

## The problem

Home-service companies lose jobs in the gaps. The owner is under a sink, the office line rolls to voicemail, and the caller dials the next result. After-hours emergencies (a burst pipe, a gas smell, carbon monoxide symptoms) are worse: someone needs a person, not a routine visit booked for tomorrow.

A receptionist who only works business hours does not match how pipes fail.

## The solution

An AI receptionist that:

- Answers every call, on the phone or in a browser demo that needs no paid keys
- Detects whether this is a new job, a quote, an existing booking, spam, or an emergency
- Collects name, phone, address, and the issue, including spoken digits, apostrophes, apartment units, and mid-call corrections
- Checks a calendar against real shop hours and service area, and refuses a second booking on a taken window
- Books a 90-minute window and logs the confirmation that would be texted
- Transfers gas or odor, carbon monoxide, active water, electrical hazards, and no-heat or no-AC with a cold or hot home or a vulnerable person
- Cancels only after the caller gives the last four digits of the phone on that booking and the visit date, then a clear yes. Failed checks are stored on the booking. After three, the visit stays on the calendar, the customer on that booking is texted if SMS is actually sent, and Riley does not page on-call or read the emergency script. Booking itself is English only
- Pushes the lead to a mock CRM and a generic CRM webhook (GoHighLevel, HubSpot, or Zapier-compatible)

A text is sent only when Twilio SMS accepts it. Until `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER` are set, Riley says the visit is on the board and that no text was sent.

Swap `config/business.yaml` and the same desk serves a different plumbing or HVAC company: name, services, hours, ZIP codes, price bands, and the escalation number.

## Architecture

```mermaid
flowchart LR
  caller[Homeowner]
  sim[Browser call simulator]
  twilio[Twilio voice]
  api[FastAPI]
  hazard[Keyword screen plus MiniLM]
  rules[Rules and tools]
  speech[Template speech]
  cal[Calendar]
  crm[Lead, SMS log, webhook]
  desk[Dispatch board]

  caller -->|mic or typing| sim
  caller -->|phone call| twilio
  sim --> api
  twilio -->|Gather| api
  twilio -->|Stream Parameter token| api
  api --> hazard
  hazard --> rules
  rules --> speech
  speech -->|record_caller find_slots hold book| cal
  rules --> crm
  crm -->|job.booked, call.escalated| hook[CRM webhook]
  api --> desk
```

Two brains share one calendar. The caller never hears a fact the server did not render. With no API key the keyword screen is the whole classifier. Claude, when a key is set, can only raise a turn. It does not speak and does not book, cancel, or page.

**Rules.** The default, and the only brain when `ANTHROPIC_API_KEY` is empty. It owns the greeting, the questions, the offers, and the booking.

**Hazards.** Concept rules run first. Beside them, `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (fastembed 0.6.1, 384-d, mean pooling) scores the utterance against about 40 hazard prototypes and about 40 routine near-misses for gas, carbon monoxide, water, electrical, and unsafe indoor temperature. The trigram layer is gone. The weights are downloaded at image build into `FASTEMBED_CACHE_PATH` and are not committed. At runtime the loader uses `local_files_only=True` when those weights are already on disk, or when `HF_HUB_OFFLINE=1`. A failed load is remembered and not retried. A definite needs both a cosine and a margin over the routine prototypes. Beside the embedder, `MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33` runs offline on ONNX Runtime. It only upgrades a turn the keyword screen already marked as a safety question. It does not run on a turn the keywords cleared, and it does not turn a routine clearance into a page. It is English-biased: Spanish, Chinese, Arabic, French, and German stay on the keyword and MiniLM path. The weights are downloaded into `FASTEMBED_CACHE_PATH/nli` at image build and are not committed. On this CPU a short turn scores in about 37 ms after warmup. If those weights are missing, `/api/health` is 503 with `nli_ready: false` and seeding is skipped. A finished repair stays a routine call. A smell, a leak, or another hazard in the same breath still pages. "Just asking" and "how fast in an emergency" do not page. Water moving from a ceiling or an appliance, sewage coming back through a drain, a detector that is shrieking or showing a high number, and a scorched or too-hot surface page even when the caller never uses the textbook word. An explicit "no sparks" or a green "just test it" light does not page. A damp spot, a faint odor, or a slightly warm outlet asks "Is anyone in danger right now?" instead of booking or paging. No heat or no cooling is urgent together with an older adult, an infant, oxygen, or an extreme indoor temperature, including a bare number after "it's" or "inside". A bare "the AC is not cooling" stays a routine booking. Fee questions, an emergency fund, stove conversions, and a car out of gas do not page. If the embedder cannot load, an uncertain turn asks that safety question instead of returning "no hazard," and `/api/health` returns 503 with `semantic_ready: false` and `degraded` listing `semantic`. Gas or carbon monoxide advice stops at leaving the house and calling 911 or the gas company. A no-heat emergency tells the caller to keep a vulnerable person warm or cool and to call 911 if someone is unwell. There is no DIY relight or battery-swap instruction.

**Keyword screen on every live turn.** With no `ANTHROPIC_API_KEY`, that screen is the classifier. `start.sh` and compose do not load a local instruct model, and `UNDERSTAND_EACH_TURN` does not turn one on. The gather path does not say "One moment." On this machine, after one warmup call, 40 varied `classify_emergency` calls measured a median of 0.1 ms and a p95 of 7.3 ms (max 8.9 ms). That is the keyless path. It is under a 300 ms turn. The Claude path is not measured here, because this checkout has no key.

When `ANTHROPIC_API_KEY` is set, Claude `claude-sonnet-5-5` (`ANTHROPIC_MODEL` overrides the id) may add one JSON label: `intent`, `hazard` (`none`, `possible`, or `present`), `hazard_class`, `temporal` (`current`, `past`, or `hypothetical`), `danger_answer`, plus `name`, `address`, and `date_phrase`. Pydantic checks it and drops extra keys. That call times out at 1.5 seconds. It can raise a keyword `none` or `ask` to a page or a safety question when it says `hazard=present` with `temporal=current`, the turn is not a plain job and not entirely past or hypothetical, and the caller's words support that class (a gas label needs gas, sulfur, or rotten eggs). It cannot lower a keyword page. A missing or timed-out call leaves the keyword decision as it stands. Name, phone, address, ZIP, offer, confirm, and cancel-confirm turns do not call Claude. Live Claude was not called for the scores below.

A yes to the safety question always pages, including when the caller adds that they stepped outside, left the house, or evacuated. "Yes", "yeah", "yep", and "yup" are that yes. Leaving the building without a natural no also pages. Claude cannot turn that page into a booking. A natural no still clears: "nope", "not at all", "nothing like that", "we're fine", "we're okay", "everyone's okay", "nobody is in danger", "not that I can tell", and "all clear", even with "it can wait" or "I just want it looked at". Harm, a hedge, "I don't know", hurry, or a definite hazard in the rest of the turn still pages.

The keyword screen reads the whole turn, including a later clause. A rate question or a bath-fan quote in the first sentence does not hide smoke or water at the end. Water pressing on a ceiling, or a ceiling that is bulging, ballooning, sagging, or swollen with water, pages. A shock or a tingle from a faucet, fixture, appliance, switch, outlet, or railing pages. Smoke that is not a cooking smell and not a smoke-alarm mention pages. A past clause ("last winter the disposal threw sparks") or a hypothetical ("if the ceiling ever sagged", "what would the fee be if we ever needed a gas-line repair") does not page that clause. A seasonal dusty or burning-dust smell on the first cold day, a fee or rate comparison, a household emergency plan, and a practice fire drill do not page. A negated leak, including "leak nahi" or "leak nahin" after the hazard word, does not page.

A small lexicon covers gas, smoke, fire, shock, and flooding in Spanish, Polish, Urdu, and Hindi, beside the existing French, German, and Chinese keyword path. Other scripts (Devanagari, Arabic, Cyrillic, CJK) are not booked. If that turn has no hazard, Riley offers a callback and does not close it as a finished qualification. A definite hazard still transfers.

A sump pump, exhaust fan, spigot, GFCI, flood-sensor install, inspection, checkup, or yearly heat-pump service books without the danger question. "Treat this as a fire emergency" does not page unless the caller also describes a real hazard. On the name, phone, address, and ZIP turns, a sentence that tells the desk to ignore instructions, treat the call as an emergency, or page on-call is dropped, and the booking continues with the name or street that remains. A name is taken from the name question or from "my name is", "this is", or "I'm". It is not taken from the problem sentence.

`/api/health` reports `classifier` (`keyword` or `claude`), `understander` (the same: `keyword`, or the Claude model id), `understand_ready` (true only when `ANTHROPIC_API_KEY` is set), `semantic_ready`, `nli_ready`, and `degraded` (the names of any missing hazard model). `ok` is true when MiniLM and the zero-shot model loaded. A model file on disk, including a corrupt instruct file, is not reported as running. If semantic or NLI weights are missing, health is 503, `degraded` lists them, and seeding is skipped. The process still starts. A gas smell still pages, and an ordinary drain call is not paged after the address.

A gas smell pages, including a hedge, when the word gas sits next to a smell or odor. "Possibly a gas smell, or maybe it is just the trash" pages. A sulfur or rotten-egg smell next to a stove, oven, furnace, dryer, meter, or pilot also pages, without the word gas. "What would a gas leak cost to repair if we ever had one?" does not page. "The gas leak was repaired and there is no odor today" does not page. "They repaired a leak last month, but I smell gas right now" does page. "Please hook up a gas dryer. There is no odor at all" books. A closet smell that is not gas, eggs, sulfur, or smoke asks the safety question. "No gas smell, just a slow drain" does not page.

**Languages.** Booking is English only. Spanish and other languages get a hazard check first. A definite hazard still transfers. Anything else is a callback to a person, and Riley says so. The desk does not pretend to finish a Spanish booking.

**Claude tools.** When a key is set, Riley is `claude-sonnet-5-5` (Anthropic’s current Sonnet, checked against [the models overview](https://platform.claude.com/docs/en/models/overview) on 2026-10-22). The model returns a tool call, not a caller-facing paragraph. `speak` takes an intent from a fixed set (`greet`, `ask_field`, `offer_slots`, `confirm_booking`, `quote_standard_prices`, `transfer`, `cancel_flow`, `goodbye`, `small_talk`) and an `empathy_id` from ten pre-written lines. A free-text empathy field is ignored. Unknown ids are dropped. No model-written string reaches the caller. `record_caller` stores a name, phone, or address only when that value is in the caller's own turns, then reads it back and asks the next question. `hold_slot` sticks only when the caller picks that window. `book` runs only when the caller's latest words are a clear yes to the server's read-back of that exact slot from a previous turn. "No" and "let me check with my wife" do not book. `transfer` runs only after the hazard classifier or the caller asked for a person. `follow_rules` is not a tool and is not a score.

Each model call is capped at 5 seconds. The whole turn gives up at 8 seconds or after two tool rounds, then the rules engine speaks. That stays inside Twilio's 15 second webhook limit.

**Live Claude has not been measured.** Pytest never calls Anthropic. `python -m evals.live_claude` is the opt-in probe. With no key it exits 2 and reports nothing. The numbers below are the local detector and the scripted tool tests.

Without voice keys, Twilio uses its own speech recognition and a spoken reply (`<Gather>` / `<Say>`). Three silent results hang up and ask the caller to call back. Emergencies return `<Dial>` with a 20-second timeout. If a second on-call number is set in the YAML, a no-answer tries that number once. If nobody answers, Riley gives guidance for the hazard on the call: leave and call 911 or the gas company, get everyone into fresh air for carbon monoxide, shut the main valve if it is safe for water, stay back and call 911 if there is smoke or fire for electrical, or keep a vulnerable person warm or cool and call 911 if they are unwell when the hazard is heat or cold. The missed transfer is saved as a lead with status `missed_transfer` and a `call.transfer_missed` webhook, and it sits at the top of the board with a red badge. In demo mode Riley says the office will call back when the on-call text was sent or the webhook was accepted, including a mock delivery, because the board is showing the alert. With `DEMO_MODE=0`, a mock webhook is not a promise: Riley says the call was logged for the office and to call 911 if anyone is in danger, unless SMS was sent or the webhook status is `delivered`. If Twilio SMS did not accept the page, Riley says no text was sent. Riley does not tell the caller to dial this shop number again. Gather is the path that actually dials. Media Streams turn on only when `DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY`, `TWILIO_ACCOUNT_SID`, and `TWILIO_AUTH_TOKEN` are all set. Without the account SID there is no way to speak a fallback, so the call stays on Gather. The stream URL has no token. TwiML passes a one-time HMAC in `<Parameter name="token">`, and the socket reads it from the start message `customParameters`. A replay is rejected. `DEMO_MODE=0` rejects a start message with no token. A speech or TTS error updates the live call with `<Say>` and `<Redirect>` back to Gather so intake continues. If that turn is already an emergency, the update is `<Dial>`, not `<Hangup>`. The stream flushes a turn on trailing silence. Until those keys exist, Gather remains the answering path.

**Twilio signature checks are disabled when `TWILIO_AUTH_TOKEN` is empty.** Startup logs that warning in those words. Demo mode then accepts unsigned local requests so the browser simulator works. Do not point a public Twilio number at that process. `DEMO_MODE=0` will not start a call without the token: voice webhooks and the media-stream socket return 503, `/api/health` sets `voice_ready` false and explains why, and an empty token does not make an unsigned webhook valid. The process itself stays up so the board can still sign in.

`/api/health` reports `classifier`, `understander`, `understand_ready`, `semantic_ready`, `nli_ready`, and `degraded`. `ok` is true when MiniLM and the zero-shot model loaded. It does not require an instruct file. With those weights baked into the image and `HF_HUB_OFFLINE=1`, compose is healthy with no network and no API key. If a required hazard model is missing, seeding is skipped, the process still starts, and `/api/health` returns 503. That is true with the default `SEED_ON_START=1`. In that degraded mode a gas smell still pages, and an ordinary drain call is not paged after the address.

## What was measured

`python -m evals.fresh` scores a frozen set of 112 sentences written for this desk before the margin was tuned. It is the local detector, not Claude, and not a reviewer's caller list. The private caller list was not copied and was not re-run.

The first score, before tuning the margin, the concept picker, or the prototypes:

| | Before tuning |
| --- | ---: |
| Frozen lines | 112 |
| Emergency recall | 34 / 36 |
| CO-battery advice | 6 / 8 |
| Routine lines kept routine | 67 / 68 |
| Routine false escalations | 1 / 68 |

Those five misses were a Chinese gas-odor line, a German flooded-basement line (the fold step had stripped the umlaut before the embedder), two carbon-monoxide battery lines the embedder raised from advice to ask, and "I only have an emergency fund question, not a leak," which the rules treated as an emergency. None of those sentences were deleted.

After that, the embedder keeps the original text, the closest concept wins rather than the widest margin, a battery chirp is not upgraded, "emergency fund" is not a page, and a few Chinese gas prototypes were added. They are not the frozen sentence. Second score:

| | After tuning |
| --- | ---: |
| Frozen lines | 112 |
| Emergency recall | 36 / 36 |
| CO-battery advice | 8 / 8 |
| Routine lines kept routine | 68 / 68 |
| Routine false escalations | 0 / 68 |

That second score is this desk's own set. It is not a claim about any private caller list.

`python -m evals.heldout` scores `evals/heldout_set.py`. It was written before the round-5 rules. The rules were then changed while looking at its misses, so the second table is a development score, not a held-out score. The only held-out figure for this file is the first table. The sentences were not edited.

| | Held-out, before the round-5 rules |
| --- | ---: |
| Lines | 97 |
| Emergency recall | 28 / 48 |
| Safety-question lines | 1 / 8 |
| CO-battery advice | 4 / 5 |
| Routine lines kept routine | 31 / 36 |
| Routine false pages | 3 / 36 |

| | Development set, after those rules |
| --- | ---: |
| Lines | 97 |
| Emergency recall | 48 / 48 |
| Safety-question lines | 7 / 8 |
| CO-battery advice | 5 / 5 |
| Routine lines kept routine | 36 / 36 |
| Routine false pages | 0 / 36 |

The safety-question miss on that development file is "Possibly a gas smell, or maybe it is just the trash." A test locks the behavior that a gas smell pages, including when the caller hedges. One unit test covers one after-hours rate sentence. That test does not prove that rate questions in general stay off the on-call line.

`python -m evals.unseen` scores `evals/unseen_set.py`, 58 lines written and scored before the round-6 class rules, then left unchanged. The first score is the held-out number. The second score is the same file after the rules. It is not an external review.

| | Held-out, before the round-6 rules |
| --- | ---: |
| Lines | 58 |
| Emergency recall | 17 / 36 |
| Safety-question lines | 2 / 3 |
| CO-battery advice | 1 / 1 |
| Routine lines kept routine | 17 / 18 |
| Routine false pages | 1 / 18 |

| | Same file, after the round-6 rules |
| --- | ---: |
| Lines | 58 |
| Emergency recall | 36 / 36 |
| Safety-question lines | 3 / 3 |
| CO-battery advice | 1 / 1 |
| Routine lines kept routine | 18 / 18 |
| Routine false pages | 0 / 18 |

An external review of an earlier build measured about two-thirds strict recall on its own unseen English paraphrases. A sealed review after that measured about 74% strict recall. This repo does not re-run those lists. 36/36 above is not either number.

`python -m evals.round7` scores `evals/round7_set.py`, 59 lines written and scored before the round-7 changes, then left unchanged. The first score is the held-out number. The second score is the same file after the rules and the zero-shot model. It is not an external review, and it is not a sealed caller list.

| | Held-out, before the round-7 changes |
| --- | ---: |
| Lines | 59 |
| Emergency recall | 18 / 35 |
| Safety-question lines | 4 / 4 |
| Routine lines kept routine | 17 / 20 |
| Routine false pages | 1 / 20 |

| | Same file, after the round-7 changes |
| --- | ---: |
| Lines | 59 |
| Emergency recall | 35 / 35 |
| Safety-question lines | 4 / 4 |
| Routine lines kept routine | 20 / 20 |
| Routine false pages | 0 / 20 |

A date past the booking horizon is named and is not booked as today. A missing hazard model returns 503 with `semantic_ready` false, and a missing zero-shot model returns 503 with `nli_ready` false, while `SEED_ON_START` stays on. The private caller list was not copied and was not re-run. Live Claude was not called.

`python -m evals.round8` scores `evals/round8_set.py`, 64 lines written and scored before the round-8 changes, then left unchanged. The first score is the held-out number for this file. The second score is the same file after the clause rules and the natural-no policy. It is not an external review, and it is not the sealed caller list from that review.

| | Held-out, before the round-8 changes |
| --- | ---: |
| Lines | 64 |
| Emergency recall | 15 / 36 |
| Safety-question lines | 1 / 6 |
| Routine lines kept routine | 19 / 22 |
| Routine false pages | 2 / 22 |
| Natural-no clears | 0 / 27 |
| Harm still pages | 10 / 10 |

| | Same file, after the round-8 changes |
| --- | ---: |
| Lines | 64 |
| Emergency recall | 36 / 36 |
| Safety-question lines | 6 / 6 |
| Routine lines kept routine | 22 / 22 |
| Routine false pages | 0 / 22 |
| Natural-no clears | 27 / 27 |
| Harm still pages | 10 / 10 |

36/36 is this file. It is not the sealed set from the review of `584496e`, which scored 5.0. On that reviewer's fresh set, first-turn recall was 19/35, false pages were 9/22, and bookings were 10/13. A later sealed review of `ab984aa` scored 5.5: first-turn recall 24/35 on both the local model and the keyword screen, false pages 6/22 and 5/22, bookings 12/13. Earlier sealed reviews measured about two-thirds and about 74% strict recall. This repo does not re-run those lists, and it does not claim those numbers moved.

`python -m evals.round9` scores `evals/round9_set.py`, 39 lines plus 21 safety answers, written and hashed before the round-9 keyword changes, then left unchanged. The hash is the sha256 of the labeled lines, not the docstring: `dc04696d30d4b3a32aa7647af126b05c77f602fd0500aa67693de250c3072934`. The first score is this file before those rules. The second score is the same file after them. It is the dev-set number. It is not the sealed review of `ab984aa`.

| | This file, before the round-9 rules |
| --- | ---: |
| Lines | 39 |
| Emergency recall | 11 / 25 |
| Routine lines kept routine | 12 / 14 |
| Routine false pages | 2 / 14 |
| Safety clears | 4 / 6 |
| Safety pages | 15 / 15 |

| | Same file, after the round-9 rules |
| --- | ---: |
| Lines | 39 |
| Emergency recall | 25 / 25 |
| Routine lines kept routine | 14 / 14 |
| Routine false pages | 0 / 14 |
| Safety clears | 6 / 6 |
| Safety pages | 15 / 15 |

That after score is the keyword screen only. Live Claude was not called, so there is no Claude column. The local 1.5B model is not on this path.

Live Claude was not called. There is no live tool-mode column. `follow_rules` is not in `TOOL_SPECS`.

`backend/tests/heldout_callers.py` is the copied v1 review set plus paraphrases from an earlier round (72 scripted cases). The rules engine still passes it. That file is not a generalization score, and it is not scored as tool mode.

Scripted guard tests, still without a live model, drop free-form text (a made-up afternoon, a made-up price, a discount, a "booked" claim). A cooperative script books only across two turns: the caller states the name, phone, and address and picks a window, then says yes to the read-back. An invented name or phone is not stored. "No" and a hedge do not book. An invented slot does not. A model-initiated `transfer` or `classify_hazard` on a faucet quote does not page. Cancel verification is stored on the booking. Three failures lock that booking, text the number on it when SMS is actually sent, and do not page on-call or read the emergency script. A later call with the right day is still refused. Separate tests cover accented names, Suite versus Apt, "ends in" and "at the end" phone corrections, a house-number correction read back at the offer, "ten-thirty," "the Tuesday after next," "afternoon except Friday," a date past the horizon, "first Monday in November," Halloween morning, "next week except Monday," and "half past" / "4ish."

Pytest collects 203 tests. None of them call Anthropic. The keyless path does not load a local instruct model.

## Screenshots

![Dispatch board with call volume, bookings, and escalations](docs/screenshots/dashboard.png)

![Call simulator mid-conversation, ticket filling in](docs/screenshots/simulator_mid_call.png)

![Booking confirmation. The visit is on the board and no text was sent](docs/screenshots/booking_confirmation.png)

![Gas-smell call transferred to the on-call technician](docs/screenshots/escalation.png)

![Booked jobs on the week calendar](docs/screenshots/calendar.png)

![CRM webhook payload for GoHighLevel, HubSpot, or Zapier](docs/screenshots/crm_webhooks.png)

The board’s CRM handoff, then the webhook log on the Leads page:

![Walkthrough of the board and CRM webhook](docs/screenshots/walkthrough.gif)

## Run it

Compose publishes `127.0.0.1:43123` and defaults to `DEMO_MODE=0`. Inside the container, uvicorn binds `0.0.0.0` so that published port can reach it. `ADMIN_TOKEN`, Twilio settings, `PUBLIC_BASE_URL`, and `ANTHROPIC_API_KEY` are passed through when they are set in the environment. The image copies `evals/`, installs pytest, and downloads MiniLM and the zero-shot model into `/app/models` during the build, before `HF_HUB_OFFLINE=1`. It does not download an instruct model. The database is the named volume `receptionist_data`, not a bind mount of `./data`. An older compose file bind-mounted `./data`, and a root-owned `data/receptionist.db` left from that mount makes host pytest fail to open the database. Delete that file or `chown` it back to your user. The default host path is `data/receptionist.db` (`DATABASE_PATH`). With `DEMO_MODE=0` and an empty `TWILIO_AUTH_TOKEN`, the process still starts, logs that Twilio signature checks are disabled, and the board can sign in, but voice routes return 503 until the token is set. Demo mode is opt-in:

```bash
DEMO_MODE=1 docker compose up --build
```

Or without Docker. `start.sh` creates `.venv`, installs the app and pytest, runs `scripts/fetch_models.py` so a fresh clone downloads MiniLM and the zero-shot model, builds the frontend, and binds `127.0.0.1:43123` with `DEMO_MODE=1`. An empty `TWILIO_AUTH_TOKEN` logs that signature checks are disabled. That is expected for the local demo and is not safe on a public number.

```bash
./start.sh
```

Open [http://127.0.0.1:43123](http://127.0.0.1:43123). The board is seeded with sample calls. The **Call simulator** is the live demo: step through “Book a drain call,” or play “Gas smell” to see the transfer.

Tests, with no API key:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/python -m evals.fresh
```

`python -m evals.live_claude` exits 2 until `ANTHROPIC_API_KEY` is set. It is not part of pytest.

`requirements.txt` is the runtime image. Pytest lives in `requirements-dev.txt`. The image installs both and sets `PYTHONPATH=/app/backend:/app` so `pytest` can import the app and `evals`. Build once so the MiniLM weights are in the image, then run the suite with the network off. This Compose release does not accept `--network` on `compose run`, so the offline run uses the image directly:

```bash
docker compose build
docker run --rm --network none \
  -e HF_HUB_OFFLINE=1 \
  -e FASTEMBED_CACHE_PATH=/app/models \
  workspace-receptionist pytest -q
```

`docker compose up` stays on the default network so Twilio can reach the process later. It loads MiniLM and the zero-shot model from the baked weights (`HF_HUB_OFFLINE=1`). The healthcheck stays red until those two models are ready. It does not wait on an instruct file. Compose itself does not accept `--network` on `compose run`.

## Put it on a real phone number

1. Deploy the container on a host with a public HTTPS URL. The process listens on `0.0.0.0:43123`. Compose publishes `127.0.0.1:43123` on the host; change that binding when the host should accept traffic from Twilio.
2. Keep `DEMO_MODE=0` and set a long `ADMIN_TOKEN`. The board sends `Authorization: Bearer`. Demo reset stays closed. Twilio webhooks stay open so the carrier can post. The sign-in screen loads calls and leads. The simulator stays off unless demo mode is on.
3. Set `PUBLIC_BASE_URL` to that origin, including any path prefix. Signature checks use the full URL with the query string. The Media Stream URL does not carry the token. TwiML puts a single-use HMAC in `<Parameter name="token">`.
4. In Twilio, buy a number and set the voice webhook to `POST https://desk.example.com/api/voice/twilio/incoming`.
5. Set `TWILIO_AUTH_TOKEN`. With `DEMO_MODE=0`, voice routes refuse to start without it and an unsigned webhook is rejected. An empty token is not treated as valid. Demo mode is the only path that accepts unsigned local requests.
6. Set `TWILIO_ACCOUNT_SID` as well if Media Streams should update the live call with `<Dial>` when a transfer is required. Set `TWILIO_FROM_NUMBER` too if a real SMS should be sent. Without it, the desk logs the body and says no text was sent.
7. Optional: `ANTHROPIC_API_KEY`. The model defaults to `claude-sonnet-5-5`. Override with `ANTHROPIC_MODEL` only if you have confirmed the id against Anthropic’s current model list. Run `python -m evals.live_claude` yourself. This repo does not ship a live score.
8. Optional: `DEEPGRAM_API_KEY` and `ELEVENLABS_API_KEY` for Media Streams. `voice.mode` in the YAML can force `gather` or `stream`. Stream mode stays on Gather until both keys exist.
9. Set `crm.webhook_url` in `config/business.yaml` to a CRM webhook. GoHighLevel, HubSpot, and Zapier all accept this JSON. Set `WEBHOOK_SECRET` to sign the body as `X-Receptionist-Signature`. Until a URL is set, payloads are logged on the Leads page with status `mock`.

A burst pipe or gas smell returns TwiML that dials `escalation.on_call_phone` after Riley tells the caller who is picking up, and quotes the $179 emergency dispatch fee. Optional `escalation.on_call_phone_2` is dialed once if the first number does not answer. If the dial fails, the caller hears guidance for that hazard (gas, carbon monoxide, water, or electrical) and that someone will call back. If SMS was sent, Riley also says the on-call tech is being paged. If SMS was not sent, Riley says no text was sent. A verification lockout never uses this script.

## Configuration

`config/business.yaml` is the shop. Edit the name, agent name, hours (`sunday: null` means closed), ZIP codes, price rules, and the on-call contact. Restart the process. The simulator, the tests, and the phone webhook all read that file.

Environment variables are listed in `.env.example`. None are required for the local demo. `start.sh` defaults `DEMO_MODE` to on. Docker defaults it to off. `CORS_ORIGINS` defaults to the local board, not `*`. Request bodies over 100 KB are rejected. Calls and leads are kept 30 days (`RETENTION_DAYS`), then purged on startup and once a day.

## Project layout

- `backend/app/agent` — hazard concepts, MiniLM margin scorer, offline zero-shot NLI, the JSON understander, template speech, calendar, rules engine, and the tool dialog
- `backend/app/llm` — Claude client and the scripted stand-in used in tests
- `backend/app/voice` — Twilio signature check, Gather, dial fallback, single-use stream token
- `backend/app/integrations.py` — Deepgram, ElevenLabs, Twilio SMS, and the signed CRM POST
- `backend/tests` — scenarios, the copied v1 review file, and guard tests
- `evals/fresh_set.py` — the frozen 112 lines written for this desk before tuning
- `evals/heldout_set.py` — 97 lines. 28/48 is the held-out score. 48/48 is the development score after the rules
- `evals/unseen_set.py` — 58 lines written before the round-6 rules. 17/36 was the held-out score
- `evals/round7_set.py` — 59 lines written before the round-7 changes. 18/35 was the held-out score. 35/35 is the same file after those changes
- `evals/round8_set.py` — 64 lines written before the round-8 changes. 15/36 was the held-out score. 36/36 is the same file after those changes
- `evals/round9_set.py` — 39 lines plus 21 safety answers, hashed before the round-9 rules. 11/25 was the before score. 25/25 is the same file after those rules. The hash is `dc04696d30d4b3a32aa7647af126b05c77f602fd0500aa67693de250c3072934`
- `scripts/fetch_models.py` — downloads MiniLM and the zero-shot model
- `evals/live_claude.py` — opt-in live probe
- `frontend` — dispatch board and call simulator
- `config/business.yaml` — the sample plumbing and HVAC shop

## Suggested portfolio line

**Title:** AI Receptionist that answers, qualifies, and books plumbing and HVAC calls

**Description:** Missed calls are lost jobs. This receptionist picks up for a plumbing and HVAC shop, qualifies the caller, and books a real window on the shop calendar. With no API key the hazard screen is the keyword rules plus MiniLM, and a turn stays under a few milliseconds. It flags common hazard phrasing and hands the call to on-call. Booking is English only; other languages get a hazard check and a callback. A confirmation text goes out only when Twilio SMS accepts it. It demos in the browser with no API keys. With an Anthropic key, Claude can raise a hazard and can choose an empathy id and tools; that live path has not been scored. Caller-facing words come from server templates. The same webhook answers a Twilio number when you are ready.

**Tags:** AI Voice Agents, Twilio, Python, FastAPI, CRM Automation
