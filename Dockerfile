FROM rust:latest AS rust-builder
RUN cargo install gerrit-grr
RUN cargo install package-lock-lint
RUN cargo install cargo-audit

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
    php-igbinary php-xdebug php-ldap php-redis \
    python3 python3-dev python3-venv \
    # explicitly include libssl, for grr
    libssl1.1 \
    # for mathoid
    librsvg2-dev \
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
COPY --from=rust-builder /usr/local/cargo/bin/package-lock-lint /usr/bin/package-lock-lint
COPY --from=rust-builder /usr/local/cargo/bin/cargo-audit /usr/bin/cargo-audit
COPY files/gitconfig /etc/gitconfig
COPY files/timeout-wrapper.sh /usr/local/bin/timeout-wrapper
RUN gem install --no-rdoc --no-ri jsduck

RUN install --owner=nobody --group=nogroup --directory /cache
RUN install --owner=nobody --group=nogroup --directory /src
RUN install --owner=nobody --group=nogroup --directory /venv
# Some tooling (e.g. git config) is easier if we have a home dir.
RUN install --owner=nobody --group=nogroup --directory /nonexistent

USER nobody
ENV PYTHONUNBUFFERED 1
RUN python3 -m venv /venv/ && /venv/bin/pip install -U wheel
COPY runner/setup.py /src/
COPY runner/requirements.txt /src/
RUN cd src/ \
    && /venv/bin/pip install -r requirements.txt
COPY ./runner/runner /src/runner
RUN cd src/ \
    && /venv/bin/python setup.py install
ENV COMPOSER_PROCESS_TIMEOUT 1800
# Shared cache
ENV NPM_CONFIG_CACHE=/cache
ENV XDG_CACHE_HOME=/cache
ENV BROWSERSLIST_IGNORE_OLD_DATA="yes"
WORKDIR /src
ENTRYPOINT ["/usr/local/bin/timeout-wrapper"]
CMD ["runner"]
