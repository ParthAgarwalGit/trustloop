"""
TrustLoop stimulus specification.

This file is the SINGLE SOURCE OF TRUTH for experimental content. Everything the
participant sees is derived from here by `stimuli/build_trials.py`.

Design invariants (enforced by `stimuli/validate_trials.py`):
  I1. Ground truth is COMPUTED from the catalog, never hand-asserted. A trial is an
      "error trial" iff the agent's recommended item actually fails >=1 constraint,
      or the agent states a total price that differs from the true total.
  I2. Tone (honest vs sycophantic) is content-independent. The agent's hedging
      register must NOT correlate with whether a trial is seeded, or tone would
      leak ground truth and confound H3/H4.
  I3. Every constraint is checkable against a concrete catalog field, so the
      `full` disclosure condition can show claim-vs-catalog side by side.
  I4. Every trial has >=1 genuinely compliant alternative in its candidate set, so
      "override" is always a rational option available to the participant.

Edit this file to change stimuli, then run:
    python stimuli/build_trials.py && python stimuli/validate_trials.py
"""

# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------
# Fields are deliberately concrete and machine-checkable. `label` and `unit` drive
# the evidence panel rendering in the app.

FIELD_META = {
    "price":         {"label": "Price",           "unit": "$",     "kind": "currency"},
    "ram_gb":        {"label": "RAM",             "unit": " GB",   "kind": "number"},
    "storage_gb":    {"label": "Storage",         "unit": " GB",   "kind": "number"},
    "weight_kg":     {"label": "Weight",          "unit": " kg",   "kind": "number"},
    "battery_hours": {"label": "Battery life",    "unit": " h",    "kind": "number"},
    "screen_in":     {"label": "Screen",          "unit": '"',     "kind": "number"},
    "rating":        {"label": "User rating",     "unit": "/5",    "kind": "number"},
    "total_price":   {"label": "Total price",     "unit": "$",     "kind": "currency"},
    "flight_price":  {"label": "Flight",          "unit": "$",     "kind": "currency"},
    "hotel_night":   {"label": "Hotel per night", "unit": "$",     "kind": "currency"},
    "nights":        {"label": "Nights",          "unit": "",      "kind": "number"},
    "hotel_rating":  {"label": "Hotel rating",    "unit": "/5",    "kind": "number"},
    "stops":         {"label": "Stops",           "unit": "",      "kind": "number"},
    "refundable":    {"label": "Refundable",      "unit": "",      "kind": "bool"},
}

LAPTOPS = [
    # id     name                      price ram store weight batt screen rating
    ("L01", "Aeris Slim 14",            829, 16,  512, 1.29, 11.5, 14.0, 4.4),
    ("L02", "Nimbus Pro 15",            899,  8,  512, 1.62,  9.0, 15.6, 4.2),
    ("L03", "Corvid Air 13",            749, 16,  256, 1.18, 12.0, 13.3, 4.3),
    ("L04", "Valta Book 14",            869, 16,  512, 1.71, 10.5, 14.0, 4.5),
    ("L05", "Meridian X1",              999, 32, 1024, 1.35, 13.0, 14.0, 4.7),
    ("L06", "Nimbus Air 13",            679,  8,  256, 1.21,  8.5, 13.3, 4.0),
    ("L07", "Aeris Ultra 14",           879, 16,  512, 1.31, 10.0, 14.0, 4.4),
    ("L08", "Kestrel Work 15",          789, 16,  256, 1.88,  7.5, 15.6, 4.1),
    ("L09", "Corvid Pro 14",            939, 16,  512, 1.44, 12.5, 14.0, 4.6),
    ("L10", "Valta Lite 13",            699, 12,  256, 1.24,  9.5, 13.3, 4.2),
    ("L11", "Meridian Go 13",           859, 16,  512, 1.09, 14.0, 13.3, 4.5),
    ("L12", "Kestrel Slim 14",          819,  8,  512, 1.33, 11.0, 14.0, 4.3),
    ("L13", "Aeris Book 15",            949, 16, 1024, 1.79, 10.0, 15.6, 4.4),
    ("L14", "Corvid Lite 13",           729, 16,  256, 1.52,  9.0, 13.3, 4.1),
    ("L15", "Nimbus Studio 14",         889, 16,  512, 1.26, 12.0, 14.0, 4.6),
    ("L16", "Valta Pro 15",             969, 32,  512, 1.68, 11.5, 15.6, 4.5),
    ("L17", "Kestrel Air 13",           759, 16,  256, 1.15,  8.0, 13.3, 4.0),
    ("L18", "Meridian Book 14",         839, 16,  512, 1.47, 13.5, 14.0, 4.4),
]

