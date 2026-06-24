-- Push Notifications infrastructure
-- Run once against the production MySQL database.
-- No Alembic — manual migration.

CREATE TABLE IF NOT EXISTS user_push_tokens (
    user_id     INT         NOT NULL,
    token       VARCHAR(500) NOT NULL,
    latitude    DOUBLE      NULL,
    longitude   DOUBLE      NULL,
    updated_at  DATETIME    NULL,
    PRIMARY KEY (user_id),
    CONSTRAINT fk_upt_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notification_subscriptions (
    id          INT         NOT NULL AUTO_INCREMENT,
    user_id     INT         NOT NULL,
    post_type_id INT        NOT NULL,
    category    VARCHAR(100) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_sub (user_id, post_type_id, category),
    INDEX idx_ns_user (user_id),
    CONSTRAINT fk_ns_user      FOREIGN KEY (user_id)      REFERENCES users(id)      ON DELETE CASCADE,
    CONSTRAINT fk_ns_post_type FOREIGN KEY (post_type_id) REFERENCES post_types(id) ON DELETE CASCADE
);
