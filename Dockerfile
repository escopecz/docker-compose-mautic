FROM mautic/mautic:5.0.3-apache
RUN php ../vendor/bin/composer require chimpino/theme-air --working-dir=.. --no-interaction