<?php
// Produce private stage/live config from the M7 migration and untouched M4 config.
// Arguments: migrated.php source.php output-dir database host password-file site-url
[$script,$migrated,$source,$output,$database,$host,$passwordFile,$siteUrl]=$argv;
require $migrated;
$modern=$parameters;
require $source;
$original=$parameters;
$parameters=$modern;
$parameters['db_host']=$host;
$parameters['db_port']=3306;
$parameters['db_name']=$database;
$parameters['db_user']=$database;
$parameters['db_password']=trim(file_get_contents($passwordFile));
$parameters['site_url']=$siteUrl;
$parameters['cache_path']='/var/www/html/var/cache';
$parameters['log_path']='/var/www/html/var/logs';
$parameters['tmp_path']='/var/www/html/var/tmp';
$parameters['upload_dir']='/var/www/html/docroot/media/files';
$parameters['image_path']='/var/www/html/docroot/media/images';
$parameters['mailer_spool_path']='/var/www/html/var/spool';
$parameters['trusted_proxies']=['127.0.0.1','REMOTE_ADDR'];
$parameters['cronfig']=$original['cronfig']??[];
if (($original['mailer_transport']??'')!=='smtp' || ($original['mailer_spool_type']??'')!=='memory') {
    throw new RuntimeException('Unreviewed source mail transport; manual conversion required.');
}
$scheme=($original['mailer_encryption']??'')==='ssl'?'smtps':'smtp';
$dsn=$scheme.'://'.rawurlencode($original['mailer_user']).':'.rawurlencode($original['mailer_password']).'@'.$original['mailer_host'].':'.$original['mailer_port'];
// Mautic resolves percent placeholders through its parameter container.
$parameters['mailer_dsn']=str_replace('%','%%',$dsn);
$parameters['messenger_dsn_email']='sync://';
$parameters['messenger_dsn_hit']='sync://';
foreach(['mailer_from_email','mailer_from_name','mailer_return_path','mailer_reply_to_email'] as $key){
    if(array_key_exists($key,$original))$parameters[$key]=$original[$key];
}
file_put_contents($output.'/local.live.php',"<?php\n\$parameters = ".var_export($parameters,true).";\n");
$parameters['mailer_dsn']='null://null';
$parameters['cronfig']=['api_key'=>'','secret_key'=>''];
file_put_contents($output.'/local.stage.php',"<?php\n\$parameters = ".var_export($parameters,true).";\n");
chmod($output.'/local.live.php',0600);chmod($output.'/local.stage.php',0600);
