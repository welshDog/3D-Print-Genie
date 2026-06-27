# 🍓 Print Genie — Raspberry Pi Runbook (Phase 0 → 1)

Copy-paste your way from a blank SD card to **spaghetti alerts on your phone**. Every block is meant
to be pasted straight into a terminal. Replace anything in `<angle brackets>`.

> Target host: **Raspberry Pi 4 or 5**, **Raspberry Pi OS Lite 64-bit**.
> Outcome of this runbook: PrintGuard running in Docker, watching the Kobra X via a USB webcam,
> firing a Discord alert + snapshot the second it sees a failure.

---

## ✅ Before you start (shopping + physical)

- Raspberry Pi 4 (2GB+) or Pi 5, USB-C power, microSD 16GB+
- USB webcam (Logitech C270-class is perfect, ~£20)
- Pi sits on the same network as the Kobra X

**Physical (do this first, no software):**
1. Kobra X tune-up: wash the build plate, check belt tension (guitar-string, not floppy), snug the
   eccentric nuts, lube the rails, run a first-layer calibration.
2. Zip-tie the webcam to the top frame bar **pointing straight down** — aim for the **whole bed** in
   frame.
3. On the printer: **Settings → Network → LAN Mode = ON** (needed later for the Phase-4 pause spike).
4. Optional sanity check before any Pi work — open
   [oliverbravery.github.io/PrintGuard](https://oliverbravery.github.io/PrintGuard) on a laptop,
   point its webcam at the bed, confirm the AI reacts to a deliberate tangle. If it works in the
   browser, it'll work on the Pi.

---

## 1️⃣ Flash the SD card

Use **Raspberry Pi Imager** on your PC:
1. Choose **Raspberry Pi OS Lite (64-bit)**.
2. Click the ⚙️ (or "Edit Settings") **before** writing:
   - Set hostname: `printgenie`
   - Enable **SSH** (password or your public key)
   - Set username `pi` + a password
   - Enter your **WiFi SSID + password** (or plan to use ethernet)
3. Write the card, pop it in the Pi, power on. Give it ~60 seconds to boot.

---

## 2️⃣ SSH in + update

```bash
ssh pi@printgenie.local        # or ssh pi@<pi-ip>
sudo apt update && sudo apt full-upgrade -y
sudo reboot                    # reconnect after it comes back up
```

---

## 3️⃣ Install Docker

```bash
ssh pi@printgenie.local
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker                  # apply the group without logging out
docker run --rm hello-world    # should print "Hello from Docker!"
```

---

## 4️⃣ Plug in + verify the webcam

```bash
ls /dev/video*                 # expect /dev/video0 (maybe video1 etc.)

# Grab a test snapshot to confirm the angle/framing:
sudo apt install -y fswebcam
fswebcam -r 1280x720 ~/test.jpg
# Copy it to your PC to eyeball it:  scp pi@printgenie.local:~/test.jpg .
```

If `/dev/video0` isn't the right device, note the correct one — you'll set it in the compose file.

---

## 5️⃣ Get Print Genie + configure

```bash
cd ~
git clone https://github.com/welshDog/3D-Print-Genie.git printgenie
cd printgenie/docker
cp .env.example .env
nano .env
```

For the **Phase 1** alert win you only need **one** value — your Discord webhook:

```ini
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxxx/yyyy
```

> **Get the webhook:** in Discord → your server → **Server Settings → Integrations → Webhooks →
> New Webhook** → pick the channel → **Copy Webhook URL**. Leave the Supabase/Meshy/economy values
> blank for now (those are Phase 2/3).

Save: `Ctrl+X` → `Y` → `Enter`.

**If your camera isn't `/dev/video0`,** edit the compose mapping:

```bash
nano docker-compose.yml
# under printguard: → devices: change "/dev/video0:/dev/video0" to your device
```

---

## 6️⃣ Launch PrintGuard

```bash
docker compose up -d
docker compose logs -f printguard      # watch it boot; Ctrl+C to stop tailing
hostname -I                            # note your Pi's IP for the next step
```

> Note: the `printgenie` glue service in the compose file is behind the `glue` profile and **stays
> off** in Phase 1 — `docker compose up -d` only starts PrintGuard. You bring the glue service up in
> Phase 2 with `docker compose --profile glue up -d`.

Open **`http://<pi-ip>:8000`** in a browser. The PrintGuard dashboard should load.

---

## 7️⃣ Configure PrintGuard (in the dashboard)

1. **Cameras → Add Camera →** choose **"This device"** (uses the Pi's USB webcam). Confirm the live
   feed; nudge the physical angle until the whole bed is visible.
2. **Printers → Add Printer →** choose **"Camera Only"** mode (no serial/API — the Kobra X can't be
   driven). Name it `Kobra X`. Bind it to the camera.
3. **Monitors → Add Monitor →** link the camera + printer.
4. **Thresholds** (start conservative to avoid false alarms):
   - Sensitivity: **0.7**
   - Sustained frames before action: **10–15** (stops shadows/hands triggering it)
   - Action on failure: **Notify only** ← keep it here until you trust it. *(Auto-pause does nothing
     on a camera-only Kobra X — that's the Phase-4 cloud spike.)*

---

## 8️⃣ Wire the Discord alert

In **PrintGuard → Settings → Notifications → Discord**, paste the same webhook URL from your `.env`,
then hit **Test**. You should get a message in your channel within seconds.

*(Telegram works too if you ever want it — `@BotFather` → `/newbot` → paste token + your chat ID from
`@userinfobot`. But Discord keeps everything in one place with the rest of your stack.)*

---

## 9️⃣ Acceptance test 🧪

1. Start any small print on the Kobra X (a Benchy or calibration cube).
2. While it prints, dangle a **tangle of filament** in front of the nozzle/bed for ~15 seconds to
   simulate spaghetti.
3. ✅ **Pass =** a Discord alert **with a snapshot** lands on your phone within seconds, and the
   PrintGuard dashboard logs the detection.

If it fires on shadows or your hand, bump **sustained frames** to 20 and/or sensitivity to 0.6.

---

## 🔭 What's next

- **Phase 2** — turn on the glue service for the **Supabase job log** + **Meshy STL preflight**:
  fill the Supabase/Meshy values in `.env`, apply `db/migrations/0001_print_genie.sql` via the
  Supabase MCP, then `docker compose --profile glue up -d`.
- **Phase 3** — point the **MCP server** (`mcp/server.py`) at the glue service so you can ask Claude
  *"how's my print going?"*, and start banking **BROski XP** per finished print.
- **Phase 4** — the **closed-loop auto-pause** spike via Anycubic cloud — see
  [`spikes/anycubic_cloud_pause.md`](../spikes/anycubic_cloud_pause.md).

---

## 🆘 Quick troubleshooting

| Symptom | Fix |
|---|---|
| `ls /dev/video*` shows nothing | Re-seat the USB cable; try a different port; `dmesg \| tail` to see if the cam enumerated. |
| Dashboard won't load at `:8000` | `docker compose ps` (is it Up?), `docker compose logs printguard`, check the Pi IP with `hostname -I`. |
| Camera black/garbled in dashboard | Wrong `/dev/videoN` in compose, or another app is holding the camera. Stop `fswebcam`/anything using it. |
| Discord test does nothing | Webhook URL typo, or the channel/webhook was deleted. Recreate the webhook and re-paste. |
| Too many false alerts | Raise sustained frames to 20, lower sensitivity to 0.6, improve lighting (even, no harsh shadows). |
| `docker: permission denied` | You skipped `newgrp docker` — run it, or log out/in. |
