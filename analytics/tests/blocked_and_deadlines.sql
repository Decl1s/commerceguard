select run_id, order_id from {{ ref('fct_order_reconciliation') }}
where (state = 'blocked' and
       (actual_capture_minor is not null or actual_refund_minor is not null))
   or (has_per_leg_context and
       (capture_due_at is null or refund_due_at is null or expectation_version is null
        or capture_state is null or refund_state is null))
