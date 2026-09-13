-- =====================================================
-- GIGTRUST ESCROW FUNDING TRANSACTION
-- =====================================================

BEGIN TRY

    BEGIN TRANSACTION;

    DECLARE @ClientID INT = 1;
    DECLARE @EscrowID INT = 1;
    DECLARE @Amount DECIMAL(12,2) = 9500.00;

    -- Check whether the client has enough balance
    IF (
        SELECT balance
        FROM Users
        WHERE user_id = @ClientID
    ) < @Amount
    BEGIN
        THROW 50001, 'Insufficient client balance.', 1;
    END;

    -- Deduct money from the client
    UPDATE Users
    SET balance = balance - @Amount
    WHERE user_id = @ClientID;

    -- Mark escrow as funded
    UPDATE Escrows
    SET
        status = 'HELD',
        funded_at = SYSUTCDATETIME()
    WHERE escrow_id = @EscrowID
      AND status = 'UNFUNDED';

    -- Ensure escrow was actually updated
    IF @@ROWCOUNT = 0
    BEGIN
        THROW 50002, 'Escrow is not available for funding.', 1;
    END;

    -- Record the financial transaction
    INSERT INTO Transactions (
        escrow_id,
        sender_id,
        receiver_id,
        amount,
        transaction_type,
        status
    )
    VALUES (
        @EscrowID,
        @ClientID,
        NULL,
        @Amount,
        'ESCROW_FUND',
        'SUCCESS'
    );

    COMMIT TRANSACTION;

END TRY

BEGIN CATCH

    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;

END CATCH;


SELECT
    escrow_id,
    amount,
    status,
    funded_at
FROM Escrows
WHERE escrow_id = 1;


-- =====================================================
-- ROLLBACK / ATOMICITY DEMONSTRATION
-- =====================================================

BEGIN TRY

    BEGIN TRANSACTION;

    DECLARE @ClientID INT = 1;
    DECLARE @Amount DECIMAL(12,2) = 1000.00;

    -- Step 1: deduct balance
    UPDATE Users
    SET balance = balance - @Amount
    WHERE user_id = @ClientID;

    -- Step 2: intentionally force an error
    THROW 50010, 'Intentional failure for rollback demo.', 1;

    -- This line will never execute
    COMMIT TRANSACTION;

END TRY

BEGIN CATCH

    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    PRINT 'Transaction rolled back successfully.';

END CATCH;