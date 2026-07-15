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

    # Feature 3: preset switch also swaps the txt2img prompts
    _wire_prompt_swap(ui_forge_preset)

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

# ---------------------------------------------------------------- Feature 3
# Per-preset default prompts: switching the UI Preset dropdown also fills the
# txt2img prompt / negative prompt with that preset's defaults (Settings ->
# the preset's own page, e.g. SD / XL). Empty default = leave the box alone.

_prompt_components = {}


def _swap_prompts(preset):
    p = getattr(shared.opts, f"{preset}_default_prompt", "") or ""
    n = getattr(shared.opts, f"{preset}_default_neg_prompt", "") or ""
    return (
        gr.update(value=p) if p.strip() else gr.skip(),
        gr.update(value=n) if n.strip() else gr.skip(),
    )


def _wire_prompt_swap(preset_dd):
    """Called from inside the patched checkpoint-manager builder, so we are
    guaranteed to be inside the live gr.Blocks context (the prompt boxes are
    built before the top bar in Forge Neo)."""
    if len(_prompt_components) != 2:
        print("[hide-quicksettings] prompt boxes not captured - prompt swap not wired", flush=True)
        return
    preset_dd.change(
        _swap_prompts,
        inputs=[preset_dd],
        outputs=[_prompt_components["txt2img_prompt"], _prompt_components["txt2img_neg_prompt"]],
        queue=False,
        show_progress=False,
    )
    print("[hide-quicksettings] Prompt swap wired.", flush=True)


def _on_after_component(component, **kwargs):
    elem_id = kwargs.get("elem_id")
    if elem_id in ("txt2img_prompt", "txt2img_neg_prompt"):
        _prompt_components[elem_id] = component


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

# Per-preset default prompts, registered on each preset's own settings page
for _name in _PresetArch.choices():
    shared.options_templates.update(
        shared.options_section(
            (f"ui_{_name}", _name.upper(), "presets"),
            {
                f"{_name}_default_prompt": shared.OptionInfo(
                    "", "Default prompt", gr.Textbox, {"lines": 6}
                ).info("Filled into txt2img prompt when switching to this preset. Leave empty to keep the current prompt."),
                f"{_name}_default_neg_prompt": shared.OptionInfo(
                    "", "Default negative prompt", gr.Textbox, {"lines": 3}
                ).info("Filled into txt2img negative prompt when switching to this preset. Leave empty to keep the current one."),
            },
        ),
    )
