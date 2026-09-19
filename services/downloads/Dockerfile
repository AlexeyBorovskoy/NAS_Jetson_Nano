# Домашняя качалка: aria2 (торренты + HTTP) и AriaNg (запасной веб-интерфейс в LAN).
# Собирается на Jetson (arm64). Версия AriaNg и SHA-256 архива закреплены.
FROM alpine:3.20
ARG ARIANG_VERSION=1.3.14
ARG ARIANG_SHA256=65bc5ed3573ef05313ea953a5c5363c8b33a4996849b2986c78660eab1a9edb2
RUN apk add --no-cache aria2 bash busybox-extras \
 && wget -q -O /tmp/ariang.zip "https://github.com/mayswind/AriaNg/releases/download/${ARIANG_VERSION}/AriaNg-${ARIANG_VERSION}-AllInOne.zip" \
 && echo "${ARIANG_SHA256}  /tmp/ariang.zip" | sha256sum -c - \
 && mkdir -p /www && unzip -q /tmp/ariang.zip -d /www && rm /tmp/ariang.zip \
 && adduser -D -u 1000 dl
COPY aria2.conf /etc/aria2/aria2.conf
COPY entrypoint.sh on_complete.sh on_stop.sh /usr/local/bin/
RUN chmod 0755 /usr/local/bin/entrypoint.sh /usr/local/bin/on_complete.sh /usr/local/bin/on_stop.sh
USER 1000
EXPOSE 6800 6880
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
