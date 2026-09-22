"""Small executable smoke check for the deterministic policy boundary."""

from agent.policy import Action, Route, proposal, should_file_report, validate_block_all_cards


def main() -> None:
    assert proposal(Action.BLOCK_CARD, 2500, "R2").route == Route.L1
    assert proposal(Action.BLOCK_CARD, 2500.01, "R2").route == Route.L2
    assert proposal(Action.FILE_REPORT, 1, "R6").route == Route.L2
    assert should_file_report(strongly_suspected_or_confirmed=True, exposure_usd=1000.01)
    assert not should_file_report(strongly_suspected_or_confirmed=True, exposure_usd=1000)
    try:
        validate_block_all_cards(at_least_two_confirmed_cards=False, credentials_confirmed_compromised=False)
    except ValueError:
        pass
    else:
        raise AssertionError("R10 guardrail was not enforced")
    print("policy smoke check passed")


if __name__ == "__main__":
    main()