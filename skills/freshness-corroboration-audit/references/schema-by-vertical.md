# Schema type must match the page vertical

Any JSON-LD is not a pass. Classify the **page template**, then require the type that lets an assistant quote the fact on that URL.

Do not require Product on a homepage, Flight on a restaurant `/book`, or Vehicle on dealership contact (LocalBusiness is correct there).

## Templates

| Page looks like | Required types | Wrong (common) |
|---|---|---|
| Product / PDP | `Product` + `Offer` (price, currency, availability) | Only `Organization` / `WebPage` |
| Collection / category grid | `ItemList` + `itemListElement` (price on listed items) | PDP `Product` only, or no listing graph |
| Airline route/search | `Flight` or `TouristTrip` + `Airport.iataCode` | `Product`+generic price, no IATA |
| Auto inventory | `Car` / `Vehicle` + `Offer` | Only dealership `LocalBusiness` |
| Local service | `LocalBusiness` + `PostalAddress` + `OpeningHoursSpecification` | Hours only in a paragraph |
| Blog / news | `Article` / `NewsArticle` + `datePublished` / `dateModified` | Org boilerplate, undated claims |
| Help / FAQ | `FAQPage` → `Question` / `acceptedAnswer` | Prose Q&A, no FAQPage |
| Any brand home | `Organization` + `sameAs` | Icons only, no identity graph |

## Examples (copy shape, not these brands)

Product:

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Trail Runner Pro 3",
  "brand": { "@type": "Brand", "name": "Acme Outdoors" },
  "sku": "TRP3-BLK-42",
  "offers": {
    "@type": "Offer",
    "price": "129.99",
    "priceCurrency": "USD",
    "availability": "https://schema.org/InStock"
  }
}
```

Collection (listing graph — Product on PDPs is not a substitute):

```json
{
  "@context": "https://schema.org",
  "@type": "ItemList",
  "name": "Silk scarves",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "item": {
        "@type": "Product",
        "name": "Handloom silk scarf",
        "offers": { "@type": "Offer", "price": "2400", "priceCurrency": "INR" }
      }
    }
  ]
}
```

Flight (Delhi→Mumbai route case):

```json
{
  "@context": "https://schema.org",
  "@type": "Flight",
  "flightNumber": "AC456",
  "provider": { "@type": "Airline", "name": "Acme Air", "iataCode": "AC" },
  "departureAirport": { "@type": "Airport", "iataCode": "DEL" },
  "arrivalAirport": { "@type": "Airport", "iataCode": "BOM" }
}
```

Vehicle, LocalBusiness, Article, FAQPage, Organization.sameAs: see detector `detect_schema_vertical` and `entity.md`. Article without `dateModified` and without visible “last updated” is a **separate** freshness finding.
