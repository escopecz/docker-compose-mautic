# Mautic 7.2.1, PHP 8.3.36. Build once; all instances share this image.
FROM mautic/mautic@sha256:2d249853dc475ce0b0c2415d09dc43657496047c21b5bfb0a383415673ebf54b AS upstream
# Node.js 24.22.1 is used only to compile editor assets.
FROM node@sha256:55fb5f5a527ea2c5c4a95f963e48ef90aa38c7b346054fdc8ee9957a2b55d205 AS editor
WORKDIR /build
COPY --from=upstream /var/www/html/docroot/plugins/GrapesJsBuilderBundle/ ./
RUN npm ci --no-audit && npm run build
FROM upstream
COPY --from=editor /build/Assets/library/js/dist/ /var/www/html/docroot/plugins/GrapesJsBuilderBundle/Assets/library/js/dist/
COPY runtime/ /opt/example/
COPY runtime/php.ini /usr/local/etc/php/conf.d/zz-example.ini
COPY runtime/apache.conf /etc/apache2/conf-enabled/zz-example.conf
RUN rm -rf /var/www/html/var/cache/* && chown -R www-data:www-data /var/www/html/config /var/www/html/var /var/www/html/docroot/media
ENTRYPOINT ["/bin/bash", "/opt/example/start.sh"]
