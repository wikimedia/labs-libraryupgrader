FROM debian:stretch
ENV LANG C.UTF-8
ADD backports.list /etc/apt/sources.list.d/backports.list
RUN apt-get update && apt-get install -y nodejs -t stretch-backports && \
    apt-get install -y composer git \
    ruby ruby2.3 ruby2.3-dev rubygems-integration \
    python-minimal build-essential \
    php-ast php-xml php-zip php-gd php-gmp php-mbstring php-curl \
    python3 python3-pip python3-setuptools python3-wheel python3-requests \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN gem install --no-rdoc --no-ri jsduck
RUN git clone --depth 1 https://gerrit.wikimedia.org/r/p/integration/npm.git /srv/npm \
    && rm -rf /srv/npm/.git \
    && ln -s /srv/npm/bin/npm-cli.js /usr/bin/npm
RUN pip3 install grr
RUN git config --global user.name "libraryupgrader"
RUN git config --global user.email "tools.libraryupgrader@tools.wmflabs.org"
ENV COMPOSER_PROCESS_TIMEOUT 1800
# Shared cache
ENV NPM_CONFIG_CACHE=/cache
ENV XDG_CACHE_HOME=/cache
COPY ./container /usr/src/myapp
COPY container/ng.py /usr/bin/libup-ng
WORKDIR /usr/src/myapp
CMD [ "python3", "thing.py" ]
