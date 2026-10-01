---
description: "Use whenever writing the company's name anywhere: app copy, About and splash, package metadata, store listings, signing-key identities, docs, emails, websites, code comments. It's Fireball Enterprise, without LLC, unless the legal name is required."
applyTo: "**"
---
# Company Name Rule
- **Write "Fireball Enterprise" — never "Fireball Enterprise LLC"** (owner, 2026-10-01). The entity type
  can change (an S corp later), and the brand shouldn't change with it.
- **Use the legal name ("Fireball Enterprise LLC") only where the law or a contract needs it:**
  - Terms of Service, Privacy Policy and other legal agreements that name the contracting party.
  - Invoices, receipts, tax and payment-processor records.
  - Contracts, trademark or registration filings.
  - Store or certificate records that must match the registered entity, such as the App Store seller or the Apple/Authenticode certificate subject. Those come from the registration, so leave them as they are.
- **Everything else uses "Fireball Enterprise":** copyright lines (`© <year> Fireball Enterprise`),
  About and splash views, package maintainers and publishers (.deb `Maintainer:`, AppStream
  `<developer>`, Snap and store publisher display names), signing-key identities (GPG/apt),
  user-facing copy, docs, READMEs, help and marketing.
- When you touch a file that still says "Fireball Enterprise LLC" outside those legal places, drop the
  "LLC" in the same change.
