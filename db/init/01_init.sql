CREATE TABLE IF NOT EXISTS device_snapshots (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    device_row_key VARCHAR(64) NOT NULL,
    update_time VARCHAR(64) NULL,
    json_data LONGTEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_device_row_key (device_row_key),
    KEY idx_created_at (created_at)
);