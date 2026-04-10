from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--window-size=1400,900",
            "--window-position=0,0",
        ],
    )

    context = browser.new_context(no_viewport=True)
    page = context.new_page()
    page.goto("https://example.com")
    print("Pagina aperta")
    time.sleep(300)
    browser.close()


    '''
rwxrwx 1 root root     8 Aug 17  2023 vnc_auto.html -> vnc.html
-rw-r--r-- 1 root root  6323 Oct 22  2021 vnc_lite.html
bash: ss: command not found
bash: ss: command not found
root@d2371218bb4b:/app# export DISPLAY=:99
x11vnc -display :99 -forever -shared -nopw -listen 0.0.0.0 -xkb -rfbport 5900 > /tmp/x11vnc.log 2>&1 &
websockify 6080 localhost:5900 --web /usr/share/novnc > /tmp/websockify.log 2>&1 &
[3] 2620
[4] 2621
root@d2371218bb4b:/app# ps aux | grep -E 'x11vnc|websockify'
curl -I http://localhost:6080/
curl -I http://localhost:6080/vnc.html
root        2620  0.2  0.2  51852 18560 pts/0    S    16:03   0:00 x11vnc -display :99 -forever -shared -nopw -listen 0.0.0.0 -xkb -rfbport 5900
root        2621  1.5  0.4  59012 36804 pts/0    S    16:03   0:00 /usr/bin/python3 /usr/bin/websockify 6080 localhost:5900 --web /usr/share/novnc
root        2623  0.0  0.0   4088  1920 pts/0    S+   16:03   0:00 grep --color=auto -E x11vnc|websockify
HTTP/1.1 200 OK
Server: WebSockify Python/3.12.3
Date: Thu, 09 Apr 2026 16:03:22 GMT
Content-type: text/html; charset=utf-8
Content-Length: 516

HTTP/1.1 200 OK
Server: WebSockify Python/3.12.3
Date: Thu, 09 Apr 2026 16:03:22 GMT
Content-type: text/html
Content-Length: 15212
Last-Modified: Fri, 22 Oct 2021 08:40:13 GMT

root@d2371218bb4b:/app# 
    '''