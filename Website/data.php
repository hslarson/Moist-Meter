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

			/* Construct the Score String
				- 3 numeric characters for score. 000 if score has aplha characters
				- x characters for text. Usually "N/A" if anything
				- 3 separator characters: %%%
				- 2 numeric characters for sorting awards 
					- 01-09 -> "Worst of..."
					- 10    -> No award
					- 11-19 -> "Best of..."
				- x characters of award text. Will be displayed in tooltip
			*/
			$score_str = (is_numeric($elem["score"]) ? "" : "000") . $elem["score"];
			$score_str = str_pad($score_str, 3, "0", STR_PAD_LEFT) . "%%%";

			/* Add Award*/
			if (isset($elem["award"])) {				
				$award = strtolower($elem["award"]);

				/* Get award type */ 
				$best = strpos($award, "best") !== FALSE;
				$score_str .=  $best ? "1" : "0";

				/* Add priority number for sorting */
				if (
					(strpos($award, "2nd") !== FALSE) ||
					(strpos($award, "3rd") !== FALSE) ||
					(strpos($award, "4th") !== FALSE) ||
					(strpos($award, "5th") !== FALSE) ||
					(strpos($award, "6th") !== FALSE) ||
					(strpos($award, "7th") !== FALSE) ||
					(strpos($award, "8th") !== FALSE) ||
					(strpos($award, "9th") !== FALSE)
				) {
					$pri = (int)(strpbrk($award, "23456789")[0]);
					$score_str .= strval($best ? 10-$pri : $pri); 
				}
				else { $score_str .=  $best ? "9" : "1"; }

				/* Add tooltip text */
				$score_str .= $elem["award"];
			}
			else { $score_str .= "10"; }

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
