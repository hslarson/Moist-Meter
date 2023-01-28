<?php
	/* Update Cache if Necessary */
	if (!file_exists("./.data_cache.json") or (filemtime("./.data.json") > filemtime("./.data_cache.json"))) {

		/* Load the Data File */
		$data = json_decode(file_get_contents("./.data.json"), TRUE);

		$out = [];
		foreach ($data as $key => $elem) {
			if (! $elem["rated"]) { continue; }

			/* Format Title */
			$title = trim( str_replace("Moist Meter:", "", str_replace("Moist Meter |", "", strval($elem["title"]))) );

			/* Construct the Score String */
			$score_str = (is_numeric($elem["score"]) ? "" : "000") . $elem["score"]; /* Pad Non-Numeric Scores with 0's */
			while (strlen($score_str) < 3) { $score_str = "0" . $score_str; }
			$score_str .= (isset($elem["award"]) ? "%%%" . $elem["award"] : ""); /* Add Award */

			/* Push to Array */
			$obj = [];
			$obj["num"] = count($data) - $key;
			$obj["date"] = $elem["date"];
			$obj["category"] = $elem["category"];
			$obj["title_id"] = $title . "%%%" . $elem["id"];
			$obj["score"] = $score_str;
			array_push($out, $obj);
		}

		/* Write Data to Cache */
		file_put_contents("./.data_cache.json", json_encode($out, JSON_PRETTY_PRINT));
	}
	

	header('Content-Type: application/json');

	/* Load the Data File */
	$data = json_decode(file_get_contents("./.data_cache.json"), TRUE);
	$start_index = 0;
	$end_index = count($data);

	/* Parse the Request */
	if (isset($_GET['start'])) { $start_index = intval($_GET['start']); }
	if (isset($_GET['end'])) { $end_index = ($end_index >= $start_index ? intval($_GET['end']) : $end_index); }
	
	/* Load Quotes */
	$quotes = json_decode(file_get_contents("./.quotes.json"), TRUE);

	/* Create Output JSON */
	$out = [];
	$out["quote"] = $quotes[rand(0, count($quotes)-1)];
	$out["data"] = array_slice($data, $start_index, $end_index-$start_index);

	echo json_encode($out);
?>
