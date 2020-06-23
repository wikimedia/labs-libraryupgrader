/*
Copyright (C) 2020 Kunal Mehta <legoktm@member.fsf.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */
use crate::{models, schema, utils};
use diesel::prelude::*;
use gerrit_grr::{fetch_patch_info, DotGitReview};
use git2::Repository;
use std::collections::HashSet;
use std::{fs, env};
use std::process::Command;
use std::thread;

/// Expect that we've already validated `our_change` is just digits
pub fn run(our_change: String) -> Result<models::Diff, String> {
    // FIXME: we're relying on internal detail that cfg.project is ignored
    let fetch = match fetch_patch_info(
        &our_change,
        DotGitReview::new("gerrit.wikimedia.org", "dummy"),
    ) {
        Ok(fetch) => fetch,
        Err(e) => return Err(e.to_string()),
    };
    // TODO: find a better way to get the project name
    let project = fetch
        .url
        .trim_start_matches("https://gerrit.wikimedia.org/r/");
    let conn = establish_connection();
    let diff = match get_diff(&our_change, &conn) {
        // Some other process is already handling this
        Some(diff) => return Ok(diff),
        None => {
            let new_diff = models::NewDiff {
                change: &our_change,
                git_ref: &fetch.git_ref,
                status: "pending",
                project,
                txtdiff: None,
            };
            diesel::insert_into(schema::diffs::table)
                .values(&new_diff)
                .execute(&conn)
                .unwrap();
            get_diff(&our_change, &conn).unwrap()
        }
    };

    thread::spawn(move || {
        internal_run(&our_change, fetch).unwrap();
    });

    Ok(diff)
}

fn run_composer_npm(path: &'static str, changed: &HashSet<String>) {
    let mut threads = vec![];
    if utils::has_composer_changes(changed) {
        threads.push(thread::spawn(move || {
            // Set a consistent autoloader-stuffix to remove unnecessary diff
            Command::new("composer")
                .args(&["config", "autoloader-suffix", "static"])
                .current_dir(path)
                .status()
                .unwrap();
            Command::new("composer")
                .arg("install")
                .current_dir(path)
                .status()
                .unwrap();
        }));
    }
    if utils::has_npm_changes(changed) {
        threads.push(thread::spawn(move || {
            // XXX: Run `npm install` if no package-lock.json?
            Command::new("npm")
                .arg("ci")
                .current_dir(path)
                .status()
                .unwrap();
        }));
    }
    // Wait for all the threads to finish
    for thread in threads {
        thread.join().unwrap();
    }
}

fn internal_run(
    our_change: &str,
    fetch: gerrit_grr::Fetch,
) -> Result<(), String> {
    // FIXME
    let parent = "/src/";
    let repo1 = "/src/repo1";
    let repo2 = "/src/repo2";
    // TODO: can we avoid doing a full clone here?
    let git_repo1 = match Repository::clone(&fetch.url, &repo1) {
        Ok(repo) => repo,
        Err(e) => return Err(e.to_string()),
    };
    git_repo1
        .find_remote("origin")
        .unwrap()
        .fetch(&[&fetch.git_ref], None, None)
        .unwrap();
    let exit = match Command::new("git")
        .args(&["checkout", "FETCH_HEAD"])
        .current_dir(&repo1)
        .status()
    {
        Ok(exit) => exit,
        Err(e) => return Err(e.to_string()),
    };
    if exit.code().unwrap() != 0 {
        return Err(String::from("Failed to checkout FETCH_HEAD"));
    }
    let changed = utils::git_changed_files(git_repo1.workdir().unwrap());
    let composer = utils::has_composer_changes(&changed);
    let npm = utils::has_npm_changes(&changed);
    if !(composer || npm) {
        return Err("No changes needed".to_string());
    }
    // Run composer and npm
    run_composer_npm(&repo1, &changed);
    // Copy over to repo2
    Command::new("cp")
        .args(&["-r", &repo1, &repo2])
        .status()
        .unwrap();
    // Clean repo1
    // TODO: do these options via git2?
    Command::new("git")
        .args(&["clean", "-fdx"])
        .current_dir(&repo1)
        .status()
        .unwrap();
    Command::new("git")
        .args(&["reset", "--hard"])
        .current_dir(&repo1)
        .status()
        .unwrap();
    Command::new("git")
        .args(&["checkout", "HEAD~1"])
        .current_dir(&repo1)
        .status()
        .unwrap();
    run_composer_npm(&repo1, &changed);

    // Diff!
    let output = Command::new("diff")
        .args(&["-ru", "--exclude=.git", &repo1, &repo2])
        .current_dir(&parent)
        .output()
        .unwrap();
    let diff_output = String::from_utf8(output.stdout).unwrap();
    {
        use schema::diffs::dsl::*;
        let conn = establish_connection();
        diesel::update(diffs.filter(change.eq(our_change)))
            .set((status.eq("done"), txtdiff.eq(diff_output)))
            .execute(&conn)
            .unwrap();
        get_diff(our_change, &conn).unwrap()
    };

    // Cleanup
    fs::remove_dir_all(&repo1).unwrap();
    fs::remove_dir_all(&repo2).unwrap();

    Ok(())
}

pub fn establish_connection() -> SqliteConnection {
    let db_url = env::var("DATABASE_URL").unwrap_or_else(|_| "test2.db".to_string());
    SqliteConnection::establish(&db_url).unwrap()
}

pub fn get_diff(
    our_change: &str,
    conn: &SqliteConnection,
) -> Option<models::Diff> {
    use schema::diffs::dsl::*;
    let results = diffs
        .filter(change.eq(our_change))
        .limit(1)
        .load::<models::Diff>(conn)
        .unwrap();
    if results.is_empty() {
        None
    } else {
        Some(results[0].clone())
    }
}

pub fn recent_diffs() -> Vec<models::Diff> {
    use schema::diffs::dsl::*;
    let conn = establish_connection();
    diffs
        .filter(status.eq("done"))
        .limit(5)
        .order(id.desc())
        .load::<models::Diff>(&conn)
        .unwrap()
}
