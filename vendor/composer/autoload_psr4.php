<?php

// autoload_psr4.php @generated by Composer

$vendorDir = dirname(__DIR__);
$baseDir = dirname($vendorDir);

return array(
    'think\\view\\driver\\' => array($vendorDir . '/topthink/think-view/src'),
    'think\\captcha\\' => array($vendorDir . '/topthink/think-captcha/src'),
    'think\\' => array($vendorDir . '/topthink/think-helper/src', $vendorDir . '/topthink/think-orm/src', $vendorDir . '/topthink/think-template/src', $vendorDir . '/topthink/framework/src/think'),
    'app\\' => array($baseDir . '/app'),
    'Psr\\SimpleCache\\' => array($vendorDir . '/psr/simple-cache/src'),
    'Psr\\Log\\' => array($vendorDir . '/psr/log/Psr/Log'),
    'Psr\\Http\\Message\\' => array($vendorDir . '/psr/http-message/src'),
    'Psr\\Container\\' => array($vendorDir . '/psr/container/src'),
    'Psr\\Cache\\' => array($vendorDir . '/psr/cache/src'),
    'League\\MimeTypeDetection\\' => array($vendorDir . '/league/mime-type-detection/src'),
    'League\\Flysystem\\Cached\\' => array($vendorDir . '/league/flysystem-cached-adapter/src'),
    'League\\Flysystem\\' => array($vendorDir . '/league/flysystem/src'),
);
