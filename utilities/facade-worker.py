#!/usr/bin/python

# Copyright 2016 Brian Warner
#
# This file is part of Facade, and is made available under the terms of the GNU
# General Public License version 2.
#
# SPDX-License-Identifier:        GPL-2.0

# Git repo maintenance
#
# This script is responsible for cloning new repos and keeping existing repos up
# to date. It can be run as often as you want (and will detect when it's
# already running, so as not to spawn parallel processes), but once or twice per
# day should be more than sufficient. Each time it runs, it updates the repo
# and checks for any parents of HEAD that aren't already accounted for in the
# repos. It also rebuilds cache data for display.
#
# If for whatever reason you manually update the affiliations table in the
# database, be sure to run with the -n flag to "nuke" all existing affiliation
# data. It will be rebuilt the next time facade-worker.py runs.

import sys
import MySQLdb
import imp
import time
import datetime

try:
	imp.find_module('db')
	from db import db,cursor
except:
	sys.exit("Can't find db.py. Have you run setup.py?")

import HTMLParser
html = HTMLParser.HTMLParser()

import subprocess
import os
import getopt

import xlsxwriter

global log_level

#### Helpers ####

def get_setting(setting):

# Get a setting from the database

	query = ("SELECT value FROM settings WHERE setting='%s' ORDER BY "
		"last_modified DESC LIMIT 1" % setting)
	cursor.execute(query)
	return cursor.fetchone()["value"]

def update_status(status):

# Update the status displayed in the UI

	query = ("UPDATE settings SET value='%s' WHERE setting='utility_status'"
		% status)
	cursor.execute(query)
	db.commit()

def log_activity(level,status):

# Log an activity based upon urgency and user's preference

	log_options = ('Error','Quiet','Info','Verbose','Debug')

	if log_options.index(level) <= log_options.index(log_level):
		query = ("INSERT INTO utility_log (level,status) VALUES ('%s','%s')"
			% (level,status))
		cursor.execute(query)
		db.commit()
		sys.stderr.write("* %s\n" % status)

def update_repo_log(repos_id,status):

# Log a repo's fetch status

	log_message = ("INSERT INTO repos_fetch_log (repos_id,status) "
		"VALUES (%s,'%s')" % (repos_id,status))

	cursor.execute(log_message)
	db.commit()

def update_analysis_log(repos_id,status):

# Log a repo's analysis status

	log_message = ("INSERT INTO analysis_log (repos_id,status) "
		"VALUES (%s,'%s')" % (repos_id,status))

	cursor.execute(log_message)
	db.commit()

def check_swapped_emails(name,email):

# Sometimes people mix up their name and email in their git settings

	if name.find('@') >=0 and email.find('@') == -1:
		log_activity('Debug','Found swapped email/name: %s/%s' % (email,name))
		return email,name
	else:
		return name,email

def strip_extra_amp(email):

# Some repos have multiple ampersands, which really messes up domain pattern
# matching. This extra info is not used, so we discard it.

	if email.count('@') > 1:
		log_activity('Debug','Found extra @: %s' % email)
		return email[:email.find('@',email.find('@')+1)]
	else:
		return email

def discover_alias(email):

# Match aliases with their canonical email

	fetch_alias = "SELECT canonical FROM aliases WHERE alias='%s'" % email

	cursor.execute(fetch_alias)
	db.commit()

	aliases = list(cursor)

	if aliases:
		for alias in aliases:
			return alias['canonical']
	else:
		return email

def update_affiliation(email_type,email,affiliation,start_date):

	update = ("UPDATE analysis_data "
		"SET %s_affiliation = '%s' "
		"WHERE %s_email = '%s' "
		"AND %s_affiliation IS NULL "
		"AND %s_date >= '%s'" %
		(email_type,affiliation,
		email_type,email,
		email_type,
		email_type,start_date))

	cursor.execute(update)
	db.commit()

def store_working_commit(repo_id,commit):

# Store the working commit.

	store_commit = ("UPDATE repos "
		"SET working_commit = '%s' "
		"WHERE id = %s"
		% (commit,repo_id))

	cursor.execute(store_commit)
	db.commit()

	log_activity('Debug','Stored working commit: %s' % commit)

def trim_commit(repo_id,commit):

# Quickly remove a given commit

	remove_commit = ("DELETE FROM analysis_data "
		"WHERE repos_id=%s AND commit='%s'" %
		(repo_id,commit))

	cursor.execute(remove_commit)
	db.commit()

	log_activity('Debug','Trimmed commit: %s' % commit)

def store_working_author(email):

# Store the working author during affiliation discovery, in case it is
# interrupted and needs to be trimmed.

	store = "UPDATE settings SET value = '%s' WHERE setting = 'working_author'" % email

	cursor.execute(store)
	db.commit()

	log_activity('Debug','Stored working author: %s' % email)

