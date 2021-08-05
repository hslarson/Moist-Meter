<?php
    function update() {
        // Load Main Webpage
        $site = file_get_contents("../index.html", FALSE);

        // Find the Current Value of the last_update Tag
        $key_phrase = "last_update=";
        $start_i = strpos($site, $key_phrase);
        $end_i = strpos($site, "<", $start_i);
        if ($start_i == $end_i) { exit; }
        $replace_target = substr($site, $start_i, $end_i - $start_i);

        // Replace the Value of the last_update Tage
        $utc_time = strval(time());
        $replace_str = $key_phrase.$utc_time;
        $r_no = 1;
        $site = str_replace($replace_target, $replace_str, $site, $r_no);
        
        // Save the Webpage
        file_put_contents("../index.html", $site);
    }
?>