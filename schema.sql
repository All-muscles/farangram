DROP TABLE IF EXISTS users;
CREATE TABLE users   (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password      TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    avatar        TEXT DEFAULT 'default_avatar.jpg',
    creation_date DATETIME NOT NULL
);

DROP TABLE IF EXISTS uploads;
CREATE TABLE uploads (
    upload_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    caption       TEXT NOT NULL,
    picture       TEXT NOT NULL UNIQUE,
    uploader_id   INTEGER NOT NULL,
    creation_date DATETIME NOT NULL,
    FOREIGN KEY (uploader_id) REFERENCES users(user_id) ON DELETE CASCADE
);

DROP TABLE IF EXISTS follows;
CREATE TABLE follows (
    follow_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    follower_id   INTEGER NOT NULL,
    following_id  INTEGER NOT NULL,
    FOREIGN KEY (follower_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (following_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT no_self_following CHECK (follower_id != following_id),
    CONSTRAINT unique_rows UNIQUE (follower_id, following_id)
);

CREATE INDEX idx_uploads_uploader_id ON uploads (uploader_id);
CREATE INDEX idx_follows_follower_id ON follows (follower_id);
CREATE INDEX idx_follows_following_id ON follows (following_id);