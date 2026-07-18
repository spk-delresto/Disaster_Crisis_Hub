
CREATE DATABASE IF NOT EXISTS disaster_hub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE disaster_hub;

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(80)  NOT NULL UNIQUE,
    email       VARCHAR(120) NOT NULL UNIQUE,
    password    VARCHAR(256) NOT NULL,
    role        ENUM('admin','responder','viewer') NOT NULL DEFAULT 'viewer',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login  DATETIME
);

-- 2. DISASTERS (Crisis Reports)
CREATE TABLE IF NOT EXISTS disasters (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    disaster_type   ENUM('flood','earthquake','fire','hurricane','landslide','tsunami','other') NOT NULL,
    severity        ENUM('low','medium','high','critical') NOT NULL DEFAULT 'medium',
    severity_score  FLOAT,
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

-- 3. EMERGENCY CONTACTS
CREATE TABLE IF NOT EXISTS emergency_contacts (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    name         VARCHAR(100) NOT NULL,
    phone        VARCHAR(20),
    email        VARCHAR(120),
    relation     VARCHAR(50),
    notify_sms   BOOLEAN NOT NULL DEFAULT FALSE,
    notify_email BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. ALERTS LOG
CREATE TABLE IF NOT EXISTS alerts_log (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    disaster_id  INT NOT NULL,
    sent_to      VARCHAR(120) NOT NULL,
    method       ENUM('email','sms') NOT NULL,
    status       ENUM('sent','failed','pending') NOT NULL DEFAULT 'pending',
    sent_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (disaster_id) REFERENCES disasters(id) ON DELETE CASCADE
);

-- 5. AUDIT LOG
CREATE TABLE IF NOT EXISTS audit_log (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT,
    action     VARCHAR(100) NOT NULL,
    detail     TEXT,
    ip_address VARCHAR(45),
    user_agent VARCHAR(300),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 6. CRISIS COMMENTS/UPDATES
CREATE TABLE IF NOT EXISTS crisis_comments (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    disaster_id INT NOT NULL,
    user_id     INT NOT NULL,
    comment     TEXT NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (disaster_id) REFERENCES disasters(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 7. CRISIS CATEGORIES
CREATE TABLE IF NOT EXISTS categories (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    color       VARCHAR(7) DEFAULT '#3b82f6',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS disaster_categories (
    disaster_id INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (disaster_id, category_id),
    FOREIGN KEY (disaster_id) REFERENCES disasters(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- 8. RESOURCE REQUESTS
CREATE TABLE IF NOT EXISTS resource_requests (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    disaster_id INT NOT NULL,
    user_id     INT NOT NULL,
    resource    VARCHAR(200) NOT NULL,
    quantity    INT DEFAULT 1,
    unit        VARCHAR(50),
    priority    ENUM('low','medium','high','critical') DEFAULT 'medium',
    status      ENUM('pending','approved','fulfilled','cancelled') DEFAULT 'pending',
    notes       TEXT,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (disaster_id) REFERENCES disasters(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 9. VOLUNTEER REGISTRATIONS
CREATE TABLE IF NOT EXISTS volunteers (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    disaster_id INT NOT NULL,
    skills      TEXT,
    availability VARCHAR(100),
    status      ENUM('pending','approved','active','completed') DEFAULT 'pending',
    notes       TEXT,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (disaster_id) REFERENCES disasters(id) ON DELETE CASCADE
);

-- 10. ANNOUNCEMENTS
CREATE TABLE IF NOT EXISTS announcements (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    content     TEXT NOT NULL,
    priority    ENUM('normal','urgent','critical') DEFAULT 'normal',
    is_active   BOOLEAN DEFAULT TRUE,
    created_by  INT NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 11. AFFECTED AREAS
CREATE TABLE IF NOT EXISTS affected_areas (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    disaster_id INT NOT NULL,
    area_name   VARCHAR(200) NOT NULL,
    population  INT DEFAULT 0,
    damage_level ENUM('minor','moderate','severe','destroyed') DEFAULT 'moderate',
    notes       TEXT,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (disaster_id) REFERENCES disasters(id) ON DELETE CASCADE
);

-- 12. CRISIS MEDIA
CREATE TABLE IF NOT EXISTS crisis_media (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    disaster_id INT NOT NULL,
    user_id     INT NOT NULL,
    media_type  ENUM('image','video','document','link') NOT NULL,
    url         VARCHAR(500) NOT NULL,
    caption     VARCHAR(300),
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (disaster_id) REFERENCES disasters(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 13. RELIEF SUPPLIES
CREATE TABLE IF NOT EXISTS relief_supplies (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    disaster_id INT NOT NULL,
    item_name   VARCHAR(200) NOT NULL,
    quantity    INT DEFAULT 0,
    unit        VARCHAR(50),
    donated_by  VARCHAR(200),
    status      ENUM('available','distributed','depleted') DEFAULT 'available',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (disaster_id) REFERENCES disasters(id) ON DELETE CASCADE
);

-- 14. EVACUATION ROUTES
CREATE TABLE IF NOT EXISTS evacuation_routes (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    disaster_id  INT NOT NULL,
    route_name   VARCHAR(200) NOT NULL,
    origin       VARCHAR(200) NOT NULL,
    destination  VARCHAR(200) NOT NULL,
    distance_km  FLOAT,
    estimated_time VARCHAR(100),
    status       ENUM('open','congested','closed') DEFAULT 'open',
    notes        TEXT,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (disaster_id) REFERENCES disasters(id) ON DELETE CASCADE
);

-- 15. INCIDENT TIMELINE
CREATE TABLE IF NOT EXISTS incident_timeline (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    disaster_id INT NOT NULL,
    event_time  DATETIME NOT NULL,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    created_by  INT NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (disaster_id) REFERENCES disasters(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 16. FEEDBACK / REPORTS
CREATE TABLE IF NOT EXISTS feedback (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT,
    disaster_id INT,
    subject     VARCHAR(200) NOT NULL,
    message     TEXT NOT NULL,
    category    ENUM('general','inaccurate_info','missing_resource','suggestion','other') DEFAULT 'general',
    status      ENUM('open','reviewed','resolved') DEFAULT 'open',
    admin_reply TEXT,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (disaster_id) REFERENCES disasters(id) ON DELETE SET NULL
);
