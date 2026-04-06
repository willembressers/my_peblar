import pandas as pd


def charger(data):
    states = []

    for state in data[0]:
        # skip unavailable values
        if state["state"] == "unavailable":
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

        for forcast in state["attributes"]["forecast"]:
            tariffs.append(forcast)

    return pd.DataFrame(tariffs)
