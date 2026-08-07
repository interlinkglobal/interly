from PyInstaller.utils.hooks import collect_all, copy_metadata


playwright_data, playwright_binaries, playwright_hidden = collect_all("playwright")
pynput_data, pynput_binaries, pynput_hidden = collect_all("pynput")
rapidocr_data, rapidocr_binaries, rapidocr_hidden = collect_all("rapidocr")
onnx_data, onnx_binaries, onnx_hidden = collect_all("onnxruntime")
pillow_data, pillow_binaries, pillow_hidden = collect_all("PIL")
uia_data, uia_binaries, uia_hidden = collect_all("uiautomation")

a = Analysis(
    ["entrypoint.py"],
    pathex=["../src"],
    binaries=(
        playwright_binaries
        + pynput_binaries
        + rapidocr_binaries
        + onnx_binaries
        + pillow_binaries
        + uia_binaries
    ),
    datas=(
        playwright_data
        + pynput_data
        + rapidocr_data
        + onnx_data
        + pillow_data
        + uia_data
        + copy_metadata("interly")
    ),
    hiddenimports=(
        playwright_hidden
        + pynput_hidden
        + rapidocr_hidden
        + onnx_hidden
        + pillow_hidden
        + uia_hidden
    ),
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="interly",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
