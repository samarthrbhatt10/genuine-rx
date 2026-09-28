*** Settings ***
Documentation     Daily Scheduler Suite — RPA Automation #5: Simulates the APScheduler cron job
...               that runs every night at 02:30 IST to:
...               1. Validate the API is alive (smoke gate)
...               2. Fetch current prices for all tracked medicines via the API
...               3. Simulate writing new price_history entries
...               4. Run a data sanity check on all written prices
...               5. Generate a savings summary report
...
...               This is a standalone demonstration of the full scheduled pipeline.
...               PASS means: the entire automated nightly job completes successfully.

Resource          ../resources/shared.resource
Library           RequestsLibrary
Library           Collections
Library           DateTime
Library           String
Library           OperatingSystem
Library           BuiltIn

Suite Setup       Initialize Daily Run


*** Variables ***
${API_BASE}           http://127.0.0.1:8000/api/v1
${REPORT_DIR}         rpa/logs/daily_scheduler
${MAX_SANE_PRICE}     2000
${MIN_SANE_PRICE}     0.5
@{FETCHED_MEDS}       # populated in Step 2


*** Test Cases ***
Step 1 — Smoke Gate: API Must Be Alive Before Scrape Proceeds
    [Documentation]    Mirrors the smoke gate in scheduler_entry.py.
    ...                The daily job will ABORT if this step fails — no prices are written.
    ...                PASS means: API is up and the /resolve-medicine endpoint responds.
    [Tags]    scheduler    smoke-gate    P1
    ${body}=    Create Dictionary    raw_text=Crocin    source=typed
    ${resp}=    POST On Session    api    /resolve-medicine    json=${body}
    Status Should Be    200    ${resp}
    ${json}=    Set Variable    ${resp.json()}
    Should Be True    ${json}[matched]
    ...    msg=API returned matched=false — smoke gate would abort daily pipeline.
    Log    ✅ Smoke gate PASSED. API is alive and resolving medicines correctly.    console=True

Step 2 — Price Fetch: Collect All Medicine Prices
    [Documentation]    Fetches latest prices for all medicines from the API.
    ...                Simulates the scraper collecting current market prices.
    [Tags]    scheduler    fetch    P1
    ${resp}=    GET On Session    api    /users/1/tracked-medicines
    Status Should Be    200    ${resp}
    ${meds}=    Set Variable    ${resp.json()}
    Should Not Be Empty    ${meds}    msg=No tracked medicines found — nothing to scrape.

    ${today}=    Get Current Date    result_format=%Y-%m-%d %H:%M
    Log    === Daily Price Fetch — ${today} IST ===    console=True

    FOR    ${med}    IN    @{meds}
        Log    Fetched: ${med}[brand_name] = ₹${med}[latest_price]    console=True
        Should Be True    '${med}[latest_price]' != 'None'
        ...    msg=No price found for ${med}[brand_name] — scraper failure.
    END
    Set Suite Variable    @{FETCHED_MEDS}    @{meds}
    Log    ✅ Fetched prices for ${meds.__len__()} medicines.    console=True

Step 3 — Simulate Write: New Price_History Rows Would Be Inserted
    [Documentation]    In the live scheduler (scheduler_entry.py), this step calls
    ...                _write_price_history() to INSERT new rows into PostgreSQL.
    ...                Here we simulate and log what would be written.
    [Tags]    scheduler    write    P1
    ${count}=    Set Variable    0
    ${now}=      Get Current Date    result_format=%Y-%m-%dT%H:%M:%S
    FOR    ${med}    IN    @{FETCHED_MEDS}
        Log    [DB WRITE] INSERT INTO price_history (medicine_id=${med}[medicine_id], source=primary_pharmacy, price=${med}[latest_price], scraped_at=${now})    console=True
        ${count}=    Evaluate    ${count} + 1
    END
    Should Be True    ${count} > 0    msg=No price_history rows were written.
    Log    ✅ Simulated ${count} price_history inserts into PostgreSQL.    console=True

Step 4 — Data Sanity: Validate Every Fetched Price Is Plausible
    [Documentation]    Runs the same sanity check logic as data_sanity.robot.
    ...                Ensures no price is above ₹2000 or below ₹0.50 (implausible values).
    [Tags]    scheduler    sanity    P1
    FOR    ${med}    IN    @{FETCHED_MEDS}
        ${price}=    Set Variable    ${med}[latest_price]
        Should Be True    ${price} >= ${MIN_SANE_PRICE}
        ...    msg=Price for ${med}[brand_name] (₹${price}) is below minimum ₹${MIN_SANE_PRICE}.
        Should Be True    ${price} <= ${MAX_SANE_PRICE}
        ...    msg=Price for ${med}[brand_name] (₹${price}) exceeds max ₹${MAX_SANE_PRICE} — likely a scrape error.
    END
    Log    ✅ All prices passed sanity check (₹${MIN_SANE_PRICE} – ₹${MAX_SANE_PRICE} range).    console=True

Step 5 — Savings Report: Generate and Log the Daily Summary
    [Documentation]    Final step of the daily pipeline. Generates a human-readable
    ...                savings report comparing each medicine to its Jan Aushadhi substitute.
    ...                In production, this would be emailed/WhatsApp'd to the user.
    [Tags]    scheduler    report    P1
    ${today}=    Get Current Date    result_format=%d-%b-%Y
    Log    ============================================================    console=True
    Log    🏥 GenuineRX Daily Savings Report — ${today}                   console=True
    Log    ============================================================    console=True

    FOR    ${med}    IN    @{FETCHED_MEDS}
        ${mid}=    Set Variable    ${med}[medicine_id]
        ${sresp}=    GET On Session    api    /medicines/${mid}/substitutes
        ${subs}=    Set Variable    ${sresp.json()}[substitutes]

        ${jan_sub}=    Set Variable    ${None}
        FOR    ${s}    IN    @{subs}
            Run Keyword If    ${s}[is_jan_aushadhi]    Set Suite Variable    ${jan_sub}    ${s}
        END

        Run Keyword If    ${jan_sub} != ${None}
        ...    Log    ${med}[profile_label] | ${med}[brand_name] ₹${med}[latest_price] → Jan Aushadhi ₹${jan_sub}[price] | Save ₹${jan_sub}[savings_rupees] (${jan_sub}[savings_percent]%)    console=True
        ...    ELSE
        ...    Log    ${med}[profile_label] | ${med}[brand_name] ₹${med}[latest_price] → No Jan Aushadhi substitute    console=True
    END

    Log    ============================================================    console=True
    Log    ✅ Daily savings report complete.    console=True


*** Keywords ***
Initialize Daily Run
    [Documentation]    Creates API session and the log directory for the daily run.
    Create Session    api    ${API_BASE}    verify=False
    Create Directory    ${REPORT_DIR}
    ${now}=    Get Current Date    result_format=%Y-%m-%d %H:%M IST
    Log    GenuineRX Daily Scheduler — Job started at ${now}    console=True
