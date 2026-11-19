import json
from pathlib import Path
import pytest
from src.extract import extract_from_any_file


def test_extract_from_txt_file():
    txt_content = b"""
    MILITARY SPECIFICATION HSLA-100
    Chemical Composition:
    Carbon (C): 0.04 wt%
    Nickel (Ni): 3.50 wt%
    Copper (Cu): 1.60 wt%
    Chromium (Cr): 0.60 wt%
    Molybdenum (Mo): 0.55 wt%
    Manganese (Mn): 0.85 wt%
    Silicon (Si): 0.25 wt%
    Niobium (Nb): 0.03 wt%
    
    Processing:
    Austenitized at 900 C for 1.5 h, followed by water quench.
    Tempered at 650 C for 2.0 h.
    
    Mechanical Properties:
    Yield Strength: 690 MPa
    Tensile Strength: 795 MPa
    Charpy Impact Energy: 80 J
    Elongation: 18 %
    """
    res = extract_from_any_file(txt_content, "hsla100.txt")
    assert res["file_type"] == "TXT"
    assert res["composition"]["C"] == 0.04
    assert res["composition"]["Ni"] == 3.50
    assert res["composition"]["Cu"] == 1.60
    assert res["composition"]["Fe"] > 90.0
    assert res["properties"]["yield_strength_mpa"] == 690.0
    assert res["properties"]["charpy_toughness_j"] == 80.0
    assert res["processing"]["austenitizing_temp_c"] == 900.0
    assert res["processing"]["tempering_temp_c"] == 650.0
    assert res["physics"]["pcm"] > 0.0
    assert "session_payload" in res
    assert res["session_payload"]["st_c"] == 0.04


def test_extract_from_csv_file():
    csv_content = b"""Alloy_ID,Name,C,Mn,Si,Ni,Cr,Mo,Cu,V,Austenitizing_Temp_C,Tempering_Temp_C,Tempering_Time_h,YS_MPa,UTS_MPa,CVN_Minus40C_J,Elongation_pct
NS-01,TestNavalAlloy,0.05,0.40,0.15,6.50,1.84,0.60,3.65,0.10,900,480,4.0,1100,1260,122,16.5
"""
    res = extract_from_any_file(csv_content, "heats.csv")
    assert res["file_type"] == "CSV"
    assert res["composition"]["C"] == 0.05
    assert res["composition"]["Ni"] == 6.50
    assert res["composition"]["Cu"] == 3.65
    assert res["properties"]["yield_strength_mpa"] == 1100.0
    assert res["properties"]["charpy_toughness_j"] == 122.0
    assert res["session_payload"]["st_ni"] == 6.50


def test_extract_from_json_file():
    json_obj = {
        "steel": {
            "name": "Custom Submarine Steel",
            "composition": [
                {"element": "C", "value": 0.06},
                {"element": "Ni", "value": 5.0},
                {"element": "Cu", "value": 1.5},
            ]
        },
        "mechanical_properties": {
            "yield_strength_mpa": 850,
            "charpy_toughness_j": 105
        }
    }
    json_bytes = json.dumps(json_obj).encode("utf-8")
    res = extract_from_any_file(json_bytes, "alloy.json")
    assert res["file_type"] == "JSON"
    assert res["composition"]["C"] == 0.06
    assert res["composition"]["Ni"] == 5.0
    assert res["properties"]["yield_strength_mpa"] == 850.0
    assert res["physics"]["martensite_start_c"] > 0.0
