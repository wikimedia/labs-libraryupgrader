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
use crate::{backend, models, utils};
use rocket::request::Form;
use rocket::response::Redirect;
use rocket_contrib::templates::Template;
use serde::Serialize;

#[derive(Serialize)]
struct IndexTemplate {
    error: Option<String>,
    recent: Vec<models::Diff>,
}

#[get("/")]
fn index() -> Template {
    Template::render(
        "index",
        IndexTemplate {
            error: None,
            recent: backend::recent_diffs(),
        },
    )
}

#[derive(FromForm)]
struct IndexForm {
    change: String,
}

#[post("/", data = "<form>")]
fn handle_post(form: Form<IndexForm>) -> Result<Redirect, Template> {
    let change = &form.change;
    dbg!(change);
    if !utils::is_valid_gerrit_change(change) {
        return Err(Template::render(
            "index",
            IndexTemplate {
                error: Some("Invalid Gerrit change specified".to_string()),
                recent: backend::recent_diffs(),
            },
        ));
    }
    // TODO: queue it
    backend::run(change.clone()).unwrap();
    Ok(Redirect::to(uri!(handle_change: change)))
}

#[derive(Serialize)]
struct DiffTemplate {
    change: String,
    project: String,
    status: String,
    txtdiff: Option<String>,
}

/// Add colors to the diff, returns safe HTML
fn prettify_diff(original: &str) -> String {
    // First, escape the HTML
    let escaped = tera::escape_html(original);
    let split: Vec<&str> = escaped.split('\n').collect();
    let mut pretty = vec![];
    for line in split {
        // Colors from <https://design.wikimedia.org/style-guide/visual-style_colors.html>
        if line.starts_with('+') {
            pretty.push(format!(
                "<span style=\"color: #14866d;\">{}</span>",
                line
            ));
        } else if line.starts_with('-') {
            pretty.push(format!(
                "<span style=\"color: #d33;\">{}</span>",
                line
            ));
        } else {
            pretty.push(line.to_string());
        }
    }

    pretty.join("\n")
}

#[get("/change/<change>")]
fn handle_change(change: String) -> Template {
    if !utils::is_valid_gerrit_change(&change) {
        return Template::render(
            "index",
            IndexTemplate {
                error: Some("Invalid Gerrit change specified".to_string()),
                recent: backend::recent_diffs(),
            },
        );
    }
    let conn = backend::establish_connection();
    match backend::get_diff(&change, &conn) {
        Some(diff) => Template::render(
            "diff",
            DiffTemplate {
                change: diff.change,
                project: diff.project,
                status: diff.status,
                txtdiff: match diff.txtdiff {
                    Some(original) => Some(prettify_diff(&original)),
                    None => None,
                },
            },
        ),
        None => Template::render(
            "index",
            IndexTemplate {
                error: Some(
                    "I don't know about that change yet. Try submitting it?"
                        .to_string(),
                ),
                recent: backend::recent_diffs(),
            },
        ),
    }
}

rocket_healthz::healthz!();

pub fn rocket() -> rocket::Rocket {
    rocket::ignite()
        .attach(Template::fairing())
        .mount("/", routes![index, handle_post, handle_change, rocket_healthz])
}
