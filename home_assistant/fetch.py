import requests
from dotenv import dotenv_values

config = dotenv_values(".env")


def history(start: str, end: str, entity_id: str):
    # get the history data from the API
    url = f"{config.get('BASE_URL')}/api/history/period/{start}"
    headers = {
        "Authorization": f"Bearer {config.get('TOKEN')}",
        "Content-Type": "application/json",
    }
    params = {"filter_entity_id": entity_id, "end_time": end}
    response = requests.get(url, headers=headers, params=params)

    # check for errors
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None
    return response.json()
