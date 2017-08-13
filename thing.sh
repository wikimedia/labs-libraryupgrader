git clone https://gerrit.wikimedia.org/r/mediawiki/extensions/$EXT.git --depth=1
cd $EXT
composer update
if [ -n "$VERSION" ]; then
    composer require mediawiki/mediawiki-codesniffer $VERSION --prefer-dist;
fi;
echo '------------'
php ./vendor/bin/phpcs --report=json
echo -e "\n"
echo '------------'
