"""
Long-form agent response generation.

WHY THE OUTPUT IS LONG AND WHY IT DOES NOT HELP YOU CHECK IT
------------------------------------------------------------
An earlier version showed a tidy claim-by-claim table: "ShopBot reported 16 GB /
Catalogue record 8 GB", side by side. That made verification a single glance, which
is neither realistic nor measurable -- it tested whether someone clicked a disclosure
toggle, not whether they were willing to do the work of checking.

Real agent output is several hundred words of structured prose with inline citations.
The specification that matters is one clause inside a paragraph, among a dozen other
figures, and checking it means opening the cited page, finding the spec table and
reading the row yourself. That effort gradient is the construct we are trying to
measure, so the response is deliberately built to preserve it:

  * no pre-computed comparison between what the agent said and what the source says
  * the disputed figure is never visually distinguished from the undisputed ones
  * every candidate paragraph mentions several specifications, only some of which
    bear on the participant's stated requirements
  * citations point at pages, not at highlighted facts

WHAT THE ERROR TYPES LOOK LIKE IN LONG FORM
-------------------------------------------
  dropped_constraint -- the requirement is never addressed anywhere in the response
  false_claim        -- one figure in the prose contradicts the cited source page
  arithmetic         -- a stated total does not equal the components it is built from

INVARIANT: the agent is wrong about the WORLD, never about ITSELF. Every figure it
states must be consistent with its own conclusion, or a participant would catch the
error by noticing self-contradiction rather than by verifying against a source.

A NOTE ON PROSE QUALITY
-----------------------
Clumsy text is the fastest way to reveal that output is templated, which would
undermine the whole cover story. Two rules keep it clean:
  1. NEVER call .lower() or .capitalize() on assembled text -- .capitalize() in
     particular lowercases everything after the first character, turning "16 GB"
     into "16 gb". Write every fragment in the case it will be used in.
  2. Spec phrasings are VERB PHRASES ("lists at $819", "ships with 16 GB of memory")
     so they compose into a grammatical list after a single subject.
"""
from __future__ import annotations

import hashlib

import sources_spec as src


def _stream(seed: str) -> list[int]:
    return list(hashlib.sha256(seed.encode()).digest())


def _pick(options: list, seed: str, salt: int = 0):
    s = _stream(seed)
    return options[s[salt % len(s)] % len(options)]


def _sentence_case(text: str) -> str:
    """Upper-case the first character only. Never touches the rest (see rule 1)."""
    return text[:1].upper() + text[1:] if text else text


def _join_clauses(clauses: list[str]) -> str:
    """['lists at $819', 'ships with 16 GB'] -> 'lists at $819 and ships with 16 GB'"""
    if not clauses:
        return ""
    if len(clauses) == 1:
        return clauses[0]
    if len(clauses) == 2:
        return f"{clauses[0]} and {clauses[1]}"
    return ", ".join(clauses[:-1]) + f", and {clauses[-1]}"


# ---------------------------------------------------------------------------
# Tool-call trace (what the interface animates before the answer appears)
# ---------------------------------------------------------------------------

def build_tool_calls(trial: dict, catalog: dict, cited_items: list[str]) -> list[dict]:
    """
    The sequence of actions the agent appears to take.

    Durations are plausible rather than instant. The interface plays these back with
    real latency so the response feels produced rather than retrieved; see
    app/src/components/AgentStream.tsx.
    """
    domain_word = "laptops" if trial["domain"] == "laptop" else "trip packages"
    n_pool = 18 if trial["domain"] == "laptop" else 12
    calls: list[dict] = [
        {
            "kind": "search",
            "label": f"Searching {src.SHOP_NAME} for {domain_word}",
            "detail": f"{n_pool} listings matched",
            "url": f"{src.SHOP_DOMAIN}/search",
            "durationMs": 1500,
        },
        {
            "kind": "filter",
            "label": "Applying your requirements",
            "detail": ", ".join(c["label"] for c in trial["constraints"]),
            "durationMs": 900,
        },
    ]
    for iid in cited_items[:3]:
        item = catalog[iid]
        calls.append({
            "kind": "read",
            "label": f"Reading {item['name']} listing",
            "detail": src.SHOP_DOMAIN,
            "url": src.shop_url(item),
            "durationMs": 1300,
        })
    top = catalog[trial["recommend"]]
    calls.append({
        "kind": "read",
        "label": f"Reading {src.REVIEW_NAME} review",
        "detail": src.REVIEW_DOMAIN,
        "url": src.review_url(top),
        "durationMs": 1700,
    })
    calls.append({
        "kind": "read",
        "label": "Checking customer reviews",
        "detail": f"{len(src.customer_reviews(top))} recent reviews",
        "url": src.shop_reviews_url(top),
        "durationMs": 1200,
    })
    calls.append({
        "kind": "compare",
        "label": f"Comparing {len(trial['candidates'])} candidates",
        "detail": "against your stated requirements",
        "durationMs": 1600,
    })
    return calls


