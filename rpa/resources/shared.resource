*** Settings ***
Documentation     Shared variables, imports, and configuration for all Genuine RX RF suites.
...               Edit this file to change URLs, timeouts, or selectors globally.
...               Never hardcode these values inside individual .robot files.

*** Variables ***
# Primary pharmacy source (1mg / Tata Health)
${PRIMARY_PHARMACY_URL}         https://www.1mg.com
${PHARMACY_MEDICINE_BASE_URL}   https://www.1mg.com/drugs

# Browser timeouts (milliseconds)
${PAGE_LOAD_TIMEOUT}            15000
${NETWORK_IDLE_TIMEOUT}         5000

# CSS selectors — update here if 1mg changes its HTML structure.
# Verify these against the live site before each scrape run.
${SEL_SEARCH_BAR}               input[placeholder*='Search'], input[data-testid='search-input']
${SEL_MEDICINE_NAME}            h1.style__pro-title___3zKNC, h1[itemprop='name']
${SEL_MRP}                      span.style__price-tag___KzOkY, .drug-price .original-price
${SEL_PRICE}                    span.style__price___mM6an, .drug-price .discounted-price
${SEL_SALT_TEXT}                div.DrugHeader__meta-value___vqYVV, .saltInfo .salt-composition

# Smoke-test: a known product URL and its expected medicine name.
# Update this whenever 1mg changes product URLs.
${SMOKE_PRODUCT_URL}            https://www.1mg.com/drugs/crocin-500mg-tablet-5960
${SMOKE_EXPECTED_NAME_SUBSTR}   Crocin

# Jan Aushadhi PDF (download manually and set path before running PDF parse)
${JAN_AUSHADHI_PDF_PATH}        %{GENUINE_RX_JAN_AUSHADHI_PDF_PATH=data/jan_aushadhi_pricelist.pdf}

# Database / scheduler
${DB_URL}                       %{GENUINE_RX_DB_URL=}
