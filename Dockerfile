FROM debian:stretch-slim
COPY . /usr/src/myapp
RUN apt-get update && apt-get install -y composer git php-xml php-zip php-gd php-mbstring php-curl --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN cd /tmp && composer require mediawiki/mediawiki-codesniffer
RUN cd /tmp && composer require jakub-onderka/php-parallel-lint
RUN cd /tmp && composer require jakub-onderka/php-console-color
RUN cd /tmp && composer require jakub-onderka/php-console-highlighter
WORKDIR /usr/src/myapp
CMD [ "bash", "./thing.sh" ]

