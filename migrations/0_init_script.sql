-- create tables
CREATE TABLE IF NOT EXISTS votes
(
    id  INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    vote BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS results
(
    id  INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    vote_true INT,
    vote_false INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- create function to update results table
CREATE OR REPLACE FUNCTION update_result() RETURNS TRIGGER AS $$
DECLARE
    vote_true INT;
    vote_false INT;
BEGIN
    SELECT INTO vote_true count(*)
    FROM votes WHERE vote = TRUE;
    SELECT INTO vote_false count(*)
    FROM votes WHERE vote = FALSE;
    INSERT INTO results(vote_true, vote_false) VALUES
    (vote_true, vote_false);
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- create trigger on insert event of votes table
CREATE OR REPLACE TRIGGER t_update_result
AFTER INSERT ON votes
FOR EACH ROW EXECUTE PROCEDURE update_result();

-- Create function to notify new result
CREATE OR REPLACE FUNCTION notify_new_result() RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('new_result', concat_ws('|', NEW.id::TEXT, NEW.vote_true::TEXT, NEW.vote_false::TEXT));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on insert event of results table
CREATE OR REPLACE TRIGGER t_new_result
AFTER INSERT ON results
FOR EACH ROW EXECUTE PROCEDURE notify_new_result();
