FROM alpine:3.17

COPY analyze exiftool.cfg process /opt/
RUN apk add tini bash exiftool qpdf python3
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["sleep", "infinity"]
