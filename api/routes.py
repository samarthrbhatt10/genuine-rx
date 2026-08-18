"""
FastAPI Routes implementing 04_API_CONTRACT.md.
"""
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection

from matching_engine import find_substitutes
from matching_engine.types import (
    MedicineEntry,
    PriceEntry,
    SaltEntry,
    SaltRequirement,
)
from ocr_resolver import match_medicine_text

from .database import get_db
from .models import (
    CandidateResponse,
    PriceHistoryPoint,
    ResolveMedicineRequest,
    ResolveMedicineResponse,
    SourceMedicine,
    SubstituteItem,
    SubstitutesResponse,
    TrackedMedicineItem,
    TrackedMedicineRequest,
    UserRequest,
)

router = APIRouter(prefix="/api/v1")
DbConn = Annotated[Connection, Depends(get_db)]

# --------------------------------------------------------------------------- #
# Error Handlers
# --------------------------------------------------------------------------- #

def raise_not_found(message: str):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "not_found", "message": message}
    )

def raise_bad_request(message: str):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"error": "bad_request", "message": message}
    )


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.post("/resolve-medicine", response_model=ResolveMedicineResponse)
def resolve_medicine(req: ResolveMedicineRequest, conn: DbConn):
    """
    Resolves free text or OCR output to a specific medicine record.
    """
    # Build the catalog of brand names and aliases mapped to medicine_id
    # We fetch brand names from medicines, and known generic aliases from salts.
    # Note: OCR/Typed text is usually a brand name. If it's a salt, it points to the salt.
    # We map both to provide a rich catalog for RapidFuzz.
    
    catalog = {}
    
    meds = conn.execute("SELECT medicine_id, brand_name FROM medicines").fetchall()
    for m in meds:
        catalog[m["brand_name"].lower()] = {
            "medicine_id": m["medicine_id"],
            "brand_name": m["brand_name"]
        }
        
    # Run rapidfuzz matcher from ocr_resolver
    result = match_medicine_text(req.raw_text, catalog)
    
    candidates = None
    if result.candidates:
        candidates = [
            CandidateResponse(
                medicine_id=c["medicine_id"],
                brand_name=c["brand_name"],
                confidence=c["confidence"]
            )
            for c in result.candidates
        ]
        
    return ResolveMedicineResponse(
        matched=result.matched,
        medicine_id=result.medicine_id,
        brand_name=result.brand_name,
        confidence=result.confidence,
        needs_confirmation=result.needs_confirmation,
        candidates=candidates
    )


@router.get("/medicines/{medicine_id}/substitutes", response_model=SubstitutesResponse)
def get_substitutes(medicine_id: int, conn: DbConn):
    """
    Returns ranked salt-identical substitutes for a resolved medicine.
    """
    # 1. Fetch source medicine
    source_med = conn.execute(
        "SELECT medicine_id, brand_name FROM medicines WHERE medicine_id = %s",
        (medicine_id,)
    ).fetchone()
    if not source_med:
        raise_not_found(f"Medicine {medicine_id} not found")
        
    # 2. Fetch latest price for source medicine
    source_price_row = conn.execute(
        "SELECT price FROM price_history WHERE medicine_id = %s ORDER BY scraped_at DESC LIMIT 1",
        (medicine_id,)
    ).fetchone()
    current_price = float(source_price_row["price"]) if source_price_row else None
    
    # 3. Fetch data for Matching Engine
    # Salts
    salt_rows = conn.execute("SELECT salt_id, canonical_name, aliases FROM salts").fetchall()
    salt_table = [
        SaltEntry(r["salt_id"], r["canonical_name"], frozenset(a.lower() for a in (r["aliases"] or [])))
        for r in salt_rows
    ]
    
    # Medicines & their salts
    med_rows = conn.execute("""
        SELECT m.medicine_id, m.brand_name, m.form, m.manufacturer, m.is_jan_aushadhi,
               array_agg(ms.salt_id) AS salt_ids, array_agg(ms.strength_mg) AS strengths
          FROM medicines m
          JOIN medicine_salts ms USING (medicine_id)
         GROUP BY m.medicine_id
    """).fetchall()
    
    medicine_table = [
        MedicineEntry(
            r["medicine_id"], r["brand_name"], r["form"], r["manufacturer"], r["is_jan_aushadhi"],
            frozenset(SaltRequirement(sid, Decimal(str(smg))) for sid, smg in zip(r["salt_ids"], r["strengths"]))
        )
        for r in med_rows
    ]
    
    # Price history (latest per medicine)
    price_rows = conn.execute("""
        SELECT DISTINCT ON (medicine_id) medicine_id, source, price
          FROM price_history
         ORDER BY medicine_id, scraped_at DESC
    """).fetchall()
    price_table = [
        PriceEntry(r["medicine_id"], r["source"], Decimal(str(r["price"]))) 
        for r in price_rows
    ]
    
    # Caution list
    caution_rows = conn.execute("SELECT salt_id, reason FROM caution_list").fetchall()
    caution_salt_ids = {r["salt_id"]: r["reason"] for r in caution_rows}
    
    # Reconstruct query_salts from source_medicine's salts
    source_salt_reqs = next((m.salts for m in medicine_table if m.medicine_id == medicine_id), frozenset())
    if not source_salt_reqs:
        # Medicine has no salts? Edge case.
        return SubstitutesResponse(
            source_medicine=SourceMedicine(medicine_id=medicine_id, brand_name=source_med["brand_name"], current_price=current_price),
            substitutes=[],
            caution_flag=None
        )
        
    salt_id_to_name = {s.salt_id: s.canonical_name for s in salt_table}
    query_salts = [
        (salt_id_to_name[req.salt_id], req.strength_mg)
        for req in source_salt_reqs
        if req.salt_id in salt_id_to_name
    ]
    
    # 4. Call Matching Engine
    ranked_subs = find_substitutes(query_salts, salt_table, medicine_table, price_table, caution_salt_ids)
    
    # 5. Format response
    caution_flag = None
    if ranked_subs and ranked_subs[0].caution_flag:
        caution_flag = ranked_subs[0].caution_reason
        
    substitutes = []
    # If source has a price, compute savings against IT, else against most expensive sub
    base_price = current_price if current_price else (float(max(r.price for r in ranked_subs)) if ranked_subs else 0.0)
    
    for r in ranked_subs:
        p = float(r.price)
        savings_rupees = max(0.0, base_price - p)
        savings_percent = round((savings_rupees / base_price * 100.0) if base_price > 0 else 0.0, 1)
        
        substitutes.append(SubstituteItem(
            medicine_id=r.medicine_id,
            brand_name=r.brand_name,
            price=p,
            is_jan_aushadhi=r.is_jan_aushadhi,
            savings_rupees=savings_rupees,
            savings_percent=savings_percent
        ))
        
    return SubstitutesResponse(
        source_medicine=SourceMedicine(
            medicine_id=medicine_id,
            brand_name=source_med["brand_name"],
            current_price=current_price
        ),
        substitutes=substitutes,
        caution_flag=caution_flag
    )


