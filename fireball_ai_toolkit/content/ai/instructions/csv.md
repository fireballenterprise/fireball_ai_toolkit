---
description: "Use when creating or editing any .csv file — column layout, naming, date format, quoting, and the standard inventory schema."
applyTo: "**/*.csv"
---
# CSV File Standards
Rules for every `.csv` file in the repo, most of them user-facing files in topic `docs/` folders.

## Propose the Layout First
**Before creating a CSV, post the proposed header row in chat and wait for the user to approve or
adjust it.** Skip this only when the user already spelled out the columns they want in their
request, or when using the fixed Inventory Schema below.

## Minimal Columns
Start with only the columns the user asked for or the data actually needs. Do not pre-add
speculative "just in case" columns — they are easy to add later and hard to spot as dead weight
once a file fills up. When unsure, fewer.

## Date Format — MANDATORY
**All date fields MUST use ISO 8601 `YYYY-MM-DD`**, regardless of the column name (`purchase_date`,
`date`, `start_date`, `end_date`, …).

```csv
# ✅ CORRECT
purchase_date
2025-05-15

# ❌ WRONG
05/15/25
05/15/2025
May 15, 2025
15-05-2025
```

## Unknown / Missing Values
Use `??` for unknown values — never leave a field blank without reason.

```csv
purchase_date,purchase_price
??,??
2025-05-15,"$850 + Tax"
```

## Column Naming
- `snake_case` for all headers
- No spaces in column names

## String Quoting
- Wrap values containing commas, semicolons, or quotes in double quotes
- Use semicolons (`;`) as the separator inside a notes field, not commas

```csv
notes
"Came with 18-55mm lens; 24.2MP; 1080p video"
```

## Inventory CSV Schema
Pre-approved layout for gear/equipment inventory files — use it as-is, no need to propose it first:

```
year,make,model,type,color,serial_number,purchase_location,purchase_date,purchase_price,notes
```

- `year` — model year (integer, e.g. `2025`)
- `make` — manufacturer (e.g. `Canon`, `Nikon`)
- `model` — model name/number
- `type` — category (e.g. `Camera`, `Lens`, `Accessory`)
- `color` — color if relevant, else empty
- `serial_number` — device serial number
- `purchase_location` — store or URL (e.g. `bestbuy.com`, `Costco`)
- `purchase_date` — ISO 8601 `YYYY-MM-DD`, or `??`
- `purchase_price` — dollar amount with tax note (e.g. `"$850 + Tax"`)
- `notes` — semicolon-separated details (bundle contents, specs, purpose)
