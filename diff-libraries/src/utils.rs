/*
Copyright (C) 2020 Kunal Mehta <legoktm@debian.org>

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
use regex::Regex;
use std::collections::HashSet;
use std::path::Path;
use std::process::Command;

// TODO: can we do this witout a regex?
pub fn is_valid_gerrit_change(change: &str) -> bool {
    let re_change = Regex::new(r"^\d*?$").unwrap();
    re_change.is_match(change)
}

/// List of changed files in the HEAD commit
pub fn git_changed_files(path: &Path) -> HashSet<String> {
    let cmd = Command::new("git")
        .args(&["log", "--stat", "--oneline", "-n1"])
        .current_dir(path)
        .output()
        .unwrap();
    parse_changed_files(&String::from_utf8(cmd.stdout).unwrap())
}

fn parse_changed_files(output: &str) -> HashSet<String> {
    let split: Vec<&str> = output.trim().split('\n').collect();
    let mut files = HashSet::new();
    for (i, line) in split.iter().enumerate() {
        if i == 0 || (i + 1) == split.len() {
            // Skip
            continue;
        }
        let sp: Vec<&str> = line.split('|').collect();
        files.insert(sp[0].trim().to_string());
    }

    files
}

pub fn has_npm_changes(changes: &HashSet<String>) -> bool {
    changes.contains("package.json") || changes.contains("package-lock.json")
}

pub fn has_composer_changes(changes: &HashSet<String>) -> bool {
    changes.contains("composer.json")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_valid_gerrit_change() {
        assert!(is_valid_gerrit_change("12345"));
        assert!(is_valid_gerrit_change("1"));
        assert!(!is_valid_gerrit_change("abcde"));
        assert!(!is_valid_gerrit_change("12345:1"));
    }

    #[test]
    fn test_parse_changed_files() {
        let actual = parse_changed_files(
            "3f5ea40 (HEAD) build: Updating composer dependencies
 COPYING => LICENSE | 0
 composer.json      | 6 +++---
 2 files changed, 3 insertions(+), 3 deletions(-)
",
        );
        let mut expected = HashSet::with_capacity(2);
        expected.insert("COPYING => LICENSE".to_string());
        expected.insert("composer.json".to_string());
        assert_eq!(expected, actual);
    }
}