def trim_author(email):

# Remove the affiliations associated with an email. Used when an analysis is
# interrupted during affiliation layering, and the data will be corrupt.

	trim = ("UPDATE analysis_data "
		"SET author_affiliation = NULL "
		"WHERE author_email = '%s'" % email)

	cursor.execute(trim)
	db.commit()

	trim = ("UPDATE analysis_data "
		"SET committer_affiliation = NULL "
		"WHERE committer_email = '%s'" % email)

	cursor.execute(trim)
	db.commit()

	store_working_author('done')

	log_activity('Debug','Trimmed working author: %s' % email)

def discover_null_affiliations(attribution,email):

# Try a bunch of ways to match emails to attributions in the database. First it
# trys to match exactly. If that doesn't work, it tries to match by domain. If
# domain doesn't work, it strips subdomains from the email and tries again.

	# First we see if there's an exact match. This will also catch malformed or
	# intentionally mangled emails (e.g. "developer at domain.com") that have
	# been added as an affiliation rather than an alias.

	match_email = discover_alias(email)

	find_exact_match = ("SELECT affiliation,start_date "
		"FROM affiliations "
		"WHERE domain = '%s' "
		"ORDER BY start_date DESC" % match_email)

	cursor.execute(find_exact_match)
	db.commit

	matches = list(cursor)

	if not matches and match_email.find('@') < 0:

		# It's not a properly formatted email, leave it NULL and log it.

		log_activity('Info','Unmatchable email: %s' % match_email)

		return

	if not matches:

		# Now we go for a domain-level match. Try for an exact match.

		domain = match_email[match_email.find('@')+1:]

		find_exact_domain = ("SELECT affiliation,start_date "
			"FROM affiliations "
			"WHERE domain= '%s' "
			"ORDER BY start_date DESC" % domain)

		cursor.execute(find_exact_domain)
		db.commit()

		matches = list(cursor)

	if not matches:

		# Then try stripping any subdomains.

		find_domain = ("SELECT affiliation,start_date "
			"FROM affiliations "
			"WHERE domain = '%s' "
			"ORDER BY start_date DESC" %
			domain[domain.rfind('.',0,domain.rfind('.',0))+1:])

		cursor.execute(find_domain)
		db.commit()

		matches = list(cursor)

	if not matches:

		# One last check to see if it's an unmatched academic domain.

		if domain[-4:] in '.edu':
			matches.append({'affiliation':'(Academic)','start_date':'1970-01-01'})

	# Done looking. Now we process any matches that were found.

	if matches:

		log_activity('Debug','Found domain match for %s' % email)

		for match in matches:
                        update = ("UPDATE analysis_data "
                                "SET %s_affiliation = %%s "
                                "WHERE %s_email = %%s "
                                "AND %s_affiliation IS NULL "
                                "AND %s_date >= %%s" %
                                (attribution, attribution, attribution, attribution)
			)
                        cursor.execute(update, (match['affiliation'], email, match['start_date']))
                        db.commit()

def analyze_commit(repo_id,repo_loc,commit):

