import { useRef } from "react";
import type { Catalog, CatalogItem } from "../types";
import { telemetry } from "../lib/telemetry";
import { useVisibleFor } from "./useVisibility";
import { formatValue } from "../components/SpecCard";

// -----------------------------------------------------------------------------
// The simulated web.
//
// These pages carry the TRUTH. The agent's prose is what may be wrong, and the
// asymmetry is the entire experiment: verification means noticing that what the
// agent said does not match what the source says.
//
// Nothing here highlights, flags or compares anything. A participant checking the
// RAM has to find the RAM row in the specification table and read it, exactly as
// they would on a real retail page. Any affordance that shortened that would
// collapse the effort gradient we are trying to measure.
// -----------------------------------------------------------------------------

export interface SourcePageData {
  url: string;
  domain: string;
  siteName: string;
  [k: string]: unknown;
}

export interface Sources {
  domains: Record<string, string>;
  siteNames: Record<string, string>;
  /** itemId -> sourceType -> page. `url` here is the canonical address; never
      recompute a URL in application code, always read it from this table. */
  pages: Record<string, Record<string, SourcePageData>>;
}

function Stars({ n }: { n: number }) {
  return (
    <span className="stars" aria-label={`${n} out of 5 stars`}>
      {"★".repeat(n)}
      <span className="stars__empty">{"★".repeat(5 - n)}</span>
    </span>
  );
}

/**
 * One row of a specification table, individually instrumented.
 *
 * Per-row visibility is what lets the analysis ask the sharpest possible question:
 * of the participants who opened the page containing the disputed figure, how many
 * actually had that row on screen long enough to read it? Someone who opened the
 * page and bounced is behaviourally different from someone who read the row and
 * accepted the recommendation anyway.
 */
function SpecRow({
  field, label, value, url,
}: {
  field: string; label: string; value: string; url: string;
}) {
  const ref = useRef<HTMLTableRowElement>(null);
  useVisibleFor(ref as React.RefObject<HTMLElement>, (ms) =>
    telemetry.specRowViewed(url, field, ms),
  );
  return (
    <tr ref={ref} data-tid={`spec-${field}`}>
      <th scope="row">{label}</th>
      <td>{value}</td>
    </tr>
  );
}

function Section({
  id, url, title, children,
}: {
  id: string; url: string; title?: string; children: React.ReactNode;
}) {
  const ref = useRef<HTMLElement>(null);
  useVisibleFor(ref as React.RefObject<HTMLElement>, (ms) =>
    telemetry.sectionViewed(url, id, ms),
  );
  return (
    <section ref={ref} id={id} className="mw__section" data-tid={`section-${id}`}>
      {title && <h2 className="mw__h2">{title}</h2>}
      {children}
    </section>
  );
}

// -----------------------------------------------------------------------------
// Retailer product page
// -----------------------------------------------------------------------------

export function ShopPage({
  item, page, catalog,
}: {
  item: CatalogItem; page: SourcePageData; catalog: Catalog;
}) {
  const reviews = (page.reviews ?? []) as Array<{
    handle: string; stars: number; date: string; body: string; verified: boolean;
  }>;
  const fields = catalog.specCardFields[item.domain] ?? [];
  // The full spec sheet is longer than the summary card: the disputed figure must
  // sit among many others, not in a shortlist of three.
  const allFields = Object.keys(catalog.fieldMeta).filter(
    (f) => item[f] !== undefined,
  );
  const priceField = item.domain === "laptop" ? "price" : "total_price";
  const avg = reviews.length
    ? reviews.reduce((s, r) => s + r.stars, 0) / reviews.length
    : 0;

  return (
    <div className="mw mw--shop">
      <header className="mw__masthead">
        <span className="mw__logo">Vantage</span>
        <nav className="mw__nav">
          <span>Electronics</span><span>Travel</span><span>Deals</span>
          <span>Help</span>
        </nav>
      </header>

      <div className="mw__product">
        <div className="mw__gallery" aria-hidden="true">
          <div className="mw__gallery-main" />
          <div className="mw__gallery-thumbs">
            <span /><span /><span />
          </div>
        </div>
        <div className="mw__buybox">
          <h1 className="mw__h1">{item.name}</h1>
          <div className="mw__rating">
            <Stars n={Math.round(avg)} />
            <span className="mw__muted">
              {avg.toFixed(1)} · {reviews.length} reviews
            </span>
          </div>
          <div className="mw__price">
            {formatValue(item[priceField], "currency", "$")}
          </div>
          <p className="mw__muted mw__small">
            In stock · Free delivery · 30-day returns
          </p>
          <button type="button" className="mw__buy" disabled>
            Add to basket
          </button>
          <p className="mw__small mw__muted">
            Sold by Vantage Retail Ltd. Prices include VAT.
          </p>
        </div>
      </div>

      <Section id="specifications" url={page.url} title="Specifications">
        <table className="mw__specs">
          <tbody>
            {allFields.map((f) => {
              const meta = catalog.fieldMeta[f];
              if (!meta) return null;
              return (
                <SpecRow
                  key={f}
                  field={f}
                  label={meta.label}
                  value={formatValue(item[f], meta.kind, meta.unit)}
                  url={page.url}
                />
              );
            })}
          </tbody>
        </table>
        <p className="mw__small mw__muted">
          Specifications supplied by the manufacturer. Vantage is not responsible
          for typographical errors in third-party listings.
        </p>
      </Section>

      <Section id="description" url={page.url} title="Product description">
        <p>
          The {item.name} is aimed at buyers who want a dependable everyday machine
          without paying for features they are unlikely to use. It ships in the
          configuration listed above; other configurations are sold separately and
          may differ in memory and storage.
        </p>
        <p className="mw__muted mw__small">
          Where a specification matters to your purchase, please confirm it against
          the specification table above rather than the summary description.
        </p>
      </Section>

      <Section id="reviews" url={page.url} title={`Customer reviews (${reviews.length})`}>
        <div className="mw__reviews">
          {reviews.map((r, i) => (
            <article key={i} className="mw__review">
              <div className="mw__review-head">
                <Stars n={r.stars} />
                <span className="mw__review-handle">{r.handle}</span>
                {r.verified && (
                  <span className="mw__badge">Verified purchase</span>
                )}
                <span className="mw__muted mw__small">{r.date}</span>
              </div>
              <p>{r.body}</p>
            </article>
          ))}
        </div>
      </Section>

      <footer className="mw__footer">
        <span>© 2026 Vantage Retail Ltd</span>
        <span>Terms · Privacy · Returns</span>
      </footer>
      {fields.length === 0 && null}
    </div>
  );
}

