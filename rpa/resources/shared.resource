*** Settings ***
Documentation     Shared variables, imports, and configuration for all Genuine RX RF suites.
...               Edit this file to change URLs, timeouts, or selectors globally.
...               Never hardcode these values inside individual .robot files.

*** Variables ***
# Primary generic pharmacy source (UMANG Jan Aushadhi Sugam)
${PRIMARY_PHARMACY_URL}         https://web.umang.gov.in/web_new/department?url=pmjp%2Fservice%2F1089&dept_id=180&dept_name=Jan%20Aushadhi%20Sugam

# Browser timeouts (milliseconds)
${PAGE_LOAD_TIMEOUT}            20000
${NETWORK_IDLE_TIMEOUT}         5000

# CSS selectors — UMANG Web structure
${SEL_SEARCH_ICON}              .search-page, .fa-search
${SEL_SEARCH_INPUT}             input.search-box, input[placeholder='Search Medicine']
${SEL_MEDICINE_NAME}            mat-cell.mat-column-MedicineName p
${SEL_SIZE}                     mat-cell.mat-column-Size span, mat-cell.mat-column-Size p
${SEL_PRICE}                    mat-cell.mat-column-Price p

# Smoke-test: search term and expected result
${SMOKE_SEARCH_SALT}            Paracetamol
${SMOKE_EXPECTED_NAME_SUBSTR}   Paracetamol Tablets IP

# Jan Aushadhi PDF (download manually and set path before running PDF parse)
${JAN_AUSHADHI_PDF_PATH}        %{GENUINE_RX_JAN_AUSHADHI_PDF_PATH=data/jan_aushadhi_pricelist.pdf}

# Database / scheduler
${DB_URL}                       %{GENUINE_RX_DB_URL=}
