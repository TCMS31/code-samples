# aviyel - captured analysis run

Real transcript with **no** `GOOGLE_API_KEY` configured. Collection (POST)
reports a clear 503; analysis (GET) of the committed `input_files/travel.csv`
works offline.

```console
$ python manage.py check
System check identified no issues (0 silenced).

$ python manage.py runserver 8612

# Analyse the committed 350-video travel dataset
$ curl -s 'http://localhost:8612/analysis/?keyword=travel'
{"message":"Analysis complete for 'travel'.","videos_analysed":350,"categories":15,"files":["number_of_videos.csv","min_max_tag_videos.csv","average_durations.csv","min_max_tag_durations.csv","classified_tags.csv"]}

# An unknown keyword tells you what IS available
$ curl -s 'http://localhost:8612/analysis/?keyword=nosuchthing'
{"message":"No input file for 'nosuchthing'. POST first to collect it.","available_keywords":["travel"]}

# Collection needs a key, and says so instead of crashing
$ curl -s -X POST http://localhost:8612/analysis/ -H 'Content-Type: application/json' -d '{"keyword":"travel"}'
{"message":"GOOGLE_API_KEY is not set. Add it to .env to collect new data; existing input files under input_files/ can still be analysed."}

# Path traversal in the keyword is rejected
$ curl -s 'http://localhost:8612/analysis/?keyword=../../etc/passwd'
{"message":"Please provide a 'keyword' query parameter."}
```


## Generated output files

```console
$ ls -1 aviyel_api/output_files/
average_durations.csv
classified_tags.csv
min_max_tag_durations.csv
min_max_tag_videos.csv
number_of_videos.csv

$ cat aviyel_api/output_files/number_of_videos.csv
Category,# of Videos
Entertainment,65
Gaming,59
Education,52
People & Blogs,48
Film & Animation,34
Travel & Events,29
News & Politics,16
Music,10
Howto & Style,9
Science & Technology,9
Sports,8
Nonprofits & Activism,7
Autos & Vehicles,2
Pets & Animals,1
Comedy,1

$ cat aviyel_api/output_files/average_durations.csv
Category,Time(Seconds)
Autos & Vehicles,46.5
Comedy,617.0
Education,2357.96
Entertainment,1749.98
Film & Animation,2863.85
Gaming,1436.51
Howto & Style,521.33
Music,487.3
News & Politics,691.5
Nonprofits & Activism,2280.14
People & Blogs,815.02
Pets & Animals,1718.0
Science & Technology,902.11
Sports,1122.88
Travel & Events,1324.17

$ cat aviyel_api/output_files/min_max_tag_durations.csv
Category with Max Duration,Education
Category with Min Duration,Music
```
