-- Create User_Credentials Table for VanCr Database
CREATE TABLE User_Credentials (
    user_id UNIQUEIDENTIFIER PRIMARY KEY,
    password_hash NVARCHAR(255) NOT NULL,
    failed_login_count INT NOT NULL DEFAULT 0,
    last_login_at DATETIME2 NULL,
    password_set_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    CONSTRAINT FK_UserCredentials_Users FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Create index on last_login_at for queries
CREATE INDEX IX_UserCredentials_LastLogin ON User_Credentials(last_login_at);
