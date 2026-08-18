*** Settings ***
Documentation       Smoke tests for the UMANG Jan Aushadhi RPA scraping flow.
...                 These tests ensure we can successfully reach the official UMANG PMBJP portal,
...                 perform a search, and extract structured medicine prices using CSS selectors.

Resource            ../resources/shared.resource
Library             ../keywords/scraping_keywords.py

Suite Setup         Open Pharmacy Source    ${PRIMARY_PHARMACY_URL}

*** Test Cases ***
Verify UMANG Search and Extraction for Paracetamol
    [Documentation]    Searches for Paracetamol on UMANG and verifies the first result returns Name, Size, and Price.
    [Tags]             smoke    umang

    ${result} =    Scrape UMANG Medicine    ${SMOKE_SEARCH_SALT}
    
    Log    Extracted Data: ${result}
    
    Should Not Be Empty    ${result}[name]
    Should Not Be Empty    ${result}[size]
    Should Not Be Empty    ${result}[price]
    Should Contain         ${result}[name]    ${SMOKE_EXPECTED_NAME_SUBSTR}
    Should Contain         ${result}[price]   ₹
