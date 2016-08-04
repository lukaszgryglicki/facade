<?php

/*
Copyright 2016 Brian Warner

This file is part of Facade, and is made available under the terms of the GNU General Public License version 2.
*/

$title = "Configuration";

include_once "includes/header.php";
include_once "includes/db.php";
$db = setup_db();

if ($_SERVER["REQUEST_METHOD"] == "POST") {

	$setting = sanitize_input($db,$_POST["setting"],32);

	if ($_POST["confirmedit"]) {

		echo '<div class="content-block"><form action="' . htmlspecialchars($_SERVER["PHP_SELF"]) . '" id="editsettings" method="POST"><input type="hidden" name="setting" value="' . $setting . '">';

		if ($setting == "end_date") {

			echo '<h2>Edit date that analysis begins</h2><p><strong>Note:</strong> Changing this will affect your entire database, as current data outside the date range will be dropped.  New dates will be added.</p><p>Changes will take effect the next time facade-worker.py is run.</p>
			<p><select id="select_end_date" name="select_end_date" onchange="custom_input(this,\'custom_date\',\'70\')">
			<option value="yesterday">Default (yesterday)</option>
			<option value="custom">Custom</option>
			</select>
			<input type="text" id="custom_date" name="value" class="custom-input hidden"></p>';

		} elseif ($setting == "start_date") {

			echo '<h2>Edit date that analysis ends</h2><p><strong>Note:</strong> Changing this will affect your entire database, as current data outside the date range will be dropped.  New dates will be rebuilt.</p><p>Changes will take effect the next time facade-worker.py is run.</p>
			<p>Begin on a specific date (yyyy-mm-dd): <span class="text"><input type="text" name="value"></span></p>';

		} elseif ($setting == "gitdm") {

			echo '<h2>Where is the gitdm directory on the system?</h2><p>System path to gitdm: <span class="text"><input type="text" name="value"></span></p>';

		} elseif ($setting == "repo_directory") {

			echo '<h2>Where are you keeping the data?</h2><p><strong>Note:</strong> You should pause your repo maintenance cron job until this is set. If you are moving your repositories, copy them to the new location and then change this. Changing this setting will not move the repos automatically; you must do that yourself.  Afterwards, make sure you run the maintenance script at least once before the daily analysis to ensure everything was found and updated properly.</p>
			<p>System path to git repository directory: <span class="text"><input type="text" name="value"></span></p>
			<p><input type="checkbox" name="rebuild_repos">&nbsp;&nbsp;Re-clone all git repos at new location instead of moving existing repos. Will not cause you to lose analysis data.</p>';

		} elseif ($setting == "log_level") {

			echo '<h2>How much info do you want to collect?</h2>
			<p><input type="radio" name="log_level_radio" value="Quiet" id="log_level_quiet" checked="checked"><label for="log_level_quiet">&nbsp;&nbsp;Only log errors.</label></p>
			<p><input type="radio" name="log_level_radio" value="Info" id="log_level_info"><label for="log_level_info">&nbsp;&nbsp;Information on analysis, including when everything starts and finishes.</label></p>';

		} else {
			echo '<div class="info">Unknown setting.</div>';
		}

		echo '<input type="submit" name="edit" value="Apply setting"></form></div>';


	} elseif ($_POST["edit"]) {

		$value = sanitize_input($db,$_POST["value"],32);

		if ($setting == "end_date") {

			$select_end_date = sanitize_input($db,$_POST["select_end_date"],9);

			if ($select_end_date == "yesterday") {

				$value = $select_end_date;
			}
		}

		if ($setting == "log_level") {

			$value = sanitize_input($db,$_POST["log_level_radio"],10);
		}

		if ($value) {

			$safe_setting = TRUE;

			if ($setting == "start_date") {
				if (($value > get_setting($db,"end_date")) || ((get_setting($db,"end_date") == 'yesterday') && ($value > date("Y-m-d",time()-60*60*24)))) {
					echo '<div class="info"><p>Check your start and end dates, they appear to be out of order.</p></div>';
				}
			}

			if ($setting == "end_date") {
				if (($value < get_setting($db,"start_date")) || (($value == 'yesterday') && (get_setting($db,"start_date") > date("Y-m-d",time()-60*60*24)))) {
					echo '<div class="info"><p>Check your start and end dates, they appear to be out of order.</p></div>';
				}
			}

			if (($setting == "repo_directory") || ($setting == "gitdm")) {

				if (sanitize_input($db,$_POST["rebuild_repos"],1)) {
					$query = "UPDATE repos SET status='New'";
				}

				if (substr($value,0,1) != '/') {
					echo '<div class="info"><p><strong>WARNING:</strong><br>You appear to be using a relative path. This is not safe.</p></div>';
					$safe_setting = FALSE;
				}

				if ($value == '/') {
					echo '<div class="info"><p><strong>WARNING:</strong><br>You have set your repo directory to root. This is ok if you <i>really</i> know what you are doing, but you could also <i>really</i> screw up your system.</p><p>You have been warned.</p></div>';
				}

				if (substr($value,-1) != '/') {
					$value = $value . "/";
				}
			}

			if ($safe_setting) {
				$query = "INSERT INTO settings (setting,value) VALUES ('" . $setting . "','" . $value . "')";
				query_db($db,$query,"Updating settings");
			}

		} else {
			echo '<div class="info"><p>Cowardly refusing to apply an empty setting.</p></div>';
		}

	}
}

$query = "SELECT last_modified FROM settings WHERE setting='utility_status' ORDER BY last_modified DESC LIMIT 1";
$result = query_db($db,$query,"Get the time of the last status change");

$last_modified = strtotime($result->fetch_assoc()['last_modified']);

echo '<div class="content-block">

<h2>Data collection</h2>

<table>

<tr><td class="half"><strong>Start all analysis on this date</strong><br><i>format: yyyy-mm-dd<br>default: 2000-01-01</i></td><td class="half">' . get_setting($db,"start_date") . edit_setting_button("start_date") . '</td></tr>
<tr><td><strong>End all analysis on this date</strong><br><i>format: yyyy-mm-dd, yesterday<br>default: yesterday</i></td><td>' . get_setting($db,"end_date") . edit_setting_button("end_date") . '</td></tr>
<!--<tr><td><strong>Analysis period</strong><br><i>format: daily, weekly, monthly, annually<br>default: daily</i></td><td>' . get_setting($db,"interval") . edit_setting_button("interval") . '</td></tr>-->
</table>

<h2>System</h2>

<table>
<tr><td class="half"><strong>Location of gitdm directory on server</strong><br><i>format: system path<br>default: /opt/facade/gitdm</i></td><td class="half">' . stripslashes(get_setting($db,"gitdm")) . edit_setting_button("gitdm") . '</td></tr>
<tr><td><strong>Location of git repos (must be writable<br>by user account doing the analysis)</strong><br><i>format: system path<br>default: /opt/facade/git-trees/</i></td><td>' . get_setting($db,"repo_directory") . edit_setting_button("repo_directory") . '</td></tr>
<tr><td><strong>Log level</strong><br><i>format: Quiet, Info<br>default: Quiet</td><td>' . get_setting($db,"log_level") . edit_setting_button("log_level") . '</td></tr>
</table>

<h2>Status</h2>
<table>
<tr><td class="half"><strong>Current status of facade-worker script</strong></td><td class="half">' . stripslashes(get_setting($db,"utility_status")) . ' since ' . date("F j, Y", $last_modified) . ' at ' . date("H:i", $last_modified) .'</td></tr>
</table>


</div> <!-- .content-block -->';

include_once "includes/footer.php";
close_db($db);
?>