# This function analyzes a given commit, counting the additions, removals, and
# whitespace changes. It collects all of the metadata about the commit, and
# stashes it in the database.

	header = True
	filename = ''
	filename = ''
	added = 0
	removed = 0
	whitespace = 0

	git_log = subprocess.Popen(["git --git-dir %s log -p -M %s -n1 "
		"--pretty=format:'"
		"author_name: %%an%%nauthor_email: %%ae%%nauthor_date:%%ai%%n"
		"committer_name: %%cn%%ncommitter_email: %%ce%%ncommitter_date: %%ci%%n"
		"parents: %%p%%nEndPatch' "
		% (repo_loc,commit)], stdout=subprocess.PIPE, shell=True)

	# Stash the commit we're going to analyze so we can back it out if something
	# goes wrong later.

	log_activity('Debug','Analyzing %s' % commit)

	for line in git_log.stdout.read().split(os.linesep):
		if len(line) > 0:

			if line.find('author_name:') == 0:
				author_name = line[13:].replace("'","\\'")
				continue

			if line.find('author_email:') == 0:
				author_email = line[14:].replace("'","\\'")
				continue

			if line.find('author_date:') == 0:
 				author_date = line[12:22]
				continue

			if line.find('committer_name:') == 0:
				committer_name = line[16:].replace("'","\\'")
				continue

			if line.find('committer_email:') == 0:
				committer_email = line[17:].replace("'","\\'")
				continue

			if line.find('committer_date:') == 0:
				committer_date = line[16:26]
				continue

			if line.find('parents:') == 0:
				if len(line[9:].split(' ')) == 2:

					# We found a merge commit, which won't have a filename
					filename = '(Merge commit)';

					added = 0
					removed = 0
					whitespace = 0
				continue

			if line.find('--- a/') == 0:
				if filename == '(Deleted) ':
					filename = filename + line[6:].replace("'","\\'")
				continue

			if line.find('+++ b/') == 0:
				if not filename.find('(Deleted) ') == 0:
					filename = line[6:].replace("'","\\'")
				continue

			if line.find('rename to ') == 0:
				filename = line[10:].replace("'","\\'")
				continue

			if line.find('deleted file ') == 0:
				filename = '(Deleted) '
				continue

			if line.find('diff --git') == 0:

				# Git only displays the beginning of a file in a patch, not
				# the end. We need some kludgery to discern where one starts
				# and one ends. This is the last line always separating
				# files in commits. But we only want to do it for the second
				# time onward, since the first time we hit this line it'll be
				# right after parsing the header and there won't be any useful
				# information contained in it.

				if not header:
					store_commit(repo_id,commit,filename,
						author_name,author_email,author_date,
						committer_name,committer_email,committer_date,
						added,removed,whitespace)

				header = False

				# Reset stats and prepare for the next section
				whitespaceCheck = []
				resetRemovals = True
				filename = ''
				added = 0
				removed = 0
				whitespace = 0
				continue

			# Count additions and removals and look for whitespace changes
			if not header:
				if line[0] == '+':

					# First check if this is a whitespace change
					if len(line.strip()) == 1:
						# Line with zero length
						whitespace += 1

					else:
						# Compare against removals, detect whitespace changes
						whitespaceChange = False

						for check in whitespaceCheck:

							# Mark matches of non-trivial length
							if line[1:].strip() == check and len(line[1:].strip()) > 8:
								whitespaceChange = True

						if whitespaceChange:
							# One removal was whitespace, back it out
							removed -= 1
							whitespace += 1
							# Remove the matched line
							whitespaceCheck.remove(check)

						else:
							# Did not trigger whitespace criteria
							added += 1

					# Once we hit an addition, next removal line will be new.
					# At that point, start a new collection for checking.
					resetRemovals = True

				if line[0] == '-':
					removed += 1
					if resetRemovals:
						whitespaceCheck = []
						resetRemovals = False
					# Store the line to check next add lines for a match
					whitespaceCheck.append(line[1:].strip())

	# Store the last stats from the git log
	store_commit(repo_id,commit,filename,
		author_name,author_email,author_date,
		committer_name,committer_email,committer_date,
		added,removed,whitespace)

def store_commit(repos_id,commit,filename,
	author_name,author_email,author_date,
	committer_name,committer_email,committer_date,
	added,removed, whitespace):

# Fix some common issues in git commit logs and store data

	# Sometimes git is misconfigured and name/email get swapped
	author_name, author_email = check_swapped_emails(author_name,author_email)
	committer_name,committer_email = check_swapped_emails(committer_name,committer_email)

	# Some systems append extra info after a second @
	author_email = strip_extra_amp(author_email)
	committer_email = strip_extra_amp(committer_email)

	store = ("INSERT INTO analysis_data (repos_id,commit,filename,"
		"author_name,author_email,author_date,"
		"committer_name,committer_email,committer_date,"
		"added,removed,whitespace) VALUES ("
		"%s,'%s','%s','%s','%s','%s','%s','%s','%s',%s,%s,%s)"
		% (repos_id,commit,filename,
		author_name,author_email,author_date,
		committer_name,committer_email,committer_date,
		added,removed,whitespace))

	cursor.execute(store)
	db.commit()

	log_activity('Debug','Stored commit: %s' % commit)

#### Facade main functions ####

def git_repo_cleanup():

# Clean up any git repos that are pending deletion

	update_status('Purging deleted repos')
	log_activity('Info','Processing deletions')

	repo_base_directory = get_setting('repo_directory')

	query = "SELECT id,projects_id,path,name FROM repos WHERE status='Delete'"
	cursor.execute(query)

	delete_repos = list(cursor)

	for row in delete_repos:

		cmd = ("rm -rf %s%s/%s%s"
			% (repo_base_directory,row['projects_id'],row['path'],row['name']))

		return_code = subprocess.Popen([cmd],shell=True).wait()

		query = "DELETE FROM repos WHERE id=%s" % row['id']
		cursor.execute(query)
		db.commit()

		log_activity('Verbose','Deleted repo %s' % row['id'])

		cleanup = '%s/%s%s' % (row['projects_id'],row['path'],row['name'])

		# Remove the repo from the logs

		remove_logs = ("DELETE FROM repos_fetch_log WHERE repos_id = %s" %
			row['id'])

		cursor.execute(remove_logs)
		db.commit()

		# Attempt to cleanup any empty parent directories
		while (cleanup.find('/',0) > 0):
			cleanup = cleanup[:cleanup.rfind('/',0)]

			cmd = "rmdir %s%s" % (repo_base_directory,cleanup)
			subprocess.Popen([cmd],shell=True).wait()
			log_activity('Verbose','Attempted %s' % cmd)

		update_repo_log(row['id'],'Deleted')

	log_activity('Info','Processing deletions (complete)')

