# Empty FAQ answers (ENG-04)

Akasa Delhi–Mumbai vs Delhi–Ahmedabad: same template, real per-city facts, **identical empty FAQ accordion**.

For each `h2`–`h4` that ends in `?` or sits under an FAQ heading:

1. Take text until the next heading.
2. Empty = no alphanumeric token after stripping expand/collapse chrome. **`2h 15m` is not empty.**
3. If FAQPage `Question`/`acceptedAnswer` covers the question → skip.
4. If ≥2 uncovered empty questions on a page → high `ENG-04`.

Do not flag “Affordable Fares” boilerplate on city-pair pages. Templating with substituted facts is legitimate.
