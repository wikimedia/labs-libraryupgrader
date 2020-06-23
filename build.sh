#!/bin/sh
docker build . --tag=libraryupgrader --rm=false
docker build diff-libraries/ -t diff-libraries
