# Bluebox Badge

Bluebox Badge shows your GitHub profile stats over a scrolling blue contribution graph with the Bluebox logo at the top.

It mirrors the stock GitHub profile app: avatar bottom-left, followers, contribs and repos on the right, and tilt parallax on the graph, restyled in Bluebox blues.

## Usage

Open **Bluebox Badge** from the menu. Set your GitHub username (and optionally name and LinkedIn) in Settings. Hold LEFT and RIGHT together to refresh. HOME returns to the menu.

## Requirements

Wi-Fi is needed to fetch your profile, contributions and avatar (cached under `/state`). No credentials are stored in the app. An optional `GITHUB_TOKEN` in `secrets.py` raises API rate limits.
