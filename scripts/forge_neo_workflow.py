import gradio as gr
from modules import script_callbacks, shared
from modules_forge.presets import PresetArch as _PresetArch

# Mapping of setting labels -> elem_id for Forge quicksetting dropdowns
HIDABLE_QUICKSETTINGS = {
    "UI Preset":              "forge_ui_preset",
    "Checkpoint":             "setting_sd_model_checkpoint",
    "VAE / Text Encoder":     "setting_sd_modules",
    "Diffusion in Low Bits":  "forge_ui_dtype",
    "Refresh Button":         "forge_refresh_checkpoint",
}

def _preset_choices(PresetArch):
    """Preset choices with optional display labels ("sd:anima, xl:illustrious").
    Only the shown text changes; the underlying values stay sd/xl/... so all
    per-preset config keys (forge_checkpoint_sd, xl_t2i_cfg, ...) keep working.
    Presets ticked in "Hidden presets" are dropped from the dropdown, except
    the currently active one (so the dropdown never loses its value)."""
    labels = {}
    raw = getattr(shared.opts, "hide_quicksettings_preset_labels", "") or ""
    for part in raw.split(","):
        if ":" in part:
            key, label = part.split(":", 1)
            if key.strip() and label.strip():
                labels[key.strip()] = label.strip()
    hidden = set(getattr(shared.opts, "hide_quicksettings_hidden_presets", None) or [])
    current = getattr(shared.opts, "forge_preset", "sd")
    return [(labels.get(name, name), name) for name in PresetArch.choices()
            if name not in hidden or name == current]


def _patched_make_checkpoint_manager_ui():
    from modules_forge import main_entry
    from modules import ui_common
    from modules_forge.main_entry import (
        sd_models,
        refresh_models,
        PresetArch,
        Context,
        forge_unet_storage_dtype_options,
        checkpoint_change,
        modules_change,
        dtype_change,
    )

    hidden = set(_get_hidden())
    print(f"[hide-quicksettings] _patched_make_checkpoint_manager_ui called. Hidden: {hidden}", flush=True)

    if shared.opts.sd_model_checkpoint in [None, "None", "none", ""]:
        if len(sd_models.checkpoints_list) == 0:
            sd_models.list_models()
        if len(sd_models.checkpoints_list) > 0:
            shared.opts.set("sd_model_checkpoint", next(iter(sd_models.checkpoints_list.values())).name)

    preset_choices = _preset_choices(PresetArch)
    ui_forge_preset = None
    if "UI Preset" not in hidden:
        ui_forge_preset = gr.Dropdown(label="UI Preset", value=lambda: shared.opts.forge_preset, choices=preset_choices, elem_id="forge_ui_preset")
    else:
        # Create invisible component so downstream code doesn't break
        with gr.Group(visible=False):
            ui_forge_preset = gr.Dropdown(label="UI Preset", value=lambda: shared.opts.forge_preset, choices=preset_choices, elem_id="forge_ui_preset")

    ui_checkpoint = None
    if "Checkpoint" not in hidden:
        ui_checkpoint = gr.Dropdown(label="Checkpoint", value=None, choices=None, elem_id="setting_sd_model_checkpoint", elem_classes=["model_selection"])
    else:
        with gr.Group(visible=False):
            ui_checkpoint = gr.Dropdown(label="Checkpoint", value=None, choices=None, elem_id="setting_sd_model_checkpoint", elem_classes=["model_selection"])

    ui_vae = None
    if "VAE / Text Encoder" not in hidden:
        ui_vae = gr.Dropdown(label="VAE / Text Encoder", value=None, choices=None, multiselect=True, elem_id="setting_sd_modules", elem_classes=["model_selection"])
    else:
        with gr.Group(visible=False):
            ui_vae = gr.Dropdown(label="VAE / Text Encoder", value=None, choices=None, multiselect=True, elem_id="setting_sd_modules", elem_classes=["model_selection"])

    def refresh_model_list():
        ckpt_list, vae_list = refresh_models()
        return [gr.update(choices=ckpt_list), gr.update(choices=vae_list)]

    # Refresh button — always create it (it's inside the quicksettings row)
    if "Refresh Button" in hidden:
        with gr.Group(visible=False):
            refresh_button = ui_common.ToolButton(value=ui_common.refresh_symbol, elem_id="forge_refresh_checkpoint", tooltip="Refresh")
    else:
        refresh_button = ui_common.ToolButton(value=ui_common.refresh_symbol, elem_id="forge_refresh_checkpoint", tooltip="Refresh")

    refresh_button.click(fn=refresh_model_list, outputs=[ui_checkpoint, ui_vae], queue=False)
    Context.root_block.load(fn=refresh_model_list, outputs=[ui_checkpoint, ui_vae], queue=False)

    ui_forge_unet_dtype = None
    if "Diffusion in Low Bits" not in hidden:
        ui_forge_unet_dtype = gr.Dropdown(label="Diffusion in Low Bits", value=lambda: shared.opts.forge_unet_storage_dtype, choices=list(forge_unet_storage_dtype_options.keys()), elem_id="forge_ui_dtype")
    else:
        with gr.Group(visible=False):
            ui_forge_unet_dtype = gr.Dropdown(label="Diffusion in Low Bits", value=lambda: shared.opts.forge_unet_storage_dtype, choices=list(forge_unet_storage_dtype_options.keys()), elem_id="forge_ui_dtype")

    ui_checkpoint.input(checkpoint_change, inputs=[ui_checkpoint, ui_forge_preset], queue=False, show_progress=False)
    ui_vae.input(modules_change, inputs=[ui_vae, ui_forge_preset], queue=False, show_progress=False)
    ui_forge_unet_dtype.input(dtype_change, inputs=[ui_forge_unet_dtype, ui_forge_preset], queue=False, show_progress=False)

    # Update globals so other code referencing them still works
    main_entry.ui_forge_preset = ui_forge_preset
    main_entry.ui_checkpoint = ui_checkpoint
    main_entry.ui_vae = ui_vae
    main_entry.ui_forge_unet_dtype = ui_forge_unet_dtype

    # Feature 3+5: preset switch (and UI load) applies per-preset generation defaults
    _wire_preset_swap(ui_forge_preset)

