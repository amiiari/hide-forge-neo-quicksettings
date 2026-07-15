ahaha yes! i dont like how i cant hide those quicksettings (ui, model, text encoder, .etc) stuff in forge neo so this is an extension that does it!

you can even choose which ones to remove!!! wow! in settings yeah

NEW: you can also rename the UI Preset entries (like showing `sd` as `anima` and `xl` as `illustrious`) — set "Preset display labels" in the same settings page, format `value:label, value:label`. it's display-only, so all your per-preset settings keep working.

NEWER:
- **per-preset generation defaults** — switching preset (and every UI start) fills the txt2img prompt + negative prompt, hires-fix upscaler / denoising / upscale-by, AND the ADetailer unit 1+2 models with that preset's defaults. set them on each preset's own settings page (Settings → SD for anima, Settings → XL for illustrious, etc.). empty = that box is left alone.
- **hidden presets** — tick the presets you never use under "Hidden presets" and they vanish from the dropdown. the active one always stays visible.

## Installation

1. Clone or copy this extension into your Forge Neo `extensions/` folder:
   ```
   <Forge-Neo>/extensions/hide-quicksettings/
   ```
2. Restart the WebUI (or reload UI from Settings).
3. Go to **Settings → Hide Quicksettings** and configure what you want hidden.
4. Click **Apply settings**, then click **Reload UI**.
