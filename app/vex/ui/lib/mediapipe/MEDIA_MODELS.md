# MediaPipe hand-control models (not in this source tree)

These binary assets are larger than 5 MB, so they are omitted from the GitHub
source checkout. They ship inside the Windows installer / zip release:

- `hand_landmarker.task` (~7.5 MB)
- `wasm/vision_wasm_internal.wasm` (~12 MB)
- `wasm/vision_wasm_nosimd_internal.wasm` (~12 MB)

Download the latest release and copy them from
`app/vex/ui/lib/mediapipe/` into this tree if you are running from source and
want hand control. The JS wrappers (`vision_bundle.mjs`, `vision_wasm_*.js`)
remain here. Official upstream:
https://developers.google.com/mediapipe/solutions/vision/hand_landmarker
