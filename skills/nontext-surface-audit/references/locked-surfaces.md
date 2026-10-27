# Locked surfaces

- Hero/large images: missing `alt` or `alt=""` **only** when the image is load-bearing: `width` or `height` **&gt; 100px** (attributes or CSS), or a `hero`/`banner` class with no size. Skip UI chrome (`icon`, `logo`, `spacer`, `pixel`, `favicon`, `1x1`).
- PDF-only: `href` ending `.pdf` and word_count &lt; 80 on the HTML page.
- Canvas: `<canvas>` present and word_count &lt; 100.

IDs are distinct (`CRA-04`, `CRA-04-PDF`, `CRA-04-CANVAS`) so compose-unique-ID does not drop PDF/canvas when images also fire.
