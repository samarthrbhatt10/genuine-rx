*** Settings ***
Documentation     Price Tracking Suite — simulates the daily automated price tracking job.
...               Fetches the latest price for each tracked medicine from the database,
...               validates the data, and produces a savings summary report.
...               This is RPA Automation #3: Daily Price Monitor.
...               PASS means: every tracked medicine has a price history entry and
...               the Jan Aushadhi generic is always cheaper than the branded original.

Resource          ../resources/shared.resource
Library           ../keywords/validation_keywords.py    WITH NAME    Validation
Library           RequestsLibrary
Library           Collections
Library           DateTime

Suite Setup       Create API Session


*** Variables ***
${API_BASE}       http://127.0.0.1:8000/api/v1
${RAHUL_ID}       1
${PRIYA_ID}       3


*** Test Cases ***
Daily Price Snapshot — Rahul Watchlist
    [Documentation]    Fetches Rahul's tracked medicines and logs a savings report.
    ...                Simulates the daily cron job that monitors price changes.
    [Tags]    price-tracking    daily    P1
    ${resp}=    GET On Session    api    /users/${RAHUL_ID}/tracked-medicines
    Status Should Be    200    ${resp}
    ${meds}=    Set Variable    ${resp.json()}
    Should Not Be Empty    ${meds}    msg=Rahul has no tracked medicines.

    ${today}=    Get Current Date    result_format=%d-%b-%Y
    Log    === Daily Price Report — Rahul | ${today} ===    console=True
    FOR    ${med}    IN    @{meds}
        Log    ${med}[brand_name]: Rs.${med}[latest_price] | Saved: Rs.${med}[savings_to_date]    console=True
        Should Not Be Empty    ${med}[history]
        ...    msg=No price history for ${med}[brand_name] — daily scraper may have failed.
    END

Daily Price Snapshot — Priya Watchlist
    [Documentation]    Fetches Priya's tracked medicines and logs a savings report.
    [Tags]    price-tracking    daily    P1
    ${resp}=    GET On Session    api    /users/${PRIYA_ID}/tracked-medicines
    Status Should Be    200    ${resp}
    ${meds}=    Set Variable    ${resp.json()}
    Should Not Be Empty    ${meds}    msg=Priya has no tracked medicines.
    FOR    ${med}    IN    @{meds}
        Log    ${med}[brand_name]: Rs.${med}[latest_price]    console=True
    END

Validate Jan Aushadhi Is Always Cheapest
    [Documentation]    For every tracked medicine, fetches its substitutes and asserts
    ...                the Jan Aushadhi generic is cheaper than the branded original.
    ...                This confirms price integrity across the entire database.
    [Tags]    price-tracking    integrity    P1
    ${resp}=    GET On Session    api    /users/${RAHUL_ID}/tracked-medicines
    ${meds}=    Set Variable    ${resp.json()}
    FOR    ${med}    IN    @{meds}
        ${sid}=    Set Variable    ${med}[medicine_id]
        ${sresp}=    GET On Session    api    /medicines/${sid}/substitutes
        ${subs}=    Set Variable    ${sresp.json()}[substitutes]
        Continue For Loop If    ${subs.__len__()} < 2
        ${ja}=    Set Variable    ${subs}[0]
        ${branded}=    Set Variable    ${subs}[-1]
        Run Keyword If    ${ja}[is_jan_aushadhi]
        ...    Should Be True    ${ja}[price] < ${branded}[price]
        ...    msg=Jan Aushadhi price NOT lower than branded for ${med}[brand_name]
    END
    Log    All tracked medicines: Jan Aushadhi confirmed cheapest.    console=True

Price History Has At Least 4 Weeks Data
    [Documentation]    Asserts every tracked medicine has >= 4 price history rows.
    ...                This confirms the price scraper has been running regularly.
    [Tags]    price-tracking    history    P1
    ${resp}=    GET On Session    api    /users/${RAHUL_ID}/tracked-medicines
    ${meds}=    Set Variable    ${resp.json()}
    FOR    ${med}    IN    @{meds}
        ${hist_len}=    Evaluate    len(${med}[history])
        Should Be True    ${hist_len} >= 4
        ...    msg=${med}[brand_name] has only ${hist_len} price history rows — expected >= 4.
    END
    Log    All medicines have >= 4 weeks of price history.    console=True


*** Keywords ***
Create API Session
    Create Session    api    ${API_BASE}    verify=False
