FROM alpine:3.17

COPY analyze process /opt/
RUN apk add tini bash exiftool py3-pip py3-gobject3 py3-cairo poppler-glib gdk-pixbuf librsvg; \
    pip3 install mat2
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["sleep", "infinity"]
