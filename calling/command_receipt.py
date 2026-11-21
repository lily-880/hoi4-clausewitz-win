"""Pure offline receipt assessment. No process, Post, recovery action, or game calls.

Keep observed state distinct from a request/queue acknowledgement. This module
cannot and must not try to pause a game. It only evaluates supplied evidence.
"""
def assess_pause_receipt(*, accepted, requested_pause, observed_pause):
    if type(accepted) is not bool or type(requested_pause) is not bool:
        raise ValueError('receipt/request must be boolean')
    if observed_pause is not None and (type(observed_pause) is not int or observed_pause not in (0, 1)):
        raise ValueError('observed official pause must be 0, 1, or unknown')
    confirmed = observed_pause is not None and observed_pause == int(requested_pause)
    return {'queue_accepted': accepted, 'requested_pause': requested_pause,
            'observed_pause': observed_pause, 'state_change_confirmed': confirmed,
            'official_pause_confirmed': observed_pause == 1,
            'needs_readonly_verification': observed_pause is None,
            'acknowledgement_is_not_execution_proof': True}


def retain_unpaused_risk(*, was_unpaused, observed_pause):
    """Pure safety bookkeeping; queue acknowledgement is deliberately absent.

    Only an observed official pause1 may clear an existing unpaused risk.
    This function never retries, pauses, or touches a process.
    """
    if type(was_unpaused) is not bool:
        raise ValueError('risk flag must be boolean')
    if observed_pause is not None and (type(observed_pause) is not int or observed_pause not in (0, 1)):
        raise ValueError('official pause must be 0, 1, or unknown')
    return was_unpaused and observed_pause != 1