# ---------------------------------------------------------------------------
# Spec phrasing -- VERB PHRASES, so they compose after a subject pronoun
# ---------------------------------------------------------------------------

LAPTOP_PHRASINGS = {
    "price": ["lists at {v}", "comes in at {v}", "is priced at {v}"],
    "ram_gb": ["ships with {v} of memory", "has {v} of RAM", "comes with {v} of RAM"],
    "storage_gb": ["has {v} of storage", "includes a {v} SSD", "comes with {v} of storage"],
    "weight_kg": ["weighs {v}", "tips the scales at {v}", "comes in at {v}"],
    "battery_hours": ["is rated for {v} of battery", "gets around {v} on a charge",
                      "claims {v} of runtime"],
    "screen_in": ["has a {v} display", "uses a {v} panel"],
    "rating": ["averages {v} from customers", "holds a {v} customer rating"],
}

TRIP_PHRASINGS = {
    "total_price": ["comes to {v} in total", "works out at {v} all in", "totals {v}"],
    "flight_price": ["has flights at {v}", "puts the return flight at {v}"],
    "hotel_night": ["charges {v} a night", "runs {v} per night"],
    "nights": ["covers {v} nights", "runs for {v} nights"],
    "hotel_rating": ["scores {v} with guests", "holds a {v} guest rating"],
    "stops": ["has {v} stops", "flies with {v} stops"],
    "refundable": ["is refundable", "is non-refundable"],
}

CANDIDATE_OPENERS = [
    "This is the one I'd go with.",
    "This is my recommendation.",
    "This is where I landed.",
    "This is the strongest option of the set.",
]

RUNNER_UP_OPENERS = [
    "Worth a look if the recommendation doesn't suit.",
    "A reasonable second choice.",
    "Close, but it loses out on balance.",
    "Competitive, though not my pick.",
]

REJECT_OPENERS = [
    "I ruled this out.",
    "This didn't make the cut.",
    "I set this aside early.",
    "Not a fit for what you asked for.",
]


def _phrase(field: str, value_text: str, domain: str, seed: str) -> str:
    table = LAPTOP_PHRASINGS if domain == "laptop" else TRIP_PHRASINGS
    options = table.get(field)
    if not options:
        return f"has {field.replace('_', ' ')} of {value_text}"
    if field == "refundable":
        return options[0] if value_text == "Yes" else options[1]
    return _pick(options, seed + field).format(v=value_text)


# ---------------------------------------------------------------------------
# Response assembly
# ---------------------------------------------------------------------------

