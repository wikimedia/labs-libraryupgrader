FROM rust:latest AS rust-builder
RUN apt-get update && apt-get install -y libssl-dev
RUN cargo install gerrit-grr

FROM docker-registry.wikimedia.org/wikimedia-buster
ENV LANG C.UTF-8
ENV CHROME_BIN /usr/bin/chromium
ENV CHROMIUM_FLAGS "--no-sandbox"
RUN apt-get update && \
    apt-get install -y nodejs git ssh curl unzip \
    ruby ruby-dev rubygems-integration \
    python build-essential pkg-config \
    php-cli php-xml php-zip php-gd \
    php-gmp php-mbstring php-curl php-intl \
    php-igbinary php-xdebug php-ldap \
    python3 python3-dev python3-venv \
    # explicitly include libssl, for grr
    libssl1.1 \
    firefox-esr chromium \
    --no-install-recommends && rm -rf /var/lib/apt/lists/* && \
    # xdebug slows everything down, it'll be manually enabled as needed
    phpdismod xdebug
RUN git clone --depth 1 https://gerrit.wikimedia.org/r/integration/npm.git /srv/npm \
    && rm -rf /srv/npm/.git \
    && ln -s /srv/npm/bin/npm-cli.js /usr/bin/npm \
    # TODO: Use packaged composer once Debian's #934104 is fixed.
    && git clone --depth 1 https://gerrit.wikimedia.org/r/integration/composer.git /srv/composer \
    && rm -rf /srv/composer/.git \
    && ln -s /srv/composer/vendor/bin/composer /usr/bin/composer
COPY --from=rust-builder /usr/local/cargo/bin/grr /usr/bin/grr
COPY files/gitconfig /etc/gitconfig
RUN gem install --no-rdoc --no-ri jsduck

RUN install --owner=nobody --group=nogroup --directory /cache
RUN install --owner=nobody --group=nogroup --directory /src
RUN install --owner=nobody --group=nogroup --directory /venv
# Some tooling (e.g. git config) is easier if we have a home dir.
RUN install --owner=nobody --group=nogroup --directory /nonexistent

USER nobody
COPY files/known_hosts /nonexistent/.ssh/known_hosts
ENV PYTHONUNBUFFERED 1
RUN python3 -m venv /venv/ && /venv/bin/pip install -U wheel
COPY setup.py /src/
COPY requirements.txt /src/
COPY ./libup /src/libup
RUN cd src/ \
    && /venv/bin/pip install -r requirements.txt \
    && /venv/bin/python setup.py install
ENV COMPOSER_PROCESS_TIMEOUT 1800
# Shared cache
ENV NPM_CONFIG_CACHE=/cache
ENV XDG_CACHE_HOME=/cache
WORKDIR /src
ENTRYPOINT ["/src/libup/timeout-wrapper.sh"]
CMD ["libup-ng"]
