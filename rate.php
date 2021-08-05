<?php
    include('./update.php');
    header('Content-Type: application/json');

    // Parse the Request
    if (isset($_POST['id'], $_POST['category'], $_POST['score'])) {
        $id = htmlentities($_POST['id']);
        $category = htmlentities($_POST['category']);
        $score = htmlentities($_POST['score']);
    }
    
    // Load the Data File
    $data = json_decode(file_get_contents("../.data.json"), TRUE);

    // Find the Element We Want to Modify and Modify it
    $m = "No Matching Element Found";

    foreach ($data as $key => $elem) {
        
        if ($elem['id'] == $id) {
            $m = "Found Element, Adding Score";
            
            // Save Score
            $data[$key]["category"] = $category;
            $data[$key]["score"] = $score;
            $data[$key]["rated"] = TRUE;

            file_put_contents("../.data.json", json_encode($data, JSON_PRETTY_PRINT)); // Save the File
            update(); // Update the last_update Tag
            break;
        }
    }
    // Return the JSON Response
    echo json_encode($m);
?>