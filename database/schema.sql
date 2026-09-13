CREATE TABLE Users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,

    full_name VARCHAR(100) NOT NULL,

    email VARCHAR(150) NOT NULL UNIQUE,

    password_hash VARCHAR(255) NOT NULL,

    role VARCHAR(20) NOT NULL,

    balance DECIMAL(12,2) NOT NULL DEFAULT 0,

    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT CHK_Users_Role
        CHECK (role IN ('CLIENT', 'FREELANCER', 'ADMIN')),

    CONSTRAINT CHK_Users_Balance
        CHECK (balance >= 0)
);







CREATE TABLE Gigs (
    gig_id INT IDENTITY(1,1) PRIMARY KEY,

    client_id INT NOT NULL,

    title VARCHAR(150) NOT NULL,

    description VARCHAR(1000),

    budget DECIMAL(12,2) NOT NULL,

    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',

    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Gigs_Client
        FOREIGN KEY (client_id)
        REFERENCES Users(user_id),

    CONSTRAINT CHK_Gigs_Budget
        CHECK (budget > 0),

    CONSTRAINT CHK_Gigs_Status
        CHECK (
            status IN (
                'OPEN',
                'IN_PROGRESS',
                'COMPLETED',
                'CANCELLED'
            )
        )
);




CREATE TABLE Bids (
    bid_id INT IDENTITY(1,1) PRIMARY KEY,

    gig_id INT NOT NULL,

    freelancer_id INT NOT NULL,

    bid_amount DECIMAL(12,2) NOT NULL,

    proposal VARCHAR(1000),

    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Bids_Gig
        FOREIGN KEY (gig_id)
        REFERENCES Gigs(gig_id),

    CONSTRAINT FK_Bids_Freelancer
        FOREIGN KEY (freelancer_id)
        REFERENCES Users(user_id),

    CONSTRAINT CHK_Bids_Amount
        CHECK (bid_amount > 0),

    CONSTRAINT CHK_Bids_Status
        CHECK (
            status IN (
                'PENDING',
                'ACCEPTED',
                'REJECTED'
            )
        ),

    CONSTRAINT UQ_Bids_Gig_Freelancer
        UNIQUE (gig_id, freelancer_id)
);




CREATE TABLE Contracts (
    contract_id INT IDENTITY(1,1) PRIMARY KEY,

    gig_id INT NOT NULL UNIQUE,

    client_id INT NOT NULL,

    freelancer_id INT NOT NULL,

    agreed_amount DECIMAL(12,2) NOT NULL,

    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',

    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Contracts_Gig
        FOREIGN KEY (gig_id)
        REFERENCES Gigs(gig_id),

    CONSTRAINT FK_Contracts_Client
        FOREIGN KEY (client_id)
        REFERENCES Users(user_id),

    CONSTRAINT FK_Contracts_Freelancer
        FOREIGN KEY (freelancer_id)
        REFERENCES Users(user_id),

    CONSTRAINT CHK_Contracts_Amount
        CHECK (agreed_amount > 0),

    CONSTRAINT CHK_Contracts_Status
        CHECK (
            status IN (
                'ACTIVE',
                'WORK_SUBMITTED',
                'COMPLETED',
                'CANCELLED'
            )
        )
);





CREATE TABLE Escrows (
    escrow_id INT IDENTITY(1,1) PRIMARY KEY,

    contract_id INT NOT NULL UNIQUE,

    amount DECIMAL(12,2) NOT NULL,

    status VARCHAR(30) NOT NULL DEFAULT 'UNFUNDED',

    funded_at DATETIME2 NULL,

    released_at DATETIME2 NULL,

    CONSTRAINT FK_Escrows_Contract
        FOREIGN KEY (contract_id)
        REFERENCES Contracts(contract_id),

    CONSTRAINT CHK_Escrows_Amount
        CHECK (amount > 0),

    CONSTRAINT CHK_Escrows_Status
        CHECK (
            status IN (
                'UNFUNDED',
                'HELD',
                'RELEASED',
                'REFUNDED'
            )
        )
);






CREATE TABLE Transactions (
    transaction_id BIGINT IDENTITY(1,1) PRIMARY KEY,

    escrow_id INT NOT NULL,

    sender_id INT NOT NULL,

    receiver_id INT NULL,

    amount DECIMAL(12,2) NOT NULL,

    transaction_type VARCHAR(30) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS',

    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Transactions_Escrow
        FOREIGN KEY (escrow_id)
        REFERENCES Escrows(escrow_id),

    CONSTRAINT FK_Transactions_Sender
        FOREIGN KEY (sender_id)
        REFERENCES Users(user_id),

    CONSTRAINT FK_Transactions_Receiver
        FOREIGN KEY (receiver_id)
        REFERENCES Users(user_id),

    CONSTRAINT CHK_Transactions_Amount
        CHECK (amount > 0),

    CONSTRAINT CHK_Transactions_Type
        CHECK (
            transaction_type IN (
                'ESCROW_FUND',
                'ESCROW_RELEASE',
                'ESCROW_REFUND'
            )
        ),

    CONSTRAINT CHK_Transactions_Status
        CHECK (
            status IN (
                'SUCCESS',
                'FAILED'
            )
        )
);






CREATE TABLE LedgerBlocks (
    block_id BIGINT IDENTITY(1,1) PRIMARY KEY,

    transaction_id BIGINT NOT NULL UNIQUE,

    escrow_id INT NOT NULL,

    sender_id INT NOT NULL,

    receiver_id INT NULL,

    amount DECIMAL(12,2) NOT NULL,

    transaction_type VARCHAR(30) NOT NULL,

    previous_hash VARCHAR(64) NOT NULL,

    current_hash VARCHAR(64) NOT NULL,

    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_Ledger_Transaction
        FOREIGN KEY (transaction_id)
        REFERENCES Transactions(transaction_id)
);


ALTER TABLE LedgerBlocks
ADD hash_timestamp VARCHAR(50) NULL;