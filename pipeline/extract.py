def simple_extract(text):
    defects = []

    if "crack" in text:
        defects.append({
            "type": "crack",
            "severity": "high",
            "location": "wall"
        })

    if "corrosion" in text:
        defects.append({
            "type": "corrosion",
            "severity": "medium",
            "location": "beam"
        })

    return defects
