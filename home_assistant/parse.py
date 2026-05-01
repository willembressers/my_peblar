import pandas as pd


def charger(data):
    states = []

    for state in data[0]:
        # skip unavailable values
        if state.get("state", "") == "unavailable":
            continue

        # unwrap the attributes into the main dict
        state.update(state.pop("attributes"))

        # collect the state
        states.append(state)

    return pd.DataFrame(states)


def tariff(data):
    tariffs = []

    for state in data[0]:
        # skip unavailable values
        if state["state"] == "unavailable":
            continue

        attributes = state.get("attributes")
        if attributes:
            forecasts = attributes.get("forecast")
            if forecasts:
                for forecast in forecasts:
                    tariffs.append(forecast)

    return pd.DataFrame(tariffs)


def statistics(data, entity_id):
    return pd.DataFrame(data.get(entity_id, []))
