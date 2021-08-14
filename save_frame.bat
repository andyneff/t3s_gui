@echo on
ffmpeg -f dshow -ss 0  -i video="OBS Virtual Camera" -vframes 1 -f image2 test.png