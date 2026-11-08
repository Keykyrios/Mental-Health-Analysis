# Exam-aspirant mental healthcare: market and unit-economics analysis

Analysis behind a seed-stage pitch for an asynchronous, WhatsApp-first mental-health service for Indian competitive-exam aspirants.

**Read this first:** the market data is real and sourced (see `SOURCES.md`). The unit economics and cash runway are a **model built on founder assumptions**, not pilot measurements. No pilot data was available when this was written.

## Run it
```bash
pip install -r requirements.txt
python src/analysis.py        # writes figures/*.png, figures/state_table.csv, results.json
```
Random seed is fixed, so results reproduce exactly.

## What it finds
| Finding | Number | Kind |
|---|---|---|
| Student suicides, 2014 to 2024 | 8,068 to 14,488 (+79.6%, 6.0% a year) | data (NCRB) |
| Share of NEET UG registrations in the top 5 states | 46.8% | data |
| UP, Bihar, MP, Rajasthan: share and growth 2023-24 | 34% of registrations, +25.6% against +15.2% nationally | data |
| LTV to CAC, base | 2.76x (deck rounds to 2.75x) | model |
| LTV to CAC, Monte Carlo (50,000 draws) | median 2.17x; 14.1% of draws reach 3x | model |
| Cash left at month 24 on a Rs 8 Cr raise | Rs 3.28 Cr base; Rs 1.39 Cr bad case | model |
| Fixed-cost multiple at which cash hits zero (plan volume) | 1.56x | model |
| Cash left with zero sign-ups | Rs 0.92 Cr | model |
| Cash hits zero under cost-creep stress | 26% of 20,000 futures | model, depends on our assumed creep range |

## Figures
`figures/` holds eleven PNGs: trend, state bubble chart, 3D state bars, 3D state scatter, Lorenz curve, rank correlations, tornado, 3D LTV-to-CAC surface, Monte Carlo histogram, 3D cash surface, cash fan chart, cohort curves.

## Limits, stated plainly
- NEET UG covers medical aspirants only. JEE, CUET and UPSC state data were not found in a usable form.
- Registrations are by registration state, not where the student studies (Kota students may be counted at home).
- Pass rate by state is a pressure proxy. It is **not** evidence of distress or of demand for therapy.
- Straight-line extrapolation to 2027 is arithmetic, not a forecast.
- The model assumes sign-up volume does not fall when CAC rises. In practice it may.
- Digital phase-2 devices have no validation evidence here.
- If anyone is in crisis, text-based care is not the right tool: contact Tele-MANAS 14416 or local emergency services.
