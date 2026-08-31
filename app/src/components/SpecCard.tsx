import type { Catalog, CatalogItem } from "../types";

/**
 * The always-visible product spec card.
 *
 * Shown in BOTH disclosure conditions by design. If the opaque condition hid the
 * item's specifications entirely, error detection there would floor at zero for
 * information-availability reasons rather than psychological ones, and the
 * Disclosure main effect would be an artefact. What the manipulation varies is the
 * agent's *process and evidence*, not the existence of the product listing --
 * exactly as on a real shopping site. See docs/STIMULI_DESIGN.md.
 */
export function SpecCard({
  item,
  fields,
  catalog,
  highlight,
}: {
  item: CatalogItem;
  fields: string[];
  catalog: Catalog;
  highlight?: boolean;
}) {
  return (
    <div className={`spec-card${highlight ? " spec-card--highlight" : ""}`}>
      <div className="spec-card__name">{item.name}</div>
      <dl className="spec-card__grid">
        {fields.map((f) => {
          const meta = catalog.fieldMeta[f];
          const raw = item[f];
          if (raw === undefined || !meta) return null;
          return (
            <div key={f} className="spec-card__row">
              <dt>{meta.label}</dt>
              <dd>{formatValue(raw, meta.kind, meta.unit)}</dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}

export function formatValue(
  value: string | number | boolean,
  kind: "number" | "currency" | "bool",
  unit: string,
): string {
  if (kind === "bool") return value ? "Yes" : "No";
  if (kind === "currency") return `$${Number(value).toLocaleString()}`;
  return `${value}${unit}`;
}
