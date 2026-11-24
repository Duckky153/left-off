-- The queue: shoppers who stopped partway, at one of the stop points, who haven't finished.
-- A waiting message: an unanswered message from the shopper in the last 24 hours.
-- A quiet stall: no unanswered message at all, and no activity for 3 to 30 days.
-- (:since, :quiet_from and :quiet_to come from rules.json and the run clock.)
SELECT id,
       CASE WHEN message_at IS NOT NULL AND message_answered = 0 AND message_at >= :since
            THEN 'waiting' ELSE 'quiet' END AS kind
FROM shoppers
WHERE stop IN (:stops)
  AND finished IS NULL
  AND (
        (message_at IS NOT NULL AND message_answered = 0 AND message_at >= :since)
     OR ((message_at IS NULL OR message_answered = 1)
         AND last_activity_at >= :quiet_from
         AND last_activity_at <= :quiet_to)
  )
ORDER BY id;
