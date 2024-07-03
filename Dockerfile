# Build stage:
FROM mautic/mautic:5.0.3-apache
WORKDIR /var/www/html

# Install dependencies needed for Composer to run and rebuild assets:
RUN apt-get update && apt-get install -y git curl npm && rm -rf /var/lib/apt/lists/*

RUN php vendor/bin/composer require chimpino/theme-air

# Production stage:
FROM mautic/mautic:5.0.3-apache
WORKDIR /var/www/html

# Copy the built assets and the Mautic installation from the build stage:
COPY --from=builder --chown=www-data:www-data /var/www/html /var/www/html