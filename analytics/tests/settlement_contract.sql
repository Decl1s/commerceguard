-- Я проверяю unknown/null, независимую формулу тарифа и денежное равенство matched.
select report_id from {{ ref('mart_settlement_reconciliation') }}
where (state = 'unknown' and (expected_gross_minor is not null or expected_refund_minor is not null
                            or expected_fee_minor is not null or expected_net_minor is not null))
   or (state <> 'unknown' and (expected_gross_minor is null or expected_refund_minor is null
                              or expected_fee_minor is null or expected_net_minor is null))
   or (state <> 'unknown' and
       (expected_net_minor <> expected_gross_minor - expected_refund_minor - expected_fee_minor
        or expected_fee_minor <> floor((expected_gross_minor::numeric * fee_bps + 5000) / 10000)))
   or (state = 'matched' and (reported_gross_minor <> expected_gross_minor
                              or reported_refund_minor <> expected_refund_minor
                              or reported_fee_minor <> expected_fee_minor or reported_net_minor <> expected_net_minor))
