# Dockerfile for imghostapp

FROM fedora:34

USER root
RUN useradd -ms /bin/bash imghostusr
RUN dnf -y install git make python3-pip python3-virtualenv && \
    dnf clean all

RUN mkdir /workspace
ENV PYTHONUNBUFFERED 1
WORKDIR /workspace
RUN git clone -b main https://github.com/virtualinit/imghostapp .
RUN virtualenv venv
RUN source venv/bin/activate
RUN make devel
RUN cp docker-compose/imghostapp/launch.sh /usr/bin/imghostapp.sh
RUN cp docker-compose/imghostapp/wait-for-it.sh /usr/bin/wait-for-it.sh
RUN chmod -R g+w logs
RUN chown -R imghostusr /workspace
EXPOSE 8080
USER imghostusr
ENTRYPOINT ["/usr/bin/imghostapp.sh"]
