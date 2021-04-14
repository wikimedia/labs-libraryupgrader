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
use super::schema::diffs;
use serde::Serialize;

#[derive(Queryable, Clone, Debug, Serialize)]
pub struct Diff {
    pub id: i32,
    pub change: String,
    pub git_ref: String,
    pub status: String,
    pub project: String,
    pub txtdiff: Option<String>,
}

#[derive(Insertable)]
#[table_name = "diffs"]
pub struct NewDiff<'a> {
    pub change: &'a str,
    pub git_ref: &'a str,
    pub status: &'a str,
    pub project: &'a str,
    pub txtdiff: Option<&'a str>,
}
