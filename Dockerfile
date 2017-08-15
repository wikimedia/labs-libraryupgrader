FROM debian:stretch-slim
COPY . /usr/src/myapp
RUN apt-get update && apt-get install -y composer git php-xml php-zip php-gd php-mbstring php-curl python3 --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer 0.10.0 && rm -rf *
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer 0.10.1 && rm -rf *
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer 0.11.0 && rm -rf *
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer dev-master --prefer-dist && rm -rf *
RUN cd /tmp && composer require jakub-onderka/php-parallel-lint && rm -rf *
RUN cd /tmp && composer require jakub-onderka/php-console-color && rm -rf *
RUN cd /tmp && composer require jakub-onderka/php-console-highlighter && rm -rf *
WORKDIR /usr/src/myapp
CMD [ "bash", "./thing.sh" ]

