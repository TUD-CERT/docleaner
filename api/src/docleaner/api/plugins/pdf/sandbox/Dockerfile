FROM alpine:3.17

COPY analyze exiftool.cfg process /opt/
RUN apk add tini bash exiftool qpdf python3 py3-pip; \
    pip3 install pyhanko
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["sleep", "infinity"]
