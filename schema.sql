DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    is_admin TINYINT DEFAULT 0,
    is_banned TINYINT DEFAULT 0,
    avatar_filename VARCHAR(255)
);

CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    date_reported DATE NOT NULL,
    image_filename VARCHAR(255),
    user_id INT NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user_id INT NOT NULL,
    to_user_id INT NOT NULL,
    item_id INT NOT NULL,
    message TEXT NOT NULL,
    is_read TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_user_id) REFERENCES users (id),
    FOREIGN KEY (to_user_id)   REFERENCES users (id),
    FOREIGN KEY (item_id)      REFERENCES items (id)
);
