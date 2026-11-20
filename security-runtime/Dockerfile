ARG PHP_IMAGE
FROM ${PHP_IMAGE} AS extensions
ARG APP
RUN apt-get update && apt-get install -y --no-install-recommends libavif-dev libfreetype-dev libjpeg-dev libpng-dev libwebp-dev libxpm-dev libicu-dev libzip-dev libc-client-dev libkrb5-dev libssl-dev
RUN docker-php-ext-configure gd --with-avif --with-freetype --with-jpeg --with-webp --with-xpm \
    && docker-php-ext-install -j4 gd intl zip \
    && if [ "$APP" = mautic ]; then docker-php-ext-configure imap --with-kerberos --with-imap-ssl && docker-php-ext-install -j4 bcmath exif imap mysqli pdo_mysql sockets; fi
FROM scratch AS overlay
COPY --from=extensions /usr/local/bin/php* /usr/local/bin/
COPY --from=extensions /usr/local/bin/phar* /usr/local/bin/
COPY --from=extensions /usr/local/include/php /usr/local/include/php
COPY --from=extensions /usr/local/lib/php/extensions /usr/local/lib/php/extensions
COPY --from=extensions /usr/lib/apache2/modules/libphp.so /usr/lib/apache2/modules/libphp.so
COPY --from=extensions /usr/src/php.tar.xz* /usr/src/
