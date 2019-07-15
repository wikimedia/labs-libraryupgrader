FROM debian:stretch
ENV LANG C.UTF-8
ADD backports.list /etc/apt/sources.list.d/backports.list
COPY known_hosts /root/.ssh/known_hosts
RUN apt-get update && apt-get install -y nodejs -t stretch-backports && \
    apt-get install -y composer git ssh \
    ruby ruby2.3 ruby2.3-dev rubygems-integration \
    python-minimal build-essential pkg-config \
    php-ast php-xml php-zip php-gd php-gmp php-mbstring php-curl \
    python3 python3-dev python3-pip python3-virtualenv \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN gem install --no-rdoc --no-ri jsduck
RUN git clone --depth 1 https://gerrit.wikimedia.org/r/p/integration/npm.git /srv/npm \
    && rm -rf /srv/npm/.git \
    && ln -s /srv/npm/bin/npm-cli.js /usr/bin/npm
# TODO move grr into venv
RUN pip3 install grr
RUN python3 -m virtualenv -p python3 /venv
# TODO use package for pipenv in buster
RUN /venv/bin/pip install pipenv
RUN mkdir -p /venv/src/
COPY Pipfile /venv/src/
COPY Pipfile.lock /venv/src/
COPY setup.py /venv/src/
COPY ./libup /venv/src/libup
RUN cd /venv/src && /venv/bin/pipenv install --deploy \
    && /venv/bin/pipenv run python setup.py install
RUN git config --global user.name "libraryupgrader"
RUN git config --global user.email "tools.libraryupgrader@tools.wmflabs.org"
ENV COMPOSER_PROCESS_TIMEOUT 1800
# Shared cache
ENV NPM_CONFIG_CACHE=/cache
ENV XDG_CACHE_HOME=/cache
COPY ./libup /venv/src
WORKDIR /venv/src
ENTRYPOINT ["/venv/bin/pipenv", "run"]
CMD ["libup-ng"]
