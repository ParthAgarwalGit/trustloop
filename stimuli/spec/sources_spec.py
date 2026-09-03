"""
The simulated web: real, visitable, instrumented source pages.

WHY THIS EXISTS
---------------
The agent must cite sources the participant can actually open and check. Those
sources cannot be real external sites: the study's ground truth is the exact
specification of each catalogue item, and a live retail page changes its prices and
specs without warning. Within days a "clean" trial would silently become an error
trial, a participant who found a discrepancy could not tell whether the agent lied or
the page updated, and nobody could replicate the study later.

So we host the web ourselves. Every URL below resolves to a real page in the app,
frozen and under our control -- and because we serve it, we can record exactly which
sources were opened, how long they were read, how far they were scrolled, and whether
the participant ever reached the section containing the disputed fact. An external
link would give us a click and nothing after it.

Three source types, mirroring how people actually check a purchase:
  * retailer product page  -- authoritative specs, price, customer reviews
  * editorial review site  -- prose evaluation, pros/cons, verdict
  * community forum thread -- unstructured opinion, the least reliable source

CRITICAL INVARIANT
------------------
Source pages carry the TRUTH, always. The agent's prose is what may be wrong. That
asymmetry is the whole experiment: verification means noticing that what the agent
said does not match what the source says.
"""
from __future__ import annotations

import hashlib

# Domains for the simulated web. These are display strings; the app serves them as
# in-origin routes (see app/src/mockweb/), so they are genuinely reachable.
SHOP_DOMAIN = "vantage.shop"
REVIEW_DOMAIN = "techbench.review"
FORUM_DOMAIN = "gearloop.forum"

SHOP_NAME = "Vantage"
REVIEW_NAME = "TechBench"
FORUM_NAME = "GearLoop"


def _rng(seed_text: str) -> "list[int]":
    """Deterministic pseudo-random stream from a string, so content is stable."""
    digest = hashlib.sha256(seed_text.encode()).digest()
    return [b for b in digest]


def _pick(options: list, seed_text: str, salt: int = 0) -> object:
    stream = _rng(seed_text)
    return options[stream[salt % len(stream)] % len(options)]


def slug(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace(".", "")
        .replace("--", "-")
    )


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------

def shop_url(item: dict) -> str:
    return f"{SHOP_DOMAIN}/p/{slug(item['name'])}"


def shop_reviews_url(item: dict) -> str:
    return f"{shop_url(item)}#reviews"


def shop_specs_url(item: dict) -> str:
    return f"{shop_url(item)}#specifications"


def review_url(item: dict) -> str:
    kind = "laptops" if item["domain"] == "laptop" else "travel"
    return f"{REVIEW_DOMAIN}/{kind}/{slug(item['name'])}"


def forum_url(item: dict) -> str:
    return f"{FORUM_DOMAIN}/t/{slug(item['name'])}-owners-thread"


# ---------------------------------------------------------------------------
# Review authors and prose fragments
# ---------------------------------------------------------------------------

REVIEWER_NAMES = [
    "M. Okonkwo", "S. Baraniuk", "J. Whitfield", "A. Ferreira", "T. Nakamura",
    "R. Delacroix", "K. Andersen", "P. Silvestri", "L. Hammersley", "D. Vasquez",
    "N. Bergstrom", "C. Iwuchukwu",
]

CUSTOMER_HANDLES = [
    "quietkeyboard", "mreid_88", "not_a_reviewer", "tessellate", "hollowpoint",
    "grumbleweed", "aviva.r", "thirdcoast", "penny_dreadful", "oakfield",
    "sunkcost", "mildlyannoyed", "brackish", "wentworth_j", "clatter",
]

REVIEW_DATES = [
    "12 March 2026", "3 April 2026", "27 February 2026", "18 January 2026",
    "9 May 2026", "22 December 2025", "14 June 2026", "30 April 2026",
    "7 February 2026", "19 March 2026",
]

# Each entry carries BOTH a standalone sentence (for a customer review, where
# first-person voice is right) and a noun phrase (for embedding mid-sentence in the
# agent's prose, where a first-person fragment like "Coil whine on mine" would read
# as a splice). Keeping them paired stops the two registers being mixed up.
LAPTOP_PRAISE = [
    {"s": "The keyboard is genuinely excellent — long travel, no flex in the deck.",
     "n": "the keyboard"},
    {"s": "Build quality is a clear step above what I expected at this price.",
     "n": "the build quality"},
    {"s": "Runs completely silent under normal office load. Fans only spin up when compiling.",
     "n": "how quietly it runs"},
    {"s": "The display is bright enough to use next to a window, which was my main worry.",
     "n": "display brightness"},
    {"s": "Battery has comfortably survived a full working day for me.",
     "n": "real-world battery life"},
    {"s": "Trackpad is large and the palm rejection actually works.",
     "n": "the trackpad"},
    {"s": "Boots fast and has stayed fast after four months of daily use.",
     "n": "how well it has held up over time"},
]

