*** Settings ***
Documentation     Data sanity suite — runs after every scrape batch to validate
...               that all newly written price_history rows are plausible.
...               PASS means: every price written in the current run passes the
...               300%-deviation check in Validate Price Sanity.
...               Zero or implausible results are a hard failure, not a warning.

Resource          ../resources/shared.resource
Library           ../keywords/validation_keywords.py    WITH NAME    Validation


*** Variables ***
# These are populated by the scheduler before invoking this suite.
# Keys: medicine_id (int) -> new_price (float)
@{SCRAPE_BATCH}    # list of dicts: [{medicine_id, new_price, brand_name}, ...]


*** Test Cases ***
All Scraped Prices Pass Sanity Check
    [Documentation]    Iterates over every (medicine_id, price) pair written in the
    ...                current scrape run and asserts each passes Validate Price Sanity.
    ...                The suite is expected to be invoked with SCRAPE_BATCH populated
    ...                by the scheduler after scraping completes.
    Should Not Be Empty    ${SCRAPE_BATCH}
    ...    msg=SCRAPE_BATCH is empty — no prices were scraped. This is a hard failure.
    FOR    ${item}    IN    @{SCRAPE_BATCH}
        ${passed}=    Validation.Validate Price Sanity
        ...    medicine_id=${item}[medicine_id]
        ...    new_price=${item}[new_price]
        Should Be True    ${passed}
        ...    msg=Price sanity FAILED for ${item}[brand_name] (id=${item}[medicine_id]) — new price ${item}[new_price] is implausible.
    END
    Log    All ${SCRAPE_BATCH.__len__()} scraped prices passed sanity check.    console=True
