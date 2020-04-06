To build the docker image:
`$ ./build.sh`

To run libraryupgrader:
`$ docker run libraryupgrader libup-ng <repo> <output>`

To output libraryupgrader help:
```
$ docker run libraryupgrader libup-ng -h
usage: libup-ng [-h] repo output

next generation of libraryupgrader

positional arguments:
  repo        Git repository
  output      Path to output results to

optional arguments:
  -h, --help  show this help message and exit
```

To upgrade mediawiki/core:
`$ docker run libraryupgrader libup-ng mediawiki/core /tmp/libup`