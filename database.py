CREATE DATABASE IF NOT EXISTS disaster_hub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE disaster_hub;

CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(80)  NOT NULL UNIQUE,
    email       VARCHAR(120) NOT NULL UNIQUE,
    password    VARCHAR(256) NOT NULL,          -- bcrypt hash
    role        ENUM('admin','responder','viewer') NOT NULL DEFAULT 'viewer',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login  DATETIME
);

CREATE TABLE IF NOT EXISTS disasters (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    disaster_type   ENUM('flood','earthquake','fire','hurricane','landslide','tsunami','other') NOT NULL,
    severity        ENUM('low','medium','high','critical') NOT NULL DEFAULT 'medium',
    severity_score  FLOAT,                      -- ML predicted 0-1 score
    latitude        DECIMAL(9,6) NOT NULL,
    longitude       DECIMAL(9,6) NOT NULL,
    location_name   VARCHAR(200),
    affected_people INT DEFAULT 0,
    status          ENUM('active','monitoring','resolved') NOT NULL DEFAULT 'active',
    created_by      INT NOT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS emergency_contacts (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    name        VARCHAR(100) NOT NULL,
    phone       VARCHAR(20),
    email       VARCHAR(120),
    relation    VARCHAR(50),
    notify_sms  BOOLEAN NOT NULL DEFAULT FALSE,
    notify_email BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alerts_log (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    disaster_id  INT NOT NULL,
    sent_to      VARCHAR(120) NOT NULL,
    method       ENUM('email','sms') NOT NULL,
    status       ENUM('sent','failed','pending') NOT NULL DEFAULT 'pending',
    sent_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (disaster_id) REFERENCES disasters(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT,
    action      VARCHAR(100) NOT NULL,
    detail      TEXT,
    ip_address  VARCHAR(45),
    user_agent  VARCHAR(300),
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
