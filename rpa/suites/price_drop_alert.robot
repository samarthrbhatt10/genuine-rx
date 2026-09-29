*** Settings ***
Documentation     Price-Drop Alert Bot — RPA Automation #6.
...               Proves the full alert loop end to end:
...               detect (price drop / Jan Aushadhi option) -> build email -> deliver -> dedupe.
...               Delivery is real SMTP when GENUINE_RX_SMTP_USER/PASSWORD are set, otherwise
...               the email is saved to rpa/outbox/ (open it in a browser for the demo).
...               PASS means: alerts fire once, with correct content, and never repeat.
...
...               Run:  robot -d rpa/logs/alerts rpa/suites/price_drop_alert.robot

Library           ../keywords/alert_keywords.py    WITH NAME    Alerts
Library           Collections
Library           OperatingSystem

Suite Setup       Alerts.Reset Alert Log
Suite Teardown    Alerts.Close Alert Connection


*** Variables ***
${DEMO_BRAND}       Crocin
${DROP_PCT}         20


*** Test Cases ***
Jan Aushadhi Alternatives Are Detected And Emailed
    [Documentation]    First run after a reset must find at least one Jan Aushadhi option
    ...                and deliver at least one email.
    [Tags]    alerts    jan-aushadhi    P1
    ${s}=    Alerts.Run Price Alert Bot
    Should Be True    ${s}[jan_aushadhi] >= 1    msg=No Jan Aushadhi alternative detected for any tracked medicine.
    Should Be Empty    ${s}[errors]    msg=Email delivery errors: ${s}[errors]
    ${n}=    Get Length    ${s}[emails]
    Should Be True    ${n} >= 1    msg=No alert email was delivered (skipped: ${s}[skipped]).
    Log    Delivered ${n} email(s): ${s}[emails]    console=True

Second Run Sends Nothing New
    [Documentation]    Dedupe check — the same alerts must never be emailed twice.
    [Tags]    alerts    dedupe    P1
    ${s}=    Alerts.Run Price Alert Bot
    Should Be Equal As Integers    ${s}[drops]           0
    Should Be Equal As Integers    ${s}[jan_aushadhi]    0
    Should Be Empty    ${s}[emails]

Simulated Price Drop Triggers An Alert Email
    [Documentation]    Simulates the scraper finding a ${DROP_PCT}% cheaper ${DEMO_BRAND}; the bot
    ...                must email exactly that drop, with old and new price in the message.
    [Tags]    alerts    price-drop    P1
    ${d}=    Alerts.Simulate Price Drop    ${DEMO_BRAND}    ${DROP_PCT}
    Log    Scraper saw ${d}[brand_name]: Rs.${d}[old_price] -> Rs.${d}[new_price]    console=True
    ${s}=    Alerts.Run Price Alert Bot
    Should Be True    ${s}[drops] >= 1    msg=Price drop was not detected.
    Should Be Empty    ${s}[errors]
    ${email}=    Set Variable    ${s}[emails][0]
    Should Contain    ${email}[subject]    ${DEMO_BRAND}
    Should Contain    ${email}[subject]    Price drop
    ${new}=    Evaluate    f"Rs.{${d}[new_price]:.2f}"
    ${old}=    Evaluate    f"Rs.{${d}[old_price]:.2f}"
    Should Contain    ${email}[text]    ${new}
    Should Contain    ${email}[text]    ${old}
    Should Contain    ${email}[text]    confirm any substitute with your doctor

Outbox File Is A Valid HTML Email
    [Documentation]    Only meaningful in demo mode (no SMTP) — the saved file must contain the alert.
    [Tags]    alerts    outbox
    Alerts.Reset Alert Log
    ${d}=    Alerts.Simulate Price Drop    ${DEMO_BRAND}    ${DROP_PCT}
    ${s}=    Alerts.Run Price Alert Bot
    ${email}=    Set Variable    ${s}[emails][0]
    Pass Execution If    '${email}[mode]' == 'smtp'    Real SMTP in use — no outbox file to inspect.
    ${html}=    Alerts.Read Outbox Email    ${email}[path]
    Should Contain    ${html}    Genuine RX
    Should Contain    ${html}    ${DEMO_BRAND}
    Log    Open in browser: ${email}[path]    console=True

Dry Run Does Not Record Or Send
    [Documentation]    --dry-run must leave alert_log untouched so a real run still fires.
    [Tags]    alerts    dry-run
    Alerts.Reset Alert Log
    ${s}=    Alerts.Run Price Alert Bot    dry_run=${TRUE}
    Should Be True    ${s}[jan_aushadhi] >= 1
    ${again}=    Alerts.Run Price Alert Bot    dry_run=${TRUE}
    Should Be Equal As Integers    ${again}[jan_aushadhi]    ${s}[jan_aushadhi]
