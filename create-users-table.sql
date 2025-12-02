-- Create Users Table for VanCr Database
CREATE TABLE Users (
    user_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    email NVARCHAR(255) NOT NULL UNIQUE,
    phone NVARCHAR(50) NULL,
    first_name NVARCHAR(100) NOT NULL,
    last_name NVARCHAR(100) NOT NULL,
    active BIT NOT NULL DEFAULT 1,
    access_level NVARCHAR(50) NOT NULL DEFAULT 'Standard',
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    deleted_at DATETIME2 NULL,
    CONSTRAINT CHK_Phone_Unique UNIQUE (phone)
);

-- Create index on email for faster lookups
CREATE INDEX IX_Users_Email ON Users(email);

-- Create index on active status
CREATE INDEX IX_Users_Active ON Users(active);
