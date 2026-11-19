# GitHub Pages hosting

Live at **https://parthagarwalgit.github.io/shop-assistant-study/** — free, no account
beyond GitHub, works on phones and desktops.

## Why a separate repo

This source repo is named `trustloop` and its docs explain that 3 of 10 recommendations
are planted. Hosting at `.../trustloop/` would put "trust" in the link participants get
(banned in `docs/RECRUITMENT.md`) and point the curious at the reveal. So
`publish.py` builds the site and pushes **only the minified build** — no source, no
docs, no sourcemaps — to `ParthAgarwalGit/shop-assistant-study`, which Pages serves.

## Publishing

```bash
python deploy/pages/publish.py            # real publish
python deploy/pages/publish.py --preview  # test link only; never send it out
```

A real publish **refuses to run** unless `app/.env` sets a data sink other than `none`
and the researcher name, email and institution. Without a sink, responses never
leave the participant's browser — sending that link would waste every participant.

`VITE_ETHICS_REF` is optional: when unset, the consent and debrief screens omit the
approval sentence instead of showing a placeholder or implying an approval.

## Checking a publish

Pages takes ~1 minute. Then:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://parthagarwalgit.github.io/shop-assistant-study/
```

A blank page with 404s on `/assets/*` means the base path is wrong; `publish.py` sets
`BASE_PATH=/shop-assistant-study/`, so only a renamed repo would cause this.
