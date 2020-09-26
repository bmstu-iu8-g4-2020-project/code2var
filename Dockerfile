FROM ubuntu:18.04
LABEL maintainer="rus.kulagin2001@yandex.ru"

RUN set -e
RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y install bash
RUN apt-get -y install unzip
RUN apt-get -y install curl
RUN apt-get -y install openjdk-11-jre
RUN apt-get -y install maven
RUN apt-get -y install wget

### 3. Get Python, PIP

RUN apt-get install  python3 python3-pip -y
RUN pip3 install --upgrade pip setuptools
RUN \
if [ ! -d /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi
RUN \
if [ ! -d /usr/bin/python ]; then ln -sf /usr/bin/python3 /usr/bin/python; fi
RUN rm -r /root/.cache

