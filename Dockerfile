FROM debian:stretch-slim
ENV LANG C.UTF-8
RUN apt-get update && apt-get install -y \
    composer git \
    ruby ruby2.3 ruby2.3-dev rubygems-integration \
    nodejs nodejs-legacy python-minimal build-essential \
    php-ast php-xml php-zip php-gd php-gmp php-mbstring php-curl \
    python3 python3-pip python3-setuptools python3-wheel python3-requests \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN gem install --no-rdoc --no-ri jsduck
RUN git clone --depth 1 https://gerrit.wikimedia.org/r/p/integration/npm.git /srv/npm \
    && rm -rf /srv/npm/.git \
    && ln -s /srv/npm/bin/npm-cli.js /usr/bin/npm
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer 22.0.0 && rm -rf *
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer 18.0.0 && rm -rf *
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer 20.0.0 && rm -rf *
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer 21.0.0 && rm -rf *
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer dev-master --prefer-dist && rm -rf *
RUN cd /tmp && composer require jakub-onderka/php-parallel-lint && rm -rf *
RUN cd /tmp && composer require jakub-onderka/php-console-color && rm -rf *
RUN cd /tmp && composer require jakub-onderka/php-console-highlighter && rm -rf *
RUN pip3 install grr
RUN git config --global user.name "libraryupgrader"
RUN git config --global user.email "tools.libraryupgrader@tools.wmflabs.org"
ENV COMPOSER_PROCESS_TIMEOUT 1800
COPY ./container /usr/src/myapp
WORKDIR /usr/src/myapp
CMD [ "python3", "thing.py" ]
