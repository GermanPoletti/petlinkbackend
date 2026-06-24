-- =============================================================================
--  PETLINK — Unified Database Schema
--  MySQL 8.0+
--
--  Execution order respects foreign key dependencies:
--    1. Lookup tables (no FK deps)
--    2. users + profiles + auth tokens
--    3. posts + post children
--    4. chats + messages + agreements
--    5. notifications
-- =============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- =============================================================================
--  SECTION 1 — LOOKUP / REFERENCE TABLES
-- =============================================================================

CREATE TABLE IF NOT EXISTS roles (
    id   INT         NOT NULL,
    name VARCHAR(50) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_roles_name (name)
);

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS status_users (
    id   INT         NOT NULL,
    name VARCHAR(50) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_status_users_name (name)
);

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS status_agreements (
    id   INT         NOT NULL,
    name VARCHAR(50) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_status_agreements_name (name)
);

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS post_types (
    id         INT         NOT NULL,
    name       VARCHAR(50) NOT NULL,
    created_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME             DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_post_types_name (name)
);

-- =============================================================================
--  SECTION 2 — USERS, PROFILES & AUTH TOKENS
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id             INT          NOT NULL AUTO_INCREMENT,
    email          VARCHAR(255) NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    role_id        INT          NOT NULL DEFAULT 1,
    status_id      INT          NOT NULL DEFAULT 1,
    help_count     INT          NOT NULL DEFAULT 0,
    email_verified BOOLEAN      NOT NULL DEFAULT TRUE,
    warnings       INT          NOT NULL DEFAULT 0,
    banned_until   DATETIME              DEFAULT NULL,
    deleted_at     DATETIME              DEFAULT NULL,
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME              DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email  (email),
    INDEX idx_users_email      (email),
    INDEX idx_users_deleted    (deleted_at),
    CONSTRAINT fk_users_role   FOREIGN KEY (role_id)   REFERENCES roles(id)       ON DELETE RESTRICT,
    CONSTRAINT fk_users_status FOREIGN KEY (status_id) REFERENCES status_users(id) ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id    INT         NOT NULL,
    username   VARCHAR(50)          DEFAULT NULL,
    first_name VARCHAR(50)          DEFAULT NULL,
    last_name  VARCHAR(50)          DEFAULT NULL,
    photo_url  TEXT                 DEFAULT NULL,
    PRIMARY KEY (user_id),
    UNIQUE KEY  uq_user_profiles_username (username),
    INDEX       idx_user_profiles_username (username),
    CONSTRAINT  fk_user_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- One row per user: the JWT currently active.
