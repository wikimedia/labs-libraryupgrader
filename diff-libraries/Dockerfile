FROM rustlang/rust:nightly AS builder

COPY Cargo.* /src/
COPY diesel.toml /src/
COPY ./src /src/src
COPY ./migrations /src/migrations
RUN cd /src && cargo build --release

FROM libraryupgrader

COPY --from=builder /src/target/release/diff-libraries /usr/local/bin/diff-libraries
# https://github.com/SergioBenitez/Rocket/issues/943
COPY ./templates /usr/local/bin/templates
ENV DATABASE_URL=/src/db.db
ENV CLONE_DIR=/src/
WORKDIR /usr/local/bin/
ENTRYPOINT ["diff-libraries"]