LAPTOP_GRIPES = [
    {"s": "The webcam is mediocre. Fine for calls, not much else.",
     "n": "a mediocre webcam"},
    {"s": "Only two USB-C ports, so I'm living with a dongle.",
     "n": "a thin port selection"},
    {"s": "Speakers are thin — you'll want headphones for anything but calls.",
     "n": "weak speakers"},
    {"s": "It picks up fingerprints immediately if you get the darker finish.",
     "n": "a finish that shows fingerprints"},
    {"s": "The charger is bulkier than it needs to be.",
     "n": "an unnecessarily bulky charger"},
    {"s": "Coil whine on mine, though support says it's not typical.",
     "n": "occasional coil whine"},
    {"s": "Hinge has a little wobble when you tap the screen.",
     "n": "a slightly loose hinge"},
]

TRIP_PRAISE = [
    {"s": "Location was the selling point — walkable to almost everything we wanted.",
     "n": "the location"},
    {"s": "Staff went out of their way when our flight landed late.",
     "n": "the staff"},
    {"s": "Room was quiet despite being on the street side.",
     "n": "how quiet the rooms are"},
    {"s": "Breakfast was better than we expected for the price.",
     "n": "the breakfast"},
    {"s": "Check-in was quick and the bags were held for us after checkout.",
     "n": "the check-in process"},
    {"s": "The neighbourhood felt safe walking back in the evening.",
     "n": "the neighbourhood"},
]

TRIP_GRIPES = [
    {"s": "The lift is tiny and there were stairs to the first landing with luggage.",
     "n": "awkward access with luggage"},
    {"s": "Walls are thin — we could hear the corridor.",
     "n": "thin walls"},
    {"s": "Wi-Fi dropped out a few times in the room.",
     "n": "unreliable Wi-Fi"},
    {"s": "Bathroom was clean but very small.",
     "n": "a cramped bathroom"},
    {"s": "No air conditioning in the room we had, which mattered in the afternoon.",
     "n": "the lack of air conditioning"},
    {"s": "Street noise until about eleven at night.",
     "n": "evening street noise"},
]


def customer_reviews(item: dict, n: int = 5) -> list[dict]:
    """
    Deterministic customer reviews for a product page.

    Ratings are generated to average close to the catalogue's `rating` field so the
    page is internally consistent with the spec table -- an inconsistency here would
    be an unintended cue.
    """
    praise = LAPTOP_PRAISE if item["domain"] == "laptop" else TRIP_PRAISE
    gripes = LAPTOP_GRIPES if item["domain"] == "laptop" else TRIP_GRIPES
    target = float(item.get("rating") or item.get("hotel_rating") or 4.2)

    stream = _rng(item["id"] + "reviews")
    out = []
    # Distribute ratings around the target: mostly at/above, one or two below.
    offsets = [0, 1, 0, -1, 0, 1, -2, 0]
    for i in range(n):
        raw = target + offsets[i % len(offsets)] * 0.5
        stars = max(1, min(5, round(raw)))
        pos = praise[stream[(i * 3) % len(stream)] % len(praise)]["s"]
        neg = gripes[stream[(i * 3 + 1) % len(stream)] % len(gripes)]["s"]
        body = pos if stars >= 4 else f"{neg} Otherwise it's fine."
        if stars == 4:
            body = f"{pos} {neg}"
        out.append({
            "handle": CUSTOMER_HANDLES[stream[(i * 5) % len(stream)] % len(CUSTOMER_HANDLES)],
            "stars": stars,
            "date": REVIEW_DATES[stream[(i * 7) % len(stream)] % len(REVIEW_DATES)],
            "body": body,
            "verified": stream[(i * 11) % len(stream)] % 4 != 0,
        })
    return out