-- Enforces single-session policy at the DB level.
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS active_tokens (
    user_id    INT         NOT NULL,
    jti        VARCHAR(36) NOT NULL,
    expires_at DATETIME    NOT NULL,
    created_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME             DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY  uq_active_tokens_jti (jti),
    INDEX       idx_active_tokens_jti     (jti),
    INDEX       idx_active_tokens_expires (expires_at),
    CONSTRAINT  fk_active_tokens_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tokens_blacklist (
    id         INT         NOT NULL AUTO_INCREMENT,
    jti        VARCHAR(36) NOT NULL,
    user_id    INT         NOT NULL,
    expires_at DATETIME    NOT NULL,
    created_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME             DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY  uq_tokens_blacklist_jti (jti),
    INDEX       idx_tokens_blacklist_jti (jti),
    INDEX       idx_expires_jti          (expires_at, jti),
    CONSTRAINT  fk_tokens_blacklist_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id         INT         NOT NULL AUTO_INCREMENT,
    user_id    INT         NOT NULL,
    token      VARCHAR(64) NOT NULL,
    expires_at DATETIME    NOT NULL,
    used       BOOLEAN     NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id),
    UNIQUE KEY  uq_evt_token (token),
    INDEX       idx_evt_user (user_id),
    CONSTRAINT  fk_evt_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- =============================================================================
--  SECTION 3 — POSTS & RELATED CONTENT
-- =============================================================================

CREATE TABLE IF NOT EXISTS posts (
    id            INT          NOT NULL AUTO_INCREMENT,
    user_id       INT          NOT NULL,
    title         VARCHAR(255) NOT NULL,
    message       TEXT         NOT NULL,
    category      VARCHAR(100) NOT NULL,
    post_type_id  INT          NOT NULL,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    is_flagged    BOOLEAN      NOT NULL DEFAULT FALSE,
    latitude      DOUBLE                DEFAULT NULL,
    longitude     DOUBLE                DEFAULT NULL,
    location_text VARCHAR(255)          DEFAULT NULL,
    deleted_at    DATETIME              DEFAULT NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME              DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_user_active      (user_id, is_active),
    INDEX idx_category_date    (category, created_at),
    INDEX idx_type_date        (post_type_id, created_at),
    INDEX idx_active_type_date (is_active, post_type_id, created_at),
    INDEX idx_coordinates      (latitude, longitude),
    INDEX idx_posts_deleted    (deleted_at),
    CONSTRAINT fk_posts_user      FOREIGN KEY (user_id)      REFERENCES users(id)      ON DELETE CASCADE,
    CONSTRAINT fk_posts_post_type FOREIGN KEY (post_type_id) REFERENCES post_types(id) ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS post_multimedia (
    id         INT      NOT NULL AUTO_INCREMENT,
    post_id    INT      NOT NULL,
    url        TEXT     NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME          DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX      idx_post_uploaded (post_id, created_at),
    CONSTRAINT fk_post_multimedia_post FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS likes (
    id         INT      NOT NULL AUTO_INCREMENT,
    post_id    INT      NOT NULL,
    user_id    INT      NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME          DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY  uq_user_post_like (user_id, post_id),
    CONSTRAINT  fk_likes_post FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    CONSTRAINT  fk_likes_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS reports (
    id                INT          NOT NULL AUTO_INCREMENT,
    post_id           INT          NOT NULL,
    reporting_user_id INT          NOT NULL,
    reason            VARCHAR(255) NOT NULL,
    is_reviewed       BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME              DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX      idx_reports_post (post_id),
    INDEX      idx_reports_user (reporting_user_id),
    CONSTRAINT fk_reports_post FOREIGN KEY (post_id)           REFERENCES posts(id) ON DELETE CASCADE,
    CONSTRAINT fk_reports_user FOREIGN KEY (reporting_user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- =============================================================================
--  SECTION 4 — CHATS, MESSAGES & AGREEMENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS chats (
    id              INT      NOT NULL AUTO_INCREMENT,
    post_id         INT      NOT NULL,
    initiator_id    INT      NOT NULL,
    receiver_id     INT      NOT NULL,
    status_id       INT      NOT NULL DEFAULT 1,
    closing_date    DATETIME          DEFAULT NULL,
    resolution_note TEXT              DEFAULT NULL,
    is_active       BOOLEAN  NOT NULL DEFAULT TRUE,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME          DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY  uq_post_initiator (post_id, initiator_id),
    CONSTRAINT  fk_chats_post      FOREIGN KEY (post_id)      REFERENCES posts(id)             ON DELETE CASCADE,
    CONSTRAINT  fk_chats_initiator FOREIGN KEY (initiator_id) REFERENCES users(id)             ON DELETE CASCADE,
    CONSTRAINT  fk_chats_receiver  FOREIGN KEY (receiver_id)  REFERENCES users(id)             ON DELETE CASCADE,
    CONSTRAINT  fk_chats_status    FOREIGN KEY (status_id)    REFERENCES status_agreements(id) ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS chat_messages (
    id         INT      NOT NULL AUTO_INCREMENT,
    chat_id    INT      NOT NULL,
    sender_id  INT      NOT NULL,
    message    TEXT     NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME          DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX      idx_chat_sent (chat_id, created_at),
    CONSTRAINT fk_chat_messages_chat   FOREIGN KEY (chat_id)   REFERENCES chats(id) ON DELETE CASCADE,
    CONSTRAINT fk_chat_messages_sender FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS agreements (
    id           INT      NOT NULL AUTO_INCREMENT,
    post_id      INT      NOT NULL,
    initiator_id INT      NOT NULL,
    receiver_id  INT      NOT NULL,
    status_id    INT      NOT NULL DEFAULT 1,
    closing_date DATETIME          DEFAULT NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME          DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX      idx_status_dates (status_id, created_at),
    INDEX      idx_users_status (initiator_id, receiver_id, status_id),
    CONSTRAINT fk_agreements_post      FOREIGN KEY (post_id)      REFERENCES posts(id)             ON DELETE CASCADE,
    CONSTRAINT fk_agreements_initiator FOREIGN KEY (initiator_id) REFERENCES users(id)             ON DELETE CASCADE,
    CONSTRAINT fk_agreements_receiver  FOREIGN KEY (receiver_id)  REFERENCES users(id)             ON DELETE CASCADE,
    CONSTRAINT fk_agreements_status    FOREIGN KEY (status_id)    REFERENCES status_agreements(id) ON DELETE RESTRICT
);

-- =============================================================================
--  SECTION 5 — PUSH NOTIFICATIONS
-- =============================================================================

-- Stores the Expo push token for each user, along with their last known GPS
-- coordinates for server-side proximity filtering on post notifications.
CREATE TABLE IF NOT EXISTS user_push_tokens (
    user_id    INT          NOT NULL,
    token      VARCHAR(500) NOT NULL,
    latitude   DOUBLE                DEFAULT NULL,
    longitude  DOUBLE                DEFAULT NULL,
    updated_at DATETIME              DEFAULT NULL,
    PRIMARY KEY (user_id),
    CONSTRAINT fk_upt_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS notification_subscriptions (
    id           INT          NOT NULL AUTO_INCREMENT,
    user_id      INT          NOT NULL,
    post_type_id INT          NOT NULL,
    category     VARCHAR(100) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY  uq_sub    (user_id, post_type_id, category),
    INDEX       idx_ns_user (user_id),
    CONSTRAINT  fk_ns_user      FOREIGN KEY (user_id)      REFERENCES users(id)      ON DELETE CASCADE,
    CONSTRAINT  fk_ns_post_type FOREIGN KEY (post_type_id) REFERENCES post_types(id) ON DELETE CASCADE
);

-- =============================================================================
--  SECTION 6 — SEED DATA (lookup tables)
-- =============================================================================

INSERT IGNORE INTO roles (id, name) VALUES
    (1, 'user'),
    (2, 'moderator'),
    (3, 'admin');

INSERT IGNORE INTO status_users (id, name) VALUES
    (1, 'active'),
    (2, 'deleted'),
    (3, 'banned');

INSERT IGNORE INTO status_agreements (id, name) VALUES
    (1, 'pending'),
    (2, 'rejected'),
    (3, 'completed');

INSERT IGNORE INTO post_types (id, name) VALUES
    (1, 'Oferta'),
    (2, 'Necesidad');

-- Admin user: run the Python seed script (models/seed.py → admingen) to
-- generate the correctly bcrypt-hashed password for petlinkproject@gmail.com.

-- =============================================================================

SET FOREIGN_KEY_CHECKS = 1;