def _get_hidden():
    """Read hidden items, falling back to old key if new one isn't registered yet."""
    return (
        getattr(shared.opts, 'hide_quicksettings_hidden_items', None)
        or getattr(shared.opts, 'forge_neo_workflow_hidden_quicksettings', None)
        or []
    )

def _apply_patch():
    from modules_forge import main_entry
    if not hasattr(main_entry, 'make_checkpoint_manager_ui'):
        print("[hide-quicksettings] make_checkpoint_manager_ui NOT found on main_entry!", flush=True)
        return
    hidden = set(_get_hidden())
    # Also remove Forge quicksettings keys from opts.quicksettings_list
    mapping_to_qs = {
        "Checkpoint":          "sd_model_checkpoint",
        "VAE / Text Encoder":  "sd_vae",
    }
    for label, qs_key in mapping_to_qs.items():
        if label in hidden and qs_key in shared.opts.quicksettings_list:
            shared.opts.quicksettings_list.remove(qs_key)

    main_entry.make_checkpoint_manager_ui = _patched_make_checkpoint_manager_ui
    print(f"[hide-quicksettings] Patch applied. make_checkpoint_manager_ui replaced.", flush=True)

# ---------------------------------------------------------------- Feature 3+5
# Per-preset generation defaults: switching the UI Preset dropdown (and every
# UI (re)load) fills the txt2img prompt / negative prompt, hires-fix upscaler /
# denoising / upscale-by, and the ADetailer unit models with that preset's
# defaults (Settings -> the preset's own page, e.g. SD / XL).
# Empty default = leave that box alone.

# (elem_id to capture, per-preset option key template, value type, auto-snapshot)
# snap=True fields behave like a separate installation: switching away from a
# preset saves your current values into that preset, switching back restores
# them. Prompts (snap=False) stay template-driven from Settings only.
_GEN_TARGETS = [
    ("txt2img_prompt", "{p}_default_prompt", "str", False),
    ("txt2img_neg_prompt", "{p}_default_neg_prompt", "str", False),
    ("img2img_prompt", "{p}_default_prompt", "str", False),
    ("img2img_neg_prompt", "{p}_default_neg_prompt", "str", False),
    ("txt2img_hr_upscaler", "{p}_default_hr_upscaler", "str", True),
    ("txt2img_denoising_strength", "{p}_default_hr_denoise", "float", True),
    ("txt2img_hr_scale", "{p}_default_hr_scale", "float", True),
    ("img2img_denoising_strength", "{p}_default_i2i_denoise", "float", True),
]