def editorial_review(item: dict) -> dict:
    """A third-party editorial review. Prose only -- the spec table is the truth."""
    praise = LAPTOP_PRAISE if item["domain"] == "laptop" else TRIP_PRAISE
    gripes = LAPTOP_GRIPES if item["domain"] == "laptop" else TRIP_GRIPES
    stream = _rng(item["id"] + "editorial")

    if item["domain"] == "laptop":
        verdict_options = [
            f"The {item['name']} is a sensible, unflashy choice that gets the "
            "fundamentals right without asking you to pay for features you probably "
            "won't use.",
            f"There is nothing exotic about the {item['name']}, and that is largely "
            "the point. It is a competent machine at a competitive price.",
            f"The {item['name']} makes a strong case on value, provided its "
            "particular set of compromises happens to line up with your priorities.",
        ]
        body = (
            f"We spent two weeks with the {item['name']} as a primary work machine. "
            f"At ${item['price']}, it sits in the most crowded part of the market, "
            "which means the details decide it.\n\n"
            f"{praise[stream[0] % len(praise)]['s']} "
            f"{praise[stream[1] % len(praise)]['s']}\n\n"
            f"It is not without compromises. {gripes[stream[2] % len(gripes)]['s']} "
            f"{gripes[stream[3] % len(gripes)]['s']}\n\n"
            "Full specifications are listed below. As always, we verify every figure "
            "against the manufacturer's published sheet rather than the retailer's "
            "listing, which is not always the same thing."
        )
    else:
        verdict_options = [
            f"A dependable, well-located option that does the basics properly.",
            f"Good value for the location, with the usual caveats about older buildings.",
            f"Worth booking if the location suits you; less compelling otherwise.",
        ]
        body = (
            f"We stayed three nights at the {item['name'].split(' - ')[-1]} "
            "and assessed it against comparable options in the same price band.\n\n"
            f"{praise[stream[0] % len(praise)]['s']} "
            f"{praise[stream[1] % len(praise)]['s']}\n\n"
            f"Points against: {gripes[stream[2] % len(gripes)]['n']}, and "
            f"{gripes[stream[3] % len(gripes)]['n']}.\n\n"
            "Costs below are per the operator's published rates at time of writing."
        )

    return {
        "author": REVIEWER_NAMES[stream[4] % len(REVIEWER_NAMES)],
        "date": REVIEW_DATES[stream[5] % len(REVIEW_DATES)],
        "score": round(min(10.0, max(5.5, (float(item.get("rating") or item.get("hotel_rating") or 4.2)) * 2 + (stream[6] % 5 - 2) * 0.1)), 1),
        "verdict": verdict_options[stream[7] % len(verdict_options)],
        "body": body,
        # Sentence form for standalone use; noun form for mid-sentence embedding.
        "pros": [praise[stream[8] % len(praise)]["s"], praise[stream[9] % len(praise)]["s"]],
        "cons": [gripes[stream[10] % len(gripes)]["s"], gripes[stream[11] % len(gripes)]["s"]],
        "prosNoun": [praise[stream[8] % len(praise)]["n"], praise[stream[9] % len(praise)]["n"]],
        "consNoun": [gripes[stream[10] % len(gripes)]["n"], gripes[stream[11] % len(gripes)]["n"]],
    }


FORUM_OPENERS = [
    "Anyone actually using one of these day to day? Spec sheet looks fine but "
    "spec sheets always do.",
    "About to pull the trigger on this. Talk me out of it.",
    "Been running one for a few months, happy to answer questions.",
    "Cross-shopping this against a couple of others. What am I missing?",
]

FORUM_REPLIES = [
    "Had mine since launch. No complaints worth writing home about.",
    "Check the exact configuration before you buy — the listings vary and not "
    "every retailer is careful about which one they show you.",
    "Mine's been solid. The one thing I'd say is don't trust the marketing copy, "
    "look at the actual spec sheet.",
    "It's fine. Not exciting, but fine.",
    "I returned mine, but for reasons specific to my setup. Wouldn't generalise.",
    "Whatever you do, compare the real numbers rather than the summary. I got "
    "caught out by that once.",
    "Solid for the money. There are better machines, but not at this price.",
]


def forum_thread(item: dict) -> dict:
    stream = _rng(item["id"] + "forum")
    posts = [{
        "handle": CUSTOMER_HANDLES[stream[0] % len(CUSTOMER_HANDLES)],
        "date": REVIEW_DATES[stream[1] % len(REVIEW_DATES)],
        "body": FORUM_OPENERS[stream[2] % len(FORUM_OPENERS)],
        "op": True,
    }]
    for i in range(4):
        posts.append({
            "handle": CUSTOMER_HANDLES[stream[(i * 3 + 5) % len(stream)] % len(CUSTOMER_HANDLES)],
            "date": REVIEW_DATES[stream[(i * 3 + 6) % len(stream)] % len(REVIEW_DATES)],
            "body": FORUM_REPLIES[stream[(i * 3 + 7) % len(stream)] % len(FORUM_REPLIES)],
            "op": False,
        })
    return {"title": f"{item['name']} — owners thread", "posts": posts}


def build_sources(catalog: dict) -> dict:
    """Build every source page for every catalogue item."""
    pages = {}
    for iid, item in catalog.items():
        pages[iid] = {
            "shop": {
                "url": shop_url(item),
                "domain": SHOP_DOMAIN,
                "siteName": SHOP_NAME,
                "reviews": customer_reviews(item),
            },
            "review": {
                "url": review_url(item),
                "domain": REVIEW_DOMAIN,
                "siteName": REVIEW_NAME,
                **editorial_review(item),
            },
            "forum": {
                "url": forum_url(item),
                "domain": FORUM_DOMAIN,
                "siteName": FORUM_NAME,
                **forum_thread(item),
            },
        }
    return pages
