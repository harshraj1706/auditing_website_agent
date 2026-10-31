/**
 * Remediation Code Snippet Generator.
 * Produces copy-paste ready structured data, robots.txt directives, llms.txt,
 * and semantic HTML tailored to the audited domain and specific finding ID.
 */

import type { Finding } from '../types/audit';

export interface RemediationSnippet {
  id: string;
  title: string;
  filename: string;
  language: 'json' | 'html' | 'plaintext' | 'markdown';
  code: string;
  explanation: string;
  placementGuide: string;
}

export function generateRemediationSnippet(
  finding: Finding,
  siteContext?: { url?: string; site?: string; siteType?: string }
): RemediationSnippet | null {
  const findingId = finding.id.toUpperCase();
  const rawUrl =
    siteContext?.url ||
    (finding.affected_urls && finding.affected_urls[0]) ||
    'https://example.com';

  let domain = siteContext?.site || 'example.com';
  let siteUrl = 'https://' + domain;
  try {
    const parsed = new URL(rawUrl.startsWith('http') ? rawUrl : `https://${rawUrl}`);
    domain = parsed.hostname.replace(/^www\./, '');
    siteUrl = `${parsed.protocol}//${parsed.hostname}`;
  } catch {
    // Fallback domain
  }

  // Capitalize domain name for brand display
  const brandName = domain
    .split('.')[0]
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());

  // 1. FC-ENT-01 & Organization schema variants
  if (findingId === 'FC-ENT-01' || findingId === 'FC-ENT-02' || findingId === 'FC-ENT-03') {
    const schemaObj = {
      '@context': 'https://schema.org',
      '@type': 'Organization',
      name: brandName,
      url: siteUrl,
      logo: `${siteUrl}/logo.png`,
      description: `Official website and services for ${brandName}.`,
      sameAs: [
        `https://www.wikidata.org/wiki/Special:Search?search=${encodeURIComponent(brandName)}`,
        `https://www.linkedin.com/company/${domain.split('.')[0]}`,
        `https://x.com/${domain.split('.')[0]}`,
      ],
    };

    return {
      id: finding.id,
      title: 'Organization Schema.org JSON-LD',
      filename: 'organization-schema.html',
      language: 'html',
      code: `<script type="application/ld+json">\n${JSON.stringify(schemaObj, null, 2)}\n</script>`,
      explanation:
        'Embeds official brand identity, canonical website URL, and verified sameAs authority links into the initial HTML response for search engines and AI agents.',
      placementGuide: 'Paste inside the <head> tag of your homepage (index.html or root layout template).',
    };
  }

  // 2. FC-ENT-01-LOCAL or FC-ENT-04 (LocalBusiness schema)
  if (findingId === 'FC-ENT-01-LOCAL' || findingId === 'FC-ENT-04') {
    const schemaObj = {
      '@context': 'https://schema.org',
      '@type': 'LocalBusiness',
      name: brandName,
      image: `${siteUrl}/storefront.jpg`,
      url: siteUrl,
      telephone: '+1-555-0199',
      address: {
        '@type': 'PostalAddress',
        streetAddress: '123 Main Street',
        addressLocality: 'Cityville',
        addressRegion: 'CA',
        postalCode: '90210',
        addressCountry: 'US',
      },
      geo: {
        '@type': 'GeoCoordinates',
        latitude: 37.7749,
        longitude: -122.4194,
      },
      openingHoursSpecification: [
        {
          '@type': 'OpeningHoursSpecification',
          dayOfWeek: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
          opens: '09:00',
          closes: '18:00',
        },
      ],
    };

    return {
      id: finding.id,
      title: 'LocalBusiness Schema with NAP & Hours',
      filename: 'localbusiness-schema.html',
      language: 'html',
      code: `<script type="application/ld+json">\n${JSON.stringify(schemaObj, null, 2)}\n</script>`,
      explanation:
        'Provides definitive Name, Address, Phone (NAP), geographic coordinates, and opening hours to disambiguate local physical establishments.',
      placementGuide: 'Embed in the <head> of your homepage and /contact or /locations pages.',
    };
  }

  // 3. FC-ENT-01-ARTICLE (Article / NewsArticle schema)
  if (findingId === 'FC-ENT-01-ARTICLE') {
    const schemaObj = {
      '@context': 'https://schema.org',
      '@type': 'Article',
      headline: 'Article Title Goes Here',
      author: {
        '@type': 'Person',
        name: 'Staff Author',
      },
      datePublished: '2026-01-15T08:00:00Z',
      dateModified: '2026-02-01T12:00:00Z',
      publisher: {
        '@type': 'Organization',
        name: brandName,
        logo: {
          '@type': 'ImageObject',
          url: `${siteUrl}/logo.png`,
        },
      },
      mainEntityOfPage: {
        '@type': 'WebPage',
        '@id': `${siteUrl}/blog/article-slug`,
      },
    };

    return {
      id: finding.id,
      title: 'Article & Author Attribution JSON-LD',
      filename: 'article-schema.html',
      language: 'html',
      code: `<script type="application/ld+json">\n${JSON.stringify(schemaObj, null, 2)}\n</script>`,
      explanation:
        'Establishes editorial attribution, publication date, freshness update timestamps, and publishing organization for citation AI agents.',
      placementGuide: 'Inject dynamically into the <head> of all blog posts, news articles, and guides.',
    };
  }

  // 4. FC-ENT-01-PRODUCT (Product & Offer schema)
  if (findingId === 'FC-ENT-01-PRODUCT' || findingId === 'FC-FRESH-05') {
    const schemaObj = {
      '@context': 'https://schema.org',
      '@type': 'Product',
      name: 'Sample Product Name',
      image: `${siteUrl}/images/product.jpg`,
      description: 'Comprehensive high-quality product description.',
      brand: {
        '@type': 'Brand',
        name: brandName,
      },
      offers: {
        '@type': 'Offer',
        priceCurrency: 'USD',
        price: '49.99',
        priceValidUntil: '2027-12-31',
        availability: 'https://schema.org/InStock',
        url: `${siteUrl}/products/sample-product`,
      },
    };

    return {
      id: finding.id,
      title: 'Product & Pricing Offer Schema',
      filename: 'product-schema.html',
      language: 'html',
      code: `<script type="application/ld+json">\n${JSON.stringify(schemaObj, null, 2)}\n</script>`,
      explanation:
        'Enables AI shopping agents and Perplexity/Google shopping assistants to accurately quote exact prices, availability, and currency without crawling friction.',
      placementGuide: 'Inject in the HTML head of product display pages (PDPs).',
    };
  }

  // 5. FC-ENT-01-FAQ or ENG-04 (FAQPage schema)
  if (findingId === 'FC-ENT-01-FAQ' || findingId === 'ENG-04') {
    const schemaObj = {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: [
        {
          '@type': 'Question',
          name: `What services does ${brandName} provide?`,
          acceptedAnswer: {
            '@type': 'Answer',
            text: `${brandName} provides end-to-end technical optimization, digital discovery, and AI citability readiness solutions.`,
          },
        },
        {
          '@type': 'Question',
          name: `How do I contact ${brandName} support?`,
          acceptedAnswer: {
            '@type': 'Answer',
            text: `You can reach our official team via our contact portal or by emailing support@${domain}.`,
          },
        },
      ],
    };

    return {
      id: finding.id,
      title: 'FAQPage Structured Data',
      filename: 'faq-schema.html',
      language: 'html',
      code: `<script type="application/ld+json">\n${JSON.stringify(schemaObj, null, 2)}\n</script>`,
      explanation:
        'Allows conversational agents to directly quote question-answer pairs and resolve customer queries from authoritative on-site answers.',
      placementGuide: 'Embed in the <head> of your FAQ, Help Center, or Pricing Q&A sections.',
    };
  }

  // 6. FC-PROACT-03 (Voice / Conversational AI SpeakableSpecification)
  if (findingId === 'FC-PROACT-03') {
    const schemaObj = {
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: `${brandName} Summary Overview`,
      speakable: {
        '@type': 'SpeakableSpecification',
        cssSelector: ['h1', '.article-headline', '.article-summary', '.speakable-takeaway'],
      },
      url: `${siteUrl}/article`,
    };

    return {
      id: finding.id,
      title: 'Multimodal SpeakableSpecification Schema',
      filename: 'speakable-schema.html',
      language: 'html',
      code: `<script type="application/ld+json">\n${JSON.stringify(schemaObj, null, 2)}\n</script>`,
      explanation:
        'Instructs voice assistants (Google Assistant, Siri, Gemini Live audio briefings) which CSS selectors contain the concise audio-quotable takeaways.',
      placementGuide: 'Add to the schema block on long-form content, news articles, and press announcements.',
    };
  }

  // 7. CRA-01 (robots.txt AI Crawlers & Sitemap Directive)
  if (findingId === 'CRA-01' || findingId === 'CRA-03') {
    const robotsTxt = `# robots.txt for ${domain}
# Standard web crawlers
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /checkout/
Disallow: /api/private/

# Explicit permissions for AI search, citation & assistant crawlers
User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Applebot-Extended
Allow: /

# Canonical XML Sitemap
Sitemap: ${siteUrl}/sitemap.xml
`;

    return {
      id: finding.id,
      title: 'AI-Friendly robots.txt Configuration',
      filename: 'robots.txt',
      language: 'plaintext',
      code: robotsTxt,
      explanation:
        'Explicitly welcomes major AI discovery agents (OpenAI, Anthropic, Google, Perplexity, Apple) while securing private admin and transactional routes.',
      placementGuide: 'Save as the file /robots.txt at the web root of your domain.',
    };
  }

  // 8. FC-PROACT-01 (llms.txt Specification)
  if (findingId === 'FC-PROACT-01') {
    const llmsTxt = `# ${brandName}

> ${brandName} is an industry-leading platform providing specialized digital solutions and services.

## Core Products & Capabilities
- [Documentation](${siteUrl}/docs): Complete architectural specifications and guides
- [About Us](${siteUrl}/about): Company mission, team, and verified background
- [Contact & Support](${siteUrl}/contact): Verified official communication channels
- [Changelog](${siteUrl}/changelog): Latest product updates and feature releases

## Canonical Entity Identity
- Official Website: ${siteUrl}
- Primary Inquiries: support@${domain}
- Public Documentation: ${siteUrl}/docs
`;

    return {
      id: finding.id,
      title: 'llms.txt AI Agent Manifest',
      filename: 'llms.txt',
      language: 'markdown',
      code: llmsTxt,
      explanation:
        'Standardized plaintext specification giving LLMs and autonomous agents a clean, markdown-curated map of authoritative documentation.',
      placementGuide: 'Host at the root directory of your website as /llms.txt (e.g. https://' + domain + '/llms.txt).',
    };
  }

  // 9. FC-FRESH-06 (Missing / Blank Meta Description)
  if (findingId === 'FC-FRESH-06') {
    const metaHtml = `<!-- Primary Meta Tags -->
<title>${brandName} | Official Website</title>
<meta name="description" content="Official website of ${brandName}. Discover our latest services, capabilities, and solutions. Verified information updated for 2026." />

<!-- OpenGraph / Social Fallbacks -->
<meta property="og:title" content="${brandName} | Official Website" />
<meta property="og:description" content="Official website of ${brandName}. Discover our latest services, capabilities, and solutions." />
<meta property="og:url" content="${siteUrl}" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:description" content="Official website of ${brandName}. Discover our latest services, capabilities, and solutions." />`;

    return {
      id: finding.id,
      title: 'SEO & AI Primary Meta Description Tags',
      filename: 'meta-tags.html',
      language: 'html',
      code: metaHtml,
      explanation:
        'Populates the standard <meta name="description"> tag that primary AI search bots ingest during initial preflight indexing.',
      placementGuide: 'Insert inside the <head> section of all public HTML pages.',
    };
  }

  // 10. CRA-04 (Image Alt Attributes)
  if (findingId === 'CRA-04' || findingId.startsWith('CRA-04')) {
    const altHtml = `<!-- Ensure meaningful hero and product images have descriptive alt text -->
<img 
  src="/assets/hero-overview.jpg" 
  alt="${brandName} platform interface showing real-time AI indexing and citation telemetry" 
  width="1200" 
  height="630" 
  loading="eager" 
/>`;

    return {
      id: finding.id,
      title: 'Semantic Image Alt Text Remediation',
      filename: 'image-alt.html',
      language: 'html',
      code: altHtml,
      explanation:
        'Ensures visual search and multimodal AI crawlers can ingest context from hero imagery instead of encountering blank graphic blocks.',
      placementGuide: 'Update image elements in your HTML templates.',
    };
  }

  // 11. ENG-02 (H1 & Semantic Breadcrumbs)
  if (findingId === 'ENG-02') {
    const breadcrumbHtml = `<!-- Semantic Breadcrumb Navigation with Schema.org BreadcrumbList -->
<nav aria-label="Breadcrumb" class="breadcrumbs">
  <ol itemscope itemtype="https://schema.org/BreadcrumbList">
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
      <a itemprop="item" href="${siteUrl}"><span itemprop="name">Home</span></a>
      <meta itemprop="position" content="1" />
    </li>
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
      <a itemprop="item" href="${siteUrl}/services"><span itemprop="name">Services</span></a>
      <meta itemprop="position" content="2" />
    </li>
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
      <span itemprop="name">Current Page</span>
      <meta itemprop="position" content="3" />
    </li>
  </ol>
</nav>

<!-- Singular Descriptive H1 -->
<h1>${brandName} Solutions & Platform Capabilities</h1>`;

    return {
      id: finding.id,
      title: 'BreadcrumbList Schema & Semantic H1 Structure',
      filename: 'breadcrumbs.html',
      language: 'html',
      code: breadcrumbHtml,
      explanation:
        'Establishes unambiguous site hierarchy and navigational orientation for both LLM deep-link visitors and crawlers.',
      placementGuide: 'Place directly above main body content in your layout templates.',
    };
  }

  // 12. FC-FRESH-01 (dateModified / Freshness Signal)
  if (findingId === 'FC-FRESH-01') {
    const nowIso = new Date().toISOString();
    const freshnessHtml = `<!-- Visible or Schema.org freshness date signals -->
<time datetime="${nowIso}" itemprop="dateModified">
  Last updated: ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
</time>

<!-- Add to existing Article / WebPage JSON-LD schema: -->
"dateModified": "${nowIso}"`;

    return {
      id: finding.id,
      title: 'dateModified Freshness Attribution',
      filename: 'freshness-tag.html',
      language: 'html',
      code: freshnessHtml,
      explanation:
        'Signals to AI models that content is current and actively maintained, preventing the model from demoting answers as stale.',
      placementGuide: 'Include near the article header or footer, and add dateModified to your JSON-LD schema.',
    };
  }

  return null;
}