def git_repo_updates():

# Update existing repos

	update_status('Updating repos')
	log_activity('Info','Updating existing repos')

	repo_base_directory = get_setting('repo_directory')

	query = ("SELECT id,projects_id,git,name,path FROM repos WHERE "
		"status='Active'");
	cursor.execute(query)

	existing_repos = list(cursor)

	for row in existing_repos:

		log_activity('Verbose','Attempting to update %s' % row['git'])
		update_repo_log(row['id'],'Updating')

		cmd = ("git -C %s%s/%s%s pull"
			% (repo_base_directory,row['projects_id'],row['path'],row['name']))

		return_code = subprocess.Popen([cmd],shell=True).wait()

		if return_code == 0:
			update_repo_log(row['id'],'Up-to-date')
			log_activity('Verbose','Updated %s' % row["git"])
		else:
			update_repo_log(row['id'],'Failed (%s)' % return_code)
			log_activity('Error','Could not update %s' % row["git"])

	log_activity('Info','Updating existing repos (complete)')

def git_repo_initialize():

# Select any new git repos so we can set up their locations and git clone

	update_status('Fetching new repos')
	log_activity('Info','Fetching new repos')

	query = "SELECT id,projects_id,git FROM repos WHERE status LIKE 'New%'";
	cursor.execute(query)

	new_repos = list(cursor)

	for row in new_repos:
		print row["git"]
		update_repo_log(row['id'],'Cloning')

		git = html.unescape(row["git"])

		# Strip protocol from remote URL, set a unique path on the filesystem
		if git.find('://',0) > 0:
			repo_relative_path = git[git.find('://',0)+3:][:git[git.find('://',0)+3:].rfind('/',0)+1]
		else:
			repo_relative_path = git[:git.rfind('/',0)+1]

		# Get the full path to the directory where we'll clone the repo
		repo_path = ('%s%s/%s' %
			(repo_base_directory,row["projects_id"],repo_relative_path))

		# Get the name of repo
		repo_name = git[git.rfind('/',0)+1:]
		if repo_name.find('.git',0) > -1:
			repo_name = repo_name[:repo_name.find('.git',0)]

		# Check if there will be a storage path collision
		query = ("SELECT NULL FROM repos WHERE CONCAT(projects_id,'/',path,name) "
			"='%s/%s%s'" % (row["projects_id"],repo_relative_path,repo_name))
		cursor.execute(query)
		db.commit()

		# If there is a collision, append a slug to repo_name to yield a unique path
		if cursor.rowcount:

			slug = 1
			is_collision = True
			while is_collision:

				if os.path.isdir('%s%s-%s' % (repo_path,repo_name,slug)):
					slug += 1
				else:
					is_collision = False

			repo_name = '%s-%s' % (repo_name,slug)

			log_activity('Verbose','Identical repo detected, storing %s in %s' %
				(git,repo_name))

		# Create the prerequisite directories
		return_code = subprocess.Popen(['mkdir -p %s' %repo_path],shell=True).wait()

		# Make sure it's ok to proceed
		if return_code != 0:
			print("COULD NOT CREATE REPO DIRECTORY")

			update_repo_log(row['id'],'Failed (mkdir)')
			update_status('Failed (mkdir %s)' % repo_path)
			log_activity('Error','Could not create repo directory: %s' %
				repo_path)

			sys.exit("Could not create git repo's prerequisite directories. "
				" Do you have write access?")

		update_repo_log(row['id'],'New (cloning)')

		query = ("UPDATE repos SET status='New (Initializing)', path='%s', "
			"name='%s' WHERE id=%s"	% (repo_relative_path,repo_name,row["id"]))

		cursor.execute(query)
		db.commit()

		log_activity('Verbose','Cloning: %s' % git)

		cmd = "git -C %s clone '%s' %s" % (repo_path,git,repo_name)
		return_code = subprocess.Popen([cmd], shell=True).wait()

		if (return_code == 0):
			# If cloning succeeded, repo is ready for analysis
			query = ("UPDATE repos SET status='Active',path='%s', name='%s' "
				"WHERE id=%s" % (repo_relative_path,repo_name,row["id"]))

			cursor.execute(query)
			db.commit()

			update_repo_log(row['id'],'Up-to-date')
			log_activity('Info','Cloned %s' % git)

		else:
			# If cloning failed, log it and set the status back to new
			update_repo_log(row['id'],'Failed (%s)' % return_code)

			query = ("UPDATE repos SET status='New (failed)' WHERE id=%s"
				% row["id"])

			cursor.execute(query)
			db.commit()

			log_activity('Error','Could not clone %s' % git)

	log_activity('Info', 'Fetching new repos (complete)')