TRIPS = [
    # id     name                              flight hotel/night nights h.rating stops refundable
    ("T01", "Lisbon - Alfama Garden Hotel",      312,  118, 4, 4.4, 0, True),
    ("T02", "Lisbon - Baixa Central Inn",        312,   96, 4, 4.1, 1, False),
    ("T03", "Prague - Old Town Rezidence",       268,  104, 4, 4.5, 1, True),
    ("T04", "Prague - Vinohrady Suites",         268,   88, 4, 4.0, 0, False),
    ("T05", "Seville - Triana Riverside",        341,  126, 3, 4.6, 0, True),
    ("T06", "Seville - Macarena Boutique",       341,   99, 3, 4.2, 1, True),
    ("T07", "Krakow - Kazimierz House",          254,   79, 5, 4.3, 1, False),
    ("T08", "Krakow - Rynek Grand",              254,  132, 5, 4.7, 0, True),
    ("T09", "Porto - Ribeira Views",             298,  111, 4, 4.5, 0, True),
    ("T10", "Porto - Cedofeita Rooms",           298,   84, 4, 4.0, 1, False),
    ("T11", "Valencia - Ruzafa Loft",            325,   92, 3, 4.2, 0, True),
    ("T12", "Valencia - Marina Suites",          325,  138, 3, 4.6, 0, True),
]


def _build_catalog():
    items = {}
    for (iid, name, price, ram, store, wt, batt, screen, rating) in LAPTOPS:
        items[iid] = {
            "id": iid, "domain": "laptop", "name": name,
            "price": price, "ram_gb": ram, "storage_gb": store,
            "weight_kg": wt, "battery_hours": batt, "screen_in": screen,
            "rating": rating,
        }
    for (iid, name, flight, hotel, nights, hrating, stops, refundable) in TRIPS:
        items[iid] = {
            "id": iid, "domain": "trip", "name": name,
            "flight_price": flight, "hotel_night": hotel, "nights": nights,
            "total_price": flight + hotel * nights,
            "hotel_rating": hrating, "stops": stops, "refundable": refundable,
        }
    return items


CATALOG = _build_catalog()

# Which fields to show on the always-visible spec card, per domain.
# NOTE: the spec card is shown in ALL conditions. See docs/STIMULI_DESIGN.md for why
# (error detection must be *possible* in the opaque condition, or detection rate
# floors at zero for information-availability reasons rather than psychological ones).
SPEC_CARD_FIELDS = {
    "laptop": ["price", "ram_gb", "storage_gb", "weight_kg", "battery_hours", "rating"],
    "trip": ["total_price", "flight_price", "hotel_night", "nights", "hotel_rating", "stops"],
}


# ---------------------------------------------------------------------------
# Constraint helpers
# ---------------------------------------------------------------------------

def c(cid, field, op, value, label):
    return {"id": cid, "field": field, "op": op, "value": value, "label": label}


# ---------------------------------------------------------------------------
# Trials
# ---------------------------------------------------------------------------
# `slot` is the fixed presentation position (1-indexed). Error slots are 4, 7, 9 --
# never in the first three (learning) or the last (end-of-task fatigue).
#
# error_spec is None for honest trials. Otherwise:
#   {"type": "dropped_constraint"}  -> agent omits a constraint its pick violates
#   {"type": "false_claim", "field": <f>, "stated": <v>}
#                                   -> agent states a value contradicting the catalog
#   {"type": "arithmetic", "stated_total": <v>}
#                                   -> agent states a wrong total price
#
# `recommend` names the item the agent picks. The builder computes whether that pick
# actually satisfies every constraint; a mismatch between that and error_spec being
# None is a hard build failure.

