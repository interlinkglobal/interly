from PyInstaller.utils.hooks import collect_all, copy_metadata


playwright_data, playwright_binaries, playwright_hidden = collect_all("playwright")
pynput_data, pynput_binaries, pynput_hidden = collect_all("pynput")

a = Analysis(
    ["entrypoint.py"],
    pathex=["../src"],
    binaries=playwright_binaries + pynput_binaries,
    datas=playwright_data + pynput_data + copy_metadata("interly"),
    hiddenimports=playwright_hidden + pynput_hidden,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="interlink",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