def analysis():

# Run the analysis by looping over all active repos. For each repo, we retrieve
# the list of commits which lead to HEAD. If any are missing from the database,
# they are filled in. Then we check to see if any commits in the database are
# not in the list of parents, and prune them out.
#
# We also keep track of the last commit to be processed, so that if the analysis
# is interrupted (possibly leading to partial data in the database for the
# commit being analyzed at the time) we can recover.

	update_status('Running analysis')
	log_activity('Info','Beginning analysis')

	start_date = get_setting('start_date')

	repo_list = "SELECT id,projects_id,path,name FROM repos WHERE status='Active'"
	cursor.execute(repo_list)
	repos = list(cursor)

	for repo in repos:

		update_analysis_log(repo['id'],'Beginning analysis')
		log_activity('Verbose','Analyzing repo: %s (%s)' % (repo['id'],repo['name']))

		# First we check to see if the previous analysis didn't complete

		get_status = ("SELECT working_commit FROM repos WHERE id=%s" %
			repo['id'])

		cursor.execute(get_status)
		working_commit = cursor.fetchone()['working_commit']

		# If there's a commit still there, the previous run was interrupted and
		# the commit data may be incomplete. It should be trimmed, just in case.
		if working_commit:
			trim_commit(repo['id'],working_commit)
			store_working_commit(repo['id'],'')

		# Start the main analysis

		update_analysis_log(repo['id'],'Collecting data')

		repo_loc = ('%s%s/%s%s/.git' % (repo_base_directory,
			repo["projects_id"], repo["path"],
			repo["name"]))
		# Grab the parents of HEAD

		parents = subprocess.Popen(["git --git-dir %s log --ignore-missing "
			"--pretty=format:'%%H' --since=%s" % (repo_loc,start_date)],
			stdout=subprocess.PIPE, shell=True)

		parent_commits = set(parents.stdout.read().split(os.linesep))

		# If there are no commits in the range, we still get a blank entry in
		# the set. Remove it, as it messes with the calculations

		if '' in parent_commits:
			parent_commits.remove('')

		# Grab the existing commits from the database

		existing_commits = set()

		find_existing = ("SELECT DISTINCT commit FROM analysis_data WHERE repos_id=%s" %
			repo['id'])

		cursor.execute(find_existing)

		for commit in list(cursor):
			existing_commits.add(commit['commit'])

		# Find missing commits and add them

		missing_commits = parent_commits - existing_commits

		log_activity('Debug','Commits missing from repo %s: %s' %
			(repo['id'],len(missing_commits)))

		for commit in missing_commits:

			store_working_commit(repo['id'],commit)

			analyze_commit(repo['id'],repo_loc,commit)

			store_working_commit(repo['id'],'')

		update_analysis_log(repo['id'],'Data collection complete')

		update_analysis_log(repo['id'],'Beginning to trim commits')

		# Find commits which are out of the analysis range

		trimmed_commits = existing_commits - parent_commits

		log_activity('Debug','Commits to be trimmed from repo %s: %s' %
			(repo['id'],trimmed_commits))

		for commit in trimmed_commits:

			trim_commit(repo['id'],commit)

		update_analysis_log(repo['id'],'Commit trimming complete')

		update_analysis_log(repo['id'],'Analysis complete')

	log_activity('Info','Running analysis (complete)')

def nuke_affiliations():

# Delete all stored affiliations in the database. Normally when you
# add/remove/change affiliation data via the web UI, any potentially affected
# records will be deleted and then rebuilt on the next run. However, if you
# manually add affiliation records via the database or import them by some other
# means, there's no elegant way to discover which affiliations are affected. So
# this is the scorched earth way: remove them all to force a total rebuild.
# Brutal but effective.

	log_activity('Info','Nuking affiliations')

	nuke = ("UPDATE analysis_data SET author_affiliation = NULL, "
			"committer_affiliation = NULL")

	cursor.execute(nuke)
	db.commit()

	log_activity('Info','Nuking affiliations (complete)')

def fill_empty_affiliations():

