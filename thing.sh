git clone https://gerrit.wikimedia.org/r/mediawiki/extensions/$EXT.git --depth=1
cd $EXT
composer update
composer require mediawiki/mediawiki-codesniffer $VERSION --prefer-dist
echo '------------'
php ./vendor/bin/phpcs --report=json
echo -e "\n"
echo '------------'
