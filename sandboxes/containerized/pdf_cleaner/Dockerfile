FROM alpine:3.16

COPY process /opt/
RUN apk add tini bash exiftool qpdf
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["sleep", "infinity"]