# When a record is added, it has no affiliation data. Also, when an affiliation
# mapping is changed via the UI, affiliation data will be set to NULL. This
# function finds any records with NULL affiliation data and fills them.

	update_status('Filling empty affiliations')
	log_activity('Info','Filling empty affiliations')

	working_author = get_setting('working_author').replace("'","\\'")

	if working_author != 'done':
		log_activity('Error','Trimming author data in affiliations: %s' %
			working_author)
		trim_author(working_author)

	# Find any authors with NULL affiliations and fill them

	find_null_authors = ("SELECT DISTINCT author_email AS email, "
		"MIN(author_date) AS earliest "
		"FROM analysis_data "
		"WHERE author_affiliation IS NULL "
		"GROUP BY author_email")

	cursor.execute(find_null_authors)

	null_authors = list(cursor)

	log_activity('Debug','Found %s authors with NULL affiliation' %
		len(null_authors))

	for null_author in null_authors:

		email = null_author['email'].replace("'","\\'")

		store_working_author(email)

		discover_null_affiliations('author',email)

	store_working_author('done')

	# Find any committers with NULL affiliations and fill them

	find_null_committers = ("SELECT DISTINCT committer_email AS email, "
		"MIN(committer_date) AS earliest "
		"FROM analysis_data "
		"WHERE committer_affiliation IS NULL "
		"GROUP BY committer_email")

	cursor.execute(find_null_committers)

	null_committers = list(cursor)

	log_activity('Debug','Found %s committers with NULL affiliation' %
		len(null_committers))

	for null_committer in null_committers:

		email = null_committer['email'].replace("'","\\'")

		store_working_author(email)

		discover_null_affiliations('committer',email)

	# Now that we've matched as much as possible, fill the rest as (Unknown)

	fill_unknown_author = ("UPDATE analysis_data "
		"SET author_affiliation = '(Unknown)' "
		"WHERE author_affiliation IS NULL")

	cursor.execute(fill_unknown_author)
	db.commit()

	fill_unknown_committer = ("UPDATE analysis_data "
		"SET committer_affiliation = '(Unknown)' "
		"WHERE committer_affiliation IS NULL")

	cursor.execute(fill_unknown_committer)
	db.commit()

	store_working_author('done')

	log_activity('Info','Filling empty affiliations (complete)')

def clear_cached_tables():

	update_status('Deleting cached data')
	log_activity('Info','Deleting old cached unknown affiliations and web data')

	# Create a temporary table for each cache, so we can swap in place.

	query = "CREATE TABLE IF NOT EXISTS uc LIKE unknown_cache"

	cursor.execute(query)
	db.commit()

	query = "CREATE TABLE IF NOT EXISTS pmc LIKE project_monthly_cache";

	cursor.execute(query)
	db.commit()

	query = "CREATE TABLE IF NOT EXISTS pac LIKE project_annual_cache";

	cursor.execute(query)
	db.commit()

	query = "CREATE TABLE IF NOT EXISTS rmc LIKE repo_monthly_cache";

	cursor.execute(query)
	db.commit()

	query = "CREATE TABLE IF NOT EXISTS rac LIKE repo_annual_cache";

	cursor.execute(query)
	db.commit()

	# Swap in place, just in case someone's using the web UI at this moment.

	query = ("RENAME TABLE unknown_cache TO uc_old, "
		"uc TO unknown_cache, "
		"project_monthly_cache TO pmc_old, "
		"pmc TO project_monthly_cache, "
		"project_annual_cache TO pac_old, "
		"pac TO project_annual_cache, "
		"repo_monthly_cache TO rmc_old, "
		"rmc TO repo_monthly_cache, "
		"repo_annual_cache TO rac_old, "
		"rac TO repo_annual_cache")

	cursor.execute(query)
	db.commit()

	# Get rid of the old tables.

	query = ("DROP TABLE uc_old, "
		"pmc_old, "
		"pac_old, "
		"rmc_old, "
		"rac_old")

	cursor.execute(query)
	db.commit()

	log_activity('Info','Deleting old cached unknown affiliations and web data (complete)')

def rebuild_unknown_affiliation_and_web_caches():

