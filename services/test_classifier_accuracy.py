from services.classifier import classify_complaint


TEST_CASES = [
    # billing
    ("Why is my internet bill higher than usual?", "billing"),
    ("I was charged an unexpected amount on my broadband bill.", "billing"),
    ("Can you explain this extra charge on my account?", "billing"),

    # installation
    ("I need an appointment to install my internet.", "installation"),
    ("When will the technician come to set up my connection?", "installation"),
    ("My new broadband installation has not happened yet.", "installation"),

    # intermittent_connection
    ("My internet keeps disconnecting every few minutes.", "intermittent_connection"),
    ("The connection drops randomly throughout the day.", "intermittent_connection"),
    ("My WiFi cuts out and then comes back again.", "intermittent_connection"),

    # no_internet
    ("I have no internet connection at all.", "no_internet"),
    ("My internet is completely down.", "no_internet"),
    ("There is no connection even after restarting the router.", "no_internet"),

    # plan_change
    ("I want to upgrade my internet plan.", "plan_change"),
    ("How can I change my broadband package?", "plan_change"),
    ("I would like to switch to a different internet plan.", "plan_change"),

    # router_modem
    ("My router is not working properly.", "router_modem"),
    ("How do I restart or reset my modem?", "router_modem"),
    ("My WiFi router keeps showing an error light.", "router_modem"),

    # service_outage
    ("Is there an internet outage in my area?", "service_outage"),
    ("Has the ISP reported a service outage?", "service_outage"),
    ("Everyone in my neighborhood seems to have lost service.", "service_outage"),

    # slow_internet
    ("My internet speed is extremely slow.", "slow_internet"),
    ("Why is my broadband so slow today?", "slow_internet"),
    ("My connection is much slower than normal.", "slow_internet"),

    # technical_support
    ("I need help troubleshooting my internet connection.", "technical_support"),
    ("Can someone help me diagnose an internet problem?", "technical_support"),
    ("I need technical assistance with my connection.", "technical_support"),
]


def main():
    total = len(TEST_CASES)
    correct = 0

    print("=" * 70)
    print("NetAssist AI - Production Complaint Classifier Test")
    print("=" * 70)

    results = []

    for index, (text, expected) in enumerate(TEST_CASES, start=1):
        result = classify_complaint(text)

        predicted = result["category"]
        confidence = result["confidence"]

        is_correct = predicted == expected

        if is_correct:
            correct += 1

        results.append(is_correct)

        status = "PASS" if is_correct else "FAIL"

        print(f"\n[{index:02d}] {status}")
        print(f"Message:    {text}")
        print(f"Expected:   {expected}")
        print(f"Predicted:  {predicted}")
        print(f"Confidence: {confidence:.4f}")

    accuracy = correct / total

    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    print(f"Total tests:     {total}")
    print(f"Correct:         {correct}")
    print(f"Incorrect:       {total - correct}")
    print(f"Accuracy:        {accuracy:.4f}")
    print(f"Accuracy (%):    {accuracy * 100:.2f}%")

    print("\nRequired minimum: 80.00%")

    if accuracy >= 0.80:
        print("\nRESULT: PASS")
        print("Production complaint classifier passed the accuracy test.")
    else:
        print("\nRESULT: FAIL")
        print("Production complaint classifier did not meet the minimum accuracy.")


if __name__ == "__main__":
    main()