def _unit_elem_suffix(n):
    """ADetailer's elem_id suffix for unit n (1-based): '', '_2nd', '_3rd', '_4th', ..."""
    if n == 1:
        return ""
    d = {1: "st", 2: "nd", 3: "rd"}
    return "_" + str(n) + ("th" if 11 <= n % 100 <= 13 else d.get(n % 10, "th"))


# One slot per ADetailer unit (however many ad_max_models says exist), on BOTH
# tabs — txt2img and img2img have separate ADetailer component instances, and
# a preset switch should reconfigure the whole app like a separate install.
_AD_UNITS = int(shared.opts.data.get("ad_max_models", 2) or 2)
for _u in range(1, _AD_UNITS + 1):
    _suf = _unit_elem_suffix(_u)
    for _tab in ("txt2img", "img2img"):
        _GEN_TARGETS += [
            (f"script_{_tab}_adetailer_ad_model{_suf}", f"{{p}}_default_ad_model_{_u}", "str", True),
            (f"script_{_tab}_adetailer_ad_prompt{_suf}", f"{{p}}_default_ad_prompt_{_u}", "str", True),
            (f"script_{_tab}_adetailer_ad_negative_prompt{_suf}", f"{{p}}_default_ad_neg_prompt_{_u}", "str", True),
        ]

_captured = {}


_last_preset = None


def _apply_preset(preset, targets):
    out = []
    for elem, key_tpl, typ, _snap in targets:
        raw = getattr(shared.opts, key_tpl.format(p=preset), "")
        raw = "" if raw is None else str(raw).strip()
        if not raw:
            out.append(gr.skip())
            continue
        if raw == "EMPTY":  # sentinel: actually clear the field
            value = ""
        elif typ == "float":
            try:
                value = float(raw)
            except ValueError:
                out.append(gr.skip())
                continue
        else:
            value = raw
        # Keep the server-side component value in sync too: extensions that
        # read widget .value directly (e.g. Batch ADetailer's unit-defaults
        # snapshot) then see the active preset's values, not stale ones.
        try:
            _captured[elem].value = value
        except Exception:
            pass
        out.append(gr.update(value=value))
    return out[0] if len(out) == 1 else out


def _snapshot_preset(preset, targets, values):
    """Save the current UI values into the given preset's settings (only for
    snap=True fields) — switching away from a preset remembers what you had,
    like closing one installation and opening another."""
    changed = False
    for (_elem, key_tpl, typ, snap), val in zip(targets, values):
        if not snap or val is None:
            continue
        if typ == "float":
            raw = str(val)
        else:
            raw = str(val).strip() or "EMPTY"
        key = key_tpl.format(p=preset)
        if str(getattr(shared.opts, key, "")) != raw:
            shared.opts.set(key, raw)
            changed = True
    if changed:
        shared.opts.save(shared.config_filename)


def _wire_preset_swap(preset_dd):
    """Called from inside the patched checkpoint-manager builder, so we are
    guaranteed to be inside the live gr.Blocks context (the txt2img tab incl.
    the ADetailer accordion is built before the top bar in Forge Neo)."""
    from modules_forge.main_entry import Context

    targets = [t for t in _GEN_TARGETS if t[0] in _captured]
    if not targets:
        print("[hide-quicksettings] no components captured - preset swap not wired", flush=True)
        return
    comps = [_captured[t[0]] for t in targets]

    def _on_change(preset, *values):
        global _last_preset
        if _last_preset and _last_preset != preset:
            _snapshot_preset(_last_preset, targets, values)
        _last_preset = preset
        return _apply_preset(preset, targets)

    def _on_load(preset, *values):
        global _last_preset
        _last_preset = preset
        return _apply_preset(preset, targets)

    preset_dd.change(_on_change, inputs=[preset_dd, *comps], outputs=comps, queue=False, show_progress=False)
    # Also apply on every UI load, so per-preset defaults (ADetailer models,
    # hires settings, ...) come back after a restart regardless of ui-config.
    Context.root_block.load(_on_load, inputs=[preset_dd, *comps], outputs=comps, queue=False, show_progress=False)
    print(f"[hide-quicksettings] Preset swap wired for {len(targets)} fields (auto-remember on switch).", flush=True)