# When there's a lot of analysis data, calculating display data on the fly gets
# pretty expensive. Instead, we crunch the data based upon the user's preferred
# statistics (author or committer) and store them. We also store all records
# with an (Unknown) affiliation for display to the user.

	update_status('Caching data for display')
	log_activity('Info','Caching unknown affiliations and web data for display')

	report_date = get_setting('report_date')
	report_attribution = get_setting('report_attribution')

	# Clear the cache tables

	clear_cached_tables()

	log_activity('Verbose','Caching unknown authors and committers')

	# Cache the unknown authors

	unknown_authors = ("INSERT INTO unknown_cache "
		"SELECT 'author', "
		"r.projects_id, "
		"a.author_email, "
		"SUBSTRING_INDEX(a.author_email,'@',-1), "
		"SUM(a.added) "
		"FROM analysis_data a "
		"JOIN repos r ON r.id = a.repos_id "
		"WHERE a.author_affiliation = '(Unknown)' "
		"GROUP BY r.projects_id,a.author_email")

	cursor.execute(unknown_authors)
	db.commit()

	# Cache the unknown committers

	unknown_committers = ("INSERT INTO unknown_cache "
		"SELECT 'committer', "
		"r.projects_id, "
		"a.committer_email, "
		"SUBSTRING_INDEX(a.committer_email,'@',-1), "
		"SUM(a.added) "
		"FROM analysis_data a "
		"JOIN repos r ON r.id = a.repos_id "
		"WHERE a.committer_affiliation = '(Unknown)' "
		"GROUP BY r.projects_id,a.committer_email")

	cursor.execute(unknown_committers)
	db.commit()

	# Start caching by project

	log_activity('Verbose','Caching projects')

	cache_projects_by_month = ("INSERT INTO project_monthly_cache "
		"SELECT r.projects_id AS projects_id, "
		"a.%s_email AS email, "
		"a.%s_affiliation AS affiliation, "
		"MONTH(a.%s_date) AS month, "
		"YEAR(a.%s_date) AS year, "
		"SUM(a.added) AS added, "
		"SUM(a.removed) AS removed, "
		"SUM(a.whitespace) AS whitespace, "
		"COUNT(DISTINCT a.filename) AS files, "
		"COUNT(DISTINCT a.commit) AS patches "
		"FROM analysis_data a "
		"JOIN repos r ON r.id = a.repos_id "
		"LEFT JOIN exclude e ON "
			"(a.author_email = e.email "
				"AND (e.projects_id = r.projects_id "
					"OR e.projects_id = 0)) "
			"OR (a.author_email LIKE CONCAT('%%',e.domain) "
				"AND (e.projects_id = r.projects_id "
				"OR e.projects_id = 0)) "
		"WHERE e.email IS NULL "
		"AND e.domain IS NULL "
		"GROUP BY month, "
		"year, "
		"affiliation, "
		"a.%s_email,"
		"projects_id"
		% (report_attribution,report_attribution,
		report_date,report_date,report_attribution))

	cursor.execute(cache_projects_by_month)
	db.commit()

	cache_projects_by_year = ("INSERT INTO project_annual_cache "
		"SELECT r.projects_id AS projects_id, "
		"a.%s_email AS email, "
		"a.%s_affiliation AS affiliation, "
		"YEAR(a.%s_date) AS year, "
		"SUM(a.added) AS added, "
		"SUM(a.removed) AS removed, "
		"SUM(a.whitespace) AS whitespace, "
		"COUNT(DISTINCT a.filename) AS files, "
		"COUNT(DISTINCT a.commit) AS patches "
		"FROM analysis_data a "
		"JOIN repos r ON r.id = a.repos_id "
		"LEFT JOIN exclude e ON "
			"(a.author_email = e.email "
				"AND (e.projects_id = r.projects_id "
					"OR e.projects_id = 0)) "
			"OR (a.author_email LIKE CONCAT('%%',e.domain) "
				"AND (e.projects_id = r.projects_id "
				"OR e.projects_id = 0)) "
		"WHERE e.email IS NULL "
		"AND e.domain IS NULL "
		"GROUP BY year, "
		"affiliation, "
		"a.%s_email,"
		"projects_id"
		% (report_attribution,report_attribution,
		report_date,report_attribution))

	cursor.execute(cache_projects_by_year)
	db.commit()

	# Start caching by repo

	log_activity('Verbose','Caching repos')

	cache_repos_by_month = ("INSERT INTO repo_monthly_cache "
		"SELECT a.repos_id AS repos_id, "
		"a.%s_email AS email, "
		"a.%s_affiliation AS affiliation, "
		"MONTH(a.%s_date) AS month, "
		"YEAR(a.%s_date) AS year, "
		"SUM(a.added) AS added, "
		"SUM(a.removed) AS removed, "
		"SUM(a.whitespace) AS whitespace, "
		"COUNT(DISTINCT a.filename) AS files, "
		"COUNT(DISTINCT a.commit) AS patches "
		"FROM analysis_data a "
		"JOIN repos r ON r.id = a.repos_id "
		"LEFT JOIN exclude e ON "
			"(a.author_email = e.email "
				"AND (e.projects_id = r.projects_id "
					"OR e.projects_id = 0)) "
			"OR (a.author_email LIKE CONCAT('%%',e.domain) "
				"AND (e.projects_id = r.projects_id "
				"OR e.projects_id = 0)) "
		"WHERE e.email IS NULL "
		"AND e.domain IS NULL "
		"GROUP BY month, "
		"year, "
		"affiliation, "
		"a.%s_email,"
		"repos_id"
		% (report_attribution,report_attribution,
		report_date,report_date,report_attribution))

	cursor.execute(cache_repos_by_month)
	db.commit()

	cache_repos_by_year = ("INSERT INTO repo_annual_cache "
		"SELECT a.repos_id AS repos_id, "
		"a.%s_email AS email, "
		"a.%s_affiliation AS affiliation, "
		"YEAR(a.%s_date) AS year, "
		"SUM(a.added) AS added, "
		"SUM(a.removed) AS removed, "
		"SUM(a.whitespace) AS whitespace, "
		"COUNT(DISTINCT a.filename) AS files, "
		"COUNT(DISTINCT a.commit) AS patches "
		"FROM analysis_data a "
		"JOIN repos r ON r.id = a.repos_id "
		"LEFT JOIN exclude e ON "
			"(a.author_email = e.email "
				"AND (e.projects_id = r.projects_id "
					"OR e.projects_id = 0)) "
			"OR (a.author_email LIKE CONCAT('%%',e.domain) "
				"AND (e.projects_id = r.projects_id "
				"OR e.projects_id = 0)) "
		"WHERE e.email IS NULL "
		"AND e.domain IS NULL "
		"GROUP BY year, "
		"affiliation, "
		"a.%s_email,"
		"repos_id"
		% (report_attribution,report_attribution,
		report_date,report_attribution))

	cursor.execute(cache_repos_by_year)
	db.commit()

	log_activity('Info','Caching unknown affiliations and web data for display (complete)')

