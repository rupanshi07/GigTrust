BEGIN TRANSACTION;

-- Lock User 1
UPDATE Users
SET balance = balance
WHERE user_id = 1;

WAITFOR DELAY '00:00:05';

-- Then try to lock User 2
UPDATE Users
SET balance = balance
WHERE user_id = 2;

COMMIT TRANSACTION;


BEGIN TRANSACTION;

-- Lock User 2
UPDATE Users
SET balance = balance
WHERE user_id = 2;

WAITFOR DELAY '00:00:05';

-- Then try to lock User 1
UPDATE Users
SET balance = balance
WHERE user_id = 1;

COMMIT TRANSACTION;