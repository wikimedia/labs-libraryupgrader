#!/bin/sh
docker build . --tag=libraryupgrader --rm=false --pull
docker build diff-libraries/ -t diff-libraries --pull
