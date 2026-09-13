-- =========================
-- SAMPLE USERS
-- =========================

INSERT INTO Users (
    full_name,
    email,
    password_hash,
    role,
    balance
)
VALUES
(
    'Arjun Client',
    'arjun@gigtrust.com',
    'demo_hash',
    'CLIENT',
    50000.00
);

INSERT INTO Users (
    full_name,
    email,
    password_hash,
    role,
    balance
)
VALUES
(
    'Rahul Freelancer',
    'rahul@gigtrust.com',
    'demo_hash',
    'FREELANCER',
    5000.00
);

INSERT INTO Users (
    full_name,
    email,
    password_hash,
    role,
    balance
)
VALUES
(
    'GigTrust Admin',
    'admin@gigtrust.com',
    'demo_hash',
    'ADMIN',
    0.00
);


INSERT INTO Gigs (
    client_id,
    title,
    description,
    budget,
    status
)
VALUES
(
    1,
    'Build an AI Dashboard',
    'Develop a dashboard for monitoring freelance project activity.',
    10000.00,
    'OPEN'
);



INSERT INTO Bids (
    gig_id,
    freelancer_id,
    bid_amount,
    proposal,
    status
)
VALUES
(
    1,
    2,
    9500.00,
    'I can complete this project with FastAPI and Azure.',
    'PENDING'
);


UPDATE Bids
SET status = 'ACCEPTED'
WHERE bid_id = 1;


INSERT INTO Contracts (
    gig_id,
    client_id,
    freelancer_id,
    agreed_amount,
    status
)
VALUES
(
    1,
    1,
    2,
    9500.00,
    'ACTIVE'
);

UPDATE Gigs
SET status = 'IN_PROGRESS'
WHERE gig_id = 1;


INSERT INTO Escrows (
    contract_id,
    amount,
    status
)
VALUES
(
    1,
    9500.00,
    'UNFUNDED'
);



SELECT
    g.gig_id,
    g.title,
    c.full_name AS client_name,
    f.full_name AS freelancer_name,
    b.bid_amount,
    ct.agreed_amount,
    e.amount AS escrow_amount,
    e.status AS escrow_status
FROM Gigs g
JOIN Users c
    ON g.client_id = c.user_id
JOIN Bids b
    ON g.gig_id = b.gig_id
JOIN Users f
    ON b.freelancer_id = f.user_id
JOIN Contracts ct
    ON g.gig_id = ct.gig_id
JOIN Escrows e
    ON ct.contract_id = e.contract_id;