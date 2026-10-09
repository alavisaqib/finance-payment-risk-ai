# Data dictionary

All inputs and training records are synthetic. Fields are numeric; counts and cents must be integers.

- `amount_usd` — Payment amount (USD); valid range 1–100000; real number.
- `transactions_1h` — Transactions in last hour; valid range 1–100; integer.
- `account_age_days` — Account age (days); valid range 0–5000; integer.
- `distance_km` — Distance from usual location (km); valid range 0–20000; real number.

`target`: synthetic suspicious-payment label in probability.

Labels come from a noisy logistic function of amount, velocity, account age and location distance. No customer data, protected attributes or genuine fraud outcomes are included.