def build_response(
    trial: dict,
    catalog: dict,
    fmt_value,
    stated_value_for,
    mentioned_fields_for,
) -> dict:
    """
    Build the full long-form response.

    `stated_value_for(item_id, field) -> (value, is_false)` returns what the agent
    ASSERTS about a field, which differs from the catalogue only where an error is
    seeded. `mentioned_fields_for(item_id) -> list[str]` returns which fields the
    agent talks about for that item, with a dropped constraint's field absent.
    """
    rec_id = trial["recommend"]
    rec = catalog[rec_id]
    domain = trial["domain"]
    seed = trial["id"]
    price_field = "price" if domain == "laptop" else "total_price"

    others = [c for c in trial["candidates"] if c != rec_id]
    runner_up = others[0] if others else None
    rejects = others[1:3]

    citations: list[dict] = []

    def cite(item: dict, source_type: str) -> int:
        url = {
            "shop": src.shop_url(item),
            "reviews": src.shop_reviews_url(item),
            "review": src.review_url(item),
            "forum": src.forum_url(item),
        }[source_type]
        for c in citations:
            if c["url"] == url:
                return c["n"]
        n = len(citations) + 1
        citations.append({
            "n": n,
            "url": url,
            "itemId": item["id"],
            "sourceType": "shop" if source_type in ("shop", "reviews") else source_type,
            "anchor": "reviews" if source_type == "reviews" else None,
            "label": {
                "shop": f"{src.SHOP_NAME} — {item['name']}",
                "reviews": f"{src.SHOP_NAME} — customer reviews",
                "review": f"{src.REVIEW_NAME} — {item['name']}",
                "forum": f"{src.FORUM_NAME} — owners thread",
            }[source_type],
        })
        return n

    def clause(item: dict, field: str) -> str:
        value, _ = stated_value_for(item["id"], field)
        return _phrase(field, fmt_value(field, value), domain, seed + item["id"])

    def clauses_for(item: dict, fields: list[str]) -> list[str]:
        """
        Build a clause list, avoiding the same opening verb twice in one sentence.

        Phrasings are picked independently per field, so two fields can land on the
        same verb ("comes with 16 GB of RAM, and comes with 512 GB of storage"),
        which reads as templated. Re-roll with a salt until the verb differs.
        """
        out: list[str] = []
        for f in fields:
            c = clause(item, f)
            for salt in range(1, 4):
                if c.split()[0] not in {o.split()[0] for o in out}:
                    break
                table = LAPTOP_PHRASINGS if domain == "laptop" else TRIP_PHRASINGS
                options = table.get(f)
                if not options or len(options) < 2:
                    break
                value, _ = stated_value_for(item["id"], f)
                c = _pick(options, seed + item["id"] + f, salt).format(
                    v=fmt_value(f, value)
                )
            out.append(c)
        return out

    blocks: list[dict] = []

    # ---- Summary -----------------------------------------------------------
    rec_cite = cite(rec, "shop")
    n_considered = len(trial["candidates"])
    rec_fields = mentioned_fields_for(rec_id)
    blocks.append({"type": "h", "text": "Summary"})
    blocks.append({
        "type": "p",
        "text": (
            f"I looked at {n_considered} options on {src.SHOP_NAME} and checked the "
            f"most promising ones against independent reviews. My recommendation is "
            f"the **{rec['name']}** [{rec_cite}], which "
            f"{_join_clauses(clauses_for(rec, rec_fields[:2]))}. "
            f"Details and the alternatives I considered are below."
        ),
    })

    # ---- Detail ------------------------------------------------------------
    blocks.append({"type": "h", "text": "What I found"})

    editorial = src.editorial_review(rec)
    ed_cite = cite(rec, "review")
    rev_cite = cite(rec, "reviews")
    reviews = src.customer_reviews(rec)
    avg = sum(r["stars"] for r in reviews) / len(reviews)

    primary = clauses_for(rec, rec_fields[:3])
    extra = clauses_for(rec, rec_fields[3:5])

    body = f"{_pick(CANDIDATE_OPENERS, seed + 'rec')} It {_join_clauses(primary)}."
    if extra:
        body += f" It also {_join_clauses(extra)}."
    body += (
        f" {src.REVIEW_NAME} scored it {editorial['score']}/10 [{ed_cite}], calling it "
        f"“{editorial['verdict'].rstrip('.')}”. "
        f"Across {len(reviews)} customer reviews it averages {avg:.1f} stars "
        f"[{rev_cite}], the most common complaint being {editorial['consNoun'][0]}."
    )
    blocks.append({
        "type": "candidate",
        "name": rec["name"],
        "cite": rec_cite,
        "price": fmt_value(price_field, stated_value_for(rec_id, price_field)[0]),
        "text": body,
    })

    if runner_up:
        ru = catalog[runner_up]
        ru_cite = cite(ru, "shop")
        ru_clauses = clauses_for(ru, mentioned_fields_for(runner_up)[:3])
        blocks.append({
            "type": "candidate",
            "name": ru["name"],
            "cite": ru_cite,
            "price": fmt_value(price_field, ru[price_field]),
            "text": (
                f"{_pick(RUNNER_UP_OPENERS, seed + 'ru')} It {_join_clauses(ru_clauses)}. "
                f"It's a defensible choice, but it doesn't quite match the "
                f"{rec['name']} on the combination you asked for."
            ),
        })

    for rj_id in rejects:
        rj = catalog[rj_id]
        rj_cite = cite(rj, "shop")
        rj_clauses = clauses_for(rj, mentioned_fields_for(rj_id)[:2])
        blocks.append({
            "type": "candidate",
            "name": rj["name"],
            "cite": rj_cite,
            "price": fmt_value(price_field, rj[price_field]),
            "text": (
                f"{_pick(REJECT_OPENERS, seed + rj_id)} It {_join_clauses(rj_clauses)}."
            ),
        })

    # ---- Trade-offs --------------------------------------------------------
    blocks.append({"type": "h", "text": "Trade-offs worth knowing"})
    forum_cite = cite(rec, "forum")
    blocks.append({
        "type": "p",
        "text": (
            f"Two things come up repeatedly from owners: {editorial['consNoun'][0]} "
            f"and {editorial['consNoun'][1]}. Neither bears directly on what you "
            f"asked for, but both appear often enough in the owners' thread "
            f"[{forum_cite}] to be worth knowing before you buy. On the other side, "
            f"{editorial['prosNoun'][0]} draws consistent praise."
        ),
    })

    # ---- Recommendation ----------------------------------------------------
    blocks.append({"type": "h", "text": "Recommendation"})
    req_summary = ", ".join(c["label"] for c in trial["constraints"])
    blocks.append({
        "type": "p",
        "text": (
            f"Go with the **{rec['name']}** [{rec_cite}]. Weighing your requirements "
            f"({req_summary}) against price, customer feedback and the independent "
            f"testing, it's the option I'd put my own money on out of the "
            f"{n_considered} I looked at."
        ),
    })

    return {"blocks": blocks, "citations": citations}
