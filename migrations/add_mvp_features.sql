-- MVP features: email verification, content flags, user warnings/bans
-- Run once against the production database.

-- Users: email verification, sanction tracking
ALTER TABLE users
    ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN warnings        INT      NOT NULL DEFAULT 0,
    ADD COLUMN banned_until    DATETIME          DEFAULT NULL;

-- Posts: auto-moderation flag
ALTER TABLE posts
    ADD COLUMN is_flagged BOOLEAN NOT NULL DEFAULT FALSE;

-- Email verification tokens
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id          INT          NOT NULL AUTO_INCREMENT,
    user_id     INT          NOT NULL,
    token       VARCHAR(64)  NOT NULL,
    expires_at  DATETIME     NOT NULL,
    used        BOOLEAN      NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id),
    UNIQUE KEY  uq_evt_token (token),
    INDEX       idx_evt_user (user_id),
    CONSTRAINT  fk_evt_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
