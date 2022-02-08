To build the docker image:
`$ ./build.sh`

To run libraryupgrader:
`$ docker run libraryupgrader libup-ng <repo> <output>`

To output libraryupgrader help:
```
$ docker run libraryupgrader libup-ng -h
usage: libup-ng [-h] repo output [--branch BRANCH]

next generation of libraryupgrader

positional arguments:
  repo        Git repository
  output      Path to output results to

optional arguments:
  -h, --help  show this help message and exit
  --branch BRANCH  Git branch
```

To upgrade mediawiki/core (master branch):
`$ docker run libraryupgrader libup-ng mediawiki/core /tmp/libup`

To upgrade mediawiki/core (REL1_35 branch):
`$ docker run libraryupgrader libup-ng mediawiki/core /tmp/libup --branch REL1_35`