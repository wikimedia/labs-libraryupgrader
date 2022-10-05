FROM rust:latest AS rust-builder
RUN cargo install gerrit-grr
RUN cargo install package-lock-lint
RUN cargo install cargo-audit

FROM docker-registry.wikimedia.org/bullseye:latest
ENV LANG C.UTF-8
ENV CHROME_BIN /usr/bin/chromium
ENV CHROMIUM_FLAGS "--no-sandbox"
RUN echo "deb http://apt.wikimedia.org/wikimedia bullseye-wikimedia thirdparty/node16" > /etc/apt/sources.list.d/nodejs.list
RUN apt-get update && \
    apt-get install -y firefox-esr chromium
RUN apt-get install -y nodejs git ssh curl unzip \
    ruby ruby-dev rubygems-integration \
    python build-essential pkg-config \
    php-cli php-xml php-zip php-gd \
    php-gmp php-mbstring php-curl php-intl \
    php-igbinary php-xdebug php-ldap php-redis composer \
    python3 python3-dev python3-venv \
    # explicitly include libssl, for grr
    libssl1.1 \
    # for mathoid
    librsvg2-dev \
    --no-install-recommends && rm -rf /var/lib/apt/lists/* && \
    # xdebug slows everything down, it'll be manually enabled as needed
    phpdismod xdebug
COPY --from=rust-builder /usr/local/cargo/bin/grr /usr/bin/grr
COPY --from=rust-builder /usr/local/cargo/bin/package-lock-lint /usr/bin/package-lock-lint
COPY --from=rust-builder /usr/local/cargo/bin/cargo-audit /usr/bin/cargo-audit
COPY files/gitconfig /etc/gitconfig
COPY files/timeout-wrapper.sh /usr/local/bin/timeout-wrapper
RUN gem install jsduck

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
