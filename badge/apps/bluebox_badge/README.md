# Bluebox Badge

Bluebox Badge shows your GitHub profile stats over a scrolling blue contribution graph with the Bluebox logo at the top.

It mirrors the stock GitHub profile app: avatar bottom-left, followers, contribs and repos on the right, and tilt parallax on the graph, restyled in Bluebox blues.

## Usage

Open **Bluebox Badge** from the menu. Set your GitHub username (and optionally name and LinkedIn) in Settings. Hold LEFT and RIGHT together to refresh. Press LEFT or RIGHT to swap between the profile stats (default) and a second page showing the time (HH:MM from the badge clock, `--:--` if unset), temperature (in °F) and humidity from an optional SHT45 sensor (`--` if none). If the badge clock is unset, the app syncs it once over your Wi-Fi via NTP and shows US Pacific time (PST/PDT, DST handled automatically), retrying every 30 s on failure. Lay the badge flat (screen facing up) to show a QR code linking to https://bluebox.ai; hold it upright again to return to the profile. BACK (or the SELECT button) or HOME returns to the menu.

## Requirements

Wi-Fi is needed to fetch your profile, contributions and avatar (cached under `/state`). The temperature and humidity page needs an Adafruit SHT45 on the Qw/ST connector (I2C address 0x44). No credentials are stored in the app. An optional `GITHUB_TOKEN` in `secrets.py` raises API rate limits.
