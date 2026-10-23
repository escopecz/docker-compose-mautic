<?php
// Complete M5 migration 20201026101117's postUp after the full schema exists.
// Its original ORM query ran before later columns existed; its iterator also
// assumes array rows, while this Doctrine version yields entities directly.
if (PHP_SAPI !== 'cli') { exit(1); }
require '/var/www/html/vendor/autoload.php';
$app = include '/var/www/html/app/console-application.php';
$kernel = $app->getKernel();
$kernel->boot();
$em = $kernel->getContainer()->get('doctrine.orm.entity_manager');
$types = [
    Mautic\EmailBundle\Entity\Email::class => ['Name', 'Subject', 'CustomHtml', 'PlainText'],
    Mautic\EmailBundle\Entity\Copy::class => ['Subject', 'Body', 'BodyText'],
    Mautic\DynamicContentBundle\Entity\DynamicContent::class => ['Description'],
];
foreach ($types as $class => $fields) {
    $count = 0;
    foreach ($em->createQuery("SELECT e FROM $class e")->toIterable() as $row) {
        $entity = is_array($row) ? $row[0] : $row;
        foreach ($fields as $field) {
            $getter = 'get'.$field; $setter = 'set'.$field;
            $value = $entity->$getter();
            if ($value !== null) {
                $entity->$setter(Mautic\CoreBundle\Helper\EmojiHelper::toEmoji($value, 'short'));
            }
        }
        if (++$count % 50 === 0) { $em->flush(); $em->clear(); }
    }
    $em->flush(); $em->clear();
    printf("%s: %d records checked\n", $class, $count);
}
