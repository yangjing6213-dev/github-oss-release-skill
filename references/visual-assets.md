# Visual asset policy (compatibility reference)

For the v2 workflow, use [visual-assets-publication.md](visual-assets-publication.md).
This file remains as a compatibility entry point for projects that already
reference the older filename.

Use this policy for Logo, Cover, Screenshot and Demo decisions.

```text
VISUAL_ASSET_POLICY = OPTIONAL_BY_PROJECT
```

## Decide whether assets are required

Usually recommend visual assets for GUI desktop software, web/mobile applications, consumer-facing tools, productized projects, interface-driven workflows and projects where brand recognition materially improves understanding.

Usually allow no visual assets for CLI tools, libraries, APIs, SDKs, data-processing scripts, backend or infrastructure services, developer components, internal engines and small modules without a GUI.

Missing assets do not block release when all conditions hold:

1. README files contain no broken image references.
2. No unverified, unlicensed or misleading visual asset is included.
3. No false screenshot, interface, user data, Star count, download count or benchmark is shown.
4. No unauthorized third-party brand, copyrighted composition or private data is used.
5. Images are not necessary to explain the project's core function.
6. All other security, license, quality, documentation and platform gates pass.

Record:

```text
VISUAL_ASSETS_REQUIRED = NO
VISUAL_ASSETS_STATUS = NOT_REQUIRED_FOR_CURRENT_RELEASE
VISUAL_ASSETS_READY = NOT_APPLICABLE
```

## Included asset gate

For every included asset, verify source, creator/owner, license or permission, redistribution scope, modification rights, attribution, privacy, truthful content, decoding, dimensions, light/dark readability, and absence of watermarks or unauthorized brands. Reject placeholders, blank or solid-color stand-ins, broken images, unknown network images, fabricated dashboards or metrics, garbled text and unreviewed legacy files.

If assets may add value later, create a separate `OPTIONAL VISUAL ASSET WORKFLOW`; do not block code, documentation, safety or release preparation meanwhile.
