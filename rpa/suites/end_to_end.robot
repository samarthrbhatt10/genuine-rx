*** Settings ***
Documentation     End-to-end suite — full pipeline: prescription image -> OCR -> medicine
...               resolve -> substitute lookup -> savings report.
...               PASS means: a sample image produces a non-empty substitute list with
...               correct Jan Aushadhi entry ranked first and savings_pct computed.
...               Runs weekly. Logs total wall-clock time for the full path.
...               Requires P4 (OCR resolver) to be complete.

Resource          ../resources/shared.resource
Library           ../keywords/parsing_keywords.py      WITH NAME    Parsing
Library           ../keywords/validation_keywords.py   WITH NAME    Validation

Suite Setup       Load Salt Table From Database


*** Variables ***
# Sample prescription image used for end-to-end testing.
# Place a real scan at this path before running the weekly suite.
${E2E_SAMPLE_IMAGE}        %{GENUINE_RX_E2E_IMAGE_PATH=data/sample_prescription.jpg}
# Expected medicine name the OCR should resolve to (substring match)
${E2E_EXPECTED_MEDICINE}   Paracetamol
# medicine_id in the seeded database that corresponds to the sample image
${E2E_MEDICINE_ID}         132


*** Test Cases ***
Full Pipeline Produces Ranked Substitutes
    [Documentation]    Runs the complete path from medicine_id -> substitute list.
    ...                OCR step is handled by the OCR Resolver (P4); this suite
    ...                starts from a known medicine_id to keep it self-contained
    ...                until P4 is integrated.
    ...                Logs timing for demo purposes.
    ${start}=    Evaluate    __import__('time').time()

    ${substitutes}=    Parsing.Match Salt To Substitutes    ${E2E_MEDICINE_ID}

    ${elapsed}=    Evaluate    round(__import__('time').time() - ${start}, 2)
    Log    Substitute lookup completed in ${elapsed}s    console=True

    Should Not Be Empty    ${substitutes}
    ...    msg=No substitutes found for medicine_id=${E2E_MEDICINE_ID}.

    # Jan Aushadhi must be first
    ${first}=    Set Variable    ${substitutes}[0]
    Should Be True    ${first}[is_jan_aushadhi]
    ...    msg=Expected Jan Aushadhi brand ranked first, got: ${first}[brand_name]

    # Savings must be computed
    Should Not Be Equal    ${first}[savings_pct]    ${None}
    ...    msg=savings_pct is None — savings calculation failed.

    Log    Top substitute: ${first}[brand_name] @ Rs.${first}[price] (savings: ${first}[savings_pct]%)    console=True

Jan Aushadhi Price Is Lowest In Set
    [Documentation]    Verifies the Jan Aushadhi entry has the lowest price among results.
    ${substitutes}=    Parsing.Match Salt To Substitutes    ${E2E_MEDICINE_ID}
    ${jan}=            Set Variable    ${substitutes}[0]
    FOR    ${item}    IN    @{substitutes}
        Should Be True    ${jan}[price] <= ${item}[price]
        ...    msg=Jan Aushadhi price ${jan}[price] is not <= ${item}[brand_name] price ${item}[price].
    END

All Prices Pass Sanity Check
    [Documentation]    Runs Validate Price Sanity for every substitute in the result set.
    ${substitutes}=    Parsing.Match Salt To Substitutes    ${E2E_MEDICINE_ID}
    FOR    ${item}    IN    @{substitutes}
        ${ok}=    Validation.Validate Price Sanity
        ...    medicine_id=${item}[medicine_id]
        ...    new_price=${item}[price]
        Should Be True    ${ok}
        ...    msg=Price sanity failed for ${item}[brand_name] (id=${item}[medicine_id]).
    END


*** Keywords ***
Load Salt Table From Database
    [Documentation]    Loads the salt alias table from the database at suite start.
    Parsing.Load Salt Aliases
