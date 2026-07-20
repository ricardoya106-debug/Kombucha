# Kombucha fermentation digital twin

Streamlit dashboards for first (F1) and second (F2) fermentation, built
around a hand-tuned Fermentation Progress Index (FPI) and a regression model
that learns its own coefficients from batch history, with leave-one-batch-out
RMSE / MAE / R² validation comparing the two.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

This opens the home page; use the sidebar to reach the F1 dashboard, F2
dashboard, History log, and Model Performance page (Streamlit auto-detects
the `pages/` folder as a multipage app).

Leave **"Use simulated readings"** checked in the sidebar to try everything
without an Arduino attached — it generates a slow random walk of plausible
sensor values so you can see the FPI, alerts, and charts update.

## Project structure

```
app.py                       Home page
pages/
  1_F1_Dashboard.py          Live F1 metrics, FPI, alerts, per-sensor charts
  2_F2_Dashboard.py          Same for F2
  3_History.py                Filterable table of every stored reading + CSV export
  4_Model_Performance.py     FPI formula vs. regression model, RMSE/MAE/R2
kombucha/
  config.py                  Weights, ideal temps, thresholds — tune here first
  normalization.py           normalize(), temperature_factor(), f1_fpi(), f2_fpi()
  data_sim.py                 Synthetic batch generator (bootstraps the regression model)
  models.py                   Feature building + Ridge regression + leave-one-batch-out CV
  alerts.py                   Rule-based early-warning checks
  storage.py                  SQLite-backed reading history (kombucha_history.db)
  serial_reader.py            Real Arduino serial parsing + mock reading generator
kombucha_history.db          Created on first run
```

## Connecting your Arduino

`serial_reader.read_live()` expects one CSV line per reading over serial, in
this order:

- F1: `pH,conductivity,turbidity,color,temperature_C,water_level_pct`
- F2: `pressure_bar,temperature_C,water_level_pct`

e.g. your Arduino sketch's `Serial.println()` should output something like
`4.02,410.5,88.2,22.1,26.8,97.4`. If your sketch's field order differs,
either reorder your `Serial.println` or edit `F1_FIELDS` / `F2_FIELDS` at
the top of `serial_reader.py` to match. Uncheck "Use simulated readings" and
set the correct serial port in the sidebar once it's wired up.

## Things worth calibrating before you trust the numbers

1. **Sensor bounds.** `DEFAULT_BOUNDS` at the top of each dashboard page and
   in `4_Model_Performance.py` are reasonable starting guesses, not measured
   values. Once you've run a few real batches, replace them with your actual
   observed min/max per sensor.
2. **Ground truth for "done."** The regression model and the RMSE/MAE/R²
   comparison both need a real completion time to validate against. The
   Model Performance page asks which real batches are finished (so it knows
   the true days-remaining at every timestamp) — mark a batch complete only
   once you've confirmed by taste/titration/etc. that it was actually done.
3. **Batch count.** With only a handful of real batches, a regression model
   will overfit if trained on real data alone — that's what the synthetic
   batch blending slider on the Model Performance page is for. As you
   accumulate more real batches, dial the synthetic count down.
4. **FPI weights** in `config.py` are a starting point (`F1_WEIGHTS`,
   `F2_WEIGHTS`). Once you have several validated batches, you can compare
   which sensor's normalized value correlates most tightly with actual days
   remaining and adjust the weights accordingly.

## Alternatives if you outgrow Streamlit

Streamlit is a solid fit for this scale of project — quick to iterate on,
plenty for control-panel-style dashboards. If it ever feels limiting:

- **Grafana + InfluxDB**, with the Arduino posting to InfluxDB directly, is
  the standard choice for long-running IoT sensor dashboards with alerting
  built in — better if you want this running unattended for weeks.
- **Node-RED** if you want a visual flow editor between the Arduino and the
  dashboard/alerts instead of hand-written Python glue.
- Keep Streamlit for the modeling/analysis views and let one of the above
  handle long-term live monitoring — they're not mutually exclusive.

For a research project logged by hand over a few batches, though, Streamlit
alone (as built here) is genuinely enough — you likely don't need to add
another moving part.
