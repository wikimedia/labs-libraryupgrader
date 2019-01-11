FROM docker-registry.wikimedia.org/releng/node10-test:latest
ENV LANG C.UTF-8
RUN apt-get update && apt-get install -y \
    composer git build-essential \
    php-ast php-xml php-zip php-gd php-gmp php-mbstring php-curl \
    python3 python3-pip python3-setuptools python3-wheel python3-requests \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN pip3 install grr
RUN git config --global user.name "libraryupgrader"
RUN git config --global user.email "tools.libraryupgrader@tools.wmflabs.org"
ENV COMPOSER_PROCESS_TIMEOUT 1800
# Shared cache
ENV NPM_CONFIG_CACHE=/cache
ENV XDG_CACHE_HOME=/cache
COPY ./container /usr/src/myapp
WORKDIR /usr/src/myapp
CMD [ "python3", "thing.py" ]
