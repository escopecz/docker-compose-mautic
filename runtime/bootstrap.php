<?php
// Secret values stay in the instance volume and never enter process arguments.
$file = '/var/www/html/config/local.php';
if (is_file($file)) { exit(0); }
$password = trim(file_get_contents('/run/secrets/database_password'));
if (!preg_match('/^[a-f0-9]{48}$/D', $password)) { throw new RuntimeException('Invalid database secret'); }
$domain = getenv('MAUTIC_DOMAIN');
$parameters = [
    'db_driver' => 'pdo_mysql', 'db_host' => 'mysql', 'db_port' => 3306,
    'db_name' => getenv('MAUTIC_DB_DATABASE'), 'db_user' => getenv('MAUTIC_DB_DATABASE'),
    'db_password' => $password, 'db_table_prefix' => null,
    'trusted_hosts' => ['^'.preg_quote($domain, '~').'$', '^localhost$', '^127\.0\.0\.1$'],
    'trusted_proxies' => json_decode(getenv('TRUSTED_PROXIES') ?: '[]', true, 512, JSON_THROW_ON_ERROR),
    'mailer_dsn' => 'null://null',
    'messenger_dsn_email' => 'doctrine://default',
    'messenger_dsn_hit' => 'doctrine://default',
];
// Only web is started for installation. Jobs are enabled separately afterwards.
file_put_contents($file, "<?php\n\$parameters = ".var_export($parameters, true).";\n");
chown($file, 'www-data'); chgrp($file, 'www-data'); chmod($file, 0640);
