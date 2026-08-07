import json
import os

import pytest
from PIL import Image, ImageDraw

from computer_agent.desktop import _uia_rect, list_windows, ocr_image


class Rect:
    left = 10
    top = 20
    right = 110
    bottom = 70


def test_uia_rect_normalizes_bounds():
    assert _uia_rect(Rect()) == {"left": 10, "top": 20, "width": 100, "height": 50}


@pytest.mark.skipif(os.name != "nt", reason="Windows desktop API")
def test_list_windows_returns_json_array():
    payload = json.loads(list_windows())
    assert isinstance(payload, list)


@pytest.mark.skipif(os.name != "nt", reason="Windows OCR runtime")
def test_ocr_returns_structured_payload(tmp_path):
    source = tmp_path / "ocr.png"
    image = Image.new("RGB", (600, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 35), "INTERLY 123", fill="black")
    image.save(source)

    payload = json.loads(ocr_image(str(source)))

    assert payload["path"] == str(source.resolve())
    assert isinstance(payload["text"], str)
    assert isinstance(payload["lines"], list)
