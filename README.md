# victron-exporter

Prometheus exporter for Victron GX devices (Cerbo GX, Venus GX, or anything running Venus OS). It reads the GX over MQTT and serves metrics for Grafana Alloy or Prometheus, and ships with a Grafana dashboard and alert rules for running Victron inverter/chargers as UPS feeds. Read-only: the only message it sends a GX is the MQTT keepalive.

## Deploy

1. Copy `config.example.yaml` to `config.yaml` and list your feeds.
2. Add the `victron-exporter` service from `compose.yaml` to the Compose project that runs Alloy, so both share a network, then `docker compose up -d victron-exporter`. The image is published at `ghcr.io/lewis-green/victron-exporter` for amd64 and arm64.
3. Add `alloy/victron.alloy` to your Alloy config. Change `prometheus.remote_write.default.receiver` to the name of your remote-write component, then reload Alloy.
4. Import `grafana/victron-ups-feeds.json` into Grafana and pick your Mimir data source.
5. Load `rules/victron.rules.yaml` into the Mimir ruler, for example `mimirtool rules load rules/victron.rules.yaml`.

The exporter host must reach each GX on TCP 1883. MQTT on the GX is unauthenticated, so keep this on the management network and do not publish port 9105 beyond Alloy.

## Check it

`docker compose exec victron-exporter python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:9105/metrics').read().decode())" | grep victron_up`

Each feed should show `victron_up{feed="..."} 1.0`.

## Metrics

All metrics have a `feed` label. See `exporter/victron_exporter/mapping.py` for the full topic table.

- `victron_up`, `victron_last_update_timestamp_seconds`: collection health.
- `victron_grid_connected`, `victron_vebus_state`, `victron_ac_*`, `victron_vebus_dc_power_watts`: inverter and grid.
- `victron_battery_*`: SOC, voltage, current, power, temperature, cell min and max, charge limits.
- `victron_alarm{source,alarm}`: 0 ok, 1 warning, 2 alarm.

If a GX stops sending anything for `stale_seconds` (default 120), its values disappear from `/metrics` and `VictronFeedDataStale` fires after 5 minutes.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -r exporter/requirements-dev.txt
cd exporter && ../.venv/bin/python -m pytest -q
```

Regenerate the dashboard after editing `grafana/build_dashboard.py`: `.venv/bin/python grafana/build_dashboard.py`.

## Scope and limits

- Victron only: it relies on the Venus OS MQTT topic layout and keepalive.
- Single-phase: AC values are read from L1.
- One inverter/charger and one battery service per GX. With several, their values overwrite each other.
- Solar chargers, grid meters and PV inverters are not exported. Add rows to `FIXED` in `mapping.py` to cover them.
- MQTT must be enabled on the GX (Settings, Services).

## SOC divergence

`VictronSocDivergence` fires when feeds that should match report different SOC while on grid. This usually means one BMS counter is stale. Many BMSs only re-sync SOC at a full-charge voltage threshold; if the GX's DVCC charge voltage limit sits below that threshold, the counter never corrects. Briefly raising the limit above the threshold re-syncs it. As an example, a Seplos 16S BMS re-syncs when the pack passes 56.0 V.

## Licence

MIT. See `LICENSE`.
