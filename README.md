# Hide Quicksettings

A lightweight extension for Stable Diffusion WebUI Forge - Neo that lets you hide quicksetting dropdowns from the top bar.

## Features

- **Hide Quicksettings** — Remove unused quicksetting dropdowns (Checkpoint, VAE / Text Encoder, UI Preset, etc.) from the top bar so your interface stays clean.
- **Preset display labels** — Rename entries of the UI Preset dropdown (e.g. show `sd` as `anima` and `xl` as `illustrious`). Display only: the underlying preset values are unchanged, so all per-preset settings keep working. Configure in **Settings → Hide Quicksettings**, format `value:label, value:label`.

## Installation

1. Clone or copy this extension into your Forge Neo `extensions/` folder:
   ```
   <Forge-Neo>/extensions/hide-quicksettings/
   ```
2. Restart the WebUI (or reload UI from Settings).
3. Go to **Settings → Hide Quicksettings** and configure what you want hidden.
4. Click **Apply settings**, then click **Reload UI**.
