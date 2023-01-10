FROM alpine:3.17

COPY analyze process /opt/
RUN apk add tini bash exiftool qpdf python3
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["sleep", "infinity"]
