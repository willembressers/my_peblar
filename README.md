# my_peblar

My personal script that reads data from Home Assistant, and generates an invoice from it.

Add an `.env` file with the following.
```bash
BASE_URL = "<url-to-HA>"
TOKEN = "<HA-TOKEN>"
ENTITY_ID = "<HA-SENSOR>"
OUTPUT_DIR = "Path/to/save/invoices"
TARIFF = 0.42

NAME = "<name>"
ADDRESS = "<addres>"
POSTAL_CODE = "<POSTAL>"
CITY = "<CITY>"
```
