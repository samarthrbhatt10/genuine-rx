*** Settings ***
Documentation     Regression suite — fixed input/output table for Normalize Salt String.
...               PASS means: every known raw salt string produces the exact expected
...               (canonical_name, strength_mg) output.
...               No network calls, no database required. Run on every commit.

Resource          ../resources/shared.resource
Library           ../keywords/parsing_keywords.py    WITH NAME    Parsing

Suite Setup       Inject Test Salt Aliases


*** Test Cases ***
Normalize Single Salts
    [Documentation]    Tests basic single-salt strings with canonical names and common aliases.
    [Template]         Salt String Should Normalize To
    # Raw string                        Expected name      Expected mg
    Paracetamol 500mg                   Paracetamol        500.0
    Paracetamol 500 mg                  Paracetamol        500.0
    PCM 500mg                           Paracetamol        500.0
    Acetaminophen 500mg                 Paracetamol        500.0
    Metformin 500mg                     Metformin          500.0
    Metformin HCl 500mg                 Metformin          500.0
    Metformin Hydrochloride 500 mg      Metformin          500.0
    Atorvastatin 10mg                   Atorvastatin       10.0
    Atorvastatin Calcium 10 mg          Atorvastatin       10.0
    Glibenclamide 5mg                   Glibenclamide      5.0

Normalize Unit Conversions
    [Documentation]    Verifies g and mcg conversions produce correct mg values.
    [Template]         Salt String Should Normalize To
    Atorvastatin 0.01g                  Atorvastatin       10.0
    Metformin 0.5g                      Metformin          500.0

Normalize Combination Salts
    [Documentation]    Verifies multi-salt strings produce the correct number of results.
    ${result}=    Parsing.Normalize Salt String    Metformin 500mg + Glibenclamide 5mg
    Length Should Be    ${result}    2
    ${names}=    Evaluate    [r[0] for r in ${result}]
    Should Contain    ${names}    Metformin
    Should Contain    ${names}    Glibenclamide

    ${result2}=    Parsing.Normalize Salt String    Paracetamol 500mg / Metformin 500mg
    Length Should Be    ${result2}    2


*** Keywords ***
Inject Test Salt Aliases
    [Documentation]    Builds an in-memory salt table for the regression suite
    ...                so no database connection is needed.
    ${salt_table}=    Evaluate    [__import__('matching_engine.types', fromlist=['SaltEntry']).SaltEntry(1, 'Paracetamol', frozenset({'pcm', 'acetaminophen', 'paracetamol tab'})), __import__('matching_engine.types', fromlist=['SaltEntry']).SaltEntry(2, 'Metformin', frozenset({'metformin hcl', 'metformin hydrochloride', 'mf 500'})), __import__('matching_engine.types', fromlist=['SaltEntry']).SaltEntry(3, 'Atorvastatin', frozenset({'atorvastatin calcium', 'atorva'})), __import__('matching_engine.types', fromlist=['SaltEntry']).SaltEntry(4, 'Glibenclamide', frozenset({'glyburide', 'glibenclamide 5'}))]
    Parsing.Inject Salt Aliases For Testing    ${salt_table}

Salt String Should Normalize To
    [Arguments]    ${raw}    ${expected_name}    ${expected_mg}
    [Documentation]    Normalizes ${raw} and asserts the first result matches expected values.
    ${result}=    Parsing.Normalize Salt String    ${raw}
    Should Not Be Empty    ${result}
    ...    msg=Normalize Salt String returned empty for: "${raw}"
    ${name}=       Set Variable    ${result}[0][0]
    ${mg}=         Set Variable    ${result}[0][1]
    Should Be Equal    ${name}    ${expected_name}
    ...    msg=Expected canonical name '${expected_name}' but got '${name}' for input: "${raw}"
    Should Be Equal As Numbers    ${mg}    ${expected_mg}
    ...    msg=Expected strength ${expected_mg} mg but got ${mg} for input: "${raw}"
