*** Settings ***
Documentation     Smoke suite — verifies the primary pharmacy source is reachable and
...               structurally intact before a scheduled full scrape is allowed to run.
...               PASS means: homepage loads, search bar resolves, and the known product
...               page exposes all four expected selectors.
...               If this suite fails, the scheduled scrape MUST NOT proceed.
...               Target runtime: under 30 seconds.

Resource          ../resources/shared.resource
Library           ../keywords/scraping_keywords.py    WITH NAME    Scraping

Suite Teardown    Close Browser    # Browser Library keyword — cleans up Playwright session


*** Test Cases ***
Homepage Loads And Search Bar Is Present
    [Documentation]    Opens the primary pharmacy URL and confirms the search bar is visible.
    ...                Failure here means the site is down or has fundamentally changed layout.
    Open Pharmacy Source    ${PRIMARY_PHARMACY_URL}
    ${element_count}=    Scraping.Get Element Count    ${SEL_SEARCH_BAR}
    Should Be True    ${element_count} > 0
    ...    msg=Search bar selector '${SEL_SEARCH_BAR}' not found — site may be down or selector needs update.

Known Product Page Has All Required Selectors
    [Documentation]    Navigates to a known medicine page and asserts that all four selectors
    ...                (name, mrp, price, salt_text) resolve to non-empty text.
    ...                Failure here means the HTML structure changed — update selectors in shared.resource.
    ${data}=    Scraping.Scrape Medicine Page    ${SMOKE_PRODUCT_URL}
    Should Not Be Empty    ${data}[name]           msg=Medicine name selector returned empty.
    Should Not Be Empty    ${data}[mrp]            msg=MRP selector returned empty.
    Should Not Be Empty    ${data}[price]          msg=Price selector returned empty.
    Should Not Be Empty    ${data}[raw_salt_text]  msg=Salt text selector returned empty.
    Should Contain         ${data}[name]    ${SMOKE_EXPECTED_NAME_SUBSTR}
    ...    msg=Expected '${SMOKE_EXPECTED_NAME_SUBSTR}' in medicine name but got: ${data}[name]
    Log    Smoke passed: ${data}[name] @ Rs.${data}[price]    console=True
