from PyInstaller.utils.hooks import collect_all, copy_metadata


playwright_data, playwright_binaries, playwright_hidden = collect_all("playwright")
pynput_data, pynput_binaries, pynput_hidden = collect_all("pynput")
rapidocr_data, rapidocr_binaries, rapidocr_hidden = collect_all("rapidocr")
onnx_data, onnx_binaries, onnx_hidden = collect_all("onnxruntime")
pillow_data, pillow_binaries, pillow_hidden = collect_all("PIL")
uia_data, uia_binaries, uia_hidden = collect_all("uiautomation")
pdf_data, pdf_binaries, pdf_hidden = collect_all("pdfplumber")
docx_data, docx_binaries, docx_hidden = collect_all("docx")
excel_data, excel_binaries, excel_hidden = collect_all("openpyxl")
pptx_data, pptx_binaries, pptx_hidden = collect_all("pptx")

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
        + pdf_binaries
        + docx_binaries
        + excel_binaries
        + pptx_binaries
    ),
    datas=(
        playwright_data
        + pynput_data
        + rapidocr_data
        + onnx_data
        + pillow_data
        + uia_data
        + pdf_data
        + docx_data
        + excel_data
        + pptx_data
        + copy_metadata("interly")
        + copy_metadata("pdfplumber")
        + copy_metadata("python-docx")
        + copy_metadata("openpyxl")
        + copy_metadata("python-pptx")
    ),
    hiddenimports=(
        playwright_hidden
        + pynput_hidden
        + rapidocr_hidden
        + onnx_hidden
        + pillow_hidden
        + uia_hidden
        + pdf_hidden
        + docx_hidden
        + excel_hidden
        + pptx_hidden
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
