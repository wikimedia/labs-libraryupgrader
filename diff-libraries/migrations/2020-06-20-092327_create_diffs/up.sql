CREATE TABLE diffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    change TEXT NOT NULL,
    -- git ref that was fetched
    git_ref TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    project TEXT NOT NULL,
    txtdiff TEXT
);
