-- Define user_id and subscription_id variables
SET @user_id = 71;
SET @subscription_id = "id";

-- Insert into StripeInfo table
INSERT INTO StripeInfo (user_id, stripe_customer_id, anchor_date) 
VALUES (@user_id, @subscription_id, CURRENT_TIMESTAMP);

-- Retrieve the inserted StripeInfo id
SET @stripe_info_id = LAST_INSERT_ID();

-- Insert into Subscriptions table
INSERT INTO Subscriptions (stripe_info_id, subscription_id, start_date, paid_user) 
VALUES (@stripe_info_id, @subscription_id, CURRENT_TIMESTAMP, 3);
