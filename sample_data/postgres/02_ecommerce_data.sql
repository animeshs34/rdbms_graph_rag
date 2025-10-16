-- E-commerce Sample Data for PostgreSQL

-- Insert Categories
INSERT INTO categories (name, description, parent_category_id) VALUES
('Electronics', 'Electronic devices and accessories', NULL),
('Computers', 'Computers and computer accessories', 1),
('Smartphones', 'Mobile phones and accessories', 1),
('Clothing', 'Apparel and fashion', NULL),
('Men''s Clothing', 'Clothing for men', 4),
('Women''s Clothing', 'Clothing for women', 4),
('Books', 'Books and literature', NULL),
('Home & Garden', 'Home improvement and garden supplies', NULL);

-- Insert Customers
INSERT INTO customers (email, first_name, last_name, phone, address, city, state, zip_code) VALUES
('john.doe@email.com', 'John', 'Doe', '555-0101', '123 Main St', 'New York', 'NY', '10001'),
('jane.smith@email.com', 'Jane', 'Smith', '555-0102', '456 Oak Ave', 'Los Angeles', 'CA', '90001'),
('bob.johnson@email.com', 'Bob', 'Johnson', '555-0103', '789 Pine Rd', 'Chicago', 'IL', '60601'),
('alice.williams@email.com', 'Alice', 'Williams', '555-0104', '321 Elm St', 'Houston', 'TX', '77001'),
('charlie.brown@email.com', 'Charlie', 'Brown', '555-0105', '654 Maple Dr', 'Phoenix', 'AZ', '85001'),
('diana.davis@email.com', 'Diana', 'Davis', '555-0106', '987 Cedar Ln', 'Philadelphia', 'PA', '19101'),
('edward.miller@email.com', 'Edward', 'Miller', '555-0107', '147 Birch Ct', 'San Antonio', 'TX', '78201'),
('fiona.wilson@email.com', 'Fiona', 'Wilson', '555-0108', '258 Spruce Way', 'San Diego', 'CA', '92101'),
('george.moore@email.com', 'George', 'Moore', '555-0109', '369 Ash Blvd', 'Dallas', 'TX', '75201'),
('hannah.taylor@email.com', 'Hannah', 'Taylor', '555-0110', '741 Walnut Ave', 'San Jose', 'CA', '95101');

-- Insert Products
INSERT INTO products (name, description, category_id, price, stock_quantity, sku, brand) VALUES
('Laptop Pro 15', 'High-performance laptop with 15-inch display', 2, 1299.99, 50, 'LAP-PRO-15', 'TechBrand'),
('Smartphone X', 'Latest smartphone with advanced features', 3, 899.99, 100, 'PHONE-X', 'PhoneCorp'),
('Wireless Mouse', 'Ergonomic wireless mouse', 2, 29.99, 200, 'MOUSE-W1', 'TechBrand'),
('USB-C Cable', 'High-speed USB-C charging cable', 2, 19.99, 500, 'CABLE-USBC', 'TechBrand'),
('Men''s T-Shirt', 'Cotton t-shirt in various colors', 5, 24.99, 300, 'TSHIRT-M-001', 'FashionCo'),
('Women''s Jeans', 'Comfortable denim jeans', 6, 59.99, 150, 'JEANS-W-001', 'FashionCo'),
('Programming Book', 'Learn Python programming', 7, 39.99, 75, 'BOOK-PY-001', 'TechBooks'),
('Garden Tools Set', 'Complete set of garden tools', 8, 79.99, 40, 'GARDEN-SET-1', 'GardenPro'),
('Wireless Headphones', 'Noise-cancelling headphones', 1, 199.99, 80, 'HEAD-W1', 'AudioTech'),
('Smart Watch', 'Fitness tracking smart watch', 3, 299.99, 60, 'WATCH-S1', 'PhoneCorp');

-- Insert Orders
INSERT INTO orders (customer_id, order_date, status, total_amount, payment_method) VALUES
(1, '2024-01-15 10:30:00', 'delivered', 1329.98, 'credit_card'),
(2, '2024-01-16 14:20:00', 'delivered', 929.98, 'paypal'),
(3, '2024-01-17 09:15:00', 'shipped', 84.98, 'credit_card'),
(4, '2024-01-18 16:45:00', 'processing', 299.99, 'debit_card'),
(5, '2024-01-19 11:00:00', 'delivered', 139.97, 'credit_card'),
(1, '2024-01-20 13:30:00', 'delivered', 199.99, 'credit_card'),
(6, '2024-01-21 10:00:00', 'shipped', 59.99, 'paypal'),
(7, '2024-01-22 15:20:00', 'processing', 1299.99, 'credit_card'),
(8, '2024-01-23 12:10:00', 'delivered', 79.99, 'debit_card'),
(9, '2024-01-24 14:50:00', 'pending', 899.99, 'credit_card');

-- Insert Order Items
INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES
(1, 1, 1, 1299.99, 1299.99),
(1, 3, 1, 29.99, 29.99),
(2, 2, 1, 899.99, 899.99),
(2, 4, 1, 19.99, 19.99),
(2, 3, 1, 29.99, 29.99),
(3, 5, 2, 24.99, 49.98),
(3, 7, 1, 39.99, 39.99),
(4, 10, 1, 299.99, 299.99),
(5, 6, 1, 59.99, 59.99),
(5, 5, 2, 24.99, 49.98),
(5, 4, 1, 19.99, 19.99),
(6, 9, 1, 199.99, 199.99),
(7, 6, 1, 59.99, 59.99),
(8, 1, 1, 1299.99, 1299.99),
(9, 8, 1, 79.99, 79.99),
(10, 2, 1, 899.99, 899.99);

-- Insert Reviews
INSERT INTO reviews (product_id, customer_id, rating, title, comment, verified_purchase) VALUES
(1, 1, 5, 'Excellent laptop!', 'This laptop exceeded my expectations. Fast and reliable.', TRUE),
(2, 2, 4, 'Great phone', 'Love the camera quality, battery life could be better.', TRUE),
(3, 1, 5, 'Perfect mouse', 'Very comfortable and responsive.', TRUE),
(5, 3, 4, 'Good quality', 'Nice fabric, fits well.', TRUE),
(6, 5, 5, 'Love these jeans!', 'Perfect fit and very comfortable.', TRUE),
(7, 3, 5, 'Must-read for programmers', 'Clear explanations and great examples.', TRUE),
(9, 1, 5, 'Amazing sound quality', 'Best headphones I''ve ever owned.', TRUE),
(8, 9, 4, 'Good tools', 'Solid construction, good value for money.', TRUE),
(1, 7, 5, 'Best purchase ever', 'This laptop is incredibly fast and the display is stunning.', TRUE),
(2, 9, 3, 'Decent phone', 'Good features but a bit overpriced.', FALSE);

-- Insert Wishlist items
INSERT INTO wishlist (customer_id, product_id) VALUES
(1, 10),
(2, 1),
(3, 9),
(4, 2),
(5, 8),
(6, 1),
(7, 9),
(8, 10),
(9, 1),
(10, 2);