def _on_after_component(component, **kwargs):
    elem_id = kwargs.get("elem_id")
    if elem_id in {t[0] for t in _GEN_TARGETS}:
        _captured[elem_id] = component


script_callbacks.on_after_component(_on_after_component)

# Apply the patch before UI is built (happens at import time via script loading)
print("[hide-quicksettings] Loading extension...", flush=True)
_apply_patch()
print(f"[hide-quicksettings] Patch applied. Hidden: {_get_hidden()}", flush=True)

# Register settings under a new section in Forge Neo Settings
shared.options_templates.update(
    shared.options_section(
        ("hide_quicksettings", "Hide Quicksettings", "ui"),
        {
            "hide_quicksettings": shared.OptionHTML(
                "Hide quicksetting dropdowns from the top bar to simplify your workspace."
            ),
            "hide_quicksettings_hidden_items": shared.OptionInfo(
                [],
                "Hidden Quicksettings",
                gr.CheckboxGroup,
                lambda: {"choices": ["UI Preset", "Checkpoint", "VAE / Text Encoder", "Diffusion in Low Bits", "Refresh Button"]},
            )
            .info("Select which quicksetting elements to hide from the top bar. Requires UI reload.")
            .needs_reload_ui(),
            "hide_quicksettings_preset_labels": shared.OptionInfo(
                "sd:anima, xl:illustrious",
                "Preset display labels",
            )
            .info("Rename entries of the UI Preset dropdown, format: value:label, value:label (e.g. sd:anima, xl:illustrious). Display only — configs still use the real preset names. Requires UI reload.")
            .needs_reload_ui(),
            "hide_quicksettings_hidden_presets": shared.OptionInfo(
                [],
                "Hidden presets",
                gr.CheckboxGroup,
                lambda: {"choices": _PresetArch.choices()},
            )
            .info("Remove presets you never use from the UI Preset dropdown. The currently active preset always stays visible. Requires UI reload.")
            .needs_reload_ui(),
        },
    ),
)

# Per-preset generation defaults, registered on each preset's own settings page.
# ADetailer fields are generated for every unit slot (ad_max_models).
for _name in _PresetArch.choices():
    _fields = {
        f"{_name}_default_prompt": shared.OptionInfo(
            "", "Default prompt", gr.Textbox, {"lines": 6}
        ).info("Filled into txt2img prompt when switching to this preset. Leave empty to keep the current prompt."),
        f"{_name}_default_neg_prompt": shared.OptionInfo(
            "", "Default negative prompt", gr.Textbox, {"lines": 3}
        ).info("Filled into txt2img negative prompt when switching to this preset. Leave empty to keep the current one."),
        f"{_name}_default_hr_upscaler": shared.OptionInfo(
            "", "Default hires upscaler"
        ).info("Hires-fix upscaler name for this preset (e.g. 4xUltrasharp_4xUltrasharpV10). Empty = leave alone."),
        f"{_name}_default_hr_denoise": shared.OptionInfo(
            "", "Default hires denoising strength"
        ).info("e.g. 0.3 — empty = leave alone."),
        f"{_name}_default_hr_scale": shared.OptionInfo(
            "", "Default hires upscale by"
        ).info("e.g. 1.25 — empty = leave alone."),
        f"{_name}_default_i2i_denoise": shared.OptionInfo(
            "", "Default img2img denoising strength"
        ).info("e.g. 0.5 — empty = leave alone."),
    }
    for _u in range(1, _AD_UNITS + 1):
        _fields[f"{_name}_default_ad_model_{_u}"] = shared.OptionInfo(
            "", f"Default ADetailer model (unit {_u})"
        ).info("Exact model filename, e.g. face_yolov9c.pt. Empty = leave alone.")
        _fields[f"{_name}_default_ad_prompt_{_u}"] = shared.OptionInfo(
            "", f"Default ADetailer prompt (unit {_u})", gr.Textbox, {"lines": 2}
        ).info("Empty = leave alone; the word EMPTY = clear the field (ADetailer then uses the main prompt).")
        _fields[f"{_name}_default_ad_neg_prompt_{_u}"] = shared.OptionInfo(
            "", f"Default ADetailer negative prompt (unit {_u})", gr.Textbox, {"lines": 2}
        ).info("Empty = leave alone; EMPTY = clear.")
    shared.options_templates.update(
        shared.options_section((f"ui_{_name}", _name.upper(), "presets"), _fields),
    )
