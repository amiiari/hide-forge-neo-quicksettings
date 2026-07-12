import gradio as gr
from modules import shared

# Mapping of setting labels -> elem_id for Forge quicksetting dropdowns
HIDABLE_QUICKSETTINGS = {
    "UI Preset":              "forge_ui_preset",
    "Checkpoint":             "setting_sd_model_checkpoint",
    "VAE / Text Encoder":     "setting_sd_modules",
    "Diffusion in Low Bits":  "forge_ui_dtype",
    "Refresh Button":         "forge_refresh_checkpoint",
}

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

    hidden = set(shared.opts.forge_neo_workflow_hidden_quicksettings or [])
    print(f"[forge-neo-workflow] _patched_make_checkpoint_manager_ui called. Hidden: {hidden}", flush=True)

    if shared.opts.sd_model_checkpoint in [None, "None", "none", ""]:
        if len(sd_models.checkpoints_list) == 0:
            sd_models.list_models()
        if len(sd_models.checkpoints_list) > 0:
            shared.opts.set("sd_model_checkpoint", next(iter(sd_models.checkpoints_list.values())).name)

    ui_forge_preset = None
    if "UI Preset" not in hidden:
        ui_forge_preset = gr.Dropdown(label="UI Preset", value=lambda: shared.opts.forge_preset, choices=PresetArch.choices(), elem_id="forge_ui_preset")
    else:
        # Create invisible component so downstream code doesn't break
        with gr.Group(visible=False):
            ui_forge_preset = gr.Dropdown(label="UI Preset", value=lambda: shared.opts.forge_preset, choices=PresetArch.choices(), elem_id="forge_ui_preset")

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

def _apply_patch():
    from modules_forge import main_entry
    if not hasattr(main_entry, 'make_checkpoint_manager_ui'):
        print("[forge-neo-workflow] make_checkpoint_manager_ui NOT found on main_entry!", flush=True)
        return
    hidden = set(shared.opts.forge_neo_workflow_hidden_quicksettings or [])
    # Also remove Forge quicksettings keys from opts.quicksettings_list
    mapping_to_qs = {
        "Checkpoint":          "sd_model_checkpoint",
        "VAE / Text Encoder":  "sd_vae",
    }
    for label, qs_key in mapping_to_qs.items():
        if label in hidden and qs_key in shared.opts.quicksettings_list:
            shared.opts.quicksettings_list.remove(qs_key)

    main_entry.make_checkpoint_manager_ui = _patched_make_checkpoint_manager_ui
    print(f"[forge-neo-workflow] Patch applied. make_checkpoint_manager_ui replaced.", flush=True)

# Apply the patch before UI is built (happens at import time via script loading)
print("[forge-neo-workflow] Loading extension...", flush=True)
_apply_patch()
print(f"[forge-neo-workflow] Patch applied. Hidden: {shared.opts.forge_neo_workflow_hidden_quicksettings}", flush=True)

# Register settings under a new section in Forge Neo Settings
shared.options_templates.update(
    shared.options_section(
        ("forge_neo_workflow", "Forge Neo Workflow", "ui"),
        {
            "forge_neo_workflow": shared.OptionHTML(
                "Customize your Forge Neo workspace — hide quicksettings you don't use."
            ),
            "forge_neo_workflow_hidden_quicksettings": shared.OptionInfo(
                [],
                "Hidden Quicksettings",
                gr.CheckboxGroup,
                lambda: {"choices": ["UI Preset", "Checkpoint", "VAE / Text Encoder", "Diffusion in Low Bits", "Refresh Button"]},
            )
            .info("Select which quicksetting elements to hide from the top bar. Requires UI reload.")
            .needs_reload_ui(),
        },
    ),
)