### The real program starts here ###

# Figure out how much we're going to log
log_level = get_setting('log_level')

# Figure out what we need to do
limited_run = 0
delete_marked_repos = 0
pull_repos = 0
clone_repos = 0
run_analysis = 0
nuke_stored_affiliations = 0
fix_affiliations = 0 #
invalidate_caches = 0
rebuild_caches = 0
create_xlsx_summary_files = 0

opts,args = getopt.getopt(sys.argv[1:],'hdpcanfrx')
for opt in opts:
	if opt[0] == '-h':
		print("\nfacade-worker.py does everything except invalidating caches by\n"
				"default, unless invoked with one of these options. In that case,\n"
				"it will only do what you have selected.\n\n"
				"Options:\n"
				"	-d	Delete marked repos\n"
				"	-p	Run 'git pull' on repos\n"
				"	-c	Run 'git clone' on new repos\n"
				"	-a	Analyze git repos\n"
				"	-n	Nuke stored affiliations (if mappings modified by hand)\n"
				"	-f	Fill empty affiliations\n"
				"	-r	Rebuild unknown affiliation and web caches\n"
				"	-x	Create Excel summary files\n\n")
		sys.exit(0)

	elif opt[0] == '-d':
		delete_marked_repos = 1
		limited_run = 1
		log_activity('Info','Option set: delete marked repos.')

	elif opt[0] == '-p':
		pull_repos = 1
		limited_run = 1
		log_activity('Info','Option set: update repos.')

	elif opt[0] == '-c':
		clone_repos = 1
		limited_run = 1
		log_activity('Info','Option set: clone new repos.')

	elif opt[0] == '-a':
		run_analysis = 1
		limited_run = 1
		log_activity('Info','Option set: running analysis.')

	elif opt[0] == '-n':
		nuke_stored_affiliations = 1
		limited_run = 1
		log_activity('Info','Option set: nuking all affiliations')

	elif opt[0] == '-f':
		fix_affiliations = 1
		limited_run = 1
		log_activity('Info','Option set: fixing affiliations.')

	elif opt[0] == '-r':
		rebuild_caches = 1
		limited_run = 1
		log_activity('Info','Option set: rebuilding caches.')

	elif opt[0] == '-x':
		create_xlsx_summary_files = 1
		limited_run = 1
		log_activity('Info','Option set: creating Excel summary files.')

# Get the location of the directory where git repos are stored
repo_base_directory = get_setting('repo_directory')

# Determine if it's safe to start the script
current_status = get_setting('utility_status')

if current_status != 'Idle':
	log_activity('Error','Something is already running, aborting maintenance '
		'and analysis.\nIt is unsafe to continue.')
	sys.exit(1)

if len(repo_base_directory) == 0:
	log_activity('Error','No base directory. It is unsafe to continue.')
	update_status('Failed: No base directory')
	sys.exit(1)

# Begin working

start_time = time.time()
log_activity('Quiet','Running facade-worker.py')

if not limited_run or (limited_run and delete_marked_repos):
	git_repo_cleanup()

if not limited_run or (limited_run and pull_repos):
	git_repo_updates()

if not limited_run or (limited_run and clone_repos):
	git_repo_initialize()

if not limited_run or (limited_run and run_analysis):
	analysis()

if nuke_stored_affiliations:
	nuke_affiliations()

if not limited_run or (limited_run and fix_affiliations):
	fill_empty_affiliations()

if not limited_run or (limited_run and rebuild_caches):
	rebuild_unknown_affiliation_and_web_caches()

if not limited_run or (limited_run and create_xlsx_summary_files):

	log_activity('Info','Creating summary Excel files')

	from excel_generators import *

	log_activity('Info','Creating summary Excel files (complete)')

# All done

update_status('Idle')
log_activity('Quiet','facade-worker.py completed')

elapsed_time = time.time() - start_time

print '\nCompleted in %s\n' % datetime.timedelta(seconds=int(elapsed_time))

cursor.close()
db.close()
