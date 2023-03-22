# AVIYEL

Part of [`code-samples`](../../README.md). A captured run with real output is in
[`docs/analysis-run.md`](../docs/analysis-run.md).

# Requirements

Python 3.8-3.10 (Django 4.0 does not support 3.11+).

# Setup

```bash
cd aviyel/aviyel_api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional
python manage.py migrate
python manage.py runserver
```

**`GOOGLE_API_KEY` is only needed to collect new data (POST).** Without it the
project starts normally and the committed dataset can still be analysed:

```bash
curl 'http://localhost:8000/analysis/?keyword=travel'
```

POST without a key returns a 503 naming the missing variable rather than
crashing.

### API_ENDPOINTS

1. The task is implemented as a simple Django Rest Framework API.
2. The base url is ```http://127.0.0.1:8000/analysis/```
3. The endpoint has two methods that is ```GET``` and ```POST```


### POST
The post method is used to generate the input file for the given keyword. It utilizes the YOUTUBE data API to get list as well as details of each video. To run, use POSTMAN or some other API testing tool and hit ```http://127.0.0.1:8000/analysis/``` with the following body with content-type ```application/json```
```
{"keyword": "travel"}
```
Hitting the endpoint will search, clean and then generate a file in the ```input_files``` folder which can then be used for running the analysis.

### GET
The get method is used to run the analysis on the generated input file. To run the analysis, hit the following endpoint with keyword as the query param ```http://127.0.0.1:8000/analysis/?keyword=travel```
Hitting the endpoint will generate csv files in the ```ouput_files``` folder with the required analysis written into each file.

### OVERVIEW

1. Collected data is kept in CSV files rather than a database: the analysis is a
   whole-dataset scan, so a table would add query cost without adding value.
2. It is an API rather than a script so collection and analysis can be triggered
   independently - collect once, analyse repeatedly.
3. pandas does the analysis; Django REST Framework is only the HTTP layer.
4. `input_files/travel.csv` (350 rows) is committed so the GET endpoint works
   immediately. `output_files/` is generated at runtime and git-ignored.

### Layering

- `analysis/views.py` - HTTP only: validates the keyword, picks a path, formats
  the response.
- `analysis/services/youtube.py` - every call to Google. Video details and
  category names are batched 50 ids per request.
- `analysis/services/statistics.py` - pure pandas. Imports neither Django nor
  the network, so it is unit-tested directly against `travel.csv`.

### A note on the committed dataset

`travel.csv` was collected by the original implementation, which searched the
requested keyword on the first page only and a hardcoded unrelated string on
each of the following six pages. As a result just 29 of its 350 rows are
actually `Travel & Events`. The bug is fixed, but regenerating the file needs a
YouTube API key, so the original data is kept as-is and labelled here.

### Testing

```bash
python manage.py test        # 27 tests
```

The YouTube client is stubbed throughout - no test needs a key or a network.

### Formatting

```bash
black .                      # configured in ../../pyproject.toml
```
