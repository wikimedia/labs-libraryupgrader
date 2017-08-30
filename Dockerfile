FROM debian:stretch-slim
RUN apt-get update && apt-get install -y composer git php-xml php-zip php-gd php-mbstring php-curl python3 python3-pip python3-setuptools python3-wheel python3-requests --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer 0.11.0 && rm -rf *
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer 0.11.1 && rm -rf *
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer 0.12.0 && rm -rf *
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer dev-master --prefer-dist && rm -rf *
RUN cd /tmp && composer require jakub-onderka/php-parallel-lint && rm -rf *
RUN cd /tmp && composer require jakub-onderka/php-console-color && rm -rf *
RUN cd /tmp && composer require jakub-onderka/php-console-highlighter && rm -rf *
RUN pip3 install semver
RUN git config --global user.name "libraryupgrader"
RUN git config --global user.email "tools.libraryupgrader@tools.wmflabs.org"
COPY . /usr/src/myapp
WORKDIR /usr/src/myapp
CMD [ "python3", "thing.py" ]