@router.post("/tracked-medicines", status_code=status.HTTP_201_CREATED)
def add_tracked_medicine(req: TrackedMedicineRequest, conn: DbConn):
    """
    Add a medicine to a user's tracked list. Idempotent.
    """
    # Verify user exists
    user = conn.execute("SELECT user_id FROM users WHERE user_id = %s", (req.user_id,)).fetchone()
    if not user:
        raise_not_found(f"User {req.user_id} not found")
        
    # Verify medicine exists
    med = conn.execute("SELECT medicine_id FROM medicines WHERE medicine_id = %s", (req.medicine_id,)).fetchone()
    if not med:
        raise_not_found(f"Medicine {req.medicine_id} not found")
        
    with conn.transaction():
        conn.execute("""
            INSERT INTO tracked_medicines (user_id, medicine_id, profile_label)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, medicine_id, profile_label) DO NOTHING
        """, (req.user_id, req.medicine_id, req.profile_label))
        
    return {"status": "success", "message": "Medicine tracked successfully"}


@router.get("/users/{user_id}/tracked-medicines", response_model=list[TrackedMedicineItem])
def get_tracked_medicines(user_id: int, conn: DbConn):
    """
    Returns the user's tracked list with latest price.
    """
    user = conn.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,)).fetchone()
    if not user:
        raise_not_found(f"User {user_id} not found")
        
    rows = conn.execute("""
        SELECT t.id as tracked_id, t.medicine_id, t.profile_label, m.brand_name,
               (SELECT price FROM price_history ph 
                 WHERE ph.medicine_id = t.medicine_id 
                 ORDER BY scraped_at DESC LIMIT 1) as latest_price,
               (
                 SELECT COALESCE(
                   json_agg(json_build_object('price', h.price, 'scraped_at', h.scraped_at) ORDER BY h.scraped_at ASC),
                   '[]'::json
                 )
                 FROM price_history h
                 WHERE h.medicine_id = t.medicine_id
               ) as history
          FROM tracked_medicines t
          JOIN medicines m USING (medicine_id)
         WHERE t.user_id = %s
    """, (user_id,)).fetchall()
    
    items = []
    for r in rows:
        raw_history = r["history"] or []
        if isinstance(raw_history, str):
            import json as _json
            raw_history = _json.loads(raw_history)
        history_points = [
            PriceHistoryPoint(price=float(p["price"]), scraped_at=p["scraped_at"])
            for p in raw_history
        ]
        items.append(TrackedMedicineItem(
            tracked_id=r["tracked_id"],
            medicine_id=r["medicine_id"],
            brand_name=r["brand_name"],
            profile_label=r["profile_label"],
            latest_price=float(r["latest_price"]) if r["latest_price"] is not None else None,
            savings_to_date=0.0,
            history=history_points
        ))
        
    return items



@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(req: UserRequest, conn: DbConn):
    """
    Create a new user. Rejects invalid phones.
    """
    with conn.transaction():
        # Check if exists
        existing = conn.execute("SELECT user_id FROM users WHERE phone = %s", (req.phone,)).fetchone()
        if existing:
            return {"user_id": existing["user_id"], "message": "User already exists"}
            
        res = conn.execute(
            "INSERT INTO users (phone, consent_whatsapp) VALUES (%s, %s) RETURNING user_id",
            (req.phone, req.consent_whatsapp)
        ).fetchone()
        
    return {"user_id": res["user_id"], "message": "User created"}
