CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers (id),
    total_cents INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