// -----------------------------------------------------------------------------
// Editorial review site
// -----------------------------------------------------------------------------

export function ReviewPage({
  item, page, catalog,
}: {
  item: CatalogItem; page: SourcePageData; catalog: Catalog;
}) {
  const allFields = Object.keys(catalog.fieldMeta).filter(
    (f) => item[f] !== undefined,
  );
  const pros = (page.pros ?? []) as string[];
  const cons = (page.cons ?? []) as string[];

  return (
    <div className="mw mw--review">
      <header className="mw__masthead mw__masthead--review">
        <span className="mw__logo">TechBench</span>
        <nav className="mw__nav">
          <span>Reviews</span><span>Buying guides</span><span>How we test</span>
        </nav>
      </header>

      <article>
        <h1 className="mw__h1">{item.name} review</h1>
        <p className="mw__byline">
          By {String(page.author)} · {String(page.date)}
        </p>

        <div className="mw__score">
          <span className="mw__score-num">{String(page.score)}</span>
          <span className="mw__score-den">/10</span>
        </div>

        <p className="mw__verdict">{String(page.verdict)}</p>

        <Section id="body" url={page.url}>
          {String(page.body).split("\n\n").map((para, i) => (
            <p key={i}>{para}</p>
          ))}
        </Section>

        <Section id="proscons" url={page.url}>
          <div className="mw__proscons">
            <div>
              <h3 className="mw__h3">Pros</h3>
              <ul>{pros.map((p, i) => <li key={i}>{p}</li>)}</ul>
            </div>
            <div>
              <h3 className="mw__h3">Cons</h3>
              <ul>{cons.map((c, i) => <li key={i}>{c}</li>)}</ul>
            </div>
          </div>
        </Section>

        <Section id="specifications" url={page.url} title="Tested specifications">
          <table className="mw__specs">
            <tbody>
              {allFields.map((f) => {
                const meta = catalog.fieldMeta[f];
                if (!meta) return null;
                return (
                  <SpecRow
                    key={f}
                    field={f}
                    label={meta.label}
                    value={formatValue(item[f], meta.kind, meta.unit)}
                    url={page.url}
                  />
                );
              })}
            </tbody>
          </table>
        </Section>
      </article>

      <footer className="mw__footer">
        <span>© 2026 TechBench</span>
        <span>Independent testing since 2011</span>
      </footer>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Community forum
// -----------------------------------------------------------------------------

export function ForumPage({ page }: { page: SourcePageData }) {
  const posts = (page.posts ?? []) as Array<{
    handle: string; date: string; body: string; op: boolean;
  }>;
  return (
    <div className="mw mw--forum">
      <header className="mw__masthead mw__masthead--forum">
        <span className="mw__logo">GearLoop</span>
        <nav className="mw__nav">
          <span>Forums</span><span>New posts</span><span>Search</span>
        </nav>
      </header>

      <h1 className="mw__h1 mw__h1--forum">{String(page.title)}</h1>

      <Section id="thread" url={page.url}>
        <div className="mw__posts">
          {posts.map((p, i) => (
            <article key={i} className={`mw__post${p.op ? " mw__post--op" : ""}`}>
              <div className="mw__post-side">
                <span className="mw__avatar" aria-hidden="true" />
                <span className="mw__post-handle">{p.handle}</span>
                {p.op && <span className="mw__badge">OP</span>}
              </div>
              <div className="mw__post-body">
                <span className="mw__muted mw__small">{p.date}</span>
                <p>{p.body}</p>
              </div>
            </article>
          ))}
        </div>
      </Section>

      <footer className="mw__footer">
        <span>© 2026 GearLoop</span>
        <span>Opinions are those of individual members.</span>
      </footer>
    </div>
  );
}
