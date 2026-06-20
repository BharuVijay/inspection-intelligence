def risk_score(defects):
    weights = {"low": 1, "medium": 3, "high": 5}

    score = sum(weights.get(d["severity"], 0) for d in defects)

    if score > 8:
        return "High Risk"
    elif score > 4:
        return "Medium Risk"
    return "Low Risk"
