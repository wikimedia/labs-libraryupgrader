FROM docker-registry.wikimedia.org/wikimedia-buster
ENV LANG C.UTF-8
ENV CHROME_BIN /usr/bin/chromium
ENV CHROMIUM_FLAGS "--no-sandbox"
RUN apt-get update && \
    apt-get install -y nodejs git ssh \
    ruby ruby-dev rubygems-integration \
    python build-essential pkg-config \
    php-cli php-xml php-zip php-gd \
    php-gmp php-mbstring php-curl php-intl \
    python3 python3-dev python3-pip python3-venv \
    python3-virtualenv python3-setuptools \
    firefox-esr chromium \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 https://gerrit.wikimedia.org/r/integration/npm.git /srv/npm \
    && rm -rf /srv/npm/.git \
    && ln -s /srv/npm/bin/npm-cli.js /usr/bin/npm \
    # TODO: Use packaged composer once Debian's #934104 is fixed.
    && git clone --depth 1 https://gerrit.wikimedia.org/r/integration/composer.git /srv/composer \
    && rm -rf /srv/composer/.git \
    && ln -s /srv/composer/vendor/bin/composer /usr/bin/composer
# TODO move grr into venv
RUN pip3 install grr poetry
RUN gem install --no-rdoc --no-ri jsduck

RUN install --owner=nobody --group=nogroup --directory /src
# Some tooling (e.g. git config) is easier if we have a home dir.
RUN install --owner=nobody --group=nogroup --directory /nonexistent

USER nobody
COPY files/known_hosts /nonexistent/.ssh/known_hosts
ENV PYTHONUNBUFFERED 1
ENV POETRY_VIRTUALENVS_PATH /nonexistent/virtualenvs
COPY pyproject.toml /src/
COPY poetry.lock /src/
COPY ./libup /src/libup
RUN cd /src && poetry install --no-dev
ENV COMPOSER_PROCESS_TIMEOUT 1800
# Shared cache
ENV NPM_CONFIG_CACHE=/cache
ENV XDG_CACHE_HOME=/cache
WORKDIR /src
ENTRYPOINT ["poetry", "run"]
CMD ["libup-ng"]
