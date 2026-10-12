"""Preserve the caller's exact model alias in the pinned Claude ACP wrapper."""

import argparse
import hashlib
from pathlib import Path


UPSTREAM_SHA256 = "f086c2951a2fb1fb0d20b950f37f2e424b192ae46ecef5fdd3e31e456a211600"
ANCHOR = (
    "        const { modelState: models, resumedContextWindow } = await "
    "getAvailableModels(q, allowedModels, initializationResult.models, "
    "settingsManager, this.logger, creationOpts.resume !== undefined);\n"
)
PATCH = """        // Preserve the literal gateway model on provider-session resume.
        if (creationOpts.resume !== undefined && typeof options.model === "string") {
            await q.setModel(options.model);
            models.currentModelId = options.model;
            if (!models.availableModels.some(
                (model) => model.modelId === options.model
            )) {
                models.availableModels.push({
                    modelId: options.model,
                    name: options.model,
                    description: "Custom model",
                });
            }
        }
"""


def patch_module(module: Path) -> None:
    text = module.read_text()
    original = text.replace(PATCH, "", 1)
    if hashlib.sha256(original.encode()).hexdigest() != UPSTREAM_SHA256:
        raise ValueError("Claude ACP 0.63.0 module differs from the verified source")
    if text == original:
        if original.count(ANCHOR) != 1:
            raise ValueError("Claude resume insertion point is not unique")
        module.write_text(original.replace(ANCHOR, ANCHOR + PATCH, 1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("module", type=Path)
    patch_module(parser.parse_args().module)
