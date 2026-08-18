# API Contract — FastAPI

Base path: `/api/v1`. All responses are JSON. All endpoints are read-heavy; write endpoints are
marked explicitly. No endpoint triggers a live scrape — the RPA layer populates data on its own
schedule (see `07_BUILD_GRAPH.md` Phase 3).

## `POST /resolve-medicine`

Resolves free text or OCR output to a specific medicine record.

**Request**
```json
{ "raw_text": "Combiflarn", "source": "ocr" }   // source: "ocr" | "typed"
```
**Response**
```json
{
  "matched": true,
  "medicine_id": 4821,
  "brand_name": "Combiflam",
  "confidence": 0.91,
  "needs_confirmation": false
}
```
If `confidence < 0.75`, set `needs_confirmation: true` and return the top 3 candidates instead
of committing to one. The frontend must show a confirmation step in that case — never auto-pick
below threshold.

## `GET /medicines/{medicine_id}/substitutes`

Returns ranked salt-identical substitutes for a resolved medicine.

**Response**
```json
{
  "source_medicine": { "medicine_id": 4821, "brand_name": "Combiflam", "current_price": 42.00 },
  "substitutes": [
    {
      "medicine_id": 991,
      "brand_name": "Jan Aushadhi Generic — Ibuprofen+Paracetamol",
      "price": 6.50,
      "is_jan_aushadhi": true,
      "savings_rupees": 35.50,
      "savings_percent": 84.5
    }
  ],
  "caution_flag": null   // populated with a reason string if any matched salt is on caution_list
}
```
Ranking order is fixed: `is_jan_aushadhi DESC, price ASC`. Do not let this be reordered by any
other signal (rating, popularity, etc.) without an explicit spec update.

## `POST /tracked-medicines` (write)

**Request**
```json
{ "user_id": 12, "medicine_id": 991, "profile_label": "Amma" }
```
**Response** — `201` with the created row. Idempotent on `(user_id, medicine_id, profile_label)`.

## `GET /users/{user_id}/tracked-medicines`

Returns the user's tracked list with latest price and savings-to-date per item, used for both
the app dashboard and the WhatsApp digest generator.

## `POST /users` (write)

**Request**
```json
{ "phone": "+91XXXXXXXXXX", "consent_whatsapp": true }
```
Rejects with `400` if `consent_whatsapp` is `true` but phone is not a valid E.164 Indian number.
Consent must be explicit — never default this field to `true`.

## Error Convention

All errors return `{ "error": "<machine_readable_code>", "message": "<human readable>" }` with
an appropriate status code. Do not leak stack traces or raw exception text in the response body.
