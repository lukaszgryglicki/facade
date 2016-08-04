<?php

/*
Copyright 2016 Brian Warner

This file is part of Facade, and is made available under the terms of the GNU General Public License version 2.
*/

include_once "includes/delete.php";
include_once "includes/db.php";
$db = setup_db();


if ($_POST["confirmnew_repo"]) {

	$title = "Add a git repo";
	include_once "includes/header.php";

	$project_id = sanitize_input($db,$_POST["project_id"],11);

	echo '<form action="manage" id="newrepo" method="post">
<p><label for="git">Git repository</label><br><span class="text"><input type="text" name="git"></span></p>
<p><input type="hidden" name="project_id" value="' . $project_id . '"><input type="submit" name="new_repo" value="Add repo">
</form>';

	include_once "includes/footer.php";

} elseif ($_POST["new_repo"]) {

	$project_id = sanitize_input($db,$_POST["project_id"],11);

	// add a new repo and return to the project details pages.
	$git = sanitize_input($db,$_POST["git"],256);

	// Only do something if valid input was submitted
	if ($git) {
		$query = "INSERT INTO repos (projects_id,git,status) VALUES ('" . $project_id . "','" . $git . "','New')";  
		query_db($db,$query,"Add new git repo");
	}

	header("Location: /projects?id=" . $project_id);

} elseif ($_POST["confirmdelete_repo"]) {

	$project_id = sanitize_input($db,$_POST["project_id"],11);

	$title = "Deleting git repo";
	include_once "includes/header.php";

	$repo_id = sanitize_input($db,$_POST["repo_id"],11);

	$query = "SELECT git FROM repos WHERE id=" . $repo_id;
	$result = query_db($db,$query,"Getting git repo URL.");

	$row = $result->fetch_assoc();
	$git = $row["git"];

	echo '<p>You are about to delete all data for "' . $git . '" (including all contribution statistics).</p><p><strong>Are you sure?</strong></p><p><form action="manage" id="delete" method="post"><input type="submit" name="delete_repo" value="Delete it"><input type="hidden" name="project_id" value="' . $project_id . '"><input type="hidden" name="repo_id" value="' . $repo_id . '"></form></p>';

	include_once "includes/footer.php";

} elseif ($_POST["delete_repo"]) {

	$project_id = sanitize_input($db,$_POST["project_id"],11);

	delete_repository($db,sanitize_input($db,$_POST["repo_id"],11));

	header("Location: /projects?id=" . $project_id);

} elseif ($_POST["confirmnew_project"]) {

	$title = "Add a new project";
	include_once "includes/header.php";

	echo '<form action="manage" id="newproject" method="post">
<p><label for="project_name">Project name:</label><br><span class="text"><input type="text" name="project_name"></span></p>
<p><label for="project_url">Project website:</label><br><span class="text"><input type="text" name="project_website"></span></p>
<p><label for="project_description">Project description:</label><br><textarea name="project_description" form="newproject" cols=64 rows=4 maxlength=256 ></textarea></p>

<p><input type="submit" name="new_project" value="Add project">
</form>';

	include_once "includes/footer.php";

} elseif ($_POST["new_project"]) {

	$project_name = sanitize_input($db,$_POST["project_name"],64);
	$project_website = sanitize_input($db,$_POST["project_website"],64);
	$project_description = sanitize_input($db,$_POST["project_description"],256);

	if ($project_name) {
		$query = "INSERT INTO projects (name,website,description) VALUES ('" . $project_name . "','" . $project_website . "','" . $project_description . "')";
		query_db($db,$query,"Insert new project");
	}

	header("Location: /projects");

} elseif ($_POST["confirmedit_project"]) {

	$project_id = sanitize_input($db,$_POST["project_id"],11);

	$query = "SELECT name,description,website FROM projects WHERE id=" . $project_id;
	$result = query_db($db,$query,"Getting name, description, and website");

	$project = $result->fetch_assoc();

	$title = "Edit " . $project["name"];
	include_once "includes/header.php";

	echo '<div class="content-block"><h2>Name</h2>
	<form id="editname" action="manage" method="post">
	<p><span class="text"><input type="text" name="project_name" value="' . $project["name"] . '"></span></p>
	<input type="hidden" name="id" value="' . $project_id . '">
	<p><input type="submit" name="edit_name" value="edit name"></p>
	</form>
	</div> <!-- .content-block -->

	<div class="content-block"><h2>Description</h2>
	<form id="editdescription" action="manage" method="post">
	<p><textarea name="project_description" form="editdescription" cols=64 rows=4 maxlength=256>' . $project["description"] . '</textarea></p>
	<input type="hidden" name="id" value="' . $project_id . '">
	<p><input type="submit" name="edit_description" value="edit description"></p>
	</form>
	</div> <!-- .content-block> -->

	<div class="content-block"><h2>Website</h2>
	<form id="editwebsite" action="manage" method="post">
	<p><span class="text"><input type="text" name="project_website" value="' . $project["website"] . '"></span></p>
	<input type="hidden" name="id" value="' . $project_id . '">
	<p><input type="submit" name="edit_website" value="edit website"></p>
	</form>
	</div> <!-- .content-block -->';

	include_once "includes/footer.php";

} elseif ($_POST["edit_name"]) {

	$project_id = sanitize_input($db,$_POST["id"],11);

	// Don't allow an empty name
	if (trim($_POST["project_name"])) {
		$query = "UPDATE projects SET name='" . sanitize_input($db,$_POST["project_name"],64) . "' WHERE id=" . $project_id;
		query_db($db,$query,"updating name");
	}

	header("Location: /projects?id=" . $project_id);

} elseif ($_POST["edit_description"]) {

	$project_id = sanitize_input($db,$_POST["id"],11);

	// An empty description is fine
	$query = "UPDATE projects SET description='" . sanitize_input($db,$_POST["project_description"],256) . "' WHERE id=" . $project_id;
	query_db($db,$query,"updating description");

	header("Location: /projects?id=" . $project_id);

} elseif ($_POST["edit_website"]) {

	$project_id = sanitize_input($db,$_POST["id"],11);

	// An empty website is fine
	$query = "UPDATE projects SET website='" . sanitize_input($db,$_POST["project_website"],64) . "' WHERE id=" . $project_id;
	query_db($db,$query,"updating website");

	header("Location: /projects?id=" . $project_id);

} elseif ($_POST["confirmdelete_project"]) {

	$title = "Deleting project";
	include_once "includes/header.php";

	$project_id = sanitize_input($db,$_POST["project_id"],11);

	$query = "SELECT name FROM projects WHERE id=" . $project_id;
	$result = query_db($db,$query,"Getting project name.");

	$row = $result->fetch_assoc();
	$name = $row["name"];

	echo '<p>You are about to delete all data for "' . $name . '" (including repositories and all contribution statistics).</p><p><strong>Are you sure?</strong></p><p><form action="manage" id="delete" method="post"><input type="submit" name="delete_project" value="Delete it"><input type="hidden" value="' . $project_id . '" name="project_id"></form></p>';


} elseif ($_POST["delete_project"]) {

	delete_project ($db,sanitize_input($db,$_POST["project_id"],11));

	header("Location: /projects");
} elseif ($_POST["confirmnew_excludedomain"]) {

	$title = "Exclude a domain from analysis and results";
	include_once "includes/header.php";

	$project_id = sanitize_input($db,$_POST["project_id"],11);
	$project_name = sanitize_input($db,$_POST["project_name"],64);

	echo '<form action="manage" id="new_excludedomain" method="post">
<p><label for="domain">Domain</label><br><span class="text"><input type="text" name="domain"></span></p>
<p><input type="hidden" name="project_id" value="' . $project_id . '"><input type="submit" name="new_excludedomain" value="Exclude this domain from ' . $project_name . '">
</form>';

	include_once "includes/footer.php";

} elseif ($_POST["new_excludedomain"]) {

	// add a new domain to the exclude list and return to the project details pages.

	$project_id = sanitize_input($db,$_POST["project_id"],11);
	$domain = sanitize_input($db,$_POST["domain"],64);

	// Only do something if valid input was submitted
	if ($domain) {
		$query = "INSERT INTO exclude (projects_id,domain) VALUES ('" . $project_id . "','" . $domain . "')";  
		query_db($db,$query,"Add new exclusion domain");
	}

	header("Location: /projects?id=" . $project_id);

} elseif ($_POST["delete_excludedomain"]) {

	$project_id = sanitize_input($db,$_POST["project_id"],11);
	$exclude_id = sanitize_input($db,$_POST["exclude_id"],11);

	$query = "DELETE FROM exclude WHERE id=" . $exclude_id;
	query_db($db,$query,"Remove domain from exclude list");

	header("Location: /projects?id=" . $project_id);

} elseif ($_POST["confirmnew_excludeemail"]) {

	$title = "Exclude an email from analysis and results";
	include_once "includes/header.php";

	$project_id = sanitize_input($db,$_POST["project_id"],11);
	$project_name = sanitize_input($db,$_POST["project_name"],64);

	echo '<form action="manage" id="new_excludeemail" method="post">
<p><label for="email">Email</label><br><span class="text"><input type="text" name="email"></span></p>
<p><input type="hidden" name="project_id" value="' . $project_id . '"><input type="submit" name="new_excludeemail" value="Exclude this email from ' . $project_name . '">
</form>';

	include_once "includes/footer.php";

} elseif ($_POST["new_excludeemail"]) {

	// add a new email to the exclude list and return to the project details pages.

	$project_id = sanitize_input($db,$_POST["project_id"],11);
	$email = sanitize_input($db,$_POST["email"],64);

	// Only do something if valid input was submitted
	if ($email) {
		$query = "INSERT INTO exclude (projects_id,email) VALUES ('" . $project_id . "','" . $email . "')";  
		query_db($db,$query,"Add new exclusion email");
	}

	header("Location: /projects?id=" . $project_id);


} elseif ($_POST["delete_excludeemail"]) {

	$project_id = sanitize_input($db,$_POST["project_id"],11);
	$exclude_id = sanitize_input($db,$_POST["exclude_id"],11);

	$query = "DELETE FROM exclude WHERE id=" . $exclude_id;
	query_db($db,$query,"Remove email from exclude list");

	header("Location: /projects?id=" . $project_id);

} elseif ($_POST["add_tag"]) {

	$tag = sanitize_input($db,$_POST["select_tag"],64);
	$start_date = sanitize_input($db,$_POST["start_date"],10);
	$email = sanitize_input($db,$_POST["email"],64);

	if ($tag == 'custom') {
		$tag = sanitize_input($db,$_POST["new_tag"],64);
	}

	if (sanitize_input($db,$_POST["end_date"],10) == 'custom') {
		$end_date = sanitize_input($db,$_POST["custom_end"],10);
	}

	if (($tag) && ($start_date) && ($end_date) && ($email) && ($start_date <= $end_date)) {
		// Tag that ends on a specific date
		$query = "INSERT INTO special_tags (tag,start_date,end_date,email) VALUES ('" . $tag . "','" . $start_date . "','" . $end_date . "','" . $email . "')";
		query_db($db,$query,"inserting custom tag");

	} elseif (($tag) && ($start_date) && ($email) && !($end_date)) {
		// Tag that doesn't end on a specific date
		$query = "INSERT INTO special_tags (tag,start_date,email) VALUES ('" . $tag . "','" . $start_date . "','" . $email . "')";
		query_db($db,$query,"inserting custom tag without end date");

	} else {
		echo 'incomplete';
	}

	header("Location: /tags");

} elseif ($_POST["delete_tag"]) {

	$tag_id = sanitize_input($db,$_POST["id"],11);

	if ($tag_id) {
		$query = "DELETE FROM special_tags WHERE id=" . $tag_id;
		query_db($db,$query,"Deleting custom tag.");
	}

	header("Location: /tags");

} else {
	echo "Oops, what did you want to do?";
}


close_db($db);

?>