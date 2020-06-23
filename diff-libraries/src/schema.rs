table! {
    diffs (id) {
        id -> Integer,
        change -> Text,
        git_ref -> Text,
        status -> Text,
        project -> Text,
        txtdiff -> Nullable<Text>,
    }
}