TRIALS = [
    {
        "slot": 1, "id": "S01", "domain": "laptop",
        "prompt": "Find me a laptop under $900 with at least 16 GB of RAM and a user rating of 4.3 or higher.",
        "constraints": [
            c("c1", "price", "lt", 900, "Under $900"),
            c("c2", "ram_gb", "gte", 16, "At least 16 GB RAM"),
            c("c3", "rating", "gte", 4.3, "Rated 4.3 or higher"),
        ],
        "candidates": ["L01", "L02", "L12", "L06", "L14"],
        "recommend": "L01",
        "error_spec": None,
    },
    {
        "slot": 2, "id": "S02", "domain": "trip",
        "prompt": "Find me a trip package with a total price under $800, a hotel rated 4.0 or better, and a direct flight (no stops).",
        "constraints": [
            c("c1", "total_price", "lt", 800, "Total under $800"),
            c("c2", "hotel_rating", "gte", 4.0, "Hotel rated 4.0+"),
            c("c3", "stops", "eq", 0, "Direct flight"),
        ],
        "candidates": ["T04", "T02", "T11", "T07", "T10"],
        "recommend": "T11",
        "error_spec": None,
    },
    {
        "slot": 3, "id": "S03", "domain": "laptop",
        "prompt": "I need a laptop under $800 that weighs less than 1.3 kg and gets at least 8 hours of battery.",
        "constraints": [
            c("c1", "price", "lt", 800, "Under $800"),
            c("c2", "weight_kg", "lt", 1.3, "Lighter than 1.3 kg"),
            c("c3", "battery_hours", "gte", 8, "8+ hours battery"),
        ],
        "candidates": ["L03", "L08", "L17", "L14", "L06"],
        "recommend": "L03",
        "error_spec": None,
    },
    {
        # SEEDED ERROR 1 -- dropped constraint (weight). L04 is 1.71 kg, violates c3.
        "slot": 4, "id": "S04", "domain": "laptop",
        "prompt": "Find a laptop under $900 with at least 512 GB of storage that weighs under 1.5 kg.",
        "constraints": [
            c("c1", "price", "lt", 900, "Under $900"),
            c("c2", "storage_gb", "gte", 512, "512 GB+ storage"),
            c("c3", "weight_kg", "lt", 1.5, "Lighter than 1.5 kg"),
        ],
        "candidates": ["L04", "L07", "L15", "L13", "L12"],
        "recommend": "L04",
        "error_spec": {"type": "dropped_constraint"},
    },
    {
        "slot": 5, "id": "S05", "domain": "trip",
        "prompt": "I want a trip under $700 total with a refundable booking and a hotel rated at least 4.2.",
        "constraints": [
            c("c1", "total_price", "lt", 700, "Total under $700"),
            c("c2", "refundable", "eq", True, "Refundable"),
            c("c3", "hotel_rating", "gte", 4.2, "Hotel rated 4.2+"),
        ],
        "candidates": ["T03", "T06", "T07", "T10", "T04"],
        "recommend": "T03",
        "error_spec": None,
    },
    {
        "slot": 6, "id": "S06", "domain": "laptop",
        "prompt": "Find a laptop with 16 GB or more RAM, at least 10 hours of battery, and a price under $900.",
        "constraints": [
            c("c1", "ram_gb", "gte", 16, "16 GB+ RAM"),
            c("c2", "battery_hours", "gte", 10, "10+ hours battery"),
            c("c3", "price", "lt", 900, "Under $900"),
        ],
        "candidates": ["L15", "L05", "L11", "L08", "L10"],
        "recommend": "L15",
        "error_spec": None,
    },
    {
        # SEEDED ERROR 2 -- arithmetic. T08 true total = 254 + 132*5 = 914, over the
        # $850 cap. Agent states $794 (as if 4 nights), so its pick looks compliant.
        "slot": 7, "id": "S07", "domain": "trip",
        "prompt": "Find a trip package with a total price under $850 where the hotel is rated 4.5 or higher.",
        "constraints": [
            c("c1", "total_price", "lt", 850, "Total under $850"),
            c("c2", "hotel_rating", "gte", 4.5, "Hotel rated 4.5+"),
        ],
        "candidates": ["T08", "T03", "T09", "T05", "T12"],
        "recommend": "T08",
        "error_spec": {"type": "arithmetic", "stated_total": 794},
    },
    {
        "slot": 8, "id": "S08", "domain": "laptop",
        "prompt": "I need a laptop under $950 with at least 16 GB RAM and a screen of 14 inches or larger.",
        "constraints": [
            c("c1", "price", "lt", 950, "Under $950"),
            c("c2", "ram_gb", "gte", 16, "16 GB+ RAM"),
            c("c3", "screen_in", "gte", 14.0, '14" or larger screen'),
        ],
        "candidates": ["L09", "L12", "L17", "L03", "L10"],
        "recommend": "L09",
        "error_spec": None,
    },
    {
        # SEEDED ERROR 3 -- false claim. L12 has 8 GB RAM; agent states 16 GB.
        "slot": 9, "id": "S09", "domain": "laptop",
        "prompt": "Find a laptop under $850 with at least 16 GB of RAM and 512 GB of storage.",
        "constraints": [
            c("c1", "price", "lt", 850, "Under $850"),
            c("c2", "ram_gb", "gte", 16, "16 GB+ RAM"),
            c("c3", "storage_gb", "gte", 512, "512 GB+ storage"),
        ],
        "candidates": ["L12", "L01", "L18", "L06", "L14"],
        "recommend": "L12",
        "error_spec": {"type": "false_claim", "field": "ram_gb", "stated": 16},
    },
    {
        "slot": 10, "id": "S10", "domain": "trip",
        "prompt": "Find a trip under $750 total with a direct flight and a hotel rated 4.0 or better.",
        "constraints": [
            c("c1", "total_price", "lt", 750, "Total under $750"),
            c("c2", "stops", "eq", 0, "Direct flight"),
            c("c3", "hotel_rating", "gte", 4.0, "Hotel rated 4.0+"),
        ],
        "candidates": ["T04", "T11", "T02", "T10", "T07"],
        "recommend": "T04",
        "error_spec": None,
    },
]

# Slots at which a seeded error occurs. Asserted against TRIALS by the validator.
ERROR_SLOTS = [4, 7, 9]
