# Spike — Closed-loop auto-pause for the Kobra X

**Status:** ✅ schema fully mapped from the maintained sibling client · ⏳ unverified on a real Kobra X
(needs hardware + a one-time account login). Default `AUTO_PAUSE_ENABLED=false`.

**Question:** when PrintGuard sees a *sustained* failure, can we actually **pause** the Kobra X — not
just alert?

**Answer:** **Yes, in principle.** The Anycubic cloud exposes a `pause` order that the official app
uses, and the open-source [`hass-anycubic_cloud`](https://github.com/WaresWichall/hass-anycubic_cloud)
already implements the whole thing (auth + signing + `pause_print`) for sibling K4 printers. The only
real blockers are (1) obtaining a user **access token** (one-time login) and (2) confirming the Kobra X
behaves like its sibling the **Kobra S1**. Recommendation: **reuse that client, don't reimplement.**

---

## What I mapped (concrete)

Source: `WaresWichall/hass-anycubic_cloud` `anycubic_cloud_api/` package (and `metheos/anycubic-s1-mqtt-bridge` for S1 confirmation).

### Hosts
| Purpose | Host | Port |
|---|---|---|
| REST API (`BASE_DOMAIN`) | `cloud-universe.anycubic.com` | 443 |
| Web auth (`AUTH_DOMAIN`) | `uc.makeronline.com` | 443 |
| Cloud MQTT | `mqtt-universe.anycubic.com` | 8883 (TLS) |

### The pause path is REST, not MQTT
Pause/resume/cancel go through **`POST /work/operation/sendOrder`** (`API_ENDPOINT.send_order`), not a
raw MQTT publish. Body shape (`AnycubicProjectCtrlOrderRequest.order_request_data`):

```json
{ "order_id": 2, "printer_id": <int>, "project_id": <int> }
```

Order IDs (`const/enums.py::AnycubicOrderID`):

| Action | order_id |
|---|---|
| START_PRINT | 1 |
| **PAUSE_PRINT** | **2** |
| RESUME_PRINT | 3 |
| STOP_PRINT (cancel) | 4 |
| STOP_PRINT_FORCE | 44 |

`printer_id` comes from the device list; `project_id` is the **currently-printing** project — the
library grabs it automatically via `printer.latest_project`, so the high-level call is just
`await client.pause_print(printer)`.

### Auth model (the important nuance)
- Every request carries **app-signed headers**: `Xx-Signature = md5(app_id + ts + app_version +
  app_secret + nonce + app_id)`, plus `Xx-Nonce/Xx-Timestamp/Xx-Version/Xx-Device-Type`.
- **Those app secrets are already embedded in `hass-anycubic_cloud`** — we do **not** need to extract
  them from the app. ✅
- The user supplies a one-time **access token** → the client calls `getoauthToken` +
  `loginWithAccessToken` (`/v3/public/...`) to mint a session user-token, which it caches to a
  `.token` file and auto-refreshes.
- **How to get the access token:** the normal route is the HA integration's config flow (web login at
  `uc.makeronline.com`). For our headless use, run that login once and copy the cached token, or use
  the repo's `scripts/` login helper. This is the one manual step.

### Public API surface we use
```python
ac = AnycubicMQTTAPI(session, cookie_jar, auth_token=<ACCESS_TOKEN>)
await ac.check_api_tokens()                 # logs in / refreshes
printers = await ac.list_my_printers()      # -> [AnycubicPrinter]; .id .name .machine_name .latest_project .printer_online
await ac.pause_print(printer)               # -> msgid (sends order_id=2)
```

---

## Decision: reuse, don't reimplement
Reimplementing the app signing + access-token login + token cache from scratch would be brittle and
would break on every Anycubic change. `anycubic_cloud_api` is maintained and already does it. So:

- `spikes/probe_anycubic.py` and `service/app/pause.py` **import** `anycubic_cloud_api` (path set via
  `ANYCUBIC_CLOUD_API_PATH`).
- **Install:** `git clone https://github.com/WaresWichall/hass-anycubic_cloud` somewhere on the Pi and
  point `ANYCUBIC_CLOUD_API_PATH` at `.../custom_components/anycubic_cloud`. (It is GPL — fine for
  Bro's own use; if Print Genie is ever distributed, keep it a runtime dependency, not a copied-in
  vendor, to respect the licence.)

---

## Run the spike (in order — read-only first)

1. **Get an access token** (one-time login via the HA flow or repo login script). Put it in `.env` as
   `ANYCUBIC_ACCESS_TOKEN`.
2. **Discovery (read-only, zero risk):**
   ```bash
   ANYCUBIC_CLOUD_API_PATH=/path/to/custom_components/anycubic_cloud \
   ANYCUBIC_ACCESS_TOKEN=... \
   python spikes/probe_anycubic.py
   ```
   Confirm the **Kobra X appears**, note its `printer_id`, model string, and that
   `latest_project` is populated while it's printing.
3. **Command test on a throwaway print:** start a small print, then run the probe with `--pause`
   (it calls `pause_print`). Confirm the X pauses on the screen. Then resume from the panel.
4. **Wire it in:** set `ANYCUBIC_PRINTER_ID`, `AUTO_PAUSE_ENABLED=true` in the glue `.env`. Now a
   sustained PrintGuard detection → `service/app/pause.py::try_cloud_pause()` → pause.

## Safety rails baked into the adapter
- **Off by default** (`AUTO_PAUSE_ENABLED=false`).
- **Cooldown** (`PAUSE_COOLDOWN_S`, default 120s) so one noisy frame / repeated webhooks can't spam
  orders.
- **Pause only, never auto-cancel** — cancelling is destructive; a human makes that call.
- **Always alert Discord too** and log a `pause` event — auto-pause never replaces the alert.

## Decision gate
Ship auto-pause **only** if step 3 reproducibly pauses a real Kobra X. If the X differs from the S1
schema, document the delta here and stay alert-only (already a complete product).

## Sources
- https://github.com/WaresWichall/hass-anycubic_cloud  (`anycubic_cloud_api/` — auth, endpoints, orders, mqtt)
- https://github.com/metheos/anycubic-s1-mqtt-bridge  (S1 pause/resume/cancel confirmation)
- https://wiki.anycubic.com/en/fdm-3d-printer/anycubic-kobra-x/lan-connection-guide
- https://github.com/jbatonnet/Rinkhals  (Kobra X unsupported → local-cert route blocked)
