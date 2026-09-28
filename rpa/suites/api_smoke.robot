*** Settings ***
Documentation     API Smoke Suite — validates the live FastAPI backend responds correctly
...               to all core endpoints without requiring a browser or Playwright install.
...               This suite can run in the standard Python 3.13 venv.
...               PASS means: all API endpoints return expected HTTP 200 responses
...               with well-formed JSON bodies.
...               Run this before any demo or submission to confirm the server is up.

Resource          ../resources/shared.resource
Library           RequestsLibrary
Library           Collections

Suite Setup       Create API Session


*** Variables ***
${API_BASE}          http://127.0.0.1:8000/api/v1
${CROCIN_NAME}       Crocin
${CROCIN_ID}         132
${RAHUL_USER_ID}     1
${PRIYA_USER_ID}     3


*** Test Cases ***
POST Resolve Medicine Returns Match For Crocin
    [Documentation]    Calls /resolve-medicine with raw text 'Crocin' and asserts
    ...                the response contains a medicine_id and confidence score above 80.
    [Tags]    api    smoke    P1
    ${body}=    Create Dictionary    raw_text=${CROCIN_NAME}    source=typed
    ${resp}=    POST On Session    api    /resolve-medicine    json=${body}
    Status Should Be    200    ${resp}
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    medicine_id
    Dictionary Should Contain Key    ${json}    confidence
    Should Be True    ${json}[confidence] >= 0.80
    ...    msg=Fuzzy match confidence too low: ${json}[confidence]
    Log    Resolved: ${json}[brand_name] (id=${json}[medicine_id], confidence=${json}[confidence]%)    console=True

GET Substitutes Returns Jan Aushadhi First
    [Documentation]    Calls /medicines/{id}/substitutes for Crocin (id=132) and asserts
    ...                the first result is a Jan Aushadhi generic with positive savings.
    [Tags]    api    smoke    P1
    ${resp}=    GET On Session    api    /medicines/${CROCIN_ID}/substitutes
    Status Should Be    200    ${resp}
    ${json}=    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${json}    substitutes
    ${subs}=    Set Variable    ${json}[substitutes]
    Should Not Be Empty    ${subs}    msg=No substitutes returned for Crocin.
    ${first}=    Set Variable    ${subs}[0]
    Should Be True    ${first}[is_jan_aushadhi]
    ...    msg=First substitute is not Jan Aushadhi: ${first}[brand_name]
    Should Be True    ${first}[savings_percent] > 0
    ...    msg=Savings percentage is zero or negative.
    Log    Top substitute: ${first}[brand_name] @ Rs.${first}[price] (${first}[savings_percent]% savings)    console=True

GET Rahul Tracked Medicines Returns Watchlist
    [Documentation]    Calls /users/{id}/tracked-medicines for Rahul (user 1) and asserts
    ...                the response is a non-empty list with brand_name, history, and savings fields.
    [Tags]    api    smoke    P1
    ${resp}=    GET On Session    api    /users/${RAHUL_USER_ID}/tracked-medicines
    Status Should Be    200    ${resp}
    ${json}=    Set Variable    ${resp.json()}
    Should Not Be Empty    ${json}    msg=Rahul's watchlist is empty — did seeding run?
    ${first}=    Set Variable    ${json}[0]
    Dictionary Should Contain Key    ${first}    brand_name
    Dictionary Should Contain Key    ${first}    history
    Dictionary Should Contain Key    ${first}    savings_to_date
    Log    Rahul's watchlist: ${json.__len__()} medicines, first=${first}[brand_name]    console=True

GET Priya Tracked Medicines Returns Watchlist
    [Documentation]    Calls /users/{id}/tracked-medicines for Priya (user 3) and asserts
    ...                the response is a non-empty list.
    [Tags]    api    smoke    P1
    ${resp}=    GET On Session    api    /users/${PRIYA_USER_ID}/tracked-medicines
    Status Should Be    200    ${resp}
    ${json}=    Set Variable    ${resp.json()}
    Should Not Be Empty    ${json}    msg=Priya's watchlist is empty — did seeding run?
    Log    Priya's watchlist: ${json.__len__()} medicines    console=True

POST Resolve Medicine Handles Typo Gracefully
    [Documentation]    Sends a misspelled medicine name 'crociin' and asserts the fuzzy
    ...                matcher still resolves it with confidence above 70.
    [Tags]    api    smoke    fuzzy
    ${body}=    Create Dictionary    raw_text=crociin    source=typed
    ${resp}=    POST On Session    api    /resolve-medicine    json=${body}
    Status Should Be    200    ${resp}
    ${json}=    Set Variable    ${resp.json()}
    Should Be True    ${json}[confidence] >= 0.70
    ...    msg=Fuzzy match too weak for misspelling 'crociin': ${json}[confidence]
    Log    Fuzzy resolved 'crociin' -> ${json}[brand_name] @ ${json}[confidence]%    console=True


*** Keywords ***
Create API Session
    [Documentation]    Creates a reusable requests session for the FastAPI server.
    Create Session    api    ${API_BASE}    verify=